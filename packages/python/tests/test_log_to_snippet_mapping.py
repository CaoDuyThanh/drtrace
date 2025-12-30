from pathlib import Path
from typing import List

from drtrace_service.analysis import (  # type: ignore[import]
  LogWithSnippet,
  map_log_to_snippet,
  map_logs_to_snippets,
)
from drtrace_service.models import LogRecord  # type: ignore[import]


def _make_file(tmp_path: Path, rel_path: str, content: str) -> Path:
  file_path = tmp_path / rel_path
  file_path.parent.mkdir(parents=True, exist_ok=True)
  file_path.write_text(content)
  return file_path


def test_map_log_to_snippet_single(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  content = "\n".join([f"line {i}" for i in range(1, 11)])
  _make_file(root, "main.py", content)

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  log = LogRecord(
    ts=0.0,
    level="ERROR",
    message="boom",
    application_id="app",
    module_name="mod",
    file_path="main.py",
    line_no=5,
  )

  result = map_log_to_snippet(log, context_lines=2)
  assert isinstance(result, LogWithSnippet)
  assert result.log is log
  assert result.snippet.ok
  # Expect lines 3–7 with 5 as target
  assert [l.line_no for l in result.snippet.lines] == [3, 4, 5, 6, 7]
  assert any(l.is_target and l.line_no == 5 for l in result.snippet.lines)


def test_map_logs_to_snippets_uses_cache(tmp_path, monkeypatch):
  root = tmp_path / "src"
  root.mkdir()
  content = "\n".join([f"line {i}" for i in range(1, 21)])
  _make_file(root, "file.py", content)

  monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(root))

  logs: List[LogRecord] = [
    LogRecord(
      ts=0.0,
      level="ERROR",
      message="first",
      application_id="app",
      module_name="mod",
      file_path="file.py",
      line_no=10,
    ),
    LogRecord(
      ts=1.0,
      level="ERROR",
      message="second",
      application_id="app",
      module_name="mod",
      file_path="file.py",
      line_no=10,
    ),
  ]

  results = map_logs_to_snippets(logs, context_lines=1)
  assert len(results) == 2
  assert all(r.snippet.ok for r in results)
  # Snippets should be identical for both logs
  assert results[0].snippet.lines == results[1].snippet.lines


