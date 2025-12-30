import os

import psycopg2


DDL = """
CREATE TABLE IF NOT EXISTS logs (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  application_id TEXT NOT NULL,
  service_name TEXT,
  module_name TEXT NOT NULL,
  file_path TEXT,
  line_no INTEGER,
  exception_type TEXT,
  stacktrace TEXT,
  context JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_logs_app_ts
  ON logs (application_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_logs_service_ts
  ON logs (service_name, ts DESC);
CREATE INDEX IF NOT EXISTS idx_logs_module_ts
  ON logs (module_name, ts DESC);
"""


def main() -> None:
  dsn = os.getenv(
    "DRTRACE_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/drtrace",
  )
  conn = psycopg2.connect(dsn)
  try:
    with conn, conn.cursor() as cur:
      cur.execute(DDL)
  finally:
    conn.close()


if __name__ == "__main__":  # pragma: no cover
  main()


