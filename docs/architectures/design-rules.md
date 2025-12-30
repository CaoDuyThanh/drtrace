# DrTrace Architecture Design Rules

**Purpose**: Centralized design rules for consistent system architecture. All developers and agents MUST follow these rules.

**Last Updated**: 2025-12-29

---

## Table of Contents

1. [OpenAPI-First Discovery](#1-openapi-first-discovery)
2. [Agent Self-Containment](#2-agent-self-containment)
3. [Single Source of Truth](#3-single-source-of-truth)
4. [Configuration Patterns](#4-configuration-patterns)
5. [Error Handling](#5-error-handling)
6. [Multi-Language Consistency](#6-multi-language-consistency)

---

## 1. OpenAPI-First Discovery

### Rule 1.1: Dynamic Schema Discovery

**DO NOT hardcode API field names, endpoint paths, or response schemas in agent files or documentation.**

Agents MUST dynamically fetch and parse `/openapi.json` to extract:
- Endpoint paths and HTTP methods
- Request parameter names and types
- Response field names and types
- Schema definitions (e.g., `LogRecord`, `QueryResponse`)

### Rule 1.2: Schema Extraction Pattern

Before generating any API-related code, agents MUST:

```python
# Step 1: Fetch OpenAPI schema
import requests

daemon_url = "http://localhost:8001"
response = requests.get(f"{daemon_url}/openapi.json", timeout=5)
schema = response.json()

# Step 2: Extract relevant schema
log_record_schema = schema["components"]["schemas"]["LogRecord"]
fields = log_record_schema["properties"]
required_fields = log_record_schema.get("required", [])

# Step 3: Use field names from schema
# Example: timestamp field is 'ts' (from schema), NOT 'timestamp' (guess)
for field_name, field_info in fields.items():
    field_type = field_info.get("type")
    description = field_info.get("description", "")
```

### Rule 1.3: Fallback Order

When interacting with the daemon:

1. **Primary**: Fetch `/openapi.json` for endpoint and schema discovery
2. **Fallback**: Use core endpoints if OpenAPI unavailable (rare edge case)
3. **Never**: Guess field names or response structures

### Rule 1.4: Why This Matters

| Approach | API Changes | Maintenance | Consistency |
|----------|-------------|-------------|-------------|
| Hardcoded fields | Requires manual updates | High effort | Prone to drift |
| Dynamic OpenAPI | Automatic | Zero effort | Always consistent |

### Reference

- `docs/daemon-interaction-guide.md` - OpenAPI discovery implementation details
- `GET /openapi.json` - Daemon endpoint for schema

---

## 2. Agent Self-Containment

### Rule 2.1: Agents Must Work Independently

Agents MUST be self-contained and work regardless of installation method (npm, pip, etc.).

**Primary method**: File reading with AI understanding
**Fallback**: HTTP API calls (with OpenAPI discovery)
**Last resort**: CLI commands (only if explicitly needed)

### Rule 2.2: No Installation Assumptions

Agents MUST NOT assume:
- Python package is installed
- Daemon is running
- CLI commands are available

Instead, agents should:
- Check availability before using a method
- Gracefully fall back to alternatives
- Provide clear error messages with next steps

### Rule 2.3: Agent File Reading Pattern

For agents that analyze projects (like `log-init`):

```markdown
**Primary Method**: Read project files directly using AI understanding

1. Read key files (CMakeLists.txt, package.json, pyproject.toml, etc.)
2. Analyze structure using AI comprehension
3. Generate suggestions based on actual content
4. No external dependencies required
```

---

## 3. Single Source of Truth

### Rule 3.1: No Duplication

Each piece of information MUST have exactly one authoritative source:

| Information | Source of Truth | DO NOT Duplicate In |
|-------------|-----------------|---------------------|
| API field names | `/openapi.json` | Agent markdown files |
| API endpoints | `/openapi.json` | Hardcoded lists |
| Configuration schema | `_drtrace/config.json` | Multiple locations |
| Agent definitions | `agents/*.md` | Package-specific copies |

### Rule 3.2: Copy vs Reference

- **Copy**: Files that need to be distributed with packages (agents copied to package resources)
- **Reference**: Documentation that points to the source of truth

When copying is required (for distribution), use build scripts to ensure consistency.

### Rule 3.3: Version Control for Copies

When files are copied to multiple locations:
1. Define a single source location (e.g., `agents/` folder)
2. Use Makefile or build scripts to copy to package locations
3. Never manually edit package copies

---

## 4. Configuration Patterns

### Rule 4.1: Environment Variable Fallback

All configuration MUST follow this priority order:

1. Environment variable (highest priority)
2. Config file value (`_drtrace/config.json`)
3. Hardcoded default (lowest priority, ensures app never crashes)

### Rule 4.2: Configuration Code Pattern

**Python:**
```python
import os

application_id = os.environ.get(
    "DRTRACE_APPLICATION_ID",
    config.get("application_id", "my-app")  # Fallback default
)
```

**C++:**
```cpp
const char* env_app_id = std::getenv("DRTRACE_APPLICATION_ID");
config.application_id = env_app_id ? env_app_id : "value-from-config";
// Runtime will fallback to "my-app" if still empty
```

**JavaScript/TypeScript:**
```typescript
const applicationId = process.env.DRTRACE_APPLICATION_ID
    || config.applicationId
    || 'my-app';
```

### Rule 4.3: Never Fail on Missing Config

Applications MUST NOT crash due to missing configuration. Always provide sensible defaults.

---

## 5. Error Handling

### Rule 5.1: Graceful Degradation

When a preferred method fails, fall back gracefully:

```
OpenAPI fetch fails → Use core endpoints
Python import fails → Use HTTP API
HTTP API fails → Use CLI commands
All methods fail → Provide clear error message with next steps
```

### Rule 5.2: Helpful Error Messages

Error messages MUST include:

1. What failed
2. Why it might have failed
3. How to fix it
4. Next steps

**Example:**
```
❌ DrTrace daemon is not available.

**Possible causes:**
- Daemon not started
- Wrong port configured

**Next steps:**
1. Start daemon: `python -m drtrace_service`
2. Verify: `curl http://localhost:8001/status`
3. Check configuration in `_drtrace/config.json`
```

### Rule 5.3: Timeouts

All external calls MUST have timeouts:

- Health checks: 2 seconds
- API calls: 5 seconds
- Long-running operations: 30 seconds (or configurable)

---

## 6. Multi-Language Consistency

### Rule 6.1: Feature Parity

Core features MUST be available in all supported languages:

| Feature | Python | JavaScript | C++ |
|---------|--------|------------|-----|
| Log ingestion | ✅ | ✅ | ✅ |
| Configuration from file | ✅ | ✅ | ✅ |
| Environment variable override | ✅ | ✅ | ✅ |
| Daemon URL configuration | ✅ | ✅ | ✅ |

### Rule 6.2: Naming Conventions

Use consistent naming across languages:

| Concept | Python | JavaScript | C++ |
|---------|--------|------------|-----|
| Application ID | `application_id` | `applicationId` | `application_id` |
| Daemon URL | `daemon_url` | `daemonUrl` | `daemon_url` |
| Config file | `_drtrace/config.json` | `_drtrace/config.json` | `_drtrace/config.json` |

### Rule 6.3: API Response Consistency

All language clients MUST use field names from OpenAPI schema:
- `ts` (not `timestamp`)
- `level` (not `log_level`)
- `message` (not `msg`)

---

## Adding New Rules

When adding new design rules:

1. Create a new numbered section
2. Include:
   - Clear rule statement
   - Code examples where applicable
   - Rationale (why this rule exists)
   - Anti-patterns to avoid
3. Update the Table of Contents
4. Update "Last Updated" date

---

## References

- `docs/daemon-interaction-guide.md` - OpenAPI discovery guide
- `docs/api-reference.md` - API documentation
- `_bmad-output/architecture.md` - System architecture
- `AGENT-OPENAPI-ARCHITECTURE-REVIEW-2025-12-29.md` - Review that led to Rule 1

---

**Maintained by**: DrTrace Architecture Team
