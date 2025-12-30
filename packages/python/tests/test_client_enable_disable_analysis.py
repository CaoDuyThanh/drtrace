import logging
from typing import Any, Dict, List

from drtrace_client import setup_logging  # type: ignore[import]


def _patch_client_pipeline(monkeypatch, events: List[Dict[str, Any]]) -> None:
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


def test_analysis_disabled_via_env(monkeypatch):
  events: List[Dict[str, Any]] = []
  baseline: List[str] = []

  _patch_client_pipeline(monkeypatch, events)

  class ExistingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:  # type: ignore[override]
      baseline.append(record.getMessage())

  # Disable analysis
  monkeypatch.setenv("DRTRACE_APPLICATION_ID", "env-app")
  monkeypatch.setenv("DRTRACE_ENABLED", "false")

  logger = logging.getLogger("env_toggle_logger")
  logger.setLevel(logging.INFO)
  logger.handlers.clear()
  logger.addHandler(ExistingHandler())

  setup_logging(logger)

  logger.info("hello with analysis disabled")

  # Existing handler still sees the log
  assert "hello with analysis disabled" in baseline
  # No events should be queued/sent when disabled
  assert events == []


def test_analysis_enabled_via_env(monkeypatch):
  events: List[Dict[str, Any]] = []

  _patch_client_pipeline(monkeypatch, events)

  monkeypatch.setenv("DRTRACE_APPLICATION_ID", "env-app")
  monkeypatch.setenv("DRTRACE_ENABLED", "true")

  logger = logging.getLogger("env_enabled_logger")
  logger.setLevel(logging.INFO)
  logger.handlers.clear()

  setup_logging(logger)

  logger.info("hello with analysis enabled")

  assert len(events) == 1
  event = events[0]
  assert event["application_id"] == "env-app"
  assert event["message"] == "hello with analysis enabled"


