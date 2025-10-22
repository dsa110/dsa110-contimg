DC=docker compose -f ops/docker/docker-compose.yml
.DEFAULT_GOAL := help

.PHONY: help compose-build compose-up compose-down compose-logs compose-ps compose-restart compose-up-scheduler compose-up-stream compose-up-api compose-pull compose-down-service compose-stop docs-install docs-serve docs-build docs-deploy guardrails-check guardrails-fix ingest-docs test-catalog test-vla-catalog

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
	@echo "Examples:"
	@echo "  make compose-build"
	@echo "  make compose-up"
	@echo "  make compose-logs SERVICE=stream"
	@echo "  make compose-restart SERVICE=api"
	@echo "  make compose-up-scheduler"
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
	$(DC) up -d schedulerProcee

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
