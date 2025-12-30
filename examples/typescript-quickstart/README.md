# TypeScript Quickstart Example

A minimal working example showing how to use DrTrace logging in a TypeScript application.

## Setup

### 1. Install dependencies

```bash
npm install
```

### 2. Start the DrTrace daemon

In a separate terminal:

```bash
# From project root
pip install -e packages/python
python -m drtrace_service

# Verify it's running
python -m drtrace_service status
```

### 3. Initialize DrTrace in this project

```bash
npx drtrace init --project-root .
```

This creates `_drtrace/config.json`.

## Running the Example

### Development mode (with hot reload)

```bash
npm run dev
```

### Production mode

```bash
npm run build
npm run start
```

## How It Works

The example demonstrates:

1. **Basic logging** - `console.log()` and `console.error()`
2. **DrTrace integration** - Automatic capture via `setup_logging()`
3. **Async operations** - Promise and async/await logging
4. **Error handling** - Exception logging
5. **Analysis** - Enable/disable analysis dynamically

### Main Application

See `src/main.ts` for the implementation.

## Example Output

When running, you'll see:

1. **Console output** - Standard logging to terminal
2. **Daemon logs** - All logs captured and sent to daemon
3. **Analysis** - Query daemon for log analysis

```
✓ Application started
✓ Processing request...
✓ Request completed
✓ Analysis enabled
✓ Error logged and captured
✓ Logs analyzed
```

## Querying Logs

After running the app, query the daemon:

### Via CLI

```bash
# List recent logs
python -m drtrace_service why --app typescript-quickstart

# Analyze last error
python -m drtrace_service why --app typescript-quickstart --since 5m
```

### Via HTTP

```bash
curl -X GET http://localhost:8000/logs/query \
  -G --data-urlencode "application_id=typescript-quickstart" \
  --data-urlencode "min_level=INFO"
```

## Files

- `src/main.ts` - Main application
- `src/utils.ts` - Helper functions
- `_drtrace/config.json` - DrTrace configuration
- `package.json` - Dependencies and scripts
- `tsconfig.json` - TypeScript configuration

## Configuration

Edit `_drtrace/config.json` to customize:

```json
{
  "drtrace": {
    "log_level": "DEBUG",
    "daemon_host": "localhost",
    "daemon_port": 8000
  }
}
```

## Troubleshooting

### "Connection refused" error

- Ensure daemon is running: `python -m drtrace_service status`
- Check daemon host/port in config

### No logs appearing

- Check `log_level` setting
- Verify `DRTRACE_ENABLED=true`
- Restart daemon

### Build errors

- Ensure Node.js 16+ is installed
- Run `npm install` again
- Check TypeScript: `npm run type-check`

## Next Steps

- Check [TypeScript Setup Guide](../../docs/typescript-setup.md)
- Read [Configuration Guide](../../docs/config-guide.md)
- Try [Cross-Language Example](../python-typescript-app/)
- Review [API Reference](../../docs/api-reference.md)
