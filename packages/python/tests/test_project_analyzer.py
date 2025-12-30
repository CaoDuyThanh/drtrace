"""
Tests for the project structure analyzer module.
"""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from drtrace_service.project_analyzer import (
    ProjectAnalysis,
    analyze_project,
    detect_build_system,
    detect_existing_logging,
    detect_languages,
    find_entry_points,
)


class TestDetectLanguages:
    """Test language detection."""

    def test_detect_python_from_requirements_txt(self):
        """Test detecting Python from requirements.txt."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "requirements.txt").write_text("requests==2.0.0")

            languages = detect_languages(project_root)
            assert "python" in languages

    def test_detect_python_from_pyproject_toml(self):
        """Test detecting Python from pyproject.toml."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "pyproject.toml").write_text("[project]\nname = 'test'")

            languages = detect_languages(project_root)
            assert "python" in languages

    def test_detect_python_from_py_files(self):
        """Test detecting Python from .py files."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "main.py").write_text("print('hello')")

            languages = detect_languages(project_root)
            assert "python" in languages

    def test_detect_cpp_from_cmakelists(self):
        """Test detecting C++ from CMakeLists.txt."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")

            languages = detect_languages(project_root)
            assert "cpp" in languages

    def test_detect_cpp_from_cpp_files(self):
        """Test detecting C++ from .cpp files."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "main.cpp").write_text("int main() { return 0; }")

            languages = detect_languages(project_root)
            assert "cpp" in languages

    def test_detect_javascript_from_package_json(self):
        """Test detecting JavaScript from package.json."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "package.json").write_text('{"name": "test", "version": "1.0.0"}')

            languages = detect_languages(project_root)
            assert "javascript" in languages

    def test_detect_javascript_from_js_files(self):
        """Test detecting JavaScript from .js files."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "index.js").write_text("console.log('hello');")

            languages = detect_languages(project_root)
            assert "javascript" in languages

    def test_detect_multiple_languages(self):
        """Test detecting multiple languages in one project."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "requirements.txt").write_text("requests")
            (project_root / "package.json").write_text('{"name": "test"}')
            (project_root / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")

            languages = detect_languages(project_root)
            assert "python" in languages
            assert "javascript" in languages
            assert "cpp" in languages

    def test_detect_no_languages(self):
        """Test detecting no languages in empty directory."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            languages = detect_languages(project_root)
            assert len(languages) == 0


class TestDetectBuildSystem:
    """Test build system detection."""

    def test_detect_pip(self):
        """Test detecting pip build system."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "requirements.txt").write_text("requests")

            build_system = detect_build_system(project_root, "python")
            assert build_system == "pip"

    def test_detect_poetry(self):
        """Test detecting poetry build system."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "pyproject.toml").write_text("[tool.poetry]\nname = 'test'")

            build_system = detect_build_system(project_root, "python")
            assert build_system == "poetry"

    def test_detect_setuptools(self):
        """Test detecting setuptools build system."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "setup.py").write_text("from setuptools import setup")

            build_system = detect_build_system(project_root, "python")
            assert build_system == "setuptools"

    def test_detect_cmake(self):
        """Test detecting CMake build system."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")

            build_system = detect_build_system(project_root, "cpp")
            assert build_system == "cmake"

    def test_detect_make(self):
        """Test detecting Make build system."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "Makefile").write_text("all:\n\techo hello")

            build_system = detect_build_system(project_root, "cpp")
            assert build_system == "make"

    def test_detect_npm(self):
        """Test detecting npm build system."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "package.json").write_text('{"name": "test"}')
            (project_root / "package-lock.json").write_text("{}")

            build_system = detect_build_system(project_root, "javascript")
            assert build_system == "npm"

    def test_detect_yarn(self):
        """Test detecting yarn build system."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "package.json").write_text('{"name": "test"}')
            (project_root / "yarn.lock").write_text("# yarn lockfile")

            build_system = detect_build_system(project_root, "javascript")
            assert build_system == "yarn"

    def test_detect_pnpm(self):
        """Test detecting pnpm build system."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "package.json").write_text('{"name": "test"}')
            (project_root / "pnpm-lock.yaml").write_text("lockfileVersion: 5.0")

            build_system = detect_build_system(project_root, "javascript")
            assert build_system == "pnpm"


class TestFindEntryPoints:
    """Test entry point discovery."""

    def test_find_python_entry_points(self):
        """Test finding Python entry points."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "main.py").write_text("print('hello')")
            (project_root / "app.py").write_text("print('app')")

            entry_points = find_entry_points(project_root, "python")
            assert len(entry_points) >= 2
            assert any(ep.name == "main.py" for ep in entry_points)
            assert any(ep.name == "app.py" for ep in entry_points)

    def test_find_cpp_entry_points(self):
        """Test finding C++ entry points."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "main.cpp").write_text("int main() { return 0; }")

            entry_points = find_entry_points(project_root, "cpp")
            assert len(entry_points) >= 1
            assert any(ep.name == "main.cpp" for ep in entry_points)

    def test_find_cpp_entry_points_with_main_function(self):
        """Test finding C++ entry points by detecting main() function."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "myapp.cpp").write_text("int main() { return 0; }")

            entry_points = find_entry_points(project_root, "cpp")
            assert len(entry_points) >= 1
            assert any("myapp.cpp" in str(ep) for ep in entry_points)

    def test_find_javascript_entry_points_from_package_json(self):
        """Test finding JavaScript entry points from package.json."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "package.json").write_text('{"main": "src/index.js"}')
            (project_root / "src").mkdir()
            (project_root / "src" / "index.js").write_text("console.log('hello');")

            entry_points = find_entry_points(project_root, "javascript")
            assert len(entry_points) >= 1
            assert any("index.js" in str(ep) for ep in entry_points)

    def test_find_javascript_entry_points_common_names(self):
        """Test finding JavaScript entry points from common names."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "index.js").write_text("console.log('hello');")
            (project_root / "main.ts").write_text("console.log('hello');")

            entry_points = find_entry_points(project_root, "javascript")
            assert len(entry_points) >= 2
            assert any(ep.name == "index.js" for ep in entry_points)
            assert any(ep.name == "main.ts" for ep in entry_points)


class TestDetectExistingLogging:
    """Test existing logging detection."""

    def test_detect_python_logging(self):
        """Test detecting Python logging."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "app.py").write_text("import logging\nlogger = logging.getLogger()")

            has_logging = detect_existing_logging(project_root, "python")
            assert has_logging is True

    def test_detect_python_logging_from_import(self):
        """Test detecting Python logging from 'from logging import'."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "app.py").write_text("from logging import getLogger")

            has_logging = detect_existing_logging(project_root, "python")
            assert has_logging is True

    def test_no_python_logging(self):
        """Test no Python logging detected."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "app.py").write_text("print('hello')")

            has_logging = detect_existing_logging(project_root, "python")
            assert has_logging is False

    def test_detect_cpp_spdlog(self):
        """Test detecting C++ spdlog."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "main.cpp").write_text('#include <spdlog/spdlog.h>\nint main() {}')

            has_logging = detect_existing_logging(project_root, "cpp")
            assert has_logging is True

    def test_detect_cpp_spdlog_quotes(self):
        """Test detecting C++ spdlog with quotes."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "main.cpp").write_text('#include "spdlog/spdlog.h"\nint main() {}')

            has_logging = detect_existing_logging(project_root, "cpp")
            assert has_logging is True

    def test_no_cpp_logging(self):
        """Test no C++ logging detected."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "main.cpp").write_text("int main() { return 0; }")

            has_logging = detect_existing_logging(project_root, "cpp")
            assert has_logging is False

    def test_detect_javascript_winston(self):
        """Test detecting JavaScript winston."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "app.js").write_text("const winston = require('winston');")

            has_logging = detect_existing_logging(project_root, "javascript")
            assert has_logging is True

    def test_detect_javascript_pino(self):
        """Test detecting JavaScript pino."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "app.js").write_text('const pino = require("pino");')

            has_logging = detect_existing_logging(project_root, "javascript")
            assert has_logging is True

    def test_detect_javascript_console(self):
        """Test detecting JavaScript console usage."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "app.js").write_text("console.log('hello');")

            has_logging = detect_existing_logging(project_root, "javascript")
            assert has_logging is True

    def test_no_javascript_logging(self):
        """Test no JavaScript logging detected."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "app.js").write_text("const x = 1;")

            has_logging = detect_existing_logging(project_root, "javascript")
            assert has_logging is False


class TestAnalyzeProject:
    """Test complete project analysis."""

    def test_analyze_python_project(self):
        """Test analyzing a Python project."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "requirements.txt").write_text("requests")
            (project_root / "main.py").write_text("import logging\nprint('hello')")

            analysis = analyze_project(project_root)

            assert "python" in analysis.languages
            assert "python" in analysis.build_systems
            assert analysis.build_systems["python"] == "pip"
            assert len(analysis.entry_points["python"]) >= 1
            assert analysis.has_existing_logging["python"] is True

    def test_analyze_cpp_project(self):
        """Test analyzing a C++ project."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")
            (project_root / "main.cpp").write_text("int main() { return 0; }")

            analysis = analyze_project(project_root)

            assert "cpp" in analysis.languages
            assert "cpp" in analysis.build_systems
            assert analysis.build_systems["cpp"] == "cmake"
            assert len(analysis.entry_points["cpp"]) >= 1
            assert analysis.has_existing_logging["cpp"] is False

    def test_analyze_javascript_project(self):
        """Test analyzing a JavaScript project."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "package.json").write_text('{"name": "test", "main": "index.js"}')
            (project_root / "package-lock.json").write_text("{}")
            (project_root / "index.js").write_text("console.log('hello');")

            analysis = analyze_project(project_root)

            assert "javascript" in analysis.languages
            assert "javascript" in analysis.build_systems
            assert analysis.build_systems["javascript"] == "npm"
            assert len(analysis.entry_points["javascript"]) >= 1
            assert analysis.has_existing_logging["javascript"] is True

    def test_analyze_multi_language_project(self):
        """Test analyzing a multi-language project."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "requirements.txt").write_text("requests")
            (project_root / "package.json").write_text('{"name": "test"}')
            (project_root / "CMakeLists.txt").write_text("cmake_minimum_required(VERSION 3.10)")

            analysis = analyze_project(project_root)

            assert "python" in analysis.languages
            assert "javascript" in analysis.languages
            assert "cpp" in analysis.languages
            assert len(analysis.build_systems) == 3

    def test_analyze_empty_project(self):
        """Test analyzing an empty project."""
        with TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)

            analysis = analyze_project(project_root)

            assert len(analysis.languages) == 0
            assert len(analysis.build_systems) == 0
            assert len(analysis.entry_points) == 0

