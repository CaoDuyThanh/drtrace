"""
Unit tests for setup_suggestions module.
"""

import tempfile
from pathlib import Path

import pytest

from drtrace_service.project_analyzer import analyze_project
from drtrace_service.setup_suggestions import (
    CmakeChange,
    CodeSnippet,
    ConfigChange,
    CppSetupSuggestion,
    IncludePoint,
    IntegrationPoint,
    PythonSetupSuggestion,
    generate_cpp_setup,
    generate_python_setup,
)


@pytest.fixture
def temp_project():
    """Create a temporary project directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        yield project_root


def test_python_setup_suggestion_dataclass():
    """Test PythonSetupSuggestion dataclass structure."""
    suggestion = PythonSetupSuggestion()
    assert suggestion.integration_points == []
    assert suggestion.code_snippets == []
    assert suggestion.config_changes == []
    assert suggestion.verification_steps == []


def test_integration_point_dataclass():
    """Test IntegrationPoint dataclass."""
    point = IntegrationPoint(
        file_path=Path("main.py"),
        line_number=10,
        suggested_code="code here",
        reason="test reason",
        priority="required",
    )
    assert point.file_path == Path("main.py")
    assert point.line_number == 10
    assert point.priority == "required"


def test_code_snippet_dataclass():
    """Test CodeSnippet dataclass."""
    snippet = CodeSnippet(
        language="python",
        code="print('hello')",
        description="test snippet",
    )
    assert snippet.language == "python"
    assert snippet.code == "print('hello')"
    assert snippet.description == "test snippet"


def test_config_change_dataclass():
    """Test ConfigChange dataclass."""
    change = ConfigChange(
        file_path=Path(".env"),
        change_type="add_env_var",
        content="VAR=value",
        description="add variable",
        priority="recommended",
    )
    assert change.file_path == Path(".env")
    assert change.change_type == "add_env_var"
    assert change.priority == "recommended"


def test_generate_python_setup_with_main_py(temp_project):
    """Test generating Python setup suggestions for project with main.py."""
    # Create main.py
    main_py = temp_project / "main.py"
    main_py.write_text("print('hello')\n")

    # Create requirements.txt
    requirements = temp_project / "requirements.txt"
    requirements.write_text("requests==2.0.0\n")

    suggestion = generate_python_setup(temp_project)

    # Should have integration point
    assert len(suggestion.integration_points) > 0
    assert any("main.py" in str(p.file_path) for p in suggestion.integration_points)

    # Should have code snippets
    assert len(suggestion.code_snippets) > 0

    # Should have config changes (requirements.txt)
    assert len(suggestion.config_changes) > 0
    assert any("requirements.txt" in str(c.file_path) for c in suggestion.config_changes)

    # Should have verification steps
    assert len(suggestion.verification_steps) > 0


def test_generate_python_setup_with_app_py(temp_project):
    """Test generating Python setup suggestions for project with app.py."""
    # Create app.py
    app_py = temp_project / "app.py"
    app_py.write_text("from flask import Flask\napp = Flask(__name__)\n")

    suggestion = generate_python_setup(temp_project)

    # Should prefer app.py over other files
    assert len(suggestion.integration_points) > 0
    app_py_points = [p for p in suggestion.integration_points if "app.py" in str(p.file_path)]
    assert len(app_py_points) > 0


def test_generate_python_setup_with_existing_logging(temp_project):
    """Test generating Python setup suggestions for project with existing logging."""
    # Create main.py with logging
    main_py = temp_project / "main.py"
    main_py.write_text("import logging\nlogger = logging.getLogger()\nlogger.info('test')\n")

    suggestion = generate_python_setup(temp_project)

    # Should detect existing logging and generate compatible code
    assert len(suggestion.integration_points) > 0
    # Check that suggested code mentions existing logging
    suggested_code = suggestion.integration_points[0].suggested_code
    assert "existing" in suggested_code.lower() or "without removing" in suggested_code.lower()


def test_generate_python_setup_with_pyproject_toml(temp_project):
    """Test generating Python setup suggestions for project with pyproject.toml."""
    # Create pyproject.toml
    pyproject = temp_project / "pyproject.toml"
    pyproject.write_text("[project]\nname = 'test'\n")

    # Create main.py
    main_py = temp_project / "main.py"
    main_py.write_text("print('hello')\n")

    suggestion = generate_python_setup(temp_project)

    # Should suggest adding to pyproject.toml
    assert len(suggestion.config_changes) > 0
    assert any("pyproject.toml" in str(c.file_path) for c in suggestion.config_changes)


def test_generate_python_setup_with_env_file(temp_project):
    """Test generating Python setup suggestions for project with .env file."""
    # Create .env file
    env_file = temp_project / ".env"
    env_file.write_text("EXISTING_VAR=value\n")

    # Create main.py
    main_py = temp_project / "main.py"
    main_py.write_text("print('hello')\n")

    suggestion = generate_python_setup(temp_project)

    # Should suggest adding to existing .env
    assert len(suggestion.config_changes) > 0
    env_changes = [c for c in suggestion.config_changes if ".env" in str(c.file_path)]
    assert len(env_changes) > 0
    assert env_changes[0].change_type == "add_env_var"


def test_generate_python_setup_without_env_file(temp_project):
    """Test generating Python setup suggestions for project without .env file."""
    # Create main.py
    main_py = temp_project / "main.py"
    main_py.write_text("print('hello')\n")

    suggestion = generate_python_setup(temp_project)

    # Should suggest creating .env file
    assert len(suggestion.config_changes) > 0
    env_changes = [c for c in suggestion.config_changes if ".env" in str(c.file_path)]
    if env_changes:
        assert env_changes[0].change_type == "create_file"


def test_generate_python_setup_with_analysis_object(temp_project):
    """Test generating Python setup suggestions with pre-analyzed project."""
    # Create main.py
    main_py = temp_project / "main.py"
    main_py.write_text("print('hello')\n")

    # Analyze project first
    analysis = analyze_project(temp_project)

    # Generate suggestions with analysis object
    suggestion = generate_python_setup(temp_project, analysis=analysis)

    # Should work the same as without analysis object
    assert len(suggestion.integration_points) > 0
    assert len(suggestion.code_snippets) > 0


def test_generate_python_setup_code_snippets(temp_project):
    """Test that code snippets are generated correctly."""
    # Create main.py
    main_py = temp_project / "main.py"
    main_py.write_text("print('hello')\n")

    suggestion = generate_python_setup(temp_project)

    # Should have multiple code snippets
    assert len(suggestion.code_snippets) >= 2

    # Check that snippets have required fields
    for snippet in suggestion.code_snippets:
        assert snippet.language == "python"
        assert snippet.code
        assert snippet.description


def test_generate_python_setup_verification_steps(temp_project):
    """Test that verification steps are generated."""
    # Create main.py
    main_py = temp_project / "main.py"
    main_py.write_text("print('hello')\n")

    suggestion = generate_python_setup(temp_project)

    # Should have verification steps
    assert len(suggestion.verification_steps) >= 3

    # Should include installation step
    assert any("install" in step.lower() for step in suggestion.verification_steps)

    # Should include test code snippet
    test_snippets = [s for s in suggestion.code_snippets if "test" in s.description.lower()]
    assert len(test_snippets) > 0


def test_generate_python_setup_flask_django_pattern(temp_project):
    """Test that Flask/Django patterns are detected and suggested."""
    # Create app.py (Flask pattern)
    app_py = temp_project / "app.py"
    app_py.write_text("from flask import Flask\n")

    suggestion = generate_python_setup(temp_project)

    # Should have framework-specific snippet
    framework_snippets = [
        s for s in suggestion.code_snippets if "framework" in s.description.lower() or "flask" in s.description.lower() or "django" in s.description.lower()
    ]
    assert len(framework_snippets) > 0


def test_generate_python_setup_priority_ordering(temp_project):
    """Test that integration points are prioritized correctly."""
    # Create multiple entry point files
    (temp_project / "main.py").write_text("print('main')\n")
    (temp_project / "app.py").write_text("print('app')\n")
    (temp_project / "run.py").write_text("print('run')\n")

    suggestion = generate_python_setup(temp_project)

    # Should prefer main.py
    assert len(suggestion.integration_points) > 0
    main_point = suggestion.integration_points[0]
    assert "main.py" in str(main_point.file_path)


def test_cpp_setup_suggestion_dataclasses():
    """Basic construction of CppSetupSuggestion-related dataclasses."""
    cmake_change = CmakeChange(
        file_path=Path("CMakeLists.txt"),
        insertion_point="after include(FetchContent)",
        suggested_code="include(FetchContent)\n",
        use_fetchcontent=True,
        reason="test",
    )
    include_point = IncludePoint(
        file_path=Path("main.cpp"),
        line_number=1,
        suggested_code="// code",
        reason="test",
    )
    cpp_suggestion = CppSetupSuggestion(
        cmake_changes=[cmake_change],
        include_points=[include_point],
        code_snippets=[],
        verification_steps=[],
    )

    assert cpp_suggestion.cmake_changes[0].file_path == Path("CMakeLists.txt")
    assert cpp_suggestion.include_points[0].file_path == Path("main.cpp")


def test_generate_cpp_setup_no_cpp_language(temp_project):
    """If project has no C++ files, Cpp suggestions should be empty."""
    # Empty project: no cpp detected
    suggestion = generate_cpp_setup(temp_project)
    assert isinstance(suggestion, CppSetupSuggestion)
    assert suggestion.cmake_changes == []
    assert suggestion.include_points == []


def test_generate_cpp_setup_with_cmakelists_and_main_cpp(temp_project):
    """Generate C++ suggestions for simple CMake + main.cpp project."""
    # Create minimal CMakeLists.txt
    cmake = temp_project / "CMakeLists.txt"
    cmake.write_text(
        "cmake_minimum_required(VERSION 3.14)\n"
        "project(example)\n"
        "add_executable(example main.cpp)\n"
    )

    # Create main.cpp
    main_cpp = temp_project / "main.cpp"
    main_cpp.write_text("int main() { return 0; }\n")

    suggestion = generate_cpp_setup(temp_project)

    # Should propose at least one CMake change
    assert len(suggestion.cmake_changes) >= 1

    # Sanity-check that the suggested code references header-only integration
    # via third_party/drtrace/drtrace_sink.hpp include directory and required libraries.
    cmake_snippets = [c.suggested_code for c in suggestion.cmake_changes]
    joined = "\n".join(cmake_snippets)
    assert "third_party/drtrace" in joined
    assert "target_include_directories" in joined
    assert "CURL::libcurl" in joined
    # Verify pattern (either with spdlog or without - depends on detection)
    # If spdlog is detected, should have find_package → FetchContent fallback
    # If spdlog is not detected, should only have CURL::libcurl
    if "find_package(spdlog QUIET)" in joined:
        # spdlog adapter pattern
        assert "if(NOT spdlog_FOUND)" in joined
        assert "FetchContent_Declare" in joined
        assert "spdlog::spdlog" in joined
    else:
        # Direct API pattern (no spdlog)
        assert "CURL::libcurl" in joined
        # Should not have spdlog references
        assert "spdlog" not in joined or "no spdlog needed" in joined.lower()

    # Should propose at least one include/integration point
    assert len(suggestion.include_points) >= 1
    assert any("main.cpp" in str(p.file_path) for p in suggestion.include_points)

    # Should have C++ code snippets and verification steps
    assert any(s.language == "cpp" for s in suggestion.code_snippets)
    assert len(suggestion.verification_steps) >= 3

