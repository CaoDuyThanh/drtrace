"""
Tests for combining logs and code snippets into AI analysis input (Story 5.2).

These tests verify that logs and code snippets are correctly combined into
a structured format ready for AI analysis.
"""

import time
from typing import Any, Dict

from drtrace_service.analysis import (  # type: ignore[import]
    analysis_input_to_dict,
    prepare_ai_analysis_input,
)
from drtrace_service.models import LogRecord  # type: ignore[import]


def _make_log_record(
    file_path: str = None,  # type: ignore
    line_no: int = None,  # type: ignore
    level: str = "INFO",
    message: str = "Test log",
    **kwargs: Any,
) -> LogRecord:
    """Create a LogRecord for testing."""
    base: Dict[str, Any] = {
        "ts": time.time(),
        "level": level,
        "message": message,
        "application_id": "test-app",
        "module_name": "test_module",
        "context": {},
    }
    if file_path:
        base["file_path"] = file_path
    if line_no:
        base["line_no"] = line_no
    base.update(kwargs)
    return LogRecord(**base)


def test_prepare_ai_input_includes_logs_and_snippets(tmp_path, monkeypatch):
    """
    AC 1: Joint log + code payload construction.

    Given logs with file_path and line_no, when preparing AI input,
    then it retrieves code snippets and constructs a payload with both.
    """
    # Create a test file
    test_file = tmp_path / "test_module.py"
    test_file.write_text(
        "\n".join(
            [
                "def function_a():",
                "    pass",
                "",
                "def function_b():",
                "    raise ValueError('error')",  # Line 5
                "",
                "def function_c():",
                "    pass",
            ]
        )
    )

    monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(tmp_path))

    # Create log with file/line metadata
    log = _make_log_record(
        file_path="test_module.py",
        line_no=5,
        level="ERROR",
        message="Error occurred",
    )

    # Prepare AI input
    input_data = prepare_ai_analysis_input([log])

    # Verify structure
    assert len(input_data.logs) == 1
    entry = input_data.logs[0]

    # Verify log entry
    assert entry.log.message == "Error occurred"
    assert entry.log.level == "ERROR"
    assert entry.log.file_path == "test_module.py"
    assert entry.log.line_no == 5

    # Verify code snippet entry
    assert entry.code_snippet is not None
    assert entry.code_snippet.file_path == "test_module.py"
    assert entry.code_snippet.line_no == 5
    assert entry.code_snippet.snippet_ok is True
    assert len(entry.code_snippet.lines) > 0

    # Verify target line is marked
    target_lines = [line for line in entry.code_snippet.lines if line["is_target"]]
    assert len(target_lines) == 1
    assert "raise ValueError" in target_lines[0]["text"]


def test_prepare_ai_input_handles_logs_without_code_context(tmp_path, monkeypatch):
    """
    AC 2: Robustness to missing code context.

    Given logs without file_path/line_no, when preparing AI input,
    then those logs are included without code snippets and analysis doesn't fail.
    """
    monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(tmp_path))

    # Create logs: one with code context, one without
    log_with_code = _make_log_record(
        file_path="test.py",
        line_no=10,
        message="Log with code",
    )
    log_without_code = _make_log_record(
        message="Log without code",
        # No file_path or line_no
    )

    # Prepare AI input
    input_data = prepare_ai_analysis_input([log_with_code, log_without_code])

    # Verify both logs included
    assert len(input_data.logs) == 2

    # First log should have code snippet
    assert input_data.logs[0].code_snippet is None or not input_data.logs[0].code_snippet.snippet_ok

    # Second log should not have code snippet
    assert input_data.logs[1].code_snippet is None

    # Both logs should have log entries
    assert input_data.logs[0].log.message == "Log with code"
    assert input_data.logs[1].log.message == "Log without code"

    # Summary should reflect this
    assert input_data.summary["total_logs"] == 2
    assert input_data.summary["logs_without_code_context"] >= 1


def test_prepare_ai_input_handles_failed_snippet_retrieval(tmp_path, monkeypatch):
    """Logs with file_path/line_no but failed snippet retrieval are handled gracefully."""
    monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(tmp_path))

    # Create log with file/line that doesn't exist
    log = _make_log_record(
        file_path="nonexistent.py",
        line_no=999,
        message="Log with invalid file",
    )

    # Prepare AI input
    input_data = prepare_ai_analysis_input([log])

    # Verify log is included
    assert len(input_data.logs) == 1
    entry = input_data.logs[0]

    # Verify log entry exists
    assert entry.log.message == "Log with invalid file"

    # Verify code snippet entry indicates failure
    assert entry.code_snippet is not None
    assert entry.code_snippet.snippet_ok is False
    assert entry.code_snippet.snippet_error is not None
    assert entry.code_snippet.lines == []


def test_prepare_ai_input_includes_all_log_fields(tmp_path, monkeypatch):
    """AI input includes all relevant log fields."""
    test_file = tmp_path / "test.py"
    test_file.write_text("def test():\n    pass\n")
    monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(tmp_path))

    log = _make_log_record(
        file_path="test.py",
        line_no=1,
        level="ERROR",
        message="Test error",
        service_name="test_service",
        exception_type="ValueError",
        stacktrace="Traceback...",
        context={"request_id": "req-123"},
    )

    input_data = prepare_ai_analysis_input([log])
    entry = input_data.logs[0]

    # Verify all fields present
    assert entry.log.level == "ERROR"
    assert entry.log.message == "Test error"
    assert entry.log.service_name == "test_service"
    assert entry.log.exception_type == "ValueError"
    assert entry.log.stacktrace == "Traceback..."
    assert entry.log.context == {"request_id": "req-123"}


def test_prepare_ai_input_summary_metadata(tmp_path, monkeypatch):
    """Summary metadata correctly reflects the analysis set."""
    test_file = tmp_path / "test.py"
    test_file.write_text("def test():\n    pass\n")
    monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(tmp_path))

    base_time = time.time()

    logs = [
        _make_log_record(
            file_path="test.py",
            line_no=1,
            level="INFO",
            message="Info log",
            ts=base_time + 1.0,
        ),
        _make_log_record(
            file_path="test.py",
            line_no=1,
            level="ERROR",
            message="Error log",
            ts=base_time + 2.0,
        ),
        _make_log_record(
            message="Log without code",
            ts=base_time + 3.0,
        ),
    ]

    input_data = prepare_ai_analysis_input(logs)

    # Verify summary
    assert input_data.summary["total_logs"] == 3
    assert input_data.summary["logs_with_code_context"] >= 2
    assert input_data.summary["logs_without_code_context"] >= 1
    assert input_data.summary["error_logs"] == 1
    assert input_data.summary["time_range"]["start_ts"] == base_time + 1.0
    assert input_data.summary["time_range"]["end_ts"] == base_time + 3.0


def test_analysis_input_to_dict_serialization(tmp_path, monkeypatch):
    """analysis_input_to_dict converts AnalysisInput to JSON-serializable dict."""
    test_file = tmp_path / "test.py"
    test_file.write_text("def test():\n    pass\n")
    monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(tmp_path))

    log = _make_log_record(
        file_path="test.py",
        line_no=1,
        message="Test log",
    )

    input_data = prepare_ai_analysis_input([log])
    result_dict = analysis_input_to_dict(input_data)

    # Verify structure
    assert "logs" in result_dict
    assert "summary" in result_dict
    assert len(result_dict["logs"]) == 1

    # Verify log entry structure
    log_entry = result_dict["logs"][0]
    assert "log" in log_entry
    assert "code_snippet" in log_entry
    assert log_entry["log"]["message"] == "Test log"

    # Verify it's JSON-serializable (no complex objects)
    import json

    json_str = json.dumps(result_dict)
    assert "Test log" in json_str


def test_prepare_ai_input_multiple_logs_same_file(tmp_path, monkeypatch):
    """Multiple logs from same file reuse snippet retrieval efficiently."""
    test_file = tmp_path / "test.py"
    test_file.write_text("\n".join([f"line {i}" for i in range(1, 21)]))
    monkeypatch.setenv("DRTRACE_SOURCE_ROOTS", str(tmp_path))

    # Create multiple logs from same file at different lines
    logs = [
        _make_log_record(file_path="test.py", line_no=line, message=f"Log at line {line}")
        for line in [5, 10, 15]
    ]

    input_data = prepare_ai_analysis_input(logs)

    # Verify all logs included
    assert len(input_data.logs) == 3

    # Verify all have code snippets
    for entry in input_data.logs:
        assert entry.code_snippet is not None
        assert entry.code_snippet.snippet_ok is True

    # Verify snippets are correct for each line
    assert input_data.logs[0].code_snippet.line_no == 5
    assert input_data.logs[1].code_snippet.line_no == 10
    assert input_data.logs[2].code_snippet.line_no == 15


def test_prepare_ai_input_empty_logs_list():
    """Empty logs list produces valid but empty analysis input."""
    input_data = prepare_ai_analysis_input([])

    assert len(input_data.logs) == 0
    assert input_data.summary["total_logs"] == 0
    assert input_data.summary["logs_with_code_context"] == 0
    assert input_data.summary["logs_without_code_context"] == 0
    assert input_data.summary["time_range"]["start_ts"] is None
    assert input_data.summary["time_range"]["end_ts"] is None

