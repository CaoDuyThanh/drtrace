# DrTrace Quickstart Guide

This guide walks you through setting up DrTrace and experiencing the "ask why" flow with a minimal example application.

## Prerequisites

- **Python 3.8+** installed
- **pip** and **venv** available
- **PostgreSQL** (optional, for log storage; Docker recommended for local setup)
- Basic familiarity with Python and command-line tools

## Step 1: Set Up Environment

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

Install DrTrace in editable mode:

```bash
pip install -e .
```

This installs both the `drtrace_client` SDK and the `drtrace_service` daemon.

## Step 2: Set Up Database and Services

For the full experience, set up a local PostgreSQL database and DrTrace daemon. You have three options:

### Option A: Docker Compose (Recommended - Easiest)

This sets up both the database and API server automatically:

```bash
# Copy environment file (optional)
cp .env.example .env

# Start all services
docker-compose up -d

# Initialize database schema (first time only)
docker-compose run --rm drtrace-init

# Verify services are running
docker-compose ps
curl http://localhost:8001/status
```

The API server will be available at `http://localhost:8001` and the database at `localhost:5432`.

**Skip to Step 4** if using Docker Compose (the daemon is already running).

### Option B: Docker Database Only

If you want to use Docker for the database but run the API server natively:

```bash
docker run --name drtrace-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=drtrace \
  -p 5432:5432 \
  -d postgres:15

# Initialize schema
export DRTRACE_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/drtrace"
python scripts/init_db.py
```

Then continue with Step 3 to start the daemon natively.

### Option C: Native Setup

If you have PostgreSQL running locally:

```bash
export DRTRACE_DATABASE_URL="postgresql://user:password@localhost:5432/drtrace"
python scripts/init_db.py
```

**Note**: If you skip database setup, DrTrace will use an in-memory storage backend that doesn't persist logs between daemon restarts. This is fine for testing but limits the analysis capabilities.

## Step 3: Start the Daemon (If Not Using Docker Compose)

**Skip this step if you used Docker Compose in Step 2** - the daemon is already running.

In a terminal, start the DrTrace daemon:

```bash
export DRTRACE_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/drtrace"  # If using database
uvicorn drtrace_service.api:app --host localhost --port 8001
```

You should see output like:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://localhost:8001 (Press CTRL+C to quit)
```

Keep this terminal open. The daemon needs to be running for the client to send logs.

## Step 4: Verify Daemon Status

In a new terminal, verify the daemon is running:

```bash
python -m drtrace_service status
```

You should see:

```
DrTrace daemon status: HEALTHY
Service: drtrace_daemon v0.1.0
Listening on: localhost:8001
```

> 💡 **Tip:** You can also run `python -m drtrace_service init-project` to bootstrap
> a `_drtrace/` config folder and optionally let DrTrace **analyze your project
> and suggest setup changes** (for Python, C++, and JS/TS), applying them with
> automatic backups if you confirm.

## Step 5: Create and Run Sample Application

Create a simple Python application that logs an error. Save this as `example_app.py`:

```python
import logging
import os
import time

from drtrace_client import setup_logging

def main():
    # Set application ID
    os.environ.setdefault("DRTRACE_APPLICATION_ID", "quickstart-app")
    
    # Configure logging
    logger = logging.getLogger("quickstart")
    logging.basicConfig(level=logging.INFO)
    
    # Integrate DrTrace
    setup_logging(logger)
    
    # Log some normal activity
    logger.info("Application starting up")
    logger.info("Processing user request")
    
    # Trigger an error
    try:
        result = 100 / 0  # This will raise ZeroDivisionError
    except ZeroDivisionError:
        logger.exception("Division by zero error occurred")
    
    # Give the background log queue time to flush
    time.sleep(0.5)
    logger.info("Application shutting down")

if __name__ == "__main__":
    main()
```

Run the application:

```bash
python example_app.py
```

You should see normal log output in the console, and the error log will be sent to the DrTrace daemon in the background.

## Step 6: Analyze the Error

Now ask DrTrace "why did this error happen?" using the CLI:

```bash
python -m drtrace_service why \
  --app quickstart-app \
  --since 5m
```

This command:
- Queries logs from the past 5 minutes
- Filters by application ID `quickstart-app`
- Analyzes the error and generates an explanation

### Expected Output

You should see output like:

```
# Analysis Summary

**Application**: quickstart-app
**Time Range**: 2025-12-19 10:30:00 - 2025-12-19 10:35:00
**Logs Analyzed**: 4

## Root Cause

The error occurred because the application attempted to divide 100 by 0, which is mathematically undefined in Python. This operation raises a `ZeroDivisionError` exception.

## Evidence

- **Log Entry** (ERROR, 10:34:22): "Division by zero error occurred"
  - Location: `example_app.py:18`
  - Exception: `ZeroDivisionError`
  
- **Code Context** (`example_app.py:18`):
  ```python
  result = 100 / 0  # This will raise ZeroDivisionError
  ```

## Suggested Fixes

1. **Add input validation** (`example_app.py:17`)
   - Validate divisor is not zero before division
   - Example: `if divisor == 0: raise ValueError("Cannot divide by zero")`

2. **Use safe division** (`example_app.py:17`)
   - Use a helper function that handles zero division gracefully
   - Example: `result = safe_divide(100, 0)  # Returns None or raises custom error`
```

## Step 7: Bootstrap Agent (Optional)

If you want to use the DrTrace agent in your IDE (e.g., Cursor, VS Code with BMAD-style agents), bootstrap the agent file:

```bash
python -m drtrace_service init-agent
```

This creates `agents/log-analysis.md` in your project root. You can then activate the "Log Analysis Agent" in your IDE to query logs using natural language.

**Example agent queries:**
- "explain error from 9:00 to 10:00 for app quickstart-app"
- "what happened in the last 10 minutes for app quickstart-app"
- "show errors from the past hour"

For more details, see the [Agent Integration Examples](../examples/agent-integrations/README.md).

## Step 8: Explore More Commands

### Check Daemon Status

```bash
python -m drtrace_service status
```

### Query Logs Directly

You can also query logs without analysis:

```bash
# Using Python (requires calculating timestamps)
python -c "
from datetime import datetime, timedelta
import time
end = time.time()
start = end - 300  # 5 minutes ago
print(f'Start: {start}, End: {end}')
"
```

Then use the HTTP API or check the logs via the daemon's `/logs/query` endpoint.

### Analyze Specific Time Range

```bash
python -m drtrace_service why \
  --app quickstart-app \
  --start "2025-12-19 10:30:00" \
  --end "2025-12-19 10:35:00"
```

### Filter by Module or Service

```bash
python -m drtrace_service why \
  --app quickstart-app \
  --since 5m \
  --module quickstart \
  --min-level ERROR
```

## Troubleshooting

### Daemon Not Running

If you see:

```
DrTrace daemon status: UNREACHABLE at http://localhost:8001/status
```

**Solution**: Make sure the daemon is running (Step 3). Check that nothing else is using port 8001.

### No Logs Found

If analysis returns "No logs found":

1. **Check time range**: Use `--since 10m` or a wider range if the error happened earlier
2. **Verify application ID**: Ensure `DRTRACE_APPLICATION_ID` matches the `--app` parameter
3. **Check daemon logs**: Look at the daemon terminal for any ingestion errors
4. **Verify database**: If using PostgreSQL, ensure the database is accessible and schema is initialized

### Database Connection Errors

If you see PostgreSQL connection errors:

1. **Check database is running**: `docker ps` (if using Docker)
2. **Verify connection string**: Check `DRTRACE_DATABASE_URL` environment variable
3. **Test connection**: Try connecting with `psql` or another PostgreSQL client

### Client Not Sending Logs

If logs aren't being captured:

1. **Check environment variable**: Ensure `DRTRACE_APPLICATION_ID` is set
2. **Verify daemon URL**: Default is `http://localhost:8001/logs/ingest`
3. **Check DRTRACE_ENABLED**: Should be `true` (default) or unset
4. **Wait for flush**: The client batches logs; add a small delay before app exit

## Next Steps

- **Read the Overview**: See [docs/overview.md](overview.md) for architecture and concepts
- **Explore Agent Integration**: Check [examples/agent-integrations/README.md](../examples/agent-integrations/README.md) for BMAD and LangChain examples
- **Review API Reference**: See [docs/api-reference.md](api-reference.md) for detailed endpoint documentation (coming soon)
- **Try C++ Integration**: See [packages/cpp/drtrace-client/README.md](../packages/cpp/drtrace-client/README.md) for C++ client setup

## Summary

You've successfully:

1. ✅ Installed DrTrace
2. ✅ Set up the database (optional)
3. ✅ Started the daemon
4. ✅ Integrated DrTrace into a sample application
5. ✅ Captured an error with context
6. ✅ Analyzed the error using natural language queries
7. ✅ Received AI-generated root cause explanations with suggested fixes

DrTrace is now ready to help you debug errors in your own applications!

