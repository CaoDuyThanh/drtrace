# Interactive Project Initialization (DrTrace init-project)

## Overview

The `DrTrace init-project` command provides an interactive workflow to initialize a new DrTrace project with complete configuration, templates, and environment setup. This command creates the `_drtrace/` folder structure with all necessary files to get started with DrTrace logging integration.

In addition to basic configuration, `init-project` can now **analyze your project and suggest concrete DrTrace setup changes** (Python, C++, JavaScript/TypeScript), and optionally apply them with backups.
## Quick Start

```bash
python -m drtrace_service init-project
```

The command walks through interactive prompts to configure your project, then generates:
- Main configuration file (`config.json`)
- Environment-specific config overrides
- Environment variable template (`.env.example`)
- Configuration guide (`README.md`)
- Optional: Default agent specifications (log-analysis, log-it, log-init, log-help)

## Command Usage

### Basic Command

```bash
python -m drtrace_service init-project
```

### With Custom Project Root

```bash
python -m drtrace_service init-project --project-root /path/to/project
```

## Interactive Prompts

The initialization workflow includes the following prompts:

### 1. Project Information

**Project name** (default: "my-app")
- The human-readable name of your project

**Application ID** (default: derived from project name)
- Unique identifier for your application
- Used for log routing and filtering

### 2. Technology Stack

**Language/Runtime selection**
- `python` - Python applications
- `javascript` - JavaScript/Node.js applications  
- `cpp` - C++ applications
- `both` - Polyglot projects with multiple languages

### 3. DrTrace Daemon Configuration

**Daemon URL** (default: "http://localhost:8001")
- HTTP endpoint where the DrTrace daemon listens
- For production, use your deployment's daemon URL

**Enable DrTrace by default?** (default: yes)
- Controls whether logging is active when your application starts
- Can be overridden with `DRTRACE_ENABLED` environment variable

### 4. Environments

**Which environments to configure?**
- Select one or more of: `development`, `staging`, `production`, `ci`
- Generates per-environment config files for flexible deployment

### 5. Agent Integration (Optional)

**Enable agent interface?** (default: no)
- Whether to set up the log analysis agent subsystem

**Agent framework** (if enabled)
- `bmad` - Default framework (recommended)
- `langchain` - LangChain integration
- `other` - Custom framework

### 6. Optional Setup Suggestions

After the core configuration and files are generated, `init-project` will offer:

- **Analyze project and suggest setup?** (default: **Yes**)  
  - Uses `drtrace_service.setup_agent_interface.analyze_and_suggest()` to inspect your project (Python, C++, JS/TS).
  - Prints human-readable suggestions including:
    - Detected languages
    - Recommended integration points
    - Copy‑pasteable code snippets with language fences (```python, ```cmake, ```typescript, ```javascript).

- **Apply suggested setup changes?** (default: **No**)  
  - If you answer **Yes**, the CLI will:
    - For **Python**:
      - Insert a `setup_logging()` integration snippet into the suggested entry file (e.g., `main.py`), after imports.
      - Update or create `.env`, `.env.example`, `requirements.txt`, or `pyproject.toml` with DrTrace configuration.
    - For **C++**:
      - Insert a `FetchContent` block for the DrTrace C++ client into `CMakeLists.txt` (if present), without touching your targets.
    - For **JavaScript/TypeScript**:
      - Add a `drtrace` dependency to `package.json` (if found).
      - Append an initialization snippet to detected entry points (e.g., `main.ts`, `index.js`).

Every modification is **preceded by a timestamped backup** so you can easily diff and revert if needed.

## Generated Files

### _drtrace/config.json
Main configuration file with project metadata and settings:

```json
{
  "project_name": "my-app",
  "application_id": "my-app-123",
  "language": "python",
  "daemon_url": "http://localhost:8001",
  "enabled": true,
  "environments": ["development", "staging", "production"],
  "agent": {
    "enabled": false,
    "framework": "bmad"
  },
  "created_at": "2025-01-15T10:30:45.123456+00:00"
}
```

### _drtrace/config.{environment}.json
Environment-specific overrides (e.g., `config.production.json`):

```json
{
  "project_name": "my-app",
  "application_id": "my-app-123",
  "language": "python",
  "daemon_url": "http://prod-daemon.internal:8001",
  "enabled": true,
  "environments": ["production"],
  "agent": {
    "enabled": true,
    "framework": "bmad"
  }
}
```

### _drtrace/.env.example
Template for environment variables:

```bash
# Basic Configuration
DRTRACE_APPLICATION_ID=my-app-123
DRTRACE_DAEMON_URL=http://localhost:8001
DRTRACE_ENABLED=true

# Environment-specific overrides
# DRTRACE_DAEMON_HOST=localhost
# DRTRACE_DAEMON_PORT=8001
# DRTRACE_RETENTION_DAYS=7

# Agent configuration
# DRTRACE_AGENT_ENABLED=false
# DRTRACE_AGENT_FRAMEWORK=bmad
```

### _drtrace/README.md
Configuration guide with quick reference and setup instructions.

### _drtrace/agents/ (Optional)
Default agent specifications if agent integration is enabled:
- `log-analysis.md` - Log analysis agent for querying and analyzing logs
- `log-it.md` - Strategic logging assistant for adding effective logging
- `log-init.md` - Setup assistant for DrTrace integration
- `log-help.md` - Step-by-step setup guide with progress tracking

## Configuration Schema

The generated configuration follows this schema:

| Field | Type | Required | Description | Default |
|-------|------|----------|-------------|---------|
| `project_name` | string | Yes | Human-readable project name | — |
| `application_id` | string | Yes | Unique application identifier | — |
| `language` | string | No | Target language/runtime | `"python"` |
| `daemon_url` | string | No | DrTrace daemon HTTP URL | `"http://localhost:8001"` |
| `enabled` | boolean | No | Enable DrTrace by default | `true` |
| `environments` | array | No | List of environments to configure | `["development"]` |
| `agent.enabled` | boolean | No | Enable agent interface | `false` |
| `agent.framework` | string | No | Agent framework choice | `"bmad"` |
| `created_at` | string | No | ISO 8601 creation timestamp | Auto-generated |

## Usage Examples

### Example 1: Basic Python Project

```bash
$ python -m drtrace_service init-project

🚀 DrTrace Project Initialization
==================================================

📋 Project Information:
Project name [my-app]: my-web-api
Application ID [my-web-api]: my-web-api-prod

🔧 Technology Stack:
Select language/runtime:
  1. python
  2. javascript
  3. cpp
  4. both
Select option: 1

📡 DrTrace Daemon Configuration:
Daemon URL [http://localhost:8001]: http://localhost:8001
Enable DrTrace by default? (Y/n): y

🌍 Environments:
Which environments to configure?
(Enter numbers separated by commas, e.g., '1,3')
  1. development
  2. staging
  3. production
  4. ci
Select options: 1,3

🤖 Agent Integration (Optional):
Enable agent interface? (y/N): n

==================================================
✅ Project Initialization Complete!

📍 Configuration Location: ./_drtrace

📋 Generated Files:
   • ./_drtrace/config.json
   • ./_drtrace/config.development.json
   • ./_drtrace/config.production.json
   • ./_drtrace/.env.example
   • ./_drtrace/README.md

📖 Next Steps:
   1. Review ./_drtrace/config.json
   2. Create .env: cp ./_drtrace/.env.example .env
   3. Start the daemon:
      Option A (Docker - Recommended): docker-compose up -d
      Option B (Native): uvicorn drtrace_service.api:app --host localhost --port 8001
   4. Read ./_drtrace/README.md for more details

==================================================
```

### Example 2: Full-Featured Project with Agent

```bash
$ python -m drtrace_service init-project

[Interactive prompts...]

🔧 Technology Stack:
Select language/runtime:
  1. python
  2. javascript
  3. cpp
  4. both
Select option: 4

🌍 Environments:
Select options: 1,2,3,4

🤖 Agent Integration (Optional):
Enable agent interface? (y/N): y
Select agent framework:
  1. bmad
  2. langchain
  3. other
Select option: 1

==================================================
✅ Project Initialization Complete!

📍 Configuration Location: ./_drtrace

📋 Generated Files:
   • ./_drtrace/config.json
   • ./_drtrace/config.development.json
   • ./_drtrace/config.staging.json
   • ./_drtrace/config.production.json
   • ./_drtrace/config.ci.json
   • ./_drtrace/.env.example
   • ./_drtrace/README.md
   • ./_drtrace/agents/log-analysis.md
   • ./_drtrace/agents/log-it.md
   • ./_drtrace/agents/log-init.md
   • ./_drtrace/agents/log-help.md

==================================================
```

### Example 3: Using Setup Suggestions

```bash
$ python -m drtrace_service init-project

🚀 DrTrace Project Initialization
==================================================

📋 Project Information:
Project name [my-app]:
Application ID [my-app]:

🔧 Technology Stack:
Select language/runtime:
  1. python
  2. javascript
  3. cpp
  4. both
Select option: 4

📡 DrTrace Daemon Configuration:
Daemon URL [http://localhost:8001]:
Enable DrTrace by default? (Y/n):

🌍 Environments:
Which environments to configure?
(Enter numbers separated by commas, e.g., '1,3')
  1. development
  2. staging
  3. production
  4. ci
Select options: 1,3

🤖 Agent Integration (Optional):
Enable agent interface? (y/N):

==================================================
🧩 Setup Suggestions

# Setup Suggestions for Python
...

==================================================

Apply suggested setup changes? (y/N): y

   • Backup created: main.py.backup.20250101010101
   • Inserted Python setup code into main.py at line 12
   • Added drtrace to requirements.txt
   • Backup created: CMakeLists.txt.backup.20250101010101
   • Inserted CMake FetchContent block into CMakeLists.txt
   • Backup created: package.json.backup.20250101010101
   • Added drtrace dependency to package.json
   • Appended JS/TS initialization snippet to src/main.ts

🔍 Verifying applied setup suggestions...
   • ✅ Python setup present in main.py
   • ✅ CMake FetchContent for drtrace present in CMakeLists.txt
   • ✅ drtrace dependency present in package.json

==================================================
✅ Project Initialization Complete!
...
```

## Environment Configuration

### Basic Environment Variables

Create `.env` from the template:

```bash
cp _drtrace/.env.example .env
```

Common variables:
- `DRTRACE_APPLICATION_ID` - Your application identifier
- `DRTRACE_DAEMON_URL` - Daemon endpoint
- `DRTRACE_ENABLED` - Enable/disable DrTrace globally
- `DRTRACE_RETENTION_DAYS` - Log retention period

### Loading Configuration

Python:
```python
from pathlib import Path
from drtrace_service.cli.config_schema import ConfigSchema

# Load main config
config = ConfigSchema.load(Path("_drtrace/config.json"))

# Load environment-specific overrides
env_config = ConfigSchema.load(Path("_drtrace/config.production.json"))
```

### Per-Environment Setup

1. **Development** (`config.development.json`)
   - Local daemon instance
   - Debug logging enabled
   - Short retention (1-7 days)

2. **Staging** (`config.staging.json`)
   - Staging daemon URL
   - Production-like configuration
   - Medium retention (7-30 days)

3. **Production** (`config.production.json`)
   - Production daemon URL
   - Critical issues only
   - Long retention (30-90 days)

4. **CI** (`config.ci.json`)
   - Ephemeral daemon instance
   - Test-specific settings
   - Short retention (1 day)

## Handling Existing Configuration

If `_drtrace/config.json` already exists:

1. You'll be prompted: "Overwrite existing configuration?"
2. If yes, choose whether to create a backup (`config.json.bak-<timestamp>`)
3. New files will be created in the `_drtrace/` directory

## Next Steps After Initialization

1. **Review Configuration**
   ```bash
   cat _drtrace/config.json
   ```

2. **Create Environment File**
   ```bash
   cp _drtrace/.env.example .env
   # Edit .env with your environment-specific values
   ```

3. **Start the Daemon**
   ```bash
   python -m drtrace_service status    # Check if daemon is running
   ```

4. **Integrate with Your Code**
   
   Python:
   ```python
   from drtrace_client import setup_logging, ClientConfig
   
   config = ClientConfig(
       application_id="my-app-prod",
       enabled=True
   )
   setup_logging(config)
   ```
   
   JavaScript:
   ```javascript
   import { DrTraceClient } from 'drtrace';
   
   const client = new DrTraceClient({
       applicationId: 'my-app-prod',
       daemonUrl: 'http://localhost:8001'
   });
   ```

5. **Test the Integration**
   ```bash
   python your_app.py        # Your app with DrTrace logging
   ```

## Troubleshooting

### Command Not Found

```bash
# Make sure drtrace_service is in PYTHONPATH
export PYTHONPATH=packages/python/src:$PYTHONPATH
python -m drtrace_service init-project
```

### Cannot Write to Directory

Ensure write permissions in the project directory:
```bash
chmod u+w .
```

### Configuration Validation Errors

Check that:
- `project_name` and `application_id` are non-empty strings
- Selected environments are valid: `development`, `staging`, `production`, `ci`
- `daemon_url` is a valid HTTP URL

## Advanced: Manual Configuration

If you prefer to configure manually without the interactive prompt:

1. Create `_drtrace/` directory:
   ```bash
   mkdir -p _drtrace/agents
   ```

2. Create `config.json`:
   ```json
   {
     "project_name": "my-app",
     "application_id": "my-app-id",
     "language": "python",
     "daemon_url": "http://localhost:8001",
     "enabled": true,
     "environments": ["development"]
   }
   ```

3. Copy the agent spec (optional):
   ```bash
   python -m drtrace_service init-agent --path _drtrace/agents/log-analysis.md
   ```

## See Also

- [Configuration Guide](../docs/quickstart.md)
- [Agent Integration](../docs/agent-integration.md)
- [Environment Variables Reference](../docs/api-reference.md#environment-variables)
