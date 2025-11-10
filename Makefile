SHELL := bash
# Enforce strict error handling and pipefail across all recipes
.SHELLFLAGS := -eu -o pipefail -c

DC=docker compose -f ops/docker/docker-compose.yml
.DEFAULT_GOAL := help

# CRITICAL: All Python execution MUST use casa6 environment
# This is the ONLY Python environment used by the DSA-110 pipeline
# Path: /opt/miniforge/envs/casa6/bin/python
# Python version: 3.11.13 (in casa6 conda environment)
# Never use system python3 - it will fail due to missing CASA dependencies
# Warning suppression: -W ignore::DeprecationWarning suppresses SWIG-generated warnings
CASA6_PYTHON := /opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning
CASA6_PYTHON_CHECK := $(shell test -x /opt/miniforge/envs/casa6/bin/python && echo "ok" || echo "missing")

.PHONY: help compose-build compose-up compose-down compose-logs compose-ps compose-restart compose-up-scheduler compose-up-stream compose-up-api compose-pull compose-down-service compose-stop docs-install docs-serve docs-build docs-deploy docs-test-mermaid guardrails-check guardrails-fix ingest-docs test-smoke test-unit test-fast test-impacted test-validation test-integration test-all test-quality update-todo-date frontend-build frontend-build-docker

help:
	@echo "DSA-110 Continuum Pipeline - Docker Compose helper targets"
	@echo ""
	@echo "Prerequisites:"
	@echo "  1) Copy ops/docker/.env.example to ops/docker/.env and edit values"
	@echo "     - Set absolute host paths for: REPO_ROOT, CONTIMG_INPUT_DIR, CONTIMG_OUTPUT_DIR, CONTIMG_SCRATCH_DIR, CONTIMG_STATE_DIR"
	@echo "     - Set DB paths: CONTIMG_QUEUE_DB, CONTIMG_REGISTRY_DB, CONTIMG_PRODUCTS_DB"
	@echo "     - Set ports and user mapping: CONTIMG_API_PORT, UID, GID"
	@echo "  2) Ensure the above directories exist on the host and are writable by UID:GID"
	@echo "  3) From repo root, run these make targets (they reference ops/docker/docker-compose.yml)"
	@echo ""
	@echo "General:"
	@echo "  make compose-build                 Build images"
	@echo "  make compose-up                    Start all services"
	@echo "  make compose-down                  Stop and remove all services"
	@echo "  make compose-ps                    Show service status"
	@echo "  make compose-pull [SERVICE=name]   Pull images (all or one service)"
	@echo "  make compose-stop [SERVICE=name]   Stop services (all or one)"
	@echo "  make compose-restart [SERVICE=name]Restart services (all or one)"
	@echo "  make compose-logs [SERVICE=name]   Follow logs (all or one)"
	@echo ""
	@echo "Service-specific up:"
	@echo "  make compose-up-stream             Start only the stream service"
	@echo "  make compose-up-api                Start only the api service"
	@echo "  make compose-up-scheduler          Start only the scheduler service"
	@echo ""
	@echo "Testing & Validation:"
	@echo "  make test-help                     Show detailed testing help"
	@echo "  make test-smoke                    Ultra-fast smoke (few files)"
	@echo "  make test-fast                     Fast unit subset (fail-fast)"
	@echo "  make test-unit                     Unit tests (requires casa6)"
	@echo "  make test-validation               Validation tests (requires casa6)"
	@echo "  make test-all                      Run all tests"
	@echo "  make frontend-test-smoke           Frontend API smoke via Vitest"
	@echo "  make frontend-test-smoke-docker    Frontend API smoke in Docker"
	@echo ""
	@echo "CRITICAL: All Python execution uses casa6 environment:"
	@echo "  Python path: /opt/miniforge/envs/casa6/bin/python"
	@echo "  Python version: 3.11.13 (in casa6 conda environment)"
	@echo "  Warning suppression: -W ignore::DeprecationWarning (suppresses SWIG warnings)"
	@echo "  Never use system python3 - it will fail!"
	@echo ""
	@echo "Examples:"
	@echo "  make compose-build"
	@echo "  make compose-up"
	@echo "  make compose-logs SERVICE=stream"
	@echo "  make compose-restart SERVICE=api"
	@echo "  make compose-up-scheduler"
	@echo "  make test-validation               # Test enhanced pipeline"
	@echo ""
	@echo "Docs:"
	@echo "  mkdocs.yml config present; to serve docs locally (if mkdocs installed):"
	@echo "    pip install -r docs/requirements.txt && mkdocs serve -a 0.0.0.0:8001"
	@echo "  build: make docs-build    | deploy to GitHub Pages: make docs-deploy"
	@echo "  test Mermaid diagrams: make docs-test-mermaid"
	@echo ""
	@echo "CI/CD Integration:"
	@echo "  Tests are configured for GitHub Actions in .github/workflows/validation-tests.yml"
	@echo ""
	@echo "Maintenance:"
	@echo "  make update-todo-date              Update TODO.md date to today (auto-runs on commit)"
	@echo "  make sync-linear                   Sync TODO.md items to Linear (see docs/LINEAR_INTEGRATION.md)"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend-build                 Build frontend using casa6 Node.js (preferred)"
	@echo "  make frontend-build-docker         Build frontend using Docker (fallback if casa6 unavailable)"

# Docker Compose targets
compose-build:
	$(DC) build

compose-up:
	$(DC) up -d

compose-down:
	$(DC) down

compose-logs:
	@if [ -z "$(SERVICE)" ]; then \
		$(DC) logs -f; \
	else \
		$(DC) logs -f $(SERVICE); \
	fi

compose-ps:
	$(DC) ps

compose-pull:
	@if [ -z "$(SERVICE)" ]; then \
		$(DC) pull; \
	else \
		$(DC) pull $(SERVICE); \
	fi

compose-stop:
	@if [ -z "$(SERVICE)" ]; then \
		$(DC) stop; \
	else \
		$(DC) stop $(SERVICE); \
	fi

compose-restart:
	@if [ -z "$(SERVICE)" ]; then \
		$(DC) restart; \
	else \
		$(DC) restart $(SERVICE); \
	fi

compose-down-service:
	@if [ -z "$(SERVICE)" ]; then \
		echo "Error: SERVICE variable required. Usage: make compose-down-service SERVICE=name"; \
		exit 1; \
	fi
	$(DC) rm -f -s $(SERVICE)

# Service-specific up targets
compose-up-stream:
	$(DC) up -d stream

compose-up-api:
	$(DC) up -d api

compose-up-scheduler:
	$(DC) up -d scheduler

# Docs targets
docs-install:
	pip install -r docs/requirements.txt

docs-serve:
	mkdocs serve -a 0.0.0.0:8001

docs-build:
	mkdocs build

docs-deploy:
	mkdocs gh-deploy

docs-test-mermaid:
	@echo "Testing Mermaid diagram rendering..."
	@if ! command -v playwright > /dev/null 2>&1; then \
		echo "Installing Playwright..."; \
		pip install playwright; \
		playwright install chromium; \
	fi
	@python3 tests/docs/test_mermaid_diagrams.py

# Guardrails targets
guardrails-check:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@echo "Checking guardrails..."
	@$(CASA6_PYTHON) scripts/graphiti_guardrails_check.py --check

guardrails-fix:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@echo "Fixing guardrails..."
	@$(CASA6_PYTHON) scripts/graphiti_guardrails_check.py --fix

ingest-docs:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@echo "Ingesting documentation into Graphiti..."
	@$(CASA6_PYTHON) scripts/graphiti_ingest_docs.py

# Test targets
# Note: test-catalog and test-vla-catalog removed - test files do not exist
# Use test-unit to run all unit tests instead

test-unit:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@echo "Running unit tests..."
	@$(CASA6_PYTHON) -m pytest tests/unit/ -v

# Ultra-fast smoke suite (few, representative tests)
test-smoke:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@echo "Running ultra-fast smoke tests..."
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLBACKEND=Agg \
	$(CASA6_PYTHON) -m pytest -q -x --maxfail=1 \
		tests/test_pipeline.py \
		tests/unit/test_cli_calibration_args.py

# Fast unit tests (fail fast, minimal scope)
test-fast:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@echo "Running fast unit test subset (fail-fast, minimal logging)..."
	@PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 MPLBACKEND=Agg \
	$(CASA6_PYTHON) -m pytest tests/unit -q -x --maxfail=1 \
		-m "unit and not slow and not integration and not casa" \
		-k "not imaging and not masking and not nvss"

# Frontend smoke tests (Vitest)
frontend-test-smoke:
	@echo "Running frontend smoke tests..."
	@if [ -x "/opt/miniforge/envs/casa6/bin/npm" ]; then \
		cd frontend && NODE_OPTIONS=--experimental-global-webcrypto /opt/miniforge/envs/casa6/bin/npm run test --silent -- --run --reporter=dot; \
	else \
		cd frontend && NODE_OPTIONS=--experimental-global-webcrypto npm run test --silent -- --run --reporter=dot; \
	fi

frontend-test-smoke-docker:
	@echo "Running frontend smoke tests in Docker..."
	@cd frontend && \
	IMAGE_NAME="dsa110-frontend-test"; \
	if ! docker images | grep -q "$$IMAGE_NAME"; then \
	  echo "Building Docker image..."; \
	  docker build -t "$$IMAGE_NAME" -f Dockerfile.dev .; \
	fi; \
	docker run --rm -v "$(PWD)/frontend:/app" -w /app "$$IMAGE_NAME" \
	  sh -c "npm ci --silent || true; npm test -- src/api/__tests__/client.smoke.test.ts --run --reporter=dot"

# Impacted tests runner (maps changes to tests)
test-impacted:
	@echo "Running impacted tests via scripts/test-impacted.sh (BASE_REF=$${BASE_REF:-HEAD~1})..."
	@bash scripts/test-impacted.sh "$${BASE_REF:-}" || bash scripts/test-impacted.sh

test-validation:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@echo "Running validation tests..."
	@echo "Using casa6 environment: $(CASA6_PYTHON)"
	@$(CASA6_PYTHON) -m pytest tests/validation/ -v

test-integration:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@echo "Running integration tests..."
	@$(CASA6_PYTHON) -m pytest tests/integration/ -v

test-quality:
	@echo "Running code quality checks..."
	@echo "Checking validation function formatting..."
	@if command -v flake8 >/dev/null 2>&1; then \
		flake8 src/dsa110_contimg/conversion/helpers.py --max-line-length=79 --extend-ignore=E203,W503; \
	else \
		echo "WARNING: flake8 not found. Install with: pip install flake8"; \
	fi
	@echo "Checking for TODO/FIXME markers in validation code..."
	@grep -n "TODO\|FIXME" src/dsa110_contimg/conversion/helpers.py || echo "No TODO/FIXME found in validation code"

# Run all tests
test-all: test-quality test-unit test-validation test-integration
	@echo "All validation tests completed!"

# Install test dependencies
test-deps:
	@echo "Installing test dependencies..."
	@pip install -r requirements-test.txt 2>/dev/null || echo "requirements-test.txt not found, skipping..."

# Test help
test-help:
	@echo "Testing Help:"
	@echo ""
	@echo "Fast Tests (test-fast):"
	@echo "  - Unit-only, fail-fast subset"
	@echo "  - Excludes slow/integration/casa markers"
	@echo "  - Run with: make test-fast"
	@echo ""
	@echo "Unit Tests (test-unit):"
	@echo "  - Fast, isolated tests with mocked dependencies"
	@echo "  - No external dependencies required"
	@echo "  - Run with: make test-unit"
	@echo ""
	@echo "Impacted Tests (test-impacted):"
	@echo "  - Maps changed files to relevant tests"
	@echo "  - Uses scripts/test-impacted.sh; set BASE_REF to compare against"
	@echo "  - Run with: make test-impacted or BASE_REF=origin/main make test-impacted"
	@echo ""
	@echo "Validation Tests (test-validation):"
	@echo "  - Tests that require casa6 installation"
	@echo "  - May take longer to run"
	@echo "  - Run with: make test-validation"
	@echo ""
	@echo "Integration Tests (test-integration):"
	@echo "  - End-to-end workflow tests"
	@echo "  - May require external services"
	@echo "  - Run with: make test-integration"
	@echo ""
	@echo "Quality Checks (test-quality):"
	@echo "  - Code formatting and style checks"
	@echo "  - Run with: make test-quality"
	@echo ""
	@echo "All Tests (test-all):"
	@echo "  - Runs all test suites"
	@echo "  - Run with: make test-all"
	@echo ""
	@echo "CI/CD Integration:"
	@echo "  Tests are configured for GitHub Actions in .github/workflows/validation-tests.yml"

# Update TODO.md date automatically
update-todo-date:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@$(CASA6_PYTHON) scripts/update_todo_date.py

# Sync TODO.md to Linear
sync-linear:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@$(CASA6_PYTHON) scripts/linear_sync.py

sync-linear-dry-run:
	@if [ "$(CASA6_PYTHON_CHECK)" != "ok" ]; then \
		echo "ERROR: casa6 Python not found at $(CASA6_PYTHON)"; \
		echo "Please ensure casa6 conda environment is installed at /opt/miniforge/envs/casa6"; \
		exit 1; \
	fi
	@$(CASA6_PYTHON) scripts/linear_sync.py --dry-run

# Frontend build using casa6 Node.js (preferred) or Docker (fallback)
# casa6 has Node.js v22.6.0 which meets all requirements
frontend-build:
	@echo "Building frontend (using casa6 Node.js if available, Docker otherwise)..."
	@bash scripts/build-frontend-docker.sh

# Alias for backward compatibility
frontend-build-docker: frontend-build
	@echo "(Note: This target now uses casa6 Node.js when available)"
