"""
Python main component for multi-language example.

This demonstrates DrTrace integration in a Python component that works
alongside a C++ component.
"""

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from drtrace_client import setup_logging
from python_service import PythonService


def setup_logging_for_app():
    """Configure DrTrace logging for the application."""
    os.environ.setdefault("DRTRACE_APPLICATION_ID", "multi-language-app")
    
    # Configure root logger
    logger = logging.getLogger("python_main")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Integrate DrTrace
    setup_logging(logger)
    
    return logger


def run_cpp_component(cpp_binary_path: str):
    """Run the C++ component as a subprocess."""
    logger = logging.getLogger("python_main")
    
    logger.info("Starting C++ component", extra={
        "service_name": "multi-language-app",
        "module_name": "python_service",
    })
    
    try:
        result = subprocess.run(
            [cpp_binary_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.warning(
                f"C++ component exited with code {result.returncode}",
                extra={
                    "service_name": "multi-language-app",
                    "module_name": "python_service",
                }
            )
            if result.stderr:
                logger.error(f"C++ stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        logger.error("C++ component timed out")
    except FileNotFoundError:
        logger.error(f"C++ component not found at {cpp_binary_path}")
    except Exception as e:
        logger.exception(f"Error running C++ component: {e}")


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description="Multi-language example")
    parser.add_argument(
        "--with-cpp",
        action="store_true",
        help="Also run C++ component"
    )
    parser.add_argument(
        "--cpp-binary",
        default="./build/cpp_component",
        help="Path to C++ component binary"
    )
    args = parser.parse_args()
    
    logger = setup_logging_for_app()
    
    logger.info("Starting multi-language application", extra={
        "service_name": "multi-language-app",
        "module_name": "python_service",
    })
    
    try:
        # Initialize Python service
        service = PythonService()
        
        # Simulate normal operations
        logger.info("Processing Python operations", extra={
            "service_name": "multi-language-app",
            "module_name": "python_service",
        })
        
        service.process_data([1, 2, 3])
        service.compute_result(10, 20)
        
        # Trigger an error
        try:
            service.process_data([])  # Empty list causes error
        except Exception:
            logger.exception("Error in Python service", extra={
                "service_name": "multi-language-app",
                "module_name": "python_service",
            })
        
        # Optionally run C++ component
        if args.with_cpp:
            run_cpp_component(args.cpp_binary)
        
        logger.info("Python component completed", extra={
            "service_name": "multi-language-app",
            "module_name": "python_service",
        })
        
    except Exception as e:
        logger.exception("Fatal error in Python component", extra={
            "service_name": "multi-language-app",
            "module_name": "python_service",
        })
        raise
    
    finally:
        # Give background queue time to flush
        time.sleep(1.0)


if __name__ == "__main__":
    main()

