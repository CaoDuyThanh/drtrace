from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from .config import load_search_config, load_source_roots


@dataclass(frozen=True)
class ResolvedFile:
  ok: bool
  path: Optional[Path]
  error: Optional[str] = None


def get_source_roots() -> List[Path]:
  """
  Return configured source roots for resolving file paths.
  """
  cfg = load_source_roots()
  return cfg.roots


def resolve_file_path(file_path: str, roots: Optional[List[Path]] = None) -> ResolvedFile:
  """
  Resolve a file_path against configured source roots.

  - If file_path is absolute, check it directly.
  - If relative, try each configured root / file_path in order.
  """
  if not file_path:
    return ResolvedFile(ok=False, path=None, error="empty file_path")

  roots = roots or get_source_roots()
  candidate = Path(file_path)

  # Absolute path: check directly
  if candidate.is_absolute():
    if candidate.is_file():
      return ResolvedFile(ok=True, path=candidate)
    return ResolvedFile(ok=False, path=None, error="file not found")

  # Relative path: search under roots
  for root in roots:
    full = (root / candidate).resolve()
    if full.is_file():
      return ResolvedFile(ok=True, path=full)

  return ResolvedFile(ok=False, path=None, error="file not found")


@dataclass(frozen=True)
class FileReadResult:
  ok: bool
  content: Optional[str]
  error: Optional[str] = None


_logger = logging.getLogger("drtrace_service.code_context")


def load_file_contents(file_path: str, roots: Optional[List[Path]] = None) -> FileReadResult:
  """
  Resolve a file_path and attempt to read its contents as text.

  Returns a structured result and logs failures without raising.
  """
  resolved = resolve_file_path(file_path, roots=roots)
  if not resolved.ok or not resolved.path:
    _logger.warning("Failed to resolve file_path '%s': %s", file_path, resolved.error)
    return FileReadResult(ok=False, content=None, error=resolved.error or "unresolved")

  try:
    text = resolved.path.read_text(encoding="utf-8")
    return FileReadResult(ok=True, content=text)
  except PermissionError:
    msg = "permission denied"
    _logger.warning("Permission denied reading '%s'", resolved.path)
    return FileReadResult(ok=False, content=None, error=msg)
  except OSError as exc:
    msg = f"unreadable file: {exc}"
    _logger.warning("Error reading '%s': %s", resolved.path, exc)
    return FileReadResult(ok=False, content=None, error=msg)


@dataclass(frozen=True)
class SnippetLine:
  line_no: int  # 1-based line number
  text: str
  is_target: bool


@dataclass(frozen=True)
class SnippetResult:
  ok: bool
  lines: List[SnippetLine]
  error: Optional[str] = None


def get_code_snippet(
  file_path: str,
  line_no: int,
  context_lines: int = 5,
  roots: Optional[List[Path]] = None,
) -> SnippetResult:
  """
  Return a code snippet around a given line number.

  The snippet includes the target line and up to `context_lines` lines of
  context above and below, clipped to file boundaries. The target line is
  marked via `is_target=True`.
  """
  if line_no < 1:
    return SnippetResult(ok=False, lines=[], error="line_no must be >= 1")

  read = load_file_contents(file_path, roots=roots)
  if not read.ok or read.content is None:
    return SnippetResult(ok=False, lines=[], error=read.error or "unreadable file")

  all_lines = read.content.splitlines()
  total = len(all_lines)
  if line_no > total:
    return SnippetResult(ok=False, lines=[], error="line_no out of range")

  # Compute 0-based indices
  idx = line_no - 1
  start_idx = max(0, idx - context_lines)
  end_idx = min(total - 1, idx + context_lines)

  snippet_lines: List[SnippetLine] = []
  for i in range(start_idx, end_idx + 1):
    snippet_lines.append(
      SnippetLine(
        line_no=i + 1,
        text=all_lines[i],
        is_target=(i == idx),
      )
    )

  return SnippetResult(ok=True, lines=snippet_lines)


@dataclass(frozen=True)
class SearchMatch:
  file_path: Path
  line_no: int
  line_text: str


@dataclass(frozen=True)
class SearchResult:
  ok: bool
  matches: List[SearchMatch]
  error: Optional[str] = None


def search_in_file(
  file_path: Path,
  query: str,
  *,
  case_sensitive: bool = False,
) -> SearchResult:
  """
  Search for a query string within a single file.

  Returns all matching lines as SearchMatch entries.
  """
  try:
    text = file_path.read_text(encoding="utf-8")
  except (OSError, UnicodeDecodeError) as exc:
    _logger.warning("Error reading '%s' during search: %s", file_path, exc)
    return SearchResult(ok=False, matches=[], error=f"unreadable file: {exc}")

  if not query:
    return SearchResult(ok=True, matches=[])

  matches: List[SearchMatch] = []
  if case_sensitive:
    for idx, line in enumerate(text.splitlines(), start=1):
      if query in line:
        matches.append(SearchMatch(file_path=file_path, line_no=idx, line_text=line))
  else:
    q = query.lower()
    for idx, line in enumerate(text.splitlines(), start=1):
      if q in line.lower():
        matches.append(SearchMatch(file_path=file_path, line_no=idx, line_text=line))

  return SearchResult(ok=True, matches=matches)


def iter_source_files(roots: Optional[List[Path]] = None, extensions: Optional[Iterable[str]] = None) -> Iterable[Path]:
  """
  Yield source files under configured roots, optionally filtered by file extension.
  """
  if roots is None or extensions is None:
    cfg = load_search_config()
    roots = roots or cfg.roots
    extensions = extensions or cfg.extensions

  exts = set(extensions)

  for root in roots:
    if not root.is_dir():
      continue
    for path in root.rglob("*"):
      if path.is_file() and (not exts or path.suffix in exts):
        yield path


def search_in_roots(
  query: str,
  *,
  roots: Optional[List[Path]] = None,
  extensions: Optional[Iterable[str]] = None,
  max_results: int = 100,
  case_sensitive: bool = False,
) -> SearchResult:
  """
  Search for a query string across all source files under configured roots.
  """
  if not query:
    return SearchResult(ok=True, matches=[])

  all_matches: List[SearchMatch] = []
  for path in iter_source_files(roots=roots, extensions=extensions):
    file_result = search_in_file(path, query, case_sensitive=case_sensitive)
    if not file_result.ok:
      # Skip unreadable files but continue searching others.
      continue
    all_matches.extend(file_result.matches)
    if len(all_matches) >= max_results:
      break

  # Truncate to max_results just in case
  return SearchResult(ok=True, matches=all_matches[:max_results])


