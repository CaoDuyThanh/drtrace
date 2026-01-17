"""Grep command implementation for searching logs with POSIX regex."""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

import httpx

from drtrace_service.daemon_health import check_daemon_alive
from drtrace_service.storage import get_default_log_path


# Cache for recent log reads to avoid repeated disk scans
_log_cache: dict = {}
_cache_ttl: float = 30.0  # 30 seconds


def _get_cached_log(log_path: Path) -> Optional[List[str]]:
    """Get log from cache if fresh."""
    now = time.time()
    if log_path in _log_cache:
        content, timestamp = _log_cache[log_path]
        if now - timestamp < _cache_ttl:
            return content
        else:
            del _log_cache[log_path]
    return None


def _cache_log(log_path: Path, lines: List[str]) -> None:
    """Cache log file lines."""
    _log_cache[log_path] = (lines, time.time())


def _parse_time_duration(duration_str: str) -> Optional[timedelta]:
    """Parse duration string like '30m', '1h', '2d', '7d'.
    
    Returns:
        timedelta object or None if invalid
    """
    import re
    match = re.match(r'^(\d+)([mhd])$', duration_str.strip().lower())
    if not match:
        return None
    
    value, unit = int(match.group(1)), match.group(2)
    if unit == 'm':
        return timedelta(minutes=value)
    elif unit == 'h':
        return timedelta(hours=value)
    elif unit == 'd':
        return timedelta(days=value)
    return None


def _parse_log_line(line: str) -> Optional[Tuple[datetime, str, str, str]]:
    """Parse log line to extract timestamp, service, level, message.
    
    Expected format: [YYYY-MM-DD HH:MM:SS] [SERVICE] [LEVEL] MESSAGE
    
    Returns:
        Tuple of (datetime, service, level, message) or None if parse fails
    """
    import re
    pattern = r'^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[([^\]]+)\] \[([^\]]+)\] (.*)$'
    match = re.match(pattern, line)
    if not match:
        return None
    
    try:
        timestamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
        return (timestamp, match.group(2), match.group(3), match.group(4))
    except ValueError:
        return None


def _should_include_line(
    line: str,
    pattern: str,
    ignore_case: bool,
    invert_match: bool,
    extended_regex: bool,
    since: Optional[timedelta] = None
) -> bool:
    """Determine if a line should be included based on filters.
    
    Args:
        line: Log line to test
        pattern: Regex pattern to match
        ignore_case: If True, ignore case in pattern matching
        invert_match: If True, invert match (include non-matching)
        extended_regex: If True, use POSIX extended regex
        since: If provided, only include lines after this duration
        
    Returns:
        True if line should be included, False otherwise
    """
    # Parse line if time filtering needed
    parsed = None
    if since:
        parsed = _parse_log_line(line)
        if parsed:
            timestamp, _, _, _ = parsed
            cutoff = datetime.now() - since
            if timestamp < cutoff:
                return False
    
    # Pattern matching
    flags = re.IGNORECASE if ignore_case else 0
    try:
        if extended_regex:
            # Python's re module supports extended regex
            match = re.search(pattern, line, flags)
        else:
            # Basic regex (just search, not extended)
            match = re.search(pattern, line, flags)
    except re.error:
        # Invalid regex pattern
        return False
    
    # Apply invert logic
    if invert_match:
        return not match
    else:
        return bool(match)


def grep_command(args: Optional[List[str]] = None) -> int:
    """Execute grep command.
    
    Args:
        args: Command-line arguments (for testing)
        
    Returns:
        Exit code: 0 (matches found), 1 (no matches), 2 (error)
    """
    parser = argparse.ArgumentParser(
        prog='drtrace grep',
        description='Search logs with POSIX regex'
    )
    parser.add_argument('pattern', help='Regex pattern to search for')
    parser.add_argument('-i', '--ignore-case', action='store_true', help='Ignore case in pattern')
    parser.add_argument('-c', '--count', action='store_true', help='Output count of matches instead of matches')
    parser.add_argument('-v', '--invert-match', action='store_true', help='Invert match (output non-matching lines)')
    parser.add_argument('-n', '--line-number', action='store_true', help='Output line numbers with matches')
    parser.add_argument('-E', '--extended-regex', action='store_true', help='Use POSIX extended regex')
    parser.add_argument('--since', default=None, help='Time range: 30m/1h/2d/7d')
    parser.add_argument('--full-search', action='store_true', help='Allow searches >30d without limit')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    try:
        parsed_args = parser.parse_args(args)
    except SystemExit:
        return 2
    
    # Validate time range
    if parsed_args.since:
        since_td = _parse_time_duration(parsed_args.since)
        if not since_td:
            print(f"Error: Invalid time duration '{parsed_args.since}'", file=sys.stderr)
            return 2
        
        if since_td.days > 30 and not parsed_args.full_search:
            print(
                f"Error: Time range {parsed_args.since} exceeds 30 days. "
                "Use --full-search to allow longer searches.",
                file=sys.stderr
            )
            return 2
    else:
        since_td = None
    
    # Check if daemon is available
    daemon_available = check_daemon_alive(timeout_ms=500)
    
    if daemon_available:
        # Use daemon HTTP query path (Story 11-2: wire -E flag to message_regex)
        try:
            daemon_host = os.getenv("DRTRACE_DAEMON_HOST", "localhost")
            daemon_port = os.getenv("DRTRACE_DAEMON_PORT", "8001")
            daemon_url = f"http://{daemon_host}:{daemon_port}/logs/query"
            
            # Build query parameters
            params = {
                "since": parsed_args.since if parsed_args.since else "5m",
            }
            
            # Use message_regex if -E flag provided, else message_contains (Epic 11.1, 11.2)
            if parsed_args.extended_regex:
                params["message_regex"] = parsed_args.pattern
            else:
                params["message_contains"] = parsed_args.pattern
            
            # Query daemon using httpx
            try:
                response = httpx.get(daemon_url, params=params, timeout=5.0)
                response.raise_for_status()
                data = response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                # Daemon query failed, fall back to local file
                raise
            else:
                # Process daemon results
                from drtrace_service.models import LogRecord
                
                results = []
                for record_dict in data.get("results", []):
                    record = LogRecord(**record_dict)
                    
                    # Apply additional filters that weren't sent to API (invert_match, line_number)
                    if parsed_args.invert_match:
                        if parsed_args.extended_regex:
                            flags = re.IGNORECASE if parsed_args.ignore_case else 0
                            if re.search(parsed_args.pattern, record.message, flags):
                                continue
                        else:
                            pattern_lower = parsed_args.pattern.lower() if parsed_args.ignore_case else parsed_args.pattern
                            message_lower = record.message.lower() if parsed_args.ignore_case else record.message
                            if pattern_lower in message_lower:
                                continue
                    
                    # Format output
                    ts_str = datetime.fromtimestamp(record.ts).strftime('%Y-%m-%d %H:%M:%S')
                    service_str = f"[{record.service_name}]" if record.service_name else ""
                    msg = f"[{ts_str}] {service_str} [{record.level}] {record.message}"
                    
                    if parsed_args.line_number:
                        # Use timestamp as pseudo line number for daemon results
                        results.append(f"{int(record.ts)}:{msg}")
                    else:
                        results.append(msg)
                
                # Output results
                if parsed_args.count:
                    print(len(results))
                elif results:
                    for result in results:
                        print(result)
                else:
                    return 1
                
                return 0
        except Exception as e:
            # Daemon query failed, fall back to local file
            pass
    
    # Use local file fallback
    log_path = get_default_log_path()
    if not log_path or not log_path.exists():
        print(f"Error: Log file not found at {log_path}", file=sys.stderr)
        return 2
    
    # Check cache first
    lines = _get_cached_log(log_path)
    if lines is None:
        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            _cache_log(log_path, lines)
        except (IOError, OSError) as e:
            print(f"Error: Could not read log file: {e}", file=sys.stderr)
            return 2
    
    # Apply filters
    matches = []
    for line_num, line in enumerate(lines, start=1):
        line = line.rstrip('\n')
        if _should_include_line(
            line,
            parsed_args.pattern,
            parsed_args.ignore_case,
            parsed_args.invert_match,
            parsed_args.extended_regex,
            since_td
        ):
            if parsed_args.line_number:
                matches.append(f"{line_num}:{line}")
            else:
                matches.append(line)
    
    # Output results
    if parsed_args.count:
        print(len(matches))
    elif matches:
        for match in matches:
            print(match)
    else:
        # No matches - empty output, exit code 1
        return 1
    
    return 0
