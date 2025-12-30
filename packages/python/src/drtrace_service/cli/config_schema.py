"""
Configuration schema and validation for DrTrace projects.

Defines the structure of _drtrace/config.json and provides validation helpers.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConfigSchema:
    """Schema and validation for DrTrace configuration."""

    # JSON Schema for config.json
    SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "DrTrace Project Configuration",
        "type": "object",
        "required": ["project_name", "application_id"],
        "properties": {
            "project_name": {
                "type": "string",
                "description": "Name of the project",
                "minLength": 1,
                "maxLength": 255
            },
            "application_id": {
                "type": "string",
                "description": "Unique application identifier",
                "minLength": 1,
                "maxLength": 255
            },
            "language": {
                "type": "string",
                "enum": ["python", "javascript", "cpp", "both"],
                "default": "python"
            },
            "daemon_url": {
                "type": "string",
                "description": "URL of the DrTrace daemon (e.g., http://localhost:8001)",
                "format": "uri",
                "default": "http://localhost:8001"
            },
            "enabled": {
                "type": "boolean",
                "description": "Enable DrTrace by default",
                "default": True
            },
            "environments": {
                "type": "array",
                "description": "List of environments to configure",
                "items": {
                    "type": "string",
                    "enum": ["development", "staging", "production", "ci"]
                },
                "default": ["development"]
            },
            "agent": {
                "type": "object",
                "description": "Agent configuration",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "Enable agent interface",
                        "default": False
                    },
                    "framework": {
                        "type": "string",
                        "enum": ["bmad", "langchain", "other"],
                        "default": "bmad"
                    }
                }
            },
            "created_at": {
                "type": "string",
                "description": "ISO 8601 timestamp of config creation"
            }
        },
        "additionalProperties": False
    }

    @staticmethod
    def get_default_config(
        project_name: str,
        application_id: str,
        language: str = "python",
        daemon_url: str = "http://localhost:8001",
        enabled: bool = True,
        environments: Optional[List[str]] = None,
        agent_enabled: bool = False,
        agent_framework: str = "bmad"
    ) -> Dict[str, Any]:
        """Generate a default configuration dictionary."""
        from datetime import datetime, timezone

        return {
            "project_name": project_name,
            "application_id": application_id,
            "language": language,
            "daemon_url": daemon_url,
            "enabled": enabled,
            "environments": environments or ["development"],
            "agent": {
                "enabled": agent_enabled,
                "framework": agent_framework
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def validate(config: Dict[str, Any]) -> bool:
        """
        Validate configuration against schema.

        Returns:
            True if valid, raises ValueError if invalid.
        """
        # Basic validation (full JSON schema validation requires jsonschema library)
        required = ["project_name", "application_id"]
        for field in required:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
            if not isinstance(config[field], str) or not config[field]:
                raise ValueError(f"Field '{field}' must be a non-empty string")

        if not isinstance(config.get("enabled", True), bool):
            raise ValueError("Field 'enabled' must be boolean")

        if "environments" in config:
            if not isinstance(config["environments"], list):
                raise ValueError("Field 'environments' must be a list")
            valid_envs = {"development", "staging", "production", "ci"}
            for env in config["environments"]:
                if env not in valid_envs:
                    raise ValueError(f"Invalid environment: {env}")

        return True

    @staticmethod
    def save(config: Dict[str, Any], path: Path) -> None:
        """Save configuration to file."""
        ConfigSchema.validate(config)
        path.write_text(json.dumps(config, indent=2))

    @staticmethod
    def load(path: Path) -> Dict[str, Any]:
        """Load configuration from file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        config = json.loads(path.read_text())
        ConfigSchema.validate(config)
        return config
