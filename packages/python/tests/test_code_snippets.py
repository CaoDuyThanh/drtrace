from pathlib import Path

from drtrace_service.code_context import get_code_snippet  # type: ignore[import]


def _make_file(tmp_path: Path, rel_path: str, content: str) -> Path:
  file_path = tmp_path / rel_path
  file_path.parent.mkdir(parents=True, exist_ok=True)
  file_path.write_text(content)
  return file_path


def test_get_code_snippet_mid_file(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  content = "\n".join(
    [
      "line 1",
      "line 2",
      "line 3",
      "line 4",
      "line 5",
      "line 6",
      "line 7",
    ]
  )
  _make_file(root, "mod.py", content)

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  result = get_code_snippet("mod.py", line_no=4, context_lines=2)
  assert result.ok
  # Expected snippet: lines 2–6
  assert [l.line_no for l in result.lines] == [2, 3, 4, 5, 6]
  assert any(l.is_target and l.line_no == 4 for l in result.lines)


def test_get_code_snippet_near_start_clips_to_file(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  content = "\n".join(["a", "b", "c"])
  _make_file(root, "short.py", content)

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  result = get_code_snippet("short.py", line_no=1, context_lines=5)
  assert result.ok
  # Should start at line 1, not below
  assert [l.line_no for l in result.lines] == [1, 2, 3]
  assert any(l.is_target and l.line_no == 1 for l in result.lines)


def test_get_code_snippet_near_end_clips_to_file(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  content = "\n".join(["a", "b", "c"])
  _make_file(root, "short2.py", content)

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  result = get_code_snippet("short2.py", line_no=3, context_lines=5)
  assert result.ok
  # Should end at last line
  assert [l.line_no for l in result.lines] == [1, 2, 3]
  assert any(l.is_target and l.line_no == 3 for l in result.lines)


def test_get_code_snippet_out_of_range_line(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  _make_file(root, "tiny.py", "only one line\n")

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  result = get_code_snippet("tiny.py", line_no=10, context_lines=2)
  assert not result.ok
  assert result.lines == []
  assert result.error == "line_no out of range"


def test_get_code_snippet_invalid_line_number(monkeypatch, tmp_path):
  root = tmp_path / "src"
  root.mkdir()
  _make_file(root, "file.py", "x = 1\n")

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  result = get_code_snippet("file.py", line_no=0, context_lines=2)
  assert not result.ok
  assert result.lines == []
  assert result.error == "line_no must be >= 1"


