"""
Tests for C++ client integration validation.

These tests verify that the daemon can accept and process log payloads
that match what the C++ client would send, validating cross-language
schema compatibility.
"""

import time
from typing import Any, Dict

from fastapi.testclient import TestClient

from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]
from drtrace_service.models import LogBatch  # type: ignore[import]


class DummyStorage(storage_mod.LogStorage):  # type: ignore[misc]
    """Dummy storage that records batches for verification."""

    def __init__(self):
        self.batches: list[LogBatch] = []

    def write_batch(self, batch: LogBatch) -> None:  # pragma: no cover - trivial
        self.batches.append(batch)

    def query_time_range(self, *args, **kwargs):  # type: ignore
        return []

    def get_retention_cutoff(self, *args, **kwargs):  # type: ignore
        return 0.0

    def delete_older_than(self, *args, **kwargs):  # type: ignore
        return 0

    def delete_by_application(self, *args, **kwargs):  # type: ignore
        return 0


def _make_cpp_log_payload(
    application_id: str = "test-cpp-app",
    service_name: str = "cpp-service",
    module_name: str = "my_cpp_module",
    level: str = "INFO",
    message: str = "C++ log message",
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a log payload matching what the C++ client would send."""
    base: Dict[str, Any] = {
        "ts": time.time(),
        "level": level,
        "message": message,
        "application_id": application_id,
        "module_name": module_name,
        "context": {
            "language": "cpp",
            "thread_id": "12345",
        },
    }
    if service_name:
        base["service_name"] = service_name
    base.update(kwargs)
    return base


def test_cpp_log_payload_validates_against_unified_schema(monkeypatch):
    """C++ log payload validates against the unified schema."""
    client = TestClient(app)
    dummy = DummyStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: dummy)

    payload = {
        "application_id": "test-cpp-app",
        "logs": [_make_cpp_log_payload()],
    }

    resp = client.post("/logs/ingest", json=payload)
    assert resp.status_code == 202
    assert resp.json() == {"accepted": 1}

    # Verify the batch was stored
    assert len(dummy.batches) == 1
    batch = dummy.batches[0]
    assert batch.application_id == "test-cpp-app"
    assert len(batch.logs) == 1
    log = batch.logs[0]
    assert log.application_id == "test-cpp-app"
    assert log.module_name == "my_cpp_module"
    assert log.context.get("language") == "cpp"
    assert log.context.get("thread_id") == "12345"


def test_cpp_log_with_file_path_and_line_no(monkeypatch):
    """C++ log with file_path and line_no validates correctly."""
    client = TestClient(app)
    dummy = DummyStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: dummy)

    payload = {
        "application_id": "test-cpp-app",
        "logs": [
            _make_cpp_log_payload(
                level="ERROR",
                message="Segmentation fault",
                file_path="/src/renderer.cpp",
                line_no=128,
                exception_type="std::runtime_error",
                stacktrace="#0  0x00007f8b4c123456 in renderer::draw()",
            )
        ],
    }

    resp = client.post("/logs/ingest", json=payload)
    assert resp.status_code == 202

    log = dummy.batches[0].logs[0]
    assert log.file_path == "/src/renderer.cpp"
    assert log.line_no == 128
    assert log.exception_type == "std::runtime_error"
    assert log.stacktrace is not None


def test_cpp_logs_can_be_mixed_with_python_logs(monkeypatch):
    """Batch containing both C++ and Python logs validates correctly."""
    client = TestClient(app)
    dummy = DummyStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: dummy)

    payload = {
        "application_id": "mixed-app",
        "logs": [
            # Python log
            {
                "ts": time.time(),
                "level": "INFO",
                "message": "Python log message",
                "application_id": "mixed-app",
                "module_name": "python_module",
                "context": {"request_id": "req-123"},
            },
            # C++ log
            _make_cpp_log_payload(
                application_id="mixed-app",
                module_name="cpp_module",
                message="C++ log message",
            ),
        ],
    }

    resp = client.post("/logs/ingest", json=payload)
    assert resp.status_code == 202
    assert resp.json() == {"accepted": 2}

    batch = dummy.batches[0]
    assert len(batch.logs) == 2
    # Python log
    assert batch.logs[0].module_name == "python_module"
    assert "language" not in batch.logs[0].context
    # C++ log
    assert batch.logs[1].module_name == "cpp_module"
    assert batch.logs[1].context.get("language") == "cpp"


def test_cpp_log_without_service_name_validates(monkeypatch):
    """C++ log without service_name validates (it's optional)."""
    client = TestClient(app)
    dummy = DummyStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: dummy)

    payload = {
        "application_id": "test-cpp-app",
        "logs": [
            _make_cpp_log_payload(service_name=None)  # Remove service_name
        ],
    }
    # Remove service_name from the dict if it was set to None
    if "service_name" in payload["logs"][0] and payload["logs"][0]["service_name"] is None:
        del payload["logs"][0]["service_name"]

    resp = client.post("/logs/ingest", json=payload)
    assert resp.status_code == 202

    log = dummy.batches[0].logs[0]
    assert log.service_name is None
    assert log.context.get("language") == "cpp"


def test_cpp_log_with_extended_context(monkeypatch):
    """C++ log with extended context metadata validates."""
    client = TestClient(app)
    dummy = DummyStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: dummy)

    payload = {
        "application_id": "test-cpp-app",
        "logs": [
            _make_cpp_log_payload(
                context={
                    "language": "cpp",
                    "thread_id": "12345",
                    "process_id": "67890",
                    "compiler": "g++",
                    "build_config": "release",
                    "cpu_arch": "x86_64",
                }
            )
        ],
    }

    resp = client.post("/logs/ingest", json=payload)
    assert resp.status_code == 202

    log = dummy.batches[0].logs[0]
    context = log.context
    assert context["language"] == "cpp"
    assert context["compiler"] == "g++"
    assert context["build_config"] == "release"
    assert context["cpu_arch"] == "x86_64"

