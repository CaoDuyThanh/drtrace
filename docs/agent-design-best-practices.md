# Agent Design Best Practices

**Purpose**: Design principles and best practices for creating and maintaining DrTrace agent templates.

**Audience**: Architects, developers creating or modifying agent templates.

---

## Core Principles

### 1. OpenAPI-First Discovery

**Principle**: Use OpenAPI schema discovery for daemon interaction instead of hardcoding endpoints.

**Why**:
- ✅ Future-proof: API changes don't require agent template updates
- ✅ Single source of truth: OpenAPI schema is authoritative
- ✅ Efficient: One request gets all endpoints
- ✅ Consistent: All agents use same discovery method

**Implementation**:
- Always fetch `/openapi.json` first to discover endpoints
- Fall back to core endpoints only if OpenAPI unavailable
- Reference `docs/daemon-interaction-guide.md` for patterns

**Example**:
```python
# ✅ Good: OpenAPI-first discovery
endpoints = discover_via_openapi(daemon_url)

# ❌ Bad: Hardcoding all endpoints
endpoints = {
    "/status": "GET",
    "/logs/ingest": "POST",
    # ... many more hardcoded
}
```

---

### 2. Reusable Component Pattern

**Principle**: Extract common functionality into reusable guides/components instead of duplicating in each agent template.

**Why**:
- ✅ DRY: Don't repeat logic across agents
- ✅ Maintainability: Update once, affects all agents
- ✅ Organization: Clear separation of concerns
- ✅ Consistency: All agents use same patterns

**Implementation**:
- Create reusable guides (e.g., `docs/daemon-interaction-guide.md`)
- Reference guides from agent templates
- Keep agent templates focused on agent-specific logic

**Examples**:
- **Daemon Interaction**: `docs/daemon-interaction-guide.md` (reusable by all agents)
- **Framework Detection**: Similar pattern for spdlog/ROS detection guides
- **Language-Specific Setup**: Reusable patterns for Python/C++/JS setup

**Template Pattern**:
```markdown
## Daemon Interaction

**Reference**: See `docs/daemon-interaction-guide.md` for complete guide.

**Quick Reference**:
- Discovery: Fetch `/openapi.json` first
- Fallback: Core endpoints if OpenAPI unavailable
- Status Check: `GET /status`
```

---

### 3. Agent-Driven Analysis

**Principle**: Agents should analyze projects by reading source files directly using AI understanding, not relying on external scripts or tools.

**Why**:
- ✅ Self-contained: Works regardless of installation method
- ✅ Language-independent: No need for language-specific tools
- ✅ Intelligent: AI understanding vs pattern matching
- ✅ Reliable: Doesn't depend on external dependencies

**Implementation**:
- Read project files directly (CMakeLists.txt, package.json, main.py, etc.)
- Use AI understanding to analyze structure
- Generate suggestions based on code comprehension
- Avoid relying on Python helper functions or CLI commands

**Example**:
```markdown
# ✅ Good: Agent reads files directly
1. Read CMakeLists.txt file
2. Understand CMake structure using AI
3. Generate suggestions based on comprehension

# ❌ Bad: Relying on external script
1. Call Python helper: detect_cpp_standard()
2. Parse output
3. Generate suggestions
```

---

### 4. Future-Proofing

**Principle**: Design agents to adapt to changes without requiring template updates.

**Strategies**:
1. **OpenAPI Discovery**: Use schema discovery instead of hardcoding endpoints
2. **Configuration-Driven**: Read from config files instead of hardcoding values
3. **Graceful Degradation**: Fall back to alternatives if primary method unavailable
4. **Version-Agnostic**: Don't assume specific API versions

**Example**:
```markdown
# ✅ Good: Future-proof discovery
1. Fetch OpenAPI schema
2. Discover endpoints dynamically
3. Use discovered endpoints

# ❌ Bad: Hardcoded version-specific endpoints
1. Use /v1/status (assumes v1 API)
2. Hardcode all v1 endpoints
3. Break when v2 released
```

---

### 5. Separation of Concerns

**Principle**: Separate reusable components from agent-specific logic.

**Structure**:
```
docs/
  ├── daemon-interaction-guide.md      # Reusable: Daemon API interaction
  ├── framework-detection-guide.md     # Reusable: Framework detection patterns
  └── agent-design-best-practices.md   # This file

agents/
  ├── log-init.md                      # Agent-specific: Setup assistant
  ├── log-analysis.md                  # Agent-specific: Log analysis
  ├── log-it.md                        # Agent-specific: Strategic logging
  └── log-help.md                      # Agent-specific: Help guide
```

**Benefits**:
- Clear organization
- Easy to find reusable components
- Agent templates stay focused
- Components can be updated independently

---

## Design Patterns

### Pattern 1: OpenAPI-First Discovery

**When**: Agent needs to interact with daemon API.

**Pattern**:
1. Fetch `/openapi.json` to discover endpoints
2. Parse schema to extract available endpoints
3. Use discovered endpoints for API calls
4. Fall back to core endpoints if OpenAPI unavailable

**Reference**: `docs/daemon-interaction-guide.md`

---

### Pattern 2: Reusable Guide Reference

**When**: Multiple agents need same functionality.

**Pattern**:
1. Create reusable guide in `docs/`
2. Document pattern, examples, best practices
3. Reference guide from agent templates
4. Keep agent templates concise

**Example**:
```markdown
## Framework Detection

**Reference**: See `docs/framework-detection-guide.md` for complete guide.

**Quick Reference**:
- Read source files directly
- Detect patterns using AI understanding
- Check compatibility before suggesting
```

---

### Pattern 3: Graceful Degradation

**When**: Primary method may not be available.

**Pattern**:
1. Try primary method first (e.g., OpenAPI discovery)
2. If fails, try fallback method (e.g., core endpoints)
3. If fails, provide helpful error message
4. Never fail silently

**Example**:
```python
# Try OpenAPI first
endpoints = discover_via_openapi(daemon_url)
if not endpoints:
    # Fallback to core endpoints
    endpoints = CORE_ENDPOINTS
if not endpoints:
    # Last resort: error message
    return "Daemon unavailable. Please start daemon first."
```

---

### Pattern 4: Configuration-Driven Values

**When**: Values may change or be environment-specific.

**Pattern**:
1. Read from config files (`_drtrace/config.json`)
2. Use environment variables as override
3. Provide sensible defaults
4. Document fallback order

**Example**:
```markdown
## Configuration Priority

1. Environment variable: `DRTRACE_DAEMON_URL`
2. Config file: `_drtrace/config.json` → `daemon_url`
3. Default: `http://localhost:8001`
```

---

## Anti-Patterns to Avoid

### ❌ Hardcoding Endpoints

**Problem**: Hardcoding all endpoints in agent template.

**Why Bad**:
- Breaks when API changes
- Requires template updates for every API change
- Duplicates information (OpenAPI schema is source of truth)

**Solution**: Use OpenAPI-first discovery.

---

### ❌ Duplicating Logic

**Problem**: Copying same logic into multiple agent templates.

**Why Bad**:
- Maintenance burden (update multiple places)
- Inconsistency risk
- Harder to find and fix bugs

**Solution**: Extract to reusable guide, reference from templates.

---

### ❌ Relying on External Tools

**Problem**: Requiring Python scripts, CLI commands, or language-specific tools.

**Why Bad**:
- Breaks "agents are self-contained" principle
- May not work in all installation methods
- Adds dependencies

**Solution**: Use agent-driven analysis (read files directly).

---

### ❌ Assuming Availability

**Problem**: Assuming daemon/API/tools are always available.

**Why Bad**:
- Fails ungracefully when unavailable
- Poor user experience
- No helpful error messages

**Solution**: Always check availability, provide graceful fallbacks.

---

## Checklist for New Agents

When creating a new agent template, ensure:

- [ ] **OpenAPI-First**: Uses OpenAPI discovery for daemon interaction
- [ ] **Reusable Components**: References reusable guides instead of duplicating
- [ ] **Agent-Driven**: Reads files directly, doesn't rely on external tools
- [ ] **Future-Proof**: Uses discovery/config instead of hardcoding
- [ ] **Graceful Degradation**: Handles unavailable services gracefully
- [ ] **Documentation**: References related guides and best practices
- [ ] **Separation**: Keeps agent-specific logic separate from reusable components

---

## Examples

### Good Agent Template Structure

```markdown
# Agent Name

## Daemon Interaction

**Reference**: See `docs/daemon-interaction-guide.md` for complete guide.

**Quick Reference**:
- Discovery: Fetch `/openapi.json` first
- Status Check: `GET /status`
- Fallback: Core endpoints if OpenAPI unavailable

## Agent-Specific Logic

[Agent-specific implementation here]

## Related Documentation

- `docs/daemon-interaction-guide.md` - Daemon API interaction
- `docs/agent-design-best-practices.md` - Design principles
```

### Bad Agent Template Structure

```markdown
# Agent Name

## Daemon Endpoints (Hardcoded)

- GET /status
- POST /logs/ingest
- GET /logs/query
[... many more hardcoded endpoints ...]

## Daemon Interaction Logic (Duplicated)

[Same logic copied from another agent]

## Agent-Specific Logic

[Agent-specific implementation mixed with reusable logic]
```

---

## Maintenance Guidelines

### When to Update Guides

Update reusable guides (`docs/*-guide.md`) when:
- Pattern changes affect multiple agents
- New best practices discovered
- API changes require pattern updates

### When to Update Agent Templates

Update agent templates (`agents/*.md`) when:
- Agent-specific logic changes
- Agent capabilities change
- Agent persona/behavior changes

**Don't update templates** for:
- Daemon API changes (handled by OpenAPI discovery)
- Reusable pattern changes (update guide instead)

---

## Related Documentation

- `docs/daemon-interaction-guide.md` - Daemon API interaction patterns
- `docs/overview.md` - Architecture overview
- `agents/README.md` - Agent library overview
- Agent templates (`agents/*.md`) - Implementation examples

---

## Evolution

This document should evolve as we discover new patterns and best practices. When adding new principles:

1. Document the principle clearly
2. Provide examples (good vs bad)
3. Update checklist for new agents
4. Reference from relevant agent templates

---

**Last Updated**: 2025-12-29  
**Maintained By**: DrTrace Architecture Team

