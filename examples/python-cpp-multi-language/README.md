# Python + C++ Multi-Language Example

This example demonstrates DrTrace integration across multiple languages (Python and C++) in a single application, showing how to analyze incidents that span multiple components.

## What This Demonstrates

- **Multi-language logging**: Logs from both Python and C++ components
- **Unified schema**: Both languages use the same log schema
- **Cross-language analysis**: Analyzing incidents that involve both Python and C++ code
- **Service correlation**: Correlating logs from different language components

## Project Structure

```
python-cpp-multi-language/
├── README.md
├── python_main.py        # Python main application
├── python_service.py     # Python service component
└── cpp_component.cpp     # C++ component
```

## Prerequisites

1. **Python dependencies**:
```bash
pip install -e /path/to/drtrace
```

2. **C++ build tools**:
- CMake 3.15+
- C++17 compiler (g++ or clang++)
- libcurl development libraries

3. **DrTrace C++ client**:
```bash
cd ../../packages/cpp/drtrace-client
mkdir build && cd build
cmake ..
make
```

## Setup

1. **Start the DrTrace daemon** (in a separate terminal):

```bash
export DRTRACE_DATABASE_URL="postgresql://postgres:postgres@localhost:5432/drtrace"
uvicorn drtrace_service.api:app --host localhost --port 8001
```

2. **Set environment variables**:

```bash
export DRTRACE_APPLICATION_ID="multi-language-app"
export DRTRACE_DAEMON_URL="http://localhost:8001/logs/ingest"
```

## Building the C++ Component

```bash
cd examples/python-cpp-multi-language
mkdir build && cd build
cmake ..
make
cd ..
```

This will create `build/cpp_component` executable.

## Running the Example

### Option 1: Run Python and C++ separately

**Terminal 1 - Python component:**
```bash
cd examples/python-cpp-multi-language
python python_main.py
```

**Terminal 2 - C++ component:**
```bash
cd examples/python-cpp-multi-language
./build/cpp_component
```

### Option 2: Run from Python (spawns C++ process)

```bash
cd examples/python-cpp-multi-language
python python_main.py --with-cpp
```

## Analyzing Cross-Language Logs

After running both components, analyze the logs:

```bash
# Analyze all errors from both languages
python -m drtrace_service why \
  --application-id multi-language-app \
  --since 5m

# Analyze errors from Python only
python -m drtrace_service why \
  --application-id multi-language-app \
  --since 5m \
  --module-name python_service

# Analyze errors from C++ only
python -m drtrace_service why \
  --application-id multi-language-app \
  --since 5m \
  --module-name cpp_component

# Cross-language analysis (both components)
python -m drtrace_service why \
  --application-id multi-language-app \
  --since 5m \
  --module-name python_service \
  --module-name cpp_component
```

## Expected Output

The application will:
1. Start Python service and log operations
2. Start C++ component and log operations
3. Trigger errors in both components
4. Send logs to DrTrace daemon with unified schema

The analysis will show:
- Root cause explanations that reference both Python and C++ code
- Evidence from multiple language components
- Suggested fixes in both languages

## Key Features Demonstrated

1. **Unified log schema**: Both Python and C++ logs use the same schema
2. **Cross-language querying**: Query logs from multiple languages together
3. **Service correlation**: Correlate logs by `service_name` across languages
4. **Module filtering**: Filter by `module_name` to focus on specific components
5. **Cross-module analysis**: Analyze incidents spanning multiple language components

## Architecture

```
┌─────────────────┐
│  Python Service │──┐
│  (python_main)  │  │
└─────────────────┘  │
                     ├──> DrTrace Daemon
┌─────────────────┐  │
│  C++ Component  │──┘
│  (cpp_component) │
└─────────────────┘
```

Both components:
- Use the same `application_id`: "multi-language-app"
- Use different `module_name` values: "python_service" and "cpp_component"
- Can use the same or different `service_name` values
- Send logs to the same daemon endpoint

## Troubleshooting

### C++ component fails to build

- Ensure CMake and C++ compiler are installed
- Check that libcurl development libraries are available
- Verify spdlog is fetched correctly by CMake

### C++ logs not appearing

- Verify C++ component is sending to correct daemon URL
- Check daemon is running and accessible
- Ensure `DRTRACE_APPLICATION_ID` matches in both components

### Cross-language analysis shows no results

- Ensure both components use the same `application_id`
- Check time range includes logs from both components
- Verify both components are actually sending logs

