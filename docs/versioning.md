# Versioning Architecture and How-to

This document describes the Makefile-based version-management system used in this repository and provides a reusable pattern architects can apply in other projects.

Goals
- Keep a single source-of-truth version file (`VERSION`) at repo root.
- Provide simple `make` targets to read, bump, and commit version changes.
- Provide small, testable shell scripts for cross-language packaging workflows (npm, pip) and for syncing version numbers across packages.
- Integrate the process into CI for consistent releases.

Core elements

- `VERSION` (file)
  - Contains a single semantic version string, e.g. `0.4.0`.
  - Read by Make targets and scripts.

- `Makefile` targets
  - `version` — prints the current version (reads `VERSION`).
  - `pump-major-version`, `pump-minor-version`, `pump-patch-version` — bump semver components, update `VERSION`, commit and tag.
  - `release` — runs packaging/publish steps (invokes scripts), optionally tags and pushes.

- Scripts directory (example `scripts/`)
  - `scripts/sync-versions.sh` — mirrors the `VERSION` value into package metadata files (e.g., `package.json`, `pyproject.toml`) or other language-specific places.
  - `scripts/publish-npm.sh` / `scripts/publish-pypi.sh` — wrapper scripts that ensure the published package versions match `VERSION` and perform the publish steps safely.

Design and rationale

- Single source of truth: using a plain `VERSION` file avoids parsing multiple manifests and keeps bumping simple.
- Make as user-facing interface: `make` is available everywhere and gives a compact command surface for developers and CI.
- Idempotent scripts: scripts should validate the version in the target manifest matches `VERSION` (or update it) before publishing to avoid accidental mismatch.
- Commit + tag: bumping should create a commit and an annotated Git tag `vX.Y.Z` to make releases traceable.

Example Makefile snippets

Add the following to your `Makefile` (POSIX shell assumed):

```

### Downgrade (undo accidental bump)

Accidentally bumped your version? Downgrade safely via Make targets.

#### Major Version Downgrade

Undo a major version bump (e.g., 2.0.0 → 1.0.0):

```bash
make downgrade-major-version
```

What happens:
- VERSION is set to one major lower, minor/patch reset to 0
- Example: 2.0.0 → 1.0.0, 5.3.2 → 4.0.0
- Git commit created: "Downgrade version to X.Y.Z"
- Annotated git tag created: vX.Y.Z

#### Minor Version Downgrade

Undo a minor bump (e.g., 2.3.1 → 2.2.0):

```bash
make downgrade-minor-version
```

Behavior:
- VERSION updated to one minor lower, patch reset to 0
- Example: 2.3.1 → 2.2.0, 1.5.0 → 1.4.0
- Git commit and tag created

#### Patch Version Downgrade

Undo a patch bump (e.g., 2.3.1 → 2.3.0):

```bash
make downgrade-patch-version
```

Behavior:
- VERSION updated to one patch lower
- Example: 2.3.1 → 2.3.0, 1.0.5 → 1.0.4
- Git commit and tag created

#### Push the Downgrade

After downgrading, push your changes and tags:

```bash
git push origin HEAD
git push origin --tags
```

Both are required: the first pushes the commit, the second pushes the annotated tag.

#### Safety Checks

The downgrade script enforces cascading semver logic:
- If patch > 0: decrement patch
- If patch = 0: decrement minor, reset patch to 0
- If minor = 0: decrement major, reset minor and patch to 0
- Cannot downgrade below 0.0.0
- Working directory must be clean (no uncommitted changes)
- Warns if tag exists; use force to overwrite:

Example cascading behavior:
- 1.2.3 → 1.2.2 (decrement patch)
- 1.2.0 → 1.1.0 (patch=0, decrement minor)
- 1.0.0 → 0.0.0 (minor=0, decrement major)
- 0.0.0 cannot be downgraded further

```bash
make FORCE=1 downgrade-major-version
```

#### Published Artifacts Responsibility

If you already published the higher version, you are responsible for:
- Removing artifacts from registries (PyPI, npm, etc.)
- Notifying users of the correction
- Documenting the downgrade in CHANGELOG

#### Troubleshooting

"Working directory must be clean": commit or stash changes first.

```bash
git add . && git commit -m "commit changes"
# OR
git stash
```

"Cannot downgrade below 0.0.0": you are at the minimum version.

"Tag vX.Y.Z already exists": force overwrite the tag.

```bash
make FORCE=1 downgrade-minor-version
```

#### Related Commands

```bash
cat VERSION                            # Show current version
make version-bump-patch                # Bump to next patch
make version-bump-minor                # Bump to next minor
make version-bump-major                # Bump to next major
make downgrade-major-version           # Downgrade to previous major
make downgrade-minor-version           # Downgrade to previous minor
make downgrade-patch-version           # Downgrade to previous patch
make version-sync                      # Sync versions across packages
```
VERSION_FILE := VERSION

version:
	@cat $(VERSION_FILE) || echo "0.0.0"

_read_version = $(shell cat $(VERSION_FILE))

_bump = \
	python - <<'PY'
import sys
from pathlib import Path
v = Path('$(VERSION_FILE)').read_text().strip()
major, minor, patch = map(int, v.split('.'))
op = sys.argv[1]
if op == 'major':
    major += 1; minor = 0; patch = 0
elif op == 'minor':
    minor += 1; patch = 0
else:
    patch += 1
new = f"{major}.{minor}.{patch}"
Path('$(VERSION_FILE)').write_text(new + "\n")
print(new)
PY

pump-major-version:
	@$(MAKE) _pump OP=major

pump-minor-version:
	@$(MAKE) _pump OP=minor

pump-patch-version:
	@$(MAKE) _pump OP=patch

_pump:
	@new=$$($(MAKE) --no-print-directory _bump $(OP)); \
	git add $(VERSION_FILE); \
	git commit -m "Bump version to $$new" || true; \
	git tag -a v$$new -m "Release $$new"; \
	@echo "Bumped and tagged v$$new"

release: pump-patch-version
	@./scripts/sync-versions.sh && ./scripts/publish-npm.sh && ./scripts/publish-pypi.sh
```

Notes on the snippet:
- The `_bump` helper uses a tiny Python snippet to produce a new semver and write it to `VERSION`.
- The Make targets call `_pump` to create a commit and annotated git tag.
- `release` composes bumping and publishing; you can adjust to require manual approval or CI gating.

Example `scripts/sync-versions.sh` behavior

Implement a script that:
1. Reads `VERSION`.
2. Updates language-specific manifest files (for example, sets `package.json` `version` to `VERSION` and updates `pyproject.toml` or `setup.cfg`).
3. Runs quick validation (e.g., `npm pack --dry-run`, `python -m build --sdist --wheel --check`) to ensure packaging is consistent.
4. Optionally commit manifest changes if they were modified automatically, or fail early and instruct the user to review.

Safe publishing workflow (recommended)

1. Bump version locally using a `make pump-*` target.
2. Push the branch to the remote: `git push origin HEAD`.
3. Push tags: `git push origin --tags` (often done by CI after merge to main).
4. CI verifies the version, runs `scripts/sync-versions.sh`, runs integration tests, and then runs publish scripts from a protected pipeline job.

CI checklist for publishing job
- Ensure job runs only on protected branches or manual approval.
- Ensure environment secrets (npm token, PyPI API token) are available but never printed.
- Verify `VERSION` matches any manifest `version` fields and fail otherwise.
- Tag and create release notes automatically from `CHANGELOG.md` (optional).

Architect guidance for adoption in other projects

- Keep the pattern small: `VERSION` + one Makefile target surface + a couple of scripts is enough for most projects.
- Prefer tools you already have in your org (shell, Python, Make) rather than introducing heavy tooling.
- Keep scripts idempotent and safe: validate before publishing, require CI for final publish step.
- Record exact steps in a `docs/versioning.md` (this file) so other architects can replicate and adapt.

Appendix: One-line commands

- Print current version:

```
make version
```

- Bump patch and tag locally:

```
make pump-patch-version
git push origin HEAD
git push origin --tags
```

- Release (bump patch + sync + publish):

```
make release
```

Useful references
- Semantic Versioning: https://semver.org/
- Git tagging best practices: prefer annotated tags for releases

---

If you want, I can also:
- Convert the Makefile snippet into a standalone portable `bump-version.sh` script.
- Create a CI example for GitHub Actions that performs the protected publish flow.
