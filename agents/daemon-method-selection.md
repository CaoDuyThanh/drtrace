# Daemon Method Selection Guide

**Purpose**: Guide for AI agents to choose the right method for daemon interaction.

**Key Principle**: For AI agents, prefer **HTTP/curl first** (simpler, no dependencies), then Python, then CLI.

---

## Priority Order for AI Agents

| Priority | Method | When to Use |
|----------|--------|-------------|
| **1st** | HTTP/curl | Default - works without dependencies |
| **2nd** | Python code | When rich SDK features needed |
| **3rd** | CLI commands | Last resort - requires subprocess |

### Why HTTP-First for AI Agents?

- **No dependencies**: Just HTTP requests - works in any environment
- **Simpler**: curl commands are self-contained and portable
- **Faster**: No import overhead or Python interpreter startup
- **Universal**: Works from any language or tool

---

## Discovery First: OpenAPI Schema

**CRITICAL**: Before making any API call, fetch `/openapi.json` to discover:
- Available endpoints
- Correct field names (e.g., `ts` not `timestamp`)
- Request/response schemas

```bash
# Always fetch schema first
curl http://localhost:8001/openapi.json
```

```python
import requests

base_url = "http://localhost:8001"

# Fetch schema to discover endpoints and field names
schema = requests.get(f"{base_url}/openapi.json", timeout=5).json()
paths = schema.get("paths", {})
components = schema.get("components", {}).get("schemas", {})

# Use discovered field names, not hardcoded ones
```

**Why this matters**: API field names can change between versions. Using OpenAPI ensures compatibility.

---

## Method 1: HTTP/curl (Preferred)

### Check Daemon Status

```bash
curl http://localhost:8001/status
```

### Query Logs

```bash
# Get logs from last 5 minutes
START_TS=$(python3 -c "import time; print(time.time() - 300)")
END_TS=$(python3 -c "import time; print(time.time())")

curl "http://localhost:8001/logs/query?start_ts=${START_TS}&end_ts=${END_TS}&application_id=myapp&limit=100"
```

### Root Cause Analysis

```bash
curl "http://localhost:8001/analysis/why?application_id=myapp&start_ts=${START_TS}&end_ts=${END_TS}&min_level=ERROR"
```

### Python requests (HTTP method)

```python
import requests
import time

base_url = "http://localhost:8001"

# Step 1: Check daemon status
try:
    status = requests.get(f"{base_url}/status", timeout=2)
    if status.status_code != 200:
        print("Daemon not available")
except requests.exceptions.RequestException:
    print("Daemon not reachable")

# Step 2: Query logs
now = time.time()
params = {
    "start_ts": now - 300,  # 5 minutes ago
    "end_ts": now,
    "application_id": "myapp",
    "limit": 100
}
response = requests.get(f"{base_url}/logs/query", params=params, timeout=10)
logs = response.json().get("results", [])

# Step 3: Process using field names from OpenAPI schema
for log in logs:
    ts = log.get("ts")  # Use 'ts' not 'timestamp' (from schema)
    level = log.get("level")
    message = log.get("message")
```

---

## Method 2: Python Code (Fallback)

Use when you need rich SDK features or the HTTP method fails.

### Log Analysis

```python
from drtrace_service.agent_interface import process_agent_query, check_daemon_status
import asyncio

# Check daemon first
status = await check_daemon_status()
if not status.get("available"):
    print("Daemon not available")

# Process query - returns formatted markdown
response = await process_agent_query("explain error from 9:00 to 10:00 for app myapp")
print(response)

# Non-async context
response = asyncio.run(process_agent_query("show logs from last 5 minutes"))
```

### Setup Help

```python
from drtrace_service.help_agent_interface import (
    start_setup_guide,
    get_current_step,
    complete_step,
    troubleshoot,
)
from pathlib import Path
import asyncio

project_root = Path(".")

# Start setup guide
guide = await start_setup_guide(language="python", project_root=project_root)

# Get current step
current = await get_current_step(project_root=project_root)

# Mark step complete
next_step = await complete_step(step_number=1, project_root=project_root)

# Troubleshoot
help_text = await troubleshoot("daemon not connecting", project_root=project_root)
```

### Setup Suggestions

```python
from drtrace_service.setup_agent_interface import analyze_and_suggest, suggest_for_language
from pathlib import Path
import asyncio

project_root = Path(".")

# Get setup suggestions
suggestions = await analyze_and_suggest(project_root)

# Language-specific suggestions
python_suggestions = await suggest_for_language("python", project_root)
cpp_suggestions = await suggest_for_language("cpp", project_root)
```

---

## Method 3: CLI Commands (Last Resort)

Use only when HTTP and Python methods are unavailable.

### Check Status

```bash
python -m drtrace_service status
```

### Analyze Errors

```bash
python -m drtrace_service why --application-id myapp --since 5m --min-level ERROR
```

### Setup Help

```bash
python -m drtrace_service help guide start --language python --project-root /path/to/project
python -m drtrace_service help guide current --project-root /path/to/project
```

---

## Error Handling and Fallback Chain

```python
import requests

def interact_with_daemon(query: str) -> str:
    """Try methods in order: HTTP -> Python -> CLI"""
    base_url = "http://localhost:8001"

    # Method 1: HTTP (Preferred)
    try:
        # Check status first
        status = requests.get(f"{base_url}/status", timeout=2)
        if status.status_code == 200:
            # Make actual request...
            return "Success via HTTP"
    except requests.exceptions.RequestException:
        pass  # Fall through to Python

    # Method 2: Python (Fallback)
    try:
        from drtrace_service.agent_interface import process_agent_query
        import asyncio
        response = asyncio.run(process_agent_query(query))
        return response
    except ImportError:
        pass  # Fall through to CLI

    # Method 3: CLI (Last Resort)
    import subprocess
    result = subprocess.run(
        ["python", "-m", "drtrace_service", "status"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        return result.stdout

    # All methods failed
    return """
    Daemon is not available.

    Next Steps:
    1. Start daemon: python -m drtrace_service
    2. Verify: curl http://localhost:8001/status
    """
```

---

## When to Use Each Method

| Scenario | Recommended Method |
|----------|-------------------|
| Simple queries (status, logs) | HTTP/curl |
| Complex analysis | HTTP or Python |
| Rich markdown output needed | Python SDK |
| Running outside Python | HTTP/curl |
| Setup guide interaction | Python SDK |
| Debugging integration | CLI commands |
| Script automation | HTTP/curl |

---

## Quick Reference: Common Endpoints

**Note**: Always verify via `/openapi.json` - this list is for reference only.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/status` | GET | Health check |
| `/openapi.json` | GET | API schema |
| `/logs/query` | GET | Query logs |
| `/logs/ingest` | POST | Ingest logs |
| `/analysis/why` | GET | Root cause analysis |
| `/analysis/time-range` | GET | Time range analysis |
| `/help/guide/start` | POST | Start setup guide |
| `/help/guide/current` | GET | Current setup step |
| `/help/troubleshoot` | POST | Troubleshooting help |

---

## Important: Timestamps Are UTC

All timestamps in DrTrace API are **UTC Unix timestamps**:

| Field/Param | Format | Timezone |
|-------------|--------|----------|
| `ts` (in logs) | Unix float | UTC |
| `start_ts`, `end_ts` | Unix float | UTC |
| `since`, `until` | Relative or ISO 8601 | UTC |

**Key Rules**:
- ISO 8601 without timezone (e.g., `2025-12-31T02:44:03`) is interpreted as **UTC**, not local time
- Relative times (`5m`, `1h`) are relative to server's current UTC time
- To query with local time, include timezone offset: `2025-12-31T09:44:03+07:00`

### Converting Local Time to UTC

**Python:**
```python
from datetime import datetime, timezone, timedelta

# Local time (e.g., 2025-12-31 09:44:03 in GMT+7)
local_time = datetime(2025, 12, 31, 9, 44, 3)

# Method 1: If you know your timezone offset
local_tz = timezone(timedelta(hours=7))  # GMT+7
local_aware = local_time.replace(tzinfo=local_tz)
utc_time = local_aware.astimezone(timezone.utc)
unix_ts = utc_time.timestamp()
print(f"UTC Unix timestamp: {unix_ts}")

# Method 2: Using system timezone
import time
unix_ts = time.mktime(local_time.timetuple())
```

**Bash:**
```bash
# Convert local time to Unix timestamp
date -d "2025-12-31 09:44:03" +%s

# Convert with explicit timezone
TZ=UTC date -d "2025-12-31T02:44:03" +%s
```

### API Query Examples with Timezone

```bash
# Option 1: Include timezone in ISO 8601 (recommended for local time)
curl "http://localhost:8001/logs/query?since=2025-12-31T09:44:03%2B07:00"

# Option 2: Use relative time (always relative to server UTC time)
curl "http://localhost:8001/logs/query?since=5m"

# Option 3: Convert to UTC Unix timestamp first
UTC_TS=$(TZ=UTC date -d "2025-12-31T02:44:03" +%s)
curl "http://localhost:8001/logs/query?start_ts=$UTC_TS"

# Option 4: Use ISO 8601 in UTC (note: no timezone = UTC)
curl "http://localhost:8001/logs/query?since=2025-12-31T02:44:03"
```

### Common Timezone Pitfalls

1. **ISO 8601 Without Timezone**: Interpreted as UTC, not local time. If you pass `2025-12-31T09:44:03` thinking it's local 9:44 AM, it will be treated as 9:44 AM UTC.

2. **Server vs Client Timezone**: If your server is in a different timezone than your client, always use explicit UTC timestamps or include timezone offsets.

3. **Relative Times**: `since=5m` means 5 minutes before server's current UTC time, regardless of your local timezone.

---

## Related Documentation

- `docs/daemon-interaction-guide.md` - OpenAPI discovery details
- `docs/api-reference.md` - Complete API reference

---

**Last Updated**: 2025-12-31
