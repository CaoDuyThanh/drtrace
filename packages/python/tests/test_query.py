"""Tests for query module with daemon-only flow (Story 11-3)."""

from unittest.mock import patch

from drtrace_service.query import QueryTimingInfo, query_logs


class TestQueryTimingInfo:
    """Tests for QueryTimingInfo."""

    def test_init(self):
        """Test initialization."""
        timing = QueryTimingInfo("daemon", 42.5)
        assert timing.source == "daemon"
        assert timing.elapsed_ms == 42.5

    def test_format_label_daemon(self):
        """Test formatting label for daemon."""
        timing = QueryTimingInfo("daemon", 42)
        label = timing.format_label()
        assert "42ms" in label
        assert "daemon" in label

    def test_format_label_db(self):
        """Test formatting label for database."""
        timing = QueryTimingInfo("local db", 187)
        label = timing.format_label()
        assert "187ms" in label
        assert "local db" in label


class TestQueryLogs:
    """Tests for query_logs function."""

    def test_time_window_exceeds_24h_without_flag(self):
        """Test that >24h requires --full-search."""
        results, timing, error = query_logs("pattern", hours=48)
        assert error is not None
        assert "exceeds 24 hours" in error
        assert len(results) == 0

    def test_time_window_exceeds_24h_with_flag(self):
        """Test that --full-search allows >24h (but daemon required)."""
        with patch("drtrace_service.query.check_daemon_alive", return_value=False):
            results, timing, error = query_logs("pattern", hours=48, full_search=True)
            # Daemon unavailable error, not time window error
            assert error is not None
            assert "daemon is not running" in error.lower()

    def test_daemon_unavailable_shows_helpful_error(self):
        """Test error message when daemon is not running (Story 11-3)."""
        with patch("drtrace_service.query.check_daemon_alive", return_value=False):
            results, timing, error = query_logs("pattern")
            assert error is not None
            assert "daemon is not running" in error.lower()
            assert "drtrace daemon start" in error.lower()
            assert len(results) == 0

    def test_daemon_available_returns_not_implemented(self):
        """Test that daemon path returns not implemented (TODO in code)."""
        with patch("drtrace_service.query.check_daemon_alive", return_value=True):
            results, timing, error = query_logs("pattern")
            assert error is not None
            assert "not yet fully implemented" in error.lower()
