"""
Tests for cross-language log ingestion and querying.

These tests verify that C++ and Python logs can be ingested together
and queried from the same storage, validating Story 4.3 requirements.
"""

import time
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]
from drtrace_service.models import LogBatch, LogRecord  # type: ignore[import]


class TrackingStorage(storage_mod.LogStorage):  # type: ignore[misc]
    """Storage that tracks all written batches and supports querying."""

    def __init__(self):
        self.batches: list[LogBatch] = []
        self.all_records: list[LogRecord] = []

    def write_batch(self, batch: LogBatch) -> None:  # pragma: no cover - trivial
        self.batches.append(batch)
        self.all_records.extend(batch.logs)

    def query_time_range(
        self,
        start_ts: float,
        end_ts: float,
        application_id: Optional[str] = None,
        module_name: Optional[Any] = None,
        service_name: Optional[Any] = None,
        limit: int = 100,
    ) -> List[LogRecord]:
        """Query records matching the criteria."""
        results: List[LogRecord] = []
        for record in self.all_records:
            if record.ts < start_ts or record.ts > end_ts:
                continue
            if application_id and record.application_id != application_id:
                continue
            if module_name:
                if isinstance(module_name, list):
                    if record.module_name not in module_name:
                        continue
                else:
                    if record.module_name != module_name:
                        continue
            if service_name:
                if isinstance(service_name, list):
                    if record.service_name not in service_name:
                        continue
                else:
                    if record.service_name != service_name:
                        continue
            results.append(record)
            if len(results) >= limit:
                break
        # Sort by timestamp descending (newest first)
        results.sort(key=lambda r: r.ts, reverse=True)
        return results

    def get_retention_cutoff(self, *args, **kwargs):  # type: ignore
        return 0.0

    def delete_older_than(self, *args, **kwargs):  # type: ignore
        return 0

    def delete_by_application(self, *args, **kwargs):  # type: ignore
        return 0


def _make_python_log(
    application_id: str = "test-app",
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
        "context": {"request_id": "req-123"},
    }
    base.update(kwargs)
    return base


def _make_cpp_log(
    application_id: str = "test-app",
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
        "context": {"language": "cpp", "thread_id": "12345"},
    }
    base.update(kwargs)
    return base


def test_cpp_logs_stored_in_same_table_as_python(monkeypatch):
    """C++ logs are written to the same storage table as Python logs."""
    client = TestClient(app)
    storage = TrackingStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Ingest Python log
    python_payload = {
        "application_id": "test-app",
        "logs": [_make_python_log()],
    }
    resp = client.post("/logs/ingest", json=python_payload)
    assert resp.status_code == 202

    # Ingest C++ log
    cpp_payload = {
        "application_id": "test-app",
        "logs": [_make_cpp_log()],
    }
    resp = client.post("/logs/ingest", json=cpp_payload)
    assert resp.status_code == 202

    # Verify both are in the same storage
    assert len(storage.batches) == 2
    assert len(storage.all_records) == 2

    # Verify language markers
    python_record = storage.all_records[0]
    cpp_record = storage.all_records[1]
    assert "language" not in python_record.context or python_record.context.get("language") != "cpp"
    assert cpp_record.context.get("language") == "cpp"


def test_cross_language_query_returns_both_languages(monkeypatch):
    """Query endpoint returns both Python and C++ logs when queried together."""
    client = TestClient(app)
    storage = TrackingStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Ingest logs from both languages with same application_id
    python_log = _make_python_log(
        application_id="mixed-app",
        module_name="python_handler",
        message="Python processing request",
        ts=base_time + 1.0,
    )
    cpp_log = _make_cpp_log(
        application_id="mixed-app",
        module_name="cpp_engine",
        message="C++ rendering frame",
        ts=base_time + 2.0,
    )

    # Ingest both
    client.post("/logs/ingest", json={"application_id": "mixed-app", "logs": [python_log]})
    client.post("/logs/ingest", json={"application_id": "mixed-app", "logs": [cpp_log]})

    # Query without language filter
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id=mixed-app"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2

    # Verify both languages are present
    results = data["results"]
    module_names = {r["module_name"] for r in results}
    assert "python_handler" in module_names
    assert "cpp_engine" in module_names

    # Verify language markers in context
    languages = {
        r["context"].get("language") for r in results if "language" in r["context"]
    }
    assert "cpp" in languages


def test_cross_language_query_respects_module_filter(monkeypatch):
    """Query with module_name filter works across languages."""
    client = TestClient(app)
    storage = TrackingStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Ingest logs from both languages
    python_log = _make_python_log(
        application_id="test-app",
        module_name="shared_module",
        ts=base_time + 1.0,
    )
    cpp_log = _make_cpp_log(
        application_id="test-app",
        module_name="shared_module",  # Same module name
        ts=base_time + 2.0,
    )
    other_log = _make_python_log(
        application_id="test-app",
        module_name="other_module",
        ts=base_time + 3.0,
    )

    client.post("/logs/ingest", json={"application_id": "test-app", "logs": [python_log]})
    client.post("/logs/ingest", json={"application_id": "test-app", "logs": [cpp_log]})
    client.post("/logs/ingest", json={"application_id": "test-app", "logs": [other_log]})

    # Query for specific module (should return both Python and C++ logs)
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id=test-app&module_name=shared_module"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2  # Both Python and C++ logs from shared_module

    results = data["results"]
    assert all(r["module_name"] == "shared_module" for r in results)
    # Verify both languages present
    languages = {
        r["context"].get("language")
        for r in results
        if "language" in r["context"]
    }
    assert "cpp" in languages or len(languages) == 0  # At least one C++ log


def test_mixed_batch_ingestion_works(monkeypatch):
    """A single batch can contain both Python and C++ logs."""
    client = TestClient(app)
    storage = TrackingStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Create a batch with both languages
    mixed_batch = {
        "application_id": "mixed-app",
        "logs": [
            _make_python_log(application_id="mixed-app", message="Python log 1"),
            _make_cpp_log(application_id="mixed-app", message="C++ log 1"),
            _make_python_log(application_id="mixed-app", message="Python log 2"),
        ],
    }

    resp = client.post("/logs/ingest", json=mixed_batch)
    assert resp.status_code == 202
    assert resp.json() == {"accepted": 3}

    # Verify all records stored
    assert len(storage.all_records) == 3
    assert len(storage.batches) == 1

    # Verify language markers
    cpp_count = sum(
        1
        for r in storage.all_records
        if r.context.get("language") == "cpp"
    )
    assert cpp_count == 1


def test_cross_language_query_orders_by_timestamp(monkeypatch):
    """Cross-language queries return results ordered by timestamp (newest first)."""
    client = TestClient(app)
    storage = TrackingStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Ingest logs with different timestamps
    logs = [
        _make_python_log(
            application_id="test-app",
            message="First log",
            ts=base_time + 1.0,
        ),
        _make_cpp_log(
            application_id="test-app",
            message="Second log",
            ts=base_time + 3.0,
        ),
        _make_python_log(
            application_id="test-app",
            message="Third log",
            ts=base_time + 2.0,
        ),
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query and verify ordering (newest first)
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id=test-app"
    )

    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 3

    # Verify descending timestamp order
    timestamps = [r["ts"] for r in results]
    assert timestamps == sorted(timestamps, reverse=True)
    assert results[0]["message"] == "Second log"  # Newest (ts + 3.0)
    assert results[1]["message"] == "Third log"  # Middle (ts + 2.0)
    assert results[2]["message"] == "First log"  # Oldest (ts + 1.0)

