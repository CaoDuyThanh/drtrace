from __future__ import annotations

import os
from typing import List, Optional, Union

import psycopg2
from psycopg2.extras import Json, execute_batch

from .models import LogBatch, LogRecord


class LogStorage:
  """
  Storage abstraction for log events.

  This first implementation writes directly to Postgres using DRTRACE_DATABASE_URL.
  Tests are expected to monkeypatch get_storage() so they do not require a
  running database.
  """

  def write_batch(self, batch: LogBatch) -> None:  # pragma: no cover - integration concern
    raise NotImplementedError

  def query_time_range(
    self,
    start_ts: float,
    end_ts: float,
    application_id: Optional[str] = None,
    module_name: Optional[Union[str, List[str]]] = None,
    service_name: Optional[Union[str, List[str]]] = None,
    limit: int = 100,
  ) -> List[LogRecord]:  # pragma: no cover - integration concern
    raise NotImplementedError

  def get_retention_cutoff(self, retention_days: int) -> float:  # pragma: no cover - integration concern
    """
    Compute a unix timestamp cutoff for retention based on retention_days.
    Implemented in concrete storage backends to centralize time handling if needed.
    """
    raise NotImplementedError

  def delete_by_application(self, application_id: str, environment: Optional[str] = None) -> int:  # pragma: no cover - integration concern
    """
    Delete logs scoped to a specific application_id.

    Returns the number of rows deleted.
    """
    raise NotImplementedError


class PostgresLogStorage(LogStorage):
  def __init__(self, dsn: str) -> None:
    self._dsn = dsn

  def write_batch(self, batch: LogBatch) -> None:  # pragma: no cover - integration concern
    if not batch.logs:
      return

    rows = [_record_to_row(r) for r in batch.logs]

    conn = psycopg2.connect(self._dsn)
    try:
      with conn, conn.cursor() as cur:
        execute_batch(
          cur,
          """
          INSERT INTO logs (
            ts,
            level,
            message,
            application_id,
            service_name,
            module_name,
            file_path,
            line_no,
            exception_type,
            stacktrace,
            context
          )
          VALUES (
            to_timestamp(%s),
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
          )
          """,
          rows,
        )
    finally:
      conn.close()

  def get_retention_cutoff(self, retention_days: int) -> float:  # pragma: no cover - integration concern
    import time

    seconds = max(retention_days, 0) * 24 * 60 * 60
    return time.time() - seconds

  def delete_older_than(self, cutoff_ts: float) -> int:  # pragma: no cover - integration concern
    """
    Hard-delete logs older than the given unix timestamp cutoff.

    Returns the number of rows deleted. Intended for use by a simple
    housekeeping job in development environments.
    """
    conn = psycopg2.connect(self._dsn)
    try:
      with conn, conn.cursor() as cur:
        cur.execute(
          "DELETE FROM logs WHERE ts < to_timestamp(%s)",
          (cutoff_ts,),
        )
        # rowcount is number of rows affected by the last execute
        deleted = cur.rowcount or 0
    finally:
      conn.close()

    return deleted

  def delete_by_application(self, application_id: str, environment: Optional[str] = None) -> int:  # pragma: no cover - integration concern
    """
    Hard-delete logs for a specific application_id. Intended for use by
    admin/cleanup operations; callers should ensure the scope is explicit.
    """
    conn = psycopg2.connect(self._dsn)
    try:
      with conn, conn.cursor() as cur:
        query = "DELETE FROM logs WHERE application_id = %s"
        params: list[object] = [application_id]
        # Optional environment scoping via JSON context (if present)
        if environment:
          query += " AND context->>'environment' = %s"
          params.append(environment)

        cur.execute(query, tuple(params))
        deleted = cur.rowcount or 0
    finally:
      conn.close()

    return deleted

  def query_time_range(
    self,
    start_ts: float,
    end_ts: float,
    application_id: Optional[str] = None,
    module_name: Optional[Union[str, List[str]]] = None,
    service_name: Optional[Union[str, List[str]]] = None,
    limit: int = 100,
  ) -> List[LogRecord]:  # pragma: no cover - integration concern
    """
    Simple time-range query over logs table ordered by ts DESC.

    Supports filtering by single or multiple module_name and service_name values.
    """
    dsn = self._dsn
    conn = psycopg2.connect(dsn)
    try:
      with conn, conn.cursor() as cur:
        params: list[object] = [start_ts, end_ts]
        where = "ts BETWEEN to_timestamp(%s) AND to_timestamp(%s)"
        if application_id:
          where += " AND application_id = %s"
          params.append(application_id)
        if module_name:
          if isinstance(module_name, list):
            if module_name:
              placeholders = ",".join(["%s"] * len(module_name))
              where += f" AND module_name IN ({placeholders})"
              params.extend(module_name)
          else:
            where += " AND module_name = %s"
            params.append(module_name)
        if service_name:
          if isinstance(service_name, list):
            if service_name:
              placeholders = ",".join(["%s"] * len(service_name))
              where += f" AND service_name IN ({placeholders})"
              params.extend(service_name)
          else:
            where += " AND service_name = %s"
            params.append(service_name)

        cur.execute(
          f"""
          SELECT
            EXTRACT(EPOCH FROM ts) as ts,
            level,
            message,
            application_id,
            service_name,
            module_name,
            file_path,
            line_no,
            exception_type,
            stacktrace,
            context
          FROM logs
          WHERE {where}
          ORDER BY ts DESC
          LIMIT %s
          """,
          (*params, limit),
        )
        rows = cur.fetchall()

    finally:
      conn.close()

    records: List[LogRecord] = []
    for row in rows:
      ts, level, message, app_id, svc, mod, file_path, line_no, exc_type, stacktrace, context = row
      records.append(
        LogRecord(
          ts=ts,
          level=level,
          message=message,
          application_id=app_id,
          service_name=svc,
          module_name=mod,
          file_path=file_path,
          line_no=line_no,
          exception_type=exc_type,
          stacktrace=stacktrace,
          context=context or {},
        )
      )
    return records


_storage: LogStorage | None = None


def get_storage() -> LogStorage:
  """
  Return the global storage instance.

  In tests this can be monkeypatched to avoid real DB access.
  """
  global _storage
  if _storage is None:
    dsn = os.getenv(
      "DRTRACE_DATABASE_URL",
      "postgresql://postgres:postgres@localhost:5432/drtrace",
    )
    _storage = PostgresLogStorage(dsn)
  return _storage


def _record_to_row(record: LogRecord) -> tuple:
  return (
    record.ts,
    record.level,
    record.message,
    record.application_id,
    record.service_name,
    record.module_name,
    record.file_path,
    record.line_no,
    record.exception_type,
    record.stacktrace,
    Json(record.context or {}),
  )


