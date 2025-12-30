"""
Example: Using drtrace init-project for project initialization

This example demonstrates the interactive project initialization workflow.
"""

# This is a demonstration of what users will see when running:
# python -m drtrace_service init-project

# ============================================================================
# TERMINAL OUTPUT EXAMPLE
# ============================================================================

# $ python -m drtrace_service init-project
#
# 🚀 DrTrace Project Initialization
#
# ==================================================
#
# 📋 Project Information:
# Project name [my-app]: flask-api
# Application ID [flask-api]: flask-api-v1
#
# 🔧 Technology Stack:
# Select language/runtime:
#   1. python
#   2. javascript
#   3. both
# Select option: 1
#
# 📡 DrTrace Daemon Configuration:
# Daemon URL [http://localhost:8001]: http://localhost:8001
# Enable DrTrace by default? (Y/n): y
#
# 🌍 Environments:
# Which environments to configure?
# (Enter numbers separated by commas, e.g., '1,3')
#   1. development
#   2. staging
#   3. production
#   4. ci
# Select options: 1,3
#
# 🤖 Agent Integration (Optional):
# Enable agent interface? (y/N): y
# Select agent framework:
#   1. bmad
#   2. langchain
#   3. other
# Select option: 1
#
# ==================================================
# ✅ Project Initialization Complete!
#
# 📍 Configuration Location: ./_drtrace
#
# 📋 Generated Files:
#    • ./_drtrace/config.json
#    • ./_drtrace/config.development.json
#    • ./_drtrace/config.production.json
#    • ./_drtrace/.env.example
#    • ./_drtrace/README.md
#    • ./_drtrace/agents/log-analysis.md
#
# 📖 Next Steps:
#    1. Review ./_drtrace/config.json
#    2. Create .env: cp ./_drtrace/.env.example .env
#    3. Start the daemon: python -m drtrace_service daemon start
#    4. Read ./_drtrace/README.md for more details
#
# ==================================================


# ============================================================================
# PYTHON CODE: Using the generated configuration
# ============================================================================

from pathlib import Path
from drtrace_service.cli.config_schema import ConfigSchema
from drtrace_client import setup_logging, ClientConfig

# Load the generated configuration
config_data = ConfigSchema.load(Path("_drtrace/config.json"))

# Extract configuration values
project_name = config_data["project_name"]
application_id = config_data["application_id"]
daemon_url = config_data["daemon_url"]
enabled = config_data["enabled"]

print(f"Project: {project_name}")
print(f"Application ID: {application_id}")
print(f"Daemon: {daemon_url}")
print(f"Enabled: {enabled}")

# Set up DrTrace logging in your application
client_config = ClientConfig(
    application_id=application_id,
    daemon_url=daemon_url,
    enabled=enabled
)

setup_logging(client_config)

# Your logging now goes through DrTrace
import logging
logger = logging.getLogger(__name__)
logger.info("Application started with DrTrace logging")


# ============================================================================
# ENVIRONMENT-SPECIFIC LOADING
# ============================================================================

import os

# Determine current environment
environment = os.getenv("APP_ENV", "development")

# Load environment-specific config
env_config_path = Path("_drtrace") / f"config.{environment}.json"

if env_config_path.exists():
    env_config = ConfigSchema.load(env_config_path)
else:
    # Fall back to main config
    env_config = config_data

# Use environment-specific values
client_config = ClientConfig(
    application_id=env_config["application_id"],
    daemon_url=env_config["daemon_url"],
    enabled=env_config["enabled"]
)

print(f"Using {environment} configuration: {env_config['daemon_url']}")


# ============================================================================
# GENERATED CONFIG FILES
# ============================================================================

# _drtrace/config.json (Main Configuration)
# {
#   "project_name": "flask-api",
#   "application_id": "flask-api-v1",
#   "language": "python",
#   "daemon_url": "http://localhost:8001",
#   "enabled": true,
#   "environments": ["development", "production"],
#   "agent": {
#     "enabled": true,
#     "framework": "bmad"
#   },
#   "created_at": "2025-01-15T10:30:45.123456+00:00"
# }

# _drtrace/config.development.json (Development Overrides)
# {
#   "project_name": "flask-api",
#   "application_id": "flask-api-v1",
#   "language": "python",
#   "daemon_url": "http://localhost:8001",
#   "enabled": true,
#   "environments": ["development"],
#   "agent": {
#     "enabled": true,
#     "framework": "bmad"
#   }
# }

# _drtrace/config.production.json (Production Overrides)
# {
#   "project_name": "flask-api",
#   "application_id": "flask-api-v1",
#   "language": "python",
#   "daemon_url": "http://prod-daemon.internal:8001",
#   "enabled": true,
#   "environments": ["production"],
#   "agent": {
#     "enabled": true,
#     "framework": "bmad"
#   }
# }


# ============================================================================
# FLASK APPLICATION EXAMPLE
# ============================================================================

from flask import Flask
from drtrace_client import setup_logging, ClientConfig

app = Flask(__name__)

# Initialize DrTrace logging with generated config
config_data = ConfigSchema.load(Path("_drtrace/config.json"))
client_config = ClientConfig(
    application_id=config_data["application_id"],
    daemon_url=config_data["daemon_url"],
    enabled=config_data["enabled"]
)
setup_logging(client_config)

logger = logging.getLogger(__name__)


@app.route("/api/users/<int:user_id>")
def get_user(user_id):
    """Get user by ID."""
    logger.info(f"Fetching user {user_id}")
    
    if user_id < 0:
        logger.error(f"Invalid user ID: {user_id}")
        return {"error": "Invalid user ID"}, 400
    
    # Fetch user logic
    return {"id": user_id, "name": "John Doe"}


if __name__ == "__main__":
    app.run(debug=True)


# ============================================================================
# ENVIRONMENT FILE USAGE (.env)
# ============================================================================

# .env (created from .env.example)
# DRTRACE_APPLICATION_ID=flask-api-v1
# DRTRACE_DAEMON_URL=http://localhost:8001
# DRTRACE_ENABLED=true
# APP_ENV=development

# Load in Python:
import os
from dotenv import load_dotenv

load_dotenv()

application_id = os.getenv("DRTRACE_APPLICATION_ID")
daemon_url = os.getenv("DRTRACE_DAEMON_URL")
enabled = os.getenv("DRTRACE_ENABLED", "true").lower() == "true"
app_env = os.getenv("APP_ENV", "development")
