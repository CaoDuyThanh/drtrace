"""
Tests for the CLI 'why' command.

These tests verify:
- Time window parsing (relative and explicit)
- CLI argument parsing
- HTTP request construction
- Error handling (connection errors, HTTP errors, no data)
- Output formatting
"""

import json
import sys
from unittest.mock import MagicMock
from urllib import error, request

import pytest

from drtrace_service.__main__ import _parse_time_window, _run_why, main


def test_parse_time_window_relative_minutes():
    """Test parsing relative time window in minutes."""
    start, end = _parse_time_window(since="5m")
    assert end > start
    # Should be approximately 5 minutes (300 seconds) apart
    assert abs((end - start) - 300) < 1  # Allow 1 second tolerance


def test_parse_time_window_relative_hours():
    """Test parsing relative time window in hours."""
    start, end = _parse_time_window(since="2h")
    assert end > start
    assert abs((end - start) - 7200) < 1  # 2 hours = 7200 seconds


def test_parse_time_window_relative_seconds():
    """Test parsing relative time window in seconds."""
    start, end = _parse_time_window(since="30s")
    assert end > start
    assert abs((end - start) - 30) < 1


def test_parse_time_window_relative_days():
    """Test parsing relative time window in days."""
    start, end = _parse_time_window(since="1d")
    assert end > start
    assert abs((end - start) - 86400) < 1  # 1 day = 86400 seconds


def test_parse_time_window_explicit_timestamps():
    """Test parsing explicit start and end timestamps."""
    start_ts = 1000.0
    end_ts = 2000.0
    start, end = _parse_time_window(start=str(start_ts), end=str(end_ts))
    assert start == start_ts
    assert end == end_ts


def test_parse_time_window_invalid_relative_format():
    """Test that invalid relative time format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid time format"):
        _parse_time_window(since="invalid")


def test_parse_time_window_invalid_timestamp():
    """Test that invalid timestamp raises ValueError."""
    with pytest.raises(ValueError, match="must be Unix timestamps"):
        _parse_time_window(start="invalid", end="2000.0")


def test_parse_time_window_start_after_end():
    """Test that start after end raises ValueError."""
    with pytest.raises(ValueError, match="Start time must be before end time"):
        _parse_time_window(start="2000.0", end="1000.0")


def test_parse_time_window_missing_args():
    """Test that missing arguments raise ValueError."""
    with pytest.raises(ValueError, match="Must specify either"):
        _parse_time_window()


def test_run_why_connection_error(monkeypatch, capsys):
    """Test that connection errors are handled gracefully."""
    def mock_urlopen(*args, **kwargs):
        raise error.URLError("Connection refused")

    monkeypatch.setattr(request, "urlopen", mock_urlopen)

    with pytest.raises(SystemExit) as exc_info:
        _run_why([
            "--application-id", "test-app",
            "--since", "5m",
        ])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "Cannot connect to daemon" in captured.err
    assert "Hint:" in captured.err


def test_run_why_http_error_400(monkeypatch, capsys):
    """Test that HTTP 400 errors are handled with helpful messages."""
    def mock_urlopen(*args, **kwargs):
        http_error = error.HTTPError("url", 400, "Bad Request", {}, None)
        http_error.read = lambda: json.dumps({
            "detail": {
                "code": "INVALID_TIME_RANGE",
                "message": "start_ts must be less than end_ts",
            }
        }).encode()
        raise http_error

    monkeypatch.setattr(request, "urlopen", mock_urlopen)

    with pytest.raises(SystemExit) as exc_info:
        _run_why([
            "--application-id", "test-app",
            "--since", "5m",
        ])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "Hint:" in captured.err


def test_run_why_no_data(monkeypatch, capsys):
    """Test handling of no data response."""
    def mock_urlopen(*args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "data": {
                "explanation": None,
                "message": "No logs found",
            },
            "meta": {
                "application_id": "test-app",
                "start_ts": 1000.0,
                "end_ts": 2000.0,
                "count": 0,
                "no_data": True,
            },
        }).encode()
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *args: None
        return mock_resp

    monkeypatch.setattr(request, "urlopen", mock_urlopen)

    with pytest.raises(SystemExit) as exc_info:
        _run_why([
            "--application-id", "test-app",
            "--since", "5m",
        ])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "No logs found" in captured.out


def test_run_why_success_with_explanation(monkeypatch, capsys):
    """Test successful analysis with explanation output."""
    def mock_urlopen(*args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "data": {
                "explanation": {
                    "summary": "Division by zero error occurred",
                    "root_cause": "The function attempted to divide by zero",
                    "error_location": {
                        "file_path": "src/math_utils.py",
                        "line_no": 42,
                    },
                    "key_evidence": [
                        "Error log shows division by zero",
                        "Code at line 42 performs division",
                    ],
                    "suggested_fixes": [
                        "Add input validation before division",
                        "Check for zero denominator",
                    ],
                    "confidence": "high",
                    "evidence_references": [
                        {
                            "log_id": "log_0_1000",
                            "reason": "Error log shows division by zero",
                            "file_path": "src/math_utils.py",
                            "line_no": 42,
                            "line_range": {"start": 37, "end": 47},
                        }
                    ],
                },
            },
            "meta": {
                "application_id": "test-app",
                "start_ts": 1000.0,
                "end_ts": 2000.0,
                "count": 1,
            },
        }).encode()
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *args: None
        return mock_resp

    monkeypatch.setattr(request, "urlopen", mock_urlopen)

    with pytest.raises(SystemExit) as exc_info:
        _run_why([
            "--application-id", "test-app",
            "--since", "5m",
        ])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "ROOT CAUSE ANALYSIS" in captured.out
    assert "Division by zero error occurred" in captured.out
    assert "Root Cause:" in captured.out
    assert "Error Location:" in captured.out
    assert "Key Evidence:" in captured.out
    assert "Evidence References:" in captured.out
    assert "Suggested Fixes:" in captured.out
    assert "Confidence:" in captured.out


def test_run_why_with_filters(monkeypatch):
    """Test that filters are passed correctly to the API."""
    captured_url = None

    def mock_urlopen(url, *args, **kwargs):
        nonlocal captured_url
        captured_url = url
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "data": {"explanation": None, "message": "No logs found"},
            "meta": {"no_data": True, "count": 0},
        }).encode()
        mock_resp.__enter__ = lambda self: self
        mock_resp.__exit__ = lambda *args: None
        return mock_resp

    monkeypatch.setattr(request, "urlopen", mock_urlopen)

    with pytest.raises(SystemExit):
        _run_why([
            "--application-id", "test-app",
            "--since", "5m",
            "--min-level", "ERROR",
            "--module-name", "math_utils",
            "--service-name", "api",
            "--limit", "50",
        ])

    assert captured_url is not None
    assert "application_id=test-app" in captured_url
    assert "min_level=ERROR" in captured_url
    assert "module_name=math_utils" in captured_url
    assert "service_name=api" in captured_url
    assert "limit=50" in captured_url


def test_main_why_command(monkeypatch):
    """Test that main() routes to _run_why correctly."""
    called_args = None

    def mock_run_why(args):
        nonlocal called_args
        called_args = args
        sys.exit(0)

    monkeypatch.setattr("drtrace_service.__main__._run_why", mock_run_why)

    with pytest.raises(SystemExit) as exc_info:
        main(["why", "--application-id", "test", "--since", "5m"])

    assert exc_info.value.code == 0
    assert called_args == ["--application-id", "test", "--since", "5m"]


def test_main_invalid_command(capsys):
    """Test that invalid command shows usage."""
    with pytest.raises(SystemExit) as exc_info:
        main(["invalid"])

    assert exc_info.value.code == 1
    captured = capsys.readouterr()
    assert "Usage:" in captured.err
    assert "status" in captured.err
    assert "why" in captured.err

