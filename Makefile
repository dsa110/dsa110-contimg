DC=docker compose -f ops/docker/docker-compose.yml
.DEFAULT_GOAL := help

.PHONY: help compose-build compose-up compose-down compose-logs compose-ps compose-restart compose-up-scheduler compose-up-stream compose-up-api compose-pull compose-down-service compose-stop docs-install docs-serve docs-build docs-deploy guardrails-check guardrails-fix ingest-docs test-catalog test-vla-catalog test-unit test-validation test-integration test-all test-quality

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
	@echo "Graphiti guardrails & docs ingestion:"
	@echo "  make guardrails-check            Check uuid/summary/embeddings for the graph group (default: dsa110-contimg)"
	@echo "  make guardrails-fix              Backfill uuid/summary, re-embed missing/mismatched vectors"
	@echo "  make ingest-docs                 Ingest README/quickstart/quicklook/pipeline and link to scripts"
	@echo "    Vars: GROUP_ID=<group> (default dsa110-contimg)"
	@echo ""
	@echo "Catalog builder smoke test (run in casa6):"
	@echo "  make test-catalog                Run scripts/test_catalog_builder.py using casa6"
	@echo "  make test-vla-catalog            Run scripts/test_ingest_vla_catalog.py using casa6"

docs-install:
	pip install -r docs/requirements.txt

docs-serve:
	PYTHONPATH=$(PWD)/src mkdocs serve -a 0.0.0.0:8001

docs-build:
	PYTHONPATH=$(PWD)/src mkdocs build -d site

docs-deploy:
	mkdocs gh-deploy

# Graphiti guardrails / ingestion helpers
UV?=/home/ubuntu/.local/bin/uv
GRAPHITI_SERVER_DIR?=/home/ubuntu/proj/mcps/graphiti/mcp_server
GROUP_ID?=dsa110-contimg

guardrails-check:
	$(UV) -q run --isolated --directory $(GRAPHITI_SERVER_DIR) \
	  python scripts/graphiti_guardrails_check.py --group-id $(GROUP_ID)

guardrails-fix:
	$(UV) -q run --isolated --directory $(GRAPHITI_SERVER_DIR) \
	  python scripts/graphiti_guardrails_check.py --group-id $(GROUP_ID) --fix

ingest-docs:
	$(UV) -q run --isolated --directory $(GRAPHITI_SERVER_DIR) \
	  python scripts/graphiti_ingest_docs.py --root $(PWD) --group-id $(GROUP_ID)

compose-build:
	$(DC) build

compose-up:
	$(DC) up -d

compose-down:
	$(DC) down

# Pull images (optionally for a single service)
compose-pull:
	$(DC) pull $(SERVICE)

compose-logs:
	$(DC) logs -f $(SERVICE)

compose-ps:
	$(DC) ps

compose-restart:
	$(DC) restart $(SERVICE)

# Stop (optionally) a single service without removing containers
compose-stop:
	$(DC) stop $(SERVICE)

# Bring up only the scheduler service
compose-up-scheduler:
	$(DC) up -d scheduler

# Bring up only the stream service
compose-up-stream:
	$(DC) up -d stream

# Bring up only the api service
compose-up-api:
	$(DC) up -d api

# Remove a single service's container(s)
compose-down-service:
	$(DC) rm -f $(SERVICE)

# Catalog builder smoke test (requires casa6 at /opt/miniforge/envs/casa6)
test-catalog:
	PYTHONPATH=$(PWD)/src /opt/miniforge/envs/casa6/bin/python scripts/test_catalog_builder.py

# VLA catalog ingestion smoke test (requires casa6)
test-vla-catalog:
	PYTHONPATH=$(PWD)/src /opt/miniforge/envs/casa6/bin/python scripts/test_ingest_vla_catalog.py

# ============================================================================
# Testing and Validation Targets for Enhanced Pipeline
# ============================================================================

# Unit tests (mocked, no dependencies)
test-unit:
	@echo "Running unit tests with mocking..."
	@if command -v pytest >/dev/null 2>&1; then \
		PYTHONPATH=$(PWD)/src pytest tests/unit/test_validation_functions.py -v; \
	else \
		echo "ERROR: pytest not found. Install with: pip install pytest"; \
		exit 1; \
	fi

# Validation tests (requires casa6 environment)
test-validation:
	@echo "Running validation tests in casa6 environment..."
	@if [ -f ./test_enhanced_pipeline_production.sh ]; then \
		chmod +x ./test_enhanced_pipeline_production.sh; \
		./test_enhanced_pipeline_production.sh; \
	else \
		echo "ERROR: test_enhanced_pipeline_production.sh not found"; \
		exit 1; \
	fi

# Integration tests (synthetic data + conversion)
test-integration:
	@echo "Running integration tests with synthetic data..."
	@if [ -d "/opt/miniforge/envs/casa6" ]; then \
		export PYTHONPATH=$(PWD)/src; \
		/opt/miniforge/envs/casa6/bin/python -m pytest tests/validation/test_pipeline_validation_integration.py -v; \
	else \
		echo "ERROR: casa6 environment not found at /opt/miniforge/envs/casa6"; \
		echo "Please install casa6 environment or modify path in Makefile"; \
		exit 1; \
	fi

# Code quality checks
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
	pip install -r requirements-test.txt

# Clean test artifacts
test-clean:
	@echo "Cleaning test artifacts..."
	rm -rf /tmp/dsa110_validation_test_*
	rm -rf /tmp/test_scenarios
	rm -rf .pytest_cache
	rm -rf tests/__pycache__
	rm -rf tests/unit/__pycache__
	rm -rf tests/validation/__pycache__
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Display test help
test-help:
	@echo "DSA-110 Pipeline Testing and Validation"
	@echo "========================================"
	@echo ""
	@echo "Test Types:"
	@echo "  make test-unit        Unit tests with mocking (no dependencies)"
	@echo "  make test-validation  Validation tests with synthetic data (requires casa6)"
	@echo "  make test-integration Integration tests (requires casa6)"
	@echo "  make test-quality     Code quality and style checks"
	@echo "  make test-all         Run all tests (unit -> validation -> integration)"
	@echo ""
	@echo "Utilities:"
	@echo "  make test-deps        Install test dependencies"
	@echo "  make test-clean       Clean test artifacts and cache files"
	@echo "  make test-help        Show this help message"
	@echo ""
	@echo "Requirements:"
	@echo "  - Unit tests: pytest (pip install pytest)"
	@echo "  - Validation/Integration tests: casa6 environment at /opt/miniforge/envs/casa6"
	@echo "  - Quality checks: flake8 (pip install flake8)"
	@echo ""
	@echo "Enhanced validation functions test:"
	@echo "  - Frequency ordering validation"
	@echo "  - UVW coordinate precision checks"
	@echo "  - Antenna position accuracy validation"
	@echo "  - MODEL_DATA quality assessment"
	@echo "  - Reference antenna stability analysis"
	@echo "  - CASA file handle cleanup verification"
	@echo ""
	@echo "CI/CD Integration:"
	@echo "  Tests are configured for GitHub Actions in .github/workflows/validation-tests.yml"
