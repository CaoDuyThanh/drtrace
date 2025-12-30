# DrTrace Agent Library

Central repository for all DrTrace interactive agents. These agents guide developers through code analysis, logging decisions, and troubleshooting workflows.

## Agents

### log-analysis (Log Analysis Specialist)
Analyzes application logs and provides root-cause explanations for errors.

- **Purpose**: Help developers understand why errors occurred with AI-powered analysis
- **Input**: Natural language queries about log data and time windows
- **Output**: Structured markdown reports with summaries, root causes, evidence, and suggested fixes
- **Availability**: All ecosystems (Python, JavaScript, C++)

**Activate:**
```bash
# Python
python -m drtrace_service init-agent --agent log-analysis

# JavaScript
npx drtrace init-agent --agent log-analysis

# C++
drtrace init-agent --agent log-analysis
```

### log-it (Strategic Logging Assistant)
Helps developers add efficient, strategic logging to their code.

- **Purpose**: Guide developers through logging decisions using 5-criteria validation
- **Input**: Function or file code to analyze
- **Output**: Strategic logging suggestions with line numbers, log levels, and copy-paste ready code
- **Availability**: All ecosystems (Python, JavaScript, Java, Go, C++)

**Activate:**
```bash
# Python
python -m drtrace_service init-agent --agent log-it

# JavaScript
npx drtrace init-agent --agent log-it

# C++
drtrace init-agent --agent log-it
```

### log-init (DrTrace Setup Assistant)
Analyzes your project structure and suggests language-specific DrTrace setup.

- **Purpose**: Inspect real project files (Python, C++, JS/TS) and recommend minimal, best‑practice integration points.
- **Input**: Project root path and/or key files (e.g., `main.py`, `CMakeLists.txt`, `package.json`).
- **Output**: Markdown suggestions with integration points, code snippets, config changes, and verification steps.

**Activate:**

```bash
# Python
python -m drtrace_service init-agent --agent log-init

# JavaScript
npx drtrace init-agent --agent log-init

# C++
drtrace init-agent --agent log-init
```

See `docs/log-init-agent-guide.md` for detailed usage, examples, and how it works with `init-project`.

### log-help (DrTrace Setup Guide)
Provides interactive, step-by-step guidance and troubleshooting for DrTrace setup.

- **Purpose**: Walk you through setup steps for each language and help debug common issues.
- **Input**: Natural language requests (e.g., “start Python setup guide”, “I’m stuck – daemon not connecting”).
- **Output**: Guided checklists, progress tracking, and troubleshooting instructions.

**Activate:**

```bash
# Python
python -m drtrace_service init-agent --agent log-help

# JavaScript
npx drtrace init-agent --agent log-help

# C++
drtrace init-agent --agent log-help
```

See `docs/log-help-agent-guide.md` for guidance on step-by-step usage and troubleshooting patterns.

## Usage

1. **Bootstrap an agent into your project:**
   ```bash
   drtrace init-agent --agent <agent-name>
   ```
   This creates `_drtrace/agents/<agent-name>.md` in your project.

2. **Activate an agent in your chat/IDE:**
   - Load the agent file from `_drtrace/agents/<agent-name>.md`
   - Or use `@agent-name` shorthand if supported by your host

3. **Interact with the agent:**
   - Follow the agent's menu options
   - Provide code or query details as requested
   - Use the agent's structured responses for your work

## Supported Languages

All agents support analysis and suggestions for:
- **Python** (stdlib logging, structlog)
- **JavaScript/TypeScript** (winston, pino, bunyan)
- **Java** (SLF4J, Logback)
- **Go** (slog, logrus)
- **C++** (spdlog)

## File Format

Agents use a standardized markdown format with embedded XML configuration:

```
---
name: "agent-name"
description: "Agent description"
---

[XML activation instructions and persona definition]

[Agent implementation content]
```

Key sections:
- `<agent>` tag: Identifies the agent and its capabilities
- `<activation>`: Step-by-step instructions for activation
- `<rules>`: Behavioral guidelines
- `<persona>`: Role definition and communication style
- `<menu>`: Interactive menu items (optional)

See [log-analysis.md](log-analysis.md) or [log-it.md](log-it.md) for complete examples.

## Distribution

Agents are distributed with each ecosystem:

- **Python**: Packaged in `drtrace_service.resources.agents` via pip
- **JavaScript**: Copied to `node_modules/drtrace/agents/` via npm
- **C++**: Installed alongside library via package manager

When you run `drtrace init-agent`, the agent spec is copied from the installed package location to your local project at `_drtrace/agents/`.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Creating new agents
- Testing agents across ecosystems
- Updating existing agents
- Documentation requirements

## Maintenance

- **Version sync**: Agent files are versioned with each DrTrace release
- **Updates**: Agents are updated in main branch; new versions published with releases
- **Compatibility**: All agents must work across Python, JavaScript, and C++ ecosystems

## References

- [Agent Implementation Guide](../_bmad-output/implementation-artifacts/log-it-agent-implementation-guide.md)
- [Agent Refactoring Plan](../_bmad-output/implementation-artifacts/agent-files-shared-resource-refactoring-plan.md)
- [DrTrace Documentation](../docs/overview.md)

---

**Last Updated**: December 29, 2025  
**Maintainer**: DrTrace Architecture Team
