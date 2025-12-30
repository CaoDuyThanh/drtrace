"""
Setup Suggestion Generators Module

Generates language-specific setup suggestions for integrating DrTrace into projects.
Provides structured suggestions with integration points, code snippets, configuration,
and verification steps.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .project_analyzer import ProjectAnalysis


@dataclass
class IntegrationPoint:
    """Represents a suggested integration point in the codebase."""

    file_path: Path
    line_number: int
    suggested_code: str
    reason: str
    priority: str  # "required", "recommended", "optional"


@dataclass
class CodeSnippet:
    """Represents a code snippet with context."""

    language: str
    code: str
    description: str
    file_path: Optional[Path] = None
    line_number: Optional[int] = None


@dataclass
class ConfigChange:
    """Represents a configuration change suggestion."""

    file_path: Path
    change_type: str  # "add_env_var", "create_file", "modify_file"
    content: str
    description: str
    priority: str  # "required", "recommended", "optional"


@dataclass
class PythonSetupSuggestion:
    """Structured Python setup suggestions."""

    integration_points: List[IntegrationPoint] = field(default_factory=list)
    code_snippets: List[CodeSnippet] = field(default_factory=list)
    config_changes: List[ConfigChange] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)


@dataclass
class CmakeChange:
    """Represents a suggested change to a CMakeLists.txt file."""

    file_path: Path
    insertion_point: str  # e.g., "after include(FetchContent)", "before add_executable(...)"
    suggested_code: str
    use_fetchcontent: bool
    reason: str


@dataclass
class IncludePoint:
    """Represents a suggested include/integration point in C++ code."""

    file_path: Path
    line_number: int
    suggested_code: str
    reason: str


@dataclass
class CppSetupSuggestion:
    """Structured C++ setup suggestions."""

    cmake_changes: List[CmakeChange] = field(default_factory=list)
    include_points: List[IncludePoint] = field(default_factory=list)
    code_snippets: List[CodeSnippet] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)


@dataclass
class JsSetupSuggestion:
    """Structured JavaScript/TypeScript setup suggestions."""

    package_manager: str  # "npm", "yarn", "pnpm", or "unknown"
    install_command: str
    initialization_points: List[IntegrationPoint] = field(default_factory=list)
    code_snippets: List[CodeSnippet] = field(default_factory=list)
    config_suggestions: List[ConfigChange] = field(default_factory=list)
    verification_steps: List[str] = field(default_factory=list)


def generate_python_setup(
    project_root: Path, analysis: Optional["ProjectAnalysis"] = None
) -> PythonSetupSuggestion:
    """
    Generate Python-specific setup suggestions based on project analysis.

    Args:
        project_root: Root directory of the project
        analysis: Optional ProjectAnalysis object (if None, will analyze project)

    Returns:
        PythonSetupSuggestion with integration points, code snippets, config changes, and verification steps
    """
    from .project_analyzer import analyze_project, ProjectAnalysis

    if analysis is None:
        analysis = analyze_project(project_root)

    suggestion = PythonSetupSuggestion()

    # Find integration points
    _find_integration_points(project_root, analysis, suggestion)

    # Generate code snippets
    _generate_code_snippets(project_root, analysis, suggestion)

    # Generate configuration suggestions
    _generate_config_suggestions(project_root, analysis, suggestion)

    # Generate verification steps
    _generate_verification_steps(suggestion)

    return suggestion


def generate_cpp_setup(
    project_root: Path, analysis: Optional["ProjectAnalysis"] = None
) -> CppSetupSuggestion:
    """Generate C++-specific setup suggestions based on project analysis.

    This focuses on CMake FetchContent integration and spdlog sink wiring.
    """
    from .project_analyzer import analyze_project, ProjectAnalysis

    if analysis is None:
        analysis = analyze_project(project_root)

    suggestion = CppSetupSuggestion()

    # Only proceed if C++ is detected
    if "cpp" not in analysis.languages:
        return suggestion

    _generate_cmake_suggestions(project_root, analysis, suggestion)
    _generate_cpp_code_suggestions(project_root, analysis, suggestion)
    _generate_cpp_verification_steps(suggestion)

    return suggestion


def generate_js_setup(
    project_root: Path, analysis: Optional["ProjectAnalysis"] = None
) -> JsSetupSuggestion:
    """Generate JavaScript/TypeScript setup suggestions based on project analysis."""
    from .project_analyzer import analyze_project, ProjectAnalysis

    if analysis is None:
        analysis = analyze_project(project_root)

    # Default values before detection
    js_suggestion = JsSetupSuggestion(
        package_manager="unknown",
        install_command="npm install drtrace",
    )

    # Only proceed if JS detected
    if "javascript" not in analysis.languages:
        return js_suggestion

    _generate_js_package_suggestions(project_root, analysis, js_suggestion)
    _generate_js_initialization_suggestions(project_root, analysis, js_suggestion)
    _generate_js_verification_steps(js_suggestion)

    return js_suggestion


def _resolve_application_id(project_root: Path) -> str:
    """
    Resolve application ID at agent-time:
    1. Check DRTRACE_APPLICATION_ID env var (highest priority)
    2. Fall back to _drtrace/config.json application_id
    3. Last resort: "my-app"
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        Effective application ID string
    """
    # Priority 1: Environment variable
    env_app_id = os.getenv("DRTRACE_APPLICATION_ID")
    if env_app_id:
        return env_app_id
    
    # Priority 2: Read from _drtrace/config.json
    config_path = project_root / "_drtrace" / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            # Try both snake_case (new format) and camelCase (old format)
            app_id = config.get("application_id") or config.get("applicationId")
            if app_id:
                return app_id
            # Also check nested drtrace.applicationId (for compatibility with config_loader format)
            drtrace_section = config.get("drtrace", {})
            if isinstance(drtrace_section, dict):
                app_id = drtrace_section.get("applicationId")
                if app_id:
                    return app_id
        except (json.JSONDecodeError, OSError, KeyError):
            # If config file is malformed or missing fields, fall through to default
            pass
    
    # Priority 3: Default fallback
    return "my-app"


def _resolve_daemon_url(project_root: Path) -> str:
    """
    Resolve daemon URL at agent-time:
    1. Check DRTRACE_DAEMON_URL env var (highest priority)
    2. Fall back to _drtrace/config.json daemon_url or daemonUrl
    3. Last resort: "http://localhost:8001/logs/ingest"
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        Effective daemon URL string
    """
    # Priority 1: Environment variable
    env_daemon_url = os.getenv("DRTRACE_DAEMON_URL")
    if env_daemon_url:
        # Ensure it includes /logs/ingest if not present
        if not env_daemon_url.endswith("/logs/ingest"):
            if env_daemon_url.endswith("/"):
                return f"{env_daemon_url}logs/ingest"
            else:
                return f"{env_daemon_url}/logs/ingest"
        return env_daemon_url
    
    # Priority 2: Read from _drtrace/config.json
    config_path = project_root / "_drtrace" / "config.json"
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            # Try both snake_case (new format) and camelCase (old format)
            daemon_url = config.get("daemon_url") or config.get("daemonUrl")
            if daemon_url:
                # Ensure it includes /logs/ingest if not present
                if not daemon_url.endswith("/logs/ingest"):
                    if daemon_url.endswith("/"):
                        return f"{daemon_url}logs/ingest"
                    else:
                        return f"{daemon_url}/logs/ingest"
                return daemon_url
            # Also check nested drtrace.daemonUrl (for compatibility with config_loader format)
            drtrace_section = config.get("drtrace", {})
            if isinstance(drtrace_section, dict):
                daemon_url = drtrace_section.get("daemonUrl")
                if daemon_url:
                    # Ensure it includes /logs/ingest if not present
                    if not daemon_url.endswith("/logs/ingest"):
                        if daemon_url.endswith("/"):
                            return f"{daemon_url}logs/ingest"
                        else:
                            return f"{daemon_url}/logs/ingest"
                    return daemon_url
        except (json.JSONDecodeError, OSError, KeyError):
            # If config file is malformed or missing fields, fall through to default
            pass
    
    # Priority 3: Default fallback
    return "http://localhost:8001/logs/ingest"


def _detect_package_manager(project_root: Path) -> str:
    """Detect package manager based on lockfiles."""
    if (project_root / "yarn.lock").exists():
        return "yarn"
    if (project_root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (project_root / "package-lock.json").exists():
        return "npm"
    # Fallback: if package.json exists, assume npm
    if (project_root / "package.json").exists():
        return "npm"
    return "unknown"


def _generate_js_package_suggestions(
    project_root: Path, analysis: "ProjectAnalysis", suggestion: JsSetupSuggestion
) -> None:
    """Fill in package manager and install command + config suggestions."""
    pm = _detect_package_manager(project_root)
    suggestion.package_manager = pm

    if pm == "yarn":
        suggestion.install_command = "yarn add drtrace"
    elif pm == "pnpm":
        suggestion.install_command = "pnpm add drtrace"
    else:
        # Default to npm
        suggestion.install_command = "npm install drtrace"

    # Resolve application ID at agent-time
    app_id = _resolve_application_id(project_root)

    # Suggest adding DRTRACE_* env vars to .env similar to Python
    env_file = project_root / ".env"
    content = f"""# DrTrace JS/TS configuration
DRTRACE_APPLICATION_ID={app_id}
DRTRACE_DAEMON_URL=http://localhost:8001
DRTRACE_ENABLED=true
"""
    change_type = "add_env_var" if env_file.exists() else "create_file"
    suggestion.config_suggestions.append(
        ConfigChange(
            file_path=env_file,
            change_type=change_type,
            content=content,
            description="Add DrTrace environment variables for JS/TS client",
            priority="recommended",
        )
    )


def _generate_cmake_suggestions(
    project_root: Path, analysis: "ProjectAnalysis", suggestion: CppSetupSuggestion
) -> None:
    """Generate CMakeLists.txt integration suggestions for header-only C++ client.

    Detects spdlog usage and suggests appropriate CMake pattern:
      - If spdlog detected: Include spdlog setup (find_package → FetchContent)
      - If spdlog not detected: Only require libcurl (for direct API)
    """
    from .project_analyzer import detect_existing_logging
    
    # Look for top-level CMakeLists.txt
    cmake_file = project_root / "CMakeLists.txt"
    if not cmake_file.exists():
        return

    try:
        content = cmake_file.read_text()
    except Exception:
        return

    # Determine insertion point: after project() by default
    insertion_point = "after project()"

    # Detect if project uses spdlog
    uses_spdlog = detect_existing_logging(project_root, "cpp")
    
    if uses_spdlog:
        # Pattern 1: With spdlog (spdlog adapter)
        cmake_block = """# DrTrace C++ client (header-only)
#
# The drtrace_sink.hpp header is copied into your project by the DrTrace
# init-project command at: third_party/drtrace/drtrace_sink.hpp
# Note: third_party/drtrace/ should be committed to git (unlike _drtrace/ which is gitignored)
#
# Include the third_party/drtrace directory so the header can be found:
target_include_directories(your_target PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/drtrace
)

# DrTrace spdlog adapter requires spdlog. Try to find it via find_package first (if your project already has it configured):
find_package(spdlog QUIET)

if(NOT spdlog_FOUND)
    # Fallback: Use FetchContent to download and build spdlog automatically
    include(FetchContent)
    
    FetchContent_Declare(
        spdlog
        GIT_REPOSITORY https://github.com/gabime/spdlog.git
        GIT_TAG        v1.13.0
        GIT_SUBMODULES ""
    )
    
    FetchContent_MakeAvailable(spdlog)
endif()

# Link required dependencies:
#   - spdlog::spdlog (from find_package or FetchContent)
#   - CURL::libcurl (system dependency - must be installed)
target_link_libraries(your_target PRIVATE
    spdlog::spdlog
    CURL::libcurl
)
"""
        reason = (
            "Use header-only DrTrace C++ client with spdlog adapter: include third_party/drtrace/drtrace_sink.hpp and "
            "link against spdlog::spdlog and CURL::libcurl."
        )
    else:
        # Pattern 2: Without spdlog (direct API)
        cmake_block = """# DrTrace C++ client (header-only, direct API)
#
# The drtrace_sink.hpp header is copied into your project by the DrTrace
# init-project command at: third_party/drtrace/drtrace_sink.hpp
# Note: third_party/drtrace/ should be committed to git (unlike _drtrace/ which is gitignored)
#
# Include the third_party/drtrace directory so the header can be found:
target_include_directories(your_target PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/third_party/drtrace
)

# Link required dependencies (direct API only requires libcurl, no spdlog needed):
#   - CURL::libcurl (system dependency - must be installed)
target_link_libraries(your_target PRIVATE
    CURL::libcurl
)
"""
        reason = (
            "Use header-only DrTrace C++ client with direct API: include third_party/drtrace/drtrace_sink.hpp and "
            "link against CURL::libcurl (no spdlog required)."
        )

    suggestion.cmake_changes.append(
        CmakeChange(
            file_path=cmake_file,
            insertion_point=insertion_point,
            suggested_code=cmake_block,
            use_fetchcontent=False,
            reason=reason,
        )
    )


def _generate_cpp_code_suggestions(
    project_root: Path, analysis: "ProjectAnalysis", suggestion: CppSetupSuggestion
) -> None:
    """Generate C++ code integration suggestions (detects spdlog usage and suggests appropriate pattern)."""
    from .project_analyzer import detect_existing_logging
    
    # Prefer main.cpp/app.cpp as integration points
    entry_points = analysis.entry_points.get("cpp", [])
    preferred_names = ["main.cpp", "app.cpp"]

    target_file: Optional[Path] = None
    for name in preferred_names:
        for path in entry_points:
            if path.name == name:
                target_file = path
                break
        if target_file:
            break

    if not target_file and entry_points:
        target_file = entry_points[0]

    # Resolve application ID and daemon URL at agent-time (hardcode in generated code)
    app_id = _resolve_application_id(project_root)
    daemon_url = _resolve_daemon_url(project_root)

    # Detect if project uses spdlog
    uses_spdlog = detect_existing_logging(project_root, "cpp")
    
    if uses_spdlog:
        # Pattern 1: spdlog adapter
        code = f"""#include "third_party/drtrace/drtrace_sink.hpp"
#include <spdlog/spdlog.h>

int main(int argc, char** argv) {{
    // Configure DrTrace (hardcoded from config file at code generation time)
    drtrace::DrtraceConfig config;
    config.application_id = "{app_id}";
    config.daemon_url = "{daemon_url}";

    // Use helper function to create logger with DrTrace integration
    auto logger = drtrace::create_drtrace_logger("my_app", config);

    // Existing logging continues to work
    logger->info("Application starting with DrTrace");

    // ... rest of your application ...
}}
"""
        include_reason = (
            "Main entry point - best place to attach DrTrace sink to the default spdlog "
            "logger so all logs are forwarded to DrTrace without changing existing calls."
        )
        description = "C++ integration pattern using spdlog adapter (DrtraceSink)"
    else:
        # Pattern 2: Direct API (no spdlog)
        code = f"""#include "third_party/drtrace/drtrace_sink.hpp"

int main(int argc, char** argv) {{
    // Configure DrTrace (hardcoded from config file at code generation time)
    drtrace::DrtraceConfig config;
    config.application_id = "{app_id}";
    config.daemon_url = "{daemon_url}";

    // Use direct API (no spdlog required)
    drtrace::DrtraceClient client(config, "my_app");

    // Use the client directly
    client.info("Application starting with DrTrace");
    client.error("Error occurred", __FILE__, __LINE__);

    // ... rest of your application ...
}}
"""
        include_reason = (
            "Main entry point - best place to initialize DrTrace client for direct logging."
        )
        description = "C++ integration pattern using direct API (DrtraceClient, no spdlog required)"

    if target_file:
        suggestion.include_points.append(
            IncludePoint(
                file_path=target_file,
                line_number=1,
                suggested_code=code,
                reason=include_reason,
            )
        )

    # Also add as a generic snippet (in case main file is different)
    suggestion.code_snippets.append(
        CodeSnippet(
            language="cpp",
            code=code,
            description=description,
        )
    )


def _generate_cpp_verification_steps(suggestion: CppSetupSuggestion) -> None:
    """Generate verification steps for C++ setup."""
    suggestion.verification_steps.extend(
        [
            "1. Configure your CMake project and verify FetchContent pulls DrTrace: `cmake -B build -S .`",
            "2. Build your project: `cmake --build build`",
            "3. Run your application and ensure it links against `drtrace_cpp_client`.",
            "4. Check that logs are emitted via spdlog and forwarded to DrTrace daemon.",
            "5. Verify logs appear in DrTrace queries or analysis commands.",
        ]
    )


def _generate_js_initialization_suggestions(
    project_root: Path, analysis: "ProjectAnalysis", suggestion: JsSetupSuggestion
) -> None:
    """Identify JS/TS entry points and generate initialization examples."""
    # Entry points from analysis for javascript
    entry_points = analysis.entry_points.get("javascript", [])

    # Common names for manual detection if analysis has none
    if not entry_points:
        for name in ["index.ts", "main.ts", "app.ts", "index.js", "main.js", "app.js"]:
            path = project_root / name
            if path.exists():
                entry_points.append(path)

    # Choose first entry as primary initialization point
    target_file = entry_points[0] if entry_points else None

    # Resolve application ID at agent-time
    app_id = _resolve_application_id(project_root)

    ts_example = f"""// TypeScript example (main.ts)
import {{ setup_logging, ClientConfig }} from 'drtrace';

// Use DRTRACE_APPLICATION_ID if set; otherwise fall back to value from _drtrace/config.json
const applicationId = process.env.DRTRACE_APPLICATION_ID || '{app_id}';

const config = new ClientConfig({{
  application_id: applicationId,
  daemon_host: 'localhost',
  daemon_port: 8001,
}});

const client = setup_logging(config);

console.log('Application starting');"""

    js_example = f"""// JavaScript example (index.js)
const {{ setup_logging, ClientConfig }} = require('drtrace');

// Use DRTRACE_APPLICATION_ID if set; otherwise fall back to value from _drtrace/config.json
const applicationId = process.env.DRTRACE_APPLICATION_ID || '{app_id}';

const config = new ClientConfig({{
  application_id: applicationId,
  daemon_host: 'localhost',
  daemon_port: 8001,
}});

const client = setup_logging(config);

console.log('Application starting');"""

    # IntegrationPoint for primary file
    if target_file:
        suggestion.initialization_points.append(
            IntegrationPoint(
                file_path=target_file,
                line_number=1,
                suggested_code=ts_example if target_file.suffix == ".ts" else js_example,
                reason="Main JS/TS entry point - best place to initialize DrTrace client",
                priority="required",
            )
        )

    # Code snippets for both JS and TS
    suggestion.code_snippets.append(
        CodeSnippet(
            language="typescript",
            code=ts_example,
            description="TypeScript initialization pattern using setup_logging and ClientConfig",
        )
    )
    suggestion.code_snippets.append(
        CodeSnippet(
            language="javascript",
            code=js_example,
            description="JavaScript initialization pattern using setup_logging and ClientConfig",
        )
    )


def _generate_js_verification_steps(suggestion: JsSetupSuggestion) -> None:
    """Generate verification steps for JS/TS setup."""
    steps = [
        f"1. Install DrTrace JS/TS client: `{suggestion.install_command}`",
        "2. Ensure the DrTrace daemon is running (see TypeScript setup guide).",
        "3. Run your application and ensure console.log/console.error are captured.",
        "4. Verify logs appear in DrTrace queries or analysis commands.",
        "5. For TypeScript, run `tsc --noEmit` to ensure types compile correctly.",
    ]
    suggestion.verification_steps.extend(steps)


def _find_integration_points(
    project_root: Path, analysis: "ProjectAnalysis", suggestion: PythonSetupSuggestion
) -> None:
    """Find best integration points for setup_logging() call."""
    entry_points = analysis.entry_points.get("python", [])

    # Priority order: main.py > app.py > run.py > __init__.py > first entry point
    priority_files = ["main.py", "app.py", "run.py", "__init__.py"]

    integration_file = None
    for priority_file in priority_files:
        for entry in entry_points:
            if entry.name == priority_file:
                integration_file = entry
                break
        if integration_file:
            break

    # Fallback to first entry point if no priority file found
    if not integration_file and entry_points:
        integration_file = entry_points[0]

    # If still no entry point, check common locations
    if not integration_file:
        for priority_file in priority_files:
            candidate = project_root / priority_file
            if candidate.exists():
                integration_file = candidate
                break

    if integration_file:
        # Determine line number (try to find after imports)
        line_number = _find_insertion_line(integration_file)

        # Generate suggested code
        suggested_code = _generate_setup_code(
            analysis.has_existing_logging.get("python", False), project_root
        )

        reason = (
            f"Main entry point - best place to initialize logging for the entire application"
            if integration_file.name in ["main.py", "app.py", "run.py"]
            else f"Package initialization - good place to set up logging for this package"
        )

        suggestion.integration_points.append(
            IntegrationPoint(
                file_path=integration_file,
                line_number=line_number,
                suggested_code=suggested_code,
                reason=reason,
                priority="required",
            )
        )


def _find_insertion_line(file_path: Path) -> int:
    """Find the best line number to insert setup code (after imports)."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Find last import line
        last_import_line = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                last_import_line = i + 1

        # Return line after last import, or line 1 if no imports
        return max(last_import_line + 1, 1)
    except Exception:
        # If we can't read the file, default to line 1
        return 1


def _generate_setup_code(has_existing_logging: bool, project_root: Path) -> str:
    """
    Generate setup code snippet.
    
    Args:
        has_existing_logging: Whether the project already has logging setup
        project_root: Root directory of the project (for resolving application ID)
    """
    # Resolve application ID at agent-time
    app_id = _resolve_application_id(project_root)
    
    if has_existing_logging:
        # Integration with existing logging
        return f"""# Setup DrTrace (adds handler without removing existing handlers)
import logging
import os
from drtrace_client import setup_logging

# Use DRTRACE_APPLICATION_ID if set; otherwise fall back to value from _drtrace/config.json
application_id = os.environ.get("DRTRACE_APPLICATION_ID", "{app_id}")

# Get root logger
logger = logging.getLogger()

# Setup DrTrace - this adds a handler without removing existing ones
setup_logging(
    logger,
    application_id=application_id,
    service_name="my-service"  # optional
)

# Existing logging continues to work
logger.info("Application starting")"""
    else:
        # New logging setup
        return f"""# Setup DrTrace logging
import logging
import os
from drtrace_client import setup_logging

# Use DRTRACE_APPLICATION_ID if set; otherwise fall back to value from _drtrace/config.json
application_id = os.environ.get("DRTRACE_APPLICATION_ID", "{app_id}")

# Get root logger
logger = logging.getLogger()

# Setup DrTrace
setup_logging(
    logger,
    application_id=application_id,
    service_name="my-service"  # optional
)

# Use standard logging
logger.info("Application starting")"""


def _generate_code_snippets(
    project_root: Path, analysis: "ProjectAnalysis", suggestion: PythonSetupSuggestion
) -> None:
    """Generate code snippets for different use cases."""
    # Resolve application ID at agent-time
    app_id = _resolve_application_id(project_root)
    
    # Root logger pattern (already in integration points, but add as snippet too)
    suggestion.code_snippets.append(
        CodeSnippet(
            language="python",
            code=_generate_setup_code(analysis.has_existing_logging.get("python", False), project_root),
            description="Root logger setup - recommended for most applications",
        )
    )

    # Module logger pattern
    suggestion.code_snippets.append(
        CodeSnippet(
            language="python",
            code=f"""# For module-level logging
import logging
import os
from drtrace_client import setup_logging

# Use DRTRACE_APPLICATION_ID if set; otherwise fall back to value from _drtrace/config.json
application_id = os.environ.get("DRTRACE_APPLICATION_ID", "{app_id}")

# Get module logger
logger = logging.getLogger(__name__)

# Setup DrTrace for this logger (if not already set up at root level)
# Note: Usually you only need to call setup_logging() once at the root level
setup_logging(
    logging.getLogger(),  # Use root logger
    application_id=application_id
)

# Use logger in your module
logger.info("Module message")""",
            description="Module logger pattern - for individual modules",
        )
    )

    # Flask/Django pattern
    if any(
        (project_root / f).exists()
        for f in ["app.py", "manage.py", "wsgi.py", "asgi.py", "settings.py"]
    ):
        suggestion.code_snippets.append(
            CodeSnippet(
                language="python",
                code=f"""# Flask/Django integration pattern
import logging
import os
from drtrace_client import setup_logging

# Use DRTRACE_APPLICATION_ID if set; otherwise fall back to value from _drtrace/config.json
application_id = os.environ.get("DRTRACE_APPLICATION_ID", "{app_id}")

# In your app initialization (app.py, settings.py, or wsgi.py)
logger = logging.getLogger()

# Setup DrTrace early in application startup
setup_logging(
    logger,
    application_id=application_id,
    service_name="my-service"
)

# Existing framework logging continues to work
logger.info("Application initialized")""",
                description="Framework integration pattern - for Flask/Django",
            )
        )


def _generate_config_suggestions(
    project_root: Path, analysis: "ProjectAnalysis", suggestion: PythonSetupSuggestion
) -> None:
    """Generate configuration change suggestions."""
    # Resolve application ID at agent-time
    app_id = _resolve_application_id(project_root)
    
    # Environment variable suggestion
    env_file = project_root / ".env"
    env_example_file = project_root / ".env.example"

    if env_file.exists():
        config_file = env_file
        # Add to existing .env file
        suggestion.config_changes.append(
            ConfigChange(
                file_path=config_file,
                change_type="add_env_var",
                content=f"""# DrTrace Configuration
DRTRACE_APPLICATION_ID={app_id}
DRTRACE_DAEMON_HOST=localhost
DRTRACE_DAEMON_PORT=8001
""",
                description="Add DrTrace environment variables to .env file",
                priority="recommended",
            )
        )
    elif env_example_file.exists():
        config_file = env_example_file
        # Add to existing .env.example file
        suggestion.config_changes.append(
            ConfigChange(
                file_path=config_file,
                change_type="add_env_var",
                content=f"""# DrTrace Configuration
DRTRACE_APPLICATION_ID={app_id}
DRTRACE_DAEMON_HOST=localhost
DRTRACE_DAEMON_PORT=8001
""",
                description="Add DrTrace environment variables to .env.example file",
                priority="recommended",
            )
        )
    else:
        # Create new .env file
        config_file = project_root / ".env"
        suggestion.config_changes.append(
            ConfigChange(
                file_path=config_file,
                change_type="create_file",
                content=f"""# DrTrace Configuration
DRTRACE_APPLICATION_ID={app_id}
DRTRACE_DAEMON_HOST=localhost
DRTRACE_DAEMON_PORT=8001
""",
                description="Create .env file with DrTrace configuration",
                priority="recommended",
            )
        )

    # Check for requirements.txt or pyproject.toml
    requirements_file = project_root / "requirements.txt"
    pyproject_file = project_root / "pyproject.toml"
    
    if requirements_file.exists():
        # Check if drtrace is already in requirements.txt
        try:
            content = requirements_file.read_text()
            if "drtrace" not in content.lower():
                suggestion.config_changes.append(
                    ConfigChange(
                        file_path=requirements_file,
                        change_type="modify_file",
                        content="drtrace\n",
                        description="Add drtrace to requirements.txt",
                        priority="required",
                    )
                )
        except Exception:
            # If we can't read it, suggest adding anyway
            suggestion.config_changes.append(
                ConfigChange(
                    file_path=requirements_file,
                    change_type="modify_file",
                    content="drtrace\n",
                    description="Add drtrace to requirements.txt",
                    priority="required",
                )
            )
    elif pyproject_file.exists():
        # Check if drtrace is already in pyproject.toml
        try:
            content = pyproject_file.read_text()
            if "drtrace" not in content.lower():
                suggestion.config_changes.append(
                    ConfigChange(
                        file_path=pyproject_file,
                        change_type="modify_file",
                        content='drtrace = "*"  # Add to [project.dependencies] or [tool.poetry.dependencies]',
                        description="Add drtrace to pyproject.toml dependencies",
                        priority="required",
                    )
                )
        except Exception:
            # If we can't read it, suggest adding anyway
            suggestion.config_changes.append(
                ConfigChange(
                    file_path=pyproject_file,
                    change_type="modify_file",
                    content='drtrace = "*"  # Add to [project.dependencies] or [tool.poetry.dependencies]',
                    description="Add drtrace to pyproject.toml dependencies",
                    priority="required",
                )
            )
    else:
        # No dependency file found - suggest creating requirements.txt
        suggestion.config_changes.append(
            ConfigChange(
                file_path=requirements_file,
                change_type="create_file",
                content="drtrace\n",
                description="Create requirements.txt with drtrace",
                priority="required",
            )
        )


def _generate_verification_steps(suggestion: PythonSetupSuggestion) -> None:
    """Generate verification steps for the setup."""
    suggestion.verification_steps.extend(
        [
            "1. Install the DrTrace client: `pip install drtrace`",
            "2. Ensure the DrTrace daemon is running (see daemon setup instructions)",
            "3. Run your application and check that logs are being sent to the daemon",
            "4. Verify logs appear in query results: `python -m drtrace_service query --since 1m`",
            "5. Test error logging: Trigger an error in your app and verify it appears in DrTrace",
        ]
    )

    # Add test code snippet (using a generic test-app ID for testing purposes)
    suggestion.code_snippets.append(
        CodeSnippet(
            language="python",
            code="""# Test code to verify setup
import logging
from drtrace_client import setup_logging

# Setup
logger = logging.getLogger()
setup_logging(logger, application_id="test-app")

# Test different log levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")

# Check daemon status
# Run: python -m drtrace_service status
""",
            description="Test code to verify DrTrace setup is working",
        )
    )

