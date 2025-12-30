# DrTrace Daemon Interaction Guide

**Purpose**: Reusable guide for agents to interact with the DrTrace daemon API. This guide provides a standardized, future-proof approach to daemon discovery and interaction.

**Audience**: Agent templates (`*.md` files) that need to interact with the daemon.

---

## Core Principle: OpenAPI-First Discovery

**Always use OpenAPI schema discovery first** - this ensures agents remain compatible with API changes without requiring template updates.

### Discovery Order

1. **Primary**: Fetch `/openapi.json` to discover all available endpoints dynamically
2. **Fallback**: Use hardcoded core endpoints if OpenAPI unavailable (see "Core Endpoints" below)
3. **Last Resort**: Try common conventions (`/health`, `/status`, `/docs`)

### Why OpenAPI-First?

- ✅ **Future-proof**: API changes don't require agent template updates
- ✅ **Single source of truth**: OpenAPI schema is authoritative
- ✅ **Efficient**: One request gets all endpoints vs hardcoding many
- ✅ **Consistent**: All agents use same discovery method
- ✅ **Self-documenting**: Schema includes parameters, types, examples

---

## Discovery Pattern

### Step 1: Fetch OpenAPI Schema

```python
import requests

def discover_daemon_endpoints(base_url: str = "http://localhost:8001"):
    """Discover all available endpoints from OpenAPI schema."""
    try:
        response = requests.get(f"{base_url}/openapi.json", timeout=2)
        if response.status_code == 200:
            schema = response.json()
            endpoints = extract_endpoints(schema)
            return endpoints
    except requests.exceptions.RequestException:
        pass
    return None

def extract_endpoints(schema: dict) -> dict:
    """Extract endpoint paths and methods from OpenAPI schema."""
    endpoints = {}
    paths = schema.get("paths", {})
    for path, methods in paths.items():
        endpoints[path] = list(methods.keys())
    return endpoints
```

### Step 2: Fallback to Core Endpoints

If OpenAPI discovery fails, use these core endpoints (hardcoded fallback):

```python
CORE_ENDPOINTS = {
    "status": "GET /status",
    "ingest": "POST /logs/ingest",
    "query": "GET /logs/query",
    "docs": "GET /docs",
    "openapi": "GET /openapi.json",
}
```

### Step 3: Verify Daemon Availability

```python
def check_daemon_status(base_url: str = "http://localhost:8001") -> dict:
    """Check if daemon is running and healthy."""
    try:
        # Try OpenAPI first (most reliable)
        response = requests.get(f"{base_url}/openapi.json", timeout=2)
        if response.status_code == 200:
            return {"available": True, "method": "openapi"}
        
        # Fallback to /status endpoint
        response = requests.get(f"{base_url}/status", timeout=2)
        if response.status_code == 200:
            return {"available": True, "method": "status", "data": response.json()}
    except requests.exceptions.RequestException:
        pass
    
    return {"available": False}
```

---

## Common Endpoints (Reference)

These endpoints are commonly available, but **always verify via OpenAPI schema first**:

### Health Check

- **Endpoint**: `GET /status`
- **Purpose**: Check daemon health and configuration
- **Response**:
  ```json
  {
    "status": "healthy",
    "service_name": "drtrace_daemon",
    "version": "0.1.0",
    "host": "localhost",
    "port": 8001,
    "retention_days": 7
  }
  ```

### Log Ingestion

- **Endpoint**: `POST /logs/ingest`
- **Purpose**: Ingest a batch of log events
- **Request Body**:
  ```json
  {
    "logs": [
      {
        "ts": 1703001234.567,
        "level": "INFO",
        "message": "Log message",
        "application_id": "myapp",
        "module_name": "mymodule"
      }
    ]
  }
  ```
- **Response**: `{"accepted": 1}` (202 Accepted)

### Log Querying

- **Endpoint**: `GET /logs/query`
- **Purpose**: Query logs by time range and filters
- **Parameters**:
  - `start_ts` (float): Start timestamp (Unix epoch)
  - `end_ts` (float): End timestamp (Unix epoch)
  - `application_id` (string, optional): Filter by application
  - `module_name` (string, optional): Filter by module
  - `limit` (int, optional): Max results (default: 100, max: 1000)
- **Response**:
  ```json
  {
    "results": [...],
    "count": 10
  }
  ```

### API Documentation

- **Endpoint**: `GET /docs`
- **Purpose**: FastAPI interactive documentation (Swagger UI)
- **Note**: Useful for manual exploration, but agents should use `/openapi.json`

### OpenAPI Schema

- **Endpoint**: `GET /openapi.json`
- **Purpose**: Complete OpenAPI 3.0 schema of all endpoints
- **Note**: **Primary method for endpoint discovery**

---

## Integration Pattern for Agents

### Template Pattern

When creating agent templates that interact with the daemon, include this section:

```markdown
## Daemon Interaction

**Discovery Method**: OpenAPI-First (see `docs/daemon-interaction-guide.md`)

1. **Fetch OpenAPI Schema**: `GET {daemon_url}/openapi.json`
2. **Extract Endpoints**: Parse schema to discover available endpoints
3. **Fallback**: Use core endpoints if OpenAPI unavailable
4. **Verify**: Check daemon status before making requests

**Core Endpoints** (fallback only):
- `GET /status` - Health check
- `POST /logs/ingest` - Log ingestion
- `GET /logs/query` - Log querying
- `GET /docs` - API documentation
- `GET /openapi.json` - OpenAPI schema

**Reference**: See `docs/daemon-interaction-guide.md` for complete guide.
```

### Example: Agent Using Daemon

```python
# In agent implementation
import requests

def interact_with_daemon(action: str, **kwargs):
    """Interact with daemon using OpenAPI-first discovery."""
    base_url = kwargs.get("daemon_url", "http://localhost:8001")
    
    # Step 1: Discover endpoints via OpenAPI
    endpoints = discover_daemon_endpoints(base_url)
    if not endpoints:
        # Step 2: Fallback to core endpoints
        endpoints = CORE_ENDPOINTS
    
    # Step 3: Use discovered endpoint
    if action == "status":
        endpoint = endpoints.get("/status", "/status")
        response = requests.get(f"{base_url}{endpoint}")
        return response.json()
    
    # ... other actions
```

---

## Error Handling

### Daemon Not Available

```python
def handle_daemon_unavailable():
    """Provide helpful error message when daemon unavailable."""
    return """
    ❌ DrTrace daemon is not available.
    
    **Next Steps:**
    1. Check if daemon is running: `ps aux | grep drtrace`
    2. Start daemon: `uvicorn drtrace_service.api:app --host 0.0.0.0 --port 8001`
    3. Verify: `curl http://localhost:8001/status`
    
    **Configuration:**
    - Default URL: `http://localhost:8001`
    - Override: Set `DRTRACE_DAEMON_URL` environment variable
    """
```

### OpenAPI Schema Unavailable

If `/openapi.json` is unavailable (shouldn't happen with FastAPI, but handle gracefully):

1. Fall back to core endpoints (hardcoded)
2. Log warning for debugging
3. Continue with known endpoints

---

## Best Practices

### ✅ DO

- **Use OpenAPI-first discovery** - Always fetch `/openapi.json` first
- **Cache schema** - Store discovered endpoints for session (don't refetch every request)
- **Handle errors gracefully** - Fall back to core endpoints if discovery fails
- **Verify daemon status** - Check availability before making requests
- **Use appropriate timeouts** - Set reasonable timeouts (2-5 seconds) for daemon requests
- **Reference this guide** - Include reference to this guide in agent templates

### ❌ DON'T

- **Hardcode all endpoints** - Use OpenAPI discovery instead
- **Assume endpoint availability** - Always check daemon status first
- **Ignore errors** - Handle connection errors gracefully
- **Make blocking requests** - Use timeouts to prevent hanging
- **Duplicate endpoint lists** - Reference this guide instead of copying

---

## Future Enhancements

### Versioned Endpoints

If daemon adds versioning (e.g., `/v1/status`), OpenAPI schema will reflect this automatically. Agents using OpenAPI-first discovery will continue to work without changes.

### Authentication

If authentication is added, OpenAPI schema will include security requirements. Agents should check schema for `security` field and handle accordingly.

### Rate Limiting

If rate limiting is added, OpenAPI schema may include rate limit headers. Agents should respect `X-RateLimit-*` headers if present.

---

## Related Documentation

- `docs/api-reference.md` - Complete API reference (human-readable)
- `docs/overview.md` - Architecture overview
- Agent templates (`agents/*.md`) - Examples of daemon interaction
- `agents/daemon-method-selection.md` - Method selection guide for AI agents (HTTP-first priority)

---

**Last Updated**: 2025-12-29  
**Maintained By**: DrTrace Architecture Team

