import logging
from typing import Any, Dict, List

from drtrace_client import ClientConfig, setup_logging  # type: ignore[import]


def test_client_config_from_env_fallback_to_default(monkeypatch):
  """Test that ClientConfig.from_env() falls back to 'my-app' when application_id is missing."""
  monkeypatch.delenv("DRTRACE_APPLICATION_ID", raising=False)

  # Should not raise ValueError, should use default "my-app"
  config = ClientConfig.from_env()
  assert config.application_id == "my-app"


def test_setup_logging_attaches_handler_and_enqueues_records(monkeypatch):
  events: List[Dict[str, Any]] = []

  class DummySender:
    def __call__(self, batch):
      events.extend(batch)

  # Force deterministic config
  monkeypatch.setenv("DRTRACE_APPLICATION_ID", "test-app")
  monkeypatch.setenv("DRTRACE_DAEMON_URL", "http://localhost:9/nowhere")

  # Patch LogQueue to use our DummySender synchronously
  from drtrace_client import logging_setup as ls  # type: ignore[import]

  class DummyQueue:
    def __init__(self, sender, maxsize=1000, batch_size=50):
      self._sender = DummySender()

    def start(self):
      pass

    def enqueue(self, record):
      self._sender([record])

  monkeypatch.setattr(ls, "LogQueue", DummyQueue)

  logger = logging.getLogger("test-logger")
  logger.setLevel(logging.INFO)
  setup_logging(logger)

  logger.info("hello world")

  assert len(events) == 1
  event = events[0]
  assert event["application_id"] == "test-app"
  assert event["message"] == "hello world"
  assert event["module_name"] == "test-logger"


def test_exception_logging_includes_error_context(monkeypatch):
  events: List[Dict[str, Any]] = []

  class DummySender:
    def __call__(self, batch):
      events.extend(batch)

  monkeypatch.setenv("DRTRACE_APPLICATION_ID", "test-app")
  monkeypatch.setenv("DRTRACE_DAEMON_URL", "http://localhost:9/nowhere")

  from drtrace_client import logging_setup as ls  # type: ignore[import]

  class DummyQueue:
    def __init__(self, sender, maxsize=1000, batch_size=50):
      self._sender = DummySender()

    def start(self):
      pass

    def enqueue(self, record):
      self._sender([record])

  monkeypatch.setattr(ls, "LogQueue", DummyQueue)

  logger = logging.getLogger("error-logger")
  logger.setLevel(logging.INFO)

  setup_logging(logger)

  try:
    1 / 0
  except ZeroDivisionError:
    logger.exception("boom")

  assert len(events) == 1
  event = events[0]
  assert event["application_id"] == "test-app"
  assert event["message"] == "boom"
  assert event["module_name"] == "error-logger"
  # Error context fields should be present
  assert event.get("exception_type") == "ZeroDivisionError"
  assert "stacktrace" in event and "ZeroDivisionError" in event["stacktrace"]
  assert "file_path" in event
  assert "line_no" in event


def test_service_name_is_propagated_from_config(monkeypatch):
  events: List[Dict[str, Any]] = []

  class DummySender:
    def __call__(self, batch):
      events.extend(batch)

  monkeypatch.setenv("DRTRACE_APPLICATION_ID", "app-with-service")
  monkeypatch.setenv("DRTRACE_SERVICE_NAME", "orders-service")
  monkeypatch.setenv("DRTRACE_DAEMON_URL", "http://localhost:9/nowhere")

  from drtrace_client import logging_setup as ls  # type: ignore[import]

  class DummyQueue:
    def __init__(self, sender, maxsize=1000, batch_size=50):
      self._sender = DummySender()

    def start(self):
      pass

    def enqueue(self, record):
      self._sender([record])

  monkeypatch.setattr(ls, "LogQueue", DummyQueue)

  logger = logging.getLogger("svc-logger")
  logger.setLevel(logging.INFO)

  setup_logging(logger)
  logger.info("svc hello")

  assert len(events) == 1
  event = events[0]
  assert event["application_id"] == "app-with-service"
  assert event["service_name"] == "orders-service"
  assert event["module_name"] == "svc-logger"

