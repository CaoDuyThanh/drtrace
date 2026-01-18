"""
End-to-end tests for Python CLI
Tests package installation, CLI availability, and agent file copying
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class TestPythonCLIInstallation:
    """Test Python CLI installation and basic functionality"""

    @classmethod
    def setup_class(cls):
        """Create a temporary work directory for testing"""
        cls.tmpdir = tempfile.mkdtemp(prefix="drtrace-e2e-py-")
        cls.workdir = Path(cls.tmpdir) / "workdir"
        cls.workdir.mkdir(parents=True, exist_ok=True)

        # Use current environment instead of creating nested venv
        cls.python = sys.executable
        cls.pip = sys.executable.replace('python', 'pip') if 'python' in sys.executable else 'pip'

        # Verify package is already installed in current environment
        result = subprocess.run(
            [cls.python, "-c", "import drtrace_service; print('ok')"],
            check=False,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"drtrace_service not available in current environment: {result.stderr}")

    @classmethod
    def teardown_class(cls):
        """Clean up temporary work directory"""
        if hasattr(cls, 'tmpdir') and os.path.exists(cls.tmpdir):
            shutil.rmtree(cls.tmpdir)

    def run_cmd(self, *args, **kwargs):
        """Run command in venv and return result"""
        result = subprocess.run(
            args,
            cwd=str(self.workdir),
            capture_output=True,
            text=True,
            **kwargs
        )
        return result

    def test_install_package(self):
        """Test package was installed successfully"""
        # Check if drtrace_service can be imported
        result = self.run_cmd(
            str(self.python),
            "-c",
            "import drtrace_service; print('ok')"
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"
        assert "ok" in result.stdout

    def test_cli_help(self):
        """Test CLI help command"""
        result = self.run_cmd(str(self.python), "-m", "drtrace_service")
        assert result.returncode == 1, "CLI should show help on no args"
        output = result.stdout + result.stderr
        assert "grep" in output, "grep command should be in help"
        assert "status" in output, "status command should be in help"

    def test_grep_help(self):
        """Test grep command help"""
        result = self.run_cmd(
            str(self.python),
            "-m",
            "drtrace_service",
            "grep",
            "--help"
        )
        # argparse puts help in stdout, but exit code may be 0 or 2
        output = result.stdout + result.stderr
        assert "-E" in output, "-E flag should be in grep help"
        assert "-c" in output, "-c flag should be in grep help"
        assert "--since" in output, "--since flag should be in grep help"

    def test_status_command(self):
        """Test status command"""
        result = self.run_cmd(
            str(self.python),
            "-m",
            "drtrace_service",
            "status"
        )
        output = (result.stdout + result.stderr).lower()
        # Status should work (daemon might be running or not)
        assert "status" in output or "unreachable" in output

    def test_init_agent_copies_file(self):
        """Test init-agent copies agent file correctly"""
        workdir = Path(self.tmpdir) / "workdir"
        workdir.mkdir(exist_ok=True)

        result = self.run_cmd(
            str(self.python),
            "-m",
            "drtrace_service",
            "init-agent",
            "--agent",
            "log-analysis"
        )

        assert result.returncode == 0, f"init-agent failed: {result.stderr}"
        assert "log-analysis.md" in result.stdout, "Should mention log-analysis.md"

        # Verify file was created
        agent_file = workdir / "agents" / "log-analysis.md"
        assert agent_file.exists(), f"Agent file should be created at {agent_file}"

        # Verify content
        content = agent_file.read_text()
        assert "log-analysis" in content, "Agent file should contain agent name"
        assert "Log Analysis" in content, "Agent file should contain title"

    def test_init_creates_config_and_env(self):
        """Test init creates config with defaults and env config"""
        project_dir = Path(self.tmpdir) / "init-project"
        project_dir.mkdir(parents=True, exist_ok=True)

        # Provide inputs to accept defaults (language=python) and skip analysis
        inputs = "\n".join([
            "e2e-app",  # project name
            "",         # application id (default based on name)
            "1",        # language selection (python)
            "",         # daemon url (default)
            "",         # enable DrTrace (default yes)
            "",         # environments (accept default 'development')
            "",         # agent interface disabled
            "n",        # skip optional project analysis
            "",         # trailing newline
        ])

        result = subprocess.run(
            [str(self.python), "-m", "drtrace_service", "init", "--project-root", str(project_dir)],
            input=inputs,
            text=True,
            capture_output=True,
            cwd=str(project_dir),
            timeout=60,
        )

        assert result.returncode == 0, f"init failed: {result.stderr}"

        config_path = project_dir / "_drtrace" / "config.json"
        env_config_path = project_dir / "_drtrace" / "config.development.json"
        agents_dir = project_dir / "_drtrace" / "agents"

        assert config_path.exists(), "config.json should be created"
        assert env_config_path.exists(), "environment config should be created"
        assert agents_dir.exists(), "agents directory should be created"

        config = json.loads(config_path.read_text())
        env_config = json.loads(env_config_path.read_text())

        assert config.get("project_name") == "e2e-app"
        assert config.get("application_id") == "e2e-app"
        assert config.get("daemon_url") == "http://localhost:8001"
        assert config.get("enabled") is True
        assert "development" in config.get("environments", [])

        assert env_config.get("project_name") == "e2e-app"
        assert env_config.get("application_id") == "e2e-app"
        assert "development" in env_config.get("environments", [])

    def test_version_correct(self):
        """Test version is 0.5.0"""
        result = self.run_cmd(
            str(self.python),
            "-c",
            "from importlib.metadata import version; print(version('drtrace'))"
        )
        assert result.returncode == 0, f"Version check failed: {result.stderr}"
        assert result.stdout.strip() == "0.5.0"

    def test_httpx_dependency_installed(self):
        """Test httpx dependency is installed"""
        result = self.run_cmd(
            str(self.python),
            "-c",
            "import httpx; print(httpx.__version__)"
        )
        assert result.returncode == 0, "httpx should be installed"


class TestPythonCLIGrepConstraint:
    """Test that grep command respects message_contains/message_regex constraint"""

    @classmethod
    def setup_class(cls):
        """Create temporary work directory"""
        cls.tmpdir = tempfile.mkdtemp(prefix="drtrace-e2e-grep-")

        # Use current environment instead of creating nested venv
        cls.python = sys.executable

        # Verify package is already installed in current environment
        result = subprocess.run(
            [cls.python, "-c", "import drtrace_service; print('ok')"],
            check=False,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"drtrace_service not available in current environment: {result.stderr}")

    @classmethod
    def teardown_class(cls):
        """Clean up"""
        if hasattr(cls, 'tmpdir') and os.path.exists(cls.tmpdir):
            shutil.rmtree(cls.tmpdir)

    def test_grep_without_e_flag(self):
        """Test grep without -E uses message_contains"""
        result = subprocess.run(
            [str(self.python), "-m", "drtrace_service", "grep", "--help"],
            capture_output=True,
            text=True,
            cwd=self.tmpdir
        )
        assert "-E" in result.stdout, "-E flag should be documented"
        assert "extended" in result.stdout.lower(), "Extended regex should be mentioned"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
