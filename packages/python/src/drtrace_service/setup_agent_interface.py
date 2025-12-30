"""
Setup Agent Interface Handler

Provides async functions for the log-init agent to obtain formatted setup
suggestions and validation reports for multi-language projects.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from .project_analyzer import ProjectAnalysis, analyze_project
from .setup_suggestions import (
    CppSetupSuggestion,
    JsSetupSuggestion,
    PythonSetupSuggestion,
    generate_cpp_setup,
    generate_js_setup,
    generate_python_setup,
)


async def analyze_and_suggest(project_root: Optional[Path] = None) -> str:
    """
    Analyze project and return formatted setup suggestions for all detected languages.
    """
    if project_root is None:
        project_root = Path.cwd()
    else:
        project_root = Path(project_root)

    analysis = analyze_project(project_root)

    sections: List[str] = []

    # Python suggestions
    if "python" in analysis.languages:
        py_suggestion = generate_python_setup(project_root, analysis=analysis)
        sections.append(_format_python_suggestions(py_suggestion))

    # C++ suggestions
    if "cpp" in analysis.languages:
        cpp_suggestion = generate_cpp_setup(project_root, analysis=analysis)
        sections.append(_format_cpp_suggestions(cpp_suggestion))

    # JavaScript/TypeScript suggestions
    if "javascript" in analysis.languages:
        js_suggestion = generate_js_setup(project_root, analysis=analysis)
        sections.append(_format_js_suggestions(js_suggestion))

    if not sections:
        return "# Setup Suggestions\n\nNo supported languages detected in this project."

    # Join all language sections
    return "\n\n---\n\n".join(sections)


async def suggest_for_language(language: str, project_root: Path) -> str:
    """
    Generate suggestions for a specific language.
    """
    language = language.lower()
    project_root = Path(project_root)

    analysis = analyze_project(project_root)

    if language == "python":
        suggestion = generate_python_setup(project_root, analysis=analysis)
        return _format_python_suggestions(suggestion)
    elif language in ("cpp", "c++"):
        suggestion = generate_cpp_setup(project_root, analysis=analysis)
        return _format_cpp_suggestions(suggestion)
    elif language in ("javascript", "typescript", "js", "ts"):
        suggestion = generate_js_setup(project_root, analysis=analysis)
        return _format_js_suggestions(suggestion)

    return f"❌ **Error**: Unsupported language `{language}`. Supported: python, cpp, javascript."


async def validate_setup(project_root: Path) -> str:
    """
    Validate current setup and report issues.

    For v1, this reuses the suggestion generators and focuses on:
    - Presence of integration points
    - Presence of configuration changes
    - Presence of verification steps
    """
    project_root = Path(project_root)
    analysis = analyze_project(project_root)

    lines: List[str] = []
    lines.append("# DrTrace Setup Validation")
    lines.append("")

    def _validate_python() -> None:
        suggestion = generate_python_setup(project_root, analysis=analysis)
        lines.append("## Python Setup")
        if not suggestion.integration_points:
            lines.append("- ❌ No Python integration points detected (e.g., `main.py`).")
        else:
            lines.append("- ✅ Integration points detected.")
        if not suggestion.config_changes:
            lines.append("- ⚠️ No configuration suggestions detected (check `.env` / dependencies).")
        else:
            lines.append("- ✅ Configuration suggestions available.")
        if not suggestion.verification_steps:
            lines.append("- ⚠️ No verification steps defined.")
        else:
            lines.append("- ✅ Verification steps available.")
        lines.append("")

    def _validate_cpp() -> None:
        suggestion = generate_cpp_setup(project_root, analysis=analysis)
        lines.append("## C++ Setup")
        if not suggestion.cmake_changes:
            lines.append("- ❌ No CMake FetchContent suggestions present.")
        else:
            lines.append("- ✅ CMake FetchContent suggestions available.")
        if not suggestion.include_points:
            lines.append("- ⚠️ No C++ integration points (e.g., `main.cpp`) detected.")
        else:
            lines.append("- ✅ C++ integration points suggested.")
        lines.append("")

    def _validate_js() -> None:
        suggestion = generate_js_setup(project_root, analysis=analysis)
        lines.append("## JavaScript/TypeScript Setup")
        if suggestion.package_manager == "unknown":
            lines.append("- ⚠️ Package manager not detected. Ensure `npm`, `yarn`, or `pnpm` is used.")
        else:
            lines.append(f"- ✅ Detected package manager: **{suggestion.package_manager}**.")
        if not suggestion.initialization_points:
            lines.append("- ❌ No JS/TS entry points detected for initialization.")
        else:
            lines.append("- ✅ Initialization points detected.")
        lines.append("")

    if "python" in analysis.languages:
        _validate_python()
    if "cpp" in analysis.languages:
        _validate_cpp()
    if "javascript" in analysis.languages:
        _validate_js()

    if len(lines) <= 3:
        lines.append("No supported languages detected; nothing to validate.")

    return "\n".join(lines)


def _format_python_suggestions(suggestion: PythonSetupSuggestion) -> str:
    """Format Python setup suggestions as markdown."""
    lines: List[str] = []
    lines.append("# Setup Suggestions for Python")
    lines.append("")

    if suggestion.integration_points:
        lines.append("## Integration Points")
        lines.append("")
        for idx, point in enumerate(suggestion.integration_points, start=1):
            lines.append(f"### {idx}. {point.file_path.name} ({point.priority.title()})")
            lines.append(f"**Location**: `{point.file_path}:{point.line_number}`")
            lines.append(f"**Reason**: {point.reason}")
            lines.append("")
            lines.append("```python")
            lines.append(point.suggested_code)
            lines.append("```")
            lines.append("")

    if suggestion.config_changes:
        lines.append("## Configuration")
        lines.append("")
        for change in suggestion.config_changes:
            lines.append(f"- **{change.priority.title()}**: {change.description} (`{change.file_path}`)")
        lines.append("")

    if suggestion.verification_steps:
        lines.append("## Verification Steps")
        lines.append("")
        lines.extend(suggestion.verification_steps)
        lines.append("")

    return "\n".join(lines)


def _format_cpp_suggestions(suggestion: CppSetupSuggestion) -> str:
    """Format C++ setup suggestions as markdown."""
    lines: List[str] = []
    lines.append("# Setup Suggestions for C++")
    lines.append("")

    if suggestion.cmake_changes:
        lines.append("## CMakeLists.txt Changes")
        lines.append("")
        for idx, change in enumerate(suggestion.cmake_changes, start=1):
            lines.append(f"### {idx}. {change.file_path.name}")
            lines.append(f"**Insertion Point**: {change.insertion_point}")
            lines.append(f"**Reason**: {change.reason}")
            lines.append("")
            lines.append("```cmake")
            lines.append(change.suggested_code)
            lines.append("```")
            lines.append("")

    if suggestion.include_points:
        lines.append("## Code Integration Points")
        lines.append("")
        for idx, point in enumerate(suggestion.include_points, start=1):
            lines.append(f"### {idx}. {point.file_path.name}")
            lines.append(f"**Location**: `{point.file_path}:{point.line_number}`")
            lines.append(f"**Reason**: {point.reason}")
            lines.append("")
            lines.append("```cpp")
            lines.append(point.suggested_code)
            lines.append("```")
            lines.append("")

    if suggestion.verification_steps:
        lines.append("## Verification Steps")
        lines.append("")
        lines.extend(suggestion.verification_steps)
        lines.append("")

    return "\n".join(lines)


def _format_js_suggestions(suggestion: JsSetupSuggestion) -> str:
    """Format JavaScript/TypeScript setup suggestions as markdown."""
    lines: List[str] = []
    lines.append("# Setup Suggestions for JavaScript/TypeScript")
    lines.append("")

    lines.append("## Package Installation")
    lines.append("")
    lines.append(f"- **Package Manager**: `{suggestion.package_manager}`")
    lines.append(f"- **Install Command**: `{suggestion.install_command}`")
    lines.append("")

    if suggestion.initialization_points:
        lines.append("## Initialization Points")
        lines.append("")
        for idx, point in enumerate(suggestion.initialization_points, start=1):
            lines.append(f"### {idx}. {point.file_path.name} ({point.priority.title()})")
            lines.append(f"**Location**: `{point.file_path}:{point.line_number}`")
            lines.append(f"**Reason**: {point.reason}")
            lines.append("")
            # Choose language tag based on extension
            lang = "typescript" if str(point.file_path).endswith(".ts") else "javascript"
            lines.append(f"```{lang}")
            lines.append(point.suggested_code)
            lines.append("```")
            lines.append("")

    if suggestion.config_suggestions:
        lines.append("## Configuration")
        lines.append("")
        for change in suggestion.config_suggestions:
            lines.append(f"- **{change.priority.title()}**: {change.description} (`{change.file_path}`)")
        lines.append("")

    if suggestion.verification_steps:
        lines.append("## Verification Steps")
        lines.append("")
        lines.extend(suggestion.verification_steps)
        lines.append("")

    return "\n".join(lines)


