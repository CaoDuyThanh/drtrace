"""
Setup Guide Manager

Defines language-specific setup steps and basic progress tracking helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

import json


@dataclass
class SetupStep:
    step_number: int
    title: str
    description: str
    instructions: List[str]
    verification: Callable[[Path], bool]
    language: str
    required: bool
    estimated_time: str  # e.g., "2 minutes"


def _python_steps() -> List[SetupStep]:
    def _verify_install(project_root: Path) -> bool:
        # Minimal check: look for any Python env or requirements; real check would try import
        return (project_root / "requirements.txt").exists() or (project_root / "pyproject.toml").exists()

    def _verify_init_project(project_root: Path) -> bool:
        return (project_root / "_drtrace" / "config.json").exists()

    def _verify_config_review(project_root: Path) -> bool:
        cfg = project_root / "_drtrace" / "config.json"
        return cfg.exists()

    def _verify_logging_added(project_root: Path) -> bool:
        # Simple heuristic: search for setup_logging usage
        for py_file in project_root.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            if "setup_logging" in text:
                return True
        return False

    def _verify_generic(project_root: Path) -> bool:
        # For now, treat as manual/assumed complete
        return True

    return [
        SetupStep(
            step_number=1,
            title="Install DrTrace package",
            description="Install the Python DrTrace service package via pip.",
            instructions=["Run `pip install drtrace` in your virtual environment."],
            verification=_verify_install,
            language="python",
            required=True,
            estimated_time="2 minutes",
        ),
        SetupStep(
            step_number=2,
            title="Run init-project command",
            description="Initialize project configuration using the DrTrace CLI.",
            instructions=["Run `python -m drtrace_service init-project` in your project root."],
            verification=_verify_init_project,
            language="python",
            required=True,
            estimated_time="3 minutes",
        ),
        SetupStep(
            step_number=3,
            title="Review generated configuration",
            description="Review and adjust `_drtrace/config.json` as needed.",
            instructions=["Open `_drtrace/config.json` and verify application_id, daemon host/port, and environment."],
            verification=_verify_config_review,
            language="python",
            required=True,
            estimated_time="3 minutes",
        ),
        SetupStep(
            step_number=4,
            title="Add logging setup to main application file",
            description="Wire `setup_logging()` into your main entry point.",
            instructions=[
                "Identify your main entry file (e.g., `main.py`, `app.py`).",
                "Add `setup_logging()` with appropriate application_id and service_name.",
            ],
            verification=_verify_logging_added,
            language="python",
            required=True,
            estimated_time="5 minutes",
        ),
        SetupStep(
            step_number=5,
            title="Test logging integration",
            description="Run the application and ensure logs are produced.",
            instructions=["Run your application and confirm logs appear in the console or log files."],
            verification=_verify_generic,
            language="python",
            required=True,
            estimated_time="5 minutes",
        ),
        SetupStep(
            step_number=6,
            title="Verify daemon connectivity",
            description="Ensure the DrTrace daemon is reachable.",
            instructions=[
                "Run `python -m drtrace_service status`.",
                "If not available, start the daemon (Docker Compose or native Python).",
            ],
            verification=_verify_generic,
            language="python",
            required=True,
            estimated_time="3 minutes",
        ),
        SetupStep(
            step_number=7,
            title="Test log ingestion",
            description="Emit test logs and verify they reach DrTrace.",
            instructions=[
                "Trigger a few log messages in your app.",
                "Use `python -m drtrace_service query --since 5m` to verify logs are ingested.",
            ],
            verification=_verify_generic,
            language="python",
            required=True,
            estimated_time="5 minutes",
        ),
    ]


def _cpp_steps() -> List[SetupStep]:
    def _verify_generic(project_root: Path) -> bool:
        return True

    return [
        SetupStep(
            step_number=1,
            title="Install DrTrace C++ client via FetchContent",
            description=(
                "Add FetchContent block for DrTrace C++ client to your CMakeLists.txt. "
                "Note: spdlog (v1.13.0) is handled automatically by drtrace_cpp_client; "
                "you only need to ensure libcurl is installed system-wide."
            ),
            instructions=[
                "Install libcurl system-wide (Ubuntu/Debian: `sudo apt-get install libcurl4-openssl-dev`, "
                "macOS: usually pre-installed, Windows: use vcpkg or curl.se).",
                "Open your project's root `CMakeLists.txt`.",
                "Add FetchContent block for `drtrace` as described in the docs.",
                "You do NOT need a separate FetchContent block for spdlog – it is pulled in by drtrace_cpp_client.",
            ],
            verification=lambda root: (root / "CMakeLists.txt").exists(),
            language="cpp",
            required=True,
            estimated_time="5 minutes",
        ),
        SetupStep(
            step_number=2,
            title="Update CMakeLists.txt targets",
            description="Link `drtrace_cpp_client` to your executable/library target.",
            instructions=[
                "Add `target_link_libraries(your_target PRIVATE drtrace_cpp_client)` for your target.",
            ],
            verification=_verify_generic,
            language="cpp",
            required=True,
            estimated_time="5 minutes",
        ),
        SetupStep(
            step_number=3,
            title="Include drtrace_sink.hpp in code",
            description="Include the DrTrace sink header in your main C++ file.",
            instructions=[
                "In `main.cpp` or your app entry, add `#include \"drtrace_sink.hpp\"` and spdlog integration.",
            ],
            verification=_verify_generic,
            language="cpp",
            required=True,
            estimated_time="5 minutes",
        ),
        SetupStep(
            step_number=4,
            title="Configure spdlog with DrTrace sink",
            description="Attach the DrTrace sink to the default spdlog logger.",
            instructions=[
                "Use `drtrace::create_drtrace_logger()` helper function or create a `drtrace::DrtraceSink_mt` instance and push it into `spdlog::default_logger()->sinks()`.",
            ],
            verification=_verify_generic,
            language="cpp",
            required=True,
            estimated_time="5 minutes",
        ),
        SetupStep(
            step_number=5,
            title="Test logging integration",
            description="Build and run your C++ application to ensure logs are emitted.",
            instructions=[
                "Run `cmake -B build -S . && cmake --build build`.",
                "Run your binary and ensure logs are printed.",
            ],
            verification=_verify_generic,
            language="cpp",
            required=True,
            estimated_time="10 minutes",
        ),
        SetupStep(
            step_number=6,
            title="Verify daemon connectivity",
            description="Ensure the DrTrace daemon is reachable from your C++ app.",
            instructions=[
                "Confirm daemon is running and reachable at the configured host/port.",
            ],
            verification=_verify_generic,
            language="cpp",
            required=True,
            estimated_time="3 minutes",
        ),
        SetupStep(
            step_number=7,
            title="Test log ingestion",
            description="Emit test logs and verify they appear in DrTrace.",
            instructions=[
                "Trigger log messages from your C++ application.",
                "Use DrTrace CLI to query logs and confirm ingestion.",
            ],
            verification=_verify_generic,
            language="cpp",
            required=True,
            estimated_time="5 minutes",
        ),
    ]


def _js_steps() -> List[SetupStep]:
    def _verify_install(project_root: Path) -> bool:
        return (project_root / "package.json").exists()

    def _verify_init(project_root: Path) -> bool:
        return (project_root / "_drtrace" / "config.json").exists()

    def _verify_generic(project_root: Path) -> bool:
        return True

    return [
        SetupStep(
            step_number=1,
            title="Install DrTrace package",
            description="Install the DrTrace JS/TS client.",
            instructions=[
                "Run `npm install drtrace` or the appropriate command for your package manager.",
            ],
            verification=_verify_install,
            language="javascript",
            required=True,
            estimated_time="2 minutes",
        ),
        SetupStep(
            step_number=2,
            title="Run drtrace init command",
            description="Generate DrTrace configuration using the JS CLI.",
            instructions=[
                "Run `npx drtrace init` in your project root.",
            ],
            verification=_verify_init,
            language="javascript",
            required=True,
            estimated_time="3 minutes",
        ),
        SetupStep(
            step_number=3,
            title="Review generated configuration",
            description="Review and adjust `_drtrace/config.json` and `.env.example`.",
            instructions=[
                "Open `_drtrace/config.json` and ensure settings match your environment.",
            ],
            verification=_verify_init,
            language="javascript",
            required=True,
            estimated_time="3 minutes",
        ),
        SetupStep(
            step_number=4,
            title="Initialize logger in application",
            description="Wire DrTrace client initialization into your JS/TS entry point.",
            instructions=[
                "In `main.ts` or `index.js`, initialize DrTrace client with applicationId and daemonUrl.",
            ],
            verification=_verify_generic,
            language="javascript",
            required=True,
            estimated_time="5 minutes",
        ),
        SetupStep(
            step_number=5,
            title="Test logging integration",
            description="Run your app and ensure logs are captured.",
            instructions=[
                "Run your app and generate logs via console.log / logger.",
            ],
            verification=_verify_generic,
            language="javascript",
            required=True,
            estimated_time="5 minutes",
        ),
        SetupStep(
            step_number=6,
            title="Verify daemon connectivity",
            description="Ensure the DrTrace daemon is reachable.",
            instructions=[
                "Confirm the daemon is running and reachable at the configured host/port.",
            ],
            verification=_verify_generic,
            language="javascript",
            required=True,
            estimated_time="3 minutes",
        ),
        SetupStep(
            step_number=7,
            title="Test log ingestion",
            description="Emit test logs and confirm ingestion.",
            instructions=[
                "Trigger test logs and use DrTrace tools to verify they are received.",
            ],
            verification=_verify_generic,
            language="javascript",
            required=True,
            estimated_time="5 minutes",
        ),
    ]


def get_setup_steps(language: str) -> List[SetupStep]:
    """Get ordered setup steps for a given language."""
    lang = language.lower()
    if lang == "python":
        return _python_steps()
    if lang in ("cpp", "c++"):
        return _cpp_steps()
    if lang in ("javascript", "typescript", "js", "ts"):
        return _js_steps()
    return []


def check_step_complete(step: SetupStep, project_root: Path) -> bool:
    """Call the step's verification function, handling errors gracefully."""
    try:
        return bool(step.verification(Path(project_root)))
    except Exception:
        return False


def _load_config(project_root: Path) -> Dict:
    cfg_path = project_root / "_drtrace" / "config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_config(project_root: Path, data: Dict) -> None:
    cfg_dir = project_root / "_drtrace"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "config.json"
    cfg_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def get_current_step(project_root: Path, language: str) -> Optional[SetupStep]:
    """Get the current step for a language based on stored progress."""
    project_root = Path(project_root)
    cfg = _load_config(project_root)
    setup = cfg.get("setup", {})
    lang = language.lower()
    steps = get_setup_steps(lang)
    if not steps:
        return None

    current_num = setup.get("current_step")
    if not current_num:
        return steps[0]

    for step in steps:
        if step.step_number == current_num:
            return step
    return steps[0]


def get_next_step(current_step: int, language: str) -> Optional[SetupStep]:
    """Get next step in setup process for a given language."""
    steps = get_setup_steps(language)
    for step in steps:
        if step.step_number == current_step + 1:
            return step
    return None


def update_progress(project_root: Path, language: str, completed_step: int) -> None:
    """Mark a step as completed and update current_step in config."""
    project_root = Path(project_root)
    cfg = _load_config(project_root)
    setup = cfg.get("setup", {})
    completed = set(setup.get("completed_steps", []))
    completed.add(completed_step)
    setup["completed_steps"] = sorted(completed)
    setup["current_step"] = completed_step + 1
    setup["language"] = language.lower()
    cfg["setup"] = setup
    _save_config(project_root, cfg)


