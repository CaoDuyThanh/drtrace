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


