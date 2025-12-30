"""
Quickstart example application for DrTrace.

This is a minimal example that demonstrates:
1. Integrating DrTrace into a Python application
2. Capturing structured logs with error context
3. Triggering an error that can be analyzed

Run this after:
1. Starting the DrTrace daemon: python -m drtrace_service
2. Setting DRTRACE_APPLICATION_ID environment variable (or it will default to "quickstart-app")
"""

import logging
import os
import time

from drtrace_client import setup_logging


def main():
    """Main function demonstrating DrTrace integration."""
    # Set application ID
    os.environ.setdefault("DRTRACE_APPLICATION_ID", "quickstart-app")
    
    # Configure logging
    logger = logging.getLogger("quickstart")
    logging.basicConfig(level=logging.INFO)
    
    # Integrate drtrace
    setup_logging(logger)
    
    # Log some normal activity
    logger.info("Application starting up")
    logger.info("Processing user request")
    
    # Trigger an error
    try:
        result = 100 / 0  # This will raise ZeroDivisionError
    except ZeroDivisionError:
        logger.exception("Division by zero error occurred")
    
    # Give the background log queue time to flush
    time.sleep(0.5)
    logger.info("Application shutting down")


if __name__ == "__main__":
    main()

