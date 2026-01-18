"""Tests for setup.py build process.

Note: setup.py calls setup() at module level, which causes SystemExit when imported.
We test the _copy_integration_guides() method by directly testing the method logic
without importing the entire setup.py module. We replicate the method implementation
here for testing purposes.
"""

import shutil
import tempfile
from pathlib import Path


def _copy_integration_guides_test_impl(setup_dir: Path):
    """Test implementation of _copy_integration_guides() method.

    This replicates the logic from setup.py for testing purposes.
    """
    try:
        source_guides_dir = setup_dir.parent.parent / "agents" / "integration-guides"
        target_guides_dir = setup_dir / "src" / "drtrace_service" / "resources" / "agents" / "integration-guides"

        if not source_guides_dir.exists():
            print(f"Warning: Integration guides directory not found at {source_guides_dir}")
            return False

        # Create target directory
        target_guides_dir.mkdir(parents=True, exist_ok=True)

        # Copy all .md files from integration-guides
        guide_files = list(source_guides_dir.glob("*.md"))
        if not guide_files:
            print(f"Warning: No integration guide files found in {source_guides_dir}")
            return False

        copied_count = 0
        for guide_file in guide_files:
            target_file = target_guides_dir / guide_file.name
            shutil.copy2(guide_file, target_file)
            copied_count += 1
            print(f"Copied integration guide {guide_file.name} to {target_guides_dir}")

        if copied_count > 0:
            print(f"✓ Successfully copied {copied_count} integration guide file(s)")
            return True

        return False

    except Exception as e:
        print(f"Warning: Failed to copy integration guides: {e}")
        return False


class TestCopyIntegrationGuides:
    """Test _copy_integration_guides() method."""

    def test_copy_integration_guides_copies_files(self):
        """Test that integration guides are copied during build."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create directory structure matching monorepo layout:
            # wwi/
            #   packages/
            #     python/  <- setup_dir
            #   agents/
            #     integration-guides/  <- source_guides_dir

            # Create setup directory (represents packages/python/)
            setup_dir = tmp_path / "packages" / "python"
            setup_dir.mkdir(parents=True)

            # Create source directory (represents agents/integration-guides/)
            # setup_dir.parent.parent = tmp_path (project root)
            source_guides_dir = tmp_path / "agents" / "integration-guides"
            source_guides_dir.mkdir(parents=True)

            # Create test guide file
            test_guide = source_guides_dir / "test-guide.md"
            test_content = "# Test Guide\n\nThis is a test integration guide."
            test_guide.write_text(test_content)

            # Call the test implementation
            result = _copy_integration_guides_test_impl(setup_dir)

            # Verify file was copied
            target_guide = setup_dir / "src" / "drtrace_service" / "resources" / "agents" / "integration-guides" / "test-guide.md"
            assert target_guide.exists(), f"Integration guide was not copied. Expected at {target_guide}"
            assert target_guide.read_text() == test_content, "File content doesn't match"
            assert result is True, "Method should return True when files are copied"

    def test_copy_integration_guides_handles_missing_directory(self, capsys):
        """Test graceful handling when source directory doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create setup directory but no agents directory
            # Match monorepo structure: packages/python/
            setup_dir = tmp_path / "packages" / "python"
            setup_dir.mkdir(parents=True)

            # Call the test implementation
            result = _copy_integration_guides_test_impl(setup_dir)

            # Verify warning was printed and method returned False
            captured = capsys.readouterr()
            assert "Warning" in captured.out or "not found" in captured.out.lower()
            assert result is False, "Method should return False when directory doesn't exist"

    def test_copy_integration_guides_handles_empty_directory(self, capsys):
        """Test graceful handling when source directory is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Create setup directory (match monorepo structure)
            setup_dir = tmp_path / "packages" / "python"
            setup_dir.mkdir(parents=True)

            # Create empty source directory
            source_guides_dir = tmp_path / "agents" / "integration-guides"
            source_guides_dir.mkdir(parents=True)
            # Don't create any .md files

            # Call the test implementation
            result = _copy_integration_guides_test_impl(setup_dir)

            # Verify warning was printed and method returned False
            captured = capsys.readouterr()
            assert "Warning" in captured.out or "No integration guide files" in captured.out
            assert result is False, "Method should return False when directory is empty"
