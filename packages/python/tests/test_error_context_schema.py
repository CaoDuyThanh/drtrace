from fastapi.testclient import TestClient

from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]


class DummyStorage(storage_mod.LogStorage):  # type: ignore[misc]
  def write_batch(self, batch):  # pragma: no cover - no-op
    pass


def test_ingest_accepts_enriched_error_context(monkeypatch):
  client = TestClient(app)
  monkeypatch.setattr(storage_mod, "get_storage", lambda: DummyStorage())

  payload = {
    "application_id": "app-123",
    "logs": [
      {
        "ts": 1734550000.0,
        "level": "ERROR",
        "message": "boom",
        "application_id": "app-123",
        "service_name": "svc-xyz",
        "module_name": "my_module",
        "file_path": "/app/main.py",
        "line_no": 42,
        "exception_type": "ZeroDivisionError",
        "stacktrace": "Traceback (most recent call last): ...",
        "context": {"request_id": "abc"},
      }
    ],
  }

  resp = client.post("/logs/ingest", json=payload)
  assert resp.status_code == 202
  assert resp.json() == {"accepted": 1}


def test_ingest_allows_message_only_errors_without_enriched_fields(monkeypatch):
  client = TestClient(app)
  monkeypatch.setattr(storage_mod, "get_storage", lambda: DummyStorage())

  payload = {
    "application_id": "app-123",
    "logs": [
      {
        "ts": 1734550001.0,
        "level": "ERROR",
        "message": "message only error",
        "application_id": "app-123",
        "module_name": "my_module",
      }
    ],
  }

  resp = client.post("/logs/ingest", json=payload)
  assert resp.status_code == 202
  assert resp.json() == {"accepted": 1}


