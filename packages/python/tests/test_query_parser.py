"""
Tests for natural language query parser (Story 6.6).

These tests verify:
- Time range parsing (absolute and relative)
- Filter extraction (application_id, service_name, module_name, level)
- Intent detection
- Missing information detection
- Edge cases and error handling
"""

import time
from datetime import datetime

from drtrace_service.query_parser import (
    detect_intent,
    extract_filters,
    parse_query,
    parse_time_range,
)


def test_parse_time_range_absolute_from_to():
    """Test parsing absolute time range: 'from 9:00 to 10:00'."""
    start_ts, end_ts = parse_time_range("from 9:00 to 10:00")

    assert start_ts is not None
    assert end_ts is not None
    assert end_ts > start_ts

    # Verify times are on today
    start_dt = datetime.fromtimestamp(start_ts)
    end_dt = datetime.fromtimestamp(end_ts)
    assert start_dt.hour == 9
    assert start_dt.minute == 0
    assert end_dt.hour == 10
    assert end_dt.minute == 0


def test_parse_time_range_absolute_with_ampm():
    """Test parsing absolute time range with AM/PM: 'between 2:30 PM and 2:35 PM'."""
    start_ts, end_ts = parse_time_range("between 2:30 PM and 2:35 PM")

    assert start_ts is not None
    assert end_ts is not None
    assert end_ts > start_ts

    start_dt = datetime.fromtimestamp(start_ts)
    end_dt = datetime.fromtimestamp(end_ts)
    assert start_dt.hour == 14  # 2:30 PM = 14:30
    assert start_dt.minute == 30
    assert end_dt.hour == 14
    assert end_dt.minute == 35


def test_parse_time_range_relative_last_minutes():
    """Test parsing relative time: 'last 5 minutes'."""
    time.time()
    start_ts, end_ts = parse_time_range("last 5 minutes")
    after = time.time()

    assert start_ts is not None
    assert end_ts is not None
    assert end_ts > start_ts
    assert abs(end_ts - after) < 1  # Should be very close to now
    assert abs((end_ts - start_ts) - 300) < 1  # Should be ~5 minutes (300 seconds)


def test_parse_time_range_relative_minutes_ago():
    """Test parsing relative time: '10 minutes ago'."""
    time.time()
    start_ts, end_ts = parse_time_range("what happened 10 minutes ago")
    after = time.time()

    assert start_ts is not None
    assert end_ts is not None
    assert end_ts > start_ts
    assert abs(end_ts - after) < 1
    assert abs((end_ts - start_ts) - 600) < 1  # Should be ~10 minutes


def test_parse_time_range_relative_past_hour():
    """Test parsing relative time: 'past hour'."""
    start_ts, end_ts = parse_time_range("past hour")

    assert start_ts is not None
    assert end_ts is not None
    assert end_ts > start_ts
    assert abs((end_ts - start_ts) - 3600) < 1  # Should be ~1 hour


def test_parse_time_range_with_date():
    """Test parsing time range with specific date: 'on 2025-01-27 from 10:00 to 11:00'."""
    start_ts, end_ts = parse_time_range("on 2025-01-27 from 10:00 to 11:00")

    assert start_ts is not None
    assert end_ts is not None

    start_dt = datetime.fromtimestamp(start_ts)
    end_dt = datetime.fromtimestamp(end_ts)
    assert start_dt.year == 2025
    assert start_dt.month == 1
    assert start_dt.day == 27
    assert start_dt.hour == 10
    assert end_dt.hour == 11


def test_parse_time_range_no_match():
    """Test parsing query with no time range."""
    start_ts, end_ts = parse_time_range("show me logs")

    assert start_ts is None
    assert end_ts is None


def test_extract_filters_application_id():
    """Test extracting application_id from query."""
    filters = extract_filters("for app myapp explain error")

    assert filters["application_id"] == "myapp"


def test_extract_filters_service_name():
    """Test extracting service_name from query."""
    filters = extract_filters("from service auth show errors")

    assert filters["service_name"] == "auth"


def test_extract_filters_module_name():
    """Test extracting module_name from query."""
    filters = extract_filters("module data_processor errors")

    assert filters["module_name"] == "data_processor"


def test_extract_filters_log_level():
    """Test extracting log level from query."""
    filters = extract_filters("show errors only")

    assert filters["min_level"] == "ERROR"

    filters = extract_filters("warnings and above")
    assert filters["min_level"] == "WARN"


def test_extract_filters_from_context():
    """Test that filters can be provided via context."""
    context = {"application_id": "default-app"}
    filters = extract_filters("show logs", context)

    assert filters["application_id"] == "default-app"


def test_detect_intent_explain():
    """Test detecting 'explain' intent."""
    assert detect_intent("explain error") == "explain"
    assert detect_intent("explain why error happened") == "explain"


def test_detect_intent_why():
    """Test detecting 'why' intent."""
    assert detect_intent("why did this error happen") == "why"


def test_detect_intent_show():
    """Test detecting 'show' intent."""
    assert detect_intent("show logs") == "show"


def test_detect_intent_query():
    """Test detecting 'query' intent."""
    assert detect_intent("query logs") == "query"
    assert detect_intent("get logs") == "query"


def test_detect_intent_default_error():
    """Test that queries mentioning 'error' default to 'explain'."""
    assert detect_intent("what error happened") == "explain"


def test_parse_query_complete():
    """Test parsing a complete query with all information."""
    query = "help me explain why error happen from 9:00 to 10:00 for app myapp"
    result = parse_query(query)

    assert result.intent == "explain"
    assert result.start_ts is not None
    assert result.end_ts is not None
    assert result.application_id == "myapp"
    assert len(result.missing_info) == 0


def test_parse_query_complex_filters():
    """Test parsing query with multiple filters."""
    query = "show errors from module data_processor between 2:30 PM and 2:35 PM"
    result = parse_query(query)

    assert result.intent == "show"
    assert result.start_ts is not None
    assert result.end_ts is not None
    assert result.module_name == "data_processor"
    assert result.min_level == "ERROR"


def test_parse_query_missing_application_id():
    """Test parsing query missing required application_id."""
    query = "explain error from 9:00 to 10:00"
    result = parse_query(query)

    assert result.intent == "explain"
    assert result.start_ts is not None
    assert result.end_ts is not None
    assert result.application_id is None
    assert "application_id" in result.missing_info


def test_parse_query_missing_time_range():
    """Test parsing query missing time range."""
    query = "explain error for app myapp"
    result = parse_query(query)

    assert result.intent == "explain"
    assert result.application_id == "myapp"
    assert result.start_ts is None
    assert result.end_ts is None
    assert "time_range" in result.missing_info


def test_parse_query_with_suggestions():
    """Test that suggestions are provided when available applications are in context."""
    context = {"available_applications": ["app1", "app2", "app3"]}
    query = "explain error from 9:00 to 10:00"
    result = parse_query(query, context)

    assert "application_id" in result.missing_info
    assert "application_id" in result.suggestions
    assert result.suggestions["application_id"] == ["app1", "app2", "app3"]


def test_parse_query_relative_time():
    """Test parsing query with relative time."""
    query = "what happened in the last 10 minutes for app myapp"
    result = parse_query(query)

    assert result.intent == "explain"
    assert result.start_ts is not None
    assert result.end_ts is not None
    assert result.application_id == "myapp"
    assert abs((result.end_ts - result.start_ts) - 600) < 1  # ~10 minutes


def test_parse_query_edge_case_no_time():
    """Test parsing query with no time information."""
    query = "show logs for app myapp"
    result = parse_query(query)

    assert result.intent == "show"
    assert result.application_id == "myapp"
    assert result.start_ts is None
    assert result.end_ts is None
    assert "time_range" in result.missing_info


def test_parse_query_edge_case_ambiguous_time():
    """Test parsing query with ambiguous time format."""
    # This should still attempt to parse, even if ambiguous
    query = "explain error from 9 to 10"
    result = parse_query(query)

    # May or may not parse successfully, but shouldn't crash
    assert result.intent == "explain"


def test_parse_query_multiple_filters():
    """Test parsing query with multiple filters."""
    query = "show errors from service auth module data_processor for app myapp"
    result = parse_query(query)

    assert result.service_name == "auth"
    assert result.module_name == "data_processor"
    assert result.application_id == "myapp"
    assert result.min_level == "ERROR"


def test_parse_query_case_insensitive():
    """Test that parsing is case-insensitive."""
    query = "EXPLAIN ERROR FROM 9:00 TO 10:00 FOR APP MYAPP"
    result = parse_query(query)

    assert result.intent == "explain"
    assert result.application_id == "myapp"
    assert result.start_ts is not None
    assert result.end_ts is not None

