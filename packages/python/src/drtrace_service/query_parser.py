"""
Natural language query parser for log analysis agent.

This module parses natural language queries into structured API parameters.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple


@dataclass
class ParseResult:
    """Structured result from parsing a natural language query."""

    intent: str  # "explain", "query", "show", "why"
    start_ts: Optional[float] = None  # Unix timestamp
    end_ts: Optional[float] = None  # Unix timestamp
    application_id: Optional[str] = None
    service_name: Optional[str] = None
    module_name: Optional[str] = None
    min_level: Optional[str] = None
    missing_info: List[str] = None  # type: ignore[assignment]
    suggestions: Dict[str, List[str]] = None  # type: ignore[assignment]

    def __post_init__(self):
        """Ensure list/dict fields default to empty."""
        if self.missing_info is None:
            object.__setattr__(self, "missing_info", [])
        if self.suggestions is None:
            object.__setattr__(self, "suggestions", {})


def parse_time_range(query: str, context: Optional[Dict[str, any]] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Parse time range from natural language query.

    Supports:
    - Absolute: "from 9:00 to 10:00", "between 2:30 PM and 2:35 PM"
    - Relative: "last 5 minutes", "10 minutes ago", "past hour"
    - With dates: "on 2025-01-27 from 10:00 to 11:00"

    Args:
        query: Natural language query string
        context: Optional context dict (e.g., current date)

    Returns:
        Tuple of (start_ts, end_ts) as Unix timestamps, or (None, None) if not found
    """
    query_lower = query.lower()
    now = time.time()
    today = datetime.fromtimestamp(now).date()

    # Relative time patterns
    relative_patterns = [
        (r"last\s+(\d+)\s+minutes?", lambda m: (now - int(m.group(1)) * 60, now)),
        (r"(\d+)\s+minutes?\s+ago", lambda m: (now - int(m.group(1)) * 60, now)),
        (r"past\s+(\d+)\s+hours?", lambda m: (now - int(m.group(1)) * 3600, now)),
        (r"last\s+(\d+)\s+hours?", lambda m: (now - int(m.group(1)) * 3600, now)),
        (r"past\s+hour", lambda: (now - 3600, now)),
        (r"last\s+hour", lambda: (now - 3600, now)),
        (r"past\s+(\d+)\s+days?", lambda m: (now - int(m.group(1)) * 86400, now)),
        (r"last\s+(\d+)\s+days?", lambda m: (now - int(m.group(1)) * 86400, now)),
    ]

    for pattern, func in relative_patterns:
        match = re.search(pattern, query_lower)
        if match:
            if match.groups():
                start_ts, end_ts = func(match)
            else:
                start_ts, end_ts = func()
            return (start_ts, end_ts)

    # Date + time pattern: "on 2025-01-27 from 10:00 to 11:00" (check first, more specific)
    date_time_pattern = r"on\s+(\d{4}-\d{2}-\d{2})\s+from\s+(\d{1,2}):(\d{2})\s*(am|pm)?\s+to\s+(\d{1,2}):(\d{2})\s*(am|pm)?"
    match = re.search(date_time_pattern, query_lower)
    if match:
        date_str, start_hour, start_min, start_ampm, end_hour, end_min, end_ampm = match.groups()
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            start_ts = _parse_time_to_timestamp(int(start_hour), int(start_min), start_ampm, date_obj)
            end_ts = _parse_time_to_timestamp(int(end_hour), int(end_min), end_ampm, date_obj)
            if start_ts and end_ts:
                return (start_ts, end_ts)
        except ValueError:
            pass

    # Absolute time patterns: "from 9:00 to 10:00"
    from_to_pattern = r"from\s+(\d{1,2}):(\d{2})\s*(am|pm)?\s+to\s+(\d{1,2}):(\d{2})\s*(am|pm)?"
    match = re.search(from_to_pattern, query_lower)
    if match:
        start_hour, start_min, start_ampm, end_hour, end_min, end_ampm = match.groups()
        start_ts = _parse_time_to_timestamp(int(start_hour), int(start_min), start_ampm, today)
        end_ts = _parse_time_to_timestamp(int(end_hour), int(end_min), end_ampm, today)
        if start_ts and end_ts:
            return (start_ts, end_ts)

    # Absolute time patterns: "between 2:30 PM and 2:35 PM"
    between_pattern = r"between\s+(\d{1,2}):(\d{2})\s*(am|pm)?\s+and\s+(\d{1,2}):(\d{2})\s*(am|pm)?"
    match = re.search(between_pattern, query_lower)
    if match:
        start_hour, start_min, start_ampm, end_hour, end_min, end_ampm = match.groups()
        start_ts = _parse_time_to_timestamp(int(start_hour), int(start_min), start_ampm, today)
        end_ts = _parse_time_to_timestamp(int(end_hour), int(end_min), end_ampm, today)
        if start_ts and end_ts:
            return (start_ts, end_ts)

    return (None, None)


def _parse_time_to_timestamp(hour: int, minute: int, ampm: Optional[str], date: any) -> Optional[float]:
    """Convert hour, minute, ampm, and date to Unix timestamp."""
    # Handle 12-hour format
    if ampm:
        if ampm.lower() == "pm" and hour != 12:
            hour += 12
        elif ampm.lower() == "am" and hour == 12:
            hour = 0
    # Handle 24-hour format (if hour > 12 and no ampm, assume 24-hour)
    elif hour > 12:
        pass  # Already 24-hour format
    else:
        # Ambiguous - assume 24-hour if hour is reasonable
        pass

    try:
        dt = datetime.combine(date, datetime.min.time().replace(hour=hour, minute=minute))
        return dt.timestamp()
    except (ValueError, OverflowError):
        return None


def extract_filters(query: str, context: Optional[Dict[str, any]] = None) -> Dict[str, Optional[str]]:
    """
    Extract filters from natural language query.

    Extracts:
    - application_id: "for app myapp", "application myapp"
    - service_name: "from service auth", "service auth"
    - module_name: "module data_processor", "from module data_processor"
    - min_level: "errors", "warnings", "ERROR level", "min level ERROR"

    Args:
        query: Natural language query string
        context: Optional context dict (e.g., default application_id)

    Returns:
        Dict with application_id, service_name, module_name, min_level
    """
    query_lower = query.lower()
    filters: Dict[str, Optional[str]] = {
        "application_id": None,
        "service_name": None,
        "module_name": None,
        "min_level": None,
    }

    # Application ID patterns
    app_patterns = [
        r"for\s+app\s+(\w+)",
        r"application\s+(\w+)",
        r"app\s+(\w+)",
    ]
    for pattern in app_patterns:
        match = re.search(pattern, query_lower)
        if match:
            filters["application_id"] = match.group(1)
            break

    # Service name patterns
    service_patterns = [
        r"from\s+service\s+(\w+)",
        r"service\s+(\w+)",
    ]
    for pattern in service_patterns:
        match = re.search(pattern, query_lower)
        if match:
            filters["service_name"] = match.group(1)
            break

    # Module name patterns
    module_patterns = [
        r"from\s+module\s+(\w+)",
        r"module\s+(\w+)",
    ]
    for pattern in module_patterns:
        match = re.search(pattern, query_lower)
        if match:
            filters["module_name"] = match.group(1)
            break

    # Log level patterns (check more specific patterns first)
    level_patterns = [
        (r"errors?\s+only", "ERROR"),
        (r"show\s+errors?", "ERROR"),  # "show errors" implies ERROR level
        (r"error\s+level", "ERROR"),
        (r"min\s+level\s+error", "ERROR"),
        (r"warnings?\s+(?:and\s+above|only)", "WARN"),
        (r"show\s+warnings?", "WARN"),
        (r"warning\s+level", "WARN"),
        (r"min\s+level\s+warn", "WARN"),
        (r"info\s+level", "INFO"),
        (r"debug\s+level", "DEBUG"),
        (r"critical\s+level", "CRITICAL"),
    ]
    for pattern, level in level_patterns:
        if re.search(pattern, query_lower):
            filters["min_level"] = level
            break

    # If context provides defaults, use them
    if context:
        for key in filters:
            if filters[key] is None and key in context:
                filters[key] = context.get(key)

    return filters


def detect_intent(query: str) -> str:
    """
    Detect query intent from natural language.

    Returns:
        Intent string: "explain", "query", "show", "why"
    """
    query_lower = query.lower()

    # Intent patterns (ordered by specificity - check "show" before "error")
    intent_patterns = [
        (r"why\s+did\s+.*\s+error", "why"),
        (r"explain\s+.*\s+error", "explain"),
        (r"explain\s+why", "explain"),
        (r"what\s+happened", "explain"),
        (r"show\s+logs", "show"),
        (r"show\s+errors?", "show"),  # "show errors" should be "show", not "explain"
        (r"show\s+warnings?", "show"),
        (r"query\s+logs", "query"),
        (r"get\s+logs", "query"),
    ]

    for pattern, intent in intent_patterns:
        if re.search(pattern, query_lower):
            return intent

    # Default: if query mentions "error" (and not "show errors"), assume explain intent
    if "error" in query_lower and "show" not in query_lower:
        return "explain"

    # Default: query intent
    return "query"


def parse_query(query: str, context: Optional[Dict[str, any]] = None) -> ParseResult:
    """
    Main entry point: parse full query and return structured result.

    Args:
        query: Natural language query string
        context: Optional context dict (e.g., default application_id, available applications)

    Returns:
        ParseResult with all extracted information
    """
    # Detect intent
    intent = detect_intent(query)

    # Parse time range
    start_ts, end_ts = parse_time_range(query, context)

    # Extract filters
    filters = extract_filters(query, context)

    # Check for missing required information
    missing_info: List[str] = []
    suggestions: Dict[str, List[str]] = {}

    # application_id is required for most queries
    if not filters.get("application_id"):
        missing_info.append("application_id")
        if context and "available_applications" in context:
            suggestions["application_id"] = context["available_applications"]

    # Time range is usually required
    if not start_ts or not end_ts:
        missing_info.append("time_range")

    return ParseResult(
        intent=intent,
        start_ts=start_ts,
        end_ts=end_ts,
        application_id=filters.get("application_id"),
        service_name=filters.get("service_name"),
        module_name=filters.get("module_name"),
        min_level=filters.get("min_level"),
        missing_info=missing_info,
        suggestions=suggestions,
    )

