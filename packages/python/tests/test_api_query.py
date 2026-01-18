"""
Tests for API query improvements (Stories API-1 through API-4, Epic 11.1).

These tests validate the new API features:
- Story API-1: Human-readable timestamps (since/until)
- Story API-2: Message text search (message_contains)
- Story API-3: min_level filter
- Story API-4: Cursor-based pagination
- Epic 11.1: Regex message search (message_regex)
"""

import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from drtrace_service import storage as storage_mod
from drtrace_service.api import app, decode_cursor, encode_cursor, parse_time_param
from drtrace_service.models import LogBatch, LogRecord

# ============================================
# Mock Storage for Testing
# ============================================

class ApiTestStorage(storage_mod.LogStorage):
    """Storage that supports all new query params for API testing."""

    def __init__(self):
        self.records: List[LogRecord] = []

    def write_batch(self, batch: LogBatch) -> None:
        self.records.extend(batch.logs)

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
        after_cursor: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> List[LogRecord]:
        """Query records with all API-1 through API-4 and Epic 11.1 filters."""
        level_order = {"DEBUG": 0, "INFO": 1, "WARN": 2, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}
        results: List[LogRecord] = []

        for r in self.records:
            # Time range filter
            if r.ts < start_ts or r.ts > end_ts:
                continue
            # Application ID filter
            if application_id and r.application_id != application_id:
                continue
            # Module name filter
            if module_name:
                if isinstance(module_name, list):
                    if r.module_name not in module_name:
                        continue
                elif r.module_name != module_name:
                    continue
            # Service name filter
            if service_name:
                if isinstance(service_name, list):
                    if r.service_name not in service_name:
                        continue
                elif r.service_name != service_name:
                    continue
            # Message contains filter (Story API-2)
            if message_contains:
                if message_contains.lower() not in (r.message or "").lower():
                    continue
            # Message regex filter (Epic 11.1)
            if message_regex:
                if not re.search(message_regex, r.message or "", re.IGNORECASE):
                    continue
            # Min level filter (Story API-3)
            if min_level:
                min_order = level_order.get(min_level.upper(), 0)
                record_order = level_order.get((r.level or "").upper(), 0)
                if record_order < min_order:
                    continue
            # Cursor pagination (Story API-4)
            if after_cursor:
                cursor_ts = after_cursor.get("ts")
                if cursor_ts is not None and r.ts >= cursor_ts:
                    continue
            results.append(r)

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda r: r.ts, reverse=True)
        return results[:limit]

    def get_retention_cutoff(self, *args, **kwargs):
        return 0.0

    def delete_older_than(self, *args, **kwargs):
        return 0

    def delete_by_application(self, *args, **kwargs):
        return 0


# ============================================
# Unit Tests for parse_time_param
# ============================================

class TestParseTimeParam:
    """Unit tests for the parse_time_param function (Story API-1)."""

    def test_relative_time_seconds(self):
        """Test parsing relative time in seconds."""
        now = time.time()
        result = parse_time_param("30s")
        assert abs(result - (now - 30)) < 1  # Within 1 second tolerance

    def test_relative_time_minutes(self):
        """Test parsing relative time in minutes."""
        now = time.time()
        result = parse_time_param("5m")
        assert abs(result - (now - 300)) < 1

    def test_relative_time_hours(self):
        """Test parsing relative time in hours."""
        now = time.time()
        result = parse_time_param("2h")
        assert abs(result - (now - 7200)) < 1

    def test_relative_time_days(self):
        """Test parsing relative time in days."""
        now = time.time()
        result = parse_time_param("1d")
        assert abs(result - (now - 86400)) < 1

    def test_relative_time_case_insensitive(self):
        """Test relative time is case-insensitive."""
        result1 = parse_time_param("5M")
        result2 = parse_time_param("5m")
        assert abs(result1 - result2) < 1

    def test_iso_8601_without_timezone(self):
        """Test ISO 8601 without timezone (interpreted as UTC)."""
        result = parse_time_param("2025-12-31T02:44:03")
        expected = datetime(2025, 12, 31, 2, 44, 3, tzinfo=timezone.utc).timestamp()
        assert result == expected

    def test_iso_8601_with_timezone(self):
        """Test ISO 8601 with timezone offset."""
        result = parse_time_param("2025-12-31T09:44:03+07:00")
        # 09:44:03+07:00 = 02:44:03 UTC
        expected = datetime(2025, 12, 31, 2, 44, 3, tzinfo=timezone.utc).timestamp()
        assert result == expected

    def test_unix_timestamp_float(self):
        """Test Unix timestamp as float."""
        result = parse_time_param("1767149043.5")
        assert result == 1767149043.5

    def test_unix_timestamp_integer(self):
        """Test Unix timestamp as integer."""
        result = parse_time_param("1767149043")
        assert result == 1767149043.0

    def test_unix_timestamp_integer_is_end(self):
        """Test integer timestamp with is_end=True adds 0.999999."""
        result = parse_time_param("1767149043", is_end=True)
        assert result == 1767149043.999999

    def test_invalid_format_raises(self):
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            parse_time_param("invalid")
        assert "Cannot parse time" in str(excinfo.value)


# ============================================
# Unit Tests for Cursor Encoding/Decoding
# ============================================

class TestCursorEncoding:
    """Unit tests for cursor encode/decode (Story API-4)."""

    def test_encode_cursor(self):
        """Test cursor encoding."""
        cursor = encode_cursor(1234567890.123, "abc123")
        assert isinstance(cursor, str)
        assert len(cursor) > 0

    def test_decode_cursor(self):
        """Test cursor decoding."""
        cursor = encode_cursor(1234567890.123, "abc123")
        decoded = decode_cursor(cursor)
        assert decoded["ts"] == 1234567890.123
        assert decoded["id"] == "abc123"

    def test_decode_invalid_cursor(self):
        """Test invalid cursor raises ValueError."""
        with pytest.raises(ValueError) as excinfo:
            decode_cursor("invalid_cursor_data")
        assert "Invalid cursor" in str(excinfo.value)

    def test_roundtrip(self):
        """Test encode/decode roundtrip."""
        ts = 1767149043.5
        record_id = "test-id-123"
        cursor = encode_cursor(ts, record_id)
        decoded = decode_cursor(cursor)
        assert decoded["ts"] == ts
        assert decoded["id"] == record_id


# ============================================
# API Integration Tests - Time Parsing
# ============================================

class TestTimeParsingAPI:
    """API tests for human-readable timestamp support (Story API-1)."""

    def test_since_relative_5m(self, monkeypatch):
        """Test ?since=5m returns logs from last 5 minutes."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        # Add logs: one recent, one old
        storage.records = [
            LogRecord(ts=now - 60, level="INFO", message="Recent", application_id="test", module_name="test"),
            LogRecord(ts=now - 600, level="INFO", message="Old", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=5m&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        # Only the recent log (within 5 minutes) should be returned
        assert data["count"] == 1
        assert data["results"][0]["message"] == "Recent"

    def test_since_relative_1h(self, monkeypatch):
        """Test ?since=1h returns logs from last hour."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 1800, level="INFO", message="30min ago", application_id="test", module_name="test"),
            LogRecord(ts=now - 7200, level="INFO", message="2h ago", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=1h&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["message"] == "30min ago"

    def test_since_and_until(self, monkeypatch):
        """Test ?since=1h&until=30m returns logs between 1h and 30m ago."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 600, level="INFO", message="10min ago", application_id="test", module_name="test"),
            LogRecord(ts=now - 2700, level="INFO", message="45min ago", application_id="test", module_name="test"),
            LogRecord(ts=now - 5400, level="INFO", message="90min ago", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=1h&until=30m&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        # Only "45min ago" should be between 1h and 30m ago
        assert data["count"] == 1
        assert data["results"][0]["message"] == "45min ago"

    def test_iso_timestamp(self, monkeypatch):
        """Test ISO 8601 timestamp."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        # Use a fixed timestamp
        target_time = datetime(2025, 12, 31, 2, 0, 0, tzinfo=timezone.utc)
        storage.records = [
            LogRecord(ts=target_time.timestamp() + 60, level="INFO", message="After target", application_id="test", module_name="test"),
        ]

        iso_since = "2025-12-31T02:00:00"
        iso_until = "2025-12-31T02:05:00"
        resp = client.get(f"/logs/query?since={iso_since}&until={iso_until}&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_backward_compatible_start_ts_end_ts(self, monkeypatch):
        """Test legacy start_ts/end_ts params still work."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 60, level="INFO", message="Test", application_id="test", module_name="test"),
        ]

        resp = client.get(f"/logs/query?start_ts={now - 300}&end_ts={now}&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

    def test_default_time_range_5_minutes(self, monkeypatch):
        """Test default is last 5 minutes when no time specified."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 60, level="INFO", message="Recent", application_id="test", module_name="test"),
            LogRecord(ts=now - 600, level="INFO", message="Old", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        # Only the recent log (within 5 minutes) should be returned
        assert data["count"] == 1
        assert data["results"][0]["message"] == "Recent"

    def test_invalid_time_format_returns_400(self, monkeypatch):
        """Test invalid time format returns 400."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        resp = client.get("/logs/query?since=invalid_time")
        assert resp.status_code == 400
        assert "INVALID_TIME_FORMAT" in resp.json()["detail"]["code"]


# ============================================
# API Integration Tests - Message Search
# ============================================

class TestMessageSearchAPI:
    """API tests for message_contains filter (Story API-2)."""

    def test_message_contains_basic(self, monkeypatch):
        """Test basic substring search."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="ERROR", message="Connection timeout error", application_id="test", module_name="test"),
            LogRecord(ts=now - 20, level="INFO", message="Request successful", application_id="test", module_name="test"),
            LogRecord(ts=now - 30, level="WARN", message="Timeout warning", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=5m&message_contains=timeout&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        for log in data["results"]:
            assert "timeout" in log["message"].lower()

    def test_message_contains_case_insensitive(self, monkeypatch):
        """Test search is case-insensitive."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="ERROR", message="TIMEOUT Error", application_id="test", module_name="test"),
            LogRecord(ts=now - 20, level="INFO", message="timeout warning", application_id="test", module_name="test"),
        ]

        resp_upper = client.get("/logs/query?since=5m&message_contains=TIMEOUT&application_id=test")
        resp_lower = client.get("/logs/query?since=5m&message_contains=timeout&application_id=test")
        assert resp_upper.status_code == 200
        assert resp_lower.status_code == 200
        assert resp_upper.json()["count"] == resp_lower.json()["count"] == 2

    def test_message_contains_special_chars(self, monkeypatch):
        """Test search with special characters like [E]."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="ERROR", message="[E] Critical error", application_id="test", module_name="test"),
            LogRecord(ts=now - 20, level="INFO", message="Normal log", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=5m&message_contains=[E]&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert "[E]" in data["results"][0]["message"]

    def test_message_contains_no_match(self, monkeypatch):
        """Test search with no matching logs returns empty."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="INFO", message="Normal log", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=5m&message_contains=nonexistent123&application_id=test")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


# ============================================
# API Integration Tests - Min Level Filter
# ============================================

class TestMinLevelFilterAPI:
    """API tests for min_level filter (Story API-3)."""

    def test_min_level_error(self, monkeypatch):
        """Test min_level=ERROR returns only ERROR and CRITICAL."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="DEBUG", message="Debug", application_id="test", module_name="test"),
            LogRecord(ts=now - 20, level="INFO", message="Info", application_id="test", module_name="test"),
            LogRecord(ts=now - 30, level="WARN", message="Warn", application_id="test", module_name="test"),
            LogRecord(ts=now - 40, level="ERROR", message="Error", application_id="test", module_name="test"),
            LogRecord(ts=now - 50, level="CRITICAL", message="Critical", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=5m&min_level=ERROR&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        for log in data["results"]:
            assert log["level"].upper() in ["ERROR", "CRITICAL"]

    def test_min_level_warn(self, monkeypatch):
        """Test min_level=WARN returns WARN, ERROR, CRITICAL."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="DEBUG", message="Debug", application_id="test", module_name="test"),
            LogRecord(ts=now - 20, level="INFO", message="Info", application_id="test", module_name="test"),
            LogRecord(ts=now - 30, level="WARN", message="Warn", application_id="test", module_name="test"),
            LogRecord(ts=now - 40, level="ERROR", message="Error", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=5m&min_level=WARN&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        for log in data["results"]:
            assert log["level"].upper() in ["WARN", "WARNING", "ERROR", "CRITICAL"]

    def test_min_level_info(self, monkeypatch):
        """Test min_level=INFO returns INFO, WARN, ERROR, CRITICAL."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="DEBUG", message="Debug", application_id="test", module_name="test"),
            LogRecord(ts=now - 20, level="INFO", message="Info", application_id="test", module_name="test"),
            LogRecord(ts=now - 30, level="ERROR", message="Error", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=5m&min_level=INFO&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2  # INFO and ERROR

    def test_min_level_case_insensitive(self, monkeypatch):
        """Test min_level is case-insensitive."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="ERROR", message="Error", application_id="test", module_name="test"),
        ]

        resp_upper = client.get("/logs/query?since=5m&min_level=ERROR&application_id=test")
        resp_lower = client.get("/logs/query?since=5m&min_level=error&application_id=test")
        resp_mixed = client.get("/logs/query?since=5m&min_level=Error&application_id=test")
        assert resp_upper.status_code == 200
        assert resp_lower.status_code == 200
        assert resp_mixed.status_code == 200
        assert resp_upper.json()["count"] == resp_lower.json()["count"] == resp_mixed.json()["count"]

    def test_min_level_invalid_returns_400(self, monkeypatch):
        """Test invalid level returns 400."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        resp = client.get("/logs/query?since=5m&min_level=INVALID")
        assert resp.status_code == 400
        assert "INVALID_LEVEL" in resp.json()["detail"]["code"]


# ============================================
# API Integration Tests - Pagination
# ============================================

class TestPaginationAPI:
    """API tests for cursor-based pagination (Story API-4)."""

    def test_has_more_true_when_more_results(self, monkeypatch):
        """Test has_more=true when more results available."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        # Create 150 logs
        storage.records = [
            LogRecord(ts=now - i, level="INFO", message=f"Log {i}", application_id="test", module_name="test")
            for i in range(150)
        ]

        resp = client.get("/logs/query?since=5m&limit=100&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_more"] is True
        assert data["next_cursor"] is not None
        assert data["count"] == 100

    def test_has_more_false_on_last_page(self, monkeypatch):
        """Test has_more=false on last page."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        # Create 50 logs (less than limit)
        storage.records = [
            LogRecord(ts=now - i, level="INFO", message=f"Log {i}", application_id="test", module_name="test")
            for i in range(50)
        ]

        resp = client.get("/logs/query?since=5m&limit=100&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_more"] is False
        assert data["next_cursor"] is None
        assert data["count"] == 50

    def test_cursor_pagination_works(self, monkeypatch):
        """Test cursor from first page works for second page."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        # Create 150 logs
        storage.records = [
            LogRecord(ts=now - i, level="INFO", message=f"Log {i}", application_id="test", module_name="test")
            for i in range(150)
        ]

        # Get first page
        resp1 = client.get("/logs/query?since=5m&limit=100&application_id=test")
        assert resp1.status_code == 200
        data1 = resp1.json()
        cursor = data1["next_cursor"]
        assert cursor is not None

        # Get second page
        resp2 = client.get(f"/logs/query?since=5m&limit=100&cursor={cursor}&application_id=test")
        assert resp2.status_code == 200
        data2 = resp2.json()
        # Second page should have remaining 50 logs
        assert data2["count"] == 50
        assert data2["has_more"] is False

    def test_no_duplicates_between_pages(self, monkeypatch):
        """Test no duplicate records between pages."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        # Create 100 logs
        storage.records = [
            LogRecord(ts=now - i, level="INFO", message=f"Log {i}", application_id="test", module_name="test")
            for i in range(100)
        ]

        # Get first page
        resp1 = client.get("/logs/query?since=5m&limit=50&application_id=test")
        data1 = resp1.json()
        page1_ts = {log["ts"] for log in data1["results"]}
        cursor = data1["next_cursor"]

        # Get second page
        resp2 = client.get(f"/logs/query?since=5m&limit=50&cursor={cursor}&application_id=test")
        data2 = resp2.json()
        page2_ts = {log["ts"] for log in data2["results"]}

        # No overlap between pages
        assert page1_ts.isdisjoint(page2_ts)

    def test_invalid_cursor_returns_400(self, monkeypatch):
        """Test invalid cursor returns 400."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        resp = client.get("/logs/query?since=5m&cursor=invalid_cursor_data")
        assert resp.status_code == 400
        assert "INVALID_CURSOR" in resp.json()["detail"]["code"]

    def test_response_format_includes_pagination_fields(self, monkeypatch):
        """Test response includes has_more and next_cursor fields."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="INFO", message="Test", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=5m&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert "has_more" in data
        assert "next_cursor" in data
        assert "results" in data
        assert "count" in data


# ============================================
# API Integration Tests - Combined Filters
# ============================================

class TestCombinedFiltersAPI:
    """API tests for multiple filters combined."""

    def test_level_and_message(self, monkeypatch):
        """Test min_level + message_contains."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="ERROR", message="Connection timeout", application_id="test", module_name="test"),
            LogRecord(ts=now - 20, level="INFO", message="Connection timeout info", application_id="test", module_name="test"),
            LogRecord(ts=now - 30, level="ERROR", message="Other error", application_id="test", module_name="test"),
        ]

        resp = client.get("/logs/query?since=5m&min_level=ERROR&message_contains=timeout&application_id=test")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["level"].upper() == "ERROR"
        assert "timeout" in data["results"][0]["message"].lower()

    def test_all_filters_together(self, monkeypatch):
        """Test all filters together: time + level + message + pagination."""
        client = TestClient(app)
        storage = ApiTestStorage()
        monkeypatch.setattr(storage_mod, "get_storage", lambda: storage)

        now = time.time()
        storage.records = [
            LogRecord(ts=now - 10, level="ERROR", message="Error with connection", application_id="test", module_name="mod1"),
            LogRecord(ts=now - 20, level="ERROR", message="Error with timeout", application_id="test", module_name="mod1"),
            LogRecord(ts=now - 30, level="WARN", message="Warning about connection", application_id="test", module_name="mod1"),
            LogRecord(ts=now - 40, level="ERROR", message="Error no match", application_id="test", module_name="mod1"),
        ]

        resp = client.get(
            "/logs/query?since=5m&min_level=ERROR&message_contains=connection&application_id=test&limit=10"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["level"].upper() == "ERROR"
        assert "connection" in data["results"][0]["message"].lower()
