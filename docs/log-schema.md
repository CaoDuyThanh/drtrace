# Unified Multi-Language Log Schema

This document describes the unified log schema used by DrTrace to store and query logs from multiple programming languages (Python, C++, and future languages).

## Overview

The unified schema is designed to be **language-agnostic**, allowing logs from different languages to be stored in the same database table and queried together. Language-specific metadata is stored in the extensible `context` field rather than adding top-level schema fields.

## Schema Fields

### Required Fields

These fields **must** be present in every log record:

| Field | Type | Description |
|-------|------|-------------|
| `ts` | `float` | Unix timestamp (seconds since epoch) when the log was created |
| `level` | `str` | Log level (e.g., `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL`) |
| `message` | `str` | The log message text |
| `application_id` | `str` | Identifier for the application or project emitting logs |
| `module_name` | `str` | Module, logger, or component name (e.g., `myapp.handlers`, `renderer`) |

### Optional Standard Fields

These fields are **optional** but recommended for error-level logs:

| Field | Type | Description |
|-------|------|-------------|
| `service_name` | `str \| null` | High-level service or component name |
| `file_path` | `str \| null` | Source file path (absolute or relative) |
| `line_no` | `int \| null` | Line number in the source file |
| `exception_type` | `str \| null` | Exception or error type name (e.g., `ZeroDivisionError`, `std::runtime_error`) |
| `stacktrace` | `str \| null` | Full stack trace or backtrace text |

### Extensible Context Field

| Field | Type | Description |
|-------|------|-------------|
| `context` | `Dict[str, Any]` | JSON object for arbitrary structured metadata. Defaults to `{}`. |

The `context` field is the **primary mechanism for language-specific or application-specific metadata**. Use it for:

- Language hints (e.g., `{"language": "cpp"}`)
- Request/transaction IDs (e.g., `{"request_id": "req-123"}`)
- User identifiers (e.g., `{"user_id": "user-456"}`)
- Environment information (e.g., `{"environment": "production"}`)
- Thread/process IDs (e.g., `{"thread_id": "12345", "process_id": "67890"}`)
- Framework-specific metadata (e.g., `{"framework": "django"}`)
- Compiler/build metadata (e.g., `{"compiler": "g++", "build_config": "release"}`)
- Any other custom fields needed by your application

## Database Schema

The PostgreSQL table schema matches the log record structure:

```sql
CREATE TABLE logs (
  id BIGSERIAL PRIMARY KEY,
  ts TIMESTAMPTZ NOT NULL,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  application_id TEXT NOT NULL,
  service_name TEXT,
  module_name TEXT NOT NULL,
  file_path TEXT,
  line_no INTEGER,
  exception_type TEXT,
  stacktrace TEXT,
  context JSONB NOT NULL DEFAULT '{}'::jsonb
);
```

### Indexes

The following indexes support common query patterns:

- `idx_logs_app_ts`: Composite index on `(application_id, ts DESC)` for application-scoped time-range queries
- `idx_logs_service_ts`: Composite index on `(service_name, ts DESC)` for service-scoped queries
- `idx_logs_module_ts`: Composite index on `(module_name, ts DESC)` for module-scoped queries

## Language-Specific Examples

### Python Log Record

```json
{
  "ts": 1703001234.567,
  "level": "ERROR",
  "message": "Division by zero",
  "application_id": "my-python-app",
  "service_name": "api",
  "module_name": "myapp.handlers",
  "file_path": "/app/handlers.py",
  "line_no": 42,
  "exception_type": "ZeroDivisionError",
  "stacktrace": "Traceback (most recent call last):\n  File ...",
  "context": {
    "request_id": "req-123",
    "user_id": "user-456",
    "python_version": "3.8.10",
    "framework": "django"
  }
}
```

### C++ Log Record

```json
{
  "ts": 1703001234.567,
  "level": "ERROR",
  "message": "Segmentation fault",
  "application_id": "my-cpp-app",
  "service_name": "engine",
  "module_name": "renderer",
  "file_path": "/src/renderer.cpp",
  "line_no": 128,
  "exception_type": "std::runtime_error",
  "stacktrace": "#0  0x00007f8b4c123456 in renderer::draw() at renderer.cpp:128",
  "context": {
    "language": "cpp",
    "thread_id": "12345",
    "process_id": "67890",
    "compiler": "g++",
    "build_config": "release",
    "cpu_arch": "x86_64"
  }
}
```

### Minimal Log Record (Any Language)

```json
{
  "ts": 1703001234.567,
  "level": "INFO",
  "message": "Simple log message",
  "application_id": "my-app",
  "module_name": "module"
}
```

## Schema Evolution Rules

When extending the schema in the future, follow these guidelines:

1. **Prefer `context` for new fields**: Add language-specific or optional metadata to `context` rather than creating new top-level columns. This avoids schema migrations and maintains backward compatibility.

2. **Required fields are immutable**: The required fields (`ts`, `level`, `message`, `application_id`, `module_name`) are part of the core contract and should not be removed or changed in incompatible ways.

3. **Optional fields can be added carefully**: If a new optional field is needed across all languages, it can be added as a nullable column. However, prefer `context` unless the field is:
   - Used by query filters (indexed)
   - Needed for performance (e.g., avoiding JSONB lookups)
   - Part of the core analysis workflow

4. **Backward compatibility**: Any schema changes must not break existing log records. New fields must be nullable or have defaults.

5. **Migration strategy**: If a new top-level field is added:
   - Add it as a nullable column
   - Update the `LogRecord` Pydantic model to make it optional
   - Ensure existing records can be read (null values are acceptable)
   - Update client SDKs to populate the field when available

## Validation

All log records are validated against the `LogRecord` Pydantic model before ingestion. The validation ensures:

- Required fields are present and have correct types
- Optional fields, if present, have correct types
- `context` is a valid JSON object (or defaults to `{}`)

Invalid records are rejected with a `422 Unprocessable Entity` response from the ingestion endpoint.

## Querying Across Languages

Since all languages use the same schema, you can query logs from multiple languages together:

```python
# Query all ERROR logs from a time range, regardless of language
records = storage.query_time_range(
    start_ts=start_time,
    end_ts=end_time,
    # No language filter needed - all logs use the same schema
)

# Filter by language using context if needed
# (This would require a JSONB query, not shown in the simple API)
```

The unified schema enables cross-language analysis without requiring separate tables or query paths per language.

