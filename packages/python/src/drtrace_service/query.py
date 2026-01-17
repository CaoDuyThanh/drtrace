"""Query module with daemon-only flow (Story 11-3: simplified architecture)."""

import os
import sys
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import List, Optional, Tuple

from drtrace_service.daemon_health import check_daemon_alive
from drtrace_service.models import LogRecord


# Simple query cache using LRU (for last 10 queries with 1m TTL)
@lru_cache(maxsize=10)
def _get_query_cache_key(pattern: str, service: str, level: str, hours: int) -> str:
    """Generate cache key for query."""
    return f"{pattern}:{service}:{level}:{hours}"


class QueryTimingInfo:
    """Timing and source information for query results."""

    def __init__(self, source: str, elapsed_ms: float):
        """Initialize timing info.

        Args:
            source: "daemon" or "local db"
            elapsed_ms: Time taken in milliseconds
        """
        self.source = source
        self.elapsed_ms = elapsed_ms

    def format_label(self) -> str:
        """Format timing label for output."""
        return f"Results in {int(self.elapsed_ms)}ms ({self.source})"


def query_logs(
    pattern: str,
    service_name: Optional[str] = None,
    level: Optional[str] = None,
    hours: int = 1,
    full_search: bool = False,
) -> Tuple[List[LogRecord], QueryTimingInfo, Optional[str]]:
    """Query logs via daemon API (Story 11-3: simplified, no Postgres fallback).

    Args:
        pattern: Pattern to search for
        service_name: Service to filter (optional)
        level: Log level to filter (optional)
        hours: Time window in hours (default 1)
        full_search: Allow searches beyond 1 day

    Returns:
        Tuple of (results, timing_info, error_message)
        error_message is None on success, or error string on failure
    """
    # Validate time window
    if hours > 24 and not full_search:
        error_msg = (
            f"Time window {hours}h exceeds 24 hours. "
            "Use --full-search to allow longer searches."
        )
        return [], QueryTimingInfo("none", 0), error_msg

    # Check daemon availability
    start_time = time.time()
    if not check_daemon_alive(timeout_ms=500):
        error_msg = (
            "DrTrace daemon is not running.\n\n"
            "Start the daemon with:\n"
            "  drtrace daemon start\n\n"
            "Or, if daemon is on a different host:\n"
            "  export DRTRACE_DAEMON_HOST=<host>\n"
            "  export DRTRACE_DAEMON_PORT=<port>"
        )
        return [], QueryTimingInfo("none", 0), error_msg

    # Query daemon via HTTP API
    # TODO: Implement HTTP query to daemon
    # For now, return error indicating not implemented
    error_msg = "Daemon HTTP query not yet fully implemented in query module"
    return [], QueryTimingInfo("none", 0), error_msg
