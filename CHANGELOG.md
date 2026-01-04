
# CHANGELOG
All notable changes to this project will be documented in this file.
- **Added** - for new features.
- **Changed** - for changes in existing functionality.
- **Fixed** - for bug fixes.

## v0.4.0

### Added

- Browser and Node.js JavaScript client support with a unified API, enabling frontend and backend logging ingestion and analysis.
- New automated publishing scripts (`scripts/publish-npm.sh`, `scripts/publish-pypi.sh`) and a version sync helper.
- Expanded Python API query functionality and time-series storage improvements.
- Significant test coverage for API/querying (including cross-language scenarios) and browser tests for the JS client.

### Changed

- Updated README and package metadata for JavaScript and Python packages.
- Improved initialization and logging behavior in both JS and Python clients; transport and packaging refinements (Makefile updates).

### Fixed

- Minor fixes to transport/interop and a small C++ header tweak; addressing test failures and cross-language query edge cases.
