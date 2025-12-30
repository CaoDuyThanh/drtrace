# Dockerfile for DrTrace API Server
# Based on Python 3.11 slim image

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
# PostgreSQL client libraries are included in psycopg2-binary, so no need for libpq-dev
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY packages/python/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy agents directory for fallback loading
COPY agents/ ./agents/

# Install the package in editable mode
COPY packages/python/pyproject.toml .
COPY packages/python/src/ ./src/
RUN pip install --no-cache-dir -e .

# Copy scripts directory
COPY scripts/ ./scripts/

# Create non-root user for security
RUN useradd -m -u 1000 drtrace && chown -R drtrace:drtrace /app
USER drtrace

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/status || exit 1

# Default command
CMD ["uvicorn", "drtrace_service.api:app", "--host", "0.0.0.0", "--port", "8001"]

