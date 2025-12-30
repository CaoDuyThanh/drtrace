"""
LangChain Integration Example for DrTrace Analysis API

This example shows how to integrate DrTrace's HTTP API into a LangChain agent or tool.
The example demonstrates calling the /analysis/why endpoint and processing the response.

Prerequisites:
    pip install langchain requests

Usage:
    # In your LangChain agent setup:
    from langchain_integration import DrTraceAnalysisTool
    
    tool = DrTraceAnalysisTool(daemon_url="http://localhost:8001")
    agent = initialize_agent([tool], llm, agent="zero-shot-react-description")
"""

import json
import os
import sys
import time
from typing import Optional
from urllib.parse import urlencode

try:
    import requests
except ImportError:
    print("Error: 'requests' library is required for this example.")
    print("Install it with: pip install requests")
    sys.exit(1)


class DrTraceAnalysisTool:
    """
    LangChain-compatible tool for DrTrace root-cause analysis.
    
    This tool can be added to a LangChain agent to enable log analysis capabilities.
    """
    
    def __init__(self, daemon_url: str = "http://localhost:8001"):
        """
        Initialize the DrTrace analysis tool.
        
        Args:
            daemon_url: Base URL of the DrTrace daemon (default: http://localhost:8001)
        """
        self.daemon_url = daemon_url.rstrip("/")
        self.base_url = f"{self.daemon_url}"
    
    def analyze_why(
        self,
        application_id: str,
        start_ts: Optional[float] = None,
        end_ts: Optional[float] = None,
        since: Optional[str] = None,  # e.g., "10m", "1h"
        min_level: Optional[str] = None,
        module_name: Optional[str] = None,
        service_name: Optional[str] = None,
        limit: int = 100,
    ) -> dict:
        """
        Call the /analysis/why endpoint to get root-cause explanations.
        
        Args:
            application_id: Application identifier (required)
            start_ts: Start timestamp (Unix timestamp)
            end_ts: End timestamp (Unix timestamp)
            since: Relative time window (e.g., "10m", "1h") - used if start_ts/end_ts not provided
            min_level: Minimum log level (DEBUG, INFO, WARN, ERROR, CRITICAL)
            module_name: Optional module name filter
            service_name: Optional service name filter
            limit: Maximum number of records to return
        
        Returns:
            Dictionary with analysis results
        """
        # Calculate time range if 'since' is provided
        if since and not (start_ts and end_ts):
            now = time.time()
            since_lower = since.lower().strip()
            try:
                if since_lower.endswith("s"):
                    seconds = int(since_lower[:-1])
                elif since_lower.endswith("m"):
                    seconds = int(since_lower[:-1]) * 60
                elif since_lower.endswith("h"):
                    seconds = int(since_lower[:-1]) * 3600
                elif since_lower.endswith("d"):
                    seconds = int(since_lower[:-1]) * 86400
                else:
                    seconds = int(since_lower)
                start_ts = now - seconds
                end_ts = now
            except ValueError:
                raise ValueError(f"Invalid time format: {since}. Use format like '5m', '1h', '30s'")
        
        if not start_ts or not end_ts:
            raise ValueError("Either start_ts/end_ts or 'since' must be provided")
        
        # Build query parameters
        params = {
            "application_id": application_id,
            "start_ts": start_ts,
            "end_ts": end_ts,
            "limit": limit,
        }
        
        if min_level:
            params["min_level"] = min_level.upper()
        if module_name:
            params["module_name"] = module_name
        if service_name:
            params["service_name"] = service_name
        
        # Make HTTP request
        url = f"{self.base_url}/analysis/why"
        response = requests.get(url, params=params, timeout=30.0)
        response.raise_for_status()
        
        return response.json()
    
    def format_explanation(self, result: dict) -> str:
        """
        Format the analysis result as a readable string.
        
        Args:
            result: JSON response from /analysis/why endpoint
        
        Returns:
            Formatted markdown string
        """
        data = result.get("data", {})
        explanation = data.get("explanation", {})
        meta = result.get("meta", {})
        
        lines = []
        
        if explanation.get("summary"):
            lines.append(f"## Summary\n{explanation['summary']}\n")
        
        if explanation.get("root_cause"):
            lines.append(f"## Root Cause\n{explanation['root_cause']}\n")
        
        if explanation.get("suggested_fixes"):
            lines.append("## Suggested Fixes")
            for i, fix in enumerate(explanation["suggested_fixes"], 1):
                lines.append(f"{i}. {fix.get('description', 'Fix')}")
                if fix.get("file_path"):
                    loc = f"`{fix['file_path']}`"
                    if fix.get("line_no"):
                        loc += f":{fix['line_no']}"
                    lines.append(f"   Location: {loc}")
            lines.append("")
        
        if explanation.get("confidence"):
            lines.append(f"**Confidence**: {explanation['confidence'].upper()}\n")
        
        lines.append(f"**Logs Analyzed**: {meta.get('count', 0)}")
        
        return "\n".join(lines)
    
    def run(self, query: str) -> str:
        """
        LangChain-compatible run method.
        
        This method can be used directly as a LangChain tool.
        
        Args:
            query: Natural language query (will be parsed for parameters)
        
        Returns:
            Formatted explanation string
        """
        # For a full implementation, you would parse the query here
        # For this example, we'll use a simple format: "analyze app <app_id> since <time>"
        # In production, you might use the query_parser module
        
        # Simple parsing (production would use query_parser)
        parts = query.lower().split()
        app_id = None
        since = None
        
        for i, part in enumerate(parts):
            if part == "app" and i + 1 < len(parts):
                app_id = parts[i + 1]
            elif part == "since" and i + 1 < len(parts):
                since = parts[i + 1]
        
        if not app_id:
            return "Error: Application ID required. Format: 'analyze app <app_id> since <time>'"
        
        if not since:
            since = "10m"  # Default to last 10 minutes
        
        try:
            result = self.analyze_why(application_id=app_id, since=since)
            return self.format_explanation(result)
        except Exception as e:
            return f"Error: {str(e)}"


def example_langchain_usage():
    """Example of using the DrTrace tool in a LangChain agent."""
    print("=" * 70)
    print("LangChain Integration Example")
    print("=" * 70)
    print()
    
    # Initialize the tool
    tool = DrTraceAnalysisTool(daemon_url="http://localhost:8001")
    
    # Example 1: Direct API call
    print("Example 1: Direct API call")
    print("-" * 70)
    try:
        result = tool.analyze_why(
            application_id="myapp",
            since="10m",  # Last 10 minutes
            min_level="ERROR",
        )
        
        formatted = tool.format_explanation(result)
        print(formatted)
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. The DrTrace daemon is running (python -m drtrace_service)")
        print("2. You have logs in the database for the specified time range")
    
    print()
    
    # Example 2: Using as LangChain tool
    print("=" * 70)
    print("Example 2: Using as LangChain tool")
    print("-" * 70)
    print("Tool description:", tool.run.__doc__)
    print()
    
    # Simulate LangChain tool call
    query = "analyze app myapp since 10m"
    print(f"Query: {query}")
    result = tool.run(query)
    print(result)


if __name__ == "__main__":
    print("Note: This example requires the DrTrace daemon to be running.")
    print("Start it with: python -m drtrace_service")
    print()
    
    try:
        example_langchain_usage()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

