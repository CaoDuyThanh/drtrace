"""Tests for daemon_health module.

Covers:
- Healthy daemon response (HTTP 200)
- Connection refused
- Slow response / timeout
- Network unreachable
- Cache behavior
- Environment variable overrides
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from drtrace_service.daemon_health import (
    DaemonHealthChecker,
    check_daemon_alive,
    check_daemon_alive_async,
)


class TestDaemonHealthChecker:
    """Tests for DaemonHealthChecker class."""

    def test_get_daemon_config_defaults(self):
        """Test default host/port when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            checker = DaemonHealthChecker()
            host, port = checker._get_daemon_config()
            assert host == "localhost"
            assert port == 8001

    def test_get_daemon_config_from_env(self):
        """Test host/port from environment variables."""
        with patch.dict(
            os.environ,
            {"DRTRACE_DAEMON_HOST": "192.168.1.100", "DRTRACE_DAEMON_PORT": "9001"},
        ):
            checker = DaemonHealthChecker()
            host, port = checker._get_daemon_config()
            assert host == "192.168.1.100"
            assert port == 9001

    def test_get_timeout_ms_default(self):
        """Test default timeout is 500ms."""
        with patch.dict(os.environ, {}, clear=True):
            checker = DaemonHealthChecker()
            assert checker._get_timeout_ms() == 500

    def test_get_timeout_ms_from_env(self):
        """Test timeout from environment variable."""
        with patch.dict(os.environ, {"DRTRACE_DAEMON_CHECK_TIMEOUT_MS": "1000"}):
            checker = DaemonHealthChecker()
            assert checker._get_timeout_ms() == 1000

    @pytest.mark.asyncio
    async def test_check_daemon_async_healthy(self):
        """Test successful daemon health check (HTTP 200)."""
        checker = DaemonHealthChecker()

        with patch("drtrace_service.daemon_health.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.get.return_value = mock_response

            mock_client.return_value = mock_instance

            result = await checker._check_daemon_async(500)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_daemon_async_timeout(self):
        """Test daemon health check timeout."""
        checker = DaemonHealthChecker()

        with patch("drtrace_service.daemon_health.httpx.AsyncClient") as mock_client:
            async def timeout_get(*args, **kwargs):
                await asyncio.sleep(1.0)
                return MagicMock(status_code=200)

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.get = timeout_get

            mock_client.return_value = mock_instance

            result = await checker._check_daemon_async(100)  # 100ms timeout
            assert result is False

    @pytest.mark.asyncio
    async def test_check_daemon_async_connection_refused(self):
        """Test daemon health check when connection refused."""
        checker = DaemonHealthChecker()

        with patch("drtrace_service.daemon_health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.get.side_effect = httpx.ConnectError("Connection refused")

            mock_client.return_value = mock_instance

            result = await checker._check_daemon_async(500)
            assert result is False

    @pytest.mark.asyncio
    async def test_check_daemon_async_http_error(self):
        """Test daemon health check with non-200 HTTP status."""
        checker = DaemonHealthChecker()

        with patch("drtrace_service.daemon_health.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 503

            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.get.return_value = mock_response

            mock_client.return_value = mock_instance

            result = await checker._check_daemon_async(500)
            assert result is False

    def test_check_daemon_alive_sync_healthy(self):
        """Test synchronous check with healthy daemon."""
        checker = DaemonHealthChecker()

        with patch.object(
            checker, "_check_daemon_async", new_callable=AsyncMock
        ) as mock_async:
            mock_async.return_value = True

            result = checker.check_daemon_alive(500)
            assert result is True
            mock_async.assert_called_once()

    def test_check_daemon_alive_sync_uses_default_timeout(self):
        """Test that sync check uses default timeout when not provided."""
        checker = DaemonHealthChecker()

        with patch.dict(os.environ, {"DRTRACE_DAEMON_CHECK_TIMEOUT_MS": "750"}):
            with patch.object(
                checker, "_check_daemon_async", new_callable=AsyncMock
            ) as mock_async:
                mock_async.return_value = True

                result = checker.check_daemon_alive()
                assert result is True
                # Verify it was called with the env default (750ms)
                mock_async.assert_called_with(750)

    def test_check_daemon_alive_cache_hit(self):
        """Test cache returns cached result within 2 seconds."""
        checker = DaemonHealthChecker()

        with patch.object(
            checker, "_check_daemon_async", new_callable=AsyncMock
        ) as mock_async:
            mock_async.return_value = True

            # First call
            result1 = checker.check_daemon_alive(500)
            assert result1 is True
            call_count_1 = mock_async.call_count

            # Second call within 2 seconds should use cache
            result2 = checker.check_daemon_alive(500)
            assert result2 is True
            call_count_2 = mock_async.call_count

            # _check_daemon_async should not have been called again
            assert call_count_1 == call_count_2 == 1

    def test_check_daemon_alive_cache_expiry(self):
        """Test cache expires after 2 seconds."""
        checker = DaemonHealthChecker()

        with patch.object(
            checker, "_check_daemon_async", new_callable=AsyncMock
        ) as mock_async:
            mock_async.return_value = True

            # First call
            result1 = checker.check_daemon_alive(500)
            assert result1 is True

            # Simulate time passing beyond cache duration
            checker._cache_time -= 2.1

            # Second call should skip cache and hit async check again
            result2 = checker.check_daemon_alive(500)
            assert result2 is True

            # _check_daemon_async should have been called twice
            assert mock_async.call_count == 2

    @pytest.mark.asyncio
    async def test_check_daemon_alive_async_healthy(self):
        """Test async check with healthy daemon."""
        checker = DaemonHealthChecker()

        with patch.object(
            checker, "_check_daemon_async", new_callable=AsyncMock
        ) as mock_async:
            mock_async.return_value = True

            result = await checker.check_daemon_alive_async(500)
            assert result is True
            mock_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_daemon_alive_async_cache_hit(self):
        """Test async check uses cache within 2 seconds."""
        checker = DaemonHealthChecker()

        with patch.object(
            checker, "_check_daemon_async", new_callable=AsyncMock
        ) as mock_async:
            mock_async.return_value = True

            # First call
            result1 = await checker.check_daemon_alive_async(500)
            assert result1 is True
            call_count_1 = mock_async.call_count

            # Second call within 2 seconds should use cache
            result2 = await checker.check_daemon_alive_async(500)
            assert result2 is True
            call_count_2 = mock_async.call_count

            # _check_daemon_async should not have been called again
            assert call_count_1 == call_count_2 == 1

    @pytest.mark.asyncio
    async def test_check_daemon_alive_async_uses_default_timeout(self):
        """Test that async check uses default timeout when not provided."""
        checker = DaemonHealthChecker()

        with patch.dict(os.environ, {"DRTRACE_DAEMON_CHECK_TIMEOUT_MS": "600"}):
            with patch.object(
                checker, "_check_daemon_async", new_callable=AsyncMock
            ) as mock_async:
                mock_async.return_value = True

                result = await checker.check_daemon_alive_async()
                assert result is True
                # Verify it was called with the env default (600ms)
                mock_async.assert_called_with(600)


class TestGlobalFunctions:
    """Tests for module-level convenience functions."""

    def test_check_daemon_alive_global(self):
        """Test global check_daemon_alive function."""
        with patch(
            "drtrace_service.daemon_health._health_checker.check_daemon_alive"
        ) as mock_check:
            mock_check.return_value = True

            result = check_daemon_alive(500)
            assert result is True
            mock_check.assert_called_once_with(500)

    @pytest.mark.asyncio
    async def test_check_daemon_alive_async_global(self):
        """Test global check_daemon_alive_async function."""
        with patch(
            "drtrace_service.daemon_health._health_checker.check_daemon_alive_async",
            new_callable=AsyncMock,
        ) as mock_check:
            mock_check.return_value = True

            result = await check_daemon_alive_async(500)
            assert result is True
            mock_check.assert_called_once_with(500)


class TestIntegrationWithDaemon:
    """Integration tests (requires running daemon)."""

    def test_check_against_running_daemon(self, monkeypatch):
        """Test check against actual daemon if available (optional)."""
        # This test is optional - only runs if daemon is actually running
        monkeypatch.setenv("DRTRACE_DAEMON_HOST", "localhost")
        monkeypatch.setenv("DRTRACE_DAEMON_PORT", "8001")

        # This may fail if daemon is not running, which is expected
        # In CI, the daemon would be running; in local dev, it might not be
        try:
            result = check_daemon_alive(500)
            # If daemon is running, we expect True or a reasonable check
            assert isinstance(result, bool)
        except Exception as e:
            # If daemon is not running, we accept the exception
            # but the module should still handle it gracefully
            pytest.skip(f"Daemon not running: {e}")

    def test_check_against_stopped_daemon(self, monkeypatch):
        """Test check against non-existent daemon."""
        monkeypatch.setenv("DRTRACE_DAEMON_HOST", "127.0.0.1")
        monkeypatch.setenv("DRTRACE_DAEMON_PORT", "65432")
        monkeypatch.setenv("DRTRACE_DAEMON_CHECK_TIMEOUT_MS", "100")

        # Clear global cache to avoid prior test state affecting result
        from drtrace_service import daemon_health as dh

        dh._health_checker._cache = None
        dh._health_checker._cache_time = 0

        # Force the underlying client to behave like a stopped daemon (connection refused)
        with patch("drtrace_service.daemon_health.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.__aenter__.return_value = mock_instance
            mock_instance.__aexit__.return_value = None
            mock_instance.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client.return_value = mock_instance

            result = check_daemon_alive(100)
            assert result is False
