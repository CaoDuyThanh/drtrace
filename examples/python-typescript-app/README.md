# Python & TypeScript Cross-Language Example

This example demonstrates using DrTrace to collect and analyze logs from both Python and TypeScript services running together.

## Architecture

```
┌─────────────────────────────────────┐
│   HTTP Client (TypeScript)          │
│   - Makes requests to API           │
│   - Logs all operations             │
└────────────┬────────────────────────┘
             │ HTTP
             ▼
┌─────────────────────────────────────┐
│   Python FastAPI Backend            │
│   - Handles requests                │
│   - Processes data                  │
│   - Logs operations                 │
└────────────┬────────────────────────┘
             │
             ▼
┌─────────────────────────────────────┐
│   DrTrace Daemon (Central Logger)   │
│   - Collects logs from both         │
│   - Performs unified analysis       │
│   - Stores searchable logs          │
└─────────────────────────────────────┘
```

## Setup

### Prerequisites

- Python 3.8+
- Node.js 16+
- Local DrTrace daemon running

### 1. Start the DrTrace daemon

```bash
# From project root
pip install -e packages/python
python -m drtrace_service
```

### 2. Install Python backend dependencies

```bash
cd backend
pip install -e .
# or
pip install fastapi uvicorn
```

### 3. Install TypeScript client dependencies

```bash
cd client
npm install
```

## Running the Example

### Terminal 1: Start the Python backend

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

Output:
```
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Terminal 2: Run the TypeScript client

```bash
cd client
npm run dev
```

Output:
```
TypeScript Client Starting
Connecting to http://localhost:8001/api
Creating user...
User created: id=1, name=Alice
Fetching users...
Users: [{ id: 1, name: "Alice" }]
Complete!
```

### Terminal 3: Query unified logs

```bash
# Analyze all logs from both services
python -m drtrace_service why --app cross-language-example

# Analyze just the last 5 minutes
python -m drtrace_service why --app cross-language-example --since 5m

# See all logs with details
python -m drtrace_service query --app cross-language-example
```

## How It Works

### Python Backend (FastAPI)

The backend logs all API operations:

```python
import logging
from fastapi import FastAPI

app = FastAPI()

# DrTrace logging is auto-configured via setup_logging()
logger = logging.getLogger(__name__)

@app.post("/api/users")
async def create_user(name: str):
    logger.info(f"Creating user: {name}")
    # ... implementation
    logger.info(f"User created: {user_id}")
    return {"id": user_id, "name": name}
```

### TypeScript Client

The client logs HTTP interactions:

```typescript
import { setup_logging, ClientConfig } from 'drtrace';

const config = new ClientConfig({
  application_id: 'cross-language-example',
  daemon_host: 'localhost',
  daemon_port: 8000,
});

setup_logging(config);

// Now all console.log/error are captured
console.log('Creating user...');
const response = await fetch('http://localhost:8001/api/users', {
  method: 'POST',
  body: JSON.stringify({ name: 'Alice' }),
});
console.log('User created');
```

## Files

```
python-typescript-app/
├── backend/
│   ├── main.py               # FastAPI application
│   ├── pyproject.toml        # Python dependencies
│   └── _drtrace/
│       └── config.json       # DrTrace config for backend
├── client/
│   ├── src/
│   │   └── main.ts           # TypeScript client
│   ├── package.json          # NPM dependencies
│   └── _drtrace/
│       └── config.json       # DrTrace config for client
└── README.md
```

## Configuration

### Python Backend (`backend/_drtrace/config.json`)

```json
{
  "project_name": "cross-language-backend",
  "application_id": "cross-language-example-py",
  "drtrace": {
    "enabled": true,
    "log_level": "INFO"
  }
}
```

### TypeScript Client (`client/_drtrace/config.json`)

```json
{
  "project_name": "cross-language-client",
  "application_id": "cross-language-example-ts",
  "drtrace": {
    "enabled": true,
    "log_level": "DEBUG"
  }
}
```

## Cross-Language Querying

### Analyze All Logs

```bash
# Get complete picture of what happened
python -m drtrace_service why --app cross-language-example
```

Returns combined analysis from both services:

```
Error Summary: None detected
Activity: 3 requests processed successfully
Timeline:
  - TypeScript: Client started, connected to API
  - Python: API received request, processed user
  - TypeScript: Response received, logged result
```

### Filter by Service

```bash
# Python only
python -m drtrace_service why --app cross-language-example-py

# TypeScript only  
python -m drtrace_service why --app cross-language-example-ts
```

### Analyze Errors Across Services

If an error occurs in the backend, see which client request triggered it:

```bash
# Python error
python -m drtrace_service why --app cross-language-example --since 5m
```

Output might show:
```
Timeline:
  - TypeScript: POST /api/users with name="test"
  - Python: ValueError: Invalid name format
  - TypeScript: HTTP 500 error logged
```

## Troubleshooting

### "Connection refused" from client

- Check Python backend is running: `http://localhost:8001`
- Verify daemon is running: `python -m drtrace_service status`

### No logs appearing in daemon

1. Check both services have `DRTRACE_ENABLED=true`
2. Restart daemon: restart the `python -m drtrace_service` process
3. Check log levels in config files

### Logs not appearing in Python service

- Ensure FastAPI app has logging configured
- Check `_drtrace/config.json` in backend folder
- Verify daemon host/port matches

### Logs not appearing in TypeScript service

- Ensure `setup_logging()` called before any logging
- Check `_drtrace/config.json` in client folder
- Run with `LOG_LEVEL=DEBUG` for diagnostics

## Extensions

Try extending this example:

1. **Add a database** - Log database operations from Python
2. **Add error handling** - Trigger intentional errors and analyze
3. **Add authentication** - Log auth flows across both services
4. **Add third service** - Java, Go, or Node.js backend service
5. **Real-time monitoring** - Stream logs to dashboard

## References

- [TypeScript Setup Guide](../../docs/typescript-setup.md)
- [Configuration Guide](../../docs/config-guide.md)
- [API Reference](../../docs/api-reference.md)
- [Python Documentation](../../docs/overview.md)
