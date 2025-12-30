# TypeScript Setup Guide

This guide covers setting up and using the DrTrace JavaScript/TypeScript client in your Node.js and TypeScript projects.

## Installation

### Using npm

```bash
npm install drtrace
```

### Using yarn

```bash
yarn add drtrace
```

## Quick Start

### 1. Initialize DrTrace in Your Project

DrTrace includes an interactive initialization command to set up configuration:

```bash
npx drtrace init
```

This creates a `_drtrace/` directory with:
- `config.json` - Main configuration file
- `.env.example` - Environment variable template
- `README.md` - Configuration documentation

### 2. Configure Your Application

Edit `_drtrace/config.json` to match your application:

```json
{
  "project_name": "my-app",
  "application_id": "my-app-prod-123",
  "drtrace": {
    "enabled": true,
    "daemon_host": "localhost",
    "daemon_port": 8000,
    "log_level": "INFO"
  }
}
```

### 3. Set Up Environment Variables

Copy the example file and add your values:

```bash
cp _drtrace/.env.example .env
```

Then update `.env`:

```bash
DRTRACE_APPLICATION_ID=my-app-prod-123
DRTRACE_DAEMON_URL=http://localhost:8000
DRTRACE_ENABLED=true
```

## Basic Usage

### TypeScript

```typescript
import { setup_logging, ClientConfig } from 'drtrace';

// Initialize logging with default config
const config = new ClientConfig({
  application_id: 'my-app',
  daemon_host: 'localhost',
  daemon_port: 8000,
});

const client = setup_logging(config);

// Now use standard logging
console.log('Application started');
console.error('An error occurred');
```

### JavaScript

```javascript
const { setup_logging, ClientConfig } = require('drtrace');

const config = new ClientConfig({
  application_id: 'my-app',
  daemon_host: 'localhost',
  daemon_port: 8000,
});

const client = setup_logging(config);

console.log('Application started');
console.error('An error occurred');
```

## Configuration

### Programmatic Configuration

```typescript
import { ClientConfig } from 'drtrace';

const config = new ClientConfig({
  application_id: 'my-app',
  daemon_host: 'localhost',
  daemon_port: 8000,
  log_level: 'DEBUG',
  environment: 'production',
  enabled: true,
});
```

### Configuration Priority

DrTrace loads configuration in this order (highest to lowest priority):

1. Programmatic configuration (code)
2. Environment variables (`DRTRACE_*`)
3. `.env` file (via dotenv)
4. `_drtrace/config.json`
5. Default configuration

### Environment Variables

All configuration can be overridden via environment variables:

```bash
DRTRACE_APPLICATION_ID=my-app
DRTRACE_DAEMON_HOST=log-daemon.example.com
DRTRACE_DAEMON_PORT=8000
DRTRACE_LOG_LEVEL=DEBUG
DRTRACE_ENVIRONMENT=production
DRTRACE_ENABLED=true
```

## Enable/Disable Analysis

By default, logging is captured and sent to the daemon for analysis. You can toggle this:

```typescript
import { setup_logging } from 'drtrace';

const client = setup_logging(config);

// Disable analysis (logs still captured, but not analyzed)
client.disable_analysis();

// Enable analysis
client.enable_analysis();
```

## Logging to Specific Modules

You can attach DrTrace logging to specific modules:

```typescript
import { Logger } from 'drtrace';

// Create a logger for a specific module
const logger = new Logger('my-module');

logger.log('info', 'Module started');
logger.log('error', 'An error occurred');
```

## Working with Express

```typescript
import express from 'express';
import { setup_logging } from 'drtrace';

const app = express();
const client = setup_logging(config);

// Now all console.log/console.error in your Express app is captured
app.get('/', (req, res) => {
  console.log(`Request to /`);
  res.send('Hello, World!');
});

app.listen(3000, () => {
  console.log('Server listening on port 3000');
});
```

## Working with TypeScript

### Type Definitions

All DrTrace exports include full TypeScript type definitions:

```typescript
import { ClientConfig, Logger, AnalysisResult } from 'drtrace';

// Full type support
const config: ClientConfig = {
  application_id: 'my-app',
  daemon_host: 'localhost',
  daemon_port: 8000,
};

const logger: Logger = new Logger('my-module');
```

### Strict Mode

DrTrace is compatible with TypeScript strict mode:

```bash
tsc --strict
```

## Daemon Setup

**Important**: The DrTrace daemon must be running before your JavaScript/TypeScript application can send logs.

### Option A: Docker Compose (Recommended)

The easiest way to start both the database and daemon:

```bash
# From the DrTrace repository root
docker-compose up -d

# Verify it's running
curl http://localhost:8001/status
```

The daemon will be available at `http://localhost:8001`.

### Option B: Native Python Daemon

If you have Python and PostgreSQL installed:

```bash
# Set database URL (if using PostgreSQL)
export DRTRACE_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/drtrace"

# Start the daemon
uvicorn drtrace_service.api:app --host localhost --port 8001

# In another terminal, verify it's running
python -m drtrace_service status
```

**Note**: Keep the daemon terminal open while developing. The daemon must be running for logs to be sent.

### Production

For production deployment, ensure:
1. Daemon is running on your configured host/port
2. Network connectivity exists between your app and daemon
3. `DRTRACE_ENABLED` is `true`

## Troubleshooting

### Daemon Not Responding

If you see connection errors:

1. Check daemon is running:
   ```bash
   python -m drtrace_service status
   ```

2. Verify host/port in configuration:
   ```bash
   DRTRACE_DAEMON_HOST=localhost
   DRTRACE_DAEMON_PORT=8000
   ```

3. Check network connectivity:
   ```bash
   curl http://localhost:8000/daemon/status
   ```

### Logs Not Appearing

1. Verify `DRTRACE_ENABLED=true`
2. Check `log_level` setting (DEBUG shows all logs)
3. Ensure `setup_logging()` is called early in your app startup

### Performance Issues

1. Increase `max_queue_size` in config if you have high log volume
2. Adjust `flush_interval` for batch optimization
3. Use `disable_analysis()` if analysis is not needed

## Next Steps

- Read [Configuration Guide](./config-guide.md) for detailed config schema
- Try the [TypeScript Quickstart Example](../examples/typescript-quickstart/)
- Explore [Cross-Language Examples](../examples/python-typescript-app/)
- Check [API Reference](./api-reference.md) for all available methods

## Support

For issues or questions:
- Check [API Reference](./api-reference.md)
- Review example projects
- File an issue on GitHub
