# DrTrace

## 📖 Documentation

- **[Overview](docs/overview.md)**: Comprehensive overview of DrTrace, its purpose, architecture, and capabilities
- **[Quickstart Guide](docs/quickstart.md)**: End-to-end walkthrough
- **[API Reference](docs/api-reference.md)**: HTTP endpoints and CLI commands
- **[Log-It Agent Guide](docs/log-it-agent-guide.md)**: Interactive logging assistant for adding strategic logs to your code
- **[Example Projects](examples/)**: Advanced examples and multi-language scenarios
  - [Python Multi-Module](examples/python-multi-module/README.md): Realistic multi-module Python application
  - [Python + C++ Multi-Language](examples/python-cpp-multi-language/README.md): Cross-language logging and analysis
- **[Agent Integration Examples](examples/agent-integrations/README.md)**: Framework-specific integration guides
- **[Log Schema](docs/log-schema.md)**: Unified multi-language log schema documentation
- **[Cross-Language Querying](docs/cross-language-querying.md)**: Guide to querying logs across languages

## What is **DrTrace**?

**DrTrace** (formerly known as Doctor Trace) transforms time-consuming log investigation into instant, intelligent explanations. It combines structured logging with AI analysis and source code context to provide root-cause explanations for errors, accessible through natural language queries or agent systems.

**Key Features:**
- ✅ Natural language queries: "explain error from 9:00 to 10:00"
- ✅ AI-powered root cause analysis with suggested fixes
- ✅ Multi-language support (Python, C++)
- ✅ Agent integration (BMAD, LangChain, etc.)
- ✅ Zero performance impact (<1% CPU overhead)

For a complete overview, see [docs/overview.md](docs/overview.md).

## Install the client via pip

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS

pip install -e packages/python
```

This installs the Python packages in editable mode so that:

- `drtrace_client` can be imported from your application, and  
- the local SDK/daemon code under `packages/python/src/` is used directly.

### Supported Python versions & OS

- Python **3.8+** (tested under 3.8)
- Linux/macOS; Windows should work but is not yet validated for this POC.

### Contributor testing note

- From the repo root: `PYTHONPATH=src venv/bin/python -m pytest -q`
- From `packages/python`: `PYTHONPATH=../:../src ../venv/bin/python -m pytest -q`

Both commands ensure the workspace root (which contains `examples/`) is on the import path so example-driven tests resolve.

## Docker Compose Setup (Recommended)

The easiest way to get started is using Docker Compose, which sets up both the database and API server automatically.

### Quick Start with Docker

1. **Copy environment file** (optional, uses defaults if skipped):
```bash
cp .env.example .env
# Edit .env if you want to customize settings
```

2. **Start services**:
```bash
docker-compose up -d
```

3. **Initialize database schema** (runs automatically on first startup, or run manually):
```bash
docker-compose up drtrace-init
# Or run manually if needed:
docker-compose run --rm drtrace-init
```

4. **Verify services are running**:
```bash
docker-compose ps
curl http://localhost:8001/status
```

5. **View logs**:
```bash
docker-compose logs -f
```

6. **Stop services**:
```bash
docker-compose down
```

### Docker Services

- **PostgreSQL**: Database for log storage (port 5432)
- **DrTrace API**: FastAPI daemon server (port 8001)
- **drtrace-init**: One-time database initialization (runs with `--profile init`)

For more details, see [Docker Setup Documentation](#docker-setup).

## Native Setup (Alternative)

If you prefer not to use Docker, you can set up services manually:

### Set up local Postgres for log storage

For Story 2.1 and beyond, logs are designed to be stored in a local Postgres
database. To initialize the schema:

```bash
export DRTRACE_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/drtrace"
python packages/python/scripts/init_db.py
```

This creates a `logs` table matching the ingestion schema. Tests do **not**
require Postgres; the storage layer is mocked in tests.

## Log retention (`DRTRACE_RETENTION_DAYS`)

The daemon includes a simple, opt-in retention mechanism driven by the
`DRTRACE_RETENTION_DAYS` environment variable:

- **Default**: `7` days when `DRTRACE_RETENTION_DAYS` is unset or invalid.
- **Valid range**: clamped to **1–365** days; values below 1 are treated as 1,
  and values above 365 are treated as 365.
- **Usage in development**:
  - Retention does **not** run automatically; instead, helpers are provided so
    you can run housekeeping manually or from a scheduled job:
    - `PostgresLogStorage.get_retention_cutoff(days)` computes a cutoff
      timestamp.
    - `PostgresLogStorage.delete_older_than(cutoff_ts)` deletes rows older than
      that cutoff.
  - This keeps behavior predictable and avoids surprise data loss in local
    environments.
- **Visibility**:
  - The current effective `retention_days` is exposed via the `/status`
    endpoint on the daemon, so you can confirm the active configuration.

## Minimal client configuration in an existing app

In an application that already uses the standard `logging` module:

```python
import logging
import os

from drtrace_client import setup_logging

os.environ.setdefault("DRTRACE_APPLICATION_ID", "my-application-id")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

setup_logging(
  logger,
  application_id="my-application-id",
  # service_name="optional-service-name",
  # daemon_url="http://localhost:8001/logs/ingest",
)

logger.info("Example INFO log from app")
```

This:

- Initializes the client with an `application_id`.
- Attaches a handler to the **standard `logging` module** without removing existing handlers.
- Enqueues enriched log events for delivery to the local daemon, while normal logs
  continue to flow to your existing handlers (console, files, etc.).

## Troubleshooting

- **`ValueError: DRTRACE_APPLICATION_ID is required`**  
  - Set the environment variable before configuring logging, for example:
    - `export DRTRACE_APPLICATION_ID=my-app` (shell), or  
    - `os.environ["DRTRACE_APPLICATION_ID"] = "my-app"` in code.

- **Daemon not running / connection errors**  
  - The client logs warnings like  
    `drtrace_client HTTP transport failed to reach daemon ...`  
    but **never raises** back into your app.
  - Check that your local daemon is listening on `DRTRACE_DAEMON_URL`
    (default: `http://localhost:8001/logs/ingest`).

- **Enable/disable analysis per environment (`DRTRACE_ENABLED`)**
  - `DRTRACE_ENABLED=true` (default if unset) → client queues enriched logs for the daemon.
  - `DRTRACE_ENABLED=false` → client attaches no analysis handler; your existing logging continues unchanged and no logs are sent to the daemon.
  - Recommended:
    - Local POC: leave enabled (default) or set `DRTRACE_ENABLED=true`.
    - CI/other environments where analysis should be off: set `DRTRACE_ENABLED=false`.
- **Logging level behavior**  
  - The DrTrace handler respects logger levels; set your application/root logger to `INFO` (or lower) to emit INFO records.
  - Setting `DRTRACE_ENABLED=0/false/no` disables the handler entirely if you need to silence analysis output.

- **Python version / dependencies**  
  - Ensure you are using Python 3.8+ in a clean virtual environment.
  - Install dependencies via:
    - `pip install -r packages/python/requirements.txt`


