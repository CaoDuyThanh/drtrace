"""
Unit tests for setup_agent_interface module.
"""

from pathlib import Path

import pytest

from drtrace_service import setup_agent_interface


@pytest.mark.asyncio
async def test_analyze_and_suggest_empty_project(tmp_path: Path):
    """analyze_and_suggest should return helpful message when no languages detected."""
    project_root = tmp_path

    result = await setup_agent_interface.analyze_and_suggest(project_root)

    assert "Setup Suggestions" in result
    assert "No supported languages detected" in result


@pytest.mark.asyncio
async def test_analyze_and_suggest_python_project(tmp_path: Path):
    """analyze_and_suggest should include Python section for Python projects."""
    project_root = tmp_path
    (project_root / "main.py").write_text("print('hello')\n")

    result = await setup_agent_interface.analyze_and_suggest(project_root)

    assert "# Setup Suggestions for Python" in result
    assert "Integration Points" in result or "Configuration" in result


@pytest.mark.asyncio
async def test_suggest_for_language_python(tmp_path: Path):
    """suggest_for_language('python', ...) should return Python suggestions markdown."""
    project_root = tmp_path
    (project_root / "main.py").write_text("print('hello')\n")

    result = await setup_agent_interface.suggest_for_language("python", project_root)

    assert "# Setup Suggestions for Python" in result


@pytest.mark.asyncio
async def test_suggest_for_language_cpp(tmp_path: Path):
    """suggest_for_language('cpp', ...) should return C++ suggestions markdown."""
    project_root = tmp_path
    (project_root / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.14)\nproject(example)\nadd_executable(example main.cpp)\n"
    )
    (project_root / "main.cpp").write_text("int main() { return 0; }\n")

    result = await setup_agent_interface.suggest_for_language("cpp", project_root)

    assert "# Setup Suggestions for C++" in result


@pytest.mark.asyncio
async def test_suggest_for_language_js(tmp_path: Path):
    """suggest_for_language('javascript', ...) should return JS/TS suggestions markdown."""
    project_root = tmp_path
    (project_root / "package.json").write_text('{"name": "test"}\n')
    (project_root / "index.js").write_text("console.log('hello');\n")

    result = await setup_agent_interface.suggest_for_language("javascript", project_root)

    assert "# Setup Suggestions for JavaScript/TypeScript" in result


@pytest.mark.asyncio
async def test_suggest_for_language_unsupported(tmp_path: Path):
    """Unsupported language should return clear error."""
    project_root = tmp_path

    result = await setup_agent_interface.suggest_for_language("ruby", project_root)

    assert "Unsupported language" in result


@pytest.mark.asyncio
async def test_validate_setup_empty_project(tmp_path: Path):
    """validate_setup should handle empty projects gracefully."""
    project_root = tmp_path

    result = await setup_agent_interface.validate_setup(project_root)

    assert "# DrTrace Setup Validation" in result
    assert "nothing to validate" in result.lower()


@pytest.mark.asyncio
async def test_validate_setup_python_project(tmp_path: Path):
    """validate_setup should include Python validation section when Python present."""
    project_root = tmp_path
    (project_root / "main.py").write_text("print('hello')\n")

    result = await setup_agent_interface.validate_setup(project_root)

    assert "## Python Setup" in result


@pytest.mark.asyncio
async def test_analyze_and_suggest_multi_language_project(tmp_path: Path):
    """analyze_and_suggest should include sections for all detected languages."""
    project_root = tmp_path

    # Python
    (project_root / "main.py").write_text("print('hello')\n")
    # C++
    (project_root / "CMakeLists.txt").write_text(
        "cmake_minimum_required(VERSION 3.14)\n"
        "project(example)\n"
        "add_executable(example main.cpp)\n"
    )
    (project_root / "main.cpp").write_text("int main() { return 0; }\n")
    # JavaScript
    (project_root / "package.json").write_text('{"name": "test"}\n')
    (project_root / "index.js").write_text("console.log('hello');\n")

    result = await setup_agent_interface.analyze_and_suggest(project_root)

    assert "# Setup Suggestions for Python" in result
    assert "# Setup Suggestions for C++" in result
    assert "# Setup Suggestions for JavaScript/TypeScript" in result


