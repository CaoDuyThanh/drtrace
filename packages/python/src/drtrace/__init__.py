"""DrTrace package alias for backward compatibility and consistency with npm CLI.

This package provides an alias to drtrace_service, allowing users to use
`python -m drtrace` instead of `python -m drtrace_service` for consistency
with the npm CLI pattern (`npx drtrace`).
"""

# Import everything from drtrace_service for backward compatibility
from drtrace_service import *  # noqa: F403, F401

