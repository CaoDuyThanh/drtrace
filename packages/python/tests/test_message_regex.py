"""Tests for message_regex feature (Epic 11.1)."""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from drtrace_service import api
from drtrace_service.models import LogRecord


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(api.app)


class TestMessageRegexValidation:
    """Test message_regex parameter validation."""

    def test_message_contains_and_message_regex_both_provided_returns_400(self, client):
        """Should return 400 error if both message_contains and message_regex provided."""
        response = client.get(
            "/logs/query",
            params={
                "since": "1h",
                "message_contains": "error",
                "message_regex": "error|warning",
            },
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_PARAMS"
        assert "Cannot use both message_contains and message_regex" in data["detail"]["message"]

    def test_message_regex_too_long_returns_400(self, client):
        """Should return 400 if regex pattern exceeds 500 chars."""
        long_pattern = "a" * 501
        response = client.get(
            "/logs/query",
            params={"since": "1h", "message_regex": long_pattern},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_PATTERN"
        assert "too long" in data["detail"]["message"]

    def test_message_regex_invalid_syntax_returns_400(self, client):
        """Should return 400 if regex pattern has invalid syntax."""
        response = client.get(
            "/logs/query",
            params={"since": "1h", "message_regex": "([a-z"},  # Unclosed bracket
        )
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_PATTERN"
        assert "Invalid regex pattern" in data["detail"]["message"]

    def test_message_regex_valid_pattern_accepted(self, client):
        """Should accept valid regex patterns."""
        # Mock storage to return empty list
        with patch("drtrace_service.api.storage.get_storage") as mock_storage:
            mock_backend = MagicMock()
            mock_backend.query_time_range.return_value = []
            mock_storage.return_value = mock_backend

            response = client.get(
                "/logs/query",
                params={"since": "1h", "message_regex": "error|warning"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0


class TestMessageRegexQuery:
    """Test message_regex query execution."""

    def test_message_regex_passed_to_storage(self, client):
        """Should pass message_regex parameter to storage query_time_range."""
        with patch("drtrace_service.api.storage.get_storage") as mock_storage:
            mock_backend = MagicMock()
            mock_backend.query_time_range.return_value = []
            mock_storage.return_value = mock_backend

            client.get(
                "/logs/query",
                params={"since": "1h", "message_regex": "db|cache"},
            )

            # Verify storage was called with message_regex
            mock_backend.query_time_range.assert_called_once()
            call_kwargs = mock_backend.query_time_range.call_args[1]
            assert call_kwargs["message_regex"] == "db|cache"
            assert call_kwargs["message_contains"] is None

    def test_message_contains_passed_to_storage(self, client):
        """Should pass message_contains when provided (not regex)."""
        with patch("drtrace_service.api.storage.get_storage") as mock_storage:
            mock_backend = MagicMock()
            mock_backend.query_time_range.return_value = []
            mock_storage.return_value = mock_backend

            client.get(
                "/logs/query",
                params={"since": "1h", "message_contains": "error"},
            )

            call_kwargs = mock_backend.query_time_range.call_args[1]
            assert call_kwargs["message_contains"] == "error"
            assert call_kwargs["message_regex"] is None

    def test_neither_message_filter_provided(self, client):
        """Should accept query with neither message_contains nor message_regex."""
        with patch("drtrace_service.api.storage.get_storage") as mock_storage:
            mock_backend = MagicMock()
            mock_backend.query_time_range.return_value = []
            mock_storage.return_value = mock_backend

            response = client.get(
                "/logs/query",
                params={"since": "1h"},
            )
            assert response.status_code == 200
            call_kwargs = mock_backend.query_time_range.call_args[1]
            assert call_kwargs["message_contains"] is None
            assert call_kwargs["message_regex"] is None


class TestMessageRegexIntegration:
    """Integration tests with actual storage."""

    def test_message_regex_result_format_matches_substring(self, client):
        """Regex results should have same format as substring results."""
        with patch("drtrace_service.api.storage.get_storage") as mock_storage:
            mock_backend = MagicMock()
            test_record = LogRecord(
                ts=1000000.0,
                level="ERROR",
                message="Database connection error",
                application_id="test-app",
                service_name="api",
                module_name="db",
                file_path="db.py",
                line_no=42,
                exception_type=None,
                stacktrace=None,
                context={},
            )
            mock_backend.query_time_range.return_value = [test_record]
            mock_storage.return_value = mock_backend

            response = client.get(
                "/logs/query",
                params={"since": "1h", "message_regex": "error"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert len(data["results"]) == 1
            assert data["results"][0]["message"] == "Database connection error"

    def test_common_regex_patterns(self, client):
        """Should accept common regex patterns without error."""
        patterns = [
            r"error|warning",  # Alternation
            r"^\[ERROR\]",  # Start anchor
            r"timeout$",  # End anchor
            r"(db|cache).*timeout",  # Grouping and alternation
            r"\d{3}-\d{4}",  # Digit pattern
        ]

        with patch("drtrace_service.api.storage.get_storage") as mock_storage:
            mock_backend = MagicMock()
            mock_backend.query_time_range.return_value = []
            mock_storage.return_value = mock_backend

            for pattern in patterns:
                response = client.get(
                    "/logs/query",
                    params={"since": "1h", "message_regex": pattern},
                )
                assert response.status_code == 200, f"Pattern '{pattern}' rejected"


class TestAPIDocumentation:
    """Test that API documentation mentions message_regex."""

    def test_query_logs_endpoint_documents_message_regex(self):
        """API should document message_regex parameter."""
        openapi_schema = api.app.openapi()
        logs_query_params = openapi_schema["paths"]["/logs/query"]["get"]["parameters"]

        param_names = [p["name"] for p in logs_query_params]
        assert "message_regex" in param_names
        assert "message_contains" in param_names

        # Find message_regex parameter and check description
        regex_param = next(p for p in logs_query_params if p["name"] == "message_regex")
        assert "mutually exclusive" in regex_param["description"].lower() or \
               "regex" in regex_param["description"].lower()
