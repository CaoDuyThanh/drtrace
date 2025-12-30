from __future__ import annotations

import logging
import traceback
from logging import Handler, LogRecord
from typing import Any, Dict, Optional

from .config import ClientConfig
from .queue import LogQueue
from .transport import HttpTransport


class _DrtraceHandler(Handler):
  """
  Logging handler that enriches records and enqueues them for delivery.
  """

  def __init__(self, config: ClientConfig, queue: LogQueue) -> None:
    super().__init__()
    self._config = config
    self._queue = queue

  def emit(self, record: LogRecord) -> None:
    try:
      if not self._config.enabled:
        return

      payload: Dict[str, Any] = {
        "ts": getattr(record, "created", None),
        "level": record.levelname,
        "message": record.getMessage(),
        "application_id": self._config.application_id,
        "service_name": self._config.service_name,
        "module_name": record.name,
      }

      # Enriched error context for exception-logging cases (Story 2.2).
      if record.exc_info:
        _type, _value, _tb = record.exc_info
        if _type is not None:
          payload["exception_type"] = _type.__name__
        if _tb is not None:
          payload["stacktrace"] = "".join(traceback.format_exception(_type, _value, _tb))

      # Basic file/line information when available.
      if getattr(record, "pathname", None):
        payload["file_path"] = record.pathname  # type: ignore[attr-defined]
      if getattr(record, "lineno", None) is not None:
        payload["line_no"] = record.lineno  # type: ignore[attr-defined]

      self._queue.enqueue(payload)
    except Exception:
      # Never break application logging.
      self.handleError(record)


def setup_logging(
  logger: Optional[logging.Logger] = None,
  *,
  application_id: Optional[str] = None,
  service_name: Optional[str] = None,
  daemon_url: Optional[str] = None,
) -> None:
  """
  Attach the drtrace client handler to the standard logging module.

  This does not replace existing handlers; it adds an additional handler
  that ships enriched records to the local daemon via a background queue.
  """
  config = ClientConfig.from_params_or_env(
    application_id=application_id,
    daemon_url=daemon_url,
    service_name=service_name,
  )
  if not config.enabled:
    # Analysis is disabled; preserve existing logging behavior only.
    return

  transport = HttpTransport(
    endpoint=config.daemon_url,
    application_id=config.application_id,
  )
  log_queue = LogQueue(sender=transport.send)
  log_queue.start()

  target_logger = logger or logging.getLogger()

  # Avoid attaching duplicate client handlers to the same logger.
  for existing in target_logger.handlers:
    if isinstance(existing, _DrtraceHandler):
      return

  handler = _DrtraceHandler(config=config, queue=log_queue)
  target_logger.addHandler(handler)


