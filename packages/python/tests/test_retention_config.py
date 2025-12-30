from drtrace_service.retention import (  # type: ignore[import]
  DEFAULT_RETENTION_DAYS,
  load_retention_config,
)


def test_retention_defaults_to_7_days_when_unset(monkeypatch):
  monkeypatch.delenv("DRTRACE_RETENTION_DAYS", raising=False)
  cfg = load_retention_config()
  assert cfg.days == DEFAULT_RETENTION_DAYS


def test_retention_parses_valid_integer(monkeypatch):
  monkeypatch.setenv("DRTRACE_RETENTION_DAYS", "30")
  cfg = load_retention_config()
  assert cfg.days == 30


def test_retention_clamps_to_min_and_max(monkeypatch):
  monkeypatch.setenv("DRTRACE_RETENTION_DAYS", "0")
  cfg = load_retention_config()
  assert cfg.days == 1

  monkeypatch.setenv("DRTRACE_RETENTION_DAYS", "9999")
  cfg = load_retention_config()
  assert cfg.days == 365


def test_retention_falls_back_on_invalid_value(monkeypatch):
  monkeypatch.setenv("DRTRACE_RETENTION_DAYS", "not-an-int")
  cfg = load_retention_config()
  assert cfg.days == DEFAULT_RETENTION_DAYS


