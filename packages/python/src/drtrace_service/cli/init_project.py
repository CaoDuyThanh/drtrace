"""
Interactive project initialization for DrTrace.

Provides the `python -m drtrace init` command with interactive prompts
to set up project configuration, agents, and environment files.
"""

import asyncio
import os
import sys
from importlib import resources
from pathlib import Path
from typing import Optional

from .config_schema import ConfigSchema


class ProjectInitializer:
    """Interactive project initialization."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize with optional project root."""
        self.project_root = project_root or Path.cwd()
        self.drtrace_dir = self.project_root / "_drtrace"
        self.config_path = self.drtrace_dir / "config.json"

    def prompt_text(self, prompt: str, default: Optional[str] = None) -> str:
        """Prompt for text input."""
        if default:
            full_prompt = f"{prompt} [{default}]: "
        else:
            full_prompt = f"{prompt}: "

        result = input(full_prompt).strip()
        return result if result else default or ""

    def prompt_yes_no(self, prompt: str, default: bool = True) -> bool:
        """Prompt for yes/no input."""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{prompt} ({default_str}): ").strip().lower()

        if response in ("y", "yes"):
            return True
        elif response in ("n", "no"):
            return False
        else:
            return default

    def prompt_choice(self, prompt: str, choices: list, default: Optional[str] = None) -> str:
        """Prompt for choice selection."""
        print(f"\n{prompt}")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")

        while True:
            try:
                response = input("Select option: ").strip()
                idx = int(response) - 1
                if 0 <= idx < len(choices):
                    return choices[idx]
                else:
                    print("Invalid selection. Try again.")
            except ValueError:
                print("Invalid input. Try again.")

    def prompt_multi_select(self, prompt: str, choices: list) -> list:
        """Prompt for multiple selections."""
        print(f"\n{prompt}")
        print("(Enter numbers separated by commas, e.g., '1,3')")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")

        while True:
            try:
                response = input("Select options: ").strip()
                if not response:
                    return []
                indices = [int(x.strip()) - 1 for x in response.split(",")]
                selected = []
                for idx in indices:
                    if 0 <= idx < len(choices):
                        selected.append(choices[idx])
                    else:
                        raise ValueError(f"Invalid index: {idx + 1}")
                return selected
            except (ValueError, IndexError):
                print("Invalid input. Try again.")

    def handle_existing_config(self) -> bool:
        """Handle case where config already exists."""
        if not self.config_path.exists():
            return True

        print(f"\n⚠️  Configuration already exists at {self.config_path}")

        if not self.prompt_yes_no("Overwrite existing configuration?", default=False):
            return False

        if self.prompt_yes_no("Create backup of existing config?", default=True):
            backup_path = self.config_path.with_suffix(".json.bak")
            import shutil
            shutil.copy(self.config_path, backup_path)
            print(f"✓ Backup created at {backup_path}")

        return True

    def run_interactive(self) -> bool:
        """Run the interactive initialization flow."""
        print("\n🚀 DrTrace Project Initialization\n")
        print("=" * 50)

        # Check for existing config FIRST (before collecting project info)
        if not self.handle_existing_config():
            print("\n❌ Initialization cancelled.")
            return False

        # Collect project information
        print("\n📋 Project Information:")
        project_name = self.prompt_text("Project name", default="my-app")
        application_id = self.prompt_text("Application ID", default=project_name.lower().replace(" ", "-"))

        # Language selection
        print("\n🔧 Technology Stack:")
        language = self.prompt_choice(
            "Select language/runtime:",
            ["python", "javascript", "cpp", "both"],
            default="python"
        )

        # DrTrace daemon configuration
        print("\n📡 DrTrace Daemon Configuration:")
        daemon_url = self.prompt_text(
            "Daemon URL",
            default="http://localhost:8001"
        )

        enabled = self.prompt_yes_no(
            "Enable DrTrace by default?",
            default=True
        )

        # Environment selection
        print("\n🌍 Environments:")
        available_envs = ["development", "staging", "production", "ci"]
        selected_envs = self.prompt_multi_select(
            "Which environments to configure?",
            available_envs
        )
        if not selected_envs:
            selected_envs = ["development"]

        # Agent configuration
        print("\n🤖 Agent Integration (Optional):")
        agent_enabled = self.prompt_yes_no(
            "Enable agent interface?",
            default=False
        )

        agent_framework = "bmad"
        if agent_enabled:
            agent_framework = self.prompt_choice(
                "Select agent framework:",
                ["bmad", "langchain", "other"],
                default="bmad"
            )

        # Create _drtrace directory structure
        self._create_directory_structure()

        # Generate and save main config
        config = ConfigSchema.get_default_config(
            project_name=project_name,
            application_id=application_id,
            language=language,
            daemon_url=daemon_url,
            enabled=enabled,
            environments=selected_envs,
            agent_enabled=agent_enabled,
            agent_framework=agent_framework
        )

        ConfigSchema.save(config, self.config_path)
        print(f"\n✓ Main config created: {self.config_path}")

        # Generate environment-specific configs
        self._generate_environment_configs(config)

        # Copy default agent spec(s)
        if agent_enabled:
            self._copy_agent_spec()

        # For C++ projects, copy the header-only C++ client into third_party/drtrace/
        if language in ("cpp", "both"):
            self._copy_cpp_header()
            # Copy framework-specific integration guides
            self._copy_framework_guides()

        # Generate .env.example
        self._generate_env_example(config)

        # Generate README
        self._generate_readme()

        # Optional: analyze project and suggest setup
        try:
            self._maybe_analyze_and_suggest_setup()
        except Exception as e:  # pragma: no cover - defensive, suggestions are best-effort
            print(f"\n⚠️  Setup suggestions were skipped due to an error: {e}")

        # Summary and next steps
        self._print_summary(config)

        return True

    # --- NEW: Optional setup analysis and application ---------------------

    def _maybe_analyze_and_suggest_setup(self) -> None:
        """Optionally analyze the project and display setup suggestions."""
        if not self.prompt_yes_no("Analyze project and suggest setup?", default=True):
            return

        from drtrace_service.setup_agent_interface import analyze_and_suggest

        print("\n🔎 Analyzing project for DrTrace setup suggestions...\n")
        # analyze_and_suggest returns markdown; keep it readable in terminal
        suggestions_markdown = asyncio.run(analyze_and_suggest(self.project_root))

        self._display_setup_suggestions(suggestions_markdown)

        # Ask whether to apply suggestions (non-destructive by default)
        if self.prompt_yes_no("Apply suggested setup changes?", default=False):
            self._apply_setup_suggestions(suggestions_markdown)

    def _create_directory_structure(self) -> None:
        """Create _drtrace directory structure."""
        (self.drtrace_dir / "agents").mkdir(parents=True, exist_ok=True)
        (self.drtrace_dir / "agents" / "integration-guides").mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {self.drtrace_dir}")

    def _generate_environment_configs(self, base_config: dict) -> None:
        """Generate environment-specific config files."""
        environments = base_config.get("environments", ["development"])

        for env in environments:
            env_config = base_config.copy()
            env_config_path = self.drtrace_dir / f"config.{env}.json"

            # Optionally override daemon_url for specific environments
            if env == "production":
                env_config["enabled"] = base_config.get("enabled", False)

            ConfigSchema.save(env_config, env_config_path)
            print(f"✓ Generated: {env_config_path}")

    def _copy_agent_spec(self) -> None:
        """Copy all agent files from packaged resources to _drtrace/agents/.
        
        Copies everything from agents/ directory including:
        - Agent spec files (*.md)
        - Integration guides (integration-guides/*.md)
        - Any other files (README.md, CONTRIBUTING.md, etc.)
        """
        from importlib import resources
        import os
        from pathlib import Path
        import pkg_resources

        # Try to copy all files from agents/ directory
        try:
            # Method 1: Try Python 3.9+ style (resources.files)
            try:
                if sys.version_info >= (3, 9):
                    agents_path = resources.files("drtrace_service").joinpath("resources/agents")
                    if hasattr(agents_path, 'exists') and agents_path.exists():
                        # Convert Traversable to Path for easier handling
                        # Use as_file() context manager to get actual file path
                        import tempfile
                        import shutil as shutil_module
                        with resources.as_file(agents_path) as agents_dir_path:
                            self._copy_agents_recursive(Path(agents_dir_path), self.drtrace_dir / "agents")
                        return
            except (AttributeError, FileNotFoundError, TypeError) as e:
                # TypeError can occur if as_file() doesn't work with directories
                pass

            # Method 2: Fallback to pkg_resources (Python 3.8)
            try:
                agents_dir = pkg_resources.resource_filename('drtrace_service.resources', 'agents')
                self._copy_agents_recursive(Path(agents_dir), self.drtrace_dir / "agents")
                return
            except Exception:
                pass

            # Method 3: Try development mode (monorepo)
            root_agents_dir = Path(os.getcwd()) / "agents"
            if root_agents_dir.exists():
                self._copy_agents_recursive(root_agents_dir, self.drtrace_dir / "agents")
                return

            print("⚠️  Could not find agents directory in package or development mode")

        except Exception as e:
            print(f"⚠️  Could not copy agent files: {e}")

    def _copy_agents_from_traversable(self, source_traversable, target_dir: Path) -> None:
        """Copy files from importlib.resources Traversable to target directory."""
        target_dir.mkdir(parents=True, exist_ok=True)
        copied_count = 0
        
        try:
            for item in source_traversable.iterdir():
                if hasattr(item, 'is_file') and item.is_file():
                    # It's a file
                    item_name = item.name
                    target_name = item_name
                    
                    target_file = target_dir / target_name
                    target_file.write_bytes(item.read_bytes())
                    copied_count += 1
                    
                    if item_name != target_name:
                        print(f"✓ Copied {item_name} -> {target_name}")
                    else:
                        print(f"✓ Copied {item_name}")
                elif hasattr(item, 'is_dir') and item.is_dir():
                    # It's a directory - recurse
                    sub_target = target_dir / item.name
                    self._copy_agents_from_traversable(item, sub_target)
        except Exception as e:
            print(f"⚠️  Error copying from traversable: {e}")
        
        if copied_count > 0:
            print(f"✓ Successfully copied {copied_count} file(s) from agents/")

    def _copy_agents_recursive(self, source_dir: Path, target_dir: Path) -> None:
        """Recursively copy all files from source_dir to target_dir."""
        target_dir.mkdir(parents=True, exist_ok=True)

        copied_count = 0
        for source_file in source_dir.rglob("*"):
            # Skip directories
            if source_file.is_dir():
                continue

            # Calculate relative path from source_dir
            relative_path = source_file.relative_to(source_dir)
            
            # Determine target file (no renaming needed - files are already named correctly)
            target_file = target_dir / relative_path
            
            # Create parent directories if needed
            target_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            target_file.write_bytes(source_file.read_bytes())
            copied_count += 1
            print(f"✓ Copied {relative_path}")

        if copied_count > 0:
            print(f"✓ Successfully copied {copied_count} file(s) from agents/")

    def _load_agent_spec(self, agent_name: str) -> str:
        """Load agent spec from root agents/ directory or fallback to packaged resources.
        
        Search order:
          1. Root repo directory: <repo>/agents/<agent-name>.md (development)
          2. Packaged resources: drtrace_service.resources.agents (installed)
        
        Args:
            agent_name: Name of the agent ('log-analysis', 'log-it', 'log-init', or 'log-help')
            
        Returns:
            Agent spec content as string
            
        Raises:
            FileNotFoundError: If agent spec not found
        """
        from importlib import resources
        import os

        agent_filename = f"{agent_name}.md"

        # Try root agents/ first (development mode)
        root_agent_path = os.path.join(os.getcwd(), "agents", agent_filename)
        if os.path.isfile(root_agent_path):
            with open(root_agent_path, "r", encoding="utf-8") as f:
                return f.read()

        # Fallback to packaged resources (installed mode)
        try:
            # Python 3.9+ style
            content = resources.files("drtrace_service").joinpath(
                f"resources/agents/{agent_filename}"
            ).read_text()
            return content
        except (AttributeError, FileNotFoundError):
            # Fallback for older Python versions
            try:
                with resources.open_text(
                    "drtrace_service.resources.agents",
                    agent_filename,
                    encoding="utf-8"
                ) as f:
                    return f.read()
            except FileNotFoundError:
                # Use minimal default if resource not found
                if agent_name == "log-it":
                    return self._get_default_log_it_spec()
                else:
                    return self._get_default_agent_spec()

    def _get_default_agent_spec(self) -> str:
        """Get a minimal default log-analysis agent spec."""
        return """# DrTrace Log Analysis Agent

This is the default agent spec for log analysis.

## Purpose

Analyze logs and provide root cause analysis for errors.

## Capabilities

- Parse log entries and extract key information
- Identify error patterns
- Suggest remediation steps

## Configuration

Environment-specific overrides can be set in config files.
"""

    def _get_default_log_it_spec(self) -> str:
        """Get a minimal default log-it agent spec."""
        return """# DrTrace Log-It Agent - Strategic Logging Assistant

This is the default agent spec for strategic logging assistance.

## Purpose

Help add efficient, privacy-conscious logging to your codebase.

## Capabilities

- Analyze code and suggest strategic logging points
- Validate logs against 5 criteria (efficiency, necessity, privacy, context, completeness)
- Provide copy-paste ready logging code
- Detect and flag sensitive data

## Configuration

Environment-specific overrides can be set in config files.
"""

    def _generate_env_example(self, config: dict) -> None:
        """Generate .env.example file."""
        env_file = self.drtrace_dir / ".env.example"

        content = f"""# DrTrace Configuration - Copy to .env and customize

# Basic Configuration
DRTRACE_APPLICATION_ID={config.get('application_id', 'my-app')}
DRTRACE_DAEMON_URL={config.get('daemon_url', 'http://localhost:8001')}
DRTRACE_ENABLED={str(config.get('enabled', True)).lower()}

# Environment-specific overrides
# Uncomment and modify for your environment
# DRTRACE_DAEMON_HOST=localhost
# DRTRACE_DAEMON_PORT=8001
# DRTRACE_RETENTION_DAYS=7

# Agent configuration
# DRTRACE_AGENT_ENABLED=false
# DRTRACE_AGENT_FRAMEWORK=bmad
"""

        env_file.write_text(content)
        print(f"✓ Generated: {env_file}")

    def _generate_readme(self) -> None:
        """Generate _drtrace/README.md configuration guide."""
        readme_file = self.drtrace_dir / "README.md"

        content = """# DrTrace Configuration Guide

This directory contains configuration files for the DrTrace system.

## Files

- **config.json** - Main project configuration
- **config.{environment}.json** - Environment-specific overrides
- **.env.example** - Environment variable template
- **agents/** - Agent specifications and custom rules

## Configuration

### Basic Setup

1. Review and customize `config.json`
2. For environment-specific settings, edit `config.{environment}.json`
3. Create `.env` from `.env.example` and set your environment variables

### Environment Variables

- `DRTRACE_APPLICATION_ID` - Unique application identifier
- `DRTRACE_DAEMON_URL` - URL of the DrTrace daemon
- `DRTRACE_ENABLED` - Enable/disable DrTrace globally (true/false)
- `DRTRACE_RETENTION_DAYS` - How long to retain logs (days)

### Environments

Configure separate settings for:
- **development** - Local development setup
- **staging** - Pre-production testing
- **production** - Live environment
- **ci** - Continuous integration/testing

## Usage

Load configuration based on your environment:

```python
from drtrace_service.cli.config_schema import ConfigSchema
config = ConfigSchema.load(Path("_drtrace/config.json"))
```

## Further Reading

- See `docs/` for complete documentation
- Check `agents/` for agent specifications
"""

        readme_file.write_text(content)
        print(f"✓ Generated: {readme_file}")

    def _copy_framework_guides(self) -> None:
        """Copy framework-specific integration guides to _drtrace/agents/integration-guides/.
        
        Dynamically discovers all .md files in agents/integration-guides/ directory.
        Guides are stored in agents folder so agents can access them on client side.
        """
        from importlib import resources
        import os
        from pathlib import Path

        # Create integration-guides directory in agents folder
        integration_guides_dir = self.drtrace_dir / "agents" / "integration-guides"
        integration_guides_dir.mkdir(parents=True, exist_ok=True)

        # Dynamically discover framework guides from agents/integration-guides/ directory
        root_guides_dir = Path(os.getcwd()) / "agents" / "integration-guides"
        framework_guides = []
        
        # Try root agents/integration-guides/ first (development mode)
        if root_guides_dir.exists() and root_guides_dir.is_dir():
            guide_files = list(root_guides_dir.glob("*.md"))
            framework_guides = [
                f.stem for f in guide_files
                if f.is_file()
            ]
        
        # If no guides found in development mode, try packaged resources (installed mode)
        if not framework_guides:
            try:
                # Python 3.9+ style - list all files in resources directory
                resources_path = resources.files("drtrace_service").joinpath(
                    "resources/agents/integration-guides"
                )
                if resources_path.exists():
                    framework_guides = [
                        f.stem for f in resources_path.iterdir()
                        if f.is_file() and f.suffix == ".md"
                    ]
            except (AttributeError, FileNotFoundError):
                # Fallback for older Python versions - use pkg_resources
                try:
                    import pkg_resources
                    files = pkg_resources.resource_listdir(
                        'drtrace_service.resources.agents',
                        'integration-guides'
                    )
                    framework_guides = [
                        Path(f).stem for f in files
                        if Path(f).suffix == ".md"
                    ]
                except Exception:
                    # If this fails, we'll just skip gracefully
                    pass

        # Copy each discovered guide
        for guide_name in framework_guides:
            try:
                guide_filename = f"{guide_name}.md"
                guide_path = integration_guides_dir / guide_filename
                
                # Try root agents/integration-guides/ first (development mode)
                root_guide_path = root_guides_dir / guide_filename
                if root_guide_path.exists() and root_guide_path.is_file():
                    content = root_guide_path.read_text(encoding="utf-8")
                else:
                    # Fallback to packaged resources (installed mode)
                    try:
                        # Python 3.9+ style
                        content = resources.files("drtrace_service").joinpath(
                            f"resources/agents/integration-guides/{guide_filename}"
                        ).read_text()
                    except (AttributeError, FileNotFoundError):
                        # Fallback for older Python versions - use pkg_resources
                        try:
                            import pkg_resources
                            # Get the directory path, then read the file
                            guides_dir = pkg_resources.resource_filename(
                                'drtrace_service.resources.agents',
                                'integration-guides'
                            )
                            guide_file_path = Path(guides_dir) / guide_filename
                            if guide_file_path.exists():
                                content = guide_file_path.read_text(encoding="utf-8")
                            else:
                                continue
                        except Exception:
                            # Skip if guide not found
                            continue
                
                guide_path.write_text(content)
                print(f"✓ Copied framework guide: {guide_path}")
            except Exception as e:
                print(f"⚠️  Could not copy {guide_name} framework guide: {e}")

    def _copy_cpp_header(self) -> None:
        """Copy drtrace_sink.hpp to third_party/drtrace/ for C++ projects.

        This enables header-only integration:
          - Header is copied to third_party/drtrace/drtrace_sink.hpp
          - Users include it via `#include "third_party/drtrace/drtrace_sink.hpp"`
          - CMake links only spdlog::spdlog and CURL::libcurl.
          - Note: third_party/drtrace/ should be committed to git (unlike _drtrace/ which is gitignored)
        """
        from pathlib import Path
        import shutil

        source_path = self._find_cpp_header_source()
        if not source_path or not source_path.exists():
            print(
                "⚠️  Could not find drtrace_sink.hpp - C++ header-only integration "
                "will not be available."
            )
            return

        # Destination: third_party/drtrace/drtrace_sink.hpp (committed to git)
        dest_dir = self.project_root / "third_party" / "drtrace"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / "drtrace_sink.hpp"
        try:
            shutil.copy2(source_path, dest_path)
            print(f"✓ Copied C++ header: {dest_path}")
            print("  Note: third_party/drtrace/ should be committed to git")
        except Exception as e:  # pragma: no cover - defensive
            print(
                f"⚠️  Failed to copy C++ header from {source_path} to {dest_path}: {e}"
            )

    def _find_cpp_header_source(self) -> Optional[Path]:
        """Find drtrace_sink.hpp source file for header-only C++ integration.

        Search order:
          1. Pip package location (installed mode): site-packages/drtrace_service/resources/cpp/drtrace_sink.hpp
          2. Monorepo development layout: packages/cpp/drtrace-client/src/drtrace_sink.hpp
          3. npm package location (if available): node_modules/drtrace/dist/resources/cpp/drtrace_sink.hpp
        """
        # 1. Check pip package location (installed mode)
        try:
            import importlib.util
            spec = importlib.util.find_spec("drtrace_service")
            if spec and spec.origin:
                package_dir = Path(spec.origin).parent
                pip_header_path = package_dir / "resources" / "cpp" / "drtrace_sink.hpp"
                if pip_header_path.exists():
                    return pip_header_path
        except (ImportError, AttributeError, Exception):
            # Package not installed or error getting spec - continue
            pass

        # 2. Check monorepo location (development mode)
        repo_root = self.project_root
        for _ in range(6):
            candidate = (
                repo_root
                / "packages"
                / "cpp"
                / "drtrace-client"
                / "src"
                / "drtrace_sink.hpp"
            )
            if candidate.exists():
                return candidate
            if repo_root.parent == repo_root:
                break
            repo_root = repo_root.parent

        # 3. Check npm package location (if available)
        try:
            import subprocess
            npm_root_result = subprocess.run(
                ["npm", "root"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if npm_root_result.returncode == 0:
                npm_root = Path(npm_root_result.stdout.strip())
                npm_header_path = (
                    npm_root
                    / "drtrace"
                    / "dist"
                    / "resources"
                    / "cpp"
                    / "drtrace_sink.hpp"
                )
                if npm_header_path.exists():
                    return npm_header_path
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            # npm not available or command failed - continue
            pass

        return None

    def _print_summary(self, config: dict) -> None:
        """Print initialization summary and next steps."""
        print("\n" + "=" * 50)
        print("✅ Project Initialization Complete!\n")

        print(f"📍 Configuration Location: {self.drtrace_dir}\n")

        print("📋 Generated Files:")
        print(f"   • {self.config_path}")
        for env in config.get("environments", []):
            print(f"   • {self.drtrace_dir / f'config.{env}.json'}")
        print(f"   • {self.drtrace_dir / '.env.example'}")
        print(f"   • {self.drtrace_dir / 'README.md'}")

        if config.get("agent", {}).get("enabled"):
            agents = ["log-analysis", "log-it", "log-init", "log-help"]
            for agent in agents:
                print(f"   • {self.drtrace_dir / 'agents' / f'{agent}.md'}")

        # For C++ language, surface the header-only C++ client header
        if config.get("language") in ("cpp", "both"):
            header_path = self.project_root / "third_party" / "drtrace" / "drtrace_sink.hpp"
            print(f"   • {header_path}  (C++ header-only client)")

        print("\n📖 Next Steps:")
        print(f"   1. Review {self.drtrace_dir / 'config.json'}")
        print(f"   2. Create .env: cp {self.drtrace_dir / '.env.example'} .env")
        print("   3. Start the daemon: python -m drtrace_service")
        print(f"   4. Read {self.drtrace_dir / 'README.md'} for more details")

        print("\n" + "=" * 50 + "\n")

    # --- NEW: suggestion display and apply hooks (placeholders for now) ---

    def _display_setup_suggestions(self, suggestions_markdown: str) -> None:
        """Display setup suggestions returned as markdown in a terminal-friendly way.

        For now, this simply prints the markdown with section separators. In future,
        this can be enhanced to use rich/markdown rendering.
        """
        print("\n" + "=" * 50)
        print("🧩 Setup Suggestions\n")
        print(suggestions_markdown)
        print("\n" + "=" * 50 + "\n")

    def _apply_setup_suggestions(self, suggestions_markdown: str) -> None:
        """Apply setup suggestions to the project.

        Currently implements:
        - **Python** setup suggestions (integration points + config changes)
        - **C++**: CMakeLists.txt FetchContent block (non-destructive)
        - **JavaScript/TypeScript**: Add `drtrace` dependency and append
          initialization examples to detected entry points
        """
        from drtrace_service.project_analyzer import analyze_project
        from drtrace_service.setup_suggestions import (
            generate_cpp_setup,
            generate_js_setup,
            generate_python_setup,
        )

        analysis = analyze_project(self.project_root)

        # Apply Python suggestions (setup_logging + config)
        py_suggestion = generate_python_setup(self.project_root, analysis=analysis)
        self._apply_python_setup_suggestions(py_suggestion)

        # Apply C++ suggestions (FetchContent block only, non-destructive)
        cpp_suggestion = generate_cpp_setup(self.project_root, analysis=analysis)
        self._apply_cpp_setup_suggestions(cpp_suggestion)

        # Apply JavaScript/TypeScript suggestions (dependency + init snippets)
        js_suggestion = generate_js_setup(self.project_root, analysis=analysis)
        self._apply_js_setup_suggestions(js_suggestion)

        # Simple verification / summary
        self._verify_applied_suggestions(py_suggestion, cpp_suggestion, js_suggestion)

        print("\n✅ Applied setup suggestions where possible.\n")

    # --- Python setup application helpers ---------------------------------

    def _backup_file(self, path: Path) -> None:
        """Create a timestamped backup of a file if it exists."""
        if not path.exists():
            return
        from datetime import datetime
        import shutil

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        backup_path = path.with_suffix(f"{path.suffix}.backup.{timestamp}")
        shutil.copy2(path, backup_path)
        print(f"   • Backup created: {backup_path}")

    def _apply_python_setup_suggestions(self, suggestion) -> None:
        """Apply Python integration and config changes based on suggestions."""
        # Integration points: insert setup_logging code into entry files
        for point in getattr(suggestion, "integration_points", []):
            file_path = point.file_path
            line_number = max(point.line_number, 1)
            self._backup_file(file_path)

            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except FileNotFoundError:
                # If the file doesn't exist, create it with the suggested code
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(point.suggested_code + "\n", encoding="utf-8")
                print(f"   • Created {file_path} with DrTrace setup code")
                continue

            idx = min(line_number - 1, len(lines))
            new_lines = lines[:idx] + ["", point.suggested_code, ""] + lines[idx:]
            file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print(f"   • Inserted Python setup code into {file_path} at line {line_number}")

        # Config changes: apply .env / requirements.txt / pyproject.toml updates
        for change in getattr(suggestion, "config_changes", []):
            target = change.file_path
            change_type = change.change_type

            if change_type in ("add_env_var", "modify_file"):
                self._backup_file(target)

            # Ensure parent directory exists for new files
            target.parent.mkdir(parents=True, exist_ok=True)

            if change_type == "create_file":
                target.write_text(change.content, encoding="utf-8")
                print(f"   • Created {target} with DrTrace configuration")
            elif change_type == "add_env_var":
                existing = target.read_text(encoding="utf-8") if target.exists() else ""
                if change.content not in existing:
                    with target.open("a", encoding="utf-8") as f:
                        if not existing.endswith("\n") and existing:
                            f.write("\n")
                        f.write(change.content)
                    print(f"   • Appended DrTrace env vars to {target}")
                else:
                    print(f"   • DrTrace env vars already present in {target}")
            elif change_type == "modify_file":
                # Simple append-based modification; avoids complex parsing
                existing = target.read_text(encoding="utf-8") if target.exists() else ""
                if change.content.strip() not in existing:
                    with target.open("a", encoding="utf-8") as f:
                        if not existing.endswith("\n") and existing:
                            f.write("\n")
                        f.write(change.content.rstrip() + "\n")
                    print(f"   • Appended DrTrace configuration to {target}")
                else:
                    print(f"   • Suggested change already present in {target}")

    # --- C++ setup application helpers ------------------------------------

    def _apply_cpp_setup_suggestions(self, suggestion) -> None:
        """Apply C++ FetchContent suggestions to CMakeLists.txt (non-destructive)."""
        from drtrace_service.setup_suggestions import CppSetupSuggestion  # type: ignore

        if not isinstance(suggestion, CppSetupSuggestion):
            return

        for change in getattr(suggestion, "cmake_changes", []):
            cmake_file = change.file_path
            if not cmake_file.exists():
                # Skip silently; analysis may have been optimistic
                continue

            self._backup_file(cmake_file)

            try:
                content = cmake_file.read_text(encoding="utf-8")
            except Exception:
                continue

            if change.suggested_code.strip() in content:
                # Already applied
                print(f"   • CMake FetchContent block already present in {cmake_file}")
                continue

            lines = content.splitlines()
            insert_idx = len(lines)

            # Determine insertion index based on insertion_point hint
            hint = (change.insertion_point or "").lower()
            if "include(fetchcontent)" in hint:
                for i, line in enumerate(lines):
                    if "include(FetchContent)" in line:
                        insert_idx = i + 1
                        break
            elif "project()" in hint:
                for i, line in enumerate(lines):
                    if line.strip().startswith("project("):
                        insert_idx = i + 1
                        break

            new_lines = (
                lines[:insert_idx]
                + ["", change.suggested_code, ""]
                + lines[insert_idx:]
            )
            cmake_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print(f"   • Inserted CMake FetchContent block into {cmake_file}")

    # --- JavaScript/TypeScript setup application helpers ------------------

    def _apply_js_setup_suggestions(self, suggestion) -> None:
        """Apply JS/TS suggestions: add drtrace dependency and init snippets."""
        from drtrace_service.setup_suggestions import JsSetupSuggestion  # type: ignore
        import json

        if not isinstance(suggestion, JsSetupSuggestion):
            return

        # 1. Update package.json dependencies with drtrace
        package_json = self.project_root / "package.json"
        if package_json.exists():
            self._backup_file(package_json)
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception:
                data = {}

            deps = data.get("dependencies") or {}
            if "drtrace" not in deps:
                deps["drtrace"] = "^0.2.0"
                data["dependencies"] = deps
                package_json.write_text(
                    json.dumps(data, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                print(f"   • Added drtrace dependency to {package_json}")
            else:
                print(f"   • drtrace dependency already present in {package_json}")

        # 2. Append initialization snippets to detected entry points
        for point in getattr(suggestion, "initialization_points", []):
            file_path = point.file_path
            self._backup_file(file_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            existing = ""
            if file_path.exists():
                try:
                    existing = file_path.read_text(encoding="utf-8")
                except Exception:
                    existing = ""

            # Avoid duplicating the exact snippet
            if point.suggested_code.strip() in existing:
                print(f"   • JS/TS init snippet already present in {file_path}")
                continue

            with file_path.open("a", encoding="utf-8") as f:
                if existing and not existing.endswith("\n"):
                    f.write("\n")
                f.write(
                    "\n\n// DrTrace initialization suggestion\n"
                    + point.suggested_code.rstrip()
                    + "\n"
                )
            print(f"   • Appended JS/TS initialization snippet to {file_path}")

    # --- Simple verification / reporting ----------------------------------

    def _verify_applied_suggestions(self, py_suggestion, cpp_suggestion, js_suggestion) -> None:
        """Basic verification that key suggestions were applied."""
        print("\n🔍 Verifying applied setup suggestions...")

        # Python: check that each integration file contains part of the suggested code
        for point in getattr(py_suggestion, "integration_points", []):
            file_path = point.file_path
            try:
                content = file_path.read_text(encoding="utf-8")
            except Exception:
                print(f"   • ⚠️ Could not verify Python setup in {file_path}")
                continue
            marker = "from drtrace_client import setup_logging"
            if marker in content:
                print(f"   • ✅ Python setup present in {file_path}")
            else:
                print(f"   • ⚠️ Python setup not detected in {file_path}")

        # C++: check CMakeLists.txt has FetchContent_Declare(drtrace)
        from drtrace_service.setup_suggestions import CppSetupSuggestion, JsSetupSuggestion  # type: ignore

        if isinstance(cpp_suggestion, CppSetupSuggestion):
            for change in getattr(cpp_suggestion, "cmake_changes", []):
                cmake_file = change.file_path
                try:
                    content = cmake_file.read_text(encoding="utf-8")
                except Exception:
                    print(f"   • ⚠️ Could not verify C++ setup in {cmake_file}")
                    continue
                if "FetchContent_Declare(" in content and "drtrace" in content:
                    print(f"   • ✅ CMake FetchContent for drtrace present in {cmake_file}")
                else:
                    print(f"   • ⚠️ CMake FetchContent for drtrace not detected in {cmake_file}")

        # JS: check package.json has drtrace dependency if file exists
        package_json = self.project_root / "package.json"
        if isinstance(js_suggestion, JsSetupSuggestion) and package_json.exists():
            import json

            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
            except Exception:
                print(f"   • ⚠️ Could not verify JS setup in {package_json}")
            else:
                deps = data.get("dependencies") or {}
                if "drtrace" in deps:
                    print(f"   • ✅ drtrace dependency present in {package_json}")
                else:
                    print(f"   • ⚠️ drtrace dependency not detected in {package_json}")


def run_init_project(project_root: Optional[Path] = None) -> int:
    """Entry point for init-project command."""
    try:
        initializer = ProjectInitializer(project_root)
        success = initializer.run_interactive()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Initialization cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}", file=sys.stderr)
        return 1
