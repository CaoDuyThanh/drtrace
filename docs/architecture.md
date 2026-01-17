# DrTrace Architecture Overview

## Overview

DrTrace is an AI-powered root-cause analysis tool for application logs. It provides multi-language client libraries for capturing structured logs, a local daemon for storage and querying, and AI agents for automated analysis and troubleshooting.

## Core Components

### 1. Multi-Language Clients
- **Python Client**: Primary client with full feature set
- **JavaScript/TypeScript Client**: Browser and Node.js support
- **C++ Client**: Header-only implementation with spdlog integration
- **Unified Log Schema**: Consistent log format across all languages

### 2. Local Daemon
- **Storage**: Time-series log storage with efficient querying
- **API Endpoints**: RESTful API for log ingestion and retrieval
- **Cross-Language Querying**: Unified interface for logs from different clients

### 3. AI Agents
- **Log Analysis Agent**: Generates root-cause explanations from error logs
- **Log Init Agent**: Provides setup guidance for new projects
- **Log Help Agent**: Offers logging best practices and troubleshooting
- **Agent Interface**: Standardized API for agent interactions

### 4. Packaging and Distribution
- **Monorepo Structure**: Single repository with packages for each language
- **Version Management**: Makefile-based versioning with single source of truth
- **CI/CD Pipeline**: Automated testing, building, and publishing

## Design Principles

- **Multi-Process Safe**: Clients handle concurrent logging safely
- **Minimal Integration**: Easy setup with minimal code changes
- **AI-Powered Analysis**: Automated root-cause identification
- **Cross-Language Consistency**: Unified experience across programming languages
- **Local-First**: Runs locally without external dependencies

## Architecture Decisions

- **Client-Server Model**: Clients send logs to local daemon
- **RESTful API**: Simple HTTP interface for daemon interactions
- **Semantic Versioning**: Strict semver with cascading downgrade logic
- **Agent Framework**: Extensible agent system for different analysis types
- **Header-Only C++**: Zero-dependency C++ integration</content>
<parameter name="filePath">/media/singularity/data/projects/drtrace/docs/architecture.md