import time
from typing import Any, List, Optional

from fastapi.testclient import TestClient

from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]
from drtrace_service.models import LogBatch, LogRecord  # type: ignore[import]


class DummyIdentifierStorage(storage_mod.LogStorage):  # type: ignore[misc]
  def __init__(self) -> None:
    self.records: List[LogRecord] = []

  def write_batch(self, batch: LogBatch) -> None:  # pragma: no cover - trivial
    self.records.extend(batch.logs)

  def query_time_range(
    self,
    start_ts: float,
    end_ts: float,
    application_id: Optional[str] = None,
    module_name: Optional[Any] = None,
    service_name: Optional[Any] = None,
    limit: int = 100,
  ) -> List[LogRecord]:  # pragma: no cover - trivial
    results: List[LogRecord] = []
    for r in self.records:
      if not (start_ts <= r.ts <= end_ts):
        continue
      if application_id and r.application_id != application_id:
        continue
      if module_name:
        if isinstance(module_name, list):
          if r.module_name not in module_name:
            continue
        else:
          if r.module_name != module_name:
            continue
      if service_name:
        if isinstance(service_name, list):
          if r.service_name not in service_name:
            continue
        else:
          if r.service_name != service_name:
            continue
      results.append(r)
    results.sort(key=lambda r: r.ts, reverse=True)
    return results[:limit]


def test_query_filters_by_application_and_module(monkeypatch):
  client = TestClient(app)
  dummy = DummyIdentifierStorage()
  monkeypatch.setattr(storage_mod, "get_storage", lambda: dummy)

  base = time.time()

  logs = [
    LogRecord(
      ts=base - 5,
      level="INFO",
      message="app1-modA",
      application_id="app-1",
      module_name="modA",
    ),
    LogRecord(
      ts=base - 4,
      level="INFO",
      message="app1-modB",
      application_id="app-1",
      module_name="modB",
    ),
    LogRecord(
      ts=base - 3,
      level="INFO",
      message="app2-modA",
      application_id="app-2",
      module_name="modA",
    ),
  ]

  dummy.write_batch(LogBatch(application_id="ignored", logs=logs))

  resp = client.get(
    "/logs/query",
    params={
      "start_ts": base - 10,
      "end_ts": base + 1,
      "application_id": "app-1",
      "module_name": "modB",
    },
  )
  assert resp.status_code == 200
  data = resp.json()
  assert data["count"] == 1
  assert data["results"][0]["message"] == "app1-modB"


