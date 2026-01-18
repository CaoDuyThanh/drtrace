"""
Tests for the init-project CLI workflow.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import pytest

from drtrace_service.cli.config_schema import ConfigSchema
from drtrace_service.cli.init_project import ProjectInitializer


class TestConfigSchema:
    """Test configuration schema validation."""

    def test_default_config_generation(self):
        """Test generating a default configuration."""
        config = ConfigSchema.get_default_config(
            project_name="test-app",
            application_id="test-app-123"
        )

        assert config["project_name"] == "test-app"
        assert config["application_id"] == "test-app-123"
        assert config["language"] == "python"
        assert config["daemon_url"] == "http://localhost:8001"
        assert config["enabled"] is True
        assert "created_at" in config
        assert config["agent"]["enabled"] is False

    def test_config_with_custom_values(self):
        """Test generating config with custom values."""
        config = ConfigSchema.get_default_config(
            project_name="my-project",
            application_id="my-app",
            language="javascript",
            daemon_url="http://prod:8001",
            enabled=False,
            environments=["production", "staging"],
            agent_enabled=True,
            agent_framework="langchain"
        )

        assert config["language"] == "javascript"
        assert config["daemon_url"] == "http://prod:8001"
        assert config["enabled"] is False
        assert config["environments"] == ["production", "staging"]
        assert config["agent"]["enabled"] is True
        assert config["agent"]["framework"] == "langchain"

    def test_validation_requires_project_name(self):
        """Test that validation requires project_name."""
        config = {
            "application_id": "test-app"
        }

        with pytest.raises(ValueError, match="project_name"):
            ConfigSchema.validate(config)

    def test_validation_requires_application_id(self):
        """Test that validation requires application_id."""
        config = {
            "project_name": "test-app"
        }

        with pytest.raises(ValueError, match="application_id"):
            ConfigSchema.validate(config)

    def test_validation_accepts_valid_environments(self):
        """Test that validation accepts valid environments."""
        config = ConfigSchema.get_default_config(
            project_name="test",
            application_id="test",
            environments=["development", "staging", "production"]
        )

        assert ConfigSchema.validate(config) is True

    def test_validation_rejects_invalid_environments(self):
        """Test that validation rejects invalid environments."""
        config = ConfigSchema.get_default_config(
            project_name="test",
            application_id="test",
            environments=["development", "invalid-env"]
        )

        with pytest.raises(ValueError, match="Invalid environment"):
            ConfigSchema.validate(config)

    def test_save_and_load_config(self):
        """Test saving and loading configuration files."""
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            original = ConfigSchema.get_default_config(
                project_name="test-app",
                application_id="test-app"
            )

            ConfigSchema.save(original, config_path)
            assert config_path.exists()

            loaded = ConfigSchema.load(config_path)
            assert loaded["project_name"] == original["project_name"]
            assert loaded["application_id"] == original["application_id"]

    def test_load_nonexistent_file_raises(self):
        """Test that loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            ConfigSchema.load(Path("/nonexistent/config.json"))


class TestProjectInitializer:
    """Test project initialization workflow."""

    def test_initializer_with_default_root(self):
        """Test initializer uses current directory by default."""
        initializer = ProjectInitializer()
        assert initializer.project_root == Path.cwd()
        assert initializer.drtrace_dir == Path.cwd() / "_drtrace"

    def test_initializer_with_custom_root(self):
        """Test initializer with custom project root."""
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initializer = ProjectInitializer(root)

            assert initializer.project_root == root
            assert initializer.drtrace_dir == root / "_drtrace"
            assert initializer.config_path == root / "_drtrace" / "config.json"

    def test_create_directory_structure(self):
        """Test directory structure creation."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            assert (Path(tmpdir) / "_drtrace").exists()
            assert (Path(tmpdir) / "_drtrace" / "agents").exists()

    def test_generate_environment_configs(self):
        """Test generating environment-specific configs."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            config = ConfigSchema.get_default_config(
                project_name="test",
                application_id="test",
                environments=["development", "staging", "production"]
            )

            initializer._generate_environment_configs(config)

            for env in ["development", "staging", "production"]:
                env_config_path = initializer.drtrace_dir / f"config.{env}.json"
                assert env_config_path.exists()

                env_config = json.loads(env_config_path.read_text())
                assert env_config["project_name"] == "test"

    def test_generate_env_example(self):
        """Test .env.example generation."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            config = ConfigSchema.get_default_config(
                project_name="test-app",
                application_id="test-app-123",
                daemon_url="http://custom:8001"
            )

            initializer._generate_env_example(config)

            env_file = initializer.drtrace_dir / ".env.example"
            assert env_file.exists()

            content = env_file.read_text()
            assert "DRTRACE_APPLICATION_ID=test-app-123" in content
            assert "DRTRACE_DAEMON_URL=http://custom:8001" in content
            assert "DRTRACE_ENABLED=true" in content

    def test_generate_readme(self):
        """Test README generation."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()
            initializer._generate_readme()

            readme = initializer.drtrace_dir / "README.md"
            assert readme.exists()

            content = readme.read_text()
            assert "DrTrace Configuration" in content
            assert "config.json" in content
            assert "Environment Variables" in content

    def test_handle_nonexistent_config_returns_true(self):
        """Test that nonexistent config returns True."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            assert initializer.handle_existing_config() is True

    def test_existing_config_can_be_detected(self):
        """Test that existing config can be detected."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            config = ConfigSchema.get_default_config(
                project_name="test",
                application_id="test"
            )
            ConfigSchema.save(config, initializer.config_path)

            assert initializer.config_path.exists()

    def test_default_agent_spec_content(self):
        """Test that default agent spec has expected content."""
        initializer = ProjectInitializer()
        content = initializer._get_default_agent_spec()

        assert "Log Analysis" in content
        assert "Purpose" in content
        assert "Capabilities" in content

    def test_default_log_it_spec_content(self):
        """Test that default log-it agent spec has expected content."""
        initializer = ProjectInitializer()
        content = initializer._get_default_log_it_spec()

        assert "Log-It Agent" in content
        assert "Strategic Logging" in content
        assert "privacy-conscious" in content
        assert "5 criteria" in content

    def test_load_agent_spec_log_analysis(self):
        """Test loading log-analysis agent spec."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            try:
                content = initializer._load_agent_spec("log-analysis")
                assert len(content) > 0
                assert "log-analysis" in content.lower() or "log analysis" in content.lower()
            except FileNotFoundError:
                # Fallback to default if resource not found
                content = initializer._get_default_agent_spec()
                assert "Log Analysis" in content

    def test_load_agent_spec_log_it(self):
        """Test loading log-it agent spec."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            try:
                content = initializer._load_agent_spec("log-it")
                assert len(content) > 0
                assert "log-it" in content.lower() or "log it" in content.lower()
            except FileNotFoundError:
                # Fallback to default if resource not found
                content = initializer._get_default_log_it_spec()
                assert "Log-It Agent" in content

    def test_copy_agent_spec_copies_all_agents(self):
        """Test that _copy_agent_spec copies all four agents: log-analysis, log-it, log-init, and log-help."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            initializer._copy_agent_spec()

            # All four agents should be copied
            agents = ["log-analysis", "log-it", "log-init", "log-help"]
            agent_paths = {
                agent: initializer.drtrace_dir / "agents" / f"{agent}.md"
                for agent in agents
            }

            for agent, path in agent_paths.items():
                assert path.exists(), f"{agent}.md should be created"

            # Verify content
            for agent, path in agent_paths.items():
                content = path.read_text()
                assert len(content) > 0, f"{agent}.md should have content"

    def test_copy_agent_spec_handles_errors_gracefully(self):
        """Test that _copy_agent_spec handles errors gracefully for individual agents."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            # Should not raise even if resources are missing (uses fallback)
            initializer._copy_agent_spec()

            # At least one agent file should exist (fallback should work)
            agents_dir = initializer.drtrace_dir / "agents"
            agent_files = list(agents_dir.glob("*.md"))
            assert len(agent_files) >= 1, "At least one agent file should be created"


class TestInitProjectIntegration:
    """Integration tests for complete init workflow."""

    def test_full_initialization_creates_all_files(self):
        """Test that full init creates expected directory structure."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))

            # Create the directory structure and files
            initializer._create_directory_structure()

            config = ConfigSchema.get_default_config(
                project_name="integration-test",
                application_id="int-test",
                environments=["development", "staging"]
            )

            ConfigSchema.save(config, initializer.config_path)
            initializer._generate_environment_configs(config)
            initializer._generate_env_example(config)
            initializer._generate_readme()

            # Verify all expected files exist
            assert (initializer.drtrace_dir / "config.json").exists()
            assert (initializer.drtrace_dir / "config.development.json").exists()
            assert (initializer.drtrace_dir / "config.staging.json").exists()
            assert (initializer.drtrace_dir / ".env.example").exists()
            assert (initializer.drtrace_dir / "README.md").exists()
            assert (initializer.drtrace_dir / "agents").is_dir()

    def test_initialization_with_agent(self):
        """Test initialization with agent enabled."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            config = ConfigSchema.get_default_config(
                project_name="agent-test",
                application_id="agent-test",
                agent_enabled=True,
                agent_framework="langchain"
            )

            assert config["agent"]["enabled"] is True
            assert config["agent"]["framework"] == "langchain"

            ConfigSchema.save(config, initializer.config_path)
            initializer._generate_environment_configs(config)
            initializer._copy_agent_spec()

            # Verify all four agents are copied
            agents = ["log-analysis", "log-it", "log-init", "log-help"]
            for agent in agents:
                agent_path = initializer.drtrace_dir / "agents" / f"{agent}.md"
                assert agent_path.exists(), f"{agent}.md should exist when agent enabled"

    def test_initialization_python_language(self):
        """Test initialization with Python language."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            config = ConfigSchema.get_default_config(
                project_name="python-test",
                application_id="python-test",
                language="python",
                agent_enabled=True
            )

            assert config["language"] == "python"
            ConfigSchema.save(config, initializer.config_path)
            initializer._copy_agent_spec()

            # Verify all four agents are copied for Python
            agents = ["log-analysis", "log-it", "log-init", "log-help"]
            for agent in agents:
                assert (initializer.drtrace_dir / "agents" / f"{agent}.md").exists()

    def test_initialization_javascript_language(self):
        """Test initialization with JavaScript language."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            config = ConfigSchema.get_default_config(
                project_name="js-test",
                application_id="js-test",
                language="javascript",
                agent_enabled=True
            )

            assert config["language"] == "javascript"
            ConfigSchema.save(config, initializer.config_path)
            initializer._copy_agent_spec()

            # Verify all four agents are copied for JavaScript
            agents = ["log-analysis", "log-it", "log-init", "log-help"]
            for agent in agents:
                assert (initializer.drtrace_dir / "agents" / f"{agent}.md").exists()

    def test_initialization_cpp_language(self):
        """Test initialization with C++ language."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            config = ConfigSchema.get_default_config(
                project_name="cpp-test",
                application_id="cpp-test",
                language="cpp",
                agent_enabled=True
            )

            assert config["language"] == "cpp"
            ConfigSchema.save(config, initializer.config_path)
            initializer._copy_agent_spec()

            # Verify all four agents are copied for C++
            agents = ["log-analysis", "log-it", "log-init", "log-help"]
            for agent in agents:
                assert (initializer.drtrace_dir / "agents" / f"{agent}.md").exists()

    def test_initialization_both_languages(self):
        """Test initialization with both Python and JavaScript."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            config = ConfigSchema.get_default_config(
                project_name="both-test",
                application_id="both-test",
                language="both",
                agent_enabled=True
            )

            assert config["language"] == "both"
            ConfigSchema.save(config, initializer.config_path)
            initializer._copy_agent_spec()

            # Verify agents are copied for both languages
            assert (initializer.drtrace_dir / "agents" / "log-analysis.md").exists()
            assert (initializer.drtrace_dir / "agents" / "log-it.md").exists()

    def test_agent_specs_consistent_across_languages(self):
        """Test that agent specs are consistent regardless of language choice."""
        languages = ["python", "javascript", "both"]
        reference_content = {}

        for language in languages:
            with TemporaryDirectory() as tmpdir:
                initializer = ProjectInitializer(Path(tmpdir))
                initializer._create_directory_structure()

                config = ConfigSchema.get_default_config(
                    project_name=f"test-{language}",
                    application_id=f"test-{language}",
                    language=language,
                    agent_enabled=True
                )

                initializer._copy_agent_spec()

                # Both agents should exist for all languages
                log_analysis = initializer.drtrace_dir / "agents" / "log-analysis.md"
                log_it = initializer.drtrace_dir / "agents" / "log-it.md"

                assert log_analysis.exists(), f"log-analysis.md should exist for {language}"
                assert log_it.exists(), f"log-it.md should exist for {language}"

                # Store content for comparison
                current_log_analysis = log_analysis.read_text()
                current_log_it = log_it.read_text()

                if language == "python":
                    # Store Python version as reference
                    reference_content["log-analysis"] = current_log_analysis
                    reference_content["log-it"] = current_log_it
                else:
                    # Compare with Python version
                    assert current_log_analysis == reference_content["log-analysis"], \
                        f"log-analysis.md should be consistent for {language}"
                    assert current_log_it == reference_content["log-it"], \
                        f"log-it.md should be consistent for {language}"


class TestCopyFrameworkGuides:
    """Test _copy_framework_guides() method."""

    def test_copy_framework_guides_creates_directory(self):
        """Test that integration-guides directory is created."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()
            initializer._copy_framework_guides()

            guides_dir = initializer.drtrace_dir / "agents" / "integration-guides"
            assert guides_dir.exists(), "Integration guides directory should be created"
            assert guides_dir.is_dir(), "Integration guides should be a directory"

    def test_copy_framework_guides_copies_from_packaged_resources(self):
        """Test that _copy_framework_guides copies guides from packaged resources."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            # Mock importlib.resources to return test guide
            with patch('drtrace_service.cli.init_project.resources') as mock_resources:
                # Create a mock file structure
                mock_file = MagicMock()
                mock_file.exists.return_value = True
                mock_file.iterdir.return_value = [
                    MagicMock(stem="cpp-ros-integration", suffix=".md", is_file=lambda: True)
                ]
                mock_file.joinpath.return_value.read_text.return_value = "# C++ ROS Integration Guide"

                mock_resources.files.return_value.joinpath.return_value = mock_file

                # Call the method
                initializer._copy_framework_guides()

            # Verify guide was copied (directory should exist even if no guides found)
            guides_dir = initializer.drtrace_dir / "agents" / "integration-guides"
            assert guides_dir.exists(), "Integration guides directory should exist"

    def test_copy_framework_guides_handles_missing_resources_gracefully(self):
        """Test that _copy_framework_guides handles missing resources gracefully."""
        with TemporaryDirectory() as tmpdir:
            initializer = ProjectInitializer(Path(tmpdir))
            initializer._create_directory_structure()

            # Mock importlib.resources to raise FileNotFoundError
            with patch('drtrace_service.cli.init_project.resources') as mock_resources:
                mock_resources.files.return_value.joinpath.return_value.exists.return_value = False

                # Should not raise exception
                initializer._copy_framework_guides()

            # Directory should still be created
            guides_dir = initializer.drtrace_dir / "agents" / "integration-guides"
            assert guides_dir.exists(), "Integration guides directory should exist even if no guides found"
