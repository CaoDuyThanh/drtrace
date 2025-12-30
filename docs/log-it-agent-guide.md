# Log-It Agent - Strategic Logging Assistant

## Overview

The **Log-It Agent** is an interactive AI assistant that helps you add efficient, strategic logging to your code. It validates every suggestion against a 5-criteria framework and supports Python, JavaScript/TypeScript, Java, Go, and C++.

## Key Features

- **Interactive guidance**: Analyzes functions and files to identify strategic logging points
- **5-criteria validation**: Ensures logs are efficient, necessary, privacy-safe, strategically placed, and complete
- **Multi-language support**: Provides copy-paste ready code for Python, JS, Java, Go, C++
- **Sensitive data protection**: Automatically detects and flags PII, credentials, and secrets
- **Pattern library**: Pre-built templates for common scenarios (entry/exit, external calls, errors, etc.)

## Getting Started

### Installation

The Log-It agent is included with DrTrace. Install via pip:

```bash
pip install drtrace-service
```

### Bootstrap the Agent

Initialize the agent file in your project:

```bash
# Default location: agents/log-it.md
python -m drtrace_service init-agent --agent log-it

# Custom location
python -m drtrace_service init-agent --agent log-it --path my-agents/logging.md
```

### Activation

Once the agent file exists in your project, activate it in your AI chat interface:

```
@log-it
```

Or reference the agent file directly in your conversation context.

## Usage Examples

### Example 1: Analyze a Function

**You provide:**
```python
def process_payment(order_id, amount, payment_token):
    if amount <= 0:
        return {"error": "Invalid amount"}
    result = payment_api.charge(payment_token, amount)
    if result.success:
        update_balance(order_id, amount)
        return {"success": True}
    return {"error": result.message}
```

**Agent provides:**
- 4 strategic logging points with line numbers
- Copy-paste ready Python logging code
- Warnings about `payment_token` being sensitive (suggests NOT logging it)
- Full 5-criteria validation checklist
- Log level reasoning (WARN for validation failures, INFO for success)

### Example 2: Review a File

**You provide:**
```
Review logging for my payment_service.py file
[paste full file]
```

**Agent provides:**
- Prioritized list of logging opportunities
- Identifies over-logged and under-logged areas
- Focuses on critical functions (payment processing, refunds)
- Suggests skipping verbose logging in simple helpers

### Example 3: Get Patterns

**You request:**
```
Show me Go pattern for logging external API calls
```

**Agent provides:**
```go
func CallAPI(endpoint string, payload []byte) (*Response, error) {
    start := time.Now()
    slog.Info("Calling API", "endpoint", endpoint, "bytes", len(payload))
    resp, err := http.Post(endpoint, "application/json", bytes.NewBuffer(payload))
    if err != nil {
        slog.Error("API call failed", "endpoint", endpoint, "error", err)
        return nil, err
    }
    duration := time.Since(start)
    slog.Info("API responded", "endpoint", endpoint, "status", resp.StatusCode, "took", duration)
    return resp, nil
}
```

## The 5-Criteria Framework

Every logging suggestion is validated against these criteria:

### 1. Efficiency (Performance Impact)
- ✓ Not in tight loops or high-frequency paths
- ✓ Uses lazy string formatting
- ✓ No expensive operations in log statements
- ✓ Appropriate log level

### 2. Necessity (Prevent Log Spam)
- ✓ Provides actionable insight
- ✓ Explains WHY, not just THAT
- ✓ Focuses on decision points, errors, state transitions
- ✓ Avoids logging every step of happy path

### 3. No Sensitive Information (Data Privacy)
- ✗ Never logs: passwords, tokens, keys, secrets, API keys
- ✗ Never logs: PII (user IDs, emails, SSNs, credit cards)
- ✗ Never logs: session IDs, auth headers
- ✓ Safe: status codes, processing time, function names
- ✓ When in doubt: mask, hash, or truncate

### 4. Code Context (Strategic Placement)
- ✓ Good: function entry/exit, external calls, error paths
- ✓ Good: validation failures, state transitions, decision points
- ✗ Poor: every helper function, tight loops, normal paths

### 5. Completeness (Debug-Worthy Information)
- ✓ Includes enough context for issue isolation
- ✓ Includes trace/request ID when available
- ✓ Includes relevant inputs/outputs (if not sensitive)
- ✓ Includes error/exception details

## Interactive Menu

The agent provides an interactive menu with these options:

- **[L] Log this function**: Analyze a specific function
- **[F] Log this file**: Analyze an entire file for logging gaps
- **[C] Show logging criteria**: Display the 5-criteria framework
- **[P] Show common patterns**: Get language-specific logging templates
- **[H] Help and examples**: View detailed help and real-world examples
- **[D] Dismiss Agent**: Exit the agent

## Supported Languages

The agent automatically detects your language and provides appropriate patterns:

- **Python**: stdlib `logging`, structlog
- **JavaScript/TypeScript**: winston, pino, bunyan
- **Java**: SLF4J, Logback
- **Go**: slog, logrus
- **C++**: spdlog

## Common Patterns

The agent includes pre-built patterns for these scenarios:

1. **Function entry/exit logging**: Track significant operations
2. **Validation failure logging**: Log why inputs were rejected
3. **External service call logging**: Track API/database interactions
4. **Decision point logging**: Log important if/else branches
5. **State transition logging**: Track status changes
6. **Error handling logging**: Capture exceptions with context

## Sensitive Data Protection

The agent automatically flags these patterns (case-insensitive):

**Authentication & Authorization:**
- `password`, `token`, `auth`, `bearer`, `jwt`, `api_key`
- `secret`, `private_key`, `session_id`, `cookie`

**Personal Information:**
- `user_id`, `email`, `phone`, `address`, `ssn`
- `credit_card`, `card_number`, `cvv`

**When detected, the agent:**
1. ⚠️ Flags the variable with a clear warning
2. Suggests masking techniques (hash, truncate, redact)
3. Provides rewritten safe version
4. Marks "No Sensitive Data" criterion as ⚠️ or ❌

## Best Practices

### DO:
- ✅ Log at function entry for public APIs and long-running operations
- ✅ Log external calls (APIs, databases, file I/O) with timing
- ✅ Log validation failures with reasons
- ✅ Log error paths with exception details
- ✅ Include trace/request IDs for correlation
- ✅ Use DEBUG for detailed step-by-step info
- ✅ Use INFO for significant milestones
- ✅ Use WARN for recoverable issues
- ✅ Use ERROR for exceptions and failures

### DON'T:
- ❌ Log inside tight loops (unless ERROR/milestone)
- ❌ Log every helper function call
- ❌ Log every step of the happy path
- ❌ Log sensitive data (passwords, tokens, PII)
- ❌ Log complete request/response bodies
- ❌ Use eager string concatenation (use f-strings)
- ❌ Perform expensive operations in log statements

## Example Response Format

When you request logging analysis, the agent provides:

```markdown
# Logging Analysis for [Function/File Name]

## Strategic Logging Points

### Point 1: [Location and Purpose]
- **Line**: [line number]
- **Log Level**: [DEBUG/INFO/WARN/ERROR]
- **Purpose**: [Why this log is needed]

**Suggested Code:**
\`\`\`python
logger.info(f"Processing payment: order={order_id}, amount={amount}")
\`\`\`

## Logging Criteria Validation

- **Efficiency**: ✅ [explanation]
- **Necessity**: ✅ [explanation]
- **No Sensitive Data**: ✅ or ⚠️ [explanation]
- **Code Context**: ✅ [explanation]
- **Completeness**: ✅ [explanation]

## Implementation Notes

[Additional guidance or warnings]
```

## Tips for Best Results

1. **Provide complete context**: Include the full function or relevant file sections
2. **Mention constraints**: Tell the agent about high-frequency paths or performance concerns
3. **Ask specific questions**: "Should I log every retry?" or "Is this too verbose?"
4. **Request language-specific help**: "Show me TypeScript async logging pattern"
5. **Clarify use cases**: "This is a background job" or "This handles user authentication"

## Integration with DrTrace

The Log-It agent is designed to work seamlessly with DrTrace's logging infrastructure:

- Suggests appropriate log levels for DrTrace ingestion
- Recommends structured logging formats
- Aligns with DrTrace's analysis capabilities
- Works across all DrTrace-supported languages

## Troubleshooting

**Agent file not found:**
```bash
python -m drtrace_service init-agent --agent log-it
```

**Wrong language patterns:**
Tell the agent your language: "This is Java code" or paste code with clear language hints.

**Need custom patterns:**
Ask the agent: "Show me a custom pattern for [your scenario]"

**Disagreement with suggestions:**
Discuss with the agent! It can explain reasoning and adjust recommendations.

## Further Reading

- [DrTrace Overview](overview.md)
- [Log Schema](log-schema.md)
- [Cross-Language Querying](cross-language-querying.md)
- [API Reference](api-reference.md)

## Contributing

Found a pattern that should be added? Have suggestions for improvement? Open an issue or PR in the DrTrace repository.

## License

Part of DrTrace, licensed under [insert license].
