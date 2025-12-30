"""
Agent interface handler for log analysis.

This module provides the agent interface layer that processes natural language
queries and returns formatted responses using existing analysis functionality.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from . import analysis
from .query_parser import ParseResult, parse_query


async def check_daemon_status() -> Dict[str, any]:
    """
    Check if daemon is available by calling the status endpoint.

    Returns:
        Dict with status information, or None if daemon is unavailable
    """
    import json
    import urllib.error
    import urllib.parse
    import urllib.request

    host = os.getenv("DRTRACE_DAEMON_HOST", "localhost")
    port = int(os.getenv("DRTRACE_DAEMON_PORT", "8001"))
    url = f"http://{host}:{port}/status"

    try:
        with urllib.request.urlopen(url, timeout=2.0) as resp:  # nosec B310
            data = json.loads(resp.read().decode("utf-8"))
            return {"available": True, "data": data}
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
        return {"available": False, "error": "Daemon not reachable"}


async def process_agent_query(query: str, context: Optional[Dict[str, any]] = None) -> str:
    """
    Main entry point: process natural language query and return formatted response.

    Args:
        query: Natural language query string
        context: Optional context dict (e.g., default application_id, available applications)

    Returns:
        Formatted markdown response string
    """
    if context is None:
        context = {}

    # Check daemon status first
    status = await check_daemon_status()
    if not status.get("available"):
        return _format_daemon_unavailable_error()

    # Parse query
    parse_result = parse_query(query, context)

    # Check for missing required information
    if parse_result.missing_info:
        return _format_missing_info_response(parse_result)

    # Validate we have required parameters
    if not parse_result.start_ts or not parse_result.end_ts:
        return "❌ **Error**: Time range is required. Please specify a time range (e.g., 'from 9:00 to 10:00' or 'last 10 minutes')."

    if not parse_result.application_id:
        return "❌ **Error**: Application ID is required. Please specify an application (e.g., 'for app myapp')."

    # Call appropriate analysis based on intent
    if parse_result.intent in ("explain", "why"):
        return await _process_explain_query(parse_result)
    elif parse_result.intent in ("show", "query"):
        return await _process_show_query(parse_result)
    else:
        # Default to explain
        return await _process_explain_query(parse_result)


async def _process_explain_query(parse_result: ParseResult) -> str:
    """Process an 'explain' or 'why' query."""
    # Convert module_name/service_name to lists if needed
    module_names = [parse_result.module_name] if parse_result.module_name else None
    service_names = [parse_result.service_name] if parse_result.service_name else None

    # Call analysis function directly
    records = analysis.analyze_time_range(
        application_id=parse_result.application_id,
        start_ts=parse_result.start_ts,
        end_ts=parse_result.end_ts,
        min_level=parse_result.min_level,
        module_name=module_names,
        service_name=service_names,
        limit=100,
    )

    if not records:
        return _format_no_data_response(parse_result)

    # Prepare AI analysis input
    input_data = analysis.prepare_ai_analysis_input(records, context_lines=5)

    # Generate root-cause explanation
    explanation = analysis.generate_root_cause_explanation(input_data)

    # Format response
    return _format_explanation_response(explanation, parse_result, len(records))


async def _process_show_query(parse_result: ParseResult) -> str:
    """Process a 'show' or 'query' intent - just return logs."""
    # Convert module_name/service_name to lists if needed
    module_names = [parse_result.module_name] if parse_result.module_name else None
    service_names = [parse_result.service_name] if parse_result.service_name else None

    # Call analysis function directly
    records = analysis.analyze_time_range(
        application_id=parse_result.application_id,
        start_ts=parse_result.start_ts,
        end_ts=parse_result.end_ts,
        min_level=parse_result.min_level,
        module_name=module_names,
        service_name=service_names,
        limit=100,
    )

    if not records:
        return _format_no_data_response(parse_result)

    # Format logs response
    return _format_logs_response(records, parse_result)


def _format_explanation_response(explanation: analysis.RootCauseExplanation, parse_result: ParseResult, log_count: int) -> str:
    """Format root-cause explanation as markdown."""
    lines: List[str] = []

    lines.append("# Analysis Summary")
    lines.append("")
    if explanation.summary:
        lines.append(explanation.summary)
    else:
        lines.append("Analysis completed, but summary could not be extracted.")
    lines.append("")

    lines.append("## Root Cause")
    lines.append("")
    if explanation.root_cause:
        lines.append(explanation.root_cause)
    else:
        lines.append("Root cause analysis requires additional context or investigation.")
    lines.append("")

    # Error location
    if explanation.error_location:
        lines.append("## Error Location")
        lines.append("")
        loc = explanation.error_location
        if loc.get("file_path"):
            lines.append(f"- **File**: `{loc['file_path']}`")
        if loc.get("line_no"):
            lines.append(f"- **Line**: {loc['line_no']}")
        lines.append("")

    # Key evidence
    if explanation.key_evidence:
        lines.append("## Evidence")
        lines.append("")
        lines.append("### Logs")
        lines.append("")
        for evidence in explanation.key_evidence:
            lines.append(f"- {evidence}")
        lines.append("")

    # Evidence references with code context
    if explanation.evidence_references:
        code_refs = [ref for ref in explanation.evidence_references if ref.file_path]
        if code_refs:
            lines.append("### Code Context")
            lines.append("")
            for ref in code_refs[:5]:  # Limit to top 5
                if ref.file_path:
                    lines.append(f"- **`{ref.file_path}`**")
                    if ref.line_no:
                        lines.append(f"  - Line {ref.line_no}: {ref.reason}")
                    if ref.line_range:
                        r = ref.line_range
                        lines.append(f"  - Lines {r['start']}-{r['end']}")
            lines.append("")

    # Suggested fixes
    if explanation.suggested_fixes:
        lines.append("## Suggested Fixes")
        lines.append("")
        for i, fix in enumerate(explanation.suggested_fixes, 1):
            lines.append(f"{i}. **{fix.description}**")
            if fix.file_path:
                location_line = f"   - Location: `{fix.file_path}`"
                if fix.line_no:
                    location_line += f":{fix.line_no}"
                if fix.line_range:
                    r = fix.line_range
                    location_line += f" (lines {r['start']}-{r['end']})"
                lines.append(location_line)
            if fix.confidence and fix.confidence != "medium":
                lines.append(f"   - Confidence: {fix.confidence.upper()}")
        lines.append("")
    elif not explanation.has_clear_remediation:
        lines.append("## Suggested Fixes")
        lines.append("")
        lines.append("No clear remediation identified. Further investigation required.")
        lines.append("")

    # Confidence
    lines.append("## Confidence")
    lines.append("")
    lines.append(f"**{explanation.confidence.upper()}**")
    lines.append("")

    # Metadata
    lines.append("---")
    lines.append("")
    lines.append(f"**Application**: {parse_result.application_id}")
    lines.append(f"**Time Range**: {_format_timestamp(parse_result.start_ts)} to {_format_timestamp(parse_result.end_ts)}")
    lines.append(f"**Logs Analyzed**: {log_count}")
    if parse_result.module_name:
        lines.append(f"**Module**: {parse_result.module_name}")
    if parse_result.service_name:
        lines.append(f"**Service**: {parse_result.service_name}")

    return "\n".join(lines)


def _format_logs_response(records: List, parse_result: ParseResult) -> str:
    """Format logs list as markdown."""
    lines: List[str] = []

    lines.append("# Logs")
    lines.append("")
    lines.append(f"Found {len(records)} log(s) for the specified criteria.")
    lines.append("")

    for record in records[:20]:  # Limit to first 20
        lines.append(f"## {record.level} - {record.message}")
        lines.append("")
        lines.append(f"- **Timestamp**: {_format_timestamp(record.ts)}")
        if record.module_name:
            lines.append(f"- **Module**: {record.module_name}")
        if record.service_name:
            lines.append(f"- **Service**: {record.service_name}")
        if record.file_path:
            lines.append(f"- **File**: `{record.file_path}`")
            if record.line_no:
                lines.append(f"- **Line**: {record.line_no}")
        if record.exception_type:
            lines.append(f"- **Exception**: {record.exception_type}")
        lines.append("")

    if len(records) > 20:
        lines.append(f"*... and {len(records) - 20} more logs*")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"**Application**: {parse_result.application_id}")
    lines.append(f"**Time Range**: {_format_timestamp(parse_result.start_ts)} to {_format_timestamp(parse_result.end_ts)}")

    return "\n".join(lines)


def _format_missing_info_response(parse_result: ParseResult) -> str:
    """Format response when required information is missing."""
    lines: List[str] = []

    lines.append("❌ **Missing Required Information**")
    lines.append("")

    if "application_id" in parse_result.missing_info:
        lines.append("**Application ID** is required.")
        if "application_id" in parse_result.suggestions:
            apps = parse_result.suggestions["application_id"]
            lines.append(f"Available applications: {', '.join(apps)}")
        else:
            lines.append("Please specify an application (e.g., 'for app myapp').")
        lines.append("")

    if "time_range" in parse_result.missing_info:
        lines.append("**Time Range** is required.")
        lines.append("Please specify a time range (e.g., 'from 9:00 to 10:00' or 'last 10 minutes').")
        lines.append("")

    return "\n".join(lines)


def _format_no_data_response(parse_result: ParseResult) -> str:
    """Format response when no logs are found."""
    lines: List[str] = []

    lines.append("ℹ️ **No Logs Found**")
    lines.append("")
    lines.append(f"No logs found for application `{parse_result.application_id}`")
    lines.append(f"in the time range {_format_timestamp(parse_result.start_ts)} to {_format_timestamp(parse_result.end_ts)}.")
    lines.append("")

    if parse_result.module_name:
        lines.append(f"Filters applied: module={parse_result.module_name}")
    if parse_result.service_name:
        lines.append(f"Filters applied: service={parse_result.service_name}")
    if parse_result.min_level:
        lines.append(f"Filters applied: min_level={parse_result.min_level}")

    return "\n".join(lines)


def _format_daemon_unavailable_error() -> str:
    """Format error when daemon is unavailable."""
    host = os.getenv("DRTRACE_DAEMON_HOST", "localhost")
    port = int(os.getenv("DRTRACE_DAEMON_PORT", "8001"))

    lines: List[str] = []
    lines.append("❌ **Daemon Unavailable**")
    lines.append("")
    lines.append(f"Cannot connect to DrTrace daemon at `{host}:{port}`.")
    lines.append("")
    lines.append("**Next Steps:**")
    lines.append("1. Ensure the daemon is running:")
    lines.append("   ```bash")
    lines.append("   python -m drtrace_service")
    lines.append("   ```")
    lines.append("2. Check that the daemon is listening on the correct host/port")
    lines.append("3. Verify `DRTRACE_DAEMON_HOST` and `DRTRACE_DAEMON_PORT` environment variables if using custom settings")

    return "\n".join(lines)


def _format_timestamp(ts: float) -> str:
    """Format Unix timestamp as readable string."""
    from datetime import datetime

    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

