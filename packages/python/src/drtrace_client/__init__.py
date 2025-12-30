"""
drtrace_client

Lightweight DrTrace logging client that enriches log records and queues
them for delivery to the local log analysis daemon.
"""

from .config import ClientConfig
from .logging_setup import setup_logging

__all__ = ["ClientConfig", "setup_logging"]


