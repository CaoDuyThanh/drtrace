from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set


@dataclass(frozen=True)
class SourceRootsConfig:
  roots: List[Path]


@dataclass(frozen=True)
class SearchConfig:
  roots: List[Path]
  extensions: Set[str]


def load_source_roots() -> SourceRootsConfig:
  """
  Load source roots from DRTRACE_SOURCE_ROOTS or default to the current working directory.

  DRTRACE_SOURCE_ROOTS is a os.pathsep-separated list of paths (e.g., "src:lib").
  """
  raw = os.getenv("DRTRACE_SOURCE_ROOTS")
  if not raw:
    return SourceRootsConfig(roots=[Path.cwd()])

  roots: List[Path] = []
  for part in raw.split(os.pathsep):
    part = part.strip()
    if not part:
      continue
    roots.append(Path(part).expanduser())

  if not roots:
    roots.append(Path.cwd())

  return SourceRootsConfig(roots=roots)


def load_search_config() -> SearchConfig:
  """
  Load search configuration from DRTRACE_SEARCH_EXTS and source roots.

  DRTRACE_SEARCH_EXTS is a comma-separated list of file extensions (e.g., ".py,.pyi").
  Defaults to {".py"} when unset or invalid.
  """
  roots_cfg = load_source_roots()
  raw_exts = os.getenv("DRTRACE_SEARCH_EXTS")

  exts: Set[str] = set()
  if raw_exts:
    for part in raw_exts.split(","):
      part = part.strip()
      if not part:
        continue
      if not part.startswith("."):
        part = "." + part
      exts.add(part)

  if not exts:
    exts = {".py"}

  return SearchConfig(roots=roots_cfg.roots, extensions=exts)


