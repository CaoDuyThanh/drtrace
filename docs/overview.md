# DrTrace - Overview

**Version:** 0.1.0 (POC)  
**Last Updated:** 2025-12-19

## What is DrTrace?

DrTrace is a developer tool that transforms time-consuming log investigation into instant, intelligent explanations. It combines structured logging with AI analysis and source code context to provide root-cause explanations for errors, accessible through natural language queries or agent systems.

### The Problem

Developers spend significant time manually sifting through logs to understand why errors occurred:

- **Time-Consuming Debugging**: Manual log analysis is slow and inefficient (30-60 minutes per debugging session)
- **Context Fragmentation**: Logs and source code are disconnected, requiring manual correlation
- **Multi-Module Complexity**: Investigating issues across multiple modules/services requires switching between different log formats and tools
- **Limited Intelligence**: Current logging systems don't provide explanations or root cause analysis
- **Agent Integration Gap**: AI agents can't easily access and analyze logs for debugging assistance

### The Solution

DrTrace provides:

- **Instant Contextual Analysis**: Combines logs with source code in a single AI-powered analysis
- **Natural Language Queries**: Ask "why did this error happen?" in plain English
- **Multi-Language Support**: Unified interface for logs across Python, C++, and other languages
- **Agent Integration**: Works with any agent system (BMAD, LangChain, etc.)
- **Zero Performance Impact**: Async, non-blocking log collection with <1% CPU overhead

## Core Concepts

### 1. Structured Log Collection

DrTrace captures structured log events from your application with enriched context:

- **Standard Fields**: timestamp, level, message, application_id, module_name, service_name
- **Error Context**: file_path, line_no, exception_type, stacktrace
- **Flexible Context**: Additional metadata stored as JSON

Logs are collected asynchronously and batched for efficient delivery to the local daemon.

### 2. Time-Series Storage

Logs are stored in a time-series database (PostgreSQL) optimized for time-range queries:

- Efficient queries by time range, application, module, service, or log level
- Automatic retention policies (configurable, default 7 days)
- Support for clearing logs by application or environment

### 3. Source Code Context Retrieval

When analyzing errors, DrTrace automatically retrieves relevant source code:

- Resolves file paths from log metadata
- Extracts code snippets around error locations
- Searches for additional relevant code locations
- Handles missing or inaccessible files gracefully

### 4. AI-Powered Analysis

DrTrace combines logs and code context to generate intelligent explanations:

- **Root Cause Analysis**: Identifies why errors occurred
- **Evidence Highlighting**: Points to specific logs and code locations
- **Suggested Fixes**: Provides actionable remediation steps with file/line references
- **Confidence Levels**: Indicates reliability of explanations

### 5. Agent Integration

DrTrace provides multiple interfaces for agent systems:

- **Natural Language Interface**: Process queries like "explain error from 9:00 to 10:00"
- **HTTP API**: RESTful endpoints for programmatic access
- **CLI Commands**: Command-line tools for interactive use
- **Framework Examples**: Integration snippets for BMAD, LangChain, and others

## High-Level Architecture

```
┌─────────────────┐
│  Your App       │
│  (Python/C++)   │
│                 │
│  ┌───────────┐  │
│  │ DrTrace   │  │
│  │ Client    │  │──┐
│  └───────────┘  │  │ Async
└─────────────────┘  │ Batched
                     │ HTTP
┌─────────────────┐  │
│  DrTrace Daemon │◄─┘
│                 │
│  ┌───────────┐  │
│  │ Ingestion │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ Storage   │  │
│  │ (Postgres)│  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ Analysis  │  │
│  │ + AI      │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ Code      │  │
│  │ Context   │  │
│  └───────────┘  │
└─────────────────┘
        │
        │ HTTP/CLI
        ▼
┌─────────────────┐
│  Agent Systems  │
│  (BMAD, etc.)   │
└─────────────────┘
```

### Key Components

1. **Client SDK** (`drtrace_client`): Python package that integrates with standard `logging` module
2. **Daemon** (`drtrace_service`): Local service that ingests, stores, and analyzes logs
3. **Storage Layer**: PostgreSQL-based time-series storage with retention policies
4. **Analysis Engine**: Combines logs and code context for AI-powered explanations
5. **API Layer**: HTTP endpoints and CLI commands for querying and analysis
6. **Agent Interface**: Natural language processing and framework integrations

## POC Scope

### What's Included

✅ **Core Features:**
- Python client SDK with standard logging integration
- C++ client integration using spdlog
- Local daemon with HTTP API
- Time-series log storage (PostgreSQL)
- Source code context retrieval
- AI-powered root cause analysis
- Natural language query processing
- CLI commands for analysis
- Agent integration examples (BMAD, LangChain)
- Saved and templated analysis queries

✅ **Multi-Language Support:**
- Python (full support)
- C++ (spdlog integration)
- Unified schema for cross-language querying

✅ **Analysis Capabilities:**
- Time-range analysis for single applications
- Cross-module/service incident analysis
- Root cause explanations with evidence
- Suggested fixes with code locations
- Confidence scoring

### What's Not Included (Future Work)

❌ **Production Features:**
- Multi-tenant support
- Distributed deployment
- High availability / failover
- Authentication / authorization
- Rate limiting
- Advanced security features

❌ **Additional Languages:**
- JavaScript/TypeScript client
- Rust client
- Other language integrations

❌ **Advanced Features:**
- Real-time dashboards
- Distributed tracing
- Alerting and notifications
- Advanced visualization
- Enterprise features

### Limitations

**Performance:**
- Designed for local, single-developer use
- Handles up to ~1K logs/second (not optimized for higher throughput)
- Analysis typically completes in <30 seconds

**Scale:**
- Single daemon instance (no clustering)
- Local database (no distributed storage)
- Designed for development environments, not production workloads

**AI Model:**
- Uses configurable AI model abstraction (default: stub for testing)
- Production use requires integration with actual AI provider
- Analysis quality depends on model capabilities

**Security:**
- No authentication/authorization (local POC)
- No encryption at rest or in transit
- Not designed for sensitive data or production security requirements

## Primary User Journeys

### Journey 1: Quick Error Investigation

1. **Integrate DrTrace** into your Python application (2-3 lines of code)
2. **Run your application** - logs are automatically captured
3. **Encounter an error** - error context is captured with file/line info
4. **Ask "why"** - Use CLI: `python -m drtrace_service why --app myapp --since 10m`
5. **Get explanation** - Receive root cause, evidence, and suggested fixes

### Journey 2: Agent-Powered Analysis

1. **Activate DrTrace agent** in your agent system (BMAD, LangChain, etc.)
2. **Ask natural language query**: "explain error from 9:00 to 10:00 for app myapp"
3. **Agent processes query** - Parses time range, filters, and intent
4. **Retrieves and analyzes** - Combines logs with code context
5. **Returns formatted explanation** - Structured markdown with evidence

### Journey 3: Cross-Module Investigation

1. **Multiple services/modules** log errors during an incident
2. **Query cross-module analysis**: `python -m drtrace_service why --app myapp --modules service1 service2 --since 5m`
3. **Get component-level breakdown** - See which components contributed
4. **Review suggested fixes** - Actionable steps with code locations

## Getting Started

### Quick Links

- **[Installation Guide](../README.md#install-the-client-via-pip)**: Set up DrTrace in your environment
- **[Quickstart Guide](quickstart.md)**: End-to-end walkthrough
- **[API Reference](api-reference.md)**: HTTP endpoints and CLI commands
- **[Example Projects](../examples/)**: Advanced examples and multi-language scenarios
  - [Python Multi-Module](../examples/python-multi-module/README.md): Realistic multi-module Python application
  - [Python + C++ Multi-Language](../examples/python-cpp-multi-language/README.md): Cross-language logging and analysis
- **[Agent Integration Examples](../examples/agent-integrations/README.md)**: Framework-specific integration guides

### Next Steps

1. **Install DrTrace**: `pip install -e .`
2. **Set up database**: `python scripts/init_db.py`
3. **Start daemon**: `python -m drtrace_service`
4. **Integrate client**: Add 2-3 lines to your Python app
5. **Try analysis**: Use `python -m drtrace_service why` command or agent interface

## Terminology

- **Application ID**: Unique identifier for your application (e.g., "myapp")
- **Module Name**: Component or module within an application (e.g., "data_processor")
- **Service Name**: Service identifier in a microservices architecture
- **Time Range**: Start and end timestamps for querying logs
- **Root Cause Explanation**: AI-generated explanation of why an error occurred
- **Evidence Reference**: Link between explanation and specific log entries or code locations
- **Suggested Fix**: Actionable remediation step with file/line references

## Alignment with PRD and Architecture

This overview aligns with:

- **PRD**: Problem statement, target users, success criteria, and core principles
- **Architecture**: Component design, technology choices, and system boundaries
- **Implementation**: Actual features and capabilities delivered in the POC

For detailed technical specifications, see:
- **PRD**: `_bmad-output/prd.md`
- **Architecture**: `_bmad-output/architecture.md`
- **Implementation Artifacts**: `_bmad-output/implementation-artifacts/`

## Support and Feedback

This is a POC (Proof of Concept) focused on demonstrating core capabilities. For questions, issues, or feedback:

1. Review the documentation in `docs/` and `examples/`
2. Check implementation artifacts in `_bmad-output/implementation-artifacts/`
3. Review test files in `tests/` for usage examples

---

**Note**: This is a POC version. Production features, additional language support, and enterprise capabilities are planned for future releases.

