import os

import pytest

from drtrace_service import __main__ as cli  # type: ignore[import]


def _run_cli(args, cwd):
  """Helper to run the CLI main() with a specific cwd and capture SystemExit."""
  old_cwd = os.getcwd()
  os.chdir(cwd)
  try:
    with pytest.raises(SystemExit) as exc:
      cli.main(args)
  finally:
    os.chdir(old_cwd)
  return exc.value.code


def test_init_agent_creates_file_when_missing(tmp_path):
  """init-agent should create the default agent file when missing."""
  target_dir = tmp_path / "agents"
  target_path = target_dir / "log-analysis.md"

  assert not target_path.exists()

  code = _run_cli(["init-agent"], cwd=tmp_path)
  assert code == 0
  assert target_path.exists()

  contents = target_path.read_text(encoding="utf-8")
  assert "Log Analysis Agent" in contents


def test_init_agent_skips_when_exists_without_flags(tmp_path, capsys):
  """init-agent should not overwrite an existing file without --force/--backup."""
  target_dir = tmp_path / "agents"
  target_dir.mkdir()
  target_path = target_dir / "log-analysis.md"
  target_path.write_text("custom agent", encoding="utf-8")

  code = _run_cli(["init-agent"], cwd=tmp_path)
  assert code == 1

  contents = target_path.read_text(encoding="utf-8")
  assert contents == "custom agent"

  captured = capsys.readouterr()
  assert "Agent file already exists" in captured.err
  assert "--force" in captured.err or "--backup" in captured.err


def test_init_agent_force_overwrites_existing(tmp_path):
  """init-agent --force should overwrite existing agent file."""
  target_dir = tmp_path / "agents"
  target_dir.mkdir()
  target_path = target_dir / "log-analysis.md"
  target_path.write_text("custom agent", encoding="utf-8")

  code = _run_cli(["init-agent", "--force"], cwd=tmp_path)
  assert code == 0

  contents = target_path.read_text(encoding="utf-8")
  assert "Log Analysis Agent" in contents


def test_init_agent_backup_creates_backup_and_overwrites(tmp_path):
  """init-agent --backup should create a backup and overwrite the file."""
  target_dir = tmp_path / "agents"
  target_dir.mkdir()
  target_path = target_dir / "log-analysis.md"
  target_path.write_text("custom agent", encoding="utf-8")

  code = _run_cli(["init-agent", "--backup", "--force"], cwd=tmp_path)
  assert code == 0

  # New file should contain default content
  contents = target_path.read_text(encoding="utf-8")
  assert "Log Analysis Agent" in contents

  # Backup file should exist with original content
  backups = list(target_dir.glob("log-analysis.md.bak-*"))
  assert backups, "Expected at least one backup file"
  backup_contents = backups[0].read_text(encoding="utf-8")
  assert backup_contents == "custom agent"


def test_init_agent_log_it_creates_file(tmp_path):
  """init-agent --agent log-it should create the log-it agent file."""
  target_dir = tmp_path / "agents"
  target_path = target_dir / "log-it.md"

  assert not target_path.exists()

  code = _run_cli(["init-agent", "--agent", "log-it"], cwd=tmp_path)
  assert code == 0
  assert target_path.exists()

  contents = target_path.read_text(encoding="utf-8")
  assert "Strategic Logging Assistant" in contents
  assert "log-it" in contents


def test_init_agent_log_it_with_custom_path(tmp_path):
  """init-agent --agent log-it --path custom/path should use custom path."""
  custom_path = tmp_path / "my_agents" / "logging.md"

  assert not custom_path.exists()

  code = _run_cli(["init-agent", "--agent", "log-it", "--path", str(custom_path)], cwd=tmp_path)
  assert code == 0
  assert custom_path.exists()

  contents = custom_path.read_text(encoding="utf-8")
  assert "Strategic Logging Assistant" in contents

