"""
Tests for saved and templated analysis queries (Story 6.3).

These tests verify:
- Query creation, loading, listing, and deletion
- Parameter resolution with overrides
- CLI commands for query management
- API endpoints for query management
- Execution of saved queries via CLI and API
"""

import tempfile
import time
from pathlib import Path

import pytest
import yaml

from drtrace_service import saved_queries
from drtrace_service.saved_queries import (
    SavedQuery,
    delete_query,
    list_queries,
    load_query,
    resolve_query_params,
    save_query,
)


@pytest.fixture
def temp_queries_dir(monkeypatch):
    """Create a temporary directory for queries and set it as the queries directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        queries_dir = Path(tmpdir) / "queries"
        queries_dir.mkdir(parents=True)
        monkeypatch.setenv("DRTRACE_QUERIES_DIR", str(queries_dir))
        yield queries_dir


def test_save_and_load_query(temp_queries_dir):
    """Test saving and loading a query."""
    query = SavedQuery(
        name="test-query",
        description="Test query description",
        application_id="test-app",
        default_time_window_minutes=10,
        min_level="ERROR",
        module_names=["module1", "module2"],
        service_names=["service1"],
        limit=200,
        query_type="why",
    )

    save_query(query)
    loaded = load_query("test-query")

    assert loaded is not None
    assert loaded.name == "test-query"
    assert loaded.description == "Test query description"
    assert loaded.application_id == "test-app"
    assert loaded.default_time_window_minutes == 10
    assert loaded.min_level == "ERROR"
    assert loaded.module_names == ["module1", "module2"]
    assert loaded.service_names == ["service1"]
    assert loaded.limit == 200
    assert loaded.query_type == "why"


def test_load_nonexistent_query(temp_queries_dir):
    """Test loading a query that doesn't exist."""
    loaded = load_query("nonexistent")
    assert loaded is None


def test_list_queries(temp_queries_dir):
    """Test listing all saved queries."""
    query1 = SavedQuery(name="query1", application_id="app1", default_time_window_minutes=5)
    query2 = SavedQuery(name="query2", application_id="app2", default_time_window_minutes=10)

    save_query(query1)
    save_query(query2)

    queries = list_queries()
    assert len(queries) == 2
    names = {q.name for q in queries}
    assert names == {"query1", "query2"}


def test_delete_query(temp_queries_dir):
    """Test deleting a saved query."""
    query = SavedQuery(name="to-delete", application_id="app1")
    save_query(query)

    assert load_query("to-delete") is not None
    assert delete_query("to-delete") is True
    assert load_query("to-delete") is None
    assert delete_query("to-delete") is False


def test_resolve_query_params_with_defaults(temp_queries_dir):
    """Test resolving query parameters with defaults."""
    query = SavedQuery(
        name="default-query",
        application_id="default-app",
        default_time_window_minutes=5,
        min_level="ERROR",
        module_names=["mod1"],
        limit=100,
    )
    save_query(query)

    params = resolve_query_params("default-query")

    assert params["application_id"] == "default-app"
    assert params["min_level"] == "ERROR"
    assert params["module_names"] == ["mod1"]
    assert params["limit"] == 100
    assert params["query_type"] == "why"
    # Time window should be calculated
    assert params["start_ts"] < params["end_ts"]
    assert params["end_ts"] <= time.time()


def test_resolve_query_params_with_overrides(temp_queries_dir):
    """Test resolving query parameters with overrides."""
    query = SavedQuery(
        name="override-query",
        application_id="default-app",
        default_time_window_minutes=5,
        min_level="ERROR",
        module_names=["mod1"],
        limit=100,
    )
    save_query(query)

    params = resolve_query_params(
        "override-query",
        application_id="override-app",
        min_level="WARN",
        module_names=["mod2", "mod3"],
        limit=200,
        start_ts=1000.0,
        end_ts=2000.0,
    )

    assert params["application_id"] == "override-app"
    assert params["min_level"] == "WARN"
    assert params["module_names"] == ["mod2", "mod3"]
    assert params["limit"] == 200
    assert params["start_ts"] == 1000.0
    assert params["end_ts"] == 2000.0


def test_resolve_query_params_nonexistent(temp_queries_dir):
    """Test resolving parameters for a nonexistent query."""
    with pytest.raises(ValueError, match="not found"):
        resolve_query_params("nonexistent")


def test_query_file_format(temp_queries_dir):
    """Test that query files are saved in YAML format."""
    query = SavedQuery(
        name="yaml-test",
        description="YAML format test",
        application_id="app1",
        default_time_window_minutes=5,
    )
    save_query(query)

    file_path = saved_queries.get_query_file_path("yaml-test")
    assert file_path.exists()

    with open(file_path, "r") as f:
        data = yaml.safe_load(f)

    assert data["name"] == "yaml-test"
    assert data["description"] == "YAML format test"
    assert data["application_id"] == "app1"
    assert data["default_time_window_minutes"] == 5


def test_query_name_sanitization(temp_queries_dir):
    """Test that query names are sanitized for filenames."""
    query = SavedQuery(name="test/query@name", application_id="app1")
    save_query(query)

    file_path = saved_queries.get_query_file_path("test/query@name")
    # Name should be sanitized
    assert file_path.name.startswith("test_query_name")


def test_list_queries_empty(temp_queries_dir):
    """Test listing queries when none exist."""
    queries = list_queries()
    assert queries == []


def test_saved_query_defaults():
    """Test that SavedQuery has proper defaults."""
    query = SavedQuery(name="test", application_id="app1")

    assert query.description is None
    assert query.default_time_window_minutes == 5
    assert query.min_level is None
    assert query.module_names == []
    assert query.service_names == []
    assert query.limit == 100
    assert query.query_type == "why"


def test_cli_query_list(temp_queries_dir, monkeypatch):
    """Test CLI query list command."""
    from drtrace_service.__main__ import _run_query

    query = SavedQuery(name="cli-test", application_id="app1", description="CLI test")
    save_query(query)

    import sys
    from io import StringIO

    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        _run_query(["list"])
    except SystemExit:
        pass

    output = captured_output.getvalue()
    sys.stdout = old_stdout

    assert "cli-test" in output
    assert "app1" in output


def test_cli_query_create(temp_queries_dir):
    """Test CLI query create command."""
    import sys
    from io import StringIO

    from drtrace_service.__main__ import _run_query

    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        _run_query(["create", "--name", "cli-create", "--application-id", "app1"])
    except SystemExit:
        pass

    output = captured_output.getvalue()
    sys.stdout = old_stdout

    assert "created successfully" in output

    loaded = load_query("cli-create")
    assert loaded is not None
    assert loaded.application_id == "app1"


def test_cli_query_delete(temp_queries_dir):
    """Test CLI query delete command."""
    import sys
    from io import StringIO

    from drtrace_service.__main__ import _run_query

    query = SavedQuery(name="to-delete-cli", application_id="app1")
    save_query(query)

    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()

    try:
        _run_query(["delete", "--name", "to-delete-cli"])
    except SystemExit:
        pass

    output = captured_output.getvalue()
    sys.stdout = old_stdout

    assert "deleted successfully" in output
    assert load_query("to-delete-cli") is None


def test_api_list_queries(temp_queries_dir, monkeypatch):
    """Test API list queries endpoint."""
    from fastapi.testclient import TestClient

    from drtrace_service.api import app

    query = SavedQuery(name="api-test", application_id="app1")
    save_query(query)

    client = TestClient(app)
    resp = client.get("/queries")

    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "queries" in data["data"]
    assert len(data["data"]["queries"]) >= 1
    assert any(q["name"] == "api-test" for q in data["data"]["queries"])


def test_api_create_query(temp_queries_dir, monkeypatch):
    """Test API create query endpoint."""
    from fastapi.testclient import TestClient

    from drtrace_service.api import app

    client = TestClient(app)
    resp = client.post(
        "/queries",
        params={
            "name": "api-create",
            "application_id": "app1",
            "description": "API test",
            "default_time_window_minutes": 10,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["query"]["name"] == "api-create"
    assert data["data"]["query"]["application_id"] == "app1"

    loaded = load_query("api-create")
    assert loaded is not None


def test_api_get_query(temp_queries_dir, monkeypatch):
    """Test API get query endpoint."""
    from fastapi.testclient import TestClient

    from drtrace_service.api import app

    query = SavedQuery(name="api-get", application_id="app1")
    save_query(query)

    client = TestClient(app)
    resp = client.get("/queries/api-get")

    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["query"]["name"] == "api-get"


def test_api_get_nonexistent_query(temp_queries_dir, monkeypatch):
    """Test API get query endpoint for nonexistent query."""
    from fastapi.testclient import TestClient

    from drtrace_service.api import app

    client = TestClient(app)
    resp = client.get("/queries/nonexistent")

    assert resp.status_code == 404
    data = resp.json()
    assert "not found" in data["detail"]["message"].lower()


def test_api_delete_query(temp_queries_dir, monkeypatch):
    """Test API delete query endpoint."""
    from fastapi.testclient import TestClient

    from drtrace_service.api import app

    query = SavedQuery(name="api-delete", application_id="app1")
    save_query(query)

    client = TestClient(app)
    resp = client.delete("/queries/api-delete")

    assert resp.status_code == 200
    assert load_query("api-delete") is None


def test_api_analyze_with_query_why(temp_queries_dir, monkeypatch):
    """Test API analyze with saved query (why type)."""
    from fastapi.testclient import TestClient

    from drtrace_service import storage as storage_mod
    from drtrace_service.api import app
    from drtrace_service.models import LogRecord

    query = SavedQuery(
        name="api-why",
        application_id="test-app",
        default_time_window_minutes=5,
        query_type="why",
    )
    save_query(query)

    # Mock storage
    class DummyStorage(storage_mod.LogStorage):
        def write_batch(self, batch):  # type: ignore
            pass

        def query_time_range(
            self,
            start_ts,
            end_ts,
            application_id=None,
            module_name=None,
            service_name=None,
            limit=100,
        ):
            return [
                LogRecord(
                    ts=time.time(),
                    level="ERROR",
                    message="Test error",
                    application_id="test-app",
                    module_name="test",
                    context={},
                )
            ]

        def get_retention_cutoff(self, *args, **kwargs):  # type: ignore
            return 0.0

        def delete_older_than(self, *args, **kwargs):  # type: ignore
            return 0

        def delete_by_application(self, *args, **kwargs):  # type: ignore
            return 0

    monkeypatch.setattr(storage_mod, "get_storage", lambda: DummyStorage())

    client = TestClient(app)
    resp = client.get("/analysis/query/api-why")

    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "explanation" in data["data"]
    assert data["meta"]["query_name"] == "api-why"


def test_api_analyze_with_query_cross_module(temp_queries_dir, monkeypatch):
    """Test API analyze with saved query (cross-module type)."""
    from fastapi.testclient import TestClient

    from drtrace_service import storage as storage_mod
    from drtrace_service.api import app
    from drtrace_service.models import LogRecord

    query = SavedQuery(
        name="api-cross",
        application_id="test-app",
        default_time_window_minutes=5,
        query_type="cross-module",
    )
    save_query(query)

    # Mock storage
    class DummyStorage(storage_mod.LogStorage):
        def write_batch(self, batch):  # type: ignore
            pass

        def query_time_range(
            self,
            start_ts,
            end_ts,
            application_id=None,
            module_name=None,
            service_name=None,
            limit=100,
        ):
            return [
                LogRecord(
                    ts=time.time(),
                    level="ERROR",
                    message="Test error",
                    application_id="test-app",
                    module_name="test",
                    service_name="test-svc",
                    context={},
                )
            ]

        def get_retention_cutoff(self, *args, **kwargs):  # type: ignore
            return 0.0

        def delete_older_than(self, *args, **kwargs):  # type: ignore
            return 0

        def delete_by_application(self, *args, **kwargs):  # type: ignore
            return 0

    monkeypatch.setattr(storage_mod, "get_storage", lambda: DummyStorage())

    client = TestClient(app)
    resp = client.get("/analysis/query/api-cross")

    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "explanation" in data["data"]
    assert "components" in data["data"]
    assert data["meta"]["query_name"] == "api-cross"


def test_api_analyze_with_query_overrides(temp_queries_dir, monkeypatch):
    """Test API analyze with saved query and parameter overrides."""
    from fastapi.testclient import TestClient

    from drtrace_service import storage as storage_mod
    from drtrace_service.api import app

    query = SavedQuery(
        name="api-override",
        application_id="default-app",
        default_time_window_minutes=5,
        min_level="ERROR",
        query_type="why",
    )
    save_query(query)

    # Mock storage
    class DummyStorage(storage_mod.LogStorage):
        def write_batch(self, batch):  # type: ignore
            pass

        def query_time_range(
            self,
            start_ts,
            end_ts,
            application_id=None,
            module_name=None,
            service_name=None,
            limit=100,
        ):
            # Verify overrides were applied
            assert application_id == "override-app"
            # min_level is filtered in analyze_time_range, not in storage
            return []

        def get_retention_cutoff(self, *args, **kwargs):  # type: ignore
            return 0.0

        def delete_older_than(self, *args, **kwargs):  # type: ignore
            return 0

        def delete_by_application(self, *args, **kwargs):  # type: ignore
            return 0

    monkeypatch.setattr(storage_mod, "get_storage", lambda: DummyStorage())

    client = TestClient(app)
    resp = client.get(
        "/analysis/query/api-override",
        params={
            "application_id": "override-app",
            "min_level": "WARN",
        },
    )

    assert resp.status_code == 200

