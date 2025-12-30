"""
Main entry point for the multi-module Python example.

This demonstrates DrTrace integration in a realistic multi-module application.
"""

import logging
import os
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from drtrace_client import setup_logging

from services.api_service import APIService
from services.data_service import DataService


def setup_logging_for_app():
    """Configure DrTrace logging for the application."""
    os.environ.setdefault("DRTRACE_APPLICATION_ID", "multi-module-app")
    
    # Configure root logger
    logger = logging.getLogger("multi_module_app")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Integrate DrTrace
    setup_logging(logger)
    
    return logger


def main():
    """Main application entry point."""
    logger = setup_logging_for_app()
    
    logger.info("Starting multi-module application")
    
    try:
        # Initialize services
        api_service = APIService()
        data_service = DataService()
        
        # Simulate normal operations
        logger.info("Processing user requests")
        api_service.handle_request("/api/users", {"user_id": "123"})
        api_service.handle_request("/api/data", {"query": "SELECT * FROM users"})
        
        # Simulate data processing
        logger.info("Processing data batches")
        data_service.process_batch([1, 2, 3, 4, 5])
        data_service.process_batch([10, 20, 30])
        
        # Trigger errors in different modules
        logger.info("Triggering intentional errors for demonstration")
        
        # Error in API service
        try:
            api_service.handle_request("/api/invalid", {})
        except Exception:
            logger.exception("Error in API service")
        
        # Error in data service
        try:
            data_service.process_batch([])  # Empty batch causes error
        except Exception:
            logger.exception("Error in data service")
        
        # Error in database utility
        try:
            from utils.database import Database
            db = Database()
            db.query("INVALID SQL")
        except Exception:
            logger.exception("Error in database utility")
        
        logger.info("Application completed")
        
    except Exception as e:
        logger.exception("Fatal error in main application")
        raise
    
    finally:
        # Give background queue time to flush
        time.sleep(1.0)


if __name__ == "__main__":
    main()

