"""
Tests for cross-module/service analysis (Story 6.1).

These tests verify:
- Querying logs across multiple services/modules
- Component-level context in responses
- Filtering by lists of service/module names
- Component breakdown in analysis results
"""

import time
from typing import Any, Dict, List, Optional

from fastapi.testclient import TestClient

from drtrace_service import ai_model as ai_model_mod  # type: ignore[import]
from drtrace_service import analysis as analysis_mod  # type: ignore[import]
from drtrace_service import storage as storage_mod  # type: ignore[import]
from drtrace_service.api import app  # type: ignore[import]
from drtrace_service.models import LogBatch, LogRecord  # type: ignore[import]


class CrossModuleStorage(storage_mod.LogStorage):  # type: ignore[misc]
    """Storage that supports cross-module queries."""

    def __init__(self):
        self.all_records: List[LogRecord] = []

    def write_batch(self, batch: LogBatch) -> None:
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
        """Query records matching criteria, supporting lists for module_name and service_name."""
        results: List[LogRecord] = []
        for record in self.all_records:
            if record.ts < start_ts or record.ts > end_ts:
                continue
            if application_id and record.application_id != application_id:
                continue

            # Handle list or single value for module_name
            if module_name is not None:
                if isinstance(module_name, list):
                    if record.module_name not in module_name:
                        continue
                else:
                    if record.module_name != module_name:
                        continue

            # Handle list or single value for service_name
            if service_name is not None:
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


def test_cross_module_endpoint_accepts_module_lists(monkeypatch):
    """Test that /analysis/cross-module accepts lists of module names."""
    client = TestClient(app)
    storage = CrossModuleStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Mock AI model
    class MockAIModel:
        def generate_explanation(self, prompt, **kwargs):
            return "Summary: Test\nRoot Cause: Test cause"

    mock_model = MockAIModel()
    monkeypatch.setattr(ai_model_mod, "get_ai_model", lambda: mock_model)

    base_time = time.time()

    # Seed logs from multiple modules
    logs = [
        _make_log(
            application_id="test-app",
            module_name="module_a",
            service_name="service_1",
            message="Log from module_a",
            ts=base_time + 1.0,
        ),
        _make_log(
            application_id="test-app",
            module_name="module_b",
            service_name="service_1",
            message="Log from module_b",
            ts=base_time + 2.0,
        ),
        _make_log(
            application_id="test-app",
            module_name="module_c",
            service_name="service_2",
            message="Log from module_c",
            ts=base_time + 3.0,
        ),
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query with multiple modules
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/analysis/cross-module?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}&module_names=module_a&module_names=module_b"
    )

    assert resp.status_code == 200
    data = resp.json()

    # Verify structure
    assert "data" in data
    assert "meta" in data
    assert "components" in data["data"]
    assert "logs_by_component" in data["data"]

    # Verify component breakdown
    components = data["data"]["components"]
    assert "modules" in components
    assert "module_a" in components["modules"]
    assert "module_b" in components["modules"]
    assert "module_c" not in components["modules"]  # Should be filtered out


def test_cross_module_endpoint_accepts_service_lists(monkeypatch):
    """Test that /analysis/cross-module accepts lists of service names."""
    client = TestClient(app)
    storage = CrossModuleStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Mock AI model
    class MockAIModel:
        def generate_explanation(self, prompt, **kwargs):
            return "Summary: Test\nRoot Cause: Test cause"

    mock_model = MockAIModel()
    monkeypatch.setattr(ai_model_mod, "get_ai_model", lambda: mock_model)

    base_time = time.time()

    # Seed logs from multiple services
    logs = [
        _make_log(
            application_id="test-app",
            module_name="module_a",
            service_name="service_1",
            message="Log from service_1",
            ts=base_time + 1.0,
        ),
        _make_log(
            application_id="test-app",
            module_name="module_b",
            service_name="service_2",
            message="Log from service_2",
            ts=base_time + 2.0,
        ),
        _make_log(
            application_id="test-app",
            module_name="module_c",
            service_name="service_3",
            message="Log from service_3",
            ts=base_time + 3.0,
        ),
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    # Query with multiple services
    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/analysis/cross-module?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}&service_names=service_1&service_names=service_2"
    )

    assert resp.status_code == 200
    data = resp.json()

    # Verify component breakdown
    components = data["data"]["components"]
    assert "services" in components
    assert "service_1" in components["services"]
    assert "service_2" in components["services"]
    assert "service_3" not in components["services"]  # Should be filtered out


def test_cross_module_endpoint_returns_component_context(monkeypatch):
    """Test that response includes component-level context."""
    client = TestClient(app)
    storage = CrossModuleStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Mock AI model
    class MockAIModel:
        def generate_explanation(self, prompt, **kwargs):
            return "Summary: Test\nRoot Cause: Test cause"

    mock_model = MockAIModel()
    monkeypatch.setattr(ai_model_mod, "get_ai_model", lambda: mock_model)

    base_time = time.time()

    # Seed logs from multiple components
    logs = [
        _make_log(
            application_id="test-app",
            module_name="module_a",
            service_name="service_1",
            level="ERROR",
            message="Error in module_a",
            ts=base_time + 1.0,
        ),
        _make_log(
            application_id="test-app",
            module_name="module_b",
            service_name="service_2",
            level="WARN",
            message="Warning in module_b",
            ts=base_time + 2.0,
        ),
    ]

    for log in logs:
        client.post("/logs/ingest", json={"application_id": "test-app", "logs": [log]})

    start_ts = base_time
    end_ts = base_time + 10.0
    resp = client.get(
        f"/analysis/cross-module?application_id=test-app&start_ts={start_ts}&end_ts={end_ts}"
    )

    assert resp.status_code == 200
    data = resp.json()

    # Verify component context
    assert "components" in data["data"]
    components = data["data"]["components"]
    assert "services" in components
    assert "modules" in components
    assert "total_components" in components

    # Verify logs_by_component
    assert "logs_by_component" in data["data"]
    logs_by_component = data["data"]["logs_by_component"]
    assert isinstance(logs_by_component, dict)

    # Verify meta includes components
    assert "components" in data["meta"]


def test_cross_module_analysis_function(monkeypatch):
    """Test analyze_cross_module_incident function directly."""
    storage = CrossModuleStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Mock AI model
    class MockAIModel:
        def generate_explanation(self, prompt, **kwargs):
            return "Summary: Test\nRoot Cause: Test cause"

    mock_model = MockAIModel()
    monkeypatch.setattr(ai_model_mod, "get_ai_model", lambda: mock_model)

    base_time = time.time()

    # Create logs
    logs = [
        LogRecord(
            ts=base_time + 1.0,
            level="ERROR",
            message="Error in service_1",
            application_id="test-app",
            module_name="module_a",
            service_name="service_1",
            context={},
        ),
        LogRecord(
            ts=base_time + 2.0,
            level="WARN",
            message="Warning in service_2",
            application_id="test-app",
            module_name="module_b",
            service_name="service_2",
            context={},
        ),
    ]

    # Write logs
    batch = LogBatch(application_id="test-app", logs=logs)
    storage.write_batch(batch)

    # Analyze
    result = analysis_mod.analyze_cross_module_incident(
        application_id="test-app",
        start_ts=base_time,
        end_ts=base_time + 10.0,
        module_names=["module_a", "module_b"],
        service_names=["service_1", "service_2"],
    )

    # Verify result structure
    assert result.explanation is not None
    assert result.components is not None
    assert "services" in result.components
    assert "modules" in result.components
    assert "total_components" in result.components

    # Verify component counts
    assert result.components["services"]["service_1"] == 1
    assert result.components["services"]["service_2"] == 1
    assert result.components["modules"]["module_a"] == 1
    assert result.components["modules"]["module_b"] == 1

    # Verify logs_by_component
    assert len(result.logs_by_component) > 0
    assert "service:service_1" in result.logs_by_component
    assert "service:service_2" in result.logs_by_component
    assert "module:module_a" in result.logs_by_component
    assert "module:module_b" in result.logs_by_component


def test_cross_module_analysis_filters_correctly(monkeypatch):
    """Test that cross-module analysis filters to specified components only."""
    storage = CrossModuleStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    # Mock AI model
    class MockAIModel:
        def generate_explanation(self, prompt, **kwargs):
            return "Summary: Test\nRoot Cause: Test cause"

    mock_model = MockAIModel()
    monkeypatch.setattr(ai_model_mod, "get_ai_model", lambda: mock_model)

    base_time = time.time()

    # Create logs from multiple components
    logs = [
        LogRecord(
            ts=base_time + 1.0,
            level="ERROR",
            message="Error in module_a",
            application_id="test-app",
            module_name="module_a",
            service_name="service_1",
            context={},
        ),
        LogRecord(
            ts=base_time + 2.0,
            level="ERROR",
            message="Error in module_b",
            application_id="test-app",
            module_name="module_b",
            service_name="service_2",
            context={},
        ),
        LogRecord(
            ts=base_time + 3.0,
            level="ERROR",
            message="Error in module_c",
            application_id="test-app",
            module_name="module_c",
            service_name="service_3",
            context={},
        ),
    ]

    batch = LogBatch(application_id="test-app", logs=logs)
    storage.write_batch(batch)

    # Analyze with only module_a and module_b
    result = analysis_mod.analyze_cross_module_incident(
        application_id="test-app",
        start_ts=base_time,
        end_ts=base_time + 10.0,
        module_names=["module_a", "module_b"],
    )

    # Verify only specified modules are included
    assert "module_a" in result.components["modules"]
    assert "module_b" in result.components["modules"]
    assert "module_c" not in result.components["modules"]


def test_cross_module_analysis_handles_empty_results(monkeypatch):
    """Test that cross-module analysis handles no data gracefully."""
    storage = CrossModuleStorage()
    monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

    base_time = time.time()

    # Analyze with no logs
    result = analysis_mod.analyze_cross_module_incident(
        application_id="test-app",
        start_ts=base_time,
        end_ts=base_time + 10.0,
        module_names=["module_a"],
    )

    # Verify empty result structure
    assert result.explanation is not None
    assert "No logs found" in result.explanation.summary
    assert result.components == {"services": {}, "modules": {}}
    assert result.logs_by_component == {}

