"""
Unit tests for ClientConfig::from_params_or_env() fallback behavior.

Tests:
- Fallback to "my-app" when application_id is missing
- Environment variable override
- Config file reading
- Consistency with C++ and JavaScript default value
"""

import json
import os
import tempfile
from pathlib import Path

from drtrace_client.config import ClientConfig


class TestClientConfigFallback:
    """Tests for ClientConfig fallback behavior."""

    def setup_method(self):
        """Set up test environment."""
        # Save original environment variables
        self.original_app_id = os.environ.get("DRTRACE_APPLICATION_ID")
        self.original_daemon_url = os.environ.get("DRTRACE_DAEMON_URL")

        # Clear environment variables
        if "DRTRACE_APPLICATION_ID" in os.environ:
            del os.environ["DRTRACE_APPLICATION_ID"]
        if "DRTRACE_DAEMON_URL" in os.environ:
            del os.environ["DRTRACE_DAEMON_URL"]

        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up test environment."""
        # Restore original working directory
        os.chdir(self.original_cwd)

        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

        # Restore environment variables
        if self.original_app_id:
            os.environ["DRTRACE_APPLICATION_ID"] = self.original_app_id
        elif "DRTRACE_APPLICATION_ID" in os.environ:
            del os.environ["DRTRACE_APPLICATION_ID"]

        if self.original_daemon_url:
            os.environ["DRTRACE_DAEMON_URL"] = self.original_daemon_url
        elif "DRTRACE_DAEMON_URL" in os.environ:
            del os.environ["DRTRACE_DAEMON_URL"]

    def create_config_file(self, application_id):
        """Create a config file with the given application_id."""
        config_dir = Path("_drtrace")
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        config_data = {"application_id": application_id}
        config_file.write_text(json.dumps(config_data))

    def remove_config_file(self):
        """Remove the config file."""
        config_dir = Path("_drtrace")
        if config_dir.exists():
            import shutil
            shutil.rmtree(config_dir)

    # Test Case 1: No param, no env var, no config file - should fallback to "my-app"
    def test_fallback_to_default_when_missing(self):
        """Test that application_id falls back to 'my-app' when missing."""
        self.remove_config_file()

        # Should not raise ValueError, should use default "my-app"
        config = ClientConfig.from_params_or_env()
        assert config.application_id == "my-app"

    # Test Case 2: Env var override - should use env var value
    def test_env_var_override(self):
        """Test that environment variable takes precedence."""
        self.remove_config_file()
        os.environ["DRTRACE_APPLICATION_ID"] = "test-app"

        config = ClientConfig.from_params_or_env()
        assert config.application_id == "test-app"

        del os.environ["DRTRACE_APPLICATION_ID"]

    # Test Case 3: Config file present - should use config file value
    def test_config_file_fallback(self):
        """Test that config file is read when env var is not set."""
        self.create_config_file("artos")
        if "DRTRACE_APPLICATION_ID" in os.environ:
            del os.environ["DRTRACE_APPLICATION_ID"]

        config = ClientConfig.from_params_or_env()
        assert config.application_id == "artos"

    # Test Case 4: Explicit parameter takes precedence over env var
    def test_explicit_param_takes_precedence(self):
        """Test that explicit parameter takes highest precedence."""
        self.create_config_file("artos")
        os.environ["DRTRACE_APPLICATION_ID"] = "env-app"

        config = ClientConfig.from_params_or_env(application_id="param-app")
        assert config.application_id == "param-app"

        del os.environ["DRTRACE_APPLICATION_ID"]

    # Test Case 5: Env var takes precedence over config file
    def test_env_var_takes_precedence_over_config_file(self):
        """Test that env var takes precedence over config file."""
        self.create_config_file("artos")
        os.environ["DRTRACE_APPLICATION_ID"] = "env-override"

        config = ClientConfig.from_params_or_env()
        assert config.application_id == "env-override"

        del os.environ["DRTRACE_APPLICATION_ID"]

    # Test Case 6: Consistency test - verify default value matches C++/JavaScript
    def test_consistency_with_other_languages(self):
        """Test that default value matches C++ and JavaScript."""
        self.remove_config_file()

        config = ClientConfig.from_params_or_env()
        # CRITICAL: Must use same default value as C++ and JavaScript: "my-app"
        assert config.application_id == "my-app"

    # Test Case 7: Empty config file - should fallback to default
    def test_empty_config_file_fallback(self):
        """Test that empty config file falls back to default."""
        config_dir = Path("_drtrace")
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text("{}")

        config = ClientConfig.from_params_or_env()
        assert config.application_id == "my-app"

    # Test Case 8: Invalid JSON config file - should fallback to default
    def test_invalid_config_file_fallback(self):
        """Test that invalid JSON config file falls back to default."""
        config_dir = Path("_drtrace")
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        config_file.write_text("{invalid json}")

        config = ClientConfig.from_params_or_env()
        assert config.application_id == "my-app"

    # Test Case 9: Config file with applicationId (camelCase) - should work
    def test_config_file_camelcase(self):
        """Test that config file with camelCase applicationId works."""
        config_dir = Path("_drtrace")
        config_dir.mkdir(exist_ok=True)
        config_file = config_dir / "config.json"
        config_data = {"applicationId": "camel-case-app"}
        config_file.write_text(json.dumps(config_data))

        config = ClientConfig.from_params_or_env()
        assert config.application_id == "camel-case-app"

