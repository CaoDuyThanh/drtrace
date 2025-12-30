"""Tests for DrTrace configuration loader."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from drtrace_service.config_loader import ConfigLoader, ConfigSchema, load_config


class TestConfigSchema:
    """Tests for ConfigSchema validation and defaults."""

    def test_get_default_returns_valid_config(self):
        """Test that default config is valid."""
        defaults = ConfigSchema.get_default()
        validated = ConfigSchema.validate(defaults)
        assert validated["project"]["name"] == "my-app"
        assert validated["drtrace"]["applicationId"] == "my-app"
        assert validated["drtrace"]["enabled"] is True

    def test_validate_rejects_missing_required_fields(self):
        """Test validation fails with missing required fields."""
        config = {"project": {}}  # Missing name
        with pytest.raises(ValueError, match="Missing required field"):
            ConfigSchema.validate(config)

    def test_validate_rejects_invalid_types(self):
        """Test validation fails with invalid field types."""
        config = ConfigSchema.get_default()
        config["drtrace"]["batchSize"] = "not-a-number"
        with pytest.raises(ValueError, match="Invalid type"):
            ConfigSchema.validate(config)

    def test_validate_rejects_invalid_log_level(self):
        """Test validation fails with invalid log level."""
        config = ConfigSchema.get_default()
        config["drtrace"]["logLevel"] = "invalid"
        with pytest.raises(ValueError, match="Invalid logLevel"):
            ConfigSchema.validate(config)

    def test_validate_accepts_valid_log_levels(self):
        """Test validation accepts all valid log levels."""
        for level in ["debug", "info", "warn", "error"]:
            config = ConfigSchema.get_default()
            config["drtrace"]["logLevel"] = level
            validated = ConfigSchema.validate(config)
            assert validated["drtrace"]["logLevel"] == level

    def test_validate_rejects_invalid_agent_framework(self):
        """Test validation fails with invalid agent framework."""
        config = ConfigSchema.get_default()
        config["agent"]["framework"] = "invalid-framework"
        with pytest.raises(ValueError, match="Invalid agent framework"):
            ConfigSchema.validate(config)

    def test_validate_accepts_valid_agent_frameworks(self):
        """Test validation accepts all valid agent frameworks."""
        for framework in ["bmad", "langchain", "other"]:
            config = ConfigSchema.get_default()
            config["agent"]["framework"] = framework
            validated = ConfigSchema.validate(config)
            assert validated["agent"]["framework"] == framework

    def test_validate_accepts_config_with_optional_fields(self):
        """Test validation accepts config with all optional fields."""
        config = ConfigSchema.get_default()
        config["drtrace"]["logLevel"] = "debug"
        config["agent"]["enabled"] = True
        config["agent"]["framework"] = "bmad"
        validated = ConfigSchema.validate(config)
        assert validated["drtrace"]["logLevel"] == "debug"
        assert validated["agent"]["enabled"] is True


class TestConfigMerging:
    """Tests for configuration merging logic."""

    def test_merge_configs_simple_override(self):
        """Test merging with simple value override."""
        base = {"a": 1, "b": 2}
        overrides = {"b": 3}
        result = ConfigLoader._merge_configs(base, overrides)
        assert result == {"a": 1, "b": 3}

    def test_merge_configs_deep_merge(self):
        """Test deep merging of nested dicts."""
        base = {"drtrace": {"applicationId": "app1", "enabled": True}}
        overrides = {"drtrace": {"applicationId": "app2"}}
        result = ConfigLoader._merge_configs(base, overrides)
        assert result["drtrace"]["applicationId"] == "app2"
        assert result["drtrace"]["enabled"] is True

    def test_merge_configs_adds_new_keys(self):
        """Test that merging adds new keys."""
        base = {"a": 1}
        overrides = {"b": 2}
        result = ConfigLoader._merge_configs(base, overrides)
        assert result == {"a": 1, "b": 2}

    def test_merge_configs_does_not_modify_base(self):
        """Test that merging does not modify the original base."""
        base = {"drtrace": {"applicationId": "app1"}}
        base_copy = json.loads(json.dumps(base))
        overrides = {"drtrace": {"applicationId": "app2"}}
        ConfigLoader._merge_configs(base, overrides)
        assert base == base_copy


class TestConfigLoading:
    """Tests for full configuration loading workflow."""

    def test_load_with_defaults_only(self):
        """Test loading with only defaults (no config files)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConfigLoader.load(project_root=tmpdir)
            assert config["project"]["name"] == "my-app"
            assert config["drtrace"]["applicationId"] == "my-app"
            assert config["drtrace"]["daemonUrl"] == "http://localhost:8001"

    def test_load_from_config_json(self):
        """Test loading from _drtrace/config.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {
                "project": {"name": "my-custom-app"},
                "drtrace": {"applicationId": "custom-app"},
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            config = ConfigLoader.load(project_root=tmpdir)
            assert config["project"]["name"] == "my-custom-app"
            assert config["drtrace"]["applicationId"] == "custom-app"

    def test_load_environment_specific_override(self):
        """Test loading environment-specific config overrides."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()

            # Base config
            base_config = {
                "project": {"name": "my-app"},
                "drtrace": {
                    "applicationId": "my-app",
                    "daemonUrl": "http://localhost:8001",
                    "enabled": True,
                },
            }
            with open(config_dir / "config.json", "w") as f:
                json.dump(base_config, f)

            # Production override
            prod_config = {"drtrace": {"daemonUrl": "https://production.example.com"}}
            with open(config_dir / "config.production.json", "w") as f:
                json.dump(prod_config, f)

            config = ConfigLoader.load(project_root=tmpdir, environment="production")
            assert config["drtrace"]["daemonUrl"] == "https://production.example.com"
            assert config["drtrace"]["applicationId"] == "my-app"  # From base

    def test_load_environment_subsection_override(self):
        """Test loading environment subsection from base config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()

            config_data = {
                "project": {"name": "my-app"},
                "drtrace": {
                    "applicationId": "my-app",
                    "daemonUrl": "http://localhost:8001",
                    "enabled": True,
                },
                "environment": {
                    "production": {
                        "daemonUrl": "https://production.example.com",
                        "enabled": False,
                    }
                },
            }
            with open(config_dir / "config.json", "w") as f:
                json.dump(config_data, f)

            config = ConfigLoader.load(project_root=tmpdir, environment="production")
            assert config["drtrace"]["daemonUrl"] == "https://production.example.com"
            assert config["drtrace"]["enabled"] is False

    def test_load_detects_environment_from_python_env(self):
        """Test that loader uses PYTHON_ENV variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()

            base_config = {
                "project": {"name": "my-app"},
                "drtrace": {"applicationId": "my-app"},
            }
            with open(config_dir / "config.json", "w") as f:
                json.dump(base_config, f)

            prod_config = {"drtrace": {"enabled": False}}
            with open(config_dir / "config.production.json", "w") as f:
                json.dump(prod_config, f)

            # Set PYTHON_ENV and load without explicit environment
            os.environ["PYTHON_ENV"] = "production"
            try:
                config = ConfigLoader.load(project_root=tmpdir)
                assert config["drtrace"]["enabled"] is False
            finally:
                del os.environ["PYTHON_ENV"]

    def test_load_detects_environment_from_node_env(self):
        """Test that loader uses NODE_ENV variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()

            base_config = {
                "project": {"name": "my-app"},
                "drtrace": {"applicationId": "my-app"},
            }
            with open(config_dir / "config.json", "w") as f:
                json.dump(base_config, f)

            dev_config = {"drtrace": {"logLevel": "debug"}}
            with open(config_dir / "config.development.json", "w") as f:
                json.dump(dev_config, f)

            # Set NODE_ENV and load without explicit environment
            os.environ["NODE_ENV"] = "development"
            try:
                config = ConfigLoader.load(project_root=tmpdir)
                assert config["drtrace"]["logLevel"] == "debug"
            finally:
                del os.environ["NODE_ENV"]


class TestEnvironmentVariableOverrides:
    """Tests for environment variable overrides."""

    def test_env_var_override_application_id(self):
        """Test DRTRACE_APPLICATION_ID override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {
                "project": {"name": "my-app"},
                "drtrace": {"applicationId": "from-file"},
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            os.environ["DRTRACE_APPLICATION_ID"] = "from-env"
            try:
                config = ConfigLoader.load(project_root=tmpdir)
                assert config["drtrace"]["applicationId"] == "from-env"
            finally:
                del os.environ["DRTRACE_APPLICATION_ID"]

    def test_env_var_override_daemon_url(self):
        """Test DRTRACE_DAEMON_URL override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {
                "project": {"name": "my-app"},
                "drtrace": {
                    "applicationId": "my-app",
                    "daemonUrl": "http://localhost:8001",
                },
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            os.environ["DRTRACE_DAEMON_URL"] = "http://custom-daemon:9000"
            try:
                config = ConfigLoader.load(project_root=tmpdir)
                assert config["drtrace"]["daemonUrl"] == "http://custom-daemon:9000"
            finally:
                del os.environ["DRTRACE_DAEMON_URL"]

    def test_env_var_override_enabled_true(self):
        """Test DRTRACE_ENABLED=true override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {
                "project": {"name": "my-app"},
                "drtrace": {"applicationId": "my-app", "enabled": False},
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            os.environ["DRTRACE_ENABLED"] = "true"
            try:
                config = ConfigLoader.load(project_root=tmpdir)
                assert config["drtrace"]["enabled"] is True
            finally:
                del os.environ["DRTRACE_ENABLED"]

    def test_env_var_override_enabled_false(self):
        """Test DRTRACE_ENABLED=false override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {
                "project": {"name": "my-app"},
                "drtrace": {"applicationId": "my-app", "enabled": True},
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            os.environ["DRTRACE_ENABLED"] = "false"
            try:
                config = ConfigLoader.load(project_root=tmpdir)
                assert config["drtrace"]["enabled"] is False
            finally:
                del os.environ["DRTRACE_ENABLED"]

    def test_env_var_override_batch_size(self):
        """Test DRTRACE_BATCH_SIZE integer override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {
                "project": {"name": "my-app"},
                "drtrace": {"applicationId": "my-app", "batchSize": 50},
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            os.environ["DRTRACE_BATCH_SIZE"] = "100"
            try:
                config = ConfigLoader.load(project_root=tmpdir)
                assert config["drtrace"]["batchSize"] == 100
            finally:
                del os.environ["DRTRACE_BATCH_SIZE"]

    def test_env_var_override_batch_size_invalid(self):
        """Test DRTRACE_BATCH_SIZE with invalid value raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {
                "project": {"name": "my-app"},
                "drtrace": {"applicationId": "my-app"},
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            os.environ["DRTRACE_BATCH_SIZE"] = "not-a-number"
            try:
                with pytest.raises(ValueError, match="must be an integer"):
                    ConfigLoader.load(project_root=tmpdir)
            finally:
                del os.environ["DRTRACE_BATCH_SIZE"]

    def test_env_var_override_agent_framework(self):
        """Test DRTRACE_AGENT_FRAMEWORK override."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {
                "project": {"name": "my-app"},
                "drtrace": {"applicationId": "my-app"},
                "agent": {"framework": None},
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            os.environ["DRTRACE_AGENT_FRAMEWORK"] = "langchain"
            try:
                config = ConfigLoader.load(project_root=tmpdir)
                assert config["agent"]["framework"] == "langchain"
            finally:
                del os.environ["DRTRACE_AGENT_FRAMEWORK"]

    def test_env_vars_highest_priority(self):
        """Test that env vars override file-based config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()

            # Base config
            base_config = {
                "project": {"name": "my-app"},
                "drtrace": {
                    "applicationId": "from-file",
                    "daemonUrl": "http://file-daemon:8001",
                },
            }
            with open(config_dir / "config.json", "w") as f:
                json.dump(base_config, f)

            # Production override
            prod_config = {"drtrace": {"applicationId": "from-prod-file"}}
            with open(config_dir / "config.production.json", "w") as f:
                json.dump(prod_config, f)

            # Env var override (should win)
            os.environ["DRTRACE_APPLICATION_ID"] = "from-env"
            os.environ["DRTRACE_DAEMON_URL"] = "http://env-daemon:9000"
            try:
                config = ConfigLoader.load(project_root=tmpdir, environment="production")
                assert config["drtrace"]["applicationId"] == "from-env"
                assert config["drtrace"]["daemonUrl"] == "http://env-daemon:9000"
            finally:
                del os.environ["DRTRACE_APPLICATION_ID"]
                del os.environ["DRTRACE_DAEMON_URL"]


class TestInvalidConfigurations:
    """Tests for error handling with invalid configurations."""

    def test_invalid_json_in_config_file(self):
        """Test that invalid JSON is caught."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            with open(config_file, "w") as f:
                f.write("{ invalid json }")

            with pytest.raises(ValueError, match="Invalid JSON"):
                ConfigLoader.load(project_root=tmpdir)

    def test_missing_config_file_uses_defaults(self):
        """Test that missing config file falls back to defaults."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConfigLoader.load(project_root=tmpdir)
            assert config["project"]["name"] == "my-app"

    def test_missing_drtrace_section_in_config(self):
        """Test that missing drtrace section uses defaults for that section."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {"project": {"name": "my-app"}}  # Missing drtrace section
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            # Should not raise - drtrace section comes from defaults
            config = ConfigLoader.load(project_root=tmpdir)
            assert config["project"]["name"] == "my-app"
            assert config["drtrace"]["applicationId"] == "my-app"  # From defaults


class TestConvenienceFunction:
    """Tests for load_config convenience function."""

    def test_load_config_convenience_function(self):
        """Test that load_config convenience function works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()
            config_file = config_dir / "config.json"

            config_data = {
                "project": {"name": "my-app"},
                "drtrace": {"applicationId": "test-app"},
            }
            with open(config_file, "w") as f:
                json.dump(config_data, f)

            config = load_config(project_root=tmpdir)
            assert config["project"]["name"] == "my-app"
            assert config["drtrace"]["applicationId"] == "test-app"


class TestLoadingPriority:
    """Tests to verify the complete loading priority."""

    def test_complete_loading_priority(self):
        """
        Test complete loading priority:
        1. Env vars (highest)
        2. File config
        3. Env-specific overrides
        4. Defaults (lowest)
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "_drtrace"
            config_dir.mkdir()

            # Base config (overrides defaults)
            base_config = {
                "project": {"name": "from-base"},
                "drtrace": {
                    "applicationId": "from-base",
                    "daemonUrl": "http://localhost:8001",
                    "logLevel": "info",  # Will be overridden
                },
            }
            with open(config_dir / "config.json", "w") as f:
                json.dump(base_config, f)

            # Production override (overrides base for this field)
            prod_config = {"drtrace": {"logLevel": "debug"}}
            with open(config_dir / "config.production.json", "w") as f:
                json.dump(prod_config, f)

            # Env var (overrides everything)
            os.environ["DRTRACE_DAEMON_URL"] = "http://env-daemon:9000"
            try:
                config = ConfigLoader.load(project_root=tmpdir, environment="production")

                # From env var (highest)
                assert config["drtrace"]["daemonUrl"] == "http://env-daemon:9000"

                # From env-specific override
                assert config["drtrace"]["logLevel"] == "debug"

                # From base config
                assert config["drtrace"]["applicationId"] == "from-base"

                # From defaults (for fields not specified anywhere)
                assert config["drtrace"]["batchSize"] == 50
            finally:
                del os.environ["DRTRACE_DAEMON_URL"]
