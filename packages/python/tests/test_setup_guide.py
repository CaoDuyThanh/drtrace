"""
Unit tests for setup_guide module.
"""

from pathlib import Path
import json

from drtrace_service.setup_guide import (
    SetupStep,
    check_step_complete,
    get_current_step,
    get_next_step,
    get_setup_steps,
    update_progress,
)


def test_get_setup_steps_python():
    steps = get_setup_steps("python")
    assert len(steps) >= 7
    assert all(step.language == "python" for step in steps)
    assert steps[0].step_number == 1


def test_get_setup_steps_cpp():
    steps = get_setup_steps("cpp")
    assert len(steps) >= 7
    assert all(step.language == "cpp" for step in steps)


def test_get_setup_steps_js():
    steps = get_setup_steps("javascript")
    assert len(steps) >= 7
    assert all(step.language == "javascript" for step in steps)


def test_get_setup_steps_unknown_language():
    steps = get_setup_steps("ruby")
    assert steps == []


def test_check_step_complete_handles_exceptions(tmp_path: Path):
    def bad_verification(root: Path) -> bool:
        raise RuntimeError("boom")

    step = SetupStep(
        step_number=1,
        title="Bad step",
        description="",
        instructions=[],
        verification=bad_verification,
        language="python",
        required=True,
        estimated_time="1 minute",
    )

    assert check_step_complete(step, tmp_path) is False


def test_get_current_step_defaults_to_first_step(tmp_path: Path):
    step = get_current_step(tmp_path, "python")
    assert step is not None
    assert step.step_number == 1


def test_update_progress_and_get_current_step(tmp_path: Path):
    # initial: should be step 1
    first = get_current_step(tmp_path, "python")
    assert first is not None
    assert first.step_number == 1

    # mark step 1 as completed
    update_progress(tmp_path, "python", completed_step=1)

    # now current_step should be 2
    second = get_current_step(tmp_path, "python")
    assert second is not None
    assert second.step_number == 2


def test_get_next_step_sequence():
    next_step = get_next_step(1, "python")
    assert next_step is not None
    assert next_step.step_number == 2

    # last step should have no next step
    steps = get_setup_steps("python")
    last = steps[-1].step_number
    assert get_next_step(last, "python") is None


def test_progress_persistence_to_config_file(tmp_path: Path):
    """update_progress should write setup progress into _drtrace/config.json."""
    project_root = tmp_path
    # mark a couple of steps
    update_progress(project_root, "python", completed_step=1)
    update_progress(project_root, "python", completed_step=2)

    cfg_path = project_root / "_drtrace" / "config.json"
    assert cfg_path.exists()

    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "setup" in data
    setup = data["setup"]
    assert setup.get("current_step") == 3
    assert setup.get("language") == "python"
    assert setup.get("completed_steps") == [1, 2]


def test_resume_from_incomplete_setup(tmp_path: Path):
    """get_current_step should resume from stored current_step in config."""
    project_root = tmp_path

    # Simulate stored progress: current_step = 3
    cfg_dir = project_root / "_drtrace"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "config.json"
    cfg_path.write_text(
        '{"setup": {"completed_steps": [1, 2], "current_step": 3, "language": "python"}}',
        encoding="utf-8",
    )

    current = get_current_step(project_root, "python")
    assert current is not None
    assert current.step_number == 3


