# DrTrace API and CLI Reference

This document provides a complete reference for all HTTP API endpoints and CLI commands available in DrTrace.

## Table of Contents

- [HTTP API Endpoints](#http-api-endpoints)
  - [Status](#status)
  - [Log Ingestion](#log-ingestion)
  - [Log Querying](#log-querying)
  - [Log Management](#log-management)
  - [Analysis](#analysis)
  - [Saved Queries](#saved-queries)
- [CLI Commands](#cli-commands)
  - [status](#status-command)
  - [why](#why-command)
  - [query](#query-command)
  - [init-agent](#init-agent-command)
- [Data Models](#data-models)
- [Error Responses](#error-responses)

## HTTP API Endpoints

Base URL: `http://localhost:8001` (default)

All endpoints return JSON responses. Error responses follow the standard HTTP status codes.

### Status

#### `GET /status`

Check daemon health and configuration.

**Response:**

```json
{
  "service_name": "drtrace_daemon",
  "version": "0.1.0",
  "host": "localhost",
  "port": 8001,
  "retention_days": 7
}
```

**Example:**

```bash
curl http://localhost:8001/status
```

---

### Log Ingestion

#### `POST /logs/ingest`

Ingest a batch of log events.

**Request Body:**

```json
{
  "logs": [
    {
      "timestamp": 1703001234.567,
      "level": "ERROR",
      "message": "Division by zero",
      "application_id": "myapp",
      "service_name": "api-service",
      "module_name": "calculator",
      "file_path": "/path/to/app.py",
      "line_no": 42,
      "exception_type": "ZeroDivisionError",
      "stacktrace": "Traceback...",
      "context": {
        "user_id": "123",
        "request_id": "abc-123"
      }
    }
  ]
}
```

**Response:**

```json
{
  "accepted": 1
}
```

**Status Code:** `202 Accepted`

**Example:**

```bash
curl -X POST http://localhost:8001/logs/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [{
      "timestamp": 1703001234.567,
      "level": "ERROR",
      "message": "Error occurred",
      "application_id": "myapp",
      "module_name": "main",
      "file_path": "/app/main.py",
      "line_no": 10,
      "context": {}
    }]
  }'
```

---

### Log Querying

#### `GET /logs/query`

Query logs by time range with optional filters.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `start_ts` | float | Yes | Start timestamp (Unix, inclusive) |
| `end_ts` | float | Yes | End timestamp (Unix, inclusive) |
| `application_id` | string | No | Filter by application ID |
| `module_name` | string | No | Filter by module name |
| `message_contains` | string | No | Case-insensitive substring search in log message |
| `message_regex` | string | No | POSIX regex pattern for message matching (max 500 chars) |
| `min_level` | string | No | Minimum log level (DEBUG, INFO, WARN, ERROR, CRITICAL) |
| `limit` | int | No | Max records (1-1000, default: 100) |

**⚠️ Important Constraint:**

`message_contains` and `message_regex` are **mutually exclusive**. You can use one or the other, but not both in the same request.

- Use `message_contains` for simple text searches (case-insensitive substring matching)
- Use `message_regex` for advanced pattern matching (POSIX regular expressions)

**Message Filtering Comparison:**

| Feature | `message_contains` | `message_regex` |
|---------|-------------------|-----------------|
| Match type | Substring (case-insensitive) | POSIX regex pattern |
| Example | `timeout` matches "Connection timeout" | `error\|warning` matches "error occurred" or "warning sign" |
| Use case | Simple text search | Complex patterns, alternatives, character classes |
| Max length | - | 500 characters |

**Response:**

```json
{
  "results": [
    {
      "id": 1,
      "ts": "2025-12-19T10:30:00Z",
      "level": "ERROR",
      "message": "Error occurred",
      "application_id": "myapp",
      "service_name": "api",
      "module_name": "main",
      "file_path": "/app/main.py",
      "line_no": 10,
      "exception_type": null,
      "stacktrace": null,
      "context": {}
    }
  ],
  "count": 1
}
```

**Examples:**

Simple substring search:
```bash
curl "http://localhost:8001/logs/query?start_ts=1703001200&end_ts=1703001300&message_contains=timeout"
```

Regex pattern search:
```bash
curl "http://localhost:8001/logs/query?start_ts=1703001200&end_ts=1703001300&message_regex=error%7Cwarning"
```

Combining filters:
```bash
curl "http://localhost:8001/logs/query?start_ts=1703001200&end_ts=1703001300&application_id=myapp&min_level=ERROR&limit=10"
```

**Error Response (both parameters used):**

```bash
curl "http://localhost:8001/logs/query?start_ts=1703001200&end_ts=1703001300&message_contains=error&message_regex=warn"
```

Returns HTTP 400:
```json
{
  "detail": {
    "code": "INVALID_PARAMS",
    "message": "Cannot use both message_contains and message_regex. Choose one."
  }
}
```

---

### Log Management

#### `POST /logs/clear`

Clear logs for a specific application.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `application_id` | string | Yes | Application ID to clear |
| `environment` | string | No | Optional environment filter |

**Response:**

```json
{
  "deleted": 42
}
```

**Status Code:** `200 OK`

**Example:**

```bash
curl -X POST "http://localhost:8001/logs/clear?application_id=myapp"
```

---

### Analysis

#### `GET /analysis/time-range`

Retrieve logs for analysis within a time range.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `application_id` | string | Yes | Application identifier |
| `start_ts` | float | Yes | Start timestamp (Unix, inclusive) |
| `end_ts` | float | Yes | End timestamp (Unix, inclusive) |
| `min_level` | string | No | Minimum log level (DEBUG, INFO, WARN, ERROR, CRITICAL) |
| `module_name` | string | No | Filter by module name |
| `service_name` | string | No | Filter by service name |
| `limit` | int | No | Max records (1-1000, default: 100) |

**Response:**

```json
{
  "data": {
    "logs": [
      {
        "id": 1,
        "ts": "2025-12-19T10:30:00Z",
        "level": "ERROR",
        "message": "Error occurred",
        "application_id": "myapp",
        "service_name": "api",
        "module_name": "main",
        "file_path": "/app/main.py",
        "line_no": 10,
        "exception_type": "ZeroDivisionError",
        "stacktrace": "Traceback...",
        "context": {}
      }
    ]
  },
  "meta": {
    "application_id": "myapp",
    "start_ts": 1703001200.0,
    "end_ts": 1703001300.0,
    "count": 1,
    "filters": {
      "min_level": "ERROR",
      "module_name": null,
      "service_name": null
    }
  }
}
```

**Example:**

```bash
curl "http://localhost:8001/analysis/time-range?application_id=myapp&start_ts=1703001200&end_ts=1703001300&min_level=ERROR"
```

---

#### `GET /analysis/why`

Generate root-cause explanation for errors.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `application_id` | string | Yes | Application identifier |
| `start_ts` | float | Yes | Start timestamp (Unix, inclusive) |
| `end_ts` | float | Yes | End timestamp (Unix, inclusive) |
| `min_level` | string | No | Minimum log level (DEBUG, INFO, WARN, ERROR, CRITICAL) |
| `module_name` | string | No | Filter by module name |
| `service_name` | string | No | Filter by service name |
| `limit` | int | No | Max records (1-1000, default: 100) |

**Response:**

```json
{
  "data": {
    "explanation": {
      "summary": "Division by zero error occurred in calculator module",
      "root_cause": "The application attempted to divide 100 by 0, which is undefined in Python",
      "error_location": {
        "file_path": "/app/calculator.py",
        "line_no": 42
      },
      "key_evidence": [
        "ERROR log at 10:30:00: Division by zero",
        "ZeroDivisionError exception in calculator.py:42"
      ],
      "suggested_fixes": [
        {
          "description": "Add input validation before division",
          "file_path": "/app/calculator.py",
          "line_no": 40,
          "line_range": [38, 42],
          "related_log_ids": [1],
          "confidence": "high",
          "rationale": "Prevents division by zero"
        }
      ],
      "confidence": "high",
      "has_clear_remediation": true,
      "evidence_references": [
        {
          "log_id": 1,
          "reason": "Primary error log",
          "file_path": "/app/calculator.py",
          "line_no": 42,
          "line_range": [40, 44]
        }
      ]
    }
  },
  "meta": {
    "application_id": "myapp",
    "start_ts": 1703001200.0,
    "end_ts": 1703001300.0,
    "count": 1,
    "filters": {
      "min_level": "ERROR",
      "module_name": null,
      "service_name": null
    }
  }
}
```

**Example:**

```bash
curl "http://localhost:8001/analysis/why?application_id=myapp&start_ts=1703001200&end_ts=1703001300"
```

---

#### `GET /analysis/cross-module`

Analyze incidents spanning multiple services/modules.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `application_id` | string | Yes | Application identifier |
| `start_ts` | float | Yes | Start timestamp (Unix, inclusive) |
| `end_ts` | float | Yes | End timestamp (Unix, inclusive) |
| `min_level` | string | No | Minimum log level (DEBUG, INFO, WARN, ERROR, CRITICAL) |
| `module_names` | string[] | No | List of module names to include |
| `service_names` | string[] | No | List of service names to include |
| `limit` | int | No | Max records (1-1000, default: 100) |

**Response:**

```json
{
  "data": {
    "explanation": {
      "summary": "Cross-module incident analysis",
      "root_cause": "Cascading failure across services",
      "error_location": null,
      "key_evidence": [],
      "suggested_fixes": [],
      "confidence": "medium",
      "has_clear_remediation": false,
      "evidence_references": []
    },
    "components": ["api-service", "db-service"],
    "logs_by_component": {
      "api-service": 5,
      "db-service": 3
    }
  },
  "meta": {
    "application_id": "myapp",
    "start_ts": 1703001200.0,
    "end_ts": 1703001300.0,
    "filters": {
      "min_level": "ERROR",
      "module_names": ["api", "db"],
      "service_names": null
    },
    "components": ["api-service", "db-service"]
  }
}
```

**Example:**

```bash
curl "http://localhost:8001/analysis/cross-module?application_id=myapp&start_ts=1703001200&end_ts=1703001300&module_names=api&module_names=db"
```

---

### Saved Queries

#### `GET /queries`

List all saved analysis queries.

**Response:**

```json
{
  "data": {
    "queries": [
      {
        "name": "daily-errors",
        "description": "Daily error analysis",
        "application_id": "myapp",
        "default_time_window_minutes": 60,
        "min_level": "ERROR",
        "module_names": [],
        "service_names": [],
        "limit": 100,
        "query_type": "why"
      }
    ]
  },
  "meta": {
    "count": 1
  }
}
```

**Example:**

```bash
curl http://localhost:8001/queries
```

---

#### `POST /queries`

Create a new saved query.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Query name (unique) |
| `description` | string | No | Query description |
| `application_id` | string | Yes | Default application ID |
| `default_time_window_minutes` | int | No | Default time window (default: 5) |
| `min_level` | string | No | Default minimum log level |
| `module_names` | string[] | No | Default module names |
| `service_names` | string[] | No | Default service names |
| `limit` | int | No | Default limit (default: 100) |
| `query_type` | string | No | Query type: "why" or "cross-module" (default: "why") |

**Response:**

```json
{
  "data": {
    "query": {
      "name": "daily-errors",
      "description": "Daily error analysis",
      "application_id": "myapp",
      "default_time_window_minutes": 60,
      "min_level": "ERROR",
      "module_names": [],
      "service_names": [],
      "limit": 100,
      "query_type": "why"
    }
  },
  "meta": {
    "message": "Query created successfully"
  }
}
```

**Example:**

```bash
curl -X POST "http://localhost:8001/queries?name=daily-errors&application_id=myapp&default_time_window_minutes=60&min_level=ERROR&query_type=why"
```

---

#### `GET /queries/{query_name}`

Get a saved query by name.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query_name` | string | Query name |

**Response:**

```json
{
  "data": {
    "query": {
      "name": "daily-errors",
      "description": "Daily error analysis",
      "application_id": "myapp",
      "default_time_window_minutes": 60,
      "min_level": "ERROR",
      "module_names": [],
      "service_names": [],
      "limit": 100,
      "query_type": "why"
    }
  }
}
```

**Example:**

```bash
curl http://localhost:8001/queries/daily-errors
```

---

#### `DELETE /queries/{query_name}`

Delete a saved query.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query_name` | string | Query name |

**Response:**

```json
{
  "data": {
    "message": "Query 'daily-errors' deleted successfully"
  }
}
```

**Example:**

```bash
curl -X DELETE http://localhost:8001/queries/daily-errors
```

---

#### `GET /analysis/query/{query_name}`

Run analysis using a saved query with optional parameter overrides.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query_name` | string | Query name |

**Query Parameters (all optional, override saved query defaults):**

| Parameter | Type | Description |
|-----------|------|-------------|
| `since` | string | Time window (e.g., "5m", "1h", "30s") |
| `start_ts` | float | Override start timestamp |
| `end_ts` | float | Override end timestamp |
| `application_id` | string | Override application ID |
| `min_level` | string | Override minimum log level |
| `module_names` | string[] | Override module names |
| `service_names` | string[] | Override service names |
| `limit` | int | Override limit |

**Response:**

Same format as `/analysis/why` or `/analysis/cross-module` depending on query type.

**Example:**

```bash
curl "http://localhost:8001/analysis/query/daily-errors?since=10m"
```

---

## CLI Commands

All CLI commands are accessed via:

```bash
python -m drtrace_service <command> [options]
```

### status

Check daemon status.

**Usage:**

```bash
python -m drtrace_service status
```

**Output:**

```
DrTrace daemon status: HEALTHY
Service: drtrace_daemon v0.1.0
Listening on: localhost:8001
```

**Exit Codes:**
- `0`: Daemon is healthy
- `2`: Daemon is unreachable

**Environment Variables:**
- `DRTRACE_DAEMON_HOST`: Daemon host (default: `localhost`)
- `DRTRACE_DAEMON_PORT`: Daemon port (default: `8001`)

---

### grep

Search log messages with pattern matching (similar to Unix `grep`).

**Usage:**

```bash
python -m drtrace_service grep [OPTIONS] PATTERN
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `-E`, `--extended-regex` | flag | Use extended regex (POSIX) instead of substring search |
| `--application-id` | string | Filter by application ID |
| `--since` | string | Relative time window (e.g., "5m", "1h", "30s") |
| `--daemon-host` | string | Daemon host (default: `localhost`) |
| `--daemon-port` | int | Daemon port (default: `8001`) |

**Pattern Matching Behavior:**

- **Without `-E`**: Performs case-insensitive substring search (uses API `message_contains` parameter)
- **With `-E`**: Uses POSIX regular expressions for advanced pattern matching (uses API `message_regex` parameter)

**⚠️ Note:** The `-E` and default modes are mutually exclusive at the API level - the CLI automatically sends the appropriate parameter (`message_contains` OR `message_regex`) to the daemon.

**Examples:**

Simple substring search (case-insensitive):
```bash
# Find all logs containing "timeout"
python -m drtrace_service grep timeout

# Search in specific app from last 10 minutes
python -m drtrace_service grep --application-id myapp --since 10m "connection error"
```

Extended regex search:
```bash
# Find logs matching "error" OR "warning"
python -m drtrace_service grep -E "error|warning"

# Match lines starting with "ERROR:" or "WARN:"
python -m drtrace_service grep -E "^(ERROR|WARN):"

# Find numeric IDs in format "ID-12345"
python -m drtrace_service grep -E "ID-[0-9]{5}"

# Search with application filter
python -m drtrace_service grep -E --application-id myapp "timeout|error"
```

**Output:**

Matched log entries with:
- Timestamp
- Level
- Message
- Source location (file:line)

**Exit Codes:**
- `0`: Success (matches found)
- `1`: No matches found or error
- `2`: Daemon unreachable

---

### why

Analyze why an error happened.

**Usage:**

```bash
python -m drtrace_service why [OPTIONS]
```

**Options:**

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--application-id` | string | Yes | Application ID |
| `--since` | string | No* | Relative time window (e.g., "5m", "1h", "30s") |
| `--start` | float | No* | Start timestamp (Unix) |
| `--end` | float | No* | End timestamp (Unix) |
| `--module-name` | string | No | Filter by module name |
| `--service-name` | string | No | Filter by service name |
| `--min-level` | string | No | Minimum log level (DEBUG, INFO, WARN, ERROR, CRITICAL) |
| `--limit` | int | No | Max records (default: 100) |

\* Either `--since` or both `--start` and `--end` are required.

**Examples:**

```bash
# Analyze errors from last 5 minutes
python -m drtrace_service why --application-id myapp --since 5m

# Analyze errors from specific time range
python -m drtrace_service why --application-id myapp --start 1703001200 --end 1703001300

# Filter by module and minimum level
python -m drtrace_service why --application-id myapp --since 10m --module-name calculator --min-level ERROR

# Filter by service
python -m drtrace_service why --application-id myapp --since 1h --service-name api-service
```

**Output:**

Formatted markdown explanation with:
- Analysis summary
- Root cause
- Evidence references
- Suggested fixes

**Exit Codes:**
- `0`: Success
- `1`: Error (e.g., invalid parameters, no logs found)
- `2`: Daemon unreachable

---

### query

Manage saved analysis queries.

**Usage:**

```bash
python -m drtrace_service query <subcommand> [OPTIONS]
```

**Subcommands:**

#### `list`

List all saved queries.

**Usage:**

```bash
python -m drtrace_service query list
```

**Output:**

```
Saved Queries:
  daily-errors: Daily error analysis (myapp, 60m, ERROR)
  weekly-review: Weekly analysis (myapp, 7d, INFO)
```

---

#### `create`

Create a new saved query.

**Usage:**

```bash
python -m drtrace_service query create [OPTIONS]
```

**Options:**

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--name` | string | Yes | Query name (unique) |
| `--description` | string | No | Query description |
| `--application-id` | string | Yes | Default application ID |
| `--default-window` | int | No | Default time window in minutes (default: 5) |
| `--min-level` | string | No | Default minimum log level |
| `--module-names` | string[] | No | Default module names (can be repeated) |
| `--service-names` | string[] | No | Default service names (can be repeated) |
| `--limit` | int | No | Default limit (default: 100) |
| `--type` | string | No | Query type: "why" or "cross-module" (default: "why") |

**Example:**

```bash
python -m drtrace_service query create \
  --name daily-errors \
  --description "Daily error analysis" \
  --application-id myapp \
  --default-window 60 \
  --min-level ERROR \
  --type why
```

---

#### `delete`

Delete a saved query.

**Usage:**

```bash
python -m drtrace_service query delete --name <query_name>
```

**Options:**

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--name` | string | Yes | Query name to delete |

**Example:**

```bash
python -m drtrace_service query delete --name daily-errors
```

---

#### `run`

Run a saved query with optional parameter overrides.

**Usage:**

```bash
python -m drtrace_service query run [OPTIONS]
```

**Options:**

| Option | Type | Required | Description |
|--------|------|----------|-------------|
| `--name` | string | Yes | Query name |
| `--since` | string | No | Override time window (e.g., "5m", "1h") |
| `--start` | float | No | Override start timestamp |
| `--end` | float | No | Override end timestamp |
| `--application-id` | string | No | Override application ID |
| `--min-level` | string | No | Override minimum log level |
| `--module-names` | string[] | No | Override module names (can be repeated) |
| `--service-names` | string[] | No | Override service names (can be repeated) |
| `--limit` | int | No | Override limit |

**Example:**

```bash
# Run with default parameters
python -m drtrace_service query run --name daily-errors

# Run with time window override
python -m drtrace_service query run --name daily-errors --since 10m

# Run with multiple overrides
python -m drtrace_service query run --name daily-errors --since 30m --min-level WARN
```

---

### init-agent

Bootstrap the default log-analysis agent spec into your project.

**Usage:**

```bash
python -m drtrace_service init-agent [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--path` | string | Custom target path for agent file (default: `agents/log-analysis.md`) |
| `--force` | flag | Overwrite existing agent file without prompting |
| `--backup` | flag | Create timestamped backup before overwriting (requires `--force`) |

**Description:**

The `init-agent` command copies a specific DrTrace agent specification from the installed package into your project. This agent file enables natural language querying of logs through IDE agents (e.g., Cursor, VS Code with BMAD-style agents).

**Note:** The `init-project` command (when agent integration is enabled) automatically copies all four agent specifications (log-analysis, log-it, log-init, log-help) to `_drtrace/agents/`. The `init-agent` command is used to copy a single specific agent file, typically when you want to add an agent to an existing project or customize the agent location.

**Default Behavior:**

- Creates `agents/log-analysis.md` in the current directory
- If the file already exists, the command exits with an error message (does not overwrite)
- The agent file references `drtrace_service.agent_interface.process_agent_query()` and `drtrace_service.query_parser.parse_query()` from the installed package

**Examples:**

```bash
# Bootstrap agent file with default location
python -m drtrace_service init-agent

# Bootstrap to a custom location
python -m drtrace_service init-agent --path _drtrace/agents/log-analysis.md

# Overwrite existing file (use with caution)
python -m drtrace_service init-agent --force

# Create backup before overwriting
python -m drtrace_service init-agent --force --backup
```

**Output:**

On success:
```
Agent file created: agents/log-analysis.md
```

If file exists (without `--force`):
```
Error: agents/log-analysis.md already exists.
Use --force to overwrite or --backup to create a backup first.
```

**Exit Codes:**
- `0`: Success (file created or overwritten)
- `1`: Error (e.g., file exists without `--force`, invalid path, package resource not found)

**Agent File Location:**

The default location is `agents/log-analysis.md` in your project root. This follows the BMAD agent pattern where agent files are stored in an `agents/` directory.

**Customization:**

After bootstrapping, you can edit `agents/log-analysis.md` to customize:
- Agent persona and communication style
- Menu items and commands
- Capabilities documentation
- Query examples

Your customizations are preserved. Future `init-agent` runs will not overwrite your customizations unless you use `--force`.

**Package Resource:**

The default agent spec is packaged with DrTrace at:
- Package location: `drtrace_service/resources/agents/log-analysis.md`
- Accessible via: `importlib.resources.open_text("drtrace_service.resources.agents", "log-analysis.md")`

**See Also:**

- [Agent Integration Examples](../examples/agent-integrations/README.md): Framework-specific integration guides
- [Overview](overview.md): Architecture and agent interface design

---

## Data Models

### LogRecord

```json
{
  "timestamp": 1703001234.567,
  "level": "ERROR",
  "message": "Error message",
  "application_id": "myapp",
  "service_name": "api-service",
  "module_name": "calculator",
  "file_path": "/path/to/file.py",
  "line_no": 42,
  "exception_type": "ZeroDivisionError",
  "stacktrace": "Traceback...",
  "context": {
    "key": "value"
  }
}
```

### LogBatch

```json
{
  "logs": [
    { /* LogRecord */ }
  ]
}
```

### RootCauseExplanation

```json
{
  "summary": "Brief summary",
  "root_cause": "Detailed root cause",
  "error_location": {
    "file_path": "/path/to/file.py",
    "line_no": 42
  },
  "key_evidence": ["Evidence 1", "Evidence 2"],
  "suggested_fixes": [
    {
      "description": "Fix description",
      "file_path": "/path/to/file.py",
      "line_no": 40,
      "line_range": [38, 42],
      "related_log_ids": [1, 2],
      "confidence": "high",
      "rationale": "Why this fix helps"
    }
  ],
  "confidence": "high",
  "has_clear_remediation": true,
  "evidence_references": [
    {
      "log_id": 1,
      "reason": "Why this log is relevant",
      "file_path": "/path/to/file.py",
      "line_no": 42,
      "line_range": [40, 44]
    }
  ]
}
```

---

## Error Responses

All endpoints may return standard HTTP error responses:

### 400 Bad Request

```json
{
  "detail": {
    "code": "INVALID_TIME_RANGE",
    "message": "start_ts must be less than end_ts"
  }
}
```

Common error codes:
- `INVALID_TIME_RANGE`: Start time must be before end time
- `INVALID_LEVEL`: Invalid log level
- `INVALID_TIME_FORMAT`: Invalid time format for `since` parameter
- `INVALID_QUERY_TYPE`: Query type must be "why" or "cross-module"

### 404 Not Found

```json
{
  "detail": {
    "code": "QUERY_NOT_FOUND",
    "message": "Query 'query-name' not found"
  }
}
```

### 422 Unprocessable Entity

FastAPI validation errors for invalid request body or parameters.

---

## Environment Variables

### Client Configuration

- `DRTRACE_APPLICATION_ID`: Application identifier (required)
- `DRTRACE_DAEMON_URL`: Daemon URL (default: `http://localhost:8001/logs/ingest`)
- `DRTRACE_ENABLED`: Enable/disable DrTrace (default: `true`)

### Daemon Configuration

- `DRTRACE_DATABASE_URL`: PostgreSQL connection string (default: `postgresql://postgres:postgres@localhost:5432/drtrace`)
- `DRTRACE_RETENTION_DAYS`: Log retention in days (default: `7`, range: 1-365)
- `DRTRACE_DAEMON_HOST`: Daemon host (default: `localhost`)
- `DRTRACE_DAEMON_PORT`: Daemon port (default: `8001`)

---

## See Also

- [Quickstart Guide](quickstart.md): Step-by-step walkthrough
- [Overview](overview.md): Architecture and concepts
- [Agent Integration Examples](../examples/agent-integrations/README.md): Framework-specific integration guides

