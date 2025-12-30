"""
Project Structure Analyzer Module

Analyzes project structure to detect languages, build systems, entry points,
and existing logging setup. Used by setup suggestion generators to provide
accurate, project-specific integration guidance.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ProjectAnalysis:
    """Structured analysis results for a project."""

    languages: List[str] = field(default_factory=list)
    build_systems: Dict[str, str] = field(default_factory=dict)  # language -> build_system
    entry_points: Dict[str, List[Path]] = field(default_factory=dict)  # language -> [entry files]
    config_files: Dict[str, List[Path]] = field(default_factory=dict)  # language -> [config files]
    has_existing_logging: Dict[str, bool] = field(default_factory=dict)  # language -> has_logging


def detect_languages(project_root: Path) -> List[str]:
    """
    Detect languages present in the project based on file patterns.

    Args:
        project_root: Root directory of the project

    Returns:
        List of detected languages: ["python"], ["javascript"], ["cpp"], or combinations
    """
    detected = []

    # Python indicators
    python_indicators = [
        "requirements.txt",
        "pyproject.toml",
        "setup.py",
        "Pipfile",
        "poetry.lock",
    ]
    if any((project_root / indicator).exists() for indicator in python_indicators):
        detected.append("python")
    else:
        # Check for .py files as fallback
        if any(project_root.rglob("*.py")):
            detected.append("python")

    # C++ indicators
    cpp_indicators = [
        "CMakeLists.txt",
        "Makefile",
        "CMakeCache.txt",
    ]
    if any((project_root / indicator).exists() for indicator in cpp_indicators):
        detected.append("cpp")
    else:
        # Check for .cpp, .hpp, .cc, .h files as fallback
        cpp_extensions = [".cpp", ".hpp", ".cc", ".h", ".cxx", ".hxx"]
        if any(
            f.suffix.lower() in cpp_extensions
            for f in project_root.rglob("*")
            if f.is_file()
        ):
            detected.append("cpp")

    # JavaScript/TypeScript indicators
    js_indicators = [
        "package.json",
        "yarn.lock",
        "package-lock.json",
        "pnpm-lock.yaml",
        "tsconfig.json",
    ]
    if any((project_root / indicator).exists() for indicator in js_indicators):
        detected.append("javascript")
    else:
        # Check for .js, .ts files as fallback
        js_extensions = [".js", ".ts", ".jsx", ".tsx"]
        if any(
            f.suffix.lower() in js_extensions
            for f in project_root.rglob("*")
            if f.is_file()
        ):
            detected.append("javascript")

    return detected


def detect_build_system(project_root: Path, language: str) -> Optional[str]:
    """
    Detect the build system for a specific language.

    Args:
        project_root: Root directory of the project
        language: Language to detect build system for ("python", "cpp", "javascript")

    Returns:
        Build system name or None if not detected
    """
    if language == "python":
        # Check for poetry
        if (project_root / "pyproject.toml").exists():
            try:
                content = (project_root / "pyproject.toml").read_text()
                if "[tool.poetry]" in content:
                    return "poetry"
            except Exception:
                pass

        # Check for setuptools
        if (project_root / "setup.py").exists():
            return "setuptools"

        # Check for pip (requirements.txt)
        if (project_root / "requirements.txt").exists():
            return "pip"

        # Default to pip if Python detected
        return "pip"

    elif language == "cpp":
        # Check for CMake
        if (project_root / "CMakeLists.txt").exists():
            return "cmake"

        # Check for Make
        if (project_root / "Makefile").exists():
            return "make"

        return None

    elif language == "javascript":
        # Check for yarn
        if (project_root / "yarn.lock").exists():
            return "yarn"

        # Check for pnpm
        if (project_root / "pnpm-lock.yaml").exists():
            return "pnpm"

        # Check for npm (package-lock.json)
        if (project_root / "package-lock.json").exists():
            return "npm"

        # Default to npm if package.json exists
        if (project_root / "package.json").exists():
            return "npm"

        return None

    return None


def find_entry_points(project_root: Path, language: str) -> List[Path]:
    """
    Find entry point files for a specific language.

    Args:
        project_root: Root directory of the project
        language: Language to find entry points for

    Returns:
        List of Path objects to entry point files
    """
    entry_points = []

    if language == "python":
        # Common Python entry points
        common_names = ["main.py", "app.py", "__main__.py", "setup.py", "run.py"]
        for name in common_names:
            path = project_root / name
            if path.exists():
                entry_points.append(path)

        # Also check for __main__.py in subdirectories (package entry points)
        for main_file in project_root.rglob("__main__.py"):
            entry_points.append(main_file)

    elif language == "cpp":
        # Common C++ entry points
        common_names = ["main.cpp", "app.cpp", "main.cc", "app.cc"]
        for name in common_names:
            path = project_root / name
            if path.exists():
                entry_points.append(path)

        # Check for files with main() function (simple pattern match)
        for cpp_file in project_root.rglob("*.cpp"):
            try:
                content = cpp_file.read_text()
                if "int main(" in content or "void main(" in content:
                    entry_points.append(cpp_file)
            except Exception:
                continue

    elif language == "javascript":
        # Check package.json for entry point
        package_json = project_root / "package.json"
        if package_json.exists():
            try:
                import json

                data = json.loads(package_json.read_text())
                if "main" in data:
                    main_path = project_root / data["main"]
                    if main_path.exists():
                        entry_points.append(main_path)
            except Exception:
                pass

        # Common JavaScript/TypeScript entry points
        common_names = ["index.js", "index.ts", "main.js", "main.ts", "app.js", "app.ts"]
        for name in common_names:
            path = project_root / name
            if path.exists():
                entry_points.append(path)

    return entry_points


def detect_existing_logging(project_root: Path, language: str) -> bool:
    """
    Detect if the project already uses logging.

    Args:
        project_root: Root directory of the project
        language: Language to check for logging

    Returns:
        True if existing logging is detected, False otherwise
    """
    if language == "python":
        # Check for logging module imports
        for py_file in project_root.rglob("*.py"):
            try:
                content = py_file.read_text()
                if "import logging" in content or "from logging import" in content:
                    return True
            except Exception:
                continue

    elif language == "cpp":
        # Check for spdlog or other logging includes
        for cpp_file in project_root.rglob("*.cpp"):
            try:
                content = cpp_file.read_text()
                if "#include <spdlog/" in content or "#include \"spdlog/" in content:
                    return True
                # Check for other common logging libraries
                if "#include <log" in content.lower():
                    return True
            except Exception:
                continue

        # Also check header files
        for hpp_file in project_root.rglob("*.hpp"):
            try:
                content = hpp_file.read_text()
                if "#include <spdlog/" in content or "#include \"spdlog/" in content:
                    return True
            except Exception:
                continue

    elif language == "javascript":
        # Check for winston, pino, or console usage
        for js_file in project_root.rglob("*.js"):
            try:
                content = js_file.read_text()
                if (
                    "require('winston')" in content
                    or "require(\"winston\")" in content
                    or "from 'winston'" in content
                    or "require('pino')" in content
                    or "require(\"pino\")" in content
                    or "from 'pino'" in content
                    or "console.log" in content
                    or "console.error" in content
                    or "console.warn" in content
                ):
                    return True
            except Exception:
                continue

        # Also check TypeScript files
        for ts_file in project_root.rglob("*.ts"):
            try:
                content = ts_file.read_text()
                if (
                    "import" in content
                    and ("winston" in content or "pino" in content)
                ) or "console.log" in content:
                    return True
            except Exception:
                continue

    return False


def analyze_project(project_root: Path) -> ProjectAnalysis:
    """
    Perform complete project analysis.

    Args:
        project_root: Root directory of the project

    Returns:
        ProjectAnalysis dataclass with all analysis results
    """
    project_root = Path(project_root).resolve()

    # Detect languages
    languages = detect_languages(project_root)

    # Initialize analysis result
    analysis = ProjectAnalysis(languages=languages)

    # For each detected language, detect build system, entry points, and logging
    for language in languages:
        # Build system
        build_system = detect_build_system(project_root, language)
        if build_system:
            analysis.build_systems[language] = build_system

        # Entry points
        entry_points = find_entry_points(project_root, language)
        if entry_points:
            analysis.entry_points[language] = entry_points

        # Config files (language-specific)
        config_files = []
        if language == "python":
            for config_name in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]:
                config_path = project_root / config_name
                if config_path.exists():
                    config_files.append(config_path)
        elif language == "cpp":
            for config_name in ["CMakeLists.txt", "Makefile"]:
                config_path = project_root / config_name
                if config_path.exists():
                    config_files.append(config_path)
        elif language == "javascript":
            for config_name in ["package.json", "tsconfig.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"]:
                config_path = project_root / config_name
                if config_path.exists():
                    config_files.append(config_path)

        if config_files:
            analysis.config_files[language] = config_files

        # Existing logging
        has_logging = detect_existing_logging(project_root, language)
        analysis.has_existing_logging[language] = has_logging

    return analysis

