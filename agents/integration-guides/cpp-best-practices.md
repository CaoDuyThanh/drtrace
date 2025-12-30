# C++ DrTrace Best Practices

This guide provides best practices for configuring DrTrace in C++ applications.

## Crash-Safe Logging

For applications where crash logs are critical (robotics, autonomous systems, safety-critical software):

### Configuration Options

| Configuration | Crash Safety | Network Overhead | Use Case |
|---------------|--------------|------------------|----------|
| `batch_size=1` | Highest | Highest | Safety-critical systems |
| `batch_size=5`, `flush=1s` | Medium | Medium | Important crash debugging |
| `batch_size=10`, `flush=5s` (default) | Lower | Lowest | General applications |

### Example: Safety-Critical Configuration

```cpp
drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

// For safety-critical applications: immediate send
config.batch_size = 1;  // Each log sent immediately
```

### Example: Balanced Configuration

```cpp
drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

// Balanced approach
config.batch_size = 5;
config.flush_interval = std::chrono::milliseconds(1000);  // 1 second
```

### Recommendation

For most applications, the default configuration is appropriate. Only reduce batch size if:
- Crash debugging is a primary concern
- You're willing to accept higher network overhead
- The application is safety-critical

**Note:** Signal handlers are inherently unsafe in C++. Rather than implementing partial solutions, we recommend configuring `batch_size=1` for applications where crash logs are critical.

## Log Level Filtering

Filter logs at the client to reduce network overhead in production:

```cpp
drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

// Only send WARN and above in production
config.min_level = drtrace::core::LogLevel::WARN;
```

Or via environment variable:
```bash
export DRTRACE_MIN_LEVEL=warn
```

### Available Levels

| Level | Value | Description |
|-------|-------|-------------|
| DEBUG | 0 | Detailed debugging information |
| INFO | 1 | General operational messages |
| WARN | 2 | Warning conditions |
| ERROR | 3 | Error conditions |
| CRITICAL | 4 | Critical failures |

## Buffer Size Limits

Prevent memory issues when daemon is unavailable:

```cpp
drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

// Limit buffer to 10000 logs (drop oldest when full)
config.max_buffer_size = 10000;
```

Or via environment variable:
```bash
export DRTRACE_MAX_BUFFER_SIZE=10000
```

### Behavior

- When buffer is full, **oldest logs are dropped** to make room for new ones
- Set to `0` for unlimited buffer (not recommended for production)
- Default: 10000 logs

### Memory Estimation

Each log record is approximately 200-500 bytes in memory. With default 10000 buffer:
- Minimum: ~2 MB
- Maximum: ~5 MB

## Circuit Breaker Behavior

The DrTrace client uses a circuit breaker pattern to maintain consistent performance:

### How It Works

```
CLOSED (normal) ──[failure]──> OPEN (fast-fail)
     ^                              │
     │                    [cooldown expires]
     │                              v
     └────[success]───────── HALF-OPEN (probe)
```

- **CLOSED**: Normal operation, requests go through
- **OPEN**: After failure, all requests fast-fail (< 1us) for 30 seconds
- **HALF-OPEN**: After cooldown, one probe request to check recovery

### Configuration

```cpp
drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

// Probe every 60 seconds instead of default 30
config.circuit_reset_interval = std::chrono::milliseconds(60000);
```

Or via environment variable:
```bash
export DRTRACE_CIRCUIT_RESET_MS=60000
```

### Performance Impact

| Scenario | Network Calls | Latency |
|----------|---------------|---------|
| Daemon UP | 1 (normal) | ~10ms |
| Daemon DOWN (circuit open) | 0 | < 1us |
| Daemon DOWN (probe) | 1-3 | ~3s |

This ensures your application's logging performance is not affected by daemon availability.

## Configurable Timeouts

Fine-tune network behavior for your environment:

```cpp
drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

// Increase timeout for slow networks
config.http_timeout = std::chrono::milliseconds(5000);  // 5 seconds

// Increase backoff for high-latency networks
config.retry_backoff = std::chrono::milliseconds(500);  // 500ms base

// Reduce retries for faster failure detection
config.max_retries = 2;
```

### Environment Variables

```bash
export DRTRACE_HTTP_TIMEOUT_MS=5000
export DRTRACE_RETRY_BACKOFF_MS=500
export DRTRACE_MAX_RETRIES=2
```

### Defaults

| Setting | Default | Description |
|---------|---------|-------------|
| `http_timeout` | 1000ms | HTTP request timeout |
| `retry_backoff` | 100ms | Base backoff between retries |
| `max_retries` | 3 | Maximum retry attempts |

### Retry Behavior

Total worst-case delay = `http_timeout * max_retries + backoff * (1+2+...+(max_retries-1))`

With defaults: `1000*3 + 100*(1+2)` = 3300ms per batch

## Complete Configuration Example

```cpp
#include "drtrace_sink.hpp"

int main() {
    // Load from environment with overrides
    drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

    // Safety-critical application settings
    config.batch_size = 1;
    config.min_level = drtrace::core::LogLevel::INFO;
    config.max_buffer_size = 5000;
    config.circuit_reset_interval = std::chrono::milliseconds(10000);
    config.http_timeout = std::chrono::milliseconds(2000);
    config.max_retries = 2;

    drtrace::DrtraceClient client(config);

    client.info("Application started");
    // ... application code ...

    return 0;
}
```

## Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DRTRACE_ENABLED` | true | Enable/disable logging |
| `DRTRACE_DAEMON_URL` | http://localhost:8001/logs/ingest | Daemon endpoint |
| `DRTRACE_APPLICATION_ID` | my-app | Application identifier |
| `DRTRACE_MIN_LEVEL` | debug | Minimum log level |
| `DRTRACE_MAX_BUFFER_SIZE` | 10000 | Maximum buffer size |
| `DRTRACE_CIRCUIT_RESET_MS` | 30000 | Circuit breaker reset interval |
| `DRTRACE_HTTP_TIMEOUT_MS` | 1000 | HTTP request timeout |
| `DRTRACE_RETRY_BACKOFF_MS` | 100 | Base retry backoff |
| `DRTRACE_MAX_RETRIES` | 3 | Maximum retry attempts |
