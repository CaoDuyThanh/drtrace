# Version Downgrade Feature Design

**Author Role:** Architect  
**Audience:** Dev, SM  
**Date:** January 6, 2026

---

## Problem Statement

When using `make pump-major-version`, `make pump-minor-version`, or `make pump-patch-version`, developers may accidentally bump the version. Currently, there is no easy way to reverse this mistake without manually editing files and managing git history.

**Impact:** Developer friction, broken CI/CD pipelines, incorrect published versions.

---

## Design Goals

1. **Symmetry** — Mirror the bump commands with downgrade equivalents: `make downgrade-major-version`, `make downgrade-minor-version`, `make downgrade-patch-version`
2. **Safety** — Prevent downgrades that would conflict with existing tags or published releases
3. **Clarity** — Make it obvious what's happening (downgrade vs. bump)
4. **Reversibility** — Should be possible to downgrade, then re-bump if needed

---

## Proposed Architecture

### Command Surface

```bash
make downgrade-major-version    # e.g., 2.0.0 → 1.0.0 (decrement major, reset minor/patch)
make downgrade-minor-version    # e.g., 2.3.1 → 2.2.0 (decrement minor, reset patch)
make downgrade-patch-version    # e.g., 2.3.1 → 2.3.0 (decrement patch only)
```

### Behavior

1. **Read current version** from `VERSION` file
2. **Decrement** the target component (major/minor/patch)
3. **Reset lower components** (e.g., downgrade major → reset minor and patch to 0)
4. **Check preconditions:**
   - Ensure no git tag exists for the downgrades version (or allow force flag)
   - Warn if version is already published (advisory, not blocking)
5. **Update `VERSION` file**
6. **Commit** with message: `Downgrade version to X.Y.Z`
7. **Create tag** (annotated) with message: `Downgrade to X.Y.Z`
8. **Print result** to user: `Downgraded version from A.B.C to X.Y.Z`

### Safety Guards

| Scenario | Behavior |
|----------|----------|
| Downgrading from 0.0.0 | Fail with error: "Cannot downgrade from 0.0.0" |
| Tag for downgraded version already exists | Warn, offer `--force` flag to delete old tag and proceed |
| Version is already published (npm/PyPI) | Warn (info-only, don't block); let user decide |
| Uncommitted changes in working dir | Fail: "Working directory not clean" |

---

## Implementation Notes for Dev

### Makefile Changes

Add three new targets (similar to `pump-*-version` but with decrement logic):

```makefile
downgrade-major-version:
  @$(MAKE) _downgrade OP=major

downgrade-minor-version:
  @$(MAKE) _downgrade OP=minor

downgrade-patch-version:
  @$(MAKE) _downgrade OP=patch

_downgrade:
  @new=$$(python - <<'PY'
import sys
from pathlib import Path
v = Path('VERSION').read_text().strip()
major, minor, patch = map(int, v.split('.'))
op = sys.argv[1]
if op == 'major':
    if major == 0:
        sys.exit("Cannot downgrade from 0.0.0")
    major -= 1; minor = 0; patch = 0
elif op == 'minor':
    if minor == 0 and major == 0:
        sys.exit("Cannot downgrade below 0.0.0")
    if minor == 0:
        major -= 1; minor = 0; patch = 0
    else:
        minor -= 1; patch = 0
else:  # patch
    if patch == 0 and minor == 0 and major == 0:
        sys.exit("Cannot downgrade below 0.0.0")
    if patch == 0:
        if minor == 0:
            major -= 1; minor = 0; patch = 0
        else:
            minor -= 1; patch = 0
    else:
        patch -= 1
new = f"{major}.{minor}.{patch}"
Path('VERSION').write_text(new + "\n")
print(new)
PY
); \
  git add VERSION; \
  git commit -m "Downgrade version to $$new"; \
  git tag -a v$$new -m "Downgrade to $$new"; \
  @echo "✓ Downgraded to v$$new"
```

### Error Handling

- If Python snippet fails (e.g., can't parse version), `make` exits with non-zero
- If git operations fail, abort and inform user (don't leave partial state)

### Testing Strategy

- Unit test: Python version-decrement logic (edge cases: 0.0.0, major rollover, etc.)
- Integration test: `make downgrade-patch-version` on a test repo, verify VERSION file and git tags

---

## User Documentation

Add to [docs/versioning.md](docs/versioning.md) in the "One-line commands" section:

```markdown
### Downgrade (undo accidental bump)

Accidentally bumped? Downgrade with:

make downgrade-patch-version   # e.g., 1.2.5 → 1.2.4
make downgrade-minor-version   # e.g., 1.2.5 → 1.1.0
make downgrade-major-version   # e.g., 1.2.5 → 0.0.0

Then push the downgrade commit and tag:

git push origin HEAD
git push origin --tags
```

---

## Acceptance Criteria

- [ ] `make downgrade-{major,minor,patch}-version` commands exist and work
- [ ] Safety checks prevent downgrades below 0.0.0
- [ ] VERSION file is updated and committed
- [ ] Git tag is created for the new version
- [ ] User receives clear feedback (success or error)
- [ ] Edge cases (0.0.0, force flag, published versions) are handled
- [ ] Tests pass (unit + integration)
- [ ] Documentation is updated

---

## Questions for Dev Team

1. Should we add a `--force` flag to allow overwriting existing tags?
2. Should we query npm/PyPI to check if version is already published, or just warn based on local knowledge?
3. Do we want to support downgrading multiple steps at once (e.g., `--from 1.5.0 --to 1.4.0`)?
