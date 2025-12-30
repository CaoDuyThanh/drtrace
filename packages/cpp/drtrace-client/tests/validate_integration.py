#!/usr/bin/env python3
"""
Validation script for C++ client integration.

This script helps verify that C++ logs can be ingested and stored
alongside Python logs using the unified schema.

Usage:
  1. Start the DrTrace daemon: python -m drtrace_service
  2. Build and run the C++ example: ./minimal_cpp_app
  3. Run this script: python validate_integration.py

The script queries the daemon to verify C++ logs were ingested.
"""

import json
import os
import sys
import time
from urllib import request, error

DAEMON_URL = os.getenv("DRTRACE_DAEMON_URL", "http://localhost:8001")
APPLICATION_ID = os.getenv("DRTRACE_APPLICATION_ID", "test-cpp-app")


def query_logs(start_ts: float, end_ts: float, application_id: str) -> dict:
    """Query logs from the daemon."""
    url = f"{DAEMON_URL}/logs/query?start_ts={start_ts}&end_ts={end_ts}&application_id={application_id}"
    try:
        with request.urlopen(url, timeout=5.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except (error.URLError, error.HTTPError) as e:
        print(f"Error querying daemon: {e}")
        return {"results": [], "count": 0}


def validate_cpp_logs():
    """Validate that C++ logs were ingested correctly."""
    print("Validating C++ client integration...")
    print(f"Daemon URL: {DAEMON_URL}")
    print(f"Application ID: {APPLICATION_ID}")
    print()

    # Query logs from the last minute
    end_ts = time.time()
    start_ts = end_ts - 60

    result = query_logs(start_ts, end_ts, APPLICATION_ID)

    if result["count"] == 0:
        print("❌ No logs found for the application.")
        print("   Make sure:")
        print("   1. The daemon is running (python -m drtrace_service)")
        print("   2. The C++ example was run with DRTRACE_APPLICATION_ID set")
        print("   3. Logs were sent within the last minute")
        return False

    print(f"✅ Found {result['count']} log record(s)")
    print()

    # Validate schema compliance
    all_valid = True
    for i, log in enumerate(result["results"], 1):
        print(f"Log {i}:")
        print(f"  Level: {log.get('level', 'MISSING')}")
        print(f"  Message: {log.get('message', 'MISSING')[:50]}...")
        print(f"  Module: {log.get('module_name', 'MISSING')}")

        # Check required fields
        required = ["ts", "level", "message", "application_id", "module_name"]
        missing = [f for f in required if f not in log or log[f] is None]
        if missing:
            print(f"  ❌ Missing required fields: {missing}")
            all_valid = False
        else:
            print("  ✅ All required fields present")

        # Check for C++ context
        context = log.get("context", {})
        if context.get("language") == "cpp":
            print("  ✅ C++ language marker found in context")
        else:
            print(f"  ⚠️  Language marker not found (context: {context})")

        print()

    if all_valid:
        print("✅ All logs comply with the unified schema!")
        return True
    else:
        print("❌ Some logs are missing required fields")
        return False


if __name__ == "__main__":
    success = validate_cpp_logs()
    sys.exit(0 if success else 1)

