
from fastapi.testclient import TestClient

from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]


class DummyStorage(storage_mod.LogStorage):  # type: ignore[misc]
  def write_batch(self, batch):  # pragma: no cover - no-op
    pass


def test_ingest_logs_accepts_valid_batch(monkeypatch):
  client = TestClient(app)
  monkeypatch.setattr(storage_mod, "get_storage", lambda: DummyStorage())

  payload = {
    "application_id": "app-123",
    "logs": [
      {
        "ts": 1734550000.0,
        "level": "INFO",
        "message": "hello",
        "application_id": "app-123",
        "service_name": "svc-xyz",
        "module_name": "my_module",
        "context": {"request_id": "abc"},
      }
    ],
  }

  resp = client.post("/logs/ingest", json=payload)
  assert resp.status_code == 202
  assert resp.json() == {"accepted": 1}


def test_ingest_logs_rejects_invalid_payload_missing_required_field(monkeypatch):
  client = TestClient(app)
  monkeypatch.setattr(storage_mod, "get_storage", lambda: DummyStorage())

  # Missing 'level' in inner log record
  bad_payload = {
    "application_id": "app-123",
    "logs": [
      {
        "ts": 1734550000.0,
        "message": "hello",
        "application_id": "app-123",
        "service_name": "svc-xyz",
        "module_name": "my_module",
      }
    ],
  }

  resp = client.post("/logs/ingest", json=bad_payload)
  # FastAPI/pydantic will raise a 422 validation error
  assert resp.status_code == 422


