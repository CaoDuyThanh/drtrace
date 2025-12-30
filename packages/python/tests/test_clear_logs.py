from typing import Any, List, Optional, Tuple

from fastapi.testclient import TestClient

from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]


class DummyClearStorage(storage_mod.LogStorage):  # type: ignore[misc]
  def __init__(self) -> None:
    self.clears: List[Tuple[str, str, int]] = []

  def write_batch(self, batch):  # pragma: no cover - not used here
    pass

  def query_time_range(self, *args: Any, **kwargs: Any):  # pragma: no cover - not used here
    raise NotImplementedError

  def get_retention_cutoff(self, retention_days: int) -> float:  # pragma: no cover - not used here
    raise NotImplementedError

  def delete_by_application(self, application_id: str, environment: Optional[str] = None) -> int:  # pragma: no cover - trivial
    # Simulate deletion and track calls
    if application_id == "app-to-clear" and environment == "prod":
      deleted = 3
    elif application_id == "app-to-clear" and environment is None:
      deleted = 5
    else:
      deleted = 0

    self.clears.append((application_id, environment or "", deleted))
    return deleted


def test_clear_logs_deletes_only_scoped_application(monkeypatch):
  client = TestClient(app)
  dummy = DummyClearStorage()

  monkeypatch.setattr(storage_mod, "get_storage", lambda: dummy)

  resp = client.post("/logs/clear", params={"application_id": "app-to-clear"})
  assert resp.status_code == 200
  body = resp.json()
  assert body == {"deleted": 5}

  assert dummy.clears == [("app-to-clear", "", 5)]


def test_clear_logs_with_nonexistent_application_is_safe(monkeypatch):
  client = TestClient(app)
  dummy = DummyClearStorage()

  monkeypatch.setattr(storage_mod, "get_storage", lambda: dummy)

  resp = client.post("/logs/clear", params={"application_id": "unknown-app"})
  assert resp.status_code == 200
  body = resp.json()
  assert body == {"deleted": 0}

  assert dummy.clears == [("unknown-app", "", 0)]


def test_clear_logs_scoped_by_environment(monkeypatch):
  client = TestClient(app)
  dummy = DummyClearStorage()

  monkeypatch.setattr(storage_mod, "get_storage", lambda: dummy)

  resp = client.post(
    "/logs/clear",
    params={"application_id": "app-to-clear", "environment": "prod"},
  )
  assert resp.status_code == 200
  body = resp.json()
  assert body == {"deleted": 3}

  assert dummy.clears == [("app-to-clear", "prod", 3)]


