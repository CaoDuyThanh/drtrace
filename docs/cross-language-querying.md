# Cross-Language Log Querying

This guide demonstrates how to query logs from multiple programming languages (Python, C++, and future languages) using a single unified interface.

## Overview

The DrTrace daemon stores logs from all languages in the same database table using the unified schema. This allows you to query and analyze logs across languages without switching tools or using language-specific APIs.

## Querying Across Languages

### Basic Time-Range Query

Query logs from all languages within a time range:

```bash
curl "http://localhost:8001/logs/query?start_ts=1703000000&end_ts=1703003600&application_id=my-app"
```

**Response:**
```json
{
  "results": [
    {
      "ts": 1703001234.567,
      "level": "ERROR",
      "message": "Division by zero",
      "application_id": "my-app",
      "service_name": "api",
      "module_name": "python.handlers",
      "file_path": "/app/handlers.py",
      "line_no": 42,
      "context": {"request_id": "req-123"}
    },
    {
      "ts": 1703001235.890,
      "level": "ERROR",
      "message": "Segmentation fault",
      "application_id": "my-app",
      "service_name": "engine",
      "module_name": "cpp.renderer",
      "file_path": "/src/renderer.cpp",
      "line_no": 128,
      "context": {
        "language": "cpp",
        "thread_id": "12345"
      }
    }
  ],
  "count": 2
}
```

### Filtering by Module Name

Filter logs by module name across all languages:

```bash
curl "http://localhost:8001/logs/query?start_ts=1703000000&end_ts=1703003600&application_id=my-app&module_name=shared_component"
```

This returns logs from both Python and C++ modules named `shared_component`.

### Filtering by Application ID

Query all logs from a specific application, regardless of language:

```bash
curl "http://localhost:8001/logs/query?start_ts=1703000000&end_ts=1703003600&application_id=my-app"
```

### Combined Filters

Combine multiple filters to narrow results:

```bash
curl "http://localhost:8001/logs/query?start_ts=1703000000&end_ts=1703003600&application_id=my-app&module_name=api_handler&limit=50"
```

## Identifying Log Origin

### Language Identification

C++ logs include a language marker in the `context` field:

```json
{
  "context": {
    "language": "cpp",
    "thread_id": "12345"
  }
}
```

Python logs typically don't include a language marker (Python is the default assumption for the POC).

### Module Name Patterns

Module names can help identify language origin:

- **Python**: Often use dot notation (e.g., `myapp.handlers`, `api.middleware`)
- **C++**: Often use underscore or namespace notation (e.g., `cpp_renderer`, `engine::core`)

However, this is application-specific and not guaranteed.

### Service Name

The `service_name` field can indicate which service/component emitted the log, which may correlate with language:

```json
{
  "service_name": "python-api",
  "module_name": "handlers"
}
```

vs.

```json
{
  "service_name": "cpp-engine",
  "module_name": "renderer"
}
```

## Python Example

Query logs programmatically using Python:

```python
import requests
import time

# Query logs from last hour
end_ts = time.time()
start_ts = end_ts - 3600  # 1 hour ago

response = requests.get(
    "http://localhost:8001/logs/query",
    params={
        "start_ts": start_ts,
        "end_ts": end_ts,
        "application_id": "my-app",
        "limit": 100
    }
)

data = response.json()
for log in data["results"]:
    language = log["context"].get("language", "python")
    print(f"[{language}] {log['module_name']}: {log['message']}")
```

## C++ Example

Query logs from a C++ application:

```cpp
#include <curl/curl.h>
#include <iostream>
#include <sstream>

// Query logs from last hour
double end_ts = std::time(nullptr);
double start_ts = end_ts - 3600;

std::ostringstream url;
url << "http://localhost:8001/logs/query"
    << "?start_ts=" << start_ts
    << "&end_ts=" << end_ts
    << "&application_id=my-app"
    << "&limit=100";

// Use libcurl to make request and parse JSON response
// (Implementation details omitted)
```

## Common Query Patterns

### Find All Errors Across Languages

```bash
# Query and filter by level in application code
curl "http://localhost:8001/logs/query?start_ts=1703000000&end_ts=1703003600&application_id=my-app" | \
  jq '.results[] | select(.level == "ERROR")'
```

### Find Logs from Specific Service

```bash
# Query and filter by service_name in application code
curl "http://localhost:8001/logs/query?start_ts=1703000000&end_ts=1703003600&application_id=my-app" | \
  jq '.results[] | select(.service_name == "api")'
```

### Analyze Cross-Language Interactions

```python
import requests

# Query logs from a time window
response = requests.get(
    "http://localhost:8001/logs/query",
    params={
        "start_ts": start_time,
        "end_ts": end_time,
        "application_id": "my-app"
    }
)

logs = response.json()["results"]

# Group by language
python_logs = [l for l in logs if l["context"].get("language") != "cpp"]
cpp_logs = [l for l in logs if l["context"].get("language") == "cpp"]

print(f"Python logs: {len(python_logs)}")
print(f"C++ logs: {len(cpp_logs)}")

# Analyze interactions
# (e.g., find Python API calls that triggered C++ processing)
```

## Response Format

All query responses use the same format regardless of log origin:

```json
{
  "results": [
    {
      "ts": 1703001234.567,
      "level": "INFO",
      "message": "Log message",
      "application_id": "my-app",
      "service_name": "optional-service",
      "module_name": "module.name",
      "file_path": "optional/path/to/file",
      "line_no": 42,
      "exception_type": "optional ExceptionType",
      "stacktrace": "optional stack trace",
      "context": {
        "language": "cpp",  // Optional, only for C++
        "custom": "metadata"
      }
    }
  ],
  "count": 1
}
```

## Limitations and Notes

1. **No Language Filter in API**: The current API doesn't provide a direct `language` filter parameter. Filter by `context.language` in application code after querying.

2. **Service Name Not Filterable**: The `/logs/query` endpoint doesn't support filtering by `service_name` directly. Filter in application code after querying.

3. **Unified Schema**: All logs must conform to the unified schema. Language-specific metadata goes in the `context` field.

4. **Timestamp Consistency**: All timestamps are Unix epoch seconds (float), ensuring consistent ordering across languages.

## Best Practices

1. **Use Application ID**: Always filter by `application_id` to scope queries to your application.

2. **Combine Filters**: Use `application_id` + `module_name` + time range for precise queries.

3. **Check Context**: Use `context.language` to identify log origin when needed.

4. **Handle Optional Fields**: Not all logs have `file_path`, `line_no`, or `service_name`. Check for `None` values.

5. **Respect Limits**: Use the `limit` parameter to avoid large result sets (default: 100, max: 1000).

