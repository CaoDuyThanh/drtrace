# DrTrace JavaScript Client

DrTrace JavaScript/TypeScript client for distributed tracing-style logging and analysis.

## Installation

```bash
npm install drtrace
```

## Quick Start

### Interactive Project Initialization

```bash
npx drtrace init
```

This runs an interactive setup wizard that creates the `_drtrace/` configuration folder with:
- Main configuration file (`config.json`)
- Environment-specific overrides
- Environment variables template (`.env.example`)
- Configuration guide (`README.md`)
- Default agent specification

### Manual Client Integration

```typescript
import { DrTrace } from 'drtrace';

// Initialize from _drtrace/config.json automatically
const client = DrTrace.init();

// Or override specific options
// const client = DrTrace.init({
//   applicationId: 'my-app',
//   daemonUrl: 'http://localhost:8001',
//   batchSize: 50,
//   flushIntervalMs: 1000,
//   maxRetries: 3,
//   maxQueueSize: 10000,
//   timeoutMs: 5000,
// });

// Attach to console
client.attachToConsole();

// Logs are now automatically sent to the DrTrace daemon
console.log('This is captured by DrTrace');
console.error('Errors are also captured');
```

## Starting the DrTrace Daemon

**Important**: The DrTrace daemon must be running before your application can send logs.

### Option A: Docker Compose (Recommended)

```bash
# From the DrTrace repository root
docker-compose up -d

# Verify it's running
curl http://localhost:8001/status
```

### Option B: Native Python Daemon

```bash
# Set database URL (if using PostgreSQL)
export DRTRACE_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/drtrace"

# Start the daemon
uvicorn drtrace_service.api:app --host localhost --port 8001

# In another terminal, verify it's running
python -m drtrace_service status
```

**Note**: The daemon runs on `http://localhost:8001` by default. Make sure this matches your `daemonUrl` in the config.

## Configuration

Configuration is managed via `_drtrace/config.json` created during `npx drtrace init`.

### Basic Config Structure

```json
{
  "project": {
    "name": "my-app",
    "language": "javascript"
  },
  "drtrace": {
    "applicationId": "my-app-123",
    "daemonUrl": "http://localhost:8001",
    "enabled": true,
    "logLevel": "info",
    "batchSize": 50,
    "flushIntervalMs": 1000,
    "maxRetries": 3,
    "maxQueueSize": 10000,
    "timeoutMs": 5000,
    "retentionDays": 7
  },
  "agent": {
    "enabled": false,
    "framework": "bmad"
  }
}
```

### Environment Variables

Override config via environment variables:
- `DRTRACE_APPLICATION_ID` - Application identifier
- `DRTRACE_DAEMON_URL` - Daemon URL
- `DRTRACE_ENABLED` - Enable/disable DrTrace
- `DRTRACE_LOG_LEVEL` - Log level (debug, info, warn, error)

## Development

### Setup

```bash
npm install
npm run build
```

### Testing

```bash
npm test
npm run test:watch
```

### Building

```bash
npm run build
```

### Linting & Formatting

```bash
npm run lint
npm run format
```

## API Reference

### `new DrTrace(options)`

Create a new DrTrace client instance.

**Options:**
- `applicationId` (required) - Unique application identifier
- `daemonUrl` (optional) - DrTrace daemon URL (default: `http://localhost:8001`)
- `enabled` (optional) - Enable/disable DrTrace (default: `true`)
- `batchSize` (optional) - Batch size for log batching (default: `50`)
- `flushIntervalMs` (optional) - Flush interval in milliseconds (default: `1000`)
- `maxRetries` (optional) - Retry attempts for failed sends with exponential backoff (default: `3`)
- `maxQueueSize` (optional) - Maximum queued log entries before oldest entries are dropped (default: `10000`)
- `timeoutMs` (optional) - Request timeout per batch in milliseconds (default: `5000`)

### `client.attachToConsole()`

Attach DrTrace to Node.js console for automatic log capture.

### `client.log(level, message, metadata?)`

Send a log entry to DrTrace.

**Parameters:**
- `level` - Log level: 'debug', 'info', 'warn', 'error'
- `message` - Log message
- `metadata` (optional) - Additional context as object

## License

MIT
