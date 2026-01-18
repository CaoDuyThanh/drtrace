#!/bin/bash
# publish-npm.sh - Publish JavaScript package to npm
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
JS_PACKAGE="$PROJECT_ROOT/packages/javascript/drtrace-client"

# Parse arguments
DRY_RUN=false
SKIP_TESTS=false
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
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--skip-tests]"
            exit 1
            ;;
    esac
done

echo "================================================"
echo "Publishing npm package: drtrace"
echo "================================================"

cd "$JS_PACKAGE"

# Get version
VERSION=$(node -p "require('./package.json').version")
echo "Version: $VERSION"
echo ""

# Run tests unless skipped
if [ "$SKIP_TESTS" = false ]; then
    echo "Running tests..."
    npm test
    echo ""
fi

# Build
echo "Building..."
npm run build
echo ""

# Check if logged in to npm
if ! npm whoami > /dev/null 2>&1; then
    echo "Error: Not logged in to npm. Run 'npm login' first."
    exit 1
fi

# Publish
if [ "$DRY_RUN" = true ]; then
    echo "Dry run - would publish version $VERSION"
    npm publish --dry-run
else
    echo ""
    echo "About to publish version $VERSION to npm"
    read -p "Continue? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        npm publish
        echo ""
        echo "Successfully published drtrace@$VERSION to npm"
    else
        echo "Publish cancelled"
        exit 1
    fi
fi
