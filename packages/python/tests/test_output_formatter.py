"""Tests for output formatter module."""

import json
from unittest.mock import patch

from drtrace_service.models import LogRecord
from drtrace_service.output_formatter import ColorMode, LogFormatter, OutputFormat


class TestLogFormatter:
    """Tests for LogFormatter class."""

    def test_init_default(self):
        """Test default formatter initialization."""
        formatter = LogFormatter()
        assert formatter.output_format == OutputFormat.PLAIN
        assert formatter.color_mode == ColorMode.AUTO

    def test_init_with_enum(self):
        """Test initialization with enum values."""
        formatter = LogFormatter(
            output_format=OutputFormat.JSON, color_mode=ColorMode.NEVER
        )
        assert formatter.output_format == OutputFormat.JSON
        assert formatter.color_mode == ColorMode.NEVER

    def test_init_with_strings(self):
        """Test initialization with string values."""
        formatter = LogFormatter(output_format="json", color_mode="always")
        assert formatter.output_format == OutputFormat.JSON
        assert formatter.color_mode == ColorMode.ALWAYS

    def test_should_use_colors_never(self):
        """Test that never mode disables colors."""
        formatter = LogFormatter(color_mode=ColorMode.NEVER)
        assert formatter._should_use_colors() is False

    def test_should_use_colors_always(self):
        """Test that always mode enables colors."""
        formatter = LogFormatter(color_mode=ColorMode.ALWAYS)
        assert formatter._should_use_colors() is True

    def test_should_use_colors_auto_tty(self):
        """Test auto mode detects TTY."""
        formatter = LogFormatter(color_mode=ColorMode.AUTO)
        with patch("sys.stdout.isatty", return_value=True):
            assert formatter._should_use_colors() is True

    def test_should_use_colors_auto_no_tty(self):
        """Test auto mode without TTY."""
        formatter = LogFormatter(color_mode=ColorMode.AUTO)
        with patch("sys.stdout.isatty", return_value=False):
            assert formatter._should_use_colors() is False

    def test_get_level_color_error(self):
        """Test color for ERROR level."""
        formatter = LogFormatter(color_mode=ColorMode.ALWAYS)
        color = formatter._get_level_color("ERROR")
        assert color == LogFormatter.COLOR_RED

    def test_get_level_color_warn(self):
        """Test color for WARN level."""
        formatter = LogFormatter(color_mode=ColorMode.ALWAYS)
        color = formatter._get_level_color("WARN")
        assert color == LogFormatter.COLOR_YELLOW

    def test_get_level_color_info(self):
        """Test no color for INFO level."""
        formatter = LogFormatter(color_mode=ColorMode.ALWAYS)
        color = formatter._get_level_color("INFO")
        assert color == ""

    def test_get_level_color_no_colors(self):
        """Test no color when colors disabled."""
        formatter = LogFormatter(color_mode=ColorMode.NEVER)
        color = formatter._get_level_color("ERROR")
        assert color == ""

    def test_format_plain_text(self):
        """Test plain text formatting."""
        formatter = LogFormatter(output_format=OutputFormat.PLAIN, color_mode=ColorMode.NEVER)
        record = LogRecord(
            ts=1609459200.0,  # 2021-01-01 00:00:00 UTC
            level="INFO",
            message="Test message",
            application_id="test-app",
            service_name="api",
            module_name="main",
            file_path="/app/main.py",
            line_no=42,
            exception_type=None,
            stacktrace=None,
        )

        output = formatter.format_record(record)
        assert "[" in output
        assert "api" in output
        assert "INFO" in output
        assert "Test message" in output

    def test_format_plain_text_with_color(self):
        """Test plain text formatting with colors."""
        formatter = LogFormatter(output_format=OutputFormat.PLAIN, color_mode=ColorMode.ALWAYS)
        record = LogRecord(
            ts=1609459200.0,
            level="ERROR",
            message="Error occurred",
            application_id="test-app",
            service_name="api",
            module_name="main",
            file_path="/app/main.py",
            line_no=42,
            exception_type=None,
            stacktrace=None,
        )

        output = formatter.format_record(record)
        assert LogFormatter.COLOR_RED in output
        assert LogFormatter.COLOR_RESET in output
        assert "Error occurred" in output

    def test_format_json(self):
        """Test JSON formatting."""
        formatter = LogFormatter(output_format=OutputFormat.JSON)
        record = LogRecord(
            ts=1609459200.0,
            level="INFO",
            message="Test message",
            application_id="test-app",
            service_name="api",
            module_name="main",
            file_path="/app/main.py",
            line_no=42,
            exception_type=None,
            stacktrace=None,
            context={"key": "value"},
        )

        output = formatter.format_record(record)
        data = json.loads(output)
        assert data["ts"] == 1609459200.0
        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["service_name"] == "api"
        assert data["context"]["key"] == "value"

    def test_format_plain_text_without_service(self):
        """Test plain text formatting when service is None."""
        formatter = LogFormatter(output_format=OutputFormat.PLAIN, color_mode=ColorMode.NEVER)
        record = LogRecord(
            ts=1609459200.0,
            level="DEBUG",
            message="Debug msg",
            application_id="app",
            service_name=None,
            module_name="mod",
            file_path="file.py",
            line_no=10,
            exception_type=None,
            stacktrace=None,

        )

        output = formatter.format_record(record)
        assert "[unknown]" in output
        assert "Debug msg" in output

    def test_format_records_plain(self):
        """Test formatting multiple records as plain text."""
        formatter = LogFormatter(output_format=OutputFormat.PLAIN, color_mode=ColorMode.NEVER)
        records = [
            LogRecord(
                ts=1609459200.0,
                level="INFO",
                message="First",
                application_id="app",
                service_name="api",
                module_name="m",
                file_path="f.py",
                line_no=1,
                exception_type=None,
                stacktrace=None,

            ),
            LogRecord(
                ts=1609459300.0,
                level="ERROR",
                message="Second",
                application_id="app",
                service_name="api",
                module_name="m",
                file_path="f.py",
                line_no=2,
                exception_type=None,
                stacktrace=None,

            ),
        ]

        output = formatter.format_records(records)
        lines = output.split("\n")
        assert len(lines) == 2
        assert "First" in lines[0]
        assert "Second" in lines[1]

    def test_format_records_json(self):
        """Test formatting multiple records as JSON."""
        formatter = LogFormatter(output_format=OutputFormat.JSON)
        records = [
            LogRecord(
                ts=1609459200.0,
                level="INFO",
                message="First",
                application_id="app",
                service_name="api",
                module_name="m",
                file_path="f.py",
                line_no=1,
                exception_type=None,
                stacktrace=None,

            ),
            LogRecord(
                ts=1609459300.0,
                level="ERROR",
                message="Second",
                application_id="app",
                service_name="api",
                module_name="m",
                file_path="f.py",
                line_no=2,
                exception_type=None,
                stacktrace=None,

            ),
        ]

        output = formatter.format_records(records)
        data = json.loads(output)
        assert len(data) == 2
        assert data[0]["message"] == "First"
        assert data[1]["message"] == "Second"

    def test_color_code_warning(self):
        """Test color code for WARNING (alias for WARN)."""
        formatter = LogFormatter(color_mode=ColorMode.ALWAYS)
        color = formatter._get_level_color("WARNING")
        assert color == LogFormatter.COLOR_YELLOW

    def test_plain_text_timestamp_format(self):
        """Test that plain text uses ISO format timestamp."""
        formatter = LogFormatter(output_format=OutputFormat.PLAIN, color_mode=ColorMode.NEVER)
        record = LogRecord(
            ts=1609459200.0,  # 2021-01-01 00:00:00 UTC
            level="INFO",
            message="msg",
            application_id="app",
            service_name="svc",
            module_name="mod",
            file_path="file.py",
            line_no=1,
            exception_type=None,
            stacktrace=None,

        )

        output = formatter.format_record(record)
        # Should contain ISO format timestamp (part of it)
        assert "2021-01-01" in output
        assert "T" in output  # ISO format has T separator

    def test_json_has_both_ts_and_timestamp(self):
        """Test JSON output includes both ts and human-readable timestamp."""
        formatter = LogFormatter(output_format=OutputFormat.JSON)
        record = LogRecord(
            ts=1609459200.0,
            level="INFO",
            message="msg",
            application_id="app",
            service_name="svc",
            module_name="mod",
            file_path="file.py",
            line_no=1,
            exception_type=None,
            stacktrace=None,

        )

        output = formatter.format_record(record)
        data = json.loads(output)
        assert "ts" in data
        assert "timestamp" in data
        assert data["ts"] == 1609459200.0
        assert "2021" in data["timestamp"]

    def test_empty_context_in_json(self):
        """Test that empty context is handled properly in JSON."""
        formatter = LogFormatter(output_format=OutputFormat.JSON)
        record = LogRecord(
            ts=1609459200.0,
            level="INFO",
            message="msg",
            application_id="app",
            service_name="svc",
            module_name="mod",
            file_path="file.py",
            line_no=1,
            exception_type=None,
            stacktrace=None,

        )

        output = formatter.format_record(record)
        data = json.loads(output)
        assert data["context"] == {}

    def test_context_preserved_in_json(self):
        """Test that context is preserved in JSON output."""
        formatter = LogFormatter(output_format=OutputFormat.JSON)
        context = {"user_id": 123, "request_id": "abc"}
        record = LogRecord(
            ts=1609459200.0,
            level="INFO",
            message="msg",
            application_id="app",
            service_name="svc",
            module_name="mod",
            file_path="file.py",
            line_no=1,
            exception_type=None,
            stacktrace=None,
            context=context,
        )

        output = formatter.format_record(record)
        data = json.loads(output)
        assert data["context"] == context
