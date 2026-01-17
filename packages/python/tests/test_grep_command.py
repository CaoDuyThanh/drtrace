"""Tests for grep command implementation."""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from drtrace_service.cli.grep import (
    grep_command,
    _parse_time_duration,
    _parse_log_line,
    _should_include_line,
    _get_cached_log,
    _cache_log,
)


class TestParseTimeDuration:
    """Tests for _parse_time_duration."""
    
    def test_parse_30m(self):
        """Test parsing 30 minutes."""
        td = _parse_time_duration("30m")
        assert td is not None
        assert td.total_seconds() == 1800
    
    def test_parse_1h(self):
        """Test parsing 1 hour."""
        td = _parse_time_duration("1h")
        assert td is not None
        assert td.total_seconds() == 3600
    
    def test_parse_2d(self):
        """Test parsing 2 days."""
        td = _parse_time_duration("2d")
        assert td is not None
        assert td.total_seconds() == 172800  # 2 * 24 * 3600
    
    def test_parse_7d(self):
        """Test parsing 7 days."""
        td = _parse_time_duration("7d")
        assert td is not None
        assert td.total_seconds() == 604800  # 7 * 24 * 3600
    
    def test_parse_invalid(self):
        """Test parsing invalid duration."""
        assert _parse_time_duration("invalid") is None
        assert _parse_time_duration("") is None
        assert _parse_time_duration("30") is None
    
    def test_parse_case_insensitive(self):
        """Test that parsing is case-insensitive."""
        td = _parse_time_duration("30M")
        assert td is not None
        assert td.total_seconds() == 1800
        
        td = _parse_time_duration("1H")
        assert td is not None


class TestParseLogLine:
    """Tests for _parse_log_line."""
    
    def test_parse_valid_log_line(self):
        """Test parsing a valid log line."""
        line = "[2026-01-05 10:30:45] [api] [INFO] Request received"
        result = _parse_log_line(line)
        assert result is not None
        timestamp, service, level, message = result
        assert timestamp.year == 2026
        assert timestamp.month == 1
        assert timestamp.day == 5
        assert timestamp.hour == 10
        assert timestamp.minute == 30
        assert timestamp.second == 45
        assert service == "api"
        assert level == "INFO"
        assert message == "Request received"
    
    def test_parse_invalid_timestamp(self):
        """Test parsing invalid timestamp."""
        line = "[2026-13-45 25:99:99] [api] [INFO] Invalid"
        result = _parse_log_line(line)
        assert result is None
    
    def test_parse_missing_brackets(self):
        """Test parsing line missing brackets."""
        line = "2026-01-05 10:30:45 api INFO Request"
        result = _parse_log_line(line)
        assert result is None
    
    def test_parse_message_with_brackets(self):
        """Test parsing message containing brackets."""
        line = "[2026-01-05 10:30:45] [api] [ERROR] Error: [DETAILS]"
        result = _parse_log_line(line)
        assert result is not None
        _, _, _, message = result
        assert message == "Error: [DETAILS]"


class TestShouldIncludeLine:
    """Tests for _should_include_line."""
    
    def test_basic_pattern_match(self):
        """Test basic pattern matching."""
        line = "[2026-01-05 10:30:45] [api] [INFO] Request received"
        assert _should_include_line(line, "Request", False, False, False) is True
        assert _should_include_line(line, "NotPresent", False, False, False) is False
    
    def test_case_insensitive(self):
        """Test case-insensitive matching."""
        line = "[2026-01-05 10:30:45] [api] [INFO] Request received"
        assert _should_include_line(line, "REQUEST", True, False, False) is True
        assert _should_include_line(line, "REQUEST", False, False, False) is False
    
    def test_invert_match(self):
        """Test inverted matching."""
        line = "[2026-01-05 10:30:45] [api] [INFO] Request received"
        assert _should_include_line(line, "Request", False, True, False) is False
        assert _should_include_line(line, "NotPresent", False, True, False) is True
    
    def test_regex_pattern(self):
        """Test regex pattern matching."""
        line = "[2026-01-05 10:30:45] [api] [INFO] Error: code 500"
        assert _should_include_line(line, r"Error: code \d+", False, False, True) is True
        assert _should_include_line(line, r"code 200", False, False, True) is False
    
    def test_time_filter(self):
        """Test time-based filtering."""
        from datetime import timedelta
        
        # Recent log line (should be included)
        recent = "[2026-01-05 10:30:45] [api] [INFO] Recent"
        # Assume "now" is 2026-01-05 10:30:45 for this test
        with patch('drtrace_service.cli.grep.datetime') as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 5, 10, 35, 0)
            mock_dt.strptime = datetime.strptime
            assert _should_include_line(recent, "Recent", False, False, False, timedelta(minutes=10)) is True
            assert _should_include_line(recent, "Recent", False, False, False, timedelta(minutes=4)) is False


class TestCache:
    """Tests for caching functionality."""
    
    def test_cache_hit(self):
        """Test cache hit within TTL."""
        path = Path("/test/log.log")
        lines = ["line1", "line2", "line3"]
        
        _cache_log(path, lines)
        cached = _get_cached_log(path)
        assert cached == lines
    
    def test_cache_miss_after_expiry(self):
        """Test cache miss after TTL expiry."""
        path = Path("/test/log.log")
        lines = ["line1", "line2"]
        
        with patch('drtrace_service.cli.grep.time.time') as mock_time:
            # First call to cache the data at time=0
            mock_time.return_value = 0
            _cache_log(path, lines)
            
            # Move time forward beyond TTL (30 seconds)
            mock_time.return_value = 31
            cached = _get_cached_log(path)
            assert cached is None


class TestGrepCommand:
    """Tests for grep_command."""
    
    def test_no_arguments(self):
        """Test grep without required pattern argument."""
        result = grep_command([])
        assert result == 2  # Error exit code
    
    def test_invalid_time_duration(self):
        """Test grep with invalid time duration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("[2026-01-05 10:30:45] [api] [INFO] Test\n")
            f.flush()
            log_path = f.name
        
        try:
            with patch('drtrace_service.cli.grep.get_default_log_path', return_value=Path(log_path)):
                with patch('drtrace_service.cli.grep.check_daemon_alive', return_value=False):
                    result = grep_command(["pattern", "--since", "invalid"])
                    assert result == 2  # Error exit code
        finally:
            os.unlink(log_path)
    
    def test_time_range_exceeds_30d_without_flag(self):
        """Test that >30d requires --full-search."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("[2026-01-05 10:30:45] [api] [INFO] Test\n")
            f.flush()
            log_path = f.name
        
        try:
            with patch('drtrace_service.cli.grep.get_default_log_path', return_value=Path(log_path)):
                with patch('drtrace_service.cli.grep.check_daemon_alive', return_value=False):
                    result = grep_command(["pattern", "--since", "60d"])
                    assert result == 2  # Error exit code
        finally:
            os.unlink(log_path)
    
    def test_no_matches(self):
        """Test grep with no matching lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("[2026-01-05 10:30:45] [api] [INFO] Request received\n")
            f.write("[2026-01-05 10:30:46] [api] [INFO] Response sent\n")
            f.flush()
            log_path = f.name
        
        try:
            with patch('drtrace_service.cli.grep.get_default_log_path', return_value=Path(log_path)):
                with patch('drtrace_service.cli.grep.check_daemon_alive', return_value=False):
                    result = grep_command(["NotPresent"])
                    assert result == 1  # No matches exit code
        finally:
            os.unlink(log_path)
    
    def test_matches_found(self):
        """Test grep with matches found."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("[2026-01-05 10:30:45] [api] [INFO] Request received\n")
            f.write("[2026-01-05 10:30:46] [api] [ERROR] Error occurred\n")
            f.flush()
            log_path = f.name
        
        try:
            with patch('drtrace_service.cli.grep.get_default_log_path', return_value=Path(log_path)):
                with patch('drtrace_service.cli.grep.check_daemon_alive', return_value=False):
                    result = grep_command(["Error"])
                    assert result == 0  # Matches found exit code
        finally:
            os.unlink(log_path)
    
    def test_count_matches(self):
        """Test grep -c flag."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("[2026-01-05 10:30:45] [api] [INFO] Error msg 1\n")
            f.write("[2026-01-05 10:30:46] [api] [ERROR] Error msg 2\n")
            f.write("[2026-01-05 10:30:47] [api] [INFO] Not error\n")
            f.flush()
            log_path = f.name
        
        try:
            with patch('drtrace_service.cli.grep.get_default_log_path', return_value=Path(log_path)):
                with patch('drtrace_service.cli.grep.check_daemon_alive', return_value=False):
                    with patch('builtins.print') as mock_print:
                        result = grep_command(["Error", "-c"])
                        assert result == 0
                        mock_print.assert_called_with(2)  # 2 matches
        finally:
            os.unlink(log_path)
    
    def test_ignore_case_flag(self):
        """Test -i flag for case-insensitive matching."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("[2026-01-05 10:30:45] [api] [INFO] ERROR in system\n")
            f.flush()
            log_path = f.name
        
        try:
            with patch('drtrace_service.cli.grep.get_default_log_path', return_value=Path(log_path)):
                with patch('drtrace_service.cli.grep.check_daemon_alive', return_value=False):
                    result = grep_command(["error", "-i"])
                    assert result == 0
        finally:
            os.unlink(log_path)
    
    def test_invert_match_flag(self):
        """Test -v flag for inverted matching."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("[2026-01-05 10:30:45] [api] [INFO] Normal log\n")
            f.write("[2026-01-05 10:30:46] [api] [ERROR] Error\n")
            f.flush()
            log_path = f.name
        
        try:
            with patch('drtrace_service.cli.grep.get_default_log_path', return_value=Path(log_path)):
                with patch('drtrace_service.cli.grep.check_daemon_alive', return_value=False):
                    result = grep_command(["Error", "-v"])
                    assert result == 0  # Should match the INFO line
        finally:
            os.unlink(log_path)
    
    def test_line_number_flag(self):
        """Test -n flag for line numbers."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
            f.write("[2026-01-05 10:30:45] [api] [INFO] First\n")
            f.write("[2026-01-05 10:30:46] [api] [INFO] Test line\n")
            f.flush()
            log_path = f.name
        
        try:
            with patch('drtrace_service.cli.grep.get_default_log_path', return_value=Path(log_path)):
                with patch('drtrace_service.cli.grep.check_daemon_alive', return_value=False):
                    with patch('builtins.print') as mock_print:
                        result = grep_command(["Test", "-n"])
                        assert result == 0
                        # Check that line number is included
                        mock_print.assert_called_once()
                        output = mock_print.call_args[0][0]
                        assert "2:" in output
        finally:
            os.unlink(log_path)
    
    def test_log_file_not_found(self):
        """Test grep when log file is not found."""
        with patch('drtrace_service.cli.grep.get_default_log_path', return_value=None):
            with patch('drtrace_service.cli.grep.check_daemon_alive', return_value=False):
                result = grep_command(["pattern"])
                assert result == 2  # Error exit code
