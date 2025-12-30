from pathlib import Path

from drtrace_service.code_context import search_in_file, search_in_roots  # type: ignore[import]
from drtrace_service.config import load_search_config  # type: ignore[import]


def _make_file(tmp_path: Path, rel_path: str, content: str) -> Path:
  file_path = tmp_path / rel_path
  file_path.parent.mkdir(parents=True, exist_ok=True)
  file_path.write_text(content)
  return file_path


def test_search_in_file_finds_matches(tmp_path):
  content = "\n".join(
    [
      "def foo():",
      "    pass",
      "def bar():",
      "    foo()",
    ]
  )
  file_path = _make_file(tmp_path, "mod.py", content)

  result = search_in_file(file_path, "foo")
  assert result.ok
  # Should match definition and call sites
  assert [m.line_no for m in result.matches] == [1, 4]


def test_search_in_file_no_matches(tmp_path):
  file_path = _make_file(tmp_path, "mod2.py", "print('hello')\n")

  result = search_in_file(file_path, "missing")
  assert result.ok
  assert result.matches == []


def test_search_in_roots_across_multiple_files(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  _make_file(root, "a.py", "def foo():\n    pass\n")
  _make_file(root, "b.py", "def bar():\n    foo()\n")
  _make_file(root, "c.txt", "foo in text\n")  # should be ignored (non-.py)

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  result = search_in_roots("foo")
  assert result.ok
  # Should find matches in a.py and b.py only
  paths = {m.file_path.name for m in result.matches}
  assert paths == {"a.py", "b.py"}


def test_search_in_roots_no_matches(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  _make_file(root, "a.py", "def foo():\n    pass\n")

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  result = search_in_roots("does_not_exist")
  assert result.ok
  assert result.matches == []


def test_load_search_config_defaults_and_env(monkeypatch, tmp_path):
  # Default: should use source roots + .py
  monkeypatch.delenv("DRTRACE_SOURCE_ROOTS", raising=False)
  monkeypatch.delenv("DRTRACE_SEARCH_EXTS", raising=False)

  cfg = load_search_config()
  assert ".py" in cfg.extensions
  assert cfg.roots  # non-empty

  # With explicit roots and exts
  root = tmp_path / "src"
  root.mkdir()
  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))
  monkeypatch.setenv("DRTRACE_SEARCH_EXTS", ".py,.pyi,txt")

  cfg2 = load_search_config()
  assert cfg2.roots == [root]
  # Normalized extensions
  assert {".py", ".pyi", ".txt"}.issubset(cfg2.extensions)


