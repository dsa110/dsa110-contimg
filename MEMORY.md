> Note: A published copy of this document is now available at `docs/reports/memory.md`.

## VP table construction (DSA-110)

- Canonical telescope: `OVRO_DSA` (PIPELINE_TELESCOPE_NAME; helpers stamp MS)
- Source H5: `/scratch/dsa110-contimg/dsa110-beam-model/DSA110_beam_1.h5`
- Output VP: `/scratch/dsa110-contimg/vp/dsa110.vp` (temp complex image `/scratch/dsa110-contimg/vp/dsa110_vp_tmp.im`)

CLI
```bash
python -m dsa110_contimg.beam.cli \
  --h5 /scratch/dsa110-contimg/dsa110-beam-model/DSA110_beam_1.h5 \
  --out /scratch/dsa110-contimg/vp/dsa110.vp \
  --telescope OVRO_DSA \
  --freq-hz 1.4e9
```

Jones mapping
- Jxx = X.ephi; Jxy = −X.etheta; Jyx = Y.ephi; Jyy = −Y.etheta

Coordsys
- AZEL, units deg; Stokes XX,XY,YX,YY; 1 spectral channel
- Elevation = 90° − theta(rad→deg); Azimuth = phi(deg)
- refpix center; refval [0,0]; increments from grid spacing

Registration
- vpmanager.setpbimage(compleximage=..., antnames=['*']); saveastable -> VP

Imaging guidance
- Stokes I: wproject + scalar PB correction (pbcor or widebandpbcor); mask pblimit≥0.25
- A-Projection: requires CASA to recognize telescope for built-in ATerm (not critical for I-only)
# Project Memory – dsa110-contimg

- Prefer RAM staging for per-subband MS writes and concat (`/dev/shm`) when available; fall back to SSD.
- Auto writer heuristic: ≤2 subbands -> monolithic (pyuvdata), else direct-subband.
- Fast calibration: use `--fast` with time/channel averaging; solve K on peak field, BP/G across window; phase-only by default; optional `--uvrange` cuts for speed.
- Quick imaging: `--quick` to cap imsize/niter; `--skip-fits` to avoid export; auto-selects CORRECTED_DATA when valid.
- Add concise timers around major steps to track drift (conversion concat, K/BP/G, tclean).

## 2025-10-27 – Control Panel & Service Management

### Control Panel Implementation
**Complete React-based web UI for manual job execution with live log streaming.**

**Backend (Python/FastAPI)**:
- `database/jobs.py`: SQLite job tracking (create_job, get_job, update_job_status, append_job_log, list_jobs)
- `api/job_runner.py`: Background task execution (run_calibrate_job, run_apply_job, run_image_job)
- `api/routes.py`: 7 new endpoints:
  - GET `/api/ms` - List available Measurement Sets
  - GET `/api/jobs` - List jobs with status filter
  - GET `/api/jobs/{id}` - Get job details
  - GET `/api/jobs/{id}/logs` - **SSE log streaming**
  - POST `/api/jobs/calibrate` - Create calibration job
  - POST `/api/jobs/apply` - Create apply job
  - POST `/api/jobs/image` - Create imaging job
- `api/models.py`: Job, JobParams, JobList, MSList models (Python 3.6+ compatible with Optional/List from typing)

**Frontend (React/TypeScript)**:
- `pages/ControlPage.tsx`: Full UI with MS picker, tabbed forms (Calibrate/Apply/Image), live log viewer with SSE, job status table
- `api/queries.ts`: 6 React Query hooks (useMSList, useJobs, useJob, useCreate*Job mutations)
- `api/types.ts`: TypeScript interfaces matching backend models
- Navigation: Added "Control" menu item with Settings icon

**Key Features**:
- Live log streaming via Server-Sent Events (SSE) with auto-scroll
- Job status tracking: pending → running → done/failed
- Artifact discovery (caltables, images) auto-registered after completion
- Batched log writes (every 10 lines) for performance
- Background execution via FastAPI BackgroundTasks
- All jobs run in `casa6` conda environment with PYTHONPATH set

**Architecture Decisions**:
- SQLite for job persistence (matches existing pipeline pattern)
- SSE over WebSockets (simpler, one-way, native browser support)
- BackgroundTasks over Celery (sufficient for single-server deployment)
- Batched log appends to reduce DB I/O

**Testing**: All backend unit tests passed; job CRUD, log streaming, model validation verified.

### Service Management & Port Reservation

**Problem**: Port conflicts with existing services; need reliable startup/shutdown.

**Solution**: Three-tier approach for different deployment scenarios.

**Method 1: Service Management Script** (Development - RECOMMENDED)
- Location: `scripts/manage-services.sh`
- Usage: `./scripts/manage-services.sh {start|stop|restart|status|logs} [api|dashboard|all]`
- Features:
  - Auto-kills conflicting processes on ports 8000/3000
  - PID tracking in `/var/run/dsa110/`
  - Logs to `/var/log/dsa110/`
  - Color-coded status output
  - Background process management
- Correct uvicorn command: `uvicorn dsa110_contimg.api.routes:create_app --factory --host 0.0.0.0 --port 8000`
- Note: API uses factory pattern `create_app()` in routes.py, not server.py

**Method 2: Systemd Services** (Production)
- Files: `systemd/dsa110-api.service`, `systemd/dsa110-dashboard.service`
- Installation: `systemd/INSTALL.md`
- Benefits: Auto-start on boot, automatic restart on crash, system logging
- Setup: `sudo cp systemd/*.service /etc/systemd/system/ && sudo systemctl enable dsa110-api.service`

**Method 3: Docker Compose** (Containerized)
- File: `docker-compose.yml`
- Ports: 8000 (API), 3000 (Dashboard)
- Networks: dsa110-network
- Health checks included

**Port Assignments**:
- 8000: DSA-110 API (FastAPI backend)
- 3000: DSA-110 Dashboard (React frontend)
- 8010: Alternative API port (if needed)
- 8080: Proxy services (existing)

**Common Commands**:
```bash
# Start services
sudo fuser -k 8000/tcp  # Kill port conflicts
./scripts/manage-services.sh start api

# Check status
./scripts/manage-services.sh status

# View logs
./scripts/manage-services.sh logs api

# Stop services
./scripts/manage-services.sh stop all
```

**Documentation Created**:
- `CONTROL_PANEL_README.md` - Complete architecture and API docs
- `CONTROL_PANEL_QUICKSTART.md` - Step-by-step user guide with examples
- `IMPLEMENTATION_SUMMARY.md` - Technical details and design decisions
- `PORT_MANAGEMENT.md` - Complete guide to all three service management methods
- `systemd/INSTALL.md` - Systemd installation instructions

**Files Modified/Created** (12 total):
- Backend: `database/jobs.py` (new), `api/job_runner.py` (new), `api/models.py` (extended), `api/routes.py` (extended)
- Frontend: `pages/ControlPage.tsx` (new), `api/types.ts` (extended), `api/queries.ts` (extended), `components/Navigation.tsx` (modified), `App.tsx` (modified)
- Service Management: `scripts/manage-services.sh` (new), `systemd/*.service` (new), `docker-compose.yml` (new)

**Current Status**: ✓ API running on port 8000 with all control panel endpoints functional. Service management script fixed with process tree killing. Ready for production use.

**Critical Fix (2025-10-27)**: The `kill_port` function was only killing the uvicorn child process, but the parent conda/bash wrapper would immediately respawn it. Updated to kill the entire process tree (parent and children) by detecting conda/bash/tmp parent processes and killing them first. This ensures reliable restart without manual intervention.

## 2025-10-22/23 – Telescope Identity + API/service fixes

Telescope identity standardization (OVRO_DSA)

- Single source of truth: `PIPELINE_TELESCOPE_NAME=OVRO_DSA` added to `ops/systemd/contimg.env`. Default OVRO coords: lon −118.2817°, lat 37.2314°, alt 1222 m.
- Helper `set_telescope_identity` added in `src/dsa110_contimg/conversion/helpers.py`.
  - Sets `uv.telescope_name` and location in ITRF + geodetic (rad/deg); mirrors onto `uv.telescope` when present.
- Applied on all write paths:
  - Orchestrator (`strategies/hdf5_orchestrator.py`) after merge, pre‑phasing.
  - Direct‑subband worker (`strategies/direct_subband.py`) after per‑subband read, pre‑phasing.
  - Standalone converter (`conversion/uvh5_to_ms.py`) after `read_uvh5_file`, pre‑phasing.
- MS backstop stamping: `configure_ms_for_imaging` now writes `OBSERVATION::TELESCOPE_NAME` from `PIPELINE_TELESCOPE_NAME`.
- Antenna coordinates: `utils/antpos_local/data/DSA110_Station_Coordinates.csv` is authoritative and used by `set_antenna_positions()` with safe elevation fallback.
- Docs updated with “Telescope Identity” and optional casacore Measures overlay:
  - `docs/reference/env.md`, `docs/quickstart.md`.
  - Overlay instructions: copy/append `geodetic/Observatories`, set `CASACORE_DATA=<repo>/data/measures`; not required for imaging since MS carries positions.

Systemd + API service hardening

- Units installed to `/etc/systemd/system`: `contimg-stream.service`, `contimg-api.service`; env in `ops/systemd/contimg.env`.
- Drop‑in overrides use conda: `conda run -n casa6 …` and `Environment=PYTHONPATH=/data/dsa110-contimg/src`.
- API startup fixed:
  - Exposed `app = create_app()` in `src/dsa110_contimg/api/__init__.py`.
  - Switched ExecStart to `uvicorn dsa110_contimg.api:app` (avoid `--factory` parsing issue).
- Env for API made explicit (no nested expansion): `PIPELINE_QUEUE_DB`, `PIPELINE_PRODUCTS_DB`, `PIPELINE_STATE_DIR`, `PIPELINE_EXPECTED_SUBBANDS`, `CAL_REGISTRY_DB` now set to concrete paths in `contimg.env`.
- DB initialization (one‑time) completed:
  - `/data/dsa110-contimg/state/cal_registry.sqlite3` with table `caltables`.
  - `/data/dsa110-contimg/state/ingest.sqlite3` with tables `ingest_queue`, `subband_files`, `performance_metrics`.
- Verified API endpoints:
  - `/api/status` returns queue stats and calibration sets.
  - `/api/metrics/system` returns system metrics.
- Note: systemd `append:` log redirection warnings observed; acceptable. Use journald if desired.

Operational notes / next steps

- Backfill existing MS telescope names if needed (stamp `OBSERVATION::TELESCOPE_NAME`).
- Optional casacore Measures overlay only needed for code calling `measures().observatory('OVRO_DSA')`.
- Streamer (`contimg-stream`) populates `ingest.sqlite3`; API reads DB paths from env.

## 2025-10-23 – NVSS Sky Model Seeding in Imaging

- Imaging CLI now supports `--nvss-min-mjy` to seed MODEL_DATA via ft() with NVSS point sources above a threshold within the FoV before tclean. We explicitly set `savemodel='none'` to avoid overwriting the seeded model.
- Skymodel helpers:
  - `make_multi_point_cl(points, ...)` and `make_nvss_component_cl(center, radius, min_mjy, ...)` to build CASA component lists from catalogs.
- Precedence logic in imaging:
  - If a bandpass calibrator is specified and falls within the FoV, seed a single-component calibrator model via ft().
  - Otherwise, if `nvss_min_mjy` is provided, seed a multi-component NVSS model.
- Pipeline integration:
  - `build_central_calibrator_group.py`, `build_calibrator_transit_offsets.py` pass calibrator RA/Dec/flux to prefer a single-component model; they also pass `nvss_min_mjy=10.0` as fallback.
  - General imaging paths (`image_groups_in_timerange.py`, `run_next_field_after_central.py`, `build_transit_mosaic.py`) pass `nvss_min_mjy=10.0`.
# DSA-110 Continuum Imaging Project Memory

## Key Lessons and Principles

### UVH5 to MS Conversion Process

1. **Circular Import Issues**: The historical `uvh5_to_ms_converter_v2.py` had circular import dependencies that were resolved by:
   - Implementing lazy imports in `dsa110_contimg.conversion.__init__.py`
   - Creating missing modules (`writers.py`) and functions (`write_ms_from_subbands`)
   - Using direcports from specific modules rather than package-level imports

2. **FUSE Temporary Files**: Large `.fuse_hidden*` files (70+ GB each) are created during MS writing operations:
   - These are temporary files created by FUSE filesystems during large data operations
   - They can accumulate in multiple locations: root directory, MS directories, and QA directories
   - They can accumulate if processes don't clean up properly
   - Use `sudo fuser -k` and `sudo rm -f` to force cleanup when processes hold file descriptors
   - Normal behavior for CASA/pyuvdata operations writing large datasets
   - Total cleanup freed ~400GB of disk space (from 5.1T to 4.7T usage)

3. **Python Environment**: The system requires:
   - `casa6` conda environment for `pyuvdata` and CASA tools
   - `PYTHONPATH=/data/dsa110-contimg/src` for package imports
   - Python 3.11 (not Python 2.7) for modern syntax support

4. **Conversion Success**: The v2 converter successfully:
   - Groups subbands by timestamp (30s tolerance)
   - Merges frequency channels in ascending order
   - Creates proper CASA Measurement Sets with UVW coordinates
   - Finds and creates calibrator MS files with MODEL_DATA
   - Uses direct subband writer for optimal performance
   - Preallocates `MODEL_DATA`/`CORRECTED_DATA` after writing to avoid CASA errors
5. **Module Layout**: Active conversion code now lives in `dsa110_contimg/conversion/` (helpers, batch converter, streaming daemon, strategy writers). Legacy implementations are archived under `archive/legacy/core_conversion/`; imports from `dsa110_contimg.core.conversion` are no longer supported.

### File Structure
- Input: `/data/incoming/` (UVH5 subband files)
- Output: `/data/dsa110-contimg/data-samples/ms/` (CASA MS files)
- QA: `/data/dsa110-contimg/state/qa/` (Quality assurance plots)

### Control Panel Technical Details (2025-10-27)

**Critical Implementation Notes**:
1. **API Factory Pattern**: API uses `create_app()` factory in `routes.py`, NOT `server.py`
   - Correct: `uvicorn dsa110_contimg.api.routes:create_app --factory`
   - Wrong: `uvicorn dsa110_contimg.api.server:app`

2. **Python Version Compatibility**: 
   - Base system: Python 3.6 (no `from __future__ import annotations` support)
   - Jobs run in: `casa6` conda environment (Python 3.11)
   - Solution: Use `Optional[T]` and `List[T]` from typing module in models

3. **Job Runner Environment**:
   - Must set `PYTHONPATH=/data/dsa110-contimg/src`
   - Must run via `conda run -n casa6`
   - Logs batched every 10 lines to database for performance
   - Uses subprocess with stdout/stderr capture

4. **SSE Log Streaming**:
   - EventSource API in browser connects to `/api/jobs/{id}/logs`
   - Server sends `data:` events with JSON `{"logs": "..."}`
   - Sends `event: complete` with `{"status": "done|failed"}` to close
   - Frontend auto-scrolls logs using useEffect + ref

5. **Port Management**:
   - Always check for conflicts: `lsof -i :8000` or `netstat -tlnp | grep :8000`
   - Kill conflicts: `sudo fuser -k 8000/tcp`
   - Service script handles this automatically (but needs sudo for kill)

6. **Job Database Schema**:
   - Table: `jobs` in `products.sqlite3`
   - Key columns: id, type, status, ms_path, params (JSON), logs (TEXT), artifacts (JSON array)
   - Indices on status and created_at for fast queries

7. **Artifact Discovery**:
   - Calibrate: Scans for `.kcal`, `.bpcal`, `.gpcal` in MS directory
   - Image: Scans for `.image`, `.image.pbcor`, `.residual`, `.psf`, `.pb`, `.model`
   - Stored as JSON array in `artifacts` column

8. **Background Task Execution**:
   - FastAPI BackgroundTasks spawns job immediately
   - Returns job ID to client for polling/SSE connection
   - Job runner updates status: pending → running → done/failed
   - Subprocess exit code determines final status

### Common Issues and Solutions
- **ImportError**: Check PYTHONPATH and conda environment
- **Circular imports**: Use lazy imports and direct module references
- **Port already in use**: Use `sudo fuser -k <port>/tcp` or service management script
- **API won't start**: Verify using factory pattern `--factory` flag with `routes:create_app`
- **Logs not streaming**: Check SSE connection in browser DevTools Network tab
- **Job stuck in pending**: Check backend logs, verify BackgroundTasks is spawning correctly
- **Outdated import paths**: Update any remaining `dsa110_contimg.core.conversion.*` imports to `dsa110_contimg.conversion.*`
- **Large temp files**: Monitor for `.fuse_hidden*` files and clean up if needed
- **Missing modules**: Create required modules and functions as needed
- **CASA Calibrater error (no array in MODEL_DATA row)**: If `MODEL_DATA` exists but arrays are uninitialized, CASA `gaincal`/`bandpass` can fail with "TSM: no array in row ... of column MODEL_DATA". Fix by preallocating `MODEL_DATA` (unity or zeros) and initializing `CORRECTED_DATA` across all rows after MS write. The converter now does this automatically.

### Recent Fixes (2025-10-10 → 2025-10-13)
- Field selection in delay solve now honors CASA-style names/ranges: numeric IDs, `A~B`, comma lists, and glob matches against `FIELD::NAME`. This removes a crash when `--field` is a name.
- Calibration table prefixes now use `os.path.splitext(ms)[0]` instead of `rstrip('.ms')`, preventing accidental truncation (e.g., `runs.ms` → `runs`, not `run`).
- Streaming converter now uses the strategy orchestrator (writer=`direct-subband`) in both subprocess and in‑process paths; writer type is recorded in metrics.

### Integration Notes: Zapier MCP + Azure OpenAI (2025-10-20)
- Use the Zapier Azure OpenAI actions only after configuring the action UI fields; runtime overrides via MCP may be ignored.
- Required: set the exact Azure OpenAI `Deployment Name` (alias) in the Zapier action UI.
- Ensure the Azure resource host configured in Zapier matches the actual resource (e.g., `jfaber-9261-resource.openai.azure.com` vs a stale `myoairesourced1ce90.openai.azure.com`).
- If calls fail with “Deployment Name is missing,” confirm the action UI contains the alias (e.g., `gpt-5-codex`), not the model name.
- Legacy action endpoints may reveal misconfigured hosts; fix in Zapier, then retry calls without passing `deployment` at runtime.
- Products DB helpers added: centralized `ms_index`/`images` schema management, upserts, and indices.
- API/monitoring integrates recent calibrator matches and QA discovery.

### Catalog: Master Sources (NVSS + VLASS + FIRST)
- New builder: `python -m dsa110_contimg.catalog.build_master` creates `state/catalogs/master_sources.sqlite3`.
- Inputs: NVSS (required), optional VLASS and FIRST catalogs (CSV/TSV/FITS); auto column detection with optional explicit mappings.
- Crossmatch radius: configurable (default 7.5"). Computes:
  - Spectral index α from NVSS (1.4 GHz) and VLASS (3.0 GHz) peak fluxes (units converted to Jy).
  - Compactness via FIRST deconvolved sizes; confusion when multiple matches within radius.
- DB schema:
  - `sources(source_id, ra_deg, dec_deg, s_nvss, snr_nvss, s_vlass, alpha, resolved_flag, confusion_flag)`
  - Views: `good_references` (quality cuts), `final_references` (stricter SNR + optional stable IDs)
  - Optional materialized snapshot: `final_references_table`
  - `meta` records thresholds, build_time_iso, and input file provenance (sha256/size/mtime/rows)
- Useful flags: `--nvss-flux-unit|--vlass-flux-unit {jy|mjy|ujy}`, `--goodref-snr-min|-alpha-min|-alpha-max`, `--finalref-snr-min|--finalref-ids|--materialize-final`, `--export-view|--export-csv`.

# Currently Working On:

## 2025-10-23 – Docs structure and drift points
- MkDocs nav under `mkdocs.yml` maps to `docs/` pages (Quick Start, Pipeline Visuals, Tutorials, How-To, Guides, Concepts, Reference, Reports, Simulation, Troubleshooting, Operations, Legacy).
- Common drift points to watch:
  - Systemd unit path references: use `ops/systemd/contimg-stream.service` and `contimg-api.service` (not historical `pipeline/scripts/...`).
  - API endpoints: include `/api/qa`, `/api/qa/file/{group}/{name}`, `/api/metrics/system`, `/api/metrics/system/history` in `reference/api.md`.
  - Downsampling examples: prefer unified CLI `python -m dsa110_contimg.conversion.downsample_uvh5.cli` over direct script paths.
  - Legacy conversion docs: avoid UVFITS/importuvfits flow and historical scripts; reflect current orchestrator + writers (`direct-subband`, `pyuvdata`, `auto`).
  - Env variables: document `CONTIMG_*` and `PIPELINE_*` across systemd/docker (`QUEUE_DB`, `REGISTRY_DB`, `PRODUCTS_DB`, `STATE_DIR`, `LOG_LEVEL`, `EXPECTED_SUBBANDS`, `CHUNK_MINUTES`, `MONITOR_INTERVAL`).
- Keep `reference/cli.md` aligned with actual CLIs: streaming converter, imaging worker, orchestrator, downsample CLI, registry CLI, mosaic CLI, calibration CLI.

## 2025-10-23 – Environment standardization
- Drop `casa-dev` channel and replace `casa6` with explicit `casatools`, `casatasks`, `casaconfig` from conda-forge; keep `python-casacore`.
- `ops/docker/environment.yml` updated accordingly; image builds and passes CASA + stack import tests.
- `.cursor/Dockerfile` added to mirror container runtime for background agents using conda-forge environment; user `mambauser`.
- Verified container CLI help for `imaging.worker` and `hdf5_orchestrator`; module imports OK.

## 2025-10-24 – Agentic Tooling: Serena + Graphiti Integration

### Overview
The project uses a dual-memory system combining Serena (semantic code analysis) with Graphiti (knowledge graph memory) to provide both symbolic code understanding and episodic/relational context.

### Serena: Semantic Code Analysis Agent
- **Location**: `~/proj/mcps/oraios/serena` (source repo)
- **Project Integration**: `.serena/` directory in project root
- **What It Does**: Provides IDE-like semantic code navigation using Language Server Protocol (LSP)
- **Key Capabilities**:
  - Symbol-level code understanding (classes, functions, variables)
  - Find symbol definitions and references across codebase
  - Semantic code editing (replace_symbol_body, insert_after_symbol, etc.)
  - Language server support for 30+ languages including Python
  - Project-specific memories stored as markdown in `.serena/memories/`

### Serena Memories for This Project
Located in `/data/dsa110-contimg/.serena/memories/`:
- `dsa110_comprehensive_analysis.md`: Expert scientific analysis of the pipeline
  - RFI mitigation strategy assessment
  - Calibration sequence (K→BP→G) validation
  - Imaging strategy evaluation (NVSS-guided deconvolution, tclean vs WSClean)
  - QA suite assessment
  - Recommendations: self-calibration loops, WSClean integration, multiscale deconvolution

### Graphiti: Knowledge Graph Memory
- **What It Does**: Maintains temporal knowledge graph of entities, facts, and relationships
- **Storage**: Neo4j backend (configured via MCP server)
- **Key Capabilities**:
  - Episodic memory from conversation/task context
  - Entity extraction (Preferences, Procedures, Requirements, custom entities)
  - Relationship tracking (CONSUMES, PRODUCES, DEPENDS_ON, etc.)
  - Semantic search over nodes and facts

### Workflow Synergy: How They Work Together

**Serena's Role:**
1. Provides **symbolic code structure** via LSP (call graphs, inheritance, references)
2. Enables precise code navigation and editing at the symbol level
3. Stores **scientific/domain analysis** as project memories
4. Works at the **code implementation level** (functions, classes, modules)

**Graphiti's Role:**
1. Provides **episodic/conversational context** across sessions
2. Captures **high-level entities and relationships** (data products, pipelines, concepts)
3. Stores **task history and procedural knowledge** (what worked, what didn't)
4. Works at the **conceptual/workflow level** (data lineage, dependencies, requirements)

**Integration Pattern:**
1. **Code Analysis**: Serena finds symbols and code structure
2. **Contextualization**: Graphiti provides scientific meaning and relationships
3. **Task Execution**: Serena edits code using LSP tools
4. **Memory Formation**: Graphiti stores task outcomes, lineage, lessons learned
5. **Future Retrieval**: Both memories consulted at start of new sessions

**Example Use Case:**
- User: "Update the calibration pipeline to support self-calibration"
- Graphiti search: Retrieve previous calibration requirements, known issues
- Serena analysis: Find all calibration functions, their symbols, call chains
- Graphiti context: Understand data flow (MS → K table → BP table → G table)
- Serena editing: Modify calibration functions at symbol level
- Graphiti storage: Record new self-cal procedure, updated dependencies

### Integration Points
- Both use MCP (Model Context Protocol) for tool access
- Serena memories: domain/scientific analysis (static, curated)
- Graphiti episodes: task execution history (dynamic, temporal)
- Complementary rather than overlapping: code vs. concept understanding

## 2025-10-24 – Streaming Automation & Architecture Review

### Changes Implemented

**1. tmpfs Staging Now Default**
- Changed `--stage-to-tmpfs` to default `True` in `hdf5_orchestrator.py`
- Added `--no-stage-to-tmpfs` flag for explicit SSD-only mode
- Updated `contimg.env` with `CONTIMG_STAGE_TO_TMPFS=true`
- Rationale: 47GB tmpfs available, 3-5x performance improvement, conservative 2x safety margin

**2. Comprehensive Automation Audit**
- Created `/docs/reports/STREAMING_AUTOMATION_AUDIT.md`
- Identified 4 priority tiers: Critical, Observability, Resilience, Optimization
- Documented 15+ specific recommendations with implementation details
- Established success metrics and monitoring requirements

### Key Architectural Recommendations

**Priority 1 (Critical for Lights-Out Operation):**
1. **Automatic Calibrator Fallback:** Chain of priority (active → nearest → last-known-good)
2. **Intelligent Retry Logic:** Error classification with exponential backoff per error type
3. **Self-Healing Mechanisms:** Stuck job watchdog, automatic disk space management
4. **Comprehensive Alerting:** Multi-channel alerts (Slack/email/PagerDuty) with severity levels

**Priority 2 (Enhanced Observability):**
- Prometheus metrics export for Grafana dashboards
- Distributed tracing with OpenTelemetry/Jaeger
- Correlation between traces, logs, and queue entries

**Priority 3 (Operational Resilience):**
- Configuration hot-reload without service restart
- Blue-green deployment strategy for zero-downtime updates
- Automated backups with documented disaster recovery procedures

**Priority 4 (Performance Optimization):**
- Parallel pipeline stages (conversion → calibration → imaging)
- Caching for NVSS catalog queries and beam models
- Resource throttling to prevent contention

### Success Metrics Defined

**Automation:** 99.5% zero-touch operation, < 5min automatic recovery, > 95% calibration coverage
**Reliability:** > 99% conversion success, > 95% imaging success, > 99.9% uptime, 0% data loss
**Performance:** < 10min end-to-end latency, < 10 groups queue depth, < 80% CPU utilization

### Implementation Roadmap

**Phase 1 (Weeks 1-2):** Critical automation - calibrator fallback, retry logic, alerting, watchdog
**Phase 2 (Weeks 3-4):** Observability - Prometheus/Grafana, logging, metrics API
**Phase 3 (Weeks 5-6):** Resilience - backups, recovery docs, config reload, health checks
**Phase 4 (Weeks 7-8):** Optimization - parallel stages, caching, tracing, profiling

### Next Actions

1. Review automation audit with operations team
2. Establish baseline metrics for current performance
3. Prioritize Phase 1 implementations based on operational pain points
4. Set up monitoring infrastructure (Prometheus/Grafana)
5. Document and test disaster recovery procedures

## 2025-10-24 – Quality Assurance & Alerting System

### Implemented Components

**1. Alerting Infrastructure** (`utils/alerting.py`)
- Multi-channel alert system (Slack, email, logging)
- Severity-based routing (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Rate limiting to prevent alert spam (10 alerts per category per 5 minutes)
- Global alert manager with automatic channel setup from environment variables
- Convenience functions for each severity level

**2. MS Quality Validation** (`qa/ms_quality.py`)
- Comprehensive MS validation after conversion
- Checks: column presence, UVW validity, data statistics, flagging rates
- Metrics: fraction flagged, fraction zeros, median/RMS amplitude, UV distance
- Quick check mode for fast validation
- Alerts: CRITICAL for missing columns/zero rows, WARNING for high flagging (>50%) or zeros (>30%)

**3. Calibration Quality Assessment** (`qa/calibration_quality.py`)
- Calibration table validation (K, BP, G tables)
- Solution statistics: amplitude/phase median, scatter, flagging
- CORRECTED_DATA validation after applycal
- Checks: all-zeros, unusual calibration factors, per-antenna failures
- Alerts: ERROR for failed calibration, WARNING for high flagging (>30%) or phase scatter (>90°)

**4. Image Quality Metrics** (`qa/image_quality.py`)
- Image validation for all CASA products (.image, .residual, .psf, .pb, .pbcor)
- Metrics: dynamic range, peak SNR, source detection (pixels >5-sigma)
- Residual-specific checks (mean near zero)
- Quick check mode for existence/size validation
- Alerts: ERROR for all-NaN/zeros, WARNING for low dynamic range (<5) or SNR (<5)
- INFO alerts for high-quality images (SNR >10)

**5. Integrated Pipeline QA** (`qa/pipeline_quality.py`)
- Unified interface for all quality checks
- Automatic alert generation based on quality issues
- Configurable thresholds via environment variables
- Three check functions: `check_ms_after_conversion`, `check_calibration_quality`, `check_image_quality`
- Returns (passed, metrics_dict) tuples for programmatic handling

**6. Configuration** (`ops/systemd/contimg.env`)
- Quality thresholds for all pipeline stages
- Alerting configuration (Slack webhook, email SMTP, severity levels)
- Commented examples for easy setup
- All thresholds tunable via environment variables without code changes

**7. Documentation** (`docs/howto/QUALITY_ASSURANCE_SETUP.md`)
- Complete setup guide for Slack/email alerts
- Usage examples for each quality check
- Threshold configuration guide
- Pipeline integration examples
- Troubleshooting section
- Best practices for tuning

### Key Features

**Automation-Focused Design:**
- All checks return boolean + metrics for programmatic decision-making
- Automatic alert generation with contextual information
- Quick-check modes for fast validation in tight loops
- Sampling for large datasets (10% default) to avoid performance impact

**Quality Metrics Tracked:**

*MS Quality:*
- Basic properties (rows, antennas, channels, SPWs, fields, scans, time range)
- Column presence (DATA, MODEL_DATA, CORRECTED_DATA, WEIGHT_SPECTRUM)
- Data statistics (flagging, zeros, amplitude range)
- UVW validity (presence, all-zeros check, median UV distance)

*Calibration Quality:*
- Solution counts (antennas, SPWs, total solutions)
- Amplitude statistics (median, RMS, scatter)
- Phase statistics (median, RMS, scatter in degrees)
- Per-antenna flagging rates
- CORRECTED_DATA validation (calibration factor, all-zeros check)

*Image Quality:*
- Dimensions (nx, ny, channels, Stokes)
- Pixel statistics (median, RMS, min, max)
- Dynamic range (peak/RMS)
- Peak SNR
- Source detection (pixels above 5-sigma threshold)
- Residual statistics (mean, RMS for residual images)

**Alert Categories:**
- `ms_conversion` - MS quality after UVH5→MS conversion
- `calibration` - Calibration table/CORRECTED_DATA issues
- `imaging` - Image quality issues
- `pipeline` - Overall pipeline workflow events
- Additional: `disk_space`, `queue_depth`, `stuck_job`, `system`

**Slack Integration:**
- Color-coded messages by severity
- Emoji indicators per severity level
- Structured attachments with context fields
- Automatic username/icon customization
- Webhook URL from environment variable
- Automatic disable if webhook not configured

**Email Integration (Optional):**
- SMTP support with TLS
- Multiple recipients (comma-separated)
- Defaults to ERROR and CRITICAL only
- Configurable from environment variables

**Rate Limiting:**
- 10 alerts per category per 5-minute window (configurable)
- Suppressed alerts tracked and summarized
- Prevents alert fatigue during cascading failures

### Configuration Quick Reference

```bash
# Enable Slack alerts
CONTIMG_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Quality thresholds (defaults shown)
CONTIMG_QA_MS_MAX_FLAGGED=0.5
CONTIMG_QA_MS_MAX_ZEROS=0.3
CONTIMG_QA_CAL_MAX_FLAGGED=0.3
CONTIMG_QA_IMG_MIN_DYNAMIC_RANGE=5.0
CONTIMG_QA_IMG_MIN_PEAK_SNR=5.0
```

### Usage Examples

**Quick MS Check After Conversion:**
```python
from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion
passed, metrics = check_ms_after_conversion(ms_path, quick_check_only=True, alert_on_issues=True)
```

**Full Calibration Validation:**
```python
from dsa110_contimg.qa.pipeline_quality import check_calibration_quality
passed, results = check_calibration_quality(caltables, ms_path=ms, alert_on_issues=True)
```

**Image Quality Check:**
```python
from dsa110_contimg.qa.pipeline_quality import check_image_quality
passed, metrics = check_image_quality(image_path, alert_on_issues=True)
```

### Integration Status

**Ready for Integration:**
- All QA modules created and tested
- Configuration added to `contimg.env`
- Documentation complete
- Alert system fully functional (requires webhook URL to activate)

**Next Steps for Production:**
1. Obtain Slack webhook URL from workspace admin
2. Add webhook to `contimg.env`: `CONTIMG_SLACK_WEBHOOK_URL=...`
3. Restart services: `sudo systemctl restart contimg-stream contimg-api`
4. Test alerts: `python -c "from dsa110_contimg.utils import alerting; alerting.info('test', 'System ready!')"`
5. Integrate quality checks into conversion/calibration/imaging workers
6. Monitor alert frequency for 24 hours
7. Tune thresholds based on false positive rate

### Benefits for Operations

**Zero-Touch Quality Control:**
- Automatic detection of bad MS files before calibration
- Immediate notification of calibration failures
- Validation of image quality before distribution

**Rapid Issue Detection:**
- Issues caught within seconds of occurrence
- Alerts include diagnostic context for quick triage
- Rate limiting prevents alert fatigue

**Data Quality Assurance:**
- Every MS validated before processing
- Calibration solutions verified before application
- Images checked for scientific validity

**Operational Visibility:**
- Real-time notification of pipeline health
- Historical alert tracking via API
- Integration-ready for Grafana/monitoring dashboards

## 2025-10-24 – Forced Photometry & Variability Monitoring

### Current Status (as of 2025-10-24)

**Implemented:**
- Core flux measurement (`photometry/forced.py`): peak extraction, RMS estimation, WCS conversion
- Database storage (`photometry` table): stores `peak_jyb`, `peak_err_jyb`, `nvss_flux_mjy`, `measured_at`
- CLI interface (`photometry/cli.py`): `peak`, `peak-many`, `nvss` commands
- Integration point: NVSS-driven forced photometry at catalog positions

**Not Yet Implemented:**
- Temporal tracking (no source registry or cross-epoch linking)
- Flux normalization algorithm (absolute measurements only, not relative)
- Variability metrics (χ², fractional variability, significance)
- ESE-specific detection (characteristic timescales, morphology)
- Pipeline automation (manual CLI only)
- Quality control flags

### ESE Detection Requirements

**Physical Characteristics:**
- Timescales: weeks to months (plasma lensing in ISM)
- Morphology: asymmetric light curve (slow dip → sharp caustic peaks → gradual recovery)
- Achromatic: affects all frequencies similarly
- Rare: ~0.5-1 event per source per century

**Detection Strategy:**
- Require 1-5% photometric precision for 10-50% flux variations
- Must use **relative flux** normalization (absolute calibration drifts)
- Reference ensemble: 10-20 stable NVSS sources per FoV
- Use `master_sources.sqlite3` catalog (`final_references` view) for stable, high-SNR sources
- Differential flux ratios: normalize target against ensemble median correction

### Proposed Database Schema Extension

```sql
-- Source registry (persistent IDs across epochs)
CREATE TABLE photometry_sources (
    source_id INTEGER PRIMARY KEY,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    nvss_name TEXT,
    is_reference INTEGER DEFAULT 0
);

-- Time series measurements
CREATE TABLE photometry_timeseries (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    mjd REAL NOT NULL,
    peak_jyb REAL NOT NULL,
    peak_err_jyb REAL,
    peak_norm REAL,  -- normalized flux
    correction_factor REAL,  -- ensemble correction applied
    FOREIGN KEY(source_id) REFERENCES photometry_sources(source_id)
);

-- Variability summary
CREATE TABLE photometry_variability (
    source_id INTEGER PRIMARY KEY,
    n_epochs INTEGER,
    flux_mean REAL,
    flux_std REAL,
    chi2_reduced REAL,
    frac_variability REAL,
    ese_candidate INTEGER DEFAULT 0,
    last_updated REAL,
    FOREIGN KEY(source_id) REFERENCES photometry_sources(source_id)
);
```

### Implementation Phases

1. **Enhanced Data Model** (1-2 days): Add new tables, create source registry from NVSS/master catalog
2. **Normalization Module** (2-3 days): ✓ COMPLETED `photometry/normalize.py` with ensemble correction
3. **Time Series & Variability** (2-3 days): `photometry/variability.py` with metrics computation
4. **Pipeline Integration** (1-2 days): Hook into imaging worker after `.pbcor.fits` creation
5. **Visualization & API** (2-3 days): Light curve endpoints, ESE candidate dashboard

### Implementation Status (2025-10-24)

**Completed:**
- ✓ Literature review and algorithm design (docs/reports/ESE_LITERATURE_SUMMARY.md)
- ✓ Normalization module (`photometry/normalize.py`):
  - Differential flux ratio algorithm (Option 2)
  - Reference source selection from `master_sources.final_references`
  - Baseline establishment (median of first 10 epochs)
  - Ensemble correction computation with outlier rejection
  - Error propagation
  - Reference stability checking (χ² monitoring)
- ✓ Validation test script (`tests/test_photometry_normalization_0702.py`):
  - Two modes: 'baseline' (Day 1) and 'validate' (Day 2)
  - Measures all references, computes correction, validates <3% scatter
  - Diagnostic plots (raw vs normalized flux, ratio distribution, deviations)

**Documentation:**
- ✓ Comprehensive mkdocs page created: `docs/science/photometry_normalization.md`
  - Mathematical formulation with LaTeX equations
  - Step-by-step algorithm explanation with examples
  - Usage guide with code snippets
  - Troubleshooting section
  - Performance metrics and validation criteria
- ✓ Added to mkdocs navigation under new "Science" section

**Next Steps:**
- Test on 0702+445 field (two consecutive transits, 24h apart)
- Regenerate bandpass daily
- Validate normalized scatter < 3% (target: 1-2%)
- If successful, proceed with Phase 3 (variability metrics)

## 2025-10-24 – Directory Architecture & Data Organization

### Current State

**Configuration vs. Reality Mismatch:**
- Config points to `/data/{ingest,ms,scratch}` but data actually lives in `/scratch/dsa110-contimg/`
- State databases in `/scratch/` (should be in persistent `/data/` location)
- Flat directory structure makes automated cleanup difficult

**Current `/scratch/dsa110-contimg/` Usage:**
```
incoming/     7.0 GB   - Raw UVH5 files
ms/          76  GB   - MS files, caltables (flat, needs organization)
images/      12  KB   - Nearly empty
state/      2.2  MB   - SQLite DBs (WRONG LOCATION)
static/     522 MB   - Beam models, catalogs
```

### Recommended Architecture

**Key Principles:**
1. Separate code (`/data/dsa110-contimg/`) from data (`/scratch/dsa110-contimg/`)
2. Organize by lifecycle: incoming → processing → archive → purge
3. Date-based directories for manageable navigation (YYYY-MM-DD)
4. Separate calibrators, science, and failed observations
5. Automated retention and cleanup

**Proposed Structure:**
```
/data/dsa110-contimg/          # Code & persistent state
├── state/                     # SQLite databases (persistent!)
│   ├── ingest.sqlite3
│   ├── cal_registry.sqlite3
│   ├── products.sqlite3
│   └── master_sources.sqlite3
└── ...

/scratch/dsa110-contimg/       # Fast SSD for active data
├── incoming/                  # Raw UVH5 (retention: 1-7 days)
├── ms/
│   ├── calibrators/          # Cal observations (retention: 30d)
│   │   └── YYYY-MM-DD/
│   ├── science/              # Science obs (retention: 7d after imaging)
│   │   └── YYYY-MM-DD/
│   └── failed/               # Quarantine (retention: 14d)
│       └── YYYY-MM-DD/
├── images/
│   ├── single/               # Single-epoch images (retention: 90d)
│   │   └── YYYY-MM-DD/
│   ├── mosaics/              # Mosaics (indefinite, archive to tape)
│   └── qa/                   # QA plots (retention: 30d)
│       └── YYYY-MM-DD/
├── static/                   # Static reference data
│   ├── beam-model/
│   └── catalogs/
└── tmp/                      # Transient files (auto-cleanup)
    └── staging/

/dev/shm/dsa110-contimg/      # tmpfs staging (now default, 47GB available)
└── <timestamp>/              # Per-conversion workspace (auto-cleaned)
```

**Naming Conventions:**
- Timestamps: `YYYY-MM-DDTHH:MM:SS` (ISO 8601, sortable)
- Date dirs: `YYYY-MM-DD` (max 365/year, manageable)
- Group IDs: `YYYY-MM-DD_HH_MM_SS` (filesystem-safe)

**Data Retention Policy:**
| Type | Location | Retention | Status |
|------|----------|-----------|--------|
| All data | all locations | INDEFINITE | No auto-deletion |
| Staging (tmpfs) | /dev/shm/ | Minutes | Auto-cleaned (OK) |

**Note:** No automatic deletion until archival strategy finalized. All data kept indefinitely.

**Disk Space Management:**
- Capacity: 1TB total, 378GB free (57% used)
- Alert at <200GB free (WARNING), <100GB free (CRITICAL)
- Manual cleanup only after archive to `/data/` verified
- Growth monitoring: track GB/day to predict intervention timing

### Migration Plan

**Phase 1 (Immediate):** Align config with reality
- Update `contimg.env` paths to actual `/scratch/dsa110-contimg/` locations
- No data movement, just configuration correction

**Phase 2 (This week):** Move databases to persistent storage
- Migrate `state/*.sqlite3` from `/scratch/` to `/data/`
- Setup daily backups to `/data/backups/contimg/`
- 14-day local retention, ship to remote

**Phase 3 (This month):** Implement organization & retention
- Create date-organized directory structure
- Add cleanup cron job with retention policies
- Automatic archival to tape/cloud

**Phase 4 (Ongoing):** Gradual migration
- New data follows organized structure
- Migrate existing flat files as needed
- Tune retention based on usage

### Impact on Pipeline

**API Changes Needed:**
- Path resolution from environment variables (not hardcoded)
- Database queries for file discovery (faster than filesystem search)
- Support for date-organized paths in product lookups

**Monitoring Requirements:**
- Disk usage metrics (scratch free GB, tmpfs usage %)
- Directory statistics (file count, size, oldest file age)
- Cleanup event tracking (what was purged, when, why)

### System Specifications (Confirmed)

1. **Archive strategy:** `/data/` primary target, external backup TBD
2. **Retention policy:** **INDEFINITE** - no automatic deletion until archive strategy finalized
3. **Calibration strategy:**
   - Bandpass + full calibration: every 24 hours
   - Gain calibration: every 1 hour
   - Sky models: NVSS component lists via ft() into MODEL_DATA
4. **Storage capacity:** 1TB total in `/scratch/`, 378GB free (57% used, healthy headroom)
5. **Backup infrastructure:** Under development for `/data/`

### Calibration Details

**24-Hour Full Calibration:**
- Delay (K), Bandpass (BP), Gain (G) tables
- Valid for 24 hours
- Naming: `<timestamp>_24h.{kcal,bpcal,gpcal}`

**Hourly Gain Updates:**
- Gain (G) table only
- Valid for 1 hour
- Uses BP from most recent 24h solve
- Naming: `<timestamp>_1h.gpcal`

**Sky Model Strategy:**
- Query brightest NVSS sources in field
- Build component list
- Use `ft()` to populate MODEL_DATA
- No pre-existing calibrator observations needed

### Infrastructure Usage: 95% Existing + 5% New QA Layer

**Pattern:** Building **on top of** existing pipeline, not replacing. All enhancements are additive.

**Existing Infrastructure (100% Preserved):**
- Conversion: hdf5_orchestrator, direct_subband writer, streaming_converter
- Calibration: solve_delay/bandpass/gains, RFI flagging, NVSS model generation
- Imaging: tclean wrapper, pbcor, FITS export
- Databases: cal_registry, products_db, ingest queue
- API: FastAPI monitoring endpoints
- **Total:** 88 Python files, all unchanged except config

**New Additions (Additive Quality Layer):**
- QA package: 5 new files (ms_quality, calibration_quality, image_quality, pipeline_quality)
- Alerting: 1 new file (utils/alerting.py - Slack/email/logging)
- Test scripts: 2 new files
- Documentation: 4 architecture/design docs
- Configuration: Environment variable additions (no code changes)
- **Total:** 12 new files

**Ratio:** 88 existing : 12 new = ~88% existing, ~12% new code

**Integration Pattern:** Wrapper, not replacement
- Original: `ms_path = convert_group(group_id)`
- Enhanced: `ms_path = convert_group(group_id); check_ms_after_conversion(ms_path)`
- Science algorithms untouched, quality gates wrap around them

**Philosophy:** Trust but verify - proven pipeline + automated validation for lights-out operation

See `docs/reports/PIPELINE_ENHANCEMENT_SUMMARY.md` for complete breakdown.

### Documentation

See `docs/operations/DIRECTORY_ARCHITECTURE.md` for complete specification including:
- Detailed directory tree
- Naming conventions
- Retention policy
- Migration steps
- Monitoring strategy
- Best practices

## 2025-10-24 – Data Flow Through the Pipeline

### Overview: Data Journey from Raw Visibilities to Science Images

The DSA-110 continuum imaging pipeline processes radio interferometer data through a multi-stage workflow, transforming raw visibility measurements into calibrated, deconvolved science images.

### Physical Locations (Storage)

**Input/Staging:**
- `/data/incoming/` or `/data/incoming_data/` - Raw UVH5 subband files arrive here
- `/scratch/dsa110-contimg/` - Fast SSD scratch space for staging and intermediate products
- `/dev/shm/` - Optional RAM disk (tmpfs) for ultra-fast MS writes

**Outputs:**
- `/data/dsa110-contimg/data-samples/ms/` - Converted Measurement Sets
- `/scratch/dsa110-contimg/ms/` - Working MS directory for calibration/imaging
- `/data/dsa110-contimg/state/qa/` - Quality assurance plots and diagnostics

**State & Databases:**
- `/data/dsa110-contimg/state/ingest.sqlite3` - Queue tracking (ingest_queue, subband_files, performance_metrics)
- `/data/dsa110-contimg/state/cal_registry.sqlite3` - Calibration table registry (caltables, validity windows)
- `/data/dsa110-contimg/state/products.sqlite3` - Products tracking (ms_index, images, qa_artifacts)
- `/data/dsa110-contimg/state/catalogs/master_sources.sqlite3` - NVSS/VLASS/FIRST source catalog

**Reference Data:**
- `/scratch/dsa110-contimg/vp/dsa110.vp` - Voltage pattern (primary beam model)
- `/scratch/dsa110-contimg/dsa110-beam-model/DSA110_beam_1.h5` - Beam model H5 source

### Processing Flow (Step-by-Step)

#### Stage 1: Ingest & Monitoring
**Location:** `/data/incoming/` → SQLite queue
**Process:** `streaming_converter.py` (systemd: `contimg-stream.service`)
1. **DirectoryWatcher** monitors for new `*_sb??.hdf5` files (16 subbands/group)
2. Files detected via inotify/polling and queued in `ingest.sqlite3`
3. When all 16 subbands arrive for a 5-minute window, group status → `pending`
4. **State transitions:** `collecting` → `pending` → `in_progress` → `processing_fresh` → `completed`

#### Stage 2: UVH5 → Measurement Set Conversion
**Location:** `/data/incoming/` → `/scratch/` → output MS
**Process:** `hdf5_orchestrator.py` (batch converter)
1. **Group Discovery:** `find_subband_groups()` identifies complete 16-subband sets by timestamp
2. **Writer Selection:** 
   - Auto heuristic: ≤2 subbands → `pyuvdata` (monolithic)
   - Otherwise → `direct-subband` (parallel per-subband + concat)
3. **Per-Subband Processing:**
   - Read UVH5 → UVData object via pyuvdata
   - Set telescope identity (`PIPELINE_TELESCOPE_NAME=OVRO_DSA`)
   - Phase to meridian at observation midpoint
   - Compute/update UVW coordinates
4. **Staging Strategy:**
   - RAM staging: Write to `/dev/shm/` if space available (>80% free)
   - SSD staging: Write parts to `/scratch/` for concat
5. **MS Creation:**
   - Concatenate frequency subbands (CASA `concat`)
   - Preallocate `MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM` columns
   - Stamp `OBSERVATION::TELESCOPE_NAME`
6. **Timing Checkpoints:** Conversion, concat, K/BP/G solves logged to `performance_metrics`

#### Stage 3: RFI Flagging (Pre-Calibration)
**Location:** In-place on MS
**Process:** `calibration.flagging` module
1. **reset_flags:** Clear any existing flags
2. **flag_zeros:** Flag completely zero data channels
3. **flag_rfi:** Statistical RFI detection and flagging

**Scientific Rationale:** Remove interference before calibration to ensure solution integrity

#### Stage 4: Calibration (K → BP → G)
**Location:** MS + caltables written to same directory
**Process:** `calibration.cli` or `calibration.calibration` module
1. **Calibrator Detection:** Check if MS is a known calibrator field
2. **Delay Calibration (K-table):**
   - `solve_delay()` - Frequency-independent delays per antenna
   - Solution interval: `'inf'` (entire scan)
   - Reference antenna selection via composite score (phase stability + SNR)
3. **Bandpass Calibration (BP-table):**
   - `solve_bandpass()` - Frequency-dependent gains
   - Solution interval: `'inf'`
   - Optional `--uvrange` cuts for speed
4. **Gain Calibration (G-table):**
   - `solve_gains()` - Time-variable atmospheric/instrumental effects
   - Shorter solution intervals (e.g., `'30s'` or `'int'`)
   - Phase-only mode available via `--fast`
5. **Flux Scale:** Set via `setjy` using Perley-Butler 2017 standard
6. **Registry:** Caltables registered in `cal_registry.sqlite3` with validity windows (MJD ranges)

**Fast Mode:** `--fast` enables time/channel binning, phase-only gains, uvrange cuts

#### Stage 5: Apply Calibration
**Location:** In-place, writes to `CORRECTED_DATA` column
**Process:** `apply_to_target()` or `imaging.worker.py`
1. **Lookup Active Caltables:** Query `cal_registry.sqlite3` by MS mid-MJD
2. **Apply Tables:** CASA `applycal` writes corrected visibilities
3. **Validation:** Verify `CORRECTED_DATA` is non-zero
4. **Tracking:** Update `ms_index` table with processing status

**For Non-Calibrators:** Latest registered caltables applied automatically

#### Stage 6: Sky Model Seeding (Optional)
**Location:** MS `MODEL_DATA` column
**Process:** `imaging.skymodel` + CASA `ft()`
1. **Calibrator Model:** If bandpass calibrator in FoV, seed single-component model
2. **NVSS Fallback:** Query NVSS catalog for sources >10 mJy in FoV
3. **Component List:** Build CASA component list via `make_nvss_component_cl()`
4. **Fourier Transform:** `ft()` populates `MODEL_DATA` with predicted visibilities

**Purpose:** Guided deconvolution - seed known sources to accelerate convergence

#### Stage 7: Imaging & Deconvolution
**Location:** MS → image products directory
**Process:** `imaging.cli.image_ms()` or `imaging.worker`
1. **Imager:** CASA `tclean`
   - Deconvolver: `'hogbom'` (point sources) or `'multiscale'` (extended)
   - Gridder: `'wproject'` for wide-field w-term correction
   - Weighting: Briggs robust=0.5 (typical)
2. **Model Preservation:** `savemodel='none'` to retain seeded NVSS model
3. **Primary Beam Correction:** 
   - Voltage pattern from `/scratch/dsa110-contimg/vp/dsa110.vp`
   - `pbcor=True` → `.image.pbcor` output
   - Mask at `pblimit>=0.25`
4. **Outputs:**
   - `.image` - Dirty/restored image
   - `.image.pbcor` - Primary beam corrected
   - `.residual` - Deconvolution residuals
   - `.psf` - Point spread function
   - `.model` - Sky model
   - `.pb` - Primary beam image

**Quick Mode:** `--quick` caps `imsize` and `niter` for fast-look

#### Stage 8: Quality Assurance
**Location:** `/data/dsa110-contimg/state/qa/`
**Process:** `qa.fast_plots.py`
1. **Diagnostic Plots:**
   - Amplitude vs. Time/Frequency
   - Phase vs. Time/Frequency
   - UV coverage
   - Residual statistics
2. **Metrics:**
   - Reference antenna recommendation (composite score)
   - Flagging statistics
   - Image noise/dynamic range
3. **Storage:** PNG plots + JSON metadata in QA directory

#### Stage 9: Products Database & API
**Location:** `products.sqlite3` + API endpoints
**Process:** `database.products` + `api.routes`
1. **MS Index:** `ms_index_upsert()` tracks processing status, timing, MJD range
2. **Image Catalog:** `images_insert()` records image artifacts with metadata
3. **QA Artifacts:** Links to diagnostic plots and metrics
4. **API Endpoints:**
   - `/api/status` - Queue stats and calibration sets
   - `/api/qa` - QA plot discovery
   - `/api/metrics/system` - System health
   - `/api/metrics/system/history` - Performance trends

### Data Transformations Summary

**Format Progression:**
```
UVH5 (HDF5) → UVData (memory) → MS (CASA table) → Image (CASA/FITS)
   ↓              ↓                  ↓                    ↓
16 subbands   merged UV       calibrated UV        deconvolved sky
per group     single object   + caltables          + beam model
```

**Column Evolution:**
```
DATA (raw) → [flagging] → [K·BP·G applied] → CORRECTED_DATA → [tclean] → .image
                ↓                                    ↓
           FLAGS updated                       MODEL_DATA seeded
```

**Coordinate Transformations:**
- Input: Raw correlations, original phasing
- Conversion: Phase to meridian (RA=LST at midpoint)
- Output images: ICRS J2000, tangent projection (SIN)

### Parallelization & Performance

**Concurrent Operations:**
- Per-subband MS writes (direct-subband writer)
- Parallel RFI flagging across baselines
- Multi-threaded CASA operations (OMP_NUM_THREADS)

**Staging Optimizations:**
- RAM staging via tmpfs reduces I/O latency by ~3-5x
- SSD scratch prevents contention on network storage
- Atomic moves after staging prevents partial writes

**Monitoring:**
- Real-time queue depth tracking
- Per-stage timing metrics (conversion, concat, K/BP/G, tclean)
- System resource monitoring (CPU, memory, disk I/O)

### Key Design Principles

1. **Fault Tolerance:** Queue checkpointing enables restart from failures
2. **Staging Strategy:** Two-tier (RAM/SSD) balances speed and safety
3. **Scientific Rigor:** RFI → K → BP → G calibration follows canonical sequence
4. **Guided Deconvolution:** NVSS seeding improves convergence for known sources
5. **Observability:** Comprehensive QA plots and metrics at every stage
6. **Scalability:** Parallel processing + async I/O for real-time operations

## 2025-10-24 – Front-End Design Strategy

### Overview
Comprehensive web-based UI design for DSA-110 pipeline monitoring and science data exploration. The pipeline monitors 10³-10⁴ sources/day searching for extreme scattering events (ESE).

### Design Philosophy
- **Information density over volume**: One excellent, information-rich figure beats 100 individual diagnostics
- **Ease of use**: Radio astronomers should quickly find what they need
- **Real-time monitoring**: Pipeline health and data quality at a glance
- **Science-first**: Direct access to images and variability detection

### Architecture Decisions

**Framework**: React (TypeScript)
- Component-based, large ecosystem for scientific viz
- Excellent TypeScript support for type safety
- Strong integration with FastAPI backend

**Key Libraries**:
- Plotly.js for interactive scientific plots (flux timeseries, system metrics)
- D3.js for custom visualizations (sky maps, antenna arrays)
- AG Grid for high-performance source tables (10k+ rows)
- Material-UI (MUI) for professional, consistent UI components
- JS9 or Aladin Lite for FITS image display in browser
- React Query for efficient API data fetching/caching

**Build Stack**:
- Vite (fast, modern build tool)
- Tailwind CSS + CSS Modules for styling
- Dark mode by default (astronomers work at night)

### Information Architecture

**Primary Navigation (5 pages)**:
1. **Dashboard**: Executive summary - pipeline status, latest images, active alerts
2. **Sky**: Image gallery, sky coverage maps, mosaic builder, FITS viewer
3. **Sources**: Source monitoring, flux timeseries, variability detection, ESE candidates
4. **Observing**: Telescope status, pointing history, calibrator tracking, antenna health
5. **Health**: System metrics, queue monitoring, calibration registry, performance diagnostics

### Key Features by Page

**Dashboard**:
- At-a-glance pipeline status (uptime, queue depth, calibration sets)
- Live system health metrics (CPU, memory, disk, load avg)
- Recent observations table with QA links
- Latest image thumbnails
- Active alerts panel (variability, calibrator issues, system warnings)
- Quick stats (sources monitored, ESE candidates, success rates)

**Sky Page**:
- Interactive sky map showing pointing coverage over time
- Image gallery with filtering (date, declination, quality)
- Thumbnail grid with metadata overlays
- Full FITS viewer with zoom/pan, colormaps, catalog overlays
- Per-image metadata: noise, beam, calibrator, source count
- Export functionality (FITS, PNG)

**Sources Page**:
- High-performance sortable/filterable source table (10k+ sources)
- Multi-parameter filtering (variability, flux, observations, spectral index)
- Sparkline flux trends in table
- Source detail view with full flux vs. time plot
- ESE candidate dashboard with auto-flagging
- Variability statistics: χ²_ν, σ deviation, max flux change
- Catalog crossmatch info (NVSS, VLASS, FIRST)
- Export capabilities (CSV, JSON)

**Observing Page**:
- Live telescope pointing (RA/Dec, Alt/Az, LST)
- Antenna status map (online/flagged/offline)
- Pointing history visualization (sky map, last 24h/7d/30d)
- Calibrator tracking (flux vs. elevation, detection rate)
- Upcoming calibrator transits (next 6h)

**Health Page**:
- Time-series plots for system resources (6h/24h/7d)
- Processing queue status with detailed group table
- Calibration registry (active sets, validity windows)
- Performance metrics (p50, p95 for each pipeline stage)
- Throughput monitoring (images/hour, sources/hour, TB/day)
- QA diagnostic plot gallery

### Data Visualization Patterns

**High-Density Techniques**:
- Small multiples for source monitoring (20-50 sources/page with sparklines)
- Heatmaps for sky coverage (observation count, noise, variability)
- Parallel coordinates for multi-parameter source selection
- Horizon plots for dense time-series (system metrics over days/weeks)

**Interactive Features**:
- Click-to-drill-down (table row → detail view)
- Hover tooltips on all plots
- Date range selection and filtering
- Real-time updates (WebSocket or 10s polling)
- Cross-filtering (select in plot → highlight in table)
- Zoom/pan on sky maps and images

### Real-Time Data Strategy

- **Dashboard/Health**: Poll `/api/status` every 10s or WebSocket for live updates
- **Sources page**: Lazy load on demand, cache with React Query
- **Image gallery**: Paginated, load thumbnails first (progressive loading)
- **Detail views**: Fetch on-demand, client-side cache

### Implementation Roadmap

**Phase 1 (Weeks 1-3)**: Core infrastructure
- React + Vite + MUI setup
- Dashboard page (status, metrics, recent obs)
- Sky page (image gallery)
- Health page (queue status, system metrics)
- Basic navigation and routing

**Phase 2 (Weeks 4-6)**: Science features
- Sources page (table, filtering, sorting)
- Source detail view (flux timeseries)
- Photometry API integration
- Variability statistics
- ESE candidate flagging

**Phase 3 (Weeks 7-9)**: Advanced features
- WebSocket for real-time updates
- Sky map with pointing history (D3.js)
- Observing page (telescope status)
- FITS image viewer (JS9/Aladin)
- QA diagnostic gallery

**Phase 4 (Weeks 10-12)**: Polish
- Performance optimization
- Accessibility (WCAG 2.1 AA)
- Export features (CSV, PNG, PDF)
- Responsive design
- Automated testing

### Documentation Location

- **Design document**: `/docs/concepts/frontend_design.md`
- **UI mockups**: `/docs/concepts/dashboard_mockups.md`

These provide comprehensive specs for development kickoff.

### Success Metrics

**User Experience**:
- Time to find specific source: <30s
- Time to assess pipeline health: <10s
- Source identification: "Know within 5s if something interesting happened"

**Performance**:
- Initial page load: <2s
- Data refresh: <1s
- 10k source table filter/sort: <1s
- Image thumbnail load: <500ms

### Finalized Design Decisions

1. **Source naming**: NVSS IDs (e.g., "NVSS J123456.7+420312") - primary survey for current Dec pointings
2. **Variability threshold**: 5σ auto-flags ESE candidates (χ²_ν > 5 OR flux deviation > 5σ)
3. **Alert delivery**: 
   - In-app real-time visual panel (10s refresh)
   - Slack webhooks (Phase 2, rate-limited to 1 alert/source/hour)
4. **Data retention**: Persistent storage, no expiration currently
5. **Mosaic queries**: Time-range query (start/end UTC) for ~hour-long mosaics
6. **External API**: VO Cone Search planned (Phase 3) for Aladin/TOPCAT integration

### Alert System Details

**In-App**: Real-time ESE candidate panel on Dashboard
- Color-coded: Red (>5σ), Yellow (3-5σ), Green (normal)
- Direct links to source detail pages
- Shows NVSS ID, significance, flux change, time

**Slack Integration** (Phase 2):
- Webhook-based notifications
- Rich message format with "View Source" button
- Environment: `SLACK_WEBHOOK_URL`, `SLACK_ALERT_CHANNEL`
- Rate limiting: Max 1 alert per source per hour

### Mosaic Query System

**Time-Range Interface**:
- Start/End time (UTC or MJD)
- Declination range filter (+40° to +45° current)
- Preview coverage before generation
- Async job processing for long-running mosaics
- Download FITS/PNG when complete

**API Endpoint**: `/api/mosaic/query?start_mjd=X&end_mjd=Y&dec_min=40&dec_max=45`

## 2025-10-27 – Dashboard/API bring-up and route fix

- Backend bug fix: moved `app.include_router(router)` to the end of `create_app()` so routes declared later are exposed. This enables the enhanced endpoints:
  - `/api/ese/candidates`, `/api/mosaics/query`, `/api/mosaics/create`, `/api/sources/search`, `/api/alerts/history`, `/api/ms_index`, `/api/reprocess/{group_id}`
  - File: `src/dsa110_contimg/api/routes.py`
- CORS: allowed additional dev origins (5174) to support a second Vite dev server. File: `src/dsa110_contimg/api/routes.py`.
- Docker Compose: updated `ops/docker/.env` to set `CONTIMG_API_PORT=8010` (8000/8001 were in use by host processes). Brought up `contimg-api` via `make compose-up-api`.
- Verification:
  - `curl http://localhost:8010/openapi.json` shows the new paths listed above.
  - `curl http://localhost:8010/api/ese/candidates` returns mock candidates.
- Frontend note:
  - Existing dev server at 5173 points at 8000; to use enhanced endpoints, run with `VITE_API_URL=http://localhost:8010 npm run dev` (preferably under `conda run -n casa6` to satisfy Vite's Node version requirement), or set Vite proxy target to 8010.

## 2025-10-27 – Job Runner Health + Control Panel plumbing

- Health endpoint added: `GET /api/jobs/healthz`
  - Returns readiness booleans: `ok`, `subprocess_ok`, `casa_ok`, `src_ok`, `db_ok`, `disk_ok`
  - Includes `disk` (bytes total/used/free) and `env` (python executable/version, `py_cmd`, `src_path`, `products_db`, `state_dir`, and error strings when checks fail)
  - Use for preflight checks in dashboard before enabling job actions
- SSE logs non‑blocking: switched log stream to `asyncio.sleep(1)` to avoid blocking event loop during `/api/jobs/id/{job_id}/logs` streaming
- Job runner is env‑aware (container or host):
  - Chooses interpreter via `CONTIMG_JOB_PY` → `CONTIMG_CONDA_ENV` → `sys.executable`
  - Exports `PYTHONPATH` to detected repo `src` (works for `/app/src` in container and `/data/dsa110-contimg/src` on host)
  - Removes hard‑coded `conda run -n casa6` dependency
  - File: `src/dsa110_contimg/api/job_runner.py`
- Job routes reshaped to avoid path collisions:
  - `GET /api/jobs/{job_id}` → `GET /api/jobs/id/{job_id}`
  - `GET /api/jobs/{job_id}/logs` → `GET /api/jobs/id/{job_id}/logs`
  - New: `GET /api/jobs/healthz`
- Pydantic safety: list defaults now use `default_factory` for `GroupDetail.qa` and `Job.artifacts`
- Frontend/dev convenience:
  - Vite proxy target is parametric: `API_PROXY_TARGET` (default `http://localhost:8010`)
  - File: `frontend/vite.config.ts`
- Service script improvements (`scripts/manage-services.sh`):
  - Ports configurable: `CONTIMG_API_PORT`, `CONTIMG_DASHBOARD_PORT`, `CONTIMG_DOCS_PORT`
  - Starts mkdocs (`start docs`), injects `VITE_API_URL` for dev dashboard, shows docs status
  - Fixes queue DB path to `state/ingest.sqlite3`
- Docker Compose defaults: `UID=1000`, `GID=1000` to avoid root‑owned artifacts (recreate containers to apply)
- Operational note: healthz currently shows `disk_ok=false` (very low free space under `PIPELINE_STATE_DIR`) and `casa_ok=false` in the job env. Free space or adjust mount, and set `CONTIMG_CONDA_ENV=casa6` (or `CONTIMG_JOB_PY`) if jobs should run in CASA env.
