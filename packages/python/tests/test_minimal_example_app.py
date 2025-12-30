import pathlib
import sys


def test_minimal_example_app_runs_without_unhandled_errors(monkeypatch):
  """
  Exercise the minimal example app to align with Story 1.1 ACs:
  - app can import and configure the client
  - INFO/ERROR logs are emitted without breaking existing logging
  """
  # Ensure application id is present
  monkeypatch.setenv("DRTRACE_APPLICATION_ID", "example-app")

  # Patch LogQueue to avoid spawning threads and real network I/O
  import drtrace_client.logging_setup as ls  # type: ignore[import]

  events = []

  class DummyQueue:
    def __init__(self, sender, maxsize=1000, batch_size=50):
      self._sender = sender

    def start(self):
      pass

    def enqueue(self, record):
      events.append(record)

  monkeypatch.setattr(ls, "LogQueue", DummyQueue)

  examples_root = None
  for p in pathlib.Path(__file__).resolve().parents:
    if (p / "examples").is_dir():
      examples_root = p
      break
  if examples_root and str(examples_root) not in sys.path:
    sys.path.insert(0, str(examples_root))

  # Import and run the example app
  import examples.minimal_python_app as app  # type: ignore[import]

  # Exercise main; should not raise
  app.main()

  # We expect at least one event to have been queued by the handler
  assert len(events) >= 1


