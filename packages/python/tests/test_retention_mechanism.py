from typing import Any, List, Tuple

import psycopg2  # type: ignore[import]

from drtrace_service.storage import PostgresLogStorage  # type: ignore[import]


class DummyCursor:
  def __init__(self) -> None:
    self.queries: List[Tuple[str, Tuple[Any, ...]]] = []
    self.rowcount = 0

  def execute(self, query: str, params: Tuple[Any, ...]) -> None:
    self.queries.append((query, params))
    # Simulate deleting 3 rows for testing purposes
    self.rowcount = 3

  def __enter__(self) -> "DummyCursor":
    return self

  def __exit__(self, exc_type, exc, tb) -> None:
    pass


class DummyConnection:
  def __init__(self) -> None:
    self.cursor_obj = DummyCursor()

  def cursor(self) -> DummyCursor:
    return self.cursor_obj

  def __enter__(self) -> "DummyConnection":
    return self

  def __exit__(self, exc_type, exc, tb) -> None:
    pass

  def close(self) -> None:  # pragma: no cover - trivial
    pass


def test_delete_older_than_executes_delete_with_cutoff(monkeypatch):
  dummy_conn = DummyConnection()

  def fake_connect(dsn: str) -> DummyConnection:
    return dummy_conn

  monkeypatch.setattr(psycopg2, "connect", fake_connect)

  storage = PostgresLogStorage(dsn="postgresql://example")
  deleted = storage.delete_older_than(1_700_000_000.0)

  # Should report the simulated deleted rows
  assert deleted == 3

  # Verify the SQL and parameters used
  assert len(dummy_conn.cursor_obj.queries) == 1
  query, params = dummy_conn.cursor_obj.queries[0]
  assert "DELETE FROM logs" in query
  assert params == (1_700_000_000.0,)


