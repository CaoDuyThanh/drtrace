#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path


VERSION_FILE = Path("VERSION")


def downgrade_major(major: int, minor: int, patch: int):
    if major > 0:
        return (major - 1, 0, 0)
    else:
        # Cannot downgrade from 0.x.x
        raise ValueError(f"Cannot downgrade major from {major}.{minor}.{patch}: already at 0.{minor}.{patch}")


def downgrade_minor(major: int, minor: int, patch: int):
    if minor > 0:
        return (major, minor - 1, 0)
    elif major > 0:
        # Cascade: decrement major when minor is 0
        return (major - 1, 0, 0)
    else:
        # At 0.0.X, cannot downgrade minor further
        raise ValueError(f"Cannot downgrade minor from {major}.{minor}.{patch}: already at 0.0.{patch}")


def downgrade_patch(major: int, minor: int, patch: int):
    if patch > 0:
        return (major, minor, patch - 1)
    elif minor > 0:
        # Cascade: decrement minor when patch is 0
        return (major, minor - 1, 0)
    else:
        # At X.0.0, cannot downgrade patch further
        raise ValueError(f"Cannot downgrade patch from {major}.{minor}.{patch}: already at {major}.0.0")


def parse_version(version_str: str):
    parts = version_str.strip().split(".")
    if len(parts) != 3:
        raise ValueError("Invalid version format: expected X.Y.Z")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        raise ValueError("Invalid version components: must be integers")


def format_version(major: int, minor: int, patch: int) -> str:
    return f"{major}.{minor}.{patch}"


def read_current_version() -> str:
    if not VERSION_FILE.exists():
        raise FileNotFoundError("VERSION file not found")
    return VERSION_FILE.read_text().strip()


def write_version(new_version: str):
    VERSION_FILE.write_text(new_version + "\n")


def validate_version_bounds(major: int, minor: int, patch: int) -> bool:
    if major < 0 or minor < 0 or patch < 0:
        print("ERROR: Cannot downgrade below 0.0.0")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description="Downgrade semantic version")
    parser.add_argument(
        "--operation",
        choices=["major", "minor", "patch"],
        required=True,
        help="Which component to downgrade",
    )
    args = parser.parse_args()

    try:
        current = read_current_version()
        major, minor, patch = parse_version(current)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    try:
        if args.operation == "major":
            n_major, n_minor, n_patch = downgrade_major(major, minor, patch)
        elif args.operation == "minor":
            n_major, n_minor, n_patch = downgrade_minor(major, minor, patch)
        else:
            n_major, n_minor, n_patch = downgrade_patch(major, minor, patch)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not validate_version_bounds(n_major, n_minor, n_patch):
        print(f"Current version: {current}")
        print("Downgrade requested would go below 0.0.0")
        sys.exit(1)

    new_version = format_version(n_major, n_minor, n_patch)

    try:
        write_version(new_version)
    except Exception as e:
        print(f"ERROR: Failed to write VERSION: {e}")
        sys.exit(1)

    print(f"✓ Downgraded to v{new_version}")
    sys.exit(0)


if __name__ == "__main__":
    main()
