VENV?=.venv
PYTHON?=python3

.PHONY: venv
venv:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r packages/python/requirements.txt

.PHONY: test
test:
	@mkdir -p packages/python/src/drtrace_service/resources/agents
	@cp agents/*.md packages/python/src/drtrace_service/resources/agents/ 2>/dev/null || true
	$(VENV)/bin/pip install -e packages/python
	$(VENV)/bin/pytest packages/python/tests

.PHONY: develop-install
develop-install: venv
	@mkdir -p packages/python/src/drtrace_service/resources/agents
	@cp agents/*.md packages/python/src/drtrace_service/resources/agents/ 2>/dev/null || true
	$(VENV)/bin/pip install -e packages/python

# Version management
.PHONY: version-sync version-bump-patch version-bump-minor version-bump-major

version-sync:
	@chmod +x scripts/sync-versions.sh
	@./scripts/sync-versions.sh

version-bump-patch:
	@VERSION=$$(cat VERSION | tr -d '[:space:]'); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	PATCH=$$(echo $$VERSION | cut -d. -f3); \
	NEW_PATCH=$$((PATCH + 1)); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$NEW_PATCH"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "Bumped version to $$NEW_VERSION"; \
	$(MAKE) version-sync

version-bump-minor:
	@VERSION=$$(cat VERSION | tr -d '[:space:]'); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	NEW_MINOR=$$((MINOR + 1)); \
	NEW_VERSION="$$MAJOR.$$NEW_MINOR.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "Bumped version to $$NEW_VERSION"; \
	$(MAKE) version-sync

version-bump-major:
	@VERSION=$$(cat VERSION | tr -d '[:space:]'); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	NEW_MAJOR=$$((MAJOR + 1)); \
	NEW_VERSION="$$NEW_MAJOR.0.0"; \
	echo "$$NEW_VERSION" > VERSION; \
	echo "Bumped version to $$NEW_VERSION"; \
	$(MAKE) version-sync


