from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse


@dataclass(frozen=True)
class ClientConfig:
  """
  Configuration for the log analysis client.

  Values are sourced from environment variables with sensible defaults.
  """

  application_id: str
  daemon_url: str
  service_name: str | None = None
  enabled: bool = True

  @classmethod
  def from_env(cls) -> "ClientConfig":
    """
    Load configuration from environment variables.

    Required:
      - DRTRACE_APPLICATION_ID

    Optional:
      - DRTRACE_DAEMON_URL (default: http://localhost:8001/logs/ingest)
      - DRTRACE_SERVICE_NAME
    """
    return cls.from_params_or_env()

  @classmethod
  def from_params_or_env(
    cls,
    application_id: Optional[str] = None,
    daemon_url: Optional[str] = None,
    service_name: Optional[str] = None,
  ) -> "ClientConfig":
    """
    Build configuration from explicit parameters, falling back to environment variables.

    Priority:
      1. Explicit function arguments
      2. Environment variables
      3. Config file (_drtrace/config.json)
      4. Default fallback value ("my-app" - ensures application never crashes)
    """

    app_id = application_id or os.getenv("DRTRACE_APPLICATION_ID")
    
    # Priority 3: Try reading from config file
    if not app_id:
      config_path = Path("_drtrace/config.json")
      if config_path.exists():
        try:
          config = json.loads(config_path.read_text())
          app_id = config.get("application_id") or config.get("applicationId")
        except Exception:
          pass
    
    # Priority 4: Final fallback to default value (ensures application never crashes)
    # CRITICAL: Must use same default value as C++ and JavaScript: "my-app"
    if not app_id:
      app_id = "my-app"
      # Optional: import warnings; warnings.warn("Using default application_id 'my-app'. "
      #                                         "Set DRTRACE_APPLICATION_ID or _drtrace/config.json to customize.")

    url = daemon_url or os.getenv(
      "DRTRACE_DAEMON_URL",
      "http://localhost:8001/logs/ingest",
    )
    _validate_daemon_url(url)

    svc_name = service_name or os.getenv("DRTRACE_SERVICE_NAME")
    enabled = _get_enabled_flag()

    return cls(
      application_id=app_id,
      daemon_url=url,
      service_name=svc_name,
      enabled=enabled,
    )


def _validate_daemon_url(url: str) -> None:
  parsed = urlparse(url)
  if parsed.scheme not in ("http", "https") or not parsed.netloc:
    raise ValueError(
      f"Invalid DRTRACE_DAEMON_URL '{url}'. "
      "Expected an http(s) URL like http://localhost:8001/logs/ingest. "
      "See: README.md#install-the-client-via-pip"
    )


def _get_enabled_flag() -> bool:
  """
  Determine whether analysis is enabled.

  Uses DRTRACE_ENABLED env var; defaults to True for local POC.
  Accepts common truthy/falsey strings.
  """
  raw = os.getenv("DRTRACE_ENABLED")
  if raw is None:
    return True

  value = raw.strip().lower()
  if value in ("1", "true", "yes", "on"):
    return True
  if value in ("0", "false", "no", "off"):
    return False

  # Unknown value → treat as disabled for safety and log-only behavior.
  return False


