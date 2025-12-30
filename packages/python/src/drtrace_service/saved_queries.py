"""
Saved and templated analysis queries.

This module provides functionality to save, load, and execute templated analysis queries.
Queries are stored as YAML files in a queries directory for easy editing.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class SavedQuery:
    """A saved analysis query template."""

    name: str  # Unique identifier for the query
    description: Optional[str] = None  # Human-readable description
    application_id: str = ""  # Default application_id
    default_time_window_minutes: int = 5  # Default time window in minutes
    min_level: Optional[str] = None  # Default minimum log level
    module_names: Optional[List[str]] = None  # Default module names filter
    service_names: Optional[List[str]] = None  # Default service names filter
    limit: int = 100  # Default limit
    query_type: str = "why"  # "why" or "cross-module"

    def __post_init__(self):
        """Ensure list fields default to empty lists."""
        if self.module_names is None:
            object.__setattr__(self, "module_names", [])
        if self.service_names is None:
            object.__setattr__(self, "service_names", [])


def get_queries_dir() -> Path:
    """
    Get the directory where saved queries are stored.

    Defaults to ~/.drtrace/queries or ./queries if DRTRACE_QUERIES_DIR is not set.
    """
    queries_dir = os.getenv("DRTRACE_QUERIES_DIR")
    if queries_dir:
        return Path(queries_dir)

    # Try user home directory first
    home_queries = Path.home() / ".drtrace" / "queries"
    if home_queries.exists() or os.getenv("HOME"):
        return home_queries

    # Fallback to project-local queries directory
    return Path.cwd() / "queries"


def ensure_queries_dir() -> Path:
    """Ensure the queries directory exists, creating it if necessary."""
    queries_dir = get_queries_dir()
    queries_dir.mkdir(parents=True, exist_ok=True)
    return queries_dir


def get_query_file_path(name: str) -> Path:
    """Get the file path for a saved query by name."""
    queries_dir = ensure_queries_dir()
    # Sanitize name for filename
    safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)
    return queries_dir / f"{safe_name}.yaml"


def save_query(query: SavedQuery) -> None:
    """
    Save a query to disk.

    Args:
        query: The SavedQuery to persist
    """
    file_path = get_query_file_path(query.name)
    query_dict = asdict(query)
    # Remove None values for cleaner YAML
    query_dict = {k: v for k, v in query_dict.items() if v is not None and v != []}

    with open(file_path, "w") as f:
        yaml.dump(query_dict, f, default_flow_style=False, sort_keys=False)


def load_query(name: str) -> Optional[SavedQuery]:
    """
    Load a saved query by name.

    Args:
        name: The name of the query to load

    Returns:
        SavedQuery if found, None otherwise
    """
    file_path = get_query_file_path(name)
    if not file_path.exists():
        return None

    try:
        with open(file_path, "r") as f:
            data = yaml.safe_load(f)
        if not data:
            return None
        return SavedQuery(**data)
    except (yaml.YAMLError, TypeError, KeyError):
        return None


def list_queries() -> List[SavedQuery]:
    """
    List all saved queries.

    Returns:
        List of SavedQuery objects
    """
    queries_dir = ensure_queries_dir()
    queries: List[SavedQuery] = []

    if not queries_dir.exists():
        return queries

    for file_path in queries_dir.glob("*.yaml"):
        try:
            with open(file_path, "r") as f:
                data = yaml.safe_load(f)
            if data and "name" in data:
                queries.append(SavedQuery(**data))
        except (yaml.YAMLError, TypeError, KeyError):
            # Skip invalid files
            continue

    return queries


def delete_query(name: str) -> bool:
    """
    Delete a saved query by name.

    Args:
        name: The name of the query to delete

    Returns:
        True if deleted, False if not found
    """
    file_path = get_query_file_path(name)
    if file_path.exists():
        file_path.unlink()
        return True
    return False


def resolve_query_params(
    query_name: str,
    start_ts: Optional[float] = None,
    end_ts: Optional[float] = None,
    application_id: Optional[str] = None,
    min_level: Optional[str] = None,
    module_names: Optional[List[str]] = None,
    service_names: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Resolve query parameters by loading a saved query and applying overrides.

    Args:
        query_name: Name of the saved query
        start_ts: Override start timestamp (if None, uses query default)
        end_ts: Override end timestamp (if None, uses query default)
        application_id: Override application_id (if None, uses query default)
        min_level: Override min_level (if None, uses query default)
        module_names: Override module_names (if None, uses query default)
        service_names: Override service_names (if None, uses query default)
        limit: Override limit (if None, uses query default)

    Returns:
        Dictionary of resolved parameters

    Raises:
        ValueError: If query not found
    """
    query = load_query(query_name)
    if not query:
        raise ValueError(f"Saved query '{query_name}' not found")

    import time

    # Calculate time window if not provided
    if start_ts is None or end_ts is None:
        now = time.time()
        window_seconds = query.default_time_window_minutes * 60
        if start_ts is None:
            start_ts = now - window_seconds
        if end_ts is None:
            end_ts = now

    return {
        "application_id": application_id or query.application_id,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "min_level": min_level or query.min_level,
        "module_names": module_names if module_names is not None else query.module_names,
        "service_names": service_names if service_names is not None else query.service_names,
        "limit": limit if limit is not None else query.limit,
        "query_type": query.query_type,
    }

