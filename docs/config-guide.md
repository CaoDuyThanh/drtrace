# DrTrace Configuration Guide

This guide explains the DrTrace configuration system, file structure, loading priority, and environment variable overrides for both Python and JavaScript/TypeScript clients.

## Overview

DrTrace uses a project-local `_drtrace/` folder to store configuration, environment overrides, and agent specifications.

```
_drtrace/
├── config.json
├── config.development.json
├── config.production.json
├── config.staging.json
├── config.ci.json
├── agents/
│   └── log-analysis.md
├── .env.example
└── README.md
```

## Loading Priority

From highest to lowest:
- Environment variables (prefixed with `DRTRACE_`)
- `_drtrace/config.json` (base project configuration)
- `_drtrace/config.{ENV}.json` (environment-specific overrides)
- Defaults (built into the client)

Supported environment detection:
- `NODE_ENV` (JavaScript/Node)
- `PYTHON_ENV` (Python)

## Schema

Top-level sections:
- `project`: name, language, description
- `drtrace`: applicationId, daemonUrl, enabled, logLevel, batchSize, flushIntervalMs, retentionDays
- `agent`: enabled, agentFile, framework (bmad|langchain|other)
- `environment`: nested overrides per environment (e.g., development, production)

Example `config.json`:
```json
{
  "project": {
    "name": "my-application",
    "language": "typescript",
    "description": "My Node.js/TypeScript application"
  },
  "drtrace": {
    "applicationId": "my-app",
    "daemonUrl": "http://localhost:8001",
    "enabled": true,
    "logLevel": "info",
    "batchSize": 50,
    "flushIntervalMs": 1000,
    "retentionDays": 7
  },
  "agent": {
    "enabled": true,
    "agentFile": "./_drtrace/agents/log-analysis.md",
    "framework": "bmad"
  },
  "environment": {
    "development": {
      "enabled": true,
      "daemonUrl": "http://localhost:8001"
    },
    "production": {
      "enabled": false,
      "daemonUrl": "https://drtrace-api.example.com"
    }
  }
}
```

## Environment Variables

Environment variables override file configuration. Common variables:
- `DRTRACE_APPLICATION_ID` → `drtrace.applicationId`
- `DRTRACE_DAEMON_URL` → `drtrace.daemonUrl`
- `DRTRACE_ENABLED` → `drtrace.enabled` (true/false/1/0/yes/no)
- `DRTRACE_LOG_LEVEL` → `drtrace.logLevel` (debug/info/warn/error)
- `DRTRACE_BATCH_SIZE` → `drtrace.batchSize` (integer)
- `DRTRACE_FLUSH_INTERVAL_MS` → `drtrace.flushIntervalMs` (integer)
- `DRTRACE_RETENTION_DAYS` → `drtrace.retentionDays` (integer)
- `DRTRACE_AGENT_ENABLED` → `agent.enabled`
- `DRTRACE_AGENT_FILE` → `agent.agentFile`
- `DRTRACE_AGENT_FRAMEWORK` → `agent.framework` (bmad/langchain/other)

## Sensitive Data Handling

- `_drtrace/.env.example` provides a template for environment variables.
- Do not commit real `.env` files. They are ignored by git via `.gitignore`.
- Recommended: `cp _drtrace/.env.example .env` and populate secrets locally or via CI secrets.

## Python Loader

- Module: [src/drtrace_service/config_loader.py](src/drtrace_service/config_loader.py)
- Function: `load_config(project_root='.', environment=None)`
- Behavior: loads base config, merges environment overrides, applies env vars, validates.

## JavaScript/TypeScript Loader

- Module: [packages/javascript/drtrace-client/src/config.ts](packages/javascript/drtrace-client/src/config.ts)
- Function: `loadConfig({ projectRoot: '.', environment })`
- Behavior: same as Python; uses `process.env` for environment variables.

## Common Configurations

- Development: enable DrTrace and point to local daemon
- Production: disable DrTrace by default, use HTTPS daemon URL
- CI: disable DrTrace, minimal logging, short retention

## Troubleshooting

- Invalid JSON: the loaders will throw clear errors indicating the file and parse issue.
- Invalid types or values: loaders validate enums and types, providing specific messages.
- Missing sections: defaults are applied when sections are missing.

## Next Steps

- Use `drtrace init` or `npx drtrace init` to generate `_drtrace/` scaffolding.
- Customize `_drtrace/config.json` and per-environment files.
- Set environment variables via `.env`, system env, or CI secrets.
