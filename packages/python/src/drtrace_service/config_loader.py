"""
Configuration loading and management for DrTrace.

Notes:
- The configuration section key is `drtrace`.
- Project config files use the `_drtrace/` folder name.

Priority (highest to lowest):
1. Environment variables
2. _drtrace/config.json (per-project)
3. _drtrace/config.{ENVIRONMENT}.json (environment-specific overrides)
4. Default values

Usage:
    >>> from drtrace_service.config_loader import ConfigLoader
    >>> config = ConfigLoader.load(project_root=".", environment="production")
    >>> print(config["drtrace"]["applicationId"])  # section key
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigSchema:
    """Schema validation and defaults for DrTrace configuration."""

    # Default configuration values
    DEFAULTS = {
        "project": {
            "name": "my-app",
            "language": "python",
            "description": "My application",
        },
        "drtrace": {
            "applicationId": "my-app",
            "daemonUrl": "http://localhost:8001",
            "enabled": True,
            "logLevel": "info",
            "batchSize": 50,
            "flushIntervalMs": 1000,
            "retentionDays": 7,
        },
        "agent": {
            "enabled": False,
            "agentFile": None,
            "framework": None,
        },
        "environment": {},
    }

    # Schema definition: field -> (type, required, description)
    SCHEMA = {
        "project": {
            "name": (str, True, "Project name"),
            "language": (str, False, "Language/runtime: python, javascript, or both"),
            "description": (str, False, "Project description"),
        },
        "drtrace": {
            "applicationId": (str, True, "Unique application identifier"),
            "daemonUrl": (str, False, "DrTrace daemon URL"),
            "enabled": (bool, False, "Enable DrTrace by default"),
            "logLevel": (str, False, "Log level: debug, info, warn, error"),
            "batchSize": (int, False, "Number of logs to batch before flush"),
            "flushIntervalMs": (int, False, "Milliseconds between flushes"),
            "retentionDays": (int, False, "Log retention period in days"),
        },
        "agent": {
            "enabled": (bool, False, "Enable agent integration"),
            "agentFile": (str, False, "Path to agent spec file"),
            "framework": (str, False, "Agent framework: bmad, langchain, or other"),
        },
        "environment": (dict, False, "Environment-specific overrides"),
    }

    @classmethod
    def validate(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration against schema.

        Args:
            config: Configuration dict to validate

        Returns:
            Validated configuration dict

        Raises:
            ValueError: If validation fails
        """
        errors = []

        # Check required fields
        for section, fields in cls.SCHEMA.items():
            if section == "environment":
                continue  # Skip environment section, it's flexible

            if section not in config:
                errors.append(f"Missing required section: {section}")
                continue

            if isinstance(fields, dict):
                for field, (field_type, required, _) in fields.items():
                    if required and field not in config[section]:
                        errors.append(
                            f"Missing required field: {section}.{field}"
                        )
                    elif field in config[section]:
                        value = config[section][field]
                        # Allow None for optional fields
                        if value is not None and not isinstance(value, field_type):
                            errors.append(
                                f"Invalid type for {section}.{field}: "
                                f"expected {field_type.__name__}, "
                                f"got {type(value).__name__}"
                            )

        # Validate enum values
        if "drtrace" in config:
            if "logLevel" in config["drtrace"]:
                valid_levels = ["debug", "info", "warn", "error"]
                if config["drtrace"]["logLevel"] not in valid_levels:
                    errors.append(
                        f"Invalid logLevel: {config['drtrace']['logLevel']}. "
                        f"Must be one of: {', '.join(valid_levels)}"
                    )

            if "enabled" in config["drtrace"]:
                if not isinstance(config["drtrace"]["enabled"], bool):
                    errors.append(
                        "Invalid enabled value: must be boolean"
                    )

        if "agent" in config:
            if "framework" in config["agent"] and config["agent"]["framework"]:
                valid_frameworks = ["bmad", "langchain", "other"]
                if config["agent"]["framework"] not in valid_frameworks:
                    errors.append(
                        f"Invalid agent framework: {config['agent']['framework']}. "
                        f"Must be one of: {', '.join(valid_frameworks)}"
                    )

        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))

        return config

    @classmethod
    def get_default(cls) -> Dict[str, Any]:
        """Get default configuration."""
        return json.loads(json.dumps(cls.DEFAULTS))  # Deep copy


class ConfigLoader:
    """Loads and merges configuration from multiple sources."""

    @classmethod
    def load(
        cls,
        project_root: str = ".",
        environment: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Load configuration with hierarchical merging.

        Priority (highest to lowest):
        1. Environment variables (DRTRACE_* prefix)
        2. _drtrace/config.json
        3. _drtrace/config.{environment}.json
        4. Default values

        Args:
            project_root: Root directory of the project
            environment: Environment name (e.g., 'production', 'development').
                        If None, uses PYTHON_ENV or NODE_ENV env var.

        Returns:
            Merged and validated configuration dict

        Raises:
            ValueError: If configuration is invalid
            FileNotFoundError: If config file is missing and required
        """
        config_dir = Path(project_root) / "_drtrace"
        base_config_path = config_dir / "config.json"

        # Start with defaults
        config = ConfigSchema.get_default()

        # Determine environment
        if environment is None:
            environment = os.environ.get("PYTHON_ENV") or os.environ.get("NODE_ENV")

        # Load base config from _drtrace/config.json
        if base_config_path.exists():
            config = cls._merge_configs(
                config, cls._load_json_file(base_config_path)
            )

        # Load environment-specific overrides
        if environment:
            # First, check for environment-specific subsection in base config
            if "environment" in config and environment in config["environment"]:
                config = cls._merge_configs(
                    config, {"drtrace": config["environment"][environment]}
                )

            # Then, load environment-specific config file (takes precedence)
            env_config_path = config_dir / f"config.{environment}.json"
            if env_config_path.exists():
                env_config = cls._load_json_file(env_config_path)
                config = cls._merge_configs(config, env_config)

        # Apply environment variable overrides (highest priority)
        config = cls._apply_env_var_overrides(config)

        # Validate final configuration
        config = ConfigSchema.validate(config)

        return config

    @staticmethod
    def _load_json_file(filepath: Path) -> Dict[str, Any]:
        """Load and parse JSON file."""
        try:
            with open(filepath, "r") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {filepath}: {e}")
        except OSError as e:
            raise ValueError(f"Error reading {filepath}: {e}")

    @staticmethod
    def _merge_configs(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge overrides into base config.

        Args:
            base: Base configuration dict
            overrides: Configuration dict to merge in

        Returns:
            Merged configuration
        """
        result = json.loads(json.dumps(base))  # Deep copy

        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    @staticmethod
    def _apply_env_var_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to config.

        Environment variables use DRTRACE_* prefix with UPPER_SNAKE_CASE.
        Examples:
            - DRTRACE_APPLICATION_ID -> config["drtrace"]["applicationId"]
            - DRTRACE_DAEMON_URL -> config["drtrace"]["daemonUrl"]
            - DRTRACE_ENABLED -> config["drtrace"]["enabled"]

        Args:
            config: Configuration dict

        Returns:
            Config with env var overrides applied
        """
        result = json.loads(json.dumps(config))  # Deep copy

        # Map environment variable names to config paths
        env_var_mappings = {
            "DRTRACE_APPLICATION_ID": ("drtrace", "applicationId"),
            "DRTRACE_DAEMON_URL": ("drtrace", "daemonUrl"),
            "DRTRACE_ENABLED": ("drtrace", "enabled"),
            "DRTRACE_LOG_LEVEL": ("drtrace", "logLevel"),
            "DRTRACE_BATCH_SIZE": ("drtrace", "batchSize"),
            "DRTRACE_FLUSH_INTERVAL_MS": ("drtrace", "flushIntervalMs"),
            "DRTRACE_RETENTION_DAYS": ("drtrace", "retentionDays"),
            "DRTRACE_AGENT_ENABLED": ("agent", "enabled"),
            "DRTRACE_AGENT_FILE": ("agent", "agentFile"),
            "DRTRACE_AGENT_FRAMEWORK": ("agent", "framework"),
        }

        for env_var, (section, field) in env_var_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]

                # Type conversions
                if field in ["enabled", "ENABLED"]:
                    value = value.lower() in ("true", "1", "yes")
                elif field in ["batchSize", "flushIntervalMs", "retentionDays"]:
                    try:
                        value = int(value)
                    except ValueError:
                        raise ValueError(
                            f"Invalid value for {env_var}: must be an integer"
                        )

                if section not in result:
                    result[section] = {}
                result[section][field] = value

        return result


def load_config(
    project_root: str = ".",
    environment: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Convenience function to load configuration.

    Args:
        project_root: Root directory of the project
        environment: Environment name (e.g., 'production')

    Returns:
        Loaded and validated configuration dict
    """
    return ConfigLoader.load(project_root=project_root, environment=environment)
