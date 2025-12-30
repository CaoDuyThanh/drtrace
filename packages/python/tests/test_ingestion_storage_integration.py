from typing import List

from fastapi.testclient import TestClient

from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]
from drtrace_service.models import LogBatch  # type: ignore[import]


class DummyStorage(storage_mod.LogStorage):  # type: ignore[misc]
  def __init__(self) -> None:
    self.batches: List[LogBatch] = []

  def write_batch(self, batch: LogBatch) -> None:  # pragma: no cover - trivial
    self.batches.append(batch)


def test_ingest_logs_delegates_to_storage(monkeypatch):
  client = TestClient(app)
  dummy = DummyStorage()

  def fake_get_storage():
    return dummy

  monkeypatch.setattr(storage_mod, "get_storage", fake_get_storage)

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

  assert len(dummy.batches) == 1
  batch = dummy.batches[0]
  assert batch.application_id == "app-123"
  assert len(batch.logs) == 1
  assert batch.logs[0].message == "hello"


