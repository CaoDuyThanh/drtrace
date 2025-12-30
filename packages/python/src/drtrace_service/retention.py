from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_RETENTION_DAYS = 7


@dataclass(frozen=True)
class RetentionConfig:
  days: int


def load_retention_config() -> RetentionConfig:
  raw = os.getenv("DRTRACE_RETENTION_DAYS")
  if raw is None:
    return RetentionConfig(days=DEFAULT_RETENTION_DAYS)

  try:
    value = int(raw)
  except ValueError:
    # Fallback to default on invalid input
    return RetentionConfig(days=DEFAULT_RETENTION_DAYS)

  # Clamp to a reasonable range for the POC (1–365 days)
  if value < 1:
    value = 1
  if value > 365:
    value = 365

  return RetentionConfig(days=value)


