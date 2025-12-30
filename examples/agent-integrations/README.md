# Agent Integration Examples

This directory contains example integrations for using DrTrace's analysis API with various agent frameworks.

> **Important:** These examples show **programmatic** integrations (Python code calling the agent interface or HTTP API).  
> For **IDE / chat side panel** usage (e.g., VS Code or Cursor right-hand chat), the host chat system will:
> - Activate a log analysis agent (defined in `agents/log-analysis.md`), and  
> - Call into the same agent interface handler (`process_agent_query(...)`) with the user's natural language query,  
> - Then render the returned markdown back to the user.  
> In other words, the chat UI is just a different host for the same agent interface shown here.

## Examples

### 1. BMAD-Style / Chat Integration (`bmad_integration.py`)

Shows how to integrate DrTrace's agent interface directly into a BMAD-style agent or IDE/chat host.

**Features:**

**Usage:**
```python
from drtrace_service.agent_interface import process_agent_query

response = await process_agent_query(
    "explain error from 9:00 to 10:00 for app myapp"
)
print(response)
```

**Run the example:**
```bash
# Ensure daemon is running
python -m drtrace_service

# In another terminal
python examples/agent-integrations/bmad_integration.py
```

### 2. LangChain Integration (`langchain_integration.py`)

Shows how to integrate DrTrace's HTTP API into a LangChain agent or tool.

**Features:**

**Prerequisites:**
```bash
pip install requests
# Optional: pip install langchain
```

**Usage:**
```python
from langchain_integration import DrTraceAnalysisTool

tool = DrTraceAnalysisTool(daemon_url="http://localhost:8001")
result = tool.analyze_why(application_id="myapp", since="10m")
print(tool.format_explanation(result))
```

**Run the example:**
```bash
# Ensure daemon is running
python -m drtrace_service

# In another terminal
python examples/agent-integrations/langchain_integration.py
```

## API Endpoints

The DrTrace daemon provides several HTTP endpoints for analysis:

### `/analysis/why`
Root-cause analysis endpoint that generates explanations for errors.

**Parameters:**

**Example:**
```bash
curl "http://localhost:8001/analysis/why?application_id=myapp&start_ts=1703000000&end_ts=1703003600&min_level=ERROR"
```

### `/analysis/time-range`
Retrieves logs for a specific time range.

**Parameters:** Same as `/analysis/why`

### `/analysis/cross-module`
Cross-module/service analysis for incidents spanning multiple components.

**Parameters:**

## Configuration

### Daemon URL

By default, examples connect to `http://localhost:8001`. To use a different host/port:

**Environment variables:**
```bash
export DRTRACE_DAEMON_HOST=localhost
export DRTRACE_DAEMON_PORT=8001
```

**Or in code:**
```python
tool = DrTraceAnalysisTool(daemon_url="http://your-host:8001")
```

## Response Format

### `/analysis/why` Response Structure

```json
{
  "data": {
    "explanation": {
      "summary": "Brief overview of the issue",
      "root_cause": "Primary cause of the error",
      "error_location": {
        "file_path": "src/module.py",
        "line_no": 42
      },
      "key_evidence": [
        "Evidence point 1",
        "Evidence point 2"
      ],
      "suggested_fixes": [
        {
          "description": "Fix description",
          "file_path": "src/module.py",
          "line_no": 42,
          "confidence": "high",
          "rationale": "Why this fix is suggested"
        }
      ],
      "confidence": "high",
      "has_clear_remediation": true,
      "evidence_references": [...]
    }
  },
  "meta": {
    "application_id": "myapp",
    "start_ts": 1703000000,
    "end_ts": 1703003600,
    "count": 5
  }
}
```

## Error Handling

All endpoints return standard HTTP status codes:

Error responses follow this format:
```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

## Next Steps

1. **Customize for your framework**: Adapt these examples to your specific agent framework
2. **Add authentication**: If your daemon requires authentication, add headers to requests
3. **Error handling**: Implement robust error handling for production use
4. **Caching**: Consider caching analysis results for frequently queried time ranges
5. **Streaming**: For large time ranges, consider implementing pagination or streaming

## Support

For more information, see:

