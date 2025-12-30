"""
Tests for the time-range analysis endpoint (Story 5.1).

These tests validate that the analysis endpoint correctly retrieves logs
for a time range with proper filtering and error handling.
"""

import time
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

from drtrace_service import ai_model as ai_model_mod  # type: ignore[import]
from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]
from drtrace_service.models import LogBatch, LogRecord  # type: ignore[import]


class AnalysisStorage(storage_mod.LogStorage):  # type: ignore[misc]
    """Storage that supports analysis queries."""

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
        limit: int = 100,
    ) -> List[LogRecord]:
        """Query records matching criteria."""
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
        results.sort(key=lambda r: r.ts, reverse=True)
        return results[:limit]

    def get_retention_cutoff(self, *args, **kwargs):  # type: ignore
        return 0.0

    def delete_older_than(self, *args, **kwargs):  # type: ignore
        return 0

    def delete_by_application(self, *args, **kwargs):  # type: ignore
        return 0


def _make_log(
    application_id: str = "test-app",
    level: str = "INFO",
    message: str = "Test log",
    module_name: str = "test_module",
    service_name: Optional[str] = None,
    ts: Optional[float] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Create a log payload."""
    base: Dict[str, Any] = {
        "ts": ts or time.time(),
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


def test_analysis_endpoint_returns_logs_for_time_range(monkeypatch):
    """
    AC 1: Successful analysis when logs exist.

    Given logs exist in storage for a given application_id within a time window,
    when I call the analysis endpoint, then it retrieves relevant logs and returns
    a structured JSON response.
    """
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Seed logs
    logs = [
        _make_log(
            application_id="test-app",
            message="Log 1",
            level="INFO",
            ts=base_time + 1.0,
        ),
        _make_log(
            application_id="test-app",
            message="Log 2",
            level="WARN",
            ts=base_time + 2.0,
        ),
        _make_log(
            application_id="test-app",
            message="Log 3",
            level="ERROR",
            ts=base_time + 3.0,
        ),
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query analysis endpoint
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/analysis/time-range?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}"
    )

    assert resp.status_code == 200
    data = resp.json()

    # Verify standard envelope format
    assert "data" in data
    assert "meta" in data
    assert "logs" in data["data"]
    assert isinstance(data["data"]["logs"], list)

    # Verify logs returned
    assert len(data["data"]["logs"]) == 3
    assert data["meta"]["count"] == 3
    assert data["meta"]["application_id"] == "test-app"
    assert data["meta"]["start_ts"] == start_ts
    assert data["meta"]["end_ts"] == end_ts


def test_analysis_endpoint_handles_empty_results_gracefully(monkeypatch):
    """
    AC 2: Graceful empty-result behavior.

    Given no logs exist for the requested time range,
    when I call the endpoint, then it responds successfully with an empty result
    and clearly indicates that no data was available.
    """
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Query with no logs in storage
    start_ts = time.time()
    end_ts = start_ts + 3600
    resp = client.get(
        f"/analysis/time-range?application_id=empty-app&start_ts={start_ts}&end_ts={end_ts}"
    )

    assert resp.status_code == 200  # Success, not an error
    data = resp.json()

    # Verify structure
    assert "data" in data
    assert "meta" in data
    assert data["data"]["logs"] == []
    assert data["meta"]["count"] == 0
    assert data["meta"].get("no_data") is True
    assert "message" in data["meta"]
    assert "no logs found" in data["meta"]["message"].lower()


def test_analysis_endpoint_validates_time_range(monkeypatch):
    """Invalid time range (start_ts >= end_ts) returns 400 error."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Invalid: start_ts >= end_ts
    resp = client.get(
        f"/analysis/time-range?application_id=test-app&start_ts={base_time + 10}&end_ts={base_time}"
    )

    assert resp.status_code == 400
    error = resp.json()
    assert "detail" in error
    assert error["detail"]["code"] == "INVALID_TIME_RANGE"
    assert "start_ts must be less than end_ts" in error["detail"]["message"]


def test_analysis_endpoint_validates_min_level(monkeypatch):
    """Invalid min_level returns 400 error."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Invalid level
    resp = client.get(
        f"/analysis/time-range?application_id=test-app&start_ts={base_time}&end_ts={base_time + 10}&min_level=INVALID"
    )

    assert resp.status_code == 400
    error = resp.json()
    assert "detail" in error
    assert error["detail"]["code"] == "INVALID_LEVEL"
    assert "min_level must be one of" in error["detail"]["message"]


def test_analysis_endpoint_filters_by_min_level(monkeypatch):
    """
    AC 3: Filter support - min_level filter.

    Given I provide min_level filter, when I call the endpoint,
    then results are restricted to logs at or above that level.
    """
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Seed logs with different levels
    logs = [
        _make_log(application_id="test-app", level="DEBUG", message="Debug log", ts=base_time + 1.0),
        _make_log(application_id="test-app", level="INFO", message="Info log", ts=base_time + 2.0),
        _make_log(application_id="test-app", level="WARN", message="Warn log", ts=base_time + 3.0),
        _make_log(application_id="test-app", level="ERROR", message="Error log", ts=base_time + 4.0),
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query with min_level=WARN (should return WARN and ERROR only)
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/analysis/time-range?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}&min_level=WARN"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["logs"]) == 2
    levels = {log["level"] for log in data["data"]["logs"]}
    assert "WARN" in levels
    assert "ERROR" in levels
    assert "DEBUG" not in levels
    assert "INFO" not in levels


def test_analysis_endpoint_filters_by_module_name(monkeypatch):
    """
    AC 3: Filter support - module_name filter.

    Given I provide module_name filter, when I call the endpoint,
    then only logs from that module are returned.
    """
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    logs = [
        _make_log(
            application_id="test-app",
            module_name="module_a",
            message="Module A log",
            ts=base_time + 1.0,
        ),
        _make_log(
            application_id="test-app",
            module_name="module_b",
            message="Module B log",
            ts=base_time + 2.0,
        ),
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query with module_name filter
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/analysis/time-range?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}&module_name=module_a"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["logs"]) == 1
    assert data["data"]["logs"][0]["module_name"] == "module_a"
    assert data["data"]["logs"][0]["message"] == "Module A log"


def test_analysis_endpoint_filters_by_service_name(monkeypatch):
    """
    AC 3: Filter support - service_name filter.

    Given I provide service_name filter, when I call the endpoint,
    then only logs from that service are returned.
    """
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    logs = [
        _make_log(
            application_id="test-app",
            service_name="service_a",
            message="Service A log",
            ts=base_time + 1.0,
        ),
        _make_log(
            application_id="test-app",
            service_name="service_b",
            message="Service B log",
            ts=base_time + 2.0,
        ),
        _make_log(
            application_id="test-app",
            service_name=None,  # No service_name
            message="No service log",
            ts=base_time + 3.0,
        ),
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query with service_name filter
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/analysis/time-range?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}&service_name=service_a"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["logs"]) == 1
    assert data["data"]["logs"][0]["service_name"] == "service_a"
    assert data["data"]["logs"][0]["message"] == "Service A log"


def test_analysis_endpoint_respects_limit(monkeypatch):
    """Limit parameter restricts the number of results returned."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Seed more logs than limit
    logs = [
        _make_log(application_id="test-app", message=f"Log {i}", ts=base_time + i)
        for i in range(1, 11)
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query with limit=5
    start_ts = base_time
    end_ts = base_time + 20.0
    resp = client.get(
        f"/analysis/time-range?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}&limit=5"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["logs"]) == 5
    assert data["meta"]["count"] == 5


def test_analysis_endpoint_combines_filters(monkeypatch):
    """Multiple filters can be combined."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    logs = [
        _make_log(
            application_id="test-app",
            module_name="target_module",
            service_name="target_service",
            level="ERROR",
            message="Target log",
            ts=base_time + 1.0,
        ),
        _make_log(
            application_id="test-app",
            module_name="target_module",
            service_name="target_service",
            level="INFO",  # Wrong level
            message="Wrong level",
            ts=base_time + 2.0,
        ),
        _make_log(
            application_id="test-app",
            module_name="other_module",  # Wrong module
            service_name="target_service",
            level="ERROR",
            message="Wrong module",
            ts=base_time + 3.0,
        ),
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query with combined filters
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/analysis/time-range?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}&module_name=target_module&service_name=target_service&min_level=ERROR"
    )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]["logs"]) == 1
    assert data["data"]["logs"][0]["message"] == "Target log"
    assert data["data"]["logs"][0]["level"] == "ERROR"


def test_analysis_endpoint_requires_application_id(monkeypatch):
    """application_id is required."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Missing application_id
    resp = client.get(
        f"/analysis/time-range?start_ts={base_time}&end_ts={base_time + 10}"
    )

    assert resp.status_code == 422  # FastAPI validation error


def test_analysis_endpoint_requires_time_range(monkeypatch):
    """start_ts and end_ts are required."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Missing time range
    resp = client.get("/analysis/time-range?application_id=test-app")

    assert resp.status_code == 422  # FastAPI validation error


def test_why_endpoint_returns_explanation(monkeypatch):
    """Test that /analysis/why endpoint generates and returns root-cause explanation."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Mock AI model to return predictable response
    class MockAIModel:
        def generate_explanation(self, prompt, **kwargs):
            return """Summary: Test error occurred.
Root Cause: Test root cause analysis.
Key Evidence:
- Error log shows test error
- Code at line 42 has issue
Suggested Fixes:
- Fix the issue
- Add validation
Confidence: High"""

    mock_model = MockAIModel()
    monkeypatch.setattr(ai_model_mod, "get_ai_model", lambda: mock_model)

    base_time = time.time()

    # Seed error log
    error_log = _make_log(
        application_id="test-app",
        message="Test error",
        level="ERROR",
        file_path="src/test.py",
        line_no=42,
        ts=base_time + 1.0,
    )
    client.post("/logs/ingest", json={"application_id": "test-app", "logs": [error_log]})

    # Call why endpoint
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/analysis/why?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}"
    )

    assert resp.status_code == 200
    data = resp.json()

    # Verify structure
    assert "data" in data
    assert "meta" in data
    assert "explanation" in data["data"]

    explanation = data["data"]["explanation"]
    # Verify structure exists (parser may have variations in extraction)
    assert "summary" in explanation
    assert "root_cause" in explanation
    assert "key_evidence" in explanation
    assert "suggested_fixes" in explanation
    assert "confidence" in explanation
    assert "evidence_references" in explanation
    # Evidence references should be present if we have error logs
    assert len(explanation["evidence_references"]) > 0
    # Summary and root_cause should have content (even if fallback)
    assert len(explanation["summary"]) > 0
    assert len(explanation["root_cause"]) > 0


def test_why_endpoint_handles_no_data(monkeypatch):
    """Test that /analysis/why endpoint handles no logs gracefully."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()
    start_ts = base_time
    end_ts = base_time + 10.0

    resp = client.get(
        f"/analysis/why?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}"
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["data"]["explanation"] is None
    assert data["data"]["message"] == "No logs found for the specified time range and filters"
    assert data["meta"]["no_data"] is True
    assert data["meta"]["count"] == 0


def test_why_endpoint_validates_time_range(monkeypatch):
    """Test that /analysis/why endpoint validates time range."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Invalid: start >= end
    resp = client.get(
        f"/analysis/why?application_id=test-app&start_ts={base_time + 10.0}&end_ts={base_time}"
    )

    assert resp.status_code == 400
    error = resp.json()
    assert error["detail"]["code"] == "INVALID_TIME_RANGE"


def test_why_endpoint_validates_min_level(monkeypatch):
    """Test that /analysis/why endpoint validates min_level."""
    client = TestClient(app)
    storage = AnalysisStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Invalid min_level
    resp = client.get(
        f"/analysis/why?application_id=test-app&start_ts={base_time}&end_ts={base_time + 10.0}&min_level=INVALID"
    )

    assert resp.status_code == 400
    error = resp.json()
    assert error["detail"]["code"] == "INVALID_LEVEL"

