# Contributing to DrTrace Agents

Thank you for your interest in contributing to DrTrace agents! This guide explains how to create, test, and submit new agents or improvements.

## Creating a New Agent

### 1. File Structure

Create a new agent file named `<agent-name>.md` in this directory:

```
agents/
├── <agent-name>.md
├── log-analysis.md
├── log-it.md
├── log-init.md
├── log-help.md
└── README.md
```

### 2. File Format

Use the standardized markdown format with embedded XML:

```markdown
---
name: "<agent-name>"
description: "Brief description of the agent's purpose"
---

You must fully embody this agent's persona and follow all activation instructions exactly as specified. NEVER break character until given an exit command.

\`\`\`xml
<agent id="<agent-name>.agent.yaml" name="drtrace" title="Agent Title" icon="emoji">
<activation critical="MANDATORY">
  <step n="1">First activation step</step>
  <step n="2">Second activation step</step>
  ...
  <rules>
    <r>Behavior rule 1</r>
    <r>Behavior rule 2</r>
  </rules>
</activation>

<persona>
  <role>Agent Role</role>
  <identity>Who the agent is</identity>
  <communication_style>How the agent communicates</communication_style>
  <principles>
    - Principle 1
    - Principle 2
  </principles>
</persona>

<menu title="Menu title">
  <item cmd="X" hotkey="X" name="Option name">
    Description of what this option does
  </item>
</menu>
\`\`\`

[Implementation content - patterns, frameworks, examples, etc.]
```

### 3. Key Components

**Activation Steps** (required):
- Define how the agent initializes
- Set persona and rules
- Display greeting and menu
- Wait for user input
- Process commands

**Persona** (required):
- Role: What the agent does
- Identity: Who/what the agent is
- Communication style: Tone and format
- Principles: Core behavioral guidelines

**Menu** (optional):
- Interactive commands users can choose
- Each item has cmd, hotkey, name, description
- Focus on actionable options, not auto-execution

**Implementation**:
- Patterns, examples, frameworks
- Language-specific guidance
- Copy-paste ready code snippets
- Decision trees and validation logic

### 4. Multi-Language Support

Agents must support all five languages:
- Python (stdlib logging, structlog)
- JavaScript/TypeScript (winston, pino, bunyan)
- Java (SLF4J, Logback)
- Go (slog, logrus)
- C++ (spdlog)

For each language, provide:
- Pattern examples
- Library-specific guidance
- Syntax highlighting
- Copy-paste ready code

**Example:**
```markdown
## Python Pattern
\`\`\`python
import logging
logger = logging.getLogger(__name__)
logger.info("message")
\`\`\`

## JavaScript Pattern
\`\`\`javascript
const winston = require('winston');
const logger = winston.createLogger({...});
logger.info("message");
\`\`\`
```

## Testing Your Agent

### 1. Manual Testing

**In Python:**
```bash
cd /path/to/project
python -m drtrace_service init-agent --agent <agent-name>
cat _drtrace/agents/<agent-name>.md
```

**In JavaScript:**
```bash
cd /path/to/project
npx drtrace init-agent --agent <agent-name>
cat _drtrace/agents/<agent-name>.md
```

**In C++:**
```bash
cd /path/to/project
drtrace init-agent --agent <agent-name>
cat _drtrace/agents/<agent-name>.md
```

### 2. Activation Testing

Load the agent in your preferred AI chat or IDE:
1. Copy the entire agent file content
2. Paste into the chat interface
3. Wait for the greeting and menu
4. Verify all menu options work
5. Test core workflows

### 3. Edge Cases

Test your agent with:
- Empty input
- Malformed code
- Very large code samples
- Multiple programming languages
- Missing context (ask for clarification)
- Ambiguous requests (offer options)

### 4. Automated Testing

Agents are tested via:
- **Unit tests**: Agent spec syntax validation
- **Integration tests**: Agent loading across ecosystems
- **E2E tests**: Agent activation and menu interaction

## Updating Existing Agents

When updating an existing agent:

1. **Backward Compatibility**: Maintain the same persona and core menu items
2. **Documentation**: Update `agents/README.md` if functionality changes
3. **Testing**: Run full test suite before submitting
4. **Version Notes**: Add comment in agent file about what changed

Example:
```markdown
---
name: "log-analysis"
description: "Log Analysis Agent"
version: "1.1.0"
updated: "2025-12-22"
changelog: "Added support for cross-service log correlation"
---
```

## Submission Checklist

Before submitting your agent:

- [ ] File named `<agent-name>.md`
- [ ] YAML frontmatter with name and description
- [ ] XML activation block with 9+ steps
- [ ] Persona definition (role, identity, communication_style, principles)
- [ ] Interactive menu with 3+ options
- [ ] Examples for all 5 supported languages
- [ ] Copy-paste ready code snippets
- [ ] Tested in Python, JavaScript, C++ ecosystems
- [ ] No hardcoded file paths or system-specific code
- [ ] Error handling for edge cases
- [ ] Markdown syntax verified (no broken links)
- [ ] README.md updated (if adding new agent)

## Code Guidelines

### Do's ✅
- Use lazy string formatting (f-strings, template literals)
- Validate user input before processing
- Ask for clarification if context is unclear
- Provide helpful error messages
- Include multiple examples
- Support natural language queries
- Offer copy-paste ready code

### Don'ts ❌
- Don't hardcode system paths
- Don't assume user's environment
- Don't execute code automatically (wait for confirmation)
- Don't log sensitive data
- Don't make breaking changes to existing agents
- Don't use platform-specific syntax
- Don't skip error handling

## File Size Guidelines

Agent files should be:
- **Minimal**: 200-500 lines for simple agents
- **Comprehensive**: 800-1500 lines for complex agents
- **Maximum**: 2000 lines (split into multiple agents if larger)

Avoid:
- Excessive repetition
- Redundant examples
- Over-documentation
- Unnecessary complexity

## Directory Structure

After your contribution:

```
agents/
├── <agent-name>.md            ← Your new agent
├── log-analysis.md            ← Existing
├── log-it.md                  ← Existing
├── log-init.md                ← Existing
├── log-help.md                ← Existing
├── README.md                  ← Updated
└── CONTRIBUTING.md            ← This file
```

## Distribution Pipeline

1. **Development**: Agent file created in `agents/`
2. **Testing**: Tested across ecosystems
3. **Packaging**: Included in PyPI, npm, C++ releases
4. **Deployment**: Users get agent via `pip install drtrace`, `npm install drtrace`, etc.
5. **Activation**: Users run `drtrace init-agent --agent <name>`

## Questions?

Refer to:
- [log-analysis.md](log-analysis.md) — Complete working example
- [log-it.md](log-it.md) — Another example with 5-criteria validation
- [Agent Implementation Guide](../_bmad-output/implementation-artifacts/log-it-agent-implementation-guide.md)
- [Agent Refactoring Plan](../_bmad-output/implementation-artifacts/agent-files-shared-resource-refactoring-plan.md)

## Review Process

1. **Submit**: Create PR with new/updated agent file
2. **Review**: Architecture team reviews for:
   - Correctness and completeness
   - Multi-language support
   - Edge case handling
   - Documentation quality
3. **Feedback**: Comments provided; iterate as needed
4. **Approval**: Merged to main branch
5. **Release**: Published with next version

---

**Agent Quality Standards**
- All agents must be production-ready
- Must support all 5 programming languages
- Must include comprehensive documentation
- Must handle edge cases gracefully
- Must provide value to developers

Thank you for contributing to DrTrace! 🚀
