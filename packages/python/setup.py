"""Setup script for DrTrace Python package.

This setup script includes a custom build_py command that copies agent spec files
from the monorepo root to the package directory before building, similar to how
the JavaScript package uses a prebuild hook.
"""

from pathlib import Path
import shutil
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPyCommand(build_py):
    """Custom build command that copies agent files before building."""

    def run(self):
        """Run the build process, copying agent files first."""
        # Copy agent files before building
        self._copy_agent_files()
        # Run normal build
        super().run()

    def _copy_agent_files(self):
        """Copy all files from agents/ directory to package directory.
        
        Copies everything under agents/ including:
        - Agent spec files (*.md)
        - Integration guides (integration-guides/*.md)
        - Any other files (README.md, CONTRIBUTING.md, etc.)
        """
        try:
            # Use resolve() to get absolute paths
            setup_dir = Path(__file__).parent.resolve()
            agents_dir = setup_dir.parent.parent / "agents"
            target_dir = setup_dir / "src" / "drtrace_service" / "resources" / "agents"

            # Check if agents directory exists
            if not agents_dir.exists():
                print(f"Warning: Agents directory not found at {agents_dir}")
                print(f"  Setup directory: {setup_dir}")
                print("  Continuing build without agent files (may cause issues)")
                return

            # Create target directory if it doesn't exist
            target_dir.mkdir(parents=True, exist_ok=True)

            # Copy all files from agents/ directory recursively
            copied_count = 0
            for source_file in agents_dir.rglob("*"):
                # Skip directories
                if source_file.is_dir():
                    continue
                
                # Calculate relative path and target file
                relative_path = source_file.relative_to(agents_dir)
                target_file = target_dir / relative_path
                
                # Create parent directories if needed
                target_file.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file (no renaming needed - files are already named correctly)
                shutil.copy2(source_file, target_file)
                copied_count += 1
                print(f"Copied {relative_path}")

            if copied_count > 0:
                print(f"✓ Successfully copied {copied_count} file(s) from agents/")

        except Exception as e:
            print(f"Warning: Failed to copy agent files: {e}")
            print("  Continuing build without agent files (may cause issues)")
            # Continue build even if copy fails (graceful degradation)



# Read pyproject.toml to get metadata
# Note: setuptools will read pyproject.toml automatically, but we need to register
# the custom command. We'll use setup() with minimal config since pyproject.toml
# handles most of it.
setup(
    cmdclass={"build_py": BuildPyCommand},
    # All other configuration comes from pyproject.toml
)

