# DrTrace C++ Client Integration

This directory contains the C++ client integration for DrTrace, allowing C++ applications using `spdlog` to send structured logs to the DrTrace daemon using the unified schema.

**Location**: Part of the monorepo at `packages/cpp/drtrace-client/`

## Overview

The C++ integration provides:

- **DrtraceSink**: A spdlog sink that enriches log messages with unified schema fields
- **HttpTransport**: HTTP client for sending log batches to the daemon
- **Configuration**: Environment-based configuration matching the Python client

## Dependencies

- **C++17** or later
- **libcurl**: HTTP client library for sending requests to the daemon (must be installed)
- **CMake 3.14+** (for building)
- **spdlog**: Automatically downloaded and built via CMake FetchContent (v1.13.0)

## Building

### From Repository Root

```bash
cd packages/cpp/drtrace-client
mkdir -p build && cd build
cmake ..
make
```

**Note:** On first build, CMake will automatically download spdlog (v1.13.0) from GitHub using FetchContent. This requires an internet connection.

This will build:
- `libdrtrace_cpp_client.a` (static library)

### Manual Compilation

```bash
cd packages/cpp/drtrace-client
g++ -std=c++17 \
    -Isrc \
    src/drtrace_sink.cpp \
    -lspdlog -lcurl -pthread \
    -o libdrtrace_cpp_client.a
```

## Configuration

The C++ client uses the same environment variables as the Python client:

### Required

- `DRTRACE_APPLICATION_ID`: Identifier for your application

### Optional

- `DRTRACE_DAEMON_URL`: Daemon endpoint (default: `http://localhost:8001/logs/ingest`)
- `DRTRACE_SERVICE_NAME`: Service name for logs
- `DRTRACE_ENABLED`: Set to `"false"` to disable (default: enabled)
- `DRTRACE_MIN_LEVEL`: Minimum log level to send (default: `debug`). Values: `debug`, `info`, `warn`, `error`, `critical`
- `DRTRACE_MAX_BUFFER_SIZE`: Maximum logs to buffer (default: `10000`). Set to `0` for unlimited.
- `DRTRACE_CIRCUIT_RESET_MS`: Circuit breaker cooldown in milliseconds (default: `30000`)
- `DRTRACE_HTTP_TIMEOUT_MS`: HTTP request timeout in milliseconds (default: `1000`)
- `DRTRACE_RETRY_BACKOFF_MS`: Base retry backoff in milliseconds (default: `100`)
- `DRTRACE_MAX_RETRIES`: Maximum retry attempts (default: `3`)

## Usage

### Basic Example

```cpp
#include "drtrace_sink.hpp"
#include <spdlog/spdlog.h>

int main() {
  // Load configuration from environment
  drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();

  // Create a logger with DrTrace integration
  auto logger = drtrace::create_drtrace_logger("my_app", config);

  // Use the logger normally
  logger->info("Application started");
  logger->warn("Low memory warning");
  logger->error("Something went wrong");

  // Flush before exit (or wait for automatic flush)
  logger->flush();
  return 0;
}
```

### Adding to Existing Logger

```cpp
auto logger = spdlog::get("existing_logger");
drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();
drtrace::setup_drtrace(logger, config);

// Now this logger will also send logs to DrTrace daemon
logger->info("This log goes to both existing sinks and DrTrace");
```

## Unified Schema Mapping

The C++ integration maps spdlog concepts to the unified schema:

| Unified Schema Field | C++ Source |
|---------------------|------------|
| `ts` | Current timestamp (Unix epoch seconds) |
| `level` | spdlog level (DEBUG, INFO, WARN, ERROR, etc.) |
| `message` | spdlog log message payload |
| `application_id` | From `DRTRACE_APPLICATION_ID` environment variable |
| `service_name` | From `DRTRACE_SERVICE_NAME` environment variable (optional) |
| `module_name` | spdlog logger name |
| `file_path` | spdlog source location (if available) |
| `line_no` | spdlog source line number (if available) |
| `context` | JSON object with `{"language": "cpp", "thread_id": "..."}` |

## Batching and Flushing

Logs are automatically batched and sent to the daemon:

- **Batch size**: 10 records (configurable via `DrtraceConfig::batch_size`)
- **Flush interval**: 5 seconds (configurable via `DrtraceConfig::flush_interval`)
- **Manual flush**: Call `logger->flush()` to send immediately

## Error Handling

The HTTP transport handles network errors gracefully:

- **Circuit breaker pattern**: When daemon is unavailable, requests fast-fail (< 1µs) instead of blocking
- **Automatic recovery**: Probes every 30 seconds to detect daemon availability
- Retries up to 3 times with exponential backoff (configurable)
- Logs are dropped if the daemon is unavailable (no exceptions thrown)
- Application continues normally even if log delivery fails

For detailed configuration options, see [C++ Best Practices Guide](../../agents/integration-guides/cpp-best-practices.md).

## Running the Example

1. **Start the DrTrace daemon** (if not already running):
   ```bash
   python -m drtrace_service
   ```

2. **Set environment variables**:
   ```bash
   export DRTRACE_APPLICATION_ID="my-cpp-app"
   export DRTRACE_DAEMON_URL="http://localhost:8001/logs/ingest"
   ```

3. **Run the example**:
   ```bash
   ./minimal_cpp_app
   ```

4. **Verify logs in the daemon**:
   ```bash
   # Query logs via the daemon API or check the database
   curl "http://localhost:8001/logs/query?start_ts=0&end_ts=$(date +%s)"
   ```

## Limitations (POC)

- **No persistent queue**: Logs are dropped if the daemon is unavailable
- **Synchronous HTTP**: Uses blocking libcurl calls (background thread handles batching)
- **Basic error handling**: Network errors are logged but not surfaced to application
- **No authentication**: Assumes local daemon with no auth (matches Python client POC)

## Future Enhancements

- Persistent local queue for offline operation
- Async HTTP transport using libcurl multi interface
- More sophisticated retry and backoff strategies
- Support for Unix domain sockets (matching Python client roadmap)

