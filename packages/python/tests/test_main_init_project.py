"""
Integration test for init command in __main__.py

Note: The command was renamed from "init-project" to "init" for brevity.
"""

from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest

from drtrace_service.__main__ import main


class TestInitProjectCommand:
    """Test init command integration."""

    def test_init_help_message(self, capsys):
        """Test that init command appears in help."""
        with pytest.raises(SystemExit):
            main([])

        captured = capsys.readouterr()
        # Command is "init" (not "init-project")
        assert "init" in captured.err
        assert "Interactive project initialization" in captured.err

    def test_init_command_exists(self):
        """Test that init command can be called."""
        with TemporaryDirectory() as tmpdir:
            # Mock the interactive input to skip prompts
            with patch("builtins.input") as mock_input:
                mock_input.side_effect = KeyboardInterrupt()

                with pytest.raises(SystemExit) as exc:
                    main(["init", "--project-root", tmpdir])

                # Should exit with code 1 due to KeyboardInterrupt
                assert exc.value.code == 1

    def test_usage_message_shows_init(self, capsys):
        """Test that usage message includes init command."""
        with pytest.raises(SystemExit):
            main(["invalid-command"])

        captured = capsys.readouterr()
        # Command is "init" (not "init-project")
        assert "init" in captured.err.lower()
