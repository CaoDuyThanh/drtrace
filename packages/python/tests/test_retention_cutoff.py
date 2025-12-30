import time

from drtrace_service.storage import PostgresLogStorage  # type: ignore[import]


def test_get_retention_cutoff_computes_past_timestamp(monkeypatch):
  # Freeze time.time() for deterministic behavior
  fake_now = 1_700_000_000.0
  monkeypatch.setattr(time, "time", lambda: fake_now)

  storage = PostgresLogStorage(dsn="postgresql://example")  # DSN unused here
  cutoff = storage.get_retention_cutoff(retention_days=7)

  expected = fake_now - 7 * 24 * 60 * 60
  assert cutoff == expected


