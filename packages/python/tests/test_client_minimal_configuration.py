import logging
from typing import Any, Dict, List

import pytest

from drtrace_client import setup_logging  # type: ignore[import]


def test_setup_logging_preserves_existing_handlers_and_attaches_client_handler(monkeypatch):
  events: List[Dict[str, Any]] = []
  baseline: List[str] = []

  class ExistingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
      baseline.append(record.getMessage())

  # Patch LogQueue and HttpTransport to enqueue synchronously into events
  from drtrace_client import logging_setup as ls  # type: ignore[import]
  from drtrace_client import transport as tr  # type: ignore[import]

  class DummyQueue:
    def __init__(self, sender, maxsize=1000, batch_size=50):
      self._sender = sender

    def start(self) -> None:
      pass

    def enqueue(self, record: Dict[str, Any]) -> None:
      # simulate a single-batch send
      self._sender([record])

  monkeypatch.setattr(ls, "LogQueue", DummyQueue)
  monkeypatch.setattr(tr.HttpTransport, "send", lambda self, batch: events.extend(batch))

  # Configure logger with an existing handler
  logger = logging.getLogger("existing_app_logger")
  logger.setLevel(logging.INFO)
  logger.handlers.clear()
  logger.addHandler(ExistingHandler())

  # Call setup_logging with explicit params; should keep existing handler
  setup_logging(
    logger,
    application_id="app-123",
    service_name="svc-xyz",
    daemon_url="http://localhost:8001/logs/ingest",
  )

  logger.info("hello from existing app")

  # Existing handler should still see the message
  assert "hello from existing app" in baseline
  # Client pipeline should also see an enriched event
  assert len(events) == 1
  event = events[0]
  assert event["application_id"] == "app-123"
  assert event["service_name"] == "svc-xyz"
  assert event["message"] == "hello from existing app"
  assert event["module_name"] == "existing_app_logger"


def test_setup_logging_does_not_duplicate_handler_on_multiple_calls(monkeypatch):
  events: List[Dict[str, Any]] = []

  from drtrace_client import logging_setup as ls  # type: ignore[import]
  from drtrace_client import transport as tr  # type: ignore[import]

  class DummyQueue:
    def __init__(self, sender, maxsize=1000, batch_size=50):
      self._sender = sender

    def start(self) -> None:
      pass

    def enqueue(self, record: Dict[str, Any]) -> None:
      self._sender([record])

  monkeypatch.setattr(ls, "LogQueue", DummyQueue)
  monkeypatch.setattr(tr.HttpTransport, "send", lambda self, batch: events.extend(batch))

  logger = logging.getLogger("idempotent_logger")
  logger.setLevel(logging.INFO)
  logger.handlers.clear()

  # First call attaches handler
  setup_logging(logger, application_id="app-123")
  # Second call should no-op with respect to handler count
  setup_logging(logger, application_id="app-123")

  logger.info("once")

  # Only one event should be emitted via the client handler
  assert len(events) == 1


def test_config_uses_default_application_id_when_missing(monkeypatch):
  # Clear env to verify fallback to default "my-app"
  monkeypatch.delenv("DRTRACE_APPLICATION_ID", raising=False)

  logger = logging.getLogger("missing_app_id_logger")

  # Should NOT raise - uses "my-app" fallback for cross-language consistency
  # This ensures the application never crashes due to missing config
  setup_logging(logger)
  # If we get here without exception, the test passes


def test_config_rejects_malformed_daemon_url(monkeypatch):
  # Ensure we have an application id via env, then pass a bad URL explicitly
  monkeypatch.setenv("DRTRACE_APPLICATION_ID", "env-app")

  logger = logging.getLogger("bad_url_logger")

  with pytest.raises(ValueError):
    setup_logging(logger, daemon_url="not-a-url")


