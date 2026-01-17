"""Shared output formatting for query commands.

Provides plain-text and JSON formatters for log records.
Handles color output based on terminal detection.
"""

import json
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Union

from drtrace_service.models import LogRecord


class OutputFormat(Enum):
    """Output format options."""
    PLAIN = "plain"
    JSON = "json"


class ColorMode(Enum):
    """Color output mode options."""
    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


class LogFormatter:
    """Formatter for log records supporting multiple output formats."""

    # ANSI color codes
    COLOR_RED = "\033[91m"
    COLOR_YELLOW = "\033[93m"
    COLOR_RESET = "\033[0m"

    def __init__(
        self,
        output_format: Union[OutputFormat, str] = OutputFormat.PLAIN,
        color_mode: Union[ColorMode, str] = ColorMode.AUTO,
    ):
        """Initialize formatter.

        Args:
            output_format: Output format (plain or json)
            color_mode: Color mode (auto, always, never)
        """
        if isinstance(output_format, str):
            self.output_format = OutputFormat(output_format.lower())
        else:
            self.output_format = output_format

        if isinstance(color_mode, str):
            self.color_mode = ColorMode(color_mode.lower())
        else:
            self.color_mode = color_mode

        # Determine if we should use colors
        self._use_colors = self._should_use_colors()

    def _should_use_colors(self) -> bool:
        """Determine whether to use color output.

        Returns:
            True if colors should be used, False otherwise
        """
        if self.color_mode == ColorMode.ALWAYS:
            return True
        elif self.color_mode == ColorMode.NEVER:
            return False
        else:  # AUTO
            # Detect if stdout is a terminal
            return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def _get_level_color(self, level: str) -> str:
        """Get color code for log level.

        Args:
            level: Log level string (DEBUG, INFO, WARN, ERROR, CRITICAL)

        Returns:
            ANSI color code or empty string if no color
        """
        if not self._use_colors:
            return ""

        level_upper = level.upper()
        if level_upper in ("ERROR", "CRITICAL"):
            return self.COLOR_RED
        elif level_upper in ("WARN", "WARNING"):
            return self.COLOR_YELLOW
        else:
            return ""

    def _get_reset_color(self) -> str:
        """Get color reset code if colors are enabled."""
        return self.COLOR_RESET if self._use_colors else ""

    def format_record(self, record: LogRecord) -> str:
        """Format a log record.

        Args:
            record: LogRecord to format

        Returns:
            Formatted string
        """
        if self.output_format == OutputFormat.JSON:
            return self._format_json(record)
        else:
            return self._format_plain_text(record)

    def _format_plain_text(self, record: LogRecord) -> str:
        """Format record as plain text.

        Format: [TIMESTAMP] [SERVICE] [LEVEL] MESSAGE

        Args:
            record: LogRecord to format

        Returns:
            Plain text formatted string
        """
        # Convert timestamp to ISO format
        timestamp = datetime.fromtimestamp(record.ts).isoformat(timespec="seconds")

        # Build level string with optional color
        color = self._get_level_color(record.level)
        reset = self._get_reset_color()
        level_str = f"{color}{record.level}{reset}"

        # Build message
        service = record.service_name or "unknown"
        message = record.message or ""

        return f"[{timestamp}] [{service}] [{level_str}] {message}"

    def _format_json(self, record: LogRecord) -> str:
        """Format record as JSON.

        Args:
            record: LogRecord to format

        Returns:
            JSON formatted string
        """
        record_dict = {
            "ts": record.ts,
            "timestamp": datetime.fromtimestamp(record.ts).isoformat(timespec="seconds"),
            "level": record.level,
            "message": record.message,
            "application_id": record.application_id,
            "service_name": record.service_name,
            "module_name": record.module_name,
            "file_path": record.file_path,
            "line_no": record.line_no,
            "exception_type": record.exception_type,
            "stacktrace": record.stacktrace,
            "context": record.context or {},
        }
        return json.dumps(record_dict)

    def format_records(self, records: List[LogRecord]) -> str:
        """Format multiple log records.

        Args:
            records: List of LogRecords to format

        Returns:
            Formatted string with one record per line (plain) or JSON array (json)
        """
        if self.output_format == OutputFormat.JSON:
            return json.dumps([self._record_to_dict(r) for r in records])
        else:
            return "\n".join(self.format_record(r) for r in records)

    def _record_to_dict(self, record: LogRecord) -> dict:
        """Convert record to dictionary for JSON serialization.

        Args:
            record: LogRecord to convert

        Returns:
            Dictionary representation
        """
        return {
            "ts": record.ts,
            "timestamp": datetime.fromtimestamp(record.ts).isoformat(timespec="seconds"),
            "level": record.level,
            "message": record.message,
            "application_id": record.application_id,
            "service_name": record.service_name,
            "module_name": record.module_name,
            "file_path": record.file_path,
            "line_no": record.line_no,
            "exception_type": record.exception_type,
            "stacktrace": record.stacktrace,
            "context": record.context or {},
        }
