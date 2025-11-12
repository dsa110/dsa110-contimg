# DSA-110 Continuum Imaging Pipeline - Top-Level Project Analysis

**Analysis Date:** 2025-01-XX  
**Tool:** Desktop Commander  
**Scope:** Complete project ecosystem (beyond `src/`)

## Executive Summary

This analysis examines the **complete DSA-110 continuum imaging pipeline project** from the top-level directory, revealing a comprehensive production system with:

- **147 Python modules** across source, scripts, operations, and tests
- **11 shell scripts** for operational automation
- **Multi-tier deployment** (systemd, Docker Compose, manual)
- **Full-stack architecture** (Python backend, React frontend)
- **Comprehensive operational tooling** (housekeeping, monitoring, testing)

---

## 1. Project Structure Overview

### Directory Hierarchy

```
/data/dsa110-contimg/
├── src/                    # Core Python package (100 modules, ~25K lines)
├── frontend/              # React/TypeScript dashboard (Vite + MUI)
├── ops/                   # Operational infrastructure
│   ├── docker/           # Containerized deployment
│   ├── systemd/          # Service management
│   └── pipeline/        # Operational scripts
├── scripts/               # Utility scripts (27 Python + 7 shell)
├── tests/                # Test suites
├── docs/                 # Comprehensive documentation (MkDocs)
├── state/                # Runtime state (DBs, logs, QA artifacts)
├── references/           # External library references
├── archive/              # Legacy code preservation
└── config/               # Configuration templates
```

### Key Project Files

**Root Level:**
- `README.md` - Project overview and quick start
- `Makefile` - Docker Compose helpers, docs, Graphiti tasks
- `MEMORY.md` - Project memory and lessons learned (2,000+ lines)
- `mkdocs.yml` - Documentation site configuration
- `docker-compose.yml` - Root-level compose (if used)
- `package.json` - Node.js dependencies (Socket.io, JS9)

**Configuration:**
- `ops/systemd/contimg.env` - Centralized environment variables (105 lines)
- `ops/docker/.env` - Docker deployment configuration
- `ops/docker/Dockerfile` - Multi-stage container image
- `ops/docker/environment.yml` - Conda environment specification

---

## 2. Operational Infrastructure

### Service Management

**Systemd Services** (`ops/systemd/`):
- `contimg-stream.service` - Streaming worker daemon
- `contimg-api.service` - FastAPI monitoring API
- `contimg-test-monitor.service` - Test monitoring daemon
- `contimg.env` - Shared environment configuration

**Service Management Script** (`scripts/manage-services.sh` - 486 lines):
- Port conflict detection and resolution
- PID tracking in `/var/run/dsa110/`
- Logging to `/var/log/dsa110/`
- Color-coded status output
- Supports: `start`, `stop`, `restart`, `status`, `logs`
- Auto-configures ports: API (8000), Dashboard (3210), Docs (8001)

**Key Features:**
- Process tree killing (handles conda/bash wrappers)
- Automatic port conflict resolution
- Background process management
- Service health checking

### Docker Deployment

**Docker Compose** (`ops/docker/docker-compose.yml`):
- **3 services:** `stream`, `api`, `scheduler`
- **Volume mounts:** Code, data directories, state DBs
- **Network:** `contimg-net` (isolated)
- **User mapping:** Configurable UID/GID (default 1000:1000)
- **Restart policy:** `unless-stopped`

**Dockerfile** (`ops/docker/Dockerfile`):
- Base: `mambaorg/micromamba:1.5.9-focal`
- Environment: `contimg` conda env from `environment.yml`
- Code: Volume-mounted (development-friendly)
- Sanity checks: Python version, CASA/pyuvdata imports

**Makefile Targets:**
- `make compose-build` - Build images
- `make compose-up` - Start all services
- `make compose-up-api` - Start only API
- `make compose-up-stream` - Start only streaming worker
- `make compose-logs SERVICE=stream` - View logs

---

## 3. Operational Scripts

### Core Operational Scripts (`scripts/`)

**Shell Scripts (7 total):**
1. `manage-services.sh` - Service lifecycle management
2. `run_conversion.sh` - Manual conversion runner
3. `image_ms.sh` - Manual imaging runner
4. `calibrate_bandpass.sh` - Calibration runner
5. `cleanup_casa_logs.sh` - Log cleanup utility
6. `move_casa_logs.sh` - Log migration utility
7. `scratch_sync.sh` - Scratch directory synchronization

**Python Scripts (27 total):**

**Testing & Validation:**
- `test_qa_modules.py` - QA module testing
- `test_qa_integration.py` - QA integration tests
- `test_alerting.py` - Alert system testing
- `test_catalog_builder.py` - Catalog builder smoke test
- `test_ingest_vla_catalog.py` - VLA catalog ingestion test
- `test_data_accessibility.py` - Data access validation
- `test_graphiti_mcp.py` - Graphiti MCP testing
- `test_monitor_daemon.py` - Monitoring daemon test
- `test_integration_points.py` - Integration point testing
- `test_photometry_without_db.py` - Photometry testing
- `comprehensive_test_suite.py` - Full test suite

**Knowledge Graph (Graphiti):**
- `graphiti_guardrails_check.py` - Graph health checks
- `graphiti_reembed_all.py` - Re-embed all nodes
- `graphiti_reembed_mismatched.py` - Fix mismatched embeddings
- `graphiti_ingest_docs.py` - Document ingestion
- `graphiti_import_cursor_memory.py` - Import Cursor memories
- `graphiti_add_components_from_manifests.py` - Component extraction

**Data Processing:**
- `create_test_catalog.py` - Test catalog generation
- `crossmatch_transits_pointings.py` - Transit/pointing matching
- `export_to_fits_and_png.py` - Image export utility
- `find_daily_transit_groups.py` - Daily transit discovery
- `find_latest_transit_group.py` - Latest transit finder
- `make_nvss_mask_crtf.py` - NVSS mask generation
- `make_nvss_overlay.py` - NVSS overlay creation
- `plot_observation_timeline.py` - Timeline visualization

**System Management:**
- `casa_log_daemon.py` - CASA log monitoring daemon

### Pipeline Operations (`ops/pipeline/`)

**Core Pipeline Scripts:**
- `housekeeping.py` - Queue recovery and cleanup (82 lines)
  - Recovers stale `in_progress` groups → `pending`
  - Marks stale `collecting` groups → `failed`
  - Removes old temporary staging directories
- `scheduler.py` - Scheduled tasks (nightly mosaic, housekeeping)
- `build_central_calibrator_group.py` - Calibrator group builder
- `build_calibrator_transit_offsets.py` - Transit offset builder
- `build_transit_mosaic.py` - Mosaic builder
- `image_groups_in_timerange.py` - Batch imaging
- `run_next_field_after_central.py` - Field sequencing
- `curate_transit.py` - Transit curation
- `cleanup_old_data.py` - Data cleanup (retention policy)
- `overlay_nvss_on_image.py` - NVSS overlay utility
- `backup_database.sh` - Database backup script

**Service Definitions:**
- `dsa110-streaming-converter.service` - Legacy systemd unit

---

## 4. Frontend Architecture

### Technology Stack

**Framework:** React 19.1.1 with TypeScript  
**Build Tool:** Vite 7.0.0  
**UI Library:** Material-UI (MUI) 7.3.4  
**Data Fetching:** React Query (`@tanstack/react-query`) 5.90.5  
**Visualization:** Plotly.js 3.1.2 + D3.js 7.9.0  
**Tables:** AG Grid 34.3.0  
**Routing:** React Router DOM 7.9.4

### Frontend Structure

```
frontend/
├── src/
│   ├── api/              # API client (queries.ts, types.ts)
│   ├── components/       # Reusable components (MSTable, etc.)
│   ├── pages/            # Page components (ControlPage, Dashboard, etc.)
│   ├── hooks/            # Custom React hooks
│   ├── theme/            # MUI theme configuration
│   └── utils/            # Utility functions
├── public/               # Static assets
├── dist/                 # Production build output
├── package.json          # Dependencies (57 lines)
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript configuration
└── vitest.config.ts      # Testing configuration
```

**Key Features:**
- Hot module replacement (Vite dev server)
- TypeScript strict mode
- ESLint + Vitest for testing
- Environment-based API URL configuration
- Proxy support for development

**Development Workflow:**
- Dev server: `npm run dev` (port 3210 default)
- API proxy: Configurable via `VITE_API_URL` or `vite.config.ts`
- Production build: `npm run build`
- Testing: `npm test` (Vitest)

---

## 5. Documentation System

### MkDocs Documentation (`docs/`)

**Structure:**
- **Handbook:** `docs/handbook/index.md` - Central navigation hub
- **Concepts:** Architecture, design documents
- **Guides:** Control Panel, dashboard development
- **How-To:** Quality assurance, mosaicking, reprocessing
- **Reference:** API, CLI, database schema, modules
- **Reports:** Implementation summaries, test results
- **Tutorials:** Calibration, conversion, streaming
- **Operations:** Deployment, port management, systemd migration

**Generated Site:** `site/` directory (GitHub Pages deployment)

**Configuration:** `mkdocs.yml` with:
- Material theme
- Navigation structure
- Plugin configuration (search, math)
- Custom JavaScript (Mermaid diagrams)

**Makefile Targets:**
- `make docs-install` - Install dependencies
- `make docs-serve` - Local development server (port 8001)
- `make docs-build` - Build static site
- `make docs-deploy` - Deploy to GitHub Pages

---

## 6. Testing Infrastructure

### Test Organization

**Test Directories:**
- `tests/` - Main test suite
- `tests/api/` - API endpoint tests
- `tests/simulation/` - Synthetic data tests
- `frontend/src/test/` - Frontend unit tests

**Test Files:**
- `tests/api/test_routes.py` - API route testing
- `tests/test_photometry_normalization_0702.py` - Photometry validation
- `tests/simulation/test_validate_synthetic.py` - Synthetic data validation
- `tests/testing.py` - General testing utilities
- `tests/testing_fast.py` - Fast test suite
- `tests/testing_compare_writers.py` - Writer comparison tests

**Test Configuration:**
- `tests/pytest.ini` - Pytest configuration
- `frontend/vitest.config.ts` - Frontend test configuration

**Test Scripts:**
- `scripts/comprehensive_test_suite.py` - Full integration test suite
- Multiple `test_*.py` scripts in `scripts/` for component testing

---

## 7. State Management

### Runtime State (`state/`)

**Databases (SQLite):**
- `ingest.sqlite3` - Queue tracking (ingest_queue, subband_files, performance_metrics)
- `cal_registry.sqlite3` - Calibration table registry
- `products.sqlite3` - Products tracking (ms_index, images, jobs, QA metrics)
- `master_sources.sqlite3` - NVSS/VLASS/FIRST master catalog
- `catalogs/*.sqlite3` - Various catalog databases

**Logs:**
- `state/logs/` - CASA log files (19,802+ files, auto-cleanup every 6 hours)
- `*.log` files - Various operation logs

**QA Artifacts:**
- `state/qa/` - Quality assurance plots and metrics
- Organized by timestamp directories

**Cache:**
- `state/cfcache/` - CASA cache files
- `state/catalogs/` - Cached catalog data

### State Cleanup

**CASA Log Cleanup:**
- Systemd timer: `casa-log-cleanup.timer` (every 6 hours)
- Script: `scripts/cleanup_casa_logs.sh`
- Retention: 6 hours (configurable)

**Queue Recovery:**
- Script: `ops/pipeline/housekeeping.py`
- Recovers stale jobs, marks failed groups
- Removes old temporary directories

---

## 8. Configuration Management

### Environment Variables (`ops/systemd/contimg.env`)

**Core Paths:**
- `CONTIMG_INPUT_DIR` - Input UVH5 directory
- `CONTIMG_OUTPUT_DIR` - Output MS directory
- `CONTIMG_SCRATCH_DIR` - Scratch space
- `CONTIMG_STATE_DIR` - State directory

**Database Paths:**
- `CONTIMG_QUEUE_DB` - Queue database
- `CONTIMG_REGISTRY_DB` - Calibration registry
- `CONTIMG_PRODUCTS_DB` - Products database

**Performance:**
- `OMP_NUM_THREADS=4` - OpenMP threads
- `MKL_NUM_THREADS=4` - MKL threads
- `HDF5_USE_FILE_LOCKING=FALSE` - HDF5 file locking

**Staging:**
- `CONTIMG_STAGE_TO_TMPFS=true` - Enable RAM staging
- `CONTIMG_TMPFS_PATH=/dev/shm` - tmpfs path

**Quality Assurance:**
- `CONTIMG_QA_MS_MAX_FLAGGED=0.5` - MS flagging threshold
- `CONTIMG_QA_CAL_MAX_FLAGGED=0.3` - Calibration flagging threshold
- `CONTIMG_QA_IMG_MIN_DYNAMIC_RANGE=5.0` - Image quality threshold

**Alerting:**
- `CONTIMG_SLACK_WEBHOOK_URL` - Slack integration (optional)
- `CONTIMG_SMTP_*` - Email alerts (optional)

---

## 9. Deployment Scenarios

### Scenario 1: Systemd (Production)

**Setup:**
1. Copy service files: `sudo cp ops/systemd/*.service /etc/systemd/system/`
2. Edit environment: `ops/systemd/contimg.env`
3. Enable services: `sudo systemctl enable --now contimg-stream contimg-api`

**Services:**
- `contimg-stream.service` - Streaming worker (daemon)
- `contimg-api.service` - FastAPI server (port 8000)

**Logs:**
- Journald: `sudo journalctl -u contimg-stream`
- File logs: `/var/log/dsa110/` (if configured)

### Scenario 2: Docker Compose (Containerized)

**Setup:**
1. Copy env template: `cp ops/docker/.env.example ops/docker/.env`
2. Edit `.env` with absolute paths
3. Build: `make compose-build`
4. Start: `make compose-up`

**Services:**
- `stream` - Streaming worker container
- `api` - API server container (port 8000)
- `scheduler` - Scheduled tasks container

**Volumes:**
- Code mounted from host (`/app`)
- Data directories bind-mounted
- State directories shared

### Scenario 3: Manual Development

**Setup:**
1. Use service management script: `./scripts/manage-services.sh start api`
2. Or run directly: `uvicorn dsa110_contimg.api.routes:create_app --factory`
3. Frontend: `cd frontend && npm run dev`

**Advantages:**
- Fast iteration
- Direct debugging
- Hot reload (frontend)

---

## 10. Code Organization Patterns

### Source Code (`src/dsa110_contimg/`)

**Modular Structure:**
- `api/` - FastAPI application
- `conversion/` - UVH5 → MS conversion
- `calibration/` - Calibration pipeline
- `imaging/` - Imaging pipeline
- `qa/` - Quality assurance
- `database/` - Database helpers
- `utils/` - Shared utilities

**CLI Modules:**
- Each major component has a `cli.py` module
- Consistent argument parsing patterns
- Unified logging configuration

### Operational Scripts

**Pattern:**
- Shell scripts for simple automation
- Python scripts for complex logic
- Consistent error handling
- Logging to `state/logs/`

### Frontend Code

**Pattern:**
- API client abstraction (`api/queries.ts`)
- Type-safe interfaces (`api/types.ts`)
- Component-based architecture
- React Query for data fetching

---

## 11. External Dependencies

### Python Dependencies

**Core:**
- `pyuvdata` - UVH5 reading
- `casatasks`, `casatools` - CASA operations
- `astropy` - Time/coordinate handling
- `numpy` - Numerical operations
- `FastAPI` - REST API framework

**Environment:**
- Managed via `ops/docker/environment.yml` (conda)
- Base: `casa6` conda environment

### Node.js Dependencies

**Frontend:**
- React ecosystem (React, React DOM, React Router)
- Material-UI for UI components
- Plotly.js + D3.js for visualization
- AG Grid for data tables
- React Query for API state management

**Backend Node:**
- Socket.io (for potential WebSocket support)
- JS9 (FITS image viewer library)

---

## 12. Knowledge Graph Integration

### Graphiti Integration

**Purpose:**
- Long-term project memory
- Entity extraction from commits
- Relationship tracking
- Semantic search

**Scripts:**
- `scripts/graphiti_guardrails_check.py` - Graph health validation
- `scripts/graphiti_ingest_docs.py` - Document ingestion
- `scripts/graphiti_import_cursor_memory.py` - Memory import

**Makefile Targets:**
- `make guardrails-check` - Check graph health
- `make guardrails-fix` - Fix graph issues
- `make ingest-docs` - Ingest documentation

**Git Hook:**
- `.githooks/post-commit` - Auto-record commits to graph
- Non-blocking (runs in background)
- Stores commit hash, branch, message

---

## 13. Archive & Legacy Code

### Archive Structure (`archive/`)

**Purpose:**
- Preserve historical implementations
- Reference for migration decisions
- Avoid breaking existing workflows

**Contents:**
- `archive/legacy/` - Legacy core conversion code
- `archive/working/` - Work-in-progress experiments
- `archive/chats/` - Historical chat logs
- `archive/arXivADS/` - Research paper references

**References Directory:**
- External library references (codex-africanus, dask-ms, etc.)
- Submodule-style references for learning

---

## 14. Key Operational Insights

### Strengths

1. **Comprehensive Tooling:**
   - Service management script handles port conflicts
   - Multiple deployment options (systemd, Docker, manual)
   - Automated housekeeping and cleanup

2. **Developer Experience:**
   - Hot reload for frontend development
   - Makefile targets for common tasks
   - Comprehensive documentation

3. **Operational Maturity:**
   - Log management (auto-cleanup)
   - Queue recovery mechanisms
   - Health checking and monitoring

4. **Code Quality:**
   - TypeScript for frontend type safety
   - Comprehensive test suites
   - Knowledge graph integration for memory

### Areas for Improvement

1. **Configuration:**
   - Multiple env files (systemd, docker) could be unified
   - Path configuration scattered across files

2. **Documentation:**
   - Some operational scripts lack inline docs
   - Frontend component documentation could be enhanced

3. **Testing:**
   - Frontend test coverage appears limited
   - Integration tests could be more comprehensive

4. **Deployment:**
   - Service management script requires sudo for some operations
   - Docker Compose could use more health checks

---

## 15. Project Statistics

### File Counts

- **Python Files:** 147 modules
- **Shell Scripts:** 11 files
- **TypeScript/JavaScript:** Frontend codebase
- **Documentation:** 98+ markdown files

### Code Volume

- **Source Code:** ~25,493 lines (Python)
- **Frontend:** Estimated 5,000+ lines (TypeScript/TSX)
- **Scripts:** ~2,000+ lines (Python + Shell)
- **Documentation:** 50,000+ lines (Markdown)

### Database Size

- **State Databases:** Multiple SQLite files
- **Log Files:** 19,802+ CASA log files (managed)
- **QA Artifacts:** Organized by timestamp

---

## 16. Recommendations

### Immediate Actions

1. **Unify Configuration:**
   - Create single source of truth for paths
   - Template system for environment variables
   - Validation script for configuration

2. **Enhance Documentation:**
   - Add inline docs to operational scripts
   - Document deployment decision tree
   - Create troubleshooting runbook

3. **Improve Testing:**
   - Increase frontend test coverage
   - Add integration tests for deployment scenarios
   - Automated testing in CI/CD

### Long-Term Enhancements

1. **Observability:**
   - Prometheus metrics export
   - Distributed tracing (OpenTelemetry)
   - Centralized logging (ELK stack)

2. **Automation:**
   - Self-healing mechanisms
   - Automated calibration fallback
   - Intelligent retry logic

3. **Performance:**
   - Parallel pipeline stages
   - Caching for catalog queries
   - Resource throttling

---

## Conclusion

The DSA-110 continuum imaging pipeline is a **mature, production-ready system** with comprehensive operational infrastructure. The project demonstrates:

- **Clear separation** between source code, operations, and deployment
- **Multiple deployment options** for different scenarios
- **Robust operational tooling** for production management
- **Comprehensive documentation** and knowledge management
- **Modern development practices** (TypeScript, testing, CI/CD-ready)

The top-level analysis reveals a well-organized project that goes beyond just source code, with significant investment in operational excellence, documentation, and developer experience.

**Overall Assessment:** Production-ready with strong operational foundations and clear paths for enhancement.
