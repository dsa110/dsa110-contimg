DC=docker compose -f ops/docker/docker-compose.yml
.DEFAULT_GOAL := help

.PHONY: help compose-build compose-up compose-down compose-logs compose-ps compose-restart compose-up-scheduler compose-up-stream compose-up-api compose-pull compose-down-service compose-stop docs-install docs-serve docs-build docs-deploy guardrails-check guardrails-fix ingest-docs test-catalog test-vla-catalog test-unit test-validation test-integration test-all test-quality update-todo-date

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
	@echo "  make test-unit                     Unit tests (mocked, no dependencies)"
	@echo "  make test-validation               Validation tests (requires casa6)"
	@echo "  make test-all                      Run all tests"
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
	@echo ""
	@echo "CI/CD Integration:"
	@echo "  Tests are configured for GitHub Actions in .github/workflows/validation-tests.yml"
	@echo ""
	@echo "Maintenance:"
	@echo "  make update-todo-date              Update TODO.md date to today (auto-runs on commit)"
	@echo "  make sync-linear                   Sync TODO.md items to Linear (see docs/LINEAR_INTEGRATION.md)"

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

# Guardrails targets
guardrails-check:
	@echo "Checking guardrails..."
	@python3 -m dsa110_contimg.guardrails.check

guardrails-fix:
	@echo "Fixing guardrails..."
	@python3 -m dsa110_contimg.guardrails.fix

# Ingest docs
ingest-docs:
	@echo "Ingesting documentation..."
	@python3 -m dsa110_contimg.ingest.docs

# Test targets
test-catalog:
	@echo "Testing catalog..."
	@python3 -m pytest tests/unit/test_catalog.py -v

test-vla-catalog:
	@echo "Testing VLA catalog..."
	@python3 -m pytest tests/unit/test_vla_catalog.py -v

test-unit:
	@echo "Running unit tests..."
	@python3 -m pytest tests/unit/ -v

test-validation:
	@echo "Running validation tests..."
	@echo "Note: These tests require casa6 to be installed and available"
	@python3 -m pytest tests/validation/ -v

test-integration:
	@echo "Running integration tests..."
	@python3 -m pytest tests/integration/ -v

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
	@echo "Unit Tests (test-unit):"
	@echo "  - Fast, isolated tests with mocked dependencies"
	@echo "  - No external dependencies required"
	@echo "  - Run with: make test-unit"
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
	@python3 scripts/update_todo_date.py

# Sync TODO.md to Linear
sync-linear:
	@python3 scripts/linear_sync.py

sync-linear-dry-run:
	@python3 scripts/linear_sync.py --dry-run
