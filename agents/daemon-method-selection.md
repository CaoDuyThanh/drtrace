# Daemon Method Selection Guide
**Purpose**: Guide for AI agents to choose the right method for daemon interaction.
**Key Principle**: For AI agents, prefer interaction with daemon in this order (most preferred to least, if a method is unavailable, fall back to the next):
- **CLI**: if available on client machine (check `## CLI Approach` below).
- **HTTP/curl**: for complex interactions without dependencies (check `## HTTP/curl Approach` below).
- **Python code**: when rich queries are needed (check `## Python code Approach` below).
## CLI Approach
If `drtrace` CLI is installed on the client machine:
- Check with: `drtrace --version`
- Prefer CLI commands: `drtrace grep`, `drtrace tail`, `drtrace status`
- Benefit: no HTTP overhead and faster queries
### Query Filter Rule: Mutually Exclusive
When querying logs, use **either** `message_contains` **or** `message_regex`, **NOT both**.

| Filter             | Use Case         | Example                                       |
| ------------------ | ---------------- | --------------------------------------------- |
| `message_contains` | Substring search | "timeout" matches "Connection timeout error"  |
| `message_regex`    | Regex patterns   | "(db\|cache).*timeout" matches service errors |
**Error if both used**: API returns 400 "Cannot use both filters".
### Examples
**CLI - Substring Search**:
```bash
drtrace grep "timeout" --since 1h
```
**CLI - Regex Search** (with `-E`):
```bash
drtrace grep -E "(db|cache).*timeout" --since 1h
```
## HTTP/curl Approach
### Check Daemon Status

```bash
curl http://localhost:8001/status
```
### Discovery API via OpenAPI Schema
**CRITICAL**: Before making any API call, fetch `/openapi.json` to discover:
- Available endpoints
- Correct field names (e.g., `ts` not `timestamp`)
- Request/response schemas
```bash
# Always fetch schema first
curl http://localhost:8001/openapi.json
```
### Common Endpoints (for Quick Reference)
**Note**: Always verify via `/openapi.json` - this list is for reference only (*API field names can change between versions. Using OpenAPI ensures compatibility*).

| Endpoint               | Method | Purpose              |
| ---------------------- | ------ | -------------------- |
| `/status`              | GET    | Health check         |
| `/openapi.json`        | GET    | API schema           |
| `/logs/query`          | GET    | Query logs           |
| `/logs/ingest`         | POST   | Ingest logs          |
| `/analysis/why`        | GET    | Root cause analysis  |
| `/analysis/time-range` | GET    | Time range analysis  |
| `/help/guide/start`    | POST   | Start setup guide    |
| `/help/guide/current`  | GET    | Current setup step   |
| `/help/troubleshoot`   | POST   | Troubleshooting help |
### Examples
**HTTP - Substring Search**:
```bash
curl "http://localhost:8001/logs/query?message_contains=timeout&since=1h"
```
**HTTP - Regex Search**:
```bash
curl "http://localhost:8001/logs/query?message_regex=(db|cache).*timeout&since=1h"
```
**HTTP - Query Logs**:
```bash
# Get logs from last 5 minutes
START_TS=$(python3 -c "import time; print(time.time() - 300)")
END_TS=$(python3 -c "import time; print(time.time())")
curl "http://localhost:8001/logs/query?start_ts=${START_TS}&end_ts=${END_TS}&application_id=myapp&limit=100"
```
**HTTP - Query with filter**:
```bash
curl "http://localhost:8001/analysis/why?application_id=myapp&start_ts=${START_TS}&end_ts=${END_TS}&min_level=ERROR"
```
## Python code Approach
Use when you need rich SDK features or the HTTP method fails.
### Examples
**Get OpenAPI json for API information**
```python
import requests

base_url = "http://localhost:8001"

# Fetch schema to discover endpoints and field names
schema = requests.get(f"{base_url}/openapi.json", timeout=5).json()
paths = schema.get("paths", {})
components = schema.get("components", {}).get("schemas", {})

# Use discovered field names, not hardcoded ones
```
**Python requests (HTTP method)**
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
## When to Use Each Method

| Scenario                      | Recommended Method |
| ----------------------------- | ------------------ |
| Simple queries (status, logs) | CLI, HTTP/curl     |
| Complex analysis              | HTTP or Python     |
| Rich markdown output needed   | Python SDK         |
| Running outside Python        | CLI, HTTP/curl     |
| Setup guide interaction       | Python SDK         |
| Debugging integration         | CLI commands       |
| Script automation             | CLI, HTTP/curl     |
## Important Notes
### Timestamps Are UTC
All timestamps in DrTrace API are **UTC Unix timestamps**:

| Field/Param          | Format               | Timezone |
| -------------------- | -------------------- | -------- |
| `ts` (in logs)       | Unix float           | UTC      |
| `start_ts`, `end_ts` | Unix float           | UTC      |
| `since`, `until`     | Relative or ISO 8601 | UTC      |
**Key Rules**:
- ISO 8601 without timezone (e.g., `2025-12-31T02:44:03`) is interpreted as **UTC**, not local time
- Relative times (`5m`, `1h`) are relative to server's current UTC time
- To query with local time, include timezone offset: `2025-12-31T09:44:03+07:00`
#### Converting Local Time to UTC
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
#### API Query Examples with Timezone
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
#### Common Timezone Pitfalls
1. **ISO 8601 Without Timezone**: Interpreted as UTC, not local time. If you pass `2025-12-31T09:44:03` thinking it's local 9:44 AM, it will be treated as 9:44 AM UTC.
2. **Server vs Client Timezone**: If your server is in a different timezone than your client, always use explicit UTC timestamps or include timezone offsets.
3. **Relative Times**: `since=5m` means 5 minutes before server's current UTC time, regardless of your local timezone.
---
**Last Updated**: 2026-01-06