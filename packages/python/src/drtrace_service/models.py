from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LogRecord(BaseModel):
  """
  Canonical log event shape received by the daemon.
  """

  ts: float = Field(..., description="Unix timestamp when the log was created")
  level: str
  message: str
  application_id: str
  service_name: Optional[str] = None
  module_name: str

  # Enriched error context (Story 2.2). All are optional and only populated
  # for error-level events when the client has that information.
  file_path: Optional[str] = None
  line_no: Optional[int] = None
  exception_type: Optional[str] = None
  stacktrace: Optional[str] = None

  context: Dict[str, Any] = Field(default_factory=dict)


class LogBatch(BaseModel):
  """
  Envelope used by the client to send batched logs.
  """

  application_id: str
  logs: List[LogRecord]


