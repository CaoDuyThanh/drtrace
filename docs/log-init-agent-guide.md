# log-init Agent Guide

## Overview

The `log-init` agent is the **DrTrace Setup Assistant**. It:

- Analyzes your project structure by **reading real source files** (Python, C++, JS/TS).
- Detects languages, build systems, and entry points.
- Suggests **concrete integration points** and **copy‑pasteable code** for DrTrace.
- Generates configuration suggestions and verification steps so you can confirm setup.

It is designed to be **non-destructive**: it recommends minimal, best‑practice‑aligned changes and warns about potential conflicts.

## Activation

### 1. Bootstrap the agent file

From your project root:

```bash
python -m drtrace_service init-agent --agent log-init
```

This creates `_drtrace/agents/log-init.md` (or another location if you pass `--path`).

### 2. Load in your IDE / agent host

- Point your IDE/agent host to `_drtrace/agents/log-init.md`, or  
- Use `@log-init` if your host supports shorthand activation.

On activation, the agent will:

1. Load its persona and rules from the spec.  
2. Explain that it must **read your project files** before suggesting setup.  
3. Show a menu of setup actions you can choose from.

## Menu Items

The `log-init.md` agent exposes a menu like:

- **Analyze my project (`A`)**
  - Reads key files: `main.py`, `CMakeLists.txt`, `package.json`, etc.
  - Detects languages, build systems, entry points, and existing logging.
  - Returns language‑specific setup suggestions with integration points and config changes.

- **Suggest Python setup (`P`)**
  - Focuses on Python projects.
  - Suggests where to call `setup_logging()` (e.g., `main.py`, `app.py`, `__init__.py`).
  - Provides copy‑pasteable code and env/dependency suggestions.

- **Suggest C++ setup (`C`)**
  - Reads `CMakeLists.txt` and C++ entry points.
  - **Automatically copies** `drtrace_sink.hpp` to `third_party/drtrace/drtrace_sink.hpp`
  - **Detects spdlog usage** by reading C++ source files
  - Suggests appropriate CMake pattern (with or without spdlog based on detection)
  - Provides integration patterns (spdlog adapter OR direct API based on detection)

- **Suggest JavaScript setup (`J`)**
  - Reads `package.json` and JS/TS entry points (e.g., `main.ts`, `index.js`).
  - Suggests `drtrace` dependency and initialization snippets.

- **Validate my setup (`V`)**
  - Checks whether DrTrace is already wired correctly (Python, C++, JS/TS).
  - Reports missing integration points or configuration gaps.

Each menu item uses **file reading as the primary method**, and only optionally calls helper APIs.

## Usage Examples

### Python Setup Example

#### Step 1: Ask for suggestions

In your agent host:

> “Analyze my Python project in `/path/to/project` and suggest setup.”

The agent will:

- Read files like `main.py`, `app.py`, `__init__.py`, `requirements.txt`, `pyproject.toml`.
- Detect existing logging usage (e.g., `logging` imports).
- Suggest integration points and configuration changes.

Example suggestion (simplified):

```markdown
## Integration Points

### 1. main.py (Required)
**Location**: `main.py:15`  
**Reason**: Main entry point – best place to initialize logging for the entire app.

```python
# Setup DrTrace logging
import logging
import os
from drtrace_client import setup_logging

# Use DRTRACE_APPLICATION_ID if set; otherwise fall back to value from _drtrace/config.json
application_id = os.environ.get("DRTRACE_APPLICATION_ID", "my-app-from-config")

logger = logging.getLogger()

setup_logging(
    logger,
    application_id=application_id,
    service_name="my-service",
)

logger.info("Application starting")
```
```

#### Step 2: Apply via CLI (optional)

Run:

```bash
python -m drtrace_service init-project
```

When prompted:

- Answer **Yes** to “Analyze project and suggest setup?”  
- Answer **Yes** to “Apply suggested setup changes?”

The CLI will:

- Insert the suggested `setup_logging()` snippet into `main.py`, after imports.  
- Update/create `.env`, `.env.example`, `requirements.txt` or `pyproject.toml` with DrTrace configuration.  
- Create timestamped backups before each change.

### C++ Setup Example (Header-Only)

#### Step 1: Ask for C++ suggestions

> "Suggest C++ setup for my project at `/path/to/cpp-project`."

The agent will:

- **Automatically copy** `drtrace_sink.hpp` to `third_party/drtrace/drtrace_sink.hpp` (searches monorepo, node_modules, or site-packages)
- **Detect spdlog usage** by reading C++ source files (`.cpp`, `.hpp`, `.h`) for `#include <spdlog/` or `#include "spdlog/"`
- Read `CMakeLists.txt` and any C++ entry files (e.g., `main.cpp`)
- Suggest appropriate CMake pattern (with or without spdlog based on detection)
- Provide integration code (spdlog adapter OR direct API based on detection)

**Header File Copying:**

The agent automatically copies `drtrace_sink.hpp` to `third_party/drtrace/drtrace_sink.hpp` when suggesting C++ setup. It searches for the source file efficiently in this order:

1. **npm package location** (fastest - if `package.json` exists):
   - Uses `npm list drtrace` or `npm root` to locate package
   - Checks `node_modules/drtrace/packages/cpp/drtrace-client/src/drtrace_sink.hpp`
   
2. **pip package location** (fast - if Python available):
   - Uses Python import to locate package
   - Checks `site-packages/drtrace_service/.../drtrace_sink.hpp`
   
3. **Monorepo check** (limited scope):
   - Searches upward from project root (max 6 levels) for `packages/cpp/drtrace-client/src/drtrace_sink.hpp`
   - Limited to project directory tree only (not entire filesystem)
   
4. **Ask user** (last resort):
   - Only if all above methods fail

**Note:** The agent prioritizes package manager commands over file system scanning for better performance.

**spdlog Detection:**

The agent automatically detects spdlog usage by reading C++ source files (`.cpp`, `.hpp`, `.h`) and searching for `#include <spdlog/` or `#include "spdlog/"`. Based on detection:
- **If spdlog detected**: Uses Pattern 1 (spdlog adapter)
- **If spdlog NOT detected**: Uses Pattern 2 (Direct API - NO spdlog required)

**Important:** The agent will **never** suggest adding spdlog if it's not detected. Instead, it will use Pattern 2 (Direct API) which works alongside any existing logging framework (ROS, glog, etc.) without requiring spdlog.

**Pattern 1: With spdlog (if spdlog detected)**

```cmake
# Header file already copied to third_party/drtrace/drtrace_sink.hpp
# Note: third_party/drtrace/ should be committed to git (unlike _drtrace/ which is gitignored)

# Include the third_party/drtrace directory so the header can be found:
# Path is relative to CMakeLists.txt location (${CMAKE_CURRENT_SOURCE_DIR})
# If your CMakeLists.txt is at the project root, third_party/drtrace will be at the project root.
# If CMakeLists.txt is in a subdirectory, adjust the path accordingly.
target_include_directories(your_target PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/third_party/drtrace
)

# spdlog detected - include spdlog setup:
find_package(spdlog QUIET)

if(NOT spdlog_FOUND)
    # Fallback: Use FetchContent to download and build spdlog automatically
    include(FetchContent)
    
    FetchContent_Declare(
        spdlog
        GIT_REPOSITORY https://github.com/gabime/spdlog.git
        GIT_TAG        v1.13.0
        GIT_SUBMODULES ""
    )
    
    FetchContent_MakeAvailable(spdlog)
endif()

# Link required dependencies:
#   - spdlog::spdlog (from find_package or FetchContent)
#   - CURL::libcurl (system dependency - must be installed)
target_link_libraries(your_target PRIVATE
  spdlog::spdlog
  CURL::libcurl
)
```

**Pattern 2: Without spdlog (if spdlog NOT detected)**

```cmake
# Header file already copied to third_party/drtrace/drtrace_sink.hpp
# Note: third_party/drtrace/ should be committed to git (unlike _drtrace/ which is gitignored)

# Include the third_party/drtrace directory so the header can be found:
# Path is relative to CMakeLists.txt location (${CMAKE_CURRENT_SOURCE_DIR})
# If your CMakeLists.txt is at the project root, third_party/drtrace will be at the project root.
# If CMakeLists.txt is in a subdirectory, adjust the path accordingly.
target_include_directories(your_target PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/third_party/drtrace
)

# spdlog NOT detected - using direct API (no spdlog required):
# Link required dependencies:
#   - CURL::libcurl (system dependency - must be installed)
target_link_libraries(your_target PRIVATE
  CURL::libcurl
)
```

Example code suggestions:

**Pattern 1: With spdlog (if your project uses spdlog):**

```cpp
#include "third_party/drtrace/drtrace_sink.hpp"
#include <spdlog/spdlog.h>

int main(int argc, char** argv) {
    // Load configuration from environment (reads DRTRACE_APPLICATION_ID or _drtrace/config.json)
    drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();
    
    // Use helper function to create logger with DrTrace integration
    auto logger = drtrace::create_drtrace_logger("my_app", config);

    logger->info("Application starting with DrTrace");
    // ...
}
```

**Pattern 2: Without spdlog (direct API):**

```cpp
#include "third_party/drtrace/drtrace_sink.hpp"

int main(int argc, char** argv) {
    // Load configuration from environment (reads DRTRACE_APPLICATION_ID or _drtrace/config.json)
    drtrace::DrtraceConfig config = drtrace::DrtraceConfig::from_env();
    
    // Use direct API (no spdlog required)
    drtrace::DrtraceClient client(config, "my_app");

    client.info("Application starting with DrTrace");
    client.error("Error occurred", __FILE__, __LINE__);
    // ...
}
```

**Note:** The spdlog adapter is automatically available if spdlog is detected. If your project doesn't use spdlog, use the direct API (`DrtraceClient`) which only requires libcurl.

**Framework-Specific Integration Guides:**

The `init-project` CLI automatically copies framework-specific integration guides (e.g., ROS integration) to `_drtrace/agents/integration-guides/` during initialization. These guides provide detailed examples for specific frameworks and can be referenced when using the agent.

**Note:** The agent automatically copies the header file and detects spdlog usage, so you don't need to run `init-project` separately. However, if you also run `init-project` and apply suggestions, the CLI will:

- Copy `third_party/drtrace/drtrace_sink.hpp` into your project for C++ language (committed to git)
- Copy framework-specific integration guides to `_drtrace/agents/integration-guides/` (e.g., `cpp-ros-integration.md`)
- Suggest the `target_include_directories` and `target_link_libraries` pattern above.

### JavaScript/TypeScript Setup Example

#### Step 1: Ask for JS/TS suggestions

> “Suggest JavaScript/TypeScript setup for my project at `/path/to/js-project`.”

The agent will:

- Read `package.json`, `tsconfig.json`, and common entry files such as `main.ts`, `index.js`.  
- Detect the package manager (npm/yarn/pnpm).  
- Suggest installation and initialization patterns.

Example suggestion:

```markdown
## Package Installation

- **Package Manager**: `npm`  
- **Install Command**: `npm install drtrace`

## Initialization Points

### 1. src/main.ts (Required)
**Location**: `src/main.ts:1`  
**Reason**: Main TS entry point – best place to initialize DrTrace client.

```typescript
import { setup_logging, ClientConfig } from 'drtrace';

// Use DRTRACE_APPLICATION_ID if set; otherwise fall back to value from _drtrace/config.json
const applicationId = process.env.DRTRACE_APPLICATION_ID || 'my-app-from-config';

const config = new ClientConfig({
  application_id: applicationId,
  daemon_host: 'localhost',
  daemon_port: 8001,
});

const client = setup_logging(config);

console.log('Application starting');
```
```

#### Step 2: Apply via CLI (optional)

With `init-project` apply enabled, the CLI will:

- Add `"drtrace": "^0.2.0"` to `package.json` dependencies (with backup).  
- Append the initialization snippet to `src/main.ts` or the detected entry file.

### Multi-Language Example

For a project that has **Python, C++, and JS/TS**:

1. Run the **log-init agent** with "Analyze my project" to get a combined markdown report.  
2. Run `python -m drtrace_service init-project` and apply suggestions:
   - Python integration into `main.py` or `app.py`.  
   - C++ header-only integration (`third_party/drtrace/drtrace_sink.hpp` + CMake includes/link).  
   - JS/TS dependency + init snippet.

The agent and CLI together ensure consistent, minimal‑impact setup across all languages.

## Application ID Resolution

The `log-init` agent and setup suggestion generators automatically resolve the application ID using the following priority:

1. **Environment variable** (`DRTRACE_APPLICATION_ID`) - highest priority
2. **Config file** (`_drtrace/config.json` → `application_id` field)
3. **Default fallback** (`"my-app"`)

**Agent-time vs Runtime:**

- **Agent-time**: When `log-init` generates snippets, it reads `_drtrace/config.json` (if present) and uses that value as the hardcoded default in the generated code snippets.
- **Runtime**: The generated snippets use `os.environ.get("DRTRACE_APPLICATION_ID", "<value-from-config>")` pattern, so they:
  - Use the environment variable if set (allowing overrides)
  - Fall back to the config value (hardcoded at agent-time)
  - Never read `_drtrace/config.json` at runtime (production may not have it)

**Example:**

If `_drtrace/config.json` contains:
```json
{
  "application_id": "my-awesome-app",
  ...
}
```

The generated Python snippet will be:
```python
# Use DRTRACE_APPLICATION_ID if set; otherwise fall back to value from _drtrace/config.json
application_id = os.environ.get("DRTRACE_APPLICATION_ID", "my-awesome-app")
```

This means:
- After running `init-project` + `log-init`, users typically **don't need to manually set `DRTRACE_APPLICATION_ID`**
- The snippets "just work" by reusing the config value
- Environment variables can still override the config value when needed

## Integration with init-project CLI

The `init-project` CLI and `log-init` agent complement each other:

- `log-init`:
  - Reads and understands your project structure.
  - Explains **why** each integration point is chosen.
  - Provides language‑aware context and tradeoffs.

- `init-project`:
  - Automates **applying** many of those suggestions:
    - Inserts Python setup code.
    - Patches `CMakeLists.txt` for C++.
    - Updates `package.json` and entry files for JS/TS.
  - Always creates backups and reports what changed.

Recommended workflow:

1. Run `python -m drtrace_service init-project`.  
2. Let it analyze and (optionally) apply suggestions.  
3. Use `@log-init` afterwards to:
   - Validate the setup.
   - Explore alternative integration points or patterns.

## Re-running Init Commands

Both `python -m drtrace_service init-project` and `drtrace init` include **overwrite protection** to prevent accidental loss of existing configuration.

### Overwrite Protection Behavior

When you re-run an init command and `_drtrace/config.json` already exists:

1. **Warning message** is displayed:
   ```
   ⚠️  Configuration already exists at _drtrace/config.json
   ```

2. **Prompt appears** (default: No):
   ```
   Overwrite existing configuration? (y/N):
   ```

3. **If you decline (No):**
   - Initialization stops immediately
   - No changes are made
   - Your existing configuration is preserved

4. **If you confirm (Yes):**
   - Optional backup prompt appears (default: Yes):
     ```
     Create backup of existing config? (Y/n):
     ```
   - If backup is created: `config.json` is copied to `config.json.bak`
   - Initialization proceeds and overwrites the existing config

### Example Session

```bash
$ python -m drtrace_service init-project

🚀 DrTrace Project Initialization
==================================================

⚠️  Configuration already exists at _drtrace/config.json
Overwrite existing configuration? (y/N): n

❌ Initialization cancelled.
```

Or with confirmation:

```bash
$ python -m drtrace_service init-project

🚀 DrTrace Project Initialization
==================================================

⚠️  Configuration already exists at _drtrace/config.json
Overwrite existing configuration? (y/N): y
Create backup of existing config? (Y/n): y
✓ Backup created at _drtrace/config.json.bak

📋 Project Information:
...
```

### Important Notes

- **Config check happens first**: The overwrite prompt appears **before** collecting any project information, so you won't waste time answering questions if you're going to decline.
- **Default is safe**: The default answer is "No" to prevent accidental overwrites.
- **Backup is recommended**: The backup option defaults to "Yes" to help you recover if needed.
- **Applies to both**: Python (`init-project`) and JavaScript (`drtrace init`) commands behave identically.

## Troubleshooting

Common issues:

- **Daemon not running**
  - Symptom: Suggestions mention daemon URLs, but logs never arrive.
  - Fix: Start the daemon (`uvicorn drtrace_service.api:app --host localhost --port 8001` or docker-compose) and re-run tests.

- **Import errors (`drtrace_client` / `drtrace_service`)**
  - Symptom: Python snippets fail to import DrTrace modules.
  - Fix: Install the Python package (`pip install -e .` from repo root, or `pip install drtrace-service` in your project).

- **CMake changes not picked up**
  - Symptom: CMake still cannot find DrTrace library.
  - Fix: Re-run CMake configuration and build:
    - `cmake -B build -S .`  
    - `cmake --build build`

- **JS/TS dependency not installed**
  - Symptom: `Cannot find module 'drtrace'`.
  - Fix: Run the suggested install command (`npm install drtrace`, `yarn add drtrace`, or `pnpm add drtrace`) in your JS/TS project.

When in doubt, you can always:

- Run `validate_setup()` via the setup agent interface, or  
- Ask the **log-help** agent to walk you through verification steps.


