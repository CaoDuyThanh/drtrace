"""Daemon health check module with 2-second caching and async support.

Provides non-blocking daemon availability checks for CLI commands.
Uses async/await to avoid blocking the main thread.
"""

import asyncio
import logging
import os
import time
from typing import Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class DaemonHealthChecker:
    """Checks daemon health via HTTP GET with caching and async support."""

    def __init__(self) -> None:
        """Initialize the health checker with cache."""
        self._cache: Optional[bool] = None
        self._cache_time: float = 0.0
        self._cache_duration: float = 2.0  # 2 seconds

    def _get_daemon_config(self) -> Tuple[str, int]:
        """Get daemon host and port from environment or defaults.

        Returns:
            Tuple of (host, port)
        """
        host = os.getenv("DRTRACE_DAEMON_HOST", "localhost")
        port = int(os.getenv("DRTRACE_DAEMON_PORT", "8001"))
        return host, port

    def _get_timeout_ms(self) -> int:
        """Get daemon check timeout from environment or default (500ms).

        Returns:
            Timeout in milliseconds
        """
        return int(os.getenv("DRTRACE_DAEMON_CHECK_TIMEOUT_MS", "500"))

    async def _check_daemon_async(self, timeout_ms: int) -> bool:
        """Check daemon health via HTTP GET (async).

        Args:
            timeout_ms: Timeout in milliseconds

        Returns:
            True if daemon responds with HTTP 200, False otherwise
        """
        host, port = self._get_daemon_config()
        url = f"http://{host}:{port}/status"
        timeout_seconds = timeout_ms / 1000.0

        start_time = time.time()

        try:
            logger.debug(f"Checking daemon health: GET {url} (timeout={timeout_ms}ms)")

            async with httpx.AsyncClient() as client:
                response = await asyncio.wait_for(
                    client.get(url, timeout=timeout_seconds),
                    timeout=timeout_seconds
                )

                elapsed_ms = int((time.time() - start_time) * 1000)

                if response.status_code == 200:
                    logger.debug(f"Daemon health check: OK (response time: {elapsed_ms}ms)")
                    return True
                else:
                    logger.debug(
                        f"Daemon health check: FAILED (status={response.status_code}, "
                        f"time={elapsed_ms}ms)"
                    )
                    return False

        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.debug(
                f"Daemon health check: TIMEOUT (exceeded {timeout_ms}ms, "
                f"elapsed={elapsed_ms}ms)"
            )
            return False

        except (httpx.ConnectError, httpx.RequestError, OSError) as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.debug(
                f"Daemon health check: UNREACHABLE (error={type(e).__name__}, "
                f"elapsed={elapsed_ms}ms)"
            )
            return False

    def check_daemon_alive(self, timeout_ms: Optional[int] = None) -> bool:
        """Check if daemon is alive (synchronous wrapper).

        Uses 2-second cache to avoid repeated requests. Non-blocking via asyncio.

        Args:
            timeout_ms: Timeout in milliseconds. If None, uses env var or default 500ms.

        Returns:
            True if daemon is healthy and responsive, False otherwise
        """
        # Use default timeout if not provided
        if timeout_ms is None:
            timeout_ms = self._get_timeout_ms()

        # Check cache
        now = time.time()
        if self._cache is not None and (now - self._cache_time) < self._cache_duration:
            logger.debug(
                f"Using cached daemon health result (age={int((now - self._cache_time) * 1000)}ms)"
            )
            return self._cache

        # Run async check
        try:
            # Create or get event loop for async execution
            try:
                loop = asyncio.get_running_loop()
                # If we're already in an async context, create a task
                raise RuntimeError(
                    "check_daemon_alive() called from async context. "
                    "Use check_daemon_alive_async() instead."
                )
            except RuntimeError:
                # No running loop, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    result = loop.run_until_complete(
                        self._check_daemon_async(timeout_ms)
                    )
                finally:
                    loop.close()
        except Exception as e:
            logger.debug(f"Daemon health check exception: {type(e).__name__}: {e}")
            result = False

        # Update cache
        self._cache = result
        self._cache_time = now

        return result

    async def check_daemon_alive_async(
        self, timeout_ms: Optional[int] = None
    ) -> bool:
        """Check if daemon is alive (async version).

        Uses 2-second cache to avoid repeated requests.

        Args:
            timeout_ms: Timeout in milliseconds. If None, uses env var or default 500ms.

        Returns:
            True if daemon is healthy and responsive, False otherwise
        """
        # Use default timeout if not provided
        if timeout_ms is None:
            timeout_ms = self._get_timeout_ms()

        # Check cache
        now = time.time()
        if self._cache is not None and (now - self._cache_time) < self._cache_duration:
            logger.debug(
                f"Using cached daemon health result (age={int((now - self._cache_time) * 1000)}ms)"
            )
            return self._cache

        # Run async check
        try:
            result = await self._check_daemon_async(timeout_ms)
        except Exception as e:
            logger.debug(f"Daemon health check exception: {type(e).__name__}: {e}")
            result = False

        # Update cache
        self._cache = result
        self._cache_time = now

        return result


# Global instance for CLI use
_health_checker = DaemonHealthChecker()


def check_daemon_alive(timeout_ms: Optional[int] = None) -> bool:
    """Convenience function using global health checker instance.

    Args:
        timeout_ms: Timeout in milliseconds. If None, uses env var or default 500ms.

    Returns:
        True if daemon is healthy and responsive, False otherwise
    """
    return _health_checker.check_daemon_alive(timeout_ms)


async def check_daemon_alive_async(timeout_ms: Optional[int] = None) -> bool:
    """Convenience async function using global health checker instance.

    Args:
        timeout_ms: Timeout in milliseconds. If None, uses env var or default 500ms.

    Returns:
        True if daemon is healthy and responsive, False otherwise
    """
    return await _health_checker.check_daemon_alive_async(timeout_ms)
