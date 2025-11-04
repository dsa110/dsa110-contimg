# Complete Project Review: Rules, Memories, and Pipeline Scope

**Date:** 2025-11-02  
**Scope:** Full review of dsa110-contimg rules, memory system, and pipeline architecture

---

## 1. Rules Structure

### 1.1 Core Graphiti Rules

**Location:** `.cursor/rules/graphiti/graphiti-mcp-core-rules.mdc`

**Key Principles:**
- **Always search first:** Use `search_nodes` and `search_facts` before starting tasks
- **Save immediately:** Capture requirements, preferences, and procedures as they emerge
- **Respect preferences:** Align work with discovered preferences and procedures
- **Use structured data:** Leverage JSON for automatic entity/relationship extraction
- **Search capabilities:** Hybrid search combining vector similarity, full-text, and graph traversal

**Entity Extraction:**
- Use structured extraction patterns (AI persona, task, context, instructions)
- Maintain entity integrity with clear, unique purposes
- Prefer explicit information over assumptions
- Handle ambiguity properly

**Memory Management:**
- Before tasks: Search for preferences/procedures/facts
- During work: Respect discovered knowledge, follow procedures
- After work: Save new knowledge using `add_episode` with appropriate source types
  - `'text'`: Plain content
  - `'json'`: Structured data (automatic entity extraction)
  - `'message'`: Conversation-style content

### 1.2 Project-Specific Schema

**Location:** `.cursor/rules/graphiti/graphiti-dsa110-contimg-schema.mdc`

**Defined Entities:**
- `Project`, `Module`, `File`, `FileType`, `Documentation`, `Script`, `DataSample`, `Configuration`, `Test`
- `Dataset` (UVH5/HDF5 bundles, MS)
- `Run` (pipeline execution)
- `Artifact` (outputs: FITS, MS, QC reports)
- `Paper` (references)
- `Procedure` (reproducible methods)
- `Preference` (project/module/procedure/script settings)

**Key Relationships:**
- `CONTAINS_MODULE`, `CONTAINS_FILE`, `REFERENCES_FILE`
- `USES_CONFIGURATION`, `PROCESSES_DATA_SAMPLE`, `DOCUMENTS`
- `CONSUMES`, `PRODUCES`, `EXECUTES`, `TRIGGERED_BY`
- `CONTAINS_SAMPLE`, `IMPLEMENTS_PROCEDURE`, `INFORMED_BY`
- `HAS_PREFERENCE` (at Project/Module/Script/Procedure scope)

**Project-Specific Procedures:**
1. `conversion/uvh5-to-ms`
   - Default: `writer=auto`, `stage_to_tmpfs=true`
   - Production: `parallel-subband` for 16 subbands
   - Testing: `pyuvdata` for ≤2 subbands only

2. `calibration/fast-bandpass-gain`
   - Fast mode: time/channel binning, phase-only gains, uvrange cuts
   - Default: `phase_only=true` when `--fast`

3. `imaging/quick-tclean`
   - Quick mode: reduced imsize/niter, optional FITS skip
   - Default: `nvss_min_mjy=10.0` for NVSS seeding

### 1.3 Schema Maintenance Rules

**Location:** `.cursor/rules/graphiti/graphiti-knowledge-graph-maintenance.mdc`

**Process for Schema Evolution:**
1. Identify need (new entity/relationship/property)
2. Consult existing schema
3. Propose update with justification
4. Wait for acceptance/rejection
5. Proceed based on outcome

**Principles:**
- Project schema is single source of truth
- Schema rules override general core rules
- Justify all changes with user request/context linkage

### 1.4 Agent Workflow Rules

**Location:** `.cursor/rules/dsa110_agent_workflow.mdc`

**Mandatory Workflow (Combined-Memory Learning Loop):**

**Step A: Knowledge Retrieval**
- Query Graphiti first (`search_memory_facts` or `search_memory_nodes`)
- Formulate relevant query
- Incorporate findings into plan

**Step B: Analysis and Development**
- Use Serena for code analysis
- Execute task with available tools

**Step C: Knowledge Synthesis**
- Summarize findings
- Structure as JSON payload
- Ingest via `add_memory` with `source='json'`
- Verify ingestion (optional)

### 1.5 Workspace-Specific Rules

**Repository Rule:**
- **CRITICAL:** Note lessons/principles in `MEMORY.md` (freely editable)
- Refer to `MEMORY.md` for guidance in all coding sessions

**User Rules:**
- Concise style, no unnecessary repetition
- Fix root causes, not symptoms
- One fix at a time, validate, iterate
- No emojis (use ✓/✗ if needed)
- Reference expert reasoning when possible

---

## 2. Memory System

### 2.1 Primary Memory File

**Location:** `docs/reports/memory.md` (1,301 lines)

**Key Sections:**

**VP Table Construction (DSA-110):**
- Telescope: `DSA_110`
- Source: `/scratch/dsa110-contimg/dsa110-beam-model/DSA110_beam_1.h5`
- Output: `/scratch/dsa110-contimg/vp/dsa110.vp`
- Jones mapping and coordinate system details

**Project Memory - dsa110-contimg:**
- RAM staging preference (`/dev/shm`)
- Auto writer heuristic (≤2 subbands → pyuvdata, else parallel-subband)
- Production: 16 subbands, always use `parallel-subband`
- **SQLite databases preferred** for pipeline stages
- Fast calibration: `--fast` with time/channel averaging
- Quick imaging: `--quick` to cap imsize/niter

**Critical Fixes:**
- Phase coherence fix (2025-11-02): Shared phase center for entire group
- Test MS creation utility: `scripts/create_test_ms.py`
- Upstream delay checking: `scripts/check_upstream_delays.py`
- K-calibration necessity: Documented consequences of skipping
- DSA-110 K-cal need: No exemptions found, must perform K-cal
- VLA catalog access: Always use `load_vla_catalog()` (SQLite preferred)
- Proper transit time calculation: Use astronomical calculations, verify data exists

**Control Panel & Service Management (2025-10-27):**
- React-based web UI with live log streaming
- Backend: FastAPI with SQLite job tracking
- Service management: Script/systemd/docker-compose options
- Port assignments: 8000 (API), 3000 (Dashboard)

**Telescope Identity (2025-10-22/23):**
- Single source: `PIPELINE_TELESCOPE_NAME=DSA_110`
- Helper: `set_telescope_identity` in `conversion/helpers.py`
- Applied on all write paths
- EveryBeam 0.7.4+ recognizes `DSA_110` for Airy disc

**NVSS Sky Model Seeding (2025-10-23):**
- Imaging CLI supports `--nvss-min-mjy`
- Skymodel helpers for component lists
- Precedence: Calibrator model → NVSS fallback

**UVH5 to MS Conversion Lessons:**
- Circular import issues resolved via lazy imports
- FUSE temporary files: Normal behavior, cleanup needed
- Python environment: `casa6` conda, `PYTHONPATH` required
- Module layout: Active code in `dsa110_contimg/conversion/`

**Quality Assurance & Alerting (2025-10-24):**
- Multi-channel alerts (Slack/email/logging)
- MS validation, calibration quality, image quality checks
- Configurable thresholds via environment variables
- Rate limiting (10 alerts/category/5min)

**Photometry & Variability (2025-10-24):**
- Core flux measurement implemented
- Database storage (`photometry` table)
- Normalization module: Ensemble correction algorithm
- ESE detection: Requires relative flux normalization

**Directory Architecture (2025-10-24):**
- Separate code (`/data/`) from data (`/scratch/`)
- Date-based organization (YYYY-MM-DD)
- Data retention: **INDEFINITE** (no auto-deletion)
- Storage capacity: 1TB total, 378GB free

**Pipeline Data Flow (2025-10-24):**
- 9 stages: Ingest → Conversion → RFI Flagging → Calibration → Apply → Sky Model → Imaging → QA → API
- Physical locations and database schemas documented

**Frontend Design (2025-10-24):**
- React/TypeScript with Material-UI
- 5 primary pages: Dashboard, Sky, Sources, Observing, Health
- Real-time updates, high-performance tables, FITS viewer integration

**Critical K-Calibration Issues (2025-11-02):**
- MODEL_DATA precondition check added
- Hardcoded reference frequency fixed (extract from MS)
- "Measure twice, cut once" philosophy emphasized

### 2.2 Graphiti Knowledge Graph

**Storage:** Neo4j backend (via MCP server)  
**Group ID:** `dsa110-contimg` (default)

**Entities Tracked:**
- Preferences, Procedures, Requirements
- Software components, data products, pipeline stages
- Relationships: CONSUMES, PRODUCES, DEPENDS_ON, INFORMED_BY

**Integration:**
- Git post-commit hook (`.githooks/post-commit`) records commits
- Serena memories in `.serena/memories/` for code analysis
- Graphiti episodes for task execution history

---

## 3. Pipeline Complete Scope

### 3.1 Pipeline Architecture

**Core Processing Stages:**
```
UVH5 Files → Conversion → RFI Flagging → Calibration → Apply → Sky Model → Imaging → QA → Products
  (16 sb)     (MS)        (Flags)      (K/BP/G)      (CORRECTED)  (MODEL)   (tclean)   (plots)  (DB/API)
```

### 3.2 Stage-by-Stage Breakdown

#### Stage 1: Ingest & Grouping
**Location:** `/data/incoming/` → SQLite queue  
**Process:** `streaming_converter.py` (systemd: `contimg-stream.service`)
- Watches for `*_sb??.hdf5` files
- Groups by timestamp (5-minute windows)
- Requires complete 16-subband sets
- State: `collecting` → `pending` → `in_progress` → `completed`

**Databases:**
- `state/ingest.sqlite3`: `ingest_queue`, `subband_files`, `performance_metrics`

#### Stage 2: Conversion (UVH5 → MS)
**Location:** `/data/incoming/` → `/scratch/` → MS  
**Process:** `hdf5_orchestrator.py` (orchestrator CLI)
- Writer selection:
  - Auto: ≤2 subbands → `pyuvdata` (testing only)
  - Auto: >2 subbands → `direct-subband` (production, 16 subbands)
- Operations:
  - Telescope identity setting (`DSA_110`)
  - Meridian phasing at midpoint
  - UVW coordinate computation
  - Imaging column initialization (`MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM`)
- Staging: tmpfs (`/dev/shm`) default, ~3-5x speedup
- Output: Full-band MS with all columns preallocated

#### Stage 3: RFI Flagging
**Location:** In-place on MS  
**Process:** `calibration.flagging`
- Reset flags
- Flag zeros
- Statistical RFI detection

#### Stage 4: Calibration (K → BP → G)
**Location:** MS + caltables in same directory  
**Process:** `calibration.cli` or API job runner
- **Delay (K-table):** Frequency-independent delays per antenna
  - Solution interval: `'inf'` (entire scan)
  - Reference antenna: Composite score (phase stability + SNR)
- **Bandpass (BP-table):** Frequency-dependent gains
  - Solution interval: `'inf'`
  - Optional `--uvrange` cuts for speed
- **Gain (G-table):** Time-variable atmospheric/instrumental effects
  - Shorter intervals (e.g., `'30s'` or `'int'`)
  - Phase-only mode via `--fast`
- **Fast Mode:** Time/channel binning, phase-only gains, uvrange cuts
- **Flux Scale:** Perley-Butler 2017 standard
- **Registry:** `cal_registry.sqlite3` with validity windows (MJD ranges)

**Critical Preconditions:**
- MODEL_DATA must be populated before K-calibration
- Field validation, reference antenna validation
- Calibration table validation after solve

#### Stage 5: Apply Calibration
**Location:** In-place, writes to `CORRECTED_DATA`  
**Process:** `apply_to_target()` or `imaging.worker.py`
- Lookup active caltables from `cal_registry.sqlite3` by MS mid-MJD
- CASA `applycal` writes corrected visibilities
- Validation: Verify `CORRECTED_DATA` is non-zero
- Tracking: Update `ms_index` table

#### Stage 6: Sky Model Seeding (Optional)
**Location:** MS `MODEL_DATA` column  
**Process:** `imaging.skymodel` + CASA `ft()`
- Calibrator model: Single-component if bandpass calibrator in FoV
- NVSS fallback: Query catalog for sources >10 mJy in FoV
- Component list: `make_nvss_component_cl()`
- Fourier transform: `ft()` populates `MODEL_DATA`

#### Stage 7: Imaging & Deconvolution
**Location:** MS → image products directory  
**Process:** `imaging.cli.image_ms()` or `imaging.worker`
- **Imager:** CASA `tclean`
  - Deconvolver: `'hogbom'` (point) or `'multiscale'` (extended)
  - Gridder: `'wproject'` (wide-field w-term correction)
  - Weighting: Briggs robust=0.5 (typical)
- **Model Preservation:** `savemodel='none'` to retain seeded NVSS model
- **Primary Beam Correction:**
  - Voltage pattern: `/scratch/dsa110-contimg/vp/dsa110.vp`
  - `pbcor=True` → `.image.pbcor`
  - Mask at `pblimit>=0.25`
- **Outputs:** `.image`, `.image.pbcor`, `.residual`, `.psf`, `.model`, `.pb`
- **Quick Mode:** `--quick` caps `imsize` and `niter`

#### Stage 8: Quality Assurance
**Location:** `/data/dsa110-contimg/state/qa/`  
**Process:** `qa.fast_plots.py`, `qa.pipeline_quality.py`
- **Diagnostic Plots:** Amplitude/phase vs. time/frequency, UV coverage, residuals
- **Metrics:** Reference antenna, flagging statistics, image noise/dynamic range
- **Validation:**
  - MS quality: Column presence, UVW validity, flagging rates
  - Calibration quality: Solution statistics, CORRECTED_DATA validation
  - Image quality: Dynamic range, peak SNR, source detection
- **Alerting:** Multi-channel (Slack/email/logging) with configurable thresholds

#### Stage 9: Products Database & API
**Location:** `products.sqlite3` + API endpoints  
**Process:** `database.products` + `api.routes`
- **MS Index:** Tracks processing status, timing, MJD range
- **Image Catalog:** Records artifacts with metadata
- **QA Artifacts:** Links to diagnostic plots and metrics
- **API Endpoints:**
  - `/api/status` - Queue stats and calibration sets
  - `/api/qa` - QA plot discovery
  - `/api/metrics/system` - System health
  - `/api/jobs/*` - Job management (calibrate/apply/image)
  - `/api/ms_index` - Filtered MS index
  - `/api/reprocess/{group_id}` - Reprocess groups

### 3.3 Key Components

**Conversion Layer (`conversion/`):**
- `streaming_converter.py`: Stream daemon
- `uvh5_to_ms.py`: Standalone converter
- `strategies/hdf5_orchestrator.py`: Orchestrator CLI (primary)
- `strategies/direct_subband.py`: Parallel per-subband writer (production)
- `strategies/pyuvdata_monolithic.py`: Single-shot writer (testing only)
- `helpers.py`: Antenna positions, meridian phasing, model/weights

**Calibration Layer (`calibration/`):**
- `cli.py`: Calibration workflow
- `calibration.py`: K/BP/G solving
- `flagging.py`: RFI detection and flagging
- `applycal.py`: Apply calibration tables
- `catalogs.py`: VLA calibrator catalog (SQLite preferred)
- `schedule.py`: Transit time calculations
- `model.py`, `skymodels.py`: Sky model generation

**Imaging Layer (`imaging/`):**
- `cli.py`: tclean CLI
- `worker.py`: Backfill imaging worker
- `skymodel.py`: NVSS component list generation

**Quality Assurance (`qa/`):**
- `ms_quality.py`: MS validation
- `calibration_quality.py`: Calibration quality assessment
- `image_quality.py`: Image quality metrics
- `pipeline_quality.py`: Unified QA interface
- `fast_plots.py`: Diagnostic plots

**API & Job Management (`api/`):**
- `routes.py`: FastAPI REST endpoints
- `job_runner.py`: Background task execution
- `models.py`: Pydantic models
- `data_access.py`: Database helpers

**Database Layer (`database/`):**
- `products.py`: Products DB helpers (`ms_index`, `images`)
- `registry.py`: Calibration table registry
- `jobs.py`: Job tracking and artifacts
- `registry_cli.py`: Registry CLI

**Utilities (`utils/`):**
- `alerting.py`: Multi-channel alerting (Slack/email/logging)
- `antpos_local/`: Antenna position utilities (consolidated from antpos)
- `graphiti_logging.py`: Graphiti integration

**Mosaicking (`mosaic/`):**
- `cli.py`: Mosaic planner/builder CLI
- `validation.py`: Pre/post-validation checks
- `error_handling.py`: Enhanced error handling
- `cache_persistence.py`: Cache management

**Photometry (`photometry/`):**
- `forced.py`: Peak flux extraction
- `normalize.py`: Ensemble correction algorithm
- `cli.py`: Photometry CLI

**Catalog (`catalog/`):**
- `build_master.py`: Master sources catalog builder
- `query.py`: Catalog query utilities

### 3.4 Data Flow & Storage

**Physical Locations:**
- **Input:** `/data/incoming/` - UVH5 subband files
- **Processing:** `/scratch/dsa110-contimg/` - Fast SSD scratch space
- **Staging:** `/dev/shm/` - tmpfs (RAM staging, default)
- **Output:** `/scratch/dsa110-contimg/ms/` - Measurement Sets
- **Images:** `/scratch/dsa110-contimg/images/` - Image products
- **State:** `/data/dsa110-contimg/state/` - SQLite databases (persistent)
- **QA:** `/data/dsa110-contimg/state/qa/` - Quality assurance plots

**Databases:**
- `state/ingest.sqlite3`: Queue tracking
- `state/cal_registry.sqlite3`: Calibration table registry
- `state/products.sqlite3`: Products tracking (`ms_index`, `images`, `qa_artifacts`)
- `state/catalogs/master_sources.sqlite3`: NVSS/VLASS/FIRST catalog
- `state/catalogs/vla_calibrators.sqlite3`: VLA calibrator catalog

**Reference Data:**
- `/scratch/dsa110-contimg/vp/dsa110.vp`: Voltage pattern (primary beam)
- `/scratch/dsa110-contimg/dsa110-beam-model/DSA110_beam_1.h5`: Beam model source

### 3.5 Key Design Principles

**Fault Tolerance:**
- Queue checkpointing enables restart from failures
- Precondition validation ("measure twice, cut once")
- Comprehensive error handling with context

**Performance Optimization:**
- Two-tier staging (RAM/SSD) balances speed and safety
- Parallel per-subband writes (production)
- tmpfs staging for 3-5x speedup (default)

**Scientific Rigor:**
- RFI → K → BP → G calibration sequence
- NVSS-guided deconvolution
- Primary beam correction and masking
- Quality assurance at every stage

**Observability:**
- Comprehensive QA plots and metrics
- Multi-channel alerting
- Performance metrics tracking
- Real-time API monitoring

**Scalability:**
- Parallel processing + async I/O
- Background job execution
- Batch operations support
- Real-time streaming pipeline

---

## 4. Current Status & Known Issues

### 4.1 Completed Features

**Core Pipeline:**
- ✅ UVH5 → MS conversion (production-ready)
- ✅ Calibration (K/BP/G)
- ✅ Imaging with primary beam correction
- ✅ Quality assurance system
- ✅ Alerting infrastructure
- ✅ API and job management

**Enhancements:**
- ✅ Control panel (React web UI)
- ✅ Service management (script/systemd/docker)
- ✅ Mosaicking (with PB weighting, validation)
- ✅ Photometry (forced photometry, normalization)
- ✅ Master sources catalog
- ✅ Telescope identity standardization

### 4.2 Known Issues & Gaps

**Precondition Checks (Priority: High):**
- Missing file readability validation before queuing
- Missing disk space checks before conversion
- Missing MS write validation after creation
- See `docs/reports/PIPELINE_WORKFLOW_PRECONDITION_REVIEW.md` for complete list

**Mosaicking:**
- ✅ All critical/important/enhancement items complete (2025-11-02)
- Status: ~98% compliance with VLASS standards

**Photometry & Variability:**
- Core measurement implemented
- Normalization module complete
- Variability metrics and ESE detection pending

**Frontend:**
- Core infrastructure in place
- Dashboard, Sky, Sources pages designed
- Implementation roadmap defined (4 phases, 12 weeks)

### 4.3 Operational Considerations

**Data Retention:**
- Policy: **INDEFINITE** (no automatic deletion)
- Storage: 1TB total, 378GB free (57% used)
- Organization: Date-based directories (not yet fully implemented)

**Calibration Strategy:**
- Bandpass + full calibration: Every 24 hours
- Gain calibration: Every 1 hour
- Sky models: NVSS component lists via `ft()`

**Monitoring:**
- Real-time queue depth tracking
- Per-stage timing metrics
- System resource monitoring
- Quality thresholds configurable via environment variables

---

## 5. Key Architectural Decisions

### 5.1 Writer Selection Strategy

**Production:** Always use `parallel-subband` for 16 subbands
- Per-subband MS parts written in parallel
- Concatenated via CASA `concat`
- Staged to tmpfs by default (~3-5x speedup)

**Testing:** `pyuvdata` writer for ≤2 subbands only
- Monolithic write via `UVData.write_ms`
- Not suitable for production (16 subbands)

**Auto Selection:** Heuristic based on subband count
- ≤2 → `pyuvdata` (testing)
- >2 → `parallel-subband` (production)

### 5.2 Staging Strategy

**Default:** tmpfs (`/dev/shm`) when available
- ~47GB available
- 3-5x performance improvement
- Automatic fallback to SSD if unavailable

**Fallback:** SSD scratch (`/scratch/dsa110-contimg/`)
- Used when tmpfs unavailable or disabled
- Same atomic move pattern

### 5.3 Calibration Strategy

**Fast Mode:** `--fast` flag enables:
- Time/channel binning (reduce data volume)
- Phase-only gains (faster solving)
- UVrange cuts (`>1klambda`)

**Full Mode:** Default for production
- Full time/frequency resolution
- Complex gains (amplitude + phase)
- All baselines

### 5.4 Imaging Strategy

**Quick Mode:** `--quick` flag enables:
- Reduced `imsize` (≤512)
- Fewer iterations (≤300)
- Lower robustness (0)
- Optional FITS export skip

**Full Mode:** Default for science products
- Full resolution
- Proper deconvolution
- Primary beam correction
- FITS export

### 5.5 Quality Assurance Philosophy

**Automation-Focused Design:**
- All checks return boolean + metrics for programmatic decisions
- Automatic alert generation with contextual information
- Quick-check modes for fast validation
- Sampling for large datasets (10% default)

**Multi-Channel Alerting:**
- Slack webhooks (color-coded by severity)
- Email SMTP (optional)
- Logging (always)
- Rate limiting (10 alerts/category/5min)

---

## 6. Integration Points

### 6.1 External Systems

**Serena (Semantic Code Analysis):**
- Location: `~/proj/mcps/oraios/serena`
- Project integration: `.serena/` directory
- Capabilities: Symbol-level code understanding, LSP-based navigation
- Memories: `.serena/memories/` (scientific/domain analysis)

**Graphiti (Knowledge Graph):**
- Storage: Neo4j backend
- MCP server integration
- Group ID: `dsa110-contimg`
- Entities: Preferences, Procedures, Requirements, custom entities

**Git Integration:**
- Post-commit hook: `.githooks/post-commit`
- Records commits as Graphiti episodes
- Non-blocking, background execution

### 6.2 Deployment Options

**Systemd (Production):**
- Units: `ops/systemd/contimg-stream.service`, `contimg-api.service`
- Environment: `ops/systemd/contimg.env`
- Auto-start on boot, automatic restart on crash

**Docker Compose:**
- File: `ops/docker/docker-compose.yml`
- Services: `stream`, `api`, `scheduler`
- Configuration: `ops/docker/.env`

**Service Management Script:**
- Location: `scripts/manage-services.sh`
- Usage: `./scripts/manage-services.sh {start|stop|restart|status|logs} [api|dashboard|all]`
- Auto-kills port conflicts, PID tracking, log management

---

## 7. Documentation Structure

**Primary Documentation:**
- `README.md`: Project overview and quick start
- `docs/pipeline.md`: Visual pipeline diagrams
- `docs/quicklook.md`: Sub-minute workflow example
- `docs/handbook/index.md`: Consolidated docs hub

**Reference Documentation:**
- `docs/reference/api.md`: API endpoints
- `docs/reference/cli.md`: CLI commands
- `docs/reference/env.md`: Environment variables
- `docs/reference/database_schema.md`: Database schemas

**Reports:**
- `docs/reports/memory.md`: Project memory (1,301 lines)
- `docs/reports/PIPELINE_WORKFLOW_PRECONDITION_REVIEW.md`: Precondition gaps
- `docs/reports/CRITICAL_K_CALIBRATION_ISSUES.md`: K-calibration fixes
- `docs/reports/MOSAICKING_REMAINING_WORK.md`: Mosaicking status

**How-To Guides:**
- `docs/howto/QUALITY_ASSURANCE_SETUP.md`: QA setup
- `docs/howto/build_vp_from_h5.md`: Voltage pattern construction
- `docs/howto/mosaic.md`: Mosaicking guide

---

## 8. Summary

**Project Status:** Production-ready radio astronomy data processing system

**Core Capabilities:**
- Streaming UVH5 → MS conversion (16 subbands)
- Full calibration pipeline (K → BP → G)
- Continuum imaging with primary beam correction
- Quality assurance and alerting
- API and job management
- Mosaicking support

**Memory System:**
- Graphiti knowledge graph (Neo4j backend)
- MEMORY.md file (1,301 lines of lessons learned)
- Serena code analysis memories
- Git commit tracking

**Rules Structure:**
- Graphiti core rules (general tool usage)
- Project-specific schema (dsa110-contimg entities/relationships)
- Schema maintenance rules (update process)
- Agent workflow rules (combined-memory learning loop)

**Key Principles:**
- "Measure twice, cut once" (precondition validation)
- SQLite databases preferred
- Production: Always use `parallel-subband` writer
- tmpfs staging by default
- Quality assurance at every stage

---

**Review Complete:** 2025-11-02

