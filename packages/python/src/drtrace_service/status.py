from __future__ import annotations

import os
from dataclasses import asdict, dataclass

from .retention import load_retention_config


@dataclass
class DaemonStatus:
  status: str
  service_name: str
  version: str
  host: str
  port: int
  retention_days: int


def get_status() -> dict:
  """
  Return a simple status payload for the local daemon.
  """
  host = os.getenv("DRTRACE_DAEMON_HOST", "localhost")
  port = int(os.getenv("DRTRACE_DAEMON_PORT", "8001"))
  retention_cfg = load_retention_config()

  payload = DaemonStatus(
    status="healthy",
    service_name="drtrace_daemon",
    version="0.1.0",
    host=host,
    port=port,
    retention_days=retention_cfg.days,
  )
  return asdict(payload)


