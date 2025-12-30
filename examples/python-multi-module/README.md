# Python Multi-Module Example

This example demonstrates DrTrace integration in a more realistic Python application with multiple modules and services.

## What This Demonstrates

- **Multi-module logging**: Logs from different modules (data processing, API handlers, database operations)
- **Service identification**: Using `service_name` to distinguish between services
- **Error propagation**: How errors in one module can affect others
- **Cross-module analysis**: Using DrTrace to analyze incidents across multiple modules

## Project Structure

```
python-multi-module/
├── README.md
├── main.py              # Main application entry point
├── services/
│   ├── __init__.py
│   ├── api_service.py   # API service with handlers
│   └── data_service.py  # Data processing service
└── utils/
    ├── __init__.py
    └── database.py      # Database utility module
```

## Setup

1. **Install DrTrace** (if not already installed):

```bash
pip install -e /path/to/drtrace
```

2. **Start the DrTrace daemon** (in a separate terminal):

```bash
export DRTRACE_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/drtrace"
uvicorn drtrace_service.api:app --host localhost --port 8001
```

3. **Set environment variables**:

```bash
export DRTRACE_APPLICATION_ID="multi-module-app"
export DRTRACE_DAEMON_URL="http://localhost:8001/logs/ingest"
```

## Running the Example

```bash
cd examples/python-multi-module
python main.py
```

This will:
1. Start the API service
2. Process some data
3. Trigger errors in different modules
4. Send logs to the DrTrace daemon

## Analyzing the Logs

After running the example, analyze the errors:

```bash
# Analyze all errors from the last 5 minutes
python -m drtrace_service why --application-id multi-module-app --since 5m

# Analyze errors from a specific service
python -m drtrace_service why \
  --application-id multi-module-app \
  --since 5m \
  --service-name api-service

# Analyze errors from a specific module
python -m drtrace_service why \
  --application-id multi-module-app \
  --since 5m \
  --module-name data_processor

# Cross-module analysis
python -m drtrace_service why \
  --application-id multi-module-app \
  --since 5m \
  --module-name api_handlers \
  --module-name data_processor
```

## Expected Output

The application will log:
- INFO logs from normal operations
- ERROR logs from intentional errors in different modules
- Stack traces with file paths and line numbers

The analysis will show:
- Root cause explanations for each error
- Evidence from multiple modules
- Suggested fixes with code locations

## Key Features Demonstrated

1. **Service-level filtering**: Using `service_name` to filter logs by service
2. **Module-level filtering**: Using `module_name` to filter logs by module
3. **Cross-module correlation**: Analyzing how errors in one module affect others
4. **Realistic code structure**: Multiple files, imports, and error handling patterns

