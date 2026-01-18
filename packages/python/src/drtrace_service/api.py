from __future__ import annotations

import base64
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import analysis, help_agent_interface, storage
from .models import LogBatch
from .status import get_status

app = FastAPI(title="DrTrace Daemon", version="0.1.0")


# -----------------------------------------------------------------------------
# Time Parsing Utilities (Story API-1)
# -----------------------------------------------------------------------------

def parse_time_param(value: str, is_end: bool = False) -> float:
    """Parse human-readable time to Unix timestamp.

    Accepts:
    - Relative: "5m", "1h", "2d", "30s"
    - ISO 8601: "2025-12-31T02:44:03"
    - ISO 8601 with TZ: "2025-12-31T02:44:03+07:00"
    - Unix timestamp: "1767149043" or "1767149043.5"

    Args:
        value: Time string to parse
        is_end: If True and value is integer timestamp, add 0.999999 for end of second

    Returns:
        Unix timestamp as float

    Raises:
        ValueError: If the time format cannot be parsed
    """
    value = value.strip()

    # Try relative time first (e.g., "5m", "1h", "2d", "30s")
    relative_match = re.match(r'^(\d+)([smhd])$', value, re.IGNORECASE)
    if relative_match:
        amount = int(relative_match.group(1))
        unit = relative_match.group(2).lower()
        unit_map = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
        delta = timedelta(**{unit_map[unit]: amount})
        return (datetime.now(timezone.utc) - delta).timestamp()

    # Try ISO 8601 with timezone
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        pass

    # Try Unix timestamp (integer or float)
    try:
        ts = float(value)
        # If integer and is_end, add 0.999999 to get end of second
        if is_end and ts == int(ts):
            ts += 0.999999
        return ts
    except ValueError:
        pass

    raise ValueError(f"Cannot parse time: {value}")


# -----------------------------------------------------------------------------
# Level Filtering Utilities (Story API-3)
# -----------------------------------------------------------------------------

LEVEL_ORDER = {
    "DEBUG": 0,
    "INFO": 1,
    "WARN": 2,
    "WARNING": 2,  # Alias for WARN
    "ERROR": 3,
    "CRITICAL": 4,
}


def get_levels_at_or_above(min_level: str) -> List[str]:
    """Get all levels at or above the specified minimum level."""
    min_level_upper = min_level.upper()
    if min_level_upper not in LEVEL_ORDER:
        raise ValueError(f"Unknown level: {min_level}")

    min_order = LEVEL_ORDER[min_level_upper]
    return [level for level, order in LEVEL_ORDER.items() if order >= min_order]


# -----------------------------------------------------------------------------
# Pagination Utilities (Story API-4)
# -----------------------------------------------------------------------------

def encode_cursor(ts: float, record_id: str) -> str:
    """Encode cursor as base64 JSON."""
    cursor_data = {"ts": ts, "id": record_id}
    return base64.urlsafe_b64encode(json.dumps(cursor_data).encode()).decode()


def decode_cursor(cursor: str) -> dict:
    """Decode cursor from base64 JSON."""
    try:
        return json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:
        raise ValueError("Invalid cursor format")

# CORS configuration for browser clients
# Allow all origins by default, configurable via DRTRACE_CORS_ORIGINS env var
CORS_ORIGINS = os.environ.get("DRTRACE_CORS_ORIGINS", "*")
if CORS_ORIGINS == "*":
    origins = ["*"]
else:
    origins = [o.strip() for o in CORS_ORIGINS.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models for /help/guide/* endpoints
class StartGuideRequest(BaseModel):
    """Request model for POST /help/guide/start"""
    language: str
    project_root: str


class CompleteStepRequest(BaseModel):
    """Request model for POST /help/guide/complete"""
    step_number: int
    project_root: str


class TroubleshootRequest(BaseModel):
    """Request model for POST /help/troubleshoot"""
    issue: str
    project_root: str


@app.get("/status")
async def status_endpoint() -> Dict[str, object]:
  """
  Lightweight status endpoint for the local daemon.
  """
  # In a fuller implementation we would include DB/queue checks here.
  return get_status()


@app.post("/logs/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_logs(batch: LogBatch) -> Dict[str, int]:
  """
  Ingestion endpoint for batched log events.

  This slice validates the payload shape and delegates persistence to
  the storage layer.
  """
  import logging
  import time

  logger = logging.getLogger(__name__)
  now = time.time()

  # Check for suspicious timestamps
  for log in batch.logs:
    if log.ts > now + 300:  # More than 5 minutes in future
      logger.warning(f"Log timestamp {log.ts} is {log.ts - now:.1f}s in the future")
    if log.ts < now - 86400:  # More than 1 day in past
      logger.warning(f"Log timestamp {log.ts} is {now - log.ts:.1f}s in the past")

  # Check for identical timestamps in batch
  timestamps = [log.ts for log in batch.logs]
  unique_timestamps = len(set(timestamps))
  if unique_timestamps == 1 and len(batch.logs) > 1:
    logger.warning(f"All {len(batch.logs)} logs in batch have identical timestamp {timestamps[0]}")

  backend = storage.get_storage()
  backend.write_batch(batch)
  return {"accepted": len(batch.logs)}


@app.get("/logs/query")
async def query_logs(
  # New human-readable time params (Story API-1)
  since: Optional[str] = Query(
    None,
    description="Start time (UTC): relative ('5m', '1h', '2d'), ISO 8601 ('2025-12-31T02:44:03'), or Unix timestamp. ISO 8601 without timezone is interpreted as UTC. Default: last 5 minutes"
  ),
  until: Optional[str] = Query(
    None,
    description="End time (UTC): relative ('5m', '1h', '2d'), ISO 8601 ('2025-12-31T02:44:03'), or Unix timestamp. ISO 8601 without timezone is interpreted as UTC. Default: now"
  ),
  # Legacy time params (backward compatible)
  start_ts: Optional[float] = Query(
    None,
    description="Start timestamp in UTC Unix epoch (deprecated, use 'since')"
  ),
  end_ts: Optional[float] = Query(
    None,
    description="End timestamp in UTC Unix epoch (deprecated, use 'until')"
  ),
  # Existing filters
  application_id: Optional[str] = Query(None, description="Optional application_id filter"),
  module_name: Optional[str] = Query(None, description="Optional module_name filter"),
  # New filters (Stories API-2, API-3, Epic 11.1)
  message_contains: Optional[str] = Query(
    None,
    description="Case-insensitive substring search in log message"
  ),
  message_regex: Optional[str] = Query(
    None,
    description="POSIX regex pattern for message matching (mutually exclusive with message_contains)"
  ),
  min_level: Optional[str] = Query(
    None,
    description="Minimum log level: DEBUG, INFO, WARN, ERROR, CRITICAL"
  ),
  # Pagination (Story API-4)
  cursor: Optional[str] = Query(
    None,
    description="Pagination cursor from previous response's next_cursor"
  ),
  limit: int = Query(100, ge=1, le=1000, description="Max number of records to return"),
) -> Dict[str, object]:
  """
  Query logs with flexible time formats, filters, and pagination.

  **Important: All Timestamps Are UTC**

  All timestamps in the DrTrace API are in UTC:
  - The `ts` field in log records is a UTC Unix timestamp (float)
  - Query params `start_ts`, `end_ts`, `since`, `until` expect UTC time
  - ISO 8601 without timezone (e.g., "2025-12-31T02:44:03") is interpreted as UTC
  - To query with local time, include timezone offset: "2025-12-31T09:44:03+07:00"

  **Time Formats (since/until)**:
  - Relative: "5m" (5 minutes), "1h" (1 hour), "2d" (2 days), "30s" (30 seconds)
  - ISO 8601 UTC: "2025-12-31T02:44:03" or "2025-12-31T02:44:03Z"
  - ISO 8601 with TZ: "2025-12-31T09:44:03+07:00" (converted to UTC internally)
  - Unix timestamp: "1767149043" or "1767149043.5"

  **Pagination**:
  Use `cursor` from response's `next_cursor` to fetch the next page.
  Response includes `has_more` (boolean) and `next_cursor` (string or null).
  """
  now = datetime.now(timezone.utc).timestamp()

  # Determine start time (Story API-1)
  if since:
    try:
      start = parse_time_param(since, is_end=False)
    except ValueError as e:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "INVALID_TIME_FORMAT", "message": str(e)}
      )
  elif start_ts is not None:
    start = start_ts
  else:
    # Default: last 5 minutes
    start = now - 300

  # Determine end time (Story API-1)
  if until:
    try:
      end = parse_time_param(until, is_end=True)
    except ValueError as e:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "INVALID_TIME_FORMAT", "message": str(e)}
      )
  elif end_ts is not None:
    end = end_ts
  else:
    end = now

  # Validate message_contains and message_regex are mutually exclusive (Epic 11.1)
  if message_contains and message_regex:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail={
        "code": "INVALID_PARAMS",
        "message": "Cannot use both message_contains and message_regex. Choose one."
      }
    )

  # Validate message_regex pattern (Epic 11.1)
  if message_regex:
    if len(message_regex) > 500:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
          "code": "INVALID_PATTERN",
          "message": "Pattern too long (max 500 characters)"
        }
      )
    # Try to compile the pattern to catch syntax errors early
    try:
      re.compile(message_regex)
    except re.error as e:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
          "code": "INVALID_PATTERN",
          "message": f"Invalid regex pattern: {str(e)}"
        }
      )

  # Validate min_level (Story API-3)
  if min_level:
    try:
      get_levels_at_or_above(min_level)
    except ValueError:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
          "code": "INVALID_LEVEL",
          "message": f"Invalid min_level '{min_level}'. Valid levels: DEBUG, INFO, WARN, ERROR, CRITICAL"
        }
      )

  # Decode cursor (Story API-4)
  after_cursor = None
  if cursor:
    try:
      after_cursor = decode_cursor(cursor)
    except ValueError:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "INVALID_CURSOR", "message": "Invalid cursor format"}
      )

  # Fetch limit+1 to determine has_more (Story API-4)
  backend = storage.get_storage()
  records = backend.query_time_range(
    start_ts=start,
    end_ts=end,
    application_id=application_id,
    module_name=module_name,
    message_contains=message_contains,
    message_regex=message_regex,
    min_level=min_level.upper() if min_level else None,
    after_cursor=after_cursor,
    limit=limit + 1,  # Fetch one extra to check has_more
  )

  # Determine has_more and trim results (Story API-4)
  has_more = len(records) > limit
  if has_more:
    records = records[:limit]

  # Generate next_cursor from last result (Story API-4)
  next_cursor = None
  if has_more and records:
    last = records[-1]
    # Use ts and a unique identifier (or ts itself as string)
    next_cursor = encode_cursor(last.ts, str(last.ts))

  return {
    "results": [r.model_dump() for r in records],
    "count": len(records),
    "has_more": has_more,
    "next_cursor": next_cursor,
  }


@app.post("/logs/clear", status_code=status.HTTP_200_OK)
async def clear_logs(
  application_id: str,
  environment: Optional[str] = Query(None, description="Optional environment scope (context.environment)"),
) -> Dict[str, int]:
  """
  Admin endpoint to clear logs scoped to a specific application_id.

  This is intentionally narrow in scope for safety; there is no "clear all"
  variant in the POC.
  """
  if not application_id:
    raise HTTPException(status_code=400, detail="application_id is required")

  backend = storage.get_storage()
  deleted = backend.delete_by_application(application_id, environment=environment)
  return {"deleted": deleted}


@app.get("/analysis/time-range")
async def analyze_time_range(
  application_id: str = Query(..., description="Application identifier (required)"),
  start_ts: float = Query(..., description="Start of time range (unix timestamp, inclusive)"),
  end_ts: float = Query(..., description="End of time range (unix timestamp, inclusive)"),
  min_level: Optional[str] = Query(
    None,
    description="Optional minimum log level filter (DEBUG, INFO, WARN, ERROR, CRITICAL)",
  ),
  module_name: Optional[str] = Query(None, description="Optional module_name filter"),
  service_name: Optional[str] = Query(None, description="Optional service_name filter"),
  limit: int = Query(100, ge=1, le=1000, description="Max number of records to return"),
) -> Dict[str, object]:
  """
  Time-range analysis endpoint for a single application.

  Retrieves logs for a specific application within a time window, with optional
  filtering by level, module, and service. Returns logs in a structured format
  suitable for analysis.

  This endpoint uses the standard response envelope: {"data": {...}, "meta": {...}}
  """
  # Validate time range
  if start_ts >= end_ts:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail={
        "code": "INVALID_TIME_RANGE",
        "message": "start_ts must be less than end_ts",
      },
    )

  # Validate min_level if provided
  valid_levels = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}
  if min_level and min_level.upper() not in valid_levels:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail={
        "code": "INVALID_LEVEL",
        "message": f"min_level must be one of: {', '.join(sorted(valid_levels))}",
      },
    )

  # Query logs
  records = analysis.analyze_time_range(
    application_id=application_id,
    start_ts=start_ts,
    end_ts=end_ts,
    min_level=min_level.upper() if min_level else None,
    module_name=module_name,
    service_name=service_name,
    limit=limit,
  )

  # Build response using standard envelope format
  logs_data = [r.model_dump() for r in records]

  meta = {
    "application_id": application_id,
    "start_ts": start_ts,
    "end_ts": end_ts,
    "count": len(records),
    "filters": {
      "min_level": min_level,
      "module_name": module_name,
      "service_name": service_name,
    },
  }

  # Add "no data" indicator if empty
  if len(records) == 0:
    meta["no_data"] = True
    meta["message"] = "No logs found for the specified time range and filters"

  return {
    "data": {
      "logs": logs_data,
    },
    "meta": meta,
  }


@app.get("/analysis/why")
async def analyze_why(
  application_id: str = Query(..., description="Application identifier (required)"),
  start_ts: float = Query(..., description="Start of time range (unix timestamp, inclusive)"),
  end_ts: float = Query(..., description="End of time range (unix timestamp, inclusive)"),
  min_level: Optional[str] = Query(
    None,
    description="Optional minimum log level filter (DEBUG, INFO, WARN, ERROR, CRITICAL)",
  ),
  module_name: Optional[str] = Query(None, description="Optional module_name filter"),
  service_name: Optional[str] = Query(None, description="Optional service_name filter"),
  limit: int = Query(100, ge=1, le=1000, description="Max number of records to return"),
) -> Dict[str, object]:
  """
  Root-cause analysis endpoint that generates explanations for errors.

  This endpoint:
  1. Retrieves logs for the specified time range
  2. Prepares analysis input with code snippets
  3. Generates root-cause explanation using AI
  4. Returns structured explanation with evidence references

  Returns a structured response with explanation, evidence, and suggested fixes.
  """
  # Validate time range
  if start_ts >= end_ts:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail={
        "code": "INVALID_TIME_RANGE",
        "message": "start_ts must be less than end_ts",
      },
    )

  # Validate min_level if provided
  valid_levels = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}
  if min_level and min_level.upper() not in valid_levels:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail={
        "code": "INVALID_LEVEL",
        "message": f"min_level must be one of: {', '.join(sorted(valid_levels))}",
      },
    )

  # Query logs
  records = analysis.analyze_time_range(
    application_id=application_id,
    start_ts=start_ts,
    end_ts=end_ts,
    min_level=min_level.upper() if min_level else None,
    module_name=module_name,
    service_name=service_name,
    limit=limit,
  )

  # Check if we have any logs
  if not records:
    return {
      "data": {
        "explanation": None,
        "message": "No logs found for the specified time range and filters",
      },
      "meta": {
        "application_id": application_id,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "count": 0,
        "no_data": True,
      },
    }

  # Prepare analysis input
  input_data = analysis.prepare_ai_analysis_input(records, context_lines=5)

  # Generate root-cause explanation
  explanation = analysis.generate_root_cause_explanation(input_data)

  # Convert to dict for JSON response
  explanation_dict = {
    "summary": explanation.summary,
    "root_cause": explanation.root_cause,
    "error_location": explanation.error_location,
    "key_evidence": explanation.key_evidence,
    "suggested_fixes": [
      {
        "description": fix.description,
        "file_path": fix.file_path,
        "line_no": fix.line_no,
        "line_range": fix.line_range,
        "related_log_ids": fix.related_log_ids,
        "confidence": fix.confidence,
        "rationale": fix.rationale,
      }
      for fix in explanation.suggested_fixes
    ],
    "confidence": explanation.confidence,
    "has_clear_remediation": explanation.has_clear_remediation,
    "evidence_references": [
      {
        "log_id": ref.log_id,
        "reason": ref.reason,
        "file_path": ref.file_path,
        "line_no": ref.line_no,
        "line_range": ref.line_range,
      }
      for ref in explanation.evidence_references
    ],
  }

  return {
    "data": {
      "explanation": explanation_dict,
    },
    "meta": {
      "application_id": application_id,
      "start_ts": start_ts,
      "end_ts": end_ts,
      "count": len(records),
      "filters": {
        "min_level": min_level,
        "module_name": module_name,
        "service_name": service_name,
      },
    },
  }


@app.get("/queries")
async def list_queries() -> Dict[str, object]:
  """
  List all saved analysis queries.

  Returns a list of saved query metadata.
  """
  from . import saved_queries

  queries = saved_queries.list_queries()
  return {
    "data": {
      "queries": [
        {
          "name": q.name,
          "description": q.description,
          "application_id": q.application_id,
          "default_time_window_minutes": q.default_time_window_minutes,
          "min_level": q.min_level,
          "module_names": q.module_names,
          "service_names": q.service_names,
          "limit": q.limit,
          "query_type": q.query_type,
        }
        for q in queries
      ],
    },
    "meta": {"count": len(queries)},
  }


@app.post("/queries")
async def create_query(
  name: str = Query(..., description="Query name (required)"),
  description: Optional[str] = Query(None, description="Query description"),
  application_id: str = Query(..., description="Default application_id (required)"),
  default_time_window_minutes: int = Query(5, ge=1, description="Default time window in minutes"),
  min_level: Optional[str] = Query(None, description="Default minimum log level"),
  module_names: Optional[List[str]] = Query(None, description="Default module names"),
  service_names: Optional[List[str]] = Query(None, description="Default service names"),
  limit: int = Query(100, ge=1, le=1000, description="Default limit"),
  query_type: str = Query("why", description="Query type (why or cross-module)"),
) -> Dict[str, object]:
  """
  Create a new saved analysis query.

  Returns the created query metadata.
  """
  from . import saved_queries

  if query_type not in ("why", "cross-module"):
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail={"code": "INVALID_QUERY_TYPE", "message": "query_type must be 'why' or 'cross-module'"},
    )

  query = saved_queries.SavedQuery(
    name=name,
    description=description,
    application_id=application_id,
    default_time_window_minutes=default_time_window_minutes,
    min_level=min_level,
    module_names=module_names or [],
    service_names=service_names or [],
    limit=limit,
    query_type=query_type,
  )

  saved_queries.save_query(query)

  return {
    "data": {
      "query": {
        "name": query.name,
        "description": query.description,
        "application_id": query.application_id,
        "default_time_window_minutes": query.default_time_window_minutes,
        "min_level": query.min_level,
        "module_names": query.module_names,
        "service_names": query.service_names,
        "limit": query.limit,
        "query_type": query.query_type,
      },
    },
    "meta": {"message": "Query created successfully"},
  }


@app.get("/queries/{query_name}")
async def get_query(query_name: str) -> Dict[str, object]:
  """
  Get a saved query by name.

  Returns the query metadata.
  """
  from . import saved_queries

  query = saved_queries.load_query(query_name)
  if not query:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail={"code": "QUERY_NOT_FOUND", "message": f"Query '{query_name}' not found"},
    )

  return {
    "data": {
      "query": {
        "name": query.name,
        "description": query.description,
        "application_id": query.application_id,
        "default_time_window_minutes": query.default_time_window_minutes,
        "min_level": query.min_level,
        "module_names": query.module_names,
        "service_names": query.service_names,
        "limit": query.limit,
        "query_type": query.query_type,
      },
    },
  }


@app.delete("/queries/{query_name}")
async def delete_query(query_name: str) -> Dict[str, object]:
  """
  Delete a saved query by name.

  Returns success status.
  """
  from . import saved_queries

  if not saved_queries.delete_query(query_name):
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail={"code": "QUERY_NOT_FOUND", "message": f"Query '{query_name}' not found"},
    )

  return {"data": {"message": f"Query '{query_name}' deleted successfully"}}


@app.get("/analysis/query/{query_name}")
async def analyze_with_query(
  query_name: str,
  since: Optional[str] = Query(None, description="Override time window (e.g., '5m', '1h')"),
  start_ts: Optional[float] = Query(None, description="Override start time (Unix timestamp)"),
  end_ts: Optional[float] = Query(None, description="Override end time (Unix timestamp)"),
  application_id: Optional[str] = Query(None, description="Override application_id"),
  min_level: Optional[str] = Query(None, description="Override min_level"),
  module_names: Optional[List[str]] = Query(None, description="Override module names"),
  service_names: Optional[List[str]] = Query(None, description="Override service names"),
  limit: Optional[int] = Query(None, ge=1, le=1000, description="Override limit"),
) -> Dict[str, object]:
  """
  Run analysis using a saved query with optional parameter overrides.

  This endpoint resolves the saved query parameters and applies any overrides,
  then executes the appropriate analysis endpoint.
  """
  from . import saved_queries

  # Parse time window if provided
  start_ts_override = start_ts
  end_ts_override = end_ts
  if since:
    import time

    now = time.time()
    since_lower = since.lower().strip()
    try:
      if since_lower.endswith("s"):
        seconds = int(since_lower[:-1])
      elif since_lower.endswith("m"):
        seconds = int(since_lower[:-1]) * 60
      elif since_lower.endswith("h"):
        seconds = int(since_lower[:-1]) * 3600
      elif since_lower.endswith("d"):
        seconds = int(since_lower[:-1]) * 86400
      else:
        seconds = int(since_lower)
      start_ts_override = now - seconds
      end_ts_override = now
    except ValueError:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "INVALID_TIME_FORMAT", "message": f"Invalid time format: {since}. Use format like '5m', '1h', '30s'"},
      )

  # Resolve query parameters
  try:
    params = saved_queries.resolve_query_params(
      query_name=query_name,
      start_ts=start_ts_override,
      end_ts=end_ts_override,
      application_id=application_id,
      min_level=min_level,
      module_names=module_names,
      service_names=service_names,
      limit=limit,
    )
  except ValueError as e:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail={"code": "QUERY_NOT_FOUND", "message": str(e)},
    )

  # Determine which endpoint to call
  query_type = params.pop("query_type", "why")

  if query_type == "cross-module":
    # Call cross-module analysis
    result = analysis.analyze_cross_module_incident(
      application_id=params["application_id"],
      start_ts=params["start_ts"],
      end_ts=params["end_ts"],
      min_level=params.get("min_level"),
      module_names=params.get("module_names"),
      service_names=params.get("service_names"),
      limit=params["limit"],
    )

    explanation_dict = {
      "summary": result.explanation.summary,
      "root_cause": result.explanation.root_cause,
      "error_location": result.explanation.error_location,
      "key_evidence": result.explanation.key_evidence,
      "suggested_fixes": [
        {
          "description": fix.description,
          "file_path": fix.file_path,
          "line_no": fix.line_no,
          "line_range": fix.line_range,
          "related_log_ids": fix.related_log_ids,
          "confidence": fix.confidence,
          "rationale": fix.rationale,
        }
        for fix in result.explanation.suggested_fixes
      ],
      "confidence": result.explanation.confidence,
      "has_clear_remediation": result.explanation.has_clear_remediation,
      "evidence_references": [
        {
          "log_id": ref.log_id,
          "reason": ref.reason,
          "file_path": ref.file_path,
          "line_no": ref.line_no,
          "line_range": ref.line_range,
        }
        for ref in result.explanation.evidence_references
      ],
    }

    return {
      "data": {
        "explanation": explanation_dict,
        "components": result.components,
        "logs_by_component": result.logs_by_component,
      },
      "meta": {
        "query_name": query_name,
        "application_id": params["application_id"],
        "start_ts": params["start_ts"],
        "end_ts": params["end_ts"],
        "components": result.components,
      },
    }
  else:
    # Call why analysis
    # analyze_time_range accepts single values or lists, so pass lists directly
    module_name = params.get("module_names") if params.get("module_names") else None
    service_name = params.get("service_names") if params.get("service_names") else None
    records = analysis.analyze_time_range(
      application_id=params["application_id"],
      start_ts=params["start_ts"],
      end_ts=params["end_ts"],
      min_level=params.get("min_level"),
      module_name=module_name,
      service_name=service_name,
      limit=params["limit"],
    )

    if not records:
      return {
        "data": {
          "explanation": None,
          "message": "No logs found for the specified time range and filters",
        },
        "meta": {
          "query_name": query_name,
          "application_id": params["application_id"],
          "start_ts": params["start_ts"],
          "end_ts": params["end_ts"],
          "count": 0,
          "no_data": True,
        },
      }

    input_data = analysis.prepare_ai_analysis_input(records, context_lines=5)
    explanation = analysis.generate_root_cause_explanation(input_data)

    explanation_dict = {
      "summary": explanation.summary,
      "root_cause": explanation.root_cause,
      "error_location": explanation.error_location,
      "key_evidence": explanation.key_evidence,
      "suggested_fixes": [
        {
          "description": fix.description,
          "file_path": fix.file_path,
          "line_no": fix.line_no,
          "line_range": fix.line_range,
          "related_log_ids": fix.related_log_ids,
          "confidence": fix.confidence,
          "rationale": fix.rationale,
        }
        for fix in explanation.suggested_fixes
      ],
      "confidence": explanation.confidence,
      "has_clear_remediation": explanation.has_clear_remediation,
      "evidence_references": [
        {
          "log_id": ref.log_id,
          "reason": ref.reason,
          "file_path": ref.file_path,
          "line_no": ref.line_no,
          "line_range": ref.line_range,
        }
        for ref in explanation.evidence_references
      ],
    }

    return {
      "data": {
        "explanation": explanation_dict,
      },
      "meta": {
        "query_name": query_name,
        "application_id": params["application_id"],
        "start_ts": params["start_ts"],
        "end_ts": params["end_ts"],
        "count": len(records),
      },
    }


@app.get("/analysis/cross-module")
async def analyze_cross_module(
  application_id: str = Query(..., description="Application identifier (required)"),
  start_ts: float = Query(..., description="Start of time range (unix timestamp, inclusive)"),
  end_ts: float = Query(..., description="End of time range (unix timestamp, inclusive)"),
  min_level: Optional[str] = Query(
    None,
    description="Optional minimum log level filter (DEBUG, INFO, WARN, ERROR, CRITICAL)",
  ),
  module_names: Optional[List[str]] = Query(None, description="Optional list of module names to include"),
  service_names: Optional[List[str]] = Query(None, description="Optional list of service names to include"),
  limit: int = Query(100, ge=1, le=1000, description="Max number of records to return"),
) -> Dict[str, object]:
  """
  Cross-module/service analysis endpoint for incidents spanning multiple components.

  This endpoint retrieves logs from multiple services/modules, generates root-cause
  explanations, and returns component-level context showing which components
  contributed to the incident.

  This endpoint uses the standard response envelope: {"data": {...}, "meta": {...}}
  """
  # Validate time range
  if start_ts >= end_ts:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail={
        "code": "INVALID_TIME_RANGE",
        "message": "start_ts must be less than end_ts",
      },
    )

  # Validate min_level if provided
  valid_levels = {"DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"}
  if min_level and min_level.upper() not in valid_levels:
    raise HTTPException(
      status_code=status.HTTP_400_BAD_REQUEST,
      detail={
        "code": "INVALID_LEVEL",
        "message": f"min_level must be one of: {', '.join(sorted(valid_levels))}",
      },
    )

  # Perform cross-module analysis
  result = analysis.analyze_cross_module_incident(
    application_id=application_id,
    start_ts=start_ts,
    end_ts=end_ts,
    min_level=min_level.upper() if min_level else None,
    module_names=module_names,
    service_names=service_names,
    limit=limit,
  )

  # Convert explanation to dict
  explanation_dict = {
    "summary": result.explanation.summary,
    "root_cause": result.explanation.root_cause,
    "error_location": result.explanation.error_location,
    "key_evidence": result.explanation.key_evidence,
    "suggested_fixes": [
      {
        "description": fix.description,
        "file_path": fix.file_path,
        "line_no": fix.line_no,
        "line_range": fix.line_range,
        "related_log_ids": fix.related_log_ids,
        "confidence": fix.confidence,
        "rationale": fix.rationale,
      }
      for fix in result.explanation.suggested_fixes
    ],
    "confidence": result.explanation.confidence,
    "has_clear_remediation": result.explanation.has_clear_remediation,
    "evidence_references": [
      {
        "log_id": ref.log_id,
        "reason": ref.reason,
        "file_path": ref.file_path,
        "line_no": ref.line_no,
        "line_range": ref.line_range,
      }
      for ref in result.explanation.evidence_references
    ],
  }

  meta = {
    "application_id": application_id,
    "start_ts": start_ts,
    "end_ts": end_ts,
    "filters": {
      "min_level": min_level,
      "module_names": module_names,
      "service_names": service_names,
    },
    "components": result.components,
  }

  return {
    "data": {
      "explanation": explanation_dict,
      "components": result.components,
      "logs_by_component": result.logs_by_component,
    },
    "meta": meta,
  }


@app.post("/help/guide/start")
async def start_guide(request: StartGuideRequest) -> Dict[str, object]:
    """
    Start step-by-step setup guide for a given language.

    Returns markdown-formatted setup guide content (first step).
    """
    try:
        content = await help_agent_interface.start_setup_guide(
            request.language,
            Path(request.project_root)
        )
        return {
            "data": {"content": content},
            "meta": {"language": request.language, "project_root": request.project_root}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "GUIDE_START_FAILED", "message": str(e)}
        )


@app.get("/help/guide/current")
async def get_current_guide(project_root: str = Query(..., description="Project root directory path")) -> Dict[str, object]:
    """
    Get current step information for the active language.

    Returns markdown-formatted current step information.
    """
    try:
        content = await help_agent_interface.get_current_step(Path(project_root))
        return {
            "data": {"content": content},
            "meta": {"project_root": project_root}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "GUIDE_CURRENT_FAILED", "message": str(e)}
        )


@app.post("/help/guide/complete")
async def complete_guide_step(request: CompleteStepRequest) -> Dict[str, object]:
    """
    Mark a step as complete and return next step (if any).

    Returns markdown-formatted completion message and next step.
    """
    try:
        content = await help_agent_interface.complete_step(
            request.step_number,
            Path(request.project_root)
        )
        return {
            "data": {"content": content},
            "meta": {"step_number": request.step_number, "project_root": request.project_root}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "GUIDE_COMPLETE_FAILED", "message": str(e)}
        )


@app.post("/help/troubleshoot")
async def troubleshoot_issue(request: TroubleshootRequest) -> Dict[str, object]:
    """
    Provide troubleshooting guidance for a common issue.

    Returns markdown-formatted troubleshooting guidance.
    """
    try:
        content = await help_agent_interface.troubleshoot(
            request.issue,
            Path(request.project_root)
        )
        return {
            "data": {"content": content},
            "meta": {"issue": request.issue, "project_root": request.project_root}
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "TROUBLESHOOT_FAILED", "message": str(e)}
        )


