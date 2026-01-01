#!/bin/bash
# publish-pypi.sh - Publish Python package to PyPI
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PY_PACKAGE="$PROJECT_ROOT/packages/python"

# Parse arguments
DRY_RUN=false
SKIP_TESTS=false
USE_TEST_PYPI=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --test-pypi)
            USE_TEST_PYPI=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--skip-tests] [--test-pypi]"
            exit 1
            ;;
    esac
done

echo "================================================"
echo "Publishing PyPI package: drtrace"
echo "================================================"

cd "$PY_PACKAGE"

# Get version from pyproject.toml
VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "Version: $VERSION"
echo ""

# Run tests unless skipped
if [ "$SKIP_TESTS" = false ]; then
    echo "Running tests..."
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    fi
    pytest tests/
    echo ""
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info
echo ""

# Build
echo "Building..."
python -m build
echo ""

# Check dist
echo "Built packages:"
ls -la dist/
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "Dry run - would publish version $VERSION"
    echo "Package contents:"
    python -m twine check dist/*
else
    # Determine repository
    if [ "$USE_TEST_PYPI" = true ]; then
        REPO_URL="https://test.pypi.org/legacy/"
        REPO_NAME="TestPyPI"
        echo "Publishing to TestPyPI..."
    else
        REPO_URL=""
        REPO_NAME="PyPI"
    fi

    echo ""
    echo "About to publish version $VERSION to $REPO_NAME"
    read -p "Continue? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ "$USE_TEST_PYPI" = true ]; then
            python -m twine upload --repository-url "$REPO_URL" dist/*
        else
            python -m twine upload dist/*
        fi
        echo ""
        echo "Successfully published drtrace==$VERSION to $REPO_NAME"
    else
        echo "Publish cancelled"
        exit 1
    fi
fi
