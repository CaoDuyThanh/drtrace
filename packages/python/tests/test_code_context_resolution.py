from pathlib import Path

from drtrace_service.code_context import load_file_contents, resolve_file_path  # type: ignore[import]
from drtrace_service.config import load_source_roots  # type: ignore[import]


def test_load_source_roots_defaults_to_cwd(monkeypatch, tmp_path):
  # Ensure env var is not set
  monkeypatch.delenv("DRTRACE_SOURCE_ROOTS", raising=False)

  # Change CWD to a temp directory to make behavior deterministic
  monkeypatch.chdir(tmp_path)

  cfg = load_source_roots()
  assert cfg.roots == [tmp_path]


def test_load_source_roots_from_env(monkeypatch, tmp_path):
  root1 = tmp_path / "src"
  root2 = tmp_path / "lib"
  root1.mkdir()
  root2.mkdir()

  import os

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", os.pathsep.join([str(root1), str(root2)]))

  cfg = load_source_roots()
  assert root1 in cfg.roots and root2 in cfg.roots


def test_resolve_absolute_path(tmp_path, monkeypatch):
  file_path = tmp_path / "main.py"
  file_path.write_text("print('hi')")

  # CWD/roots shouldn't matter for absolute path
  monkeypatch.delenv("DRTRACE_SOURCE_ROOTS", raising=False)

  result = resolve_file_path(str(file_path))
  assert result.ok
  assert result.path == file_path


def test_resolve_relative_path_under_root(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  file_path = root / "pkg" / "mod.py"
  file_path.parent.mkdir(parents=True, exist_ok=True)
  file_path.write_text("# test")

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  result = resolve_file_path("pkg/mod.py")
  assert result.ok
  assert result.path == file_path


def test_resolve_missing_file_returns_clear_error(monkeypatch, tmp_path):
  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(tmp_path))

  result = resolve_file_path("does/not/exist.py")
  assert not result.ok
  assert result.path is None
  assert result.error == "file not found"


def test_load_file_contents_happy_path(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  file_path = root / "pkg" / "mod.py"
  file_path.parent.mkdir(parents=True, exist_ok=True)
  file_path.write_text("print('ok')\n")

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  result = load_file_contents("pkg/mod.py")
  assert result.ok
  assert "print('ok')" in (result.content or "")


def test_load_file_contents_permission_error_logs_and_reports(caplog, tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  file_path = root / "secret.py"
  file_path.write_text("# secret\n")

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  # Force PermissionError when reading
  # Monkeypatch Path.read_text used inside load_file_contents

  original_read_text = Path.read_text

  def fake_read_text(self, *args, **kwargs):
    if self == file_path:
      raise PermissionError("denied")
    return original_read_text(self, *args, **kwargs)

  monkeypatch.setattr(Path, "read_text", fake_read_text)

  caplog.set_level("WARNING", logger="drtrace_service.code_context")
  result = load_file_contents("secret.py")

  assert not result.ok
  assert result.content is None
  assert result.error == "permission denied"

  # Ensure a warning was logged
  assert any("Permission denied reading" in rec.getMessage() for rec in caplog.records)



