"""Entry point for python -m drtrace command.

This module provides the CLI entry point for `python -m drtrace`,
which is an alias to `python -m drtrace_service` for consistency
with the npm CLI pattern (`npx drtrace`).
"""

from drtrace_service.__main__ import main

if __name__ == "__main__":
    main()

