"""
Unit tests for help_agent_interface module.
"""

from pathlib import Path

import pytest

from drtrace_service import help_agent_interface
from drtrace_service.setup_guide import update_progress


@pytest.mark.asyncio
async def test_start_setup_guide_python(tmp_path: Path):
    result = await help_agent_interface.start_setup_guide("python", tmp_path)
    assert "# Setup Guide: Python" in result
    assert "Progress: Step 1 of" in result


@pytest.mark.asyncio
async def test_start_setup_guide_unsupported(tmp_path: Path):
    result = await help_agent_interface.start_setup_guide("ruby", tmp_path)
    assert "Unsupported language" in result


@pytest.mark.asyncio
async def test_get_current_step_no_progress(tmp_path: Path):
    # Without prior progress, should fall back to first Python step
    result = await help_agent_interface.get_current_step(tmp_path)
    assert "# Setup Guide" in result


@pytest.mark.asyncio
async def test_complete_step_success(tmp_path: Path):
    # Initialize guide
    await help_agent_interface.start_setup_guide("python", tmp_path)

    # Step 1 verifies presence of requirements.txt or pyproject.toml
    (tmp_path / "requirements.txt").write_text("drtrace\n")

    result = await help_agent_interface.complete_step(1, tmp_path)
    assert "Step 1 completed" in result


@pytest.mark.asyncio
async def test_complete_step_invalid(tmp_path: Path):
    await help_agent_interface.start_setup_guide("python", tmp_path)

    result = await help_agent_interface.complete_step(99, tmp_path)
    assert "Step 99 not found" in result


@pytest.mark.asyncio
async def test_troubleshoot_daemon_issue(tmp_path: Path):
    result = await help_agent_interface.troubleshoot("daemon not connecting", tmp_path)
    assert "Daemon Not Connecting" in result


@pytest.mark.asyncio
async def test_troubleshoot_unknown_issue(tmp_path: Path):
    result = await help_agent_interface.troubleshoot("some random problem", tmp_path)
    assert "Troubleshooting" in result
    assert "could not recognize this issue" in result.lower()


