"""
Help Agent Interface Handler

Provides async functions for the log-help agent to drive the step-by-step
setup guide using the setup_guide module.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from .setup_guide import (
    SetupStep,
    check_step_complete,
    get_setup_steps,
    update_progress,
)
from .setup_guide import (
    get_current_step as guide_get_current_step,
)
from .setup_guide import (
    get_next_step as guide_get_next_step,
)


def _format_step(step: SetupStep, total_steps: int, completed_steps: List[int]) -> List[str]:
    """Format a single step section as markdown lines."""
    lines: List[str] = []
    lines.append(f"# Setup Guide: {step.language.capitalize()}")
    lines.append("")
    lines.append(f"## Progress: Step {step.step_number} of {total_steps}")
    lines.append("")
    lines.append(f"### Current Step: {step.title}")
    lines.append("")
    lines.append(f"**Description**: {step.description}")
    lines.append("")
    lines.append("**Instructions**:")
    for idx, instr in enumerate(step.instructions, start=1):
        lines.append(f"{idx}. {instr}")
    lines.append("")
    return lines


def _format_completed_steps(all_steps: List[SetupStep], completed_steps: List[int], current_step: int) -> List[str]:
    lines: List[str] = []
    lines.append("## Completed Steps")
    for step in all_steps:
        prefix = "[✓]" if step.step_number in completed_steps else "[ ]"
        suffix = " (current)" if step.step_number == current_step else ""
        lines.append(f"- {prefix} Step {step.step_number}: {step.title}{suffix}")
    lines.append("")
    return lines


async def start_setup_guide(language: str, project_root: Path) -> str:
    """
    Start step-by-step setup guide for a given language.
    """
    project_root = Path(project_root)
    steps = get_setup_steps(language)
    if not steps:
        return f"❌ **Error**: Unsupported language `{language}` for setup guide."

    # Initialize progress (set current_step to 1)
    update_progress(project_root, language, completed_step=0)

    step = steps[0]
    total = len(steps)
    completed: List[int] = []

    lines = _format_step(step, total, completed)
    lines.append("---")
    lines.extend(_format_completed_steps(steps, completed, current_step=1))

    return "\n".join(lines)


async def get_current_step(project_root: Path) -> str:
    """
    Get current step information for the active language in the project.
    """
    project_root = Path(project_root)
    # Default to python if language not yet set; guide_get_current_step uses config
    current_step = guide_get_current_step(project_root, "python")
    if current_step is None:
        return "# Setup Guide\n\nNo setup steps available for this project."

    language = current_step.language
    steps = get_setup_steps(language)
    total = len(steps)

    # Determine completed steps from config via a dummy update of step 0 (no-op)
    # and reload config through get_current_step logic
    # Simpler: inspect config file directly would require exposing helpers; keep high-level for now.
    completed: List[int] = []  # High-level interface does not expose detailed completion list yet

    lines = _format_step(current_step, total, completed)
    lines.append("---")
    lines.extend(_format_completed_steps(steps, completed, current_step=current_step.step_number))

    return "\n".join(lines)


async def complete_step(step_number: int, project_root: Path) -> str:
    """
    Mark a step as complete and return next step (if any).
    """
    project_root = Path(project_root)
    # Use current language from config by asking for current step first
    current = guide_get_current_step(project_root, "python")
    if current is None:
        return "❌ **Error**: No active setup guide. Start one with `start_setup_guide`."

    language = current.language
    steps = get_setup_steps(language)
    step_map = {s.step_number: s for s in steps}

    step = step_map.get(step_number)
    if not step:
        return f"❌ **Error**: Step {step_number} not found for language `{language}`."

    # Verify completion
    ok = check_step_complete(step, project_root)
    if not ok:
        return f"❌ **Step {step_number} not complete**.\n\nPlease follow the instructions and try again."

    # Update progress
    update_progress(project_root, language, completed_step=step_number)

    next_step = guide_get_next_step(step_number, language)
    lines: List[str] = []
    lines.append(f"✅ **Step {step_number} completed**: {step.title}")
    lines.append("")

    if next_step:
        total = len(steps)
        lines.append("")
        lines.append("### Next Step")
        lines.append("")
        lines.extend(_format_step(next_step, total, completed_steps=[]))
    else:
        lines.append("🎉 **All setup steps completed for this language!**")

    return "\n".join(lines)


async def troubleshoot(issue: str, project_root: Path) -> str:
    """
    Provide troubleshooting guidance for a common issue.

    Uses simple pattern matching to detect issue type.
    """
    text = issue.lower()

    if "daemon" in text or "connect" in text:
        return (
            "# Troubleshooting: Daemon Not Connecting\n\n"
            "1. Ensure the daemon is running (Docker Compose or native Python).\n"
            "2. Verify `DRTRACE_DAEMON_HOST` and `DRTRACE_DAEMON_PORT` in your environment or config.\n"
            "3. Run `python -m drtrace_service status` to confirm connectivity.\n"
        )
    if "import" in text:
        return (
            "# Troubleshooting: Import Errors\n\n"
            "1. Verify the DrTrace package is installed in your current environment.\n"
            "2. Check that your virtual environment is activated.\n"
            "3. Confirm that `PYTHONPATH` includes your project if needed.\n"
        )
    if "config" in text:
        return (
            "# Troubleshooting: Configuration Issues\n\n"
            "1. Ensure `_drtrace/config.json` exists and is valid JSON.\n"
            "2. Verify `application_id`, daemon host/port, and environment fields.\n"
            "3. Re-run `init-project` or `drtrace init` if needed.\n"
        )
    if "log" in text:
        return (
            "# Troubleshooting: Logs Not Appearing\n\n"
            "1. Confirm logging setup is called early in application startup.\n"
            "2. Check daemon connectivity and configuration.\n"
            "3. Use DrTrace query/analysis commands to verify ingestion.\n"
        )

    return (
        "# Troubleshooting\n\n"
        "I could not recognize this issue from common patterns.\n"
        "Please check daemon status, configuration, and installation, or provide more details."
    )


