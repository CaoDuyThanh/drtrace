#!/bin/bash
# sync-versions.sh - Synchronize version across all packages from VERSION file
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Read version from VERSION file
VERSION_FILE="$PROJECT_ROOT/VERSION"
if [ ! -f "$VERSION_FILE" ]; then
    echo "Error: VERSION file not found at $VERSION_FILE"
    exit 1
fi

VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')
if [ -z "$VERSION" ]; then
    echo "Error: VERSION file is empty"
    exit 1
fi

echo "Syncing all packages to version: $VERSION"
echo "================================================"

# Update JavaScript package.json
echo ""
echo "Updating JavaScript package.json..."
JS_PACKAGE="$PROJECT_ROOT/packages/javascript/drtrace-client"
cd "$JS_PACKAGE"
npm version "$VERSION" --no-git-tag-version --allow-same-version
echo "  JavaScript: $VERSION"
cd "$PROJECT_ROOT"

# Update Python pyproject.toml
echo ""
echo "Updating Python pyproject.toml..."
PYPROJECT="$PROJECT_ROOT/packages/python/pyproject.toml"
if [ "$(uname)" = "Darwin" ]; then
    # macOS sed requires different syntax
    sed -i '' "s/^version = \".*\"/version = \"$VERSION\"/" "$PYPROJECT"
else
    sed -i "s/^version = \".*\"/version = \"$VERSION\"/" "$PYPROJECT"
fi
echo "  Python: $VERSION"

# Update C++ header with DRTRACE_VERSION define
echo ""
echo "Updating C++ header..."
CPP_HEADER="$PROJECT_ROOT/packages/cpp/drtrace-client/src/drtrace_sink.hpp"
if [ -f "$CPP_HEADER" ]; then
    # Check if DRTRACE_VERSION already exists
    if grep -q "^#define DRTRACE_VERSION" "$CPP_HEADER"; then
        # Update existing define
        if [ "$(uname)" = "Darwin" ]; then
            sed -i '' "s/^#define DRTRACE_VERSION \".*\"/#define DRTRACE_VERSION \"$VERSION\"/" "$CPP_HEADER"
        else
            sed -i "s/^#define DRTRACE_VERSION \".*\"/#define DRTRACE_VERSION \"$VERSION\"/" "$CPP_HEADER"
        fi
    else
        # Add new define after #pragma once
        if [ "$(uname)" = "Darwin" ]; then
            sed -i '' "/^#pragma once$/a\\
#define DRTRACE_VERSION \"$VERSION\"
" "$CPP_HEADER"
        else
            sed -i "/^#pragma once$/a #define DRTRACE_VERSION \"$VERSION\"" "$CPP_HEADER"
        fi
    fi
    echo "  C++: $VERSION"
else
    echo "  C++ header not found, skipping"
fi

echo ""
echo "================================================"
echo "All packages synced to version $VERSION"
