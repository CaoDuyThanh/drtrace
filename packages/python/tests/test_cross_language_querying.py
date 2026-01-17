"""
Comprehensive tests for cross-language querying behavior.

These tests validate Story 4.4 requirements: unified query results
and filter behavior across Python and C++ logs.
"""

import time
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]
from drtrace_service.models import LogBatch, LogRecord  # type: ignore[import]


class QueryableStorage(storage_mod.LogStorage):  # type: ignore[misc]
    """Storage that supports full querying for cross-language validation."""

    def __init__(self):
        self.all_records: list[LogRecord] = []

    def write_batch(self, batch: LogBatch) -> None:  # pragma: no cover - trivial
        self.all_records.extend(batch.logs)

    def query_time_range(
        self,
        start_ts: float,
        end_ts: float,
        application_id: Optional[str] = None,
        module_name: Optional[Any] = None,
        service_name: Optional[Any] = None,
        message_contains: Optional[str] = None,
        message_regex: Optional[str] = None,
        min_level: Optional[str] = None,
        after_cursor: Optional[Any] = None,
        limit: int = 100,
    ) -> List[LogRecord]:
        """Query records matching all criteria."""
        results: List[LogRecord] = []
        for record in self.all_records:
            # Time range filter
            if record.ts < start_ts or record.ts > end_ts:
                continue
            # Application ID filter
            if application_id and record.application_id != application_id:
                continue
            # Module name filter
            if module_name:
                if isinstance(module_name, list):
                    if record.module_name not in module_name:
                        continue
                else:
                    if record.module_name != module_name:
                        continue
            # Service name filter
            if service_name:
                if isinstance(service_name, list):
                    if record.service_name not in service_name:
                        continue
                else:
                    if record.service_name != service_name:
                        continue
            # Message contains filter
            if message_contains:
                if message_contains.lower() not in (record.message or "").lower():
                    continue
            # Min level filter
            if min_level:
                level_order = {"DEBUG": 0, "INFO": 1, "WARN": 2, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
                min_order = level_order.get(min_level.upper(), 0)
                record_order = level_order.get((record.level or "").upper(), 0)
                if record_order < min_order:
                    continue
            # Cursor filter
            if after_cursor:
                cursor_ts = after_cursor.get("ts")
                if cursor_ts is not None and record.ts >= cursor_ts:
                    continue
            results.append(record)
        # Sort by timestamp descending (newest first)
        results.sort(key=lambda r: r.ts, reverse=True)
        return results[:limit]

    def get_retention_cutoff(self, *args, **kwargs):  # type: ignore
        return 0.0

    def delete_older_than(self, *args, **kwargs):  # type: ignore
        return 0

    def delete_by_application(self, *args, **kwargs):  # type: ignore
        return 0


def _make_python_log(
    application_id: str = "test-app",
    service_name: Optional[str] = "python-service",
    module_name: str = "python_module",
    level: str = "INFO",
    message: str = "Python log",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a Python log payload."""
    base: Dict[str, Any] = {
        "ts": time.time(),
        "level": level,
        "message": message,
        "application_id": application_id,
        "module_name": module_name,
        "context": {},
    }
    if service_name:
        base["service_name"] = service_name
    base.update(kwargs)
    return base


def _make_cpp_log(
    application_id: str = "test-app",
    service_name: Optional[str] = "cpp-service",
    module_name: str = "cpp_module",
    level: str = "INFO",
    message: str = "C++ log",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a C++ log payload."""
    base: Dict[str, Any] = {
        "ts": time.time(),
        "level": level,
        "message": message,
        "application_id": application_id,
        "module_name": module_name,
        "context": {"language": "cpp"},
    }
    if service_name:
        base["service_name"] = service_name
    base.update(kwargs)
    return base


def test_unified_query_results_include_both_languages(monkeypatch):
    """
    Unified query results include both Python and C++ logs.

    AC 1: Given logs from both languages, query by application_id and time range
    returns both, with identical response format.
    """
    client = TestClient(app)
    storage = QueryableStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Seed logs from both languages with same application_id
    python_log = _make_python_log(
        application_id="multi-lang-app",
        message="Python handler started",
        ts=base_time + 1.0,
    )
    cpp_log = _make_cpp_log(
        application_id="multi-lang-app",
        message="C++ engine initialized",
        ts=base_time + 2.0,
    )

    client.post("/logs/ingest", json={"application_id": "multi-lang-app", "logs": [python_log]})
    client.post("/logs/ingest", json={"application_id": "multi-lang-app", "logs": [cpp_log]})

    # Query by application_id and time range
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id=multi-lang-app"
    )

    assert resp.status_code == 200
    data = resp.json()

    # Verify response format
    assert "results" in data
    assert "count" in data
    assert isinstance(data["results"], list)
    assert data["count"] == 2

    # Verify both languages present
    results = data["results"]
    assert len(results) == 2

    # Verify response format is identical for both languages
    for result in results:
        # All results have same structure
        assert "ts" in result
        assert "level" in result
        assert "message" in result
        assert "application_id" in result
        assert "module_name" in result
        assert "context" in result

    # Verify language identification
    messages = {r["message"] for r in results}
    assert "Python handler started" in messages
    assert "C++ engine initialized" in messages


def test_module_name_filter_works_across_languages(monkeypatch):
    """
    Module name filter returns matching logs from all languages.

    AC 2: Filters like module_name work across languages without
    requiring language-specific parameters.
    """
    client = TestClient(app)
    storage = QueryableStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Create logs with same module_name but different languages
    shared_module_python = _make_python_log(
        application_id="test-app",
        module_name="shared_component",
        message="Python: shared component init",
        ts=base_time + 1.0,
    )
    shared_module_cpp = _make_cpp_log(
        application_id="test-app",
        module_name="shared_component",
        message="C++: shared component init",
        ts=base_time + 2.0,
    )
    other_module_python = _make_python_log(
        application_id="test-app",
        module_name="other_component",
        message="Python: other component",
        ts=base_time + 3.0,
    )

    # Ingest all logs
    for log in [shared_module_python, shared_module_cpp, other_module_python]:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query with module_name filter
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id=test-app&module_name=shared_component"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2  # Both Python and C++ from shared_component

    # Verify both languages returned
    results = data["results"]
    messages = {r["message"] for r in results}
    assert "Python: shared component init" in messages
    assert "C++: shared component init" in messages

    # Verify non-matching logs excluded
    assert "Python: other component" not in messages

    # Verify all results have correct module_name
    assert all(r["module_name"] == "shared_component" for r in results)


def test_application_id_filter_works_across_languages(monkeypatch):
    """Application ID filter returns logs from all languages for that application."""
    client = TestClient(app)
    storage = QueryableStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Create logs from same application but different languages
    app1_python = _make_python_log(
        application_id="app-1",
        message="App1 Python log",
        ts=base_time + 1.0,
    )
    app1_cpp = _make_cpp_log(
        application_id="app-1",
        message="App1 C++ log",
        ts=base_time + 2.0,
    )
    app2_python = _make_python_log(
        application_id="app-2",
        message="App2 Python log",
        ts=base_time + 3.0,
    )

    # Ingest all
    for log in [app1_python, app1_cpp, app2_python]:
        client.post("/logs/ingest", json={"application_id": log["application_id"], "logs": [log]})

    # Query for app-1 only
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id=app-1"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2  # Both Python and C++ from app-1

    results = data["results"]
    messages = {r["message"] for r in results}
    assert "App1 Python log" in messages
    assert "App1 C++ log" in messages
    assert "App2 Python log" not in messages  # Excluded


def test_time_range_filter_works_across_languages(monkeypatch):
    """Time range filters work consistently for both languages."""
    client = TestClient(app)
    storage = QueryableStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Create logs at different times
    early_python = _make_python_log(
        application_id="test-app",
        message="Early Python log",
        ts=base_time + 1.0,
    )
    in_range_cpp = _make_cpp_log(
        application_id="test-app",
        message="In-range C++ log",
        ts=base_time + 5.0,
    )
    in_range_python = _make_python_log(
        application_id="test-app",
        message="In-range Python log",
        ts=base_time + 6.0,
    )
    late_cpp = _make_cpp_log(
        application_id="test-app",
        message="Late C++ log",
        ts=base_time + 11.0,
    )

    # Ingest all
    for log in [early_python, in_range_cpp, in_range_python, late_cpp]:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query for time range that includes some logs from both languages
    start_ts = base_time + 4.0
    end_ts = base_time + 10.0
    resp = client.get(
        f"/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id=test-app"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2  # Both in-range logs

    results = data["results"]
    messages = {r["message"] for r in results}
    assert "In-range C++ log" in messages
    assert "In-range Python log" in messages
    assert "Early Python log" not in messages  # Excluded (before range)
    assert "Late C++ log" not in messages  # Excluded (after range)


def test_combined_filters_work_across_languages(monkeypatch):
    """Combined filters (application_id + module_name + time) work across languages."""
    client = TestClient(app)
    storage = QueryableStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Create logs with various combinations
    target_python = _make_python_log(
        application_id="target-app",
        module_name="target_module",
        message="Target Python",
        ts=base_time + 5.0,
    )
    target_cpp = _make_cpp_log(
        application_id="target-app",
        module_name="target_module",
        message="Target C++",
        ts=base_time + 6.0,
    )
    wrong_app = _make_python_log(
        application_id="other-app",
        module_name="target_module",
        message="Wrong app",
        ts=base_time + 5.0,
    )
    wrong_module = _make_python_log(
        application_id="target-app",
        module_name="other_module",
        message="Wrong module",
        ts=base_time + 5.0,
    )

    # Ingest all
    for log in [target_python, target_cpp, wrong_app, wrong_module]:
        client.post("/logs/ingest", json={"application_id": log["application_id"], "logs": [log]})

    # Query with combined filters
    start_ts = base_time + 4.0
    end_ts = base_time + 10.0
    resp = client.get(
        f"/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id=target-app&module_name=target_module"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2  # Both target logs

    results = data["results"]
    messages = {r["message"] for r in results}
    assert "Target Python" in messages
    assert "Target C++" in messages
    assert "Wrong app" not in messages
    assert "Wrong module" not in messages


def test_response_format_identical_regardless_of_language(monkeypatch):
    """Response format is identical for Python and C++ logs."""
    client = TestClient(app)
    storage = QueryableStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    python_log = _make_python_log(
        application_id="test-app",
        message="Python test",
        ts=base_time + 1.0,
    )
    cpp_log = _make_cpp_log(
        application_id="test-app",
        message="C++ test",
        ts=base_time + 2.0,
    )

    client.post("/logs/ingest", json={"application_id": "test-app", "logs": [python_log]})
    client.post("/logs/ingest", json={"application_id": "test-app", "logs": [cpp_log]})

    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id=test-app"
    )

    assert resp.status_code == 200
    data = resp.json()
    results = data["results"]

    # Verify all results have identical structure
    required_fields = {
        "ts",
        "level",
        "message",
        "application_id",
        "module_name",
        "context",
    }
    optional_fields = {
        "service_name",
        "file_path",
        "line_no",
        "exception_type",
        "stacktrace",
    }

    for result in results:
        # All required fields present
        assert required_fields.issubset(result.keys())
        # Optional fields may or may not be present, but structure is same
        result_keys = set(result.keys())
        extra_keys = result_keys - required_fields - optional_fields
        assert len(extra_keys) == 0, f"Unexpected fields: {extra_keys}"

    # Verify context is always a dict
    for result in results:
        assert isinstance(result["context"], dict)

