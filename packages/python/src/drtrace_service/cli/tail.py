"""Tail command implementation for streaming logs."""

import argparse
import signal
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set

from drtrace_service.daemon_health import check_daemon_alive
from drtrace_service.output_formatter import ColorMode, LogFormatter, OutputFormat
from drtrace_service.storage import get_default_log_path


class TailFollower:
    """Follows log file with polling."""

    def __init__(
        self,
        log_path: Path,
        poll_interval_ms: int = 500,
        service_filter: Optional[str] = None,
        level_filter: Optional[str] = None,
        color_mode: ColorMode = ColorMode.AUTO,
    ):
        """Initialize tail follower.

        Args:
            log_path: Path to log file
            poll_interval_ms: Polling interval in milliseconds
            service_filter: Service name to filter for (optional)
            level_filter: Log level to filter for (optional)
            color_mode: Color mode for output
        """
        self.log_path = log_path
        self.poll_interval = poll_interval_ms / 1000.0
        self.service_filter = service_filter
        self.level_filter = level_filter
        self.formatter = LogFormatter(
            output_format=OutputFormat.PLAIN, color_mode=color_mode
        )

        # Track file position
        self.last_pos = 0
        self.lines_seen: Set[str] = set()  # For deduplication

    def _parse_line(self, line: str) -> Optional[tuple]:
        """Parse log line to extract service and level.

        Returns:
            Tuple of (service, level) or None if parse fails
        """
        import re

        pattern = r"^\[.*\] \[([^\]]+)\] \[([^\]]+)\]"
        match = re.match(pattern, line)
        if match:
            return (match.group(1), match.group(2))
        return None

    def _should_include(self, line: str) -> bool:
        """Check if line should be included based on filters."""
        parsed = self._parse_line(line)
        if not parsed:
            return True

        service, level = parsed

        if self.service_filter and service != self.service_filter:
            return False

        if self.level_filter and level != self.level_filter:
            return False

        return True

    def tail(self) -> int:
        """Start tailing log file.

        Returns:
            Exit code (0 for normal exit, 1 for error)
        """
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                # Get initial lines (last 10)
                all_lines = f.readlines()
                initial_lines = all_lines[-10:] if len(all_lines) > 10 else all_lines

                # Print initial lines
                for line in initial_lines:
                    line = line.rstrip("\n")
                    if self._should_include(line):
                        print(line)

                # Track position
                self.last_pos = f.tell()

                # Print status
                print(f"\n[Tailing local file at {self.log_path}...]", file=sys.stderr)
                print(f"[Press Ctrl+C to exit]", file=sys.stderr)

                # Follow new entries
                try:
                    while True:
                        time.sleep(self.poll_interval)

                        with open(self.log_path, "r", encoding="utf-8") as f_follow:
                            f_follow.seek(self.last_pos)
                            new_lines = f_follow.readlines()

                            for line in new_lines:
                                line = line.rstrip("\n")
                                if line and self._should_include(line):
                                    # Avoid duplicates
                                    if line not in self.lines_seen:
                                        print(line)
                                        self.lines_seen.add(line)

                            self.last_pos = f_follow.tell()

                except KeyboardInterrupt:
                    print("\n[Tail interrupted]", file=sys.stderr)
                    return 0

        except (IOError, OSError) as e:
            print(f"Error: Could not tail log file: {e}", file=sys.stderr)
            return 1


def tail_command(args: Optional[List[str]] = None) -> int:
    """Execute tail command.

    Args:
        args: Command-line arguments (for testing)

    Returns:
        Exit code: 0 (normal exit), 1 (error)
    """
    parser = argparse.ArgumentParser(
        prog="drtrace tail", description="Stream logs in real time"
    )
    parser.add_argument(
        "-f",
        "--filter-service",
        default=None,
        help="Filter by service name (e.g., api)",
    )
    parser.add_argument(
        "-l", "--filter-level", default=None, help="Filter by log level (DEBUG, INFO, WARN, ERROR)"
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=500,
        help="Polling interval in milliseconds (default 500)",
    )
    parser.add_argument(
        "--color",
        choices=["auto", "always", "never"],
        default="auto",
        help="Color output mode",
    )

    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return 1

    # Check if daemon is available
    daemon_available = check_daemon_alive(timeout_ms=500)

    if daemon_available:
        # TODO: Implement daemon streaming path (WebSocket/SSE/long-poll)
        print(
            "Error: Daemon streaming path not yet implemented", file=sys.stderr
        )
        print(
            "Falling back to local file mode...", file=sys.stderr
        )

    # Use local file fallback
    log_path = get_default_log_path()
    if not log_path or not log_path.exists():
        print(f"Error: Log file not found at {log_path}", file=sys.stderr)
        return 1

    # Map color string to enum
    color_map = {
        "auto": ColorMode.AUTO,
        "always": ColorMode.ALWAYS,
        "never": ColorMode.NEVER,
    }
    color_mode = color_map[parsed_args.color]

    # Create follower and start tailing
    follower = TailFollower(
        log_path,
        poll_interval_ms=parsed_args.poll_interval,
        service_filter=parsed_args.filter_service,
        level_filter=parsed_args.filter_level,
        color_mode=color_mode,
    )

    return follower.tail()
