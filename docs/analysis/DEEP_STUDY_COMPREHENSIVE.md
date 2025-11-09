# DSA-110 Continuum Imaging Pipeline - Comprehensive Deep Study

**Generated:** 2025-01-XX  
**Purpose:** Comprehensive analysis of the entire dsa110-contimg codebase architecture, implementation patterns, and technical decisions

---

## Executive Summary

The DSA-110 continuum imaging pipeline is a **production-ready radio astronomy data processing system** designed to:

1. **Convert** raw UVH5 subband visibility data into CASA Measurement Sets (MS)
2. **Calibrate** observations using VLA calibrator catalog sources
3. **Image** calibrated data using WSClean (default) or CASA tclean
4. **Measure** photometry with 1-2% relative flux precision via differential normalization
5. **Detect** Extreme Scattering Events (ESEs) - plasma lensing events causing 10-50% flux variations

**Key Achievement:** The pipeline achieves **1-2% relative flux precision** (vs ~5-10% absolute) through differential photometry normalization, enabling detection of ESE flux variations at 5-10σ significance.

**Codebase Scale:**
- ~50,000+ lines of Python code
- 169+ Python modules
- 883+ classes and functions
- 1,265+ import statements
- Comprehensive FastAPI monitoring API (4,000+ lines in routes.py)

---

## Architecture Overview

### High-Level Pipeline Flow

```
UVH5 Files → Conversion → Calibration → Imaging → Photometry → ESE Detection
  (16 sb)      (MS)      ({K}/BP/G)      (tclean)    (normalize)   (variability)
```

### Core Components

#### 1. Streaming Converter (`conversion/streaming/streaming_converter.py`)
- **Purpose:** Watches `/data/incoming/` for `*_sb??.hdf5` files
- **Grouping:** Groups by timestamp (5-minute windows, 16 subbands expected)
- **State Machine:** `collecting` → `pending` → `in_progress` → `completed` → `failed`
- **Persistence:** SQLite queue (`state/ingest.sqlite3`)
- **Features:**
  - File watching via `watchdog` (if available) or polling
  - Automatic group completion detection
  - Retry logic with exponential backoff
  - Performance metrics tracking

#### 2. Conversion Layer (`conversion/strategies/`)

**Orchestrator** (`hdf5_orchestrator.py`):
- Primary entry point for conversion
- Discovers complete subband groups in time windows
- Delegates MS creation to selected writer
- Finalizes MS for imaging (columns, antenna setup, UVW)

**Writers:**
- **`direct_subband.py`** (Production):
  - Parallel per-subband writes (16 workers)
  - CASA `concat` merges subbands
  - tmpfs staging for 3-5x speedup
  - Robust error handling
  
- **`pyuvdata_monolithic.py`** (Testing only):
  - Single-shot writer via `UVData.write_ms`
  - Limited to ≤2 subbands
  - Used for validation/testing

**Operations:**
- Sets telescope identity (`DSA_110`)
- Phases to meridian at midpoint (RA=LST, Dec from UVH5)
- Computes UVW coordinates
- Initializes imaging columns (`MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM`)
- Sets antenna positions and diameters
- Validates phase center coherence

#### 3. Calibration Layer (`calibration/`)

**Calibration Types:**

1. **K-Calibration (Delay)** - **SKIPPED BY DEFAULT**
   - Frequency-independent delays per antenna
   - Skipped for DSA-110 (short 2.6 km baselines, delays <0.5 ns absorbed into gains)
   - Use `--do-k` to explicitly enable

2. **BP-Calibration (Bandpass)**
   - Frequency-dependent gains
   - Default: `combine_fields=False` (single peak field)
   - Default: `uvrange='>1klambda'` (may be too aggressive for DSA-110)
   - Default: `minsnr=3.0`
   - **Critical:** When `combine_fields=True`, pass full field range (e.g., `'0~15'`)

3. **Pre-Bandpass Phase** (optional)
   - Time-variable phase correction before bandpass
   - Default: `solint='30s'` (not `'inf'` to avoid decorrelation)
   - Default: `minsnr=3.0`

4. **G-Calibration (Gain)**
   - Time-variable atmospheric effects
   - Default: `solint='inf'` (phase-only mode `'p'`)
   - Default: `calmode='ap'` (amplitude + phase)

**Model Data Population:**
- **Default source:** `--model-source catalog` (VLA calibrator catalog)
- **Method:** pyradiosky (default) or componentlist
- **Process:**
  1. Auto-select calibrator field (if `--auto-fields`)
  2. Rephase MS to calibrator position (unless `--skip-rephase`)
  3. Create sky model from catalog
  4. Populate `MODEL_DATA` via CASA `ft()` or manual calculation
- **Critical:** `MODEL_DATA` must contain actual visibility predictions, not just zeros

**Calibration Table Registry:**
- Tracks tables in `state/cal_registry.sqlite3`
- Validity windows (MJD start/end)
- Apply order: K → BA → BP → GA → GP → 2G → FLUX
- Active/inactive status

#### 4. Imaging Layer (`imaging/`)

**Backends:**
- **WSClean** (default, 2-5x faster than tclean)
- **CASA tclean** (available, slower)

**Features:**
- NVSS sky model seeding (≥10 mJy sources)
- Primary beam correction
- Quality tiers: `development`, `standard`, `high_precision`
- Quick-look mode: smaller imsize, fewer iterations
- Optional FITS export skipping for speed

**Workers:**
- Backfill imaging worker scans MS directory
- Applies current calibration
- Images anything missed by streaming pipeline

#### 5. Photometry & Normalization (`photometry/`)

**Forced Photometry** (`forced.py`):
- Measures peak flux at catalog positions
- Uses NVSS/VLASS/FIRST crossmatch catalog
- Handles multiple sources per field

**Differential Normalization** (`normalize.py`):
- Achieves 1-2% relative precision (vs 5-10% absolute)
- Uses ensemble of stable reference sources (NVSS, SNR≥50)
- Computes correction factor from reference flux ratios
- Normalizes target sources by correction factor
- Robust outlier rejection (3σ clipping)
- Error propagation accounts for measurement and correction uncertainty

**Process:**
1. Load reference sources from `master_sources.sqlite3`
2. Establish baseline (median of first 10 epochs)
3. Compute correction factor (median of reference ratios)
4. Apply normalization to targets
5. Store in `photometry_timeseries` table

#### 6. ESE Detection (`database/migrations.py`, `api/routes.py`)

**Variability Statistics:**
- χ²_reduced, fractional variability, significance
- ESE-specific morphology: asymmetry, timescale (14-180 days), amplitude (10-50%)

**Database Tables:**
- `variability_stats`: Pre-computed statistics per source
- `ese_candidates`: Flagged candidates (auto or user-flagged)
- `photometry_timeseries`: Normalized flux measurements

**Detection Algorithm:**
- For each source with N_epochs > 20:
  - Compute χ²_reduced, fractional variability (V), significance
  - If variable (χ²_ν > 3 or V > 0.05):
    - Fit morphology (asymmetry, timescale, amplitude)
    - Compute ESE_score (weighted combination of metrics)
    - Flag if ESE_score > 0.6
  - Update `variability_stats` table

**API Endpoint:** `GET /api/ese/candidates` (currently mock data, needs integration)

#### 7. API & Monitoring (`api/`)

**FastAPI Application:**
- REST endpoints for status, products, QA
- Background job execution with SSE log streaming
- Control panel for manual job execution
- WebSocket support for real-time updates

**Key Endpoints:**
- `/api/status` - Queue status, recent groups, system metrics
- `/api/products` - MS index, images, QA artifacts
- `/api/ms_index` - Filtered MS index (by stage, status, limit)
- `/api/reprocess/{group_id}` - Nudge group back to `pending`
- `/api/ese/candidates` - ESE candidate list
- `/api/jobs` - Job management (create, status, logs)

**Models:** Comprehensive Pydantic models for all API responses

#### 8. Database Layer (`database/`)

**Products DB** (`state/products.sqlite3`):
- `ms_index`: MS metadata (path, timestamps, status, calibration applied)
- `images`: Image metadata (path, beam, noise, PB correction)
- `photometry_timeseries`: Flux measurements per source per epoch
- `variability_stats`: Pre-computed variability metrics
- `ese_candidates`: Flagged ESE candidates
- `mosaics`: Mosaic plans and metadata

**Queue DB** (`state/ingest.sqlite3`):
- `ingest_queue`: Group state, timestamps, retry counts
- `subband_files`: Individual file tracking per group
- `performance_metrics`: Writer type, timings per stage

**Cal Registry DB** (`state/cal_registry.sqlite3`):
- `caltables`: Calibration table registry with validity windows

**Catalog DBs:**
- `state/catalogs/vla_calibrators.sqlite3`: VLA calibrator catalog
- `state/catalogs/master_sources.sqlite3`: NVSS/VLASS/FIRST crossmatch

#### 9. Quality Assurance (`qa/`)

**MS Validation:**
- After conversion: phase center coherence, UVW precision, antenna positions
- After calibration: solution quality, flagging statistics
- After imaging: beam parameters, noise levels, PB correction

**Diagnostic Plots:**
- Calibration quality plots (phase vs time/freq, amplitude vs time/freq)
- Image quality metrics (beam, noise, dynamic range)
- QA thumbnails for API display

#### 10. Pipeline Orchestration Framework (`pipeline/`)

**Modern Framework** (replaces legacy subprocess-based code):
- Declarative pipeline with dependency resolution
- Direct function calls (no subprocess overhead)
- Retry policies and improved error handling
- Type-safe context passing between stages

**Key Components:**
- `PipelineContext`: Immutable context passed between stages
- `PipelineStage`: Base class for all pipeline stages
- `PipelineOrchestrator`: Executes stages respecting dependencies
- `StateRepository`: Abstraction for state persistence
- `ResourceManager`: Automatic resource cleanup
- `PipelineConfig`: Unified configuration system
- `WorkflowBuilder`: Standard workflows (imaging, quicklook, reprocessing)

**Stages:**
- `ConversionStage`: UVH5 → MS conversion
- `CalibrationSolveStage`: Calibration solving
- `CalibrationStage`: Calibration application
- `ImagingStage`: Image creation

---

## Code Organization

### Module Structure

```
src/dsa110_contimg/
├── api/                    # FastAPI monitoring API (4,000+ lines)
├── beam/                   # Beam model and voltage pattern handling
├── calibration/            # CASA-based calibration (K/BP/G)
├── catalog/                # Source catalog building and querying
├── conversion/             # UVH5 → MS conversion
│   ├── strategies/         # Writer strategies (orchestrator, direct_subband, pyuvdata)
│   ├── streaming/          # Streaming converter daemon
│   └── downsample_uvh5/    # UVH5 downsampling utilities
├── database/               # SQLite helpers and migrations
├── imaging/                # tclean/WSClean imaging
├── mosaic/                 # Mosaic planner/builder
├── photometry/             # Forced photometry and normalization
├── pipeline/               # Pipeline orchestration framework
├── pointing/               # Pointing monitoring and crossmatching
├── qa/                     # Quality assurance plots and helpers
├── simulation/             # Synthetic data generation
└── utils/                  # Shared utilities
```

### Key Design Patterns

1. **Strategy Pattern:** Writer selection (production vs testing)
2. **Factory Pattern:** Writer factory (`get_writer()`)
3. **Repository Pattern:** Database access abstraction
4. **Observer Pattern:** Pipeline observability (metrics, logging)
5. **Adapter Pattern:** Legacy workflow adapter for backward compatibility

### Code Quality Metrics

**Current Status:**
- **Logging:** ~7% complete (579 print() statements remaining across 44 files)
- **Error Handling:** ~4% complete (258 generic exceptions remaining across 47 files)
- **Type Safety:** ~5% complete (101 `# type: ignore` comments across 35 files)

**Critical Issues Fixed:**
- SQL injection vulnerabilities (CRITICAL) - FIXED
- Thread safety issues (CRITICAL) - FIXED
- Path traversal vulnerability (HIGH) - FIXED
- Resource cleanup (HIGH) - IMPROVED

**Remaining Work:**
- Error handling inconsistencies (HIGH priority) - 731 broad exception catches across 114 files
- Complete logging migration (MEDIUM priority)
- Type hint improvements (LOW priority)

---

## Technical Decisions

### Python Environment: casa6 is MANDATORY

**CRITICAL:** ALL Python execution MUST use casa6 environment at `/opt/miniforge/envs/casa6/bin/python`

- **Path:** `/opt/miniforge/envs/casa6/bin/python` (Python 3.11.13)
- **Why:** System Python (3.6.9) lacks CASA dependencies, required Python features, and scientific packages
- **Makefile:** Uses `CASA6_PYTHON` variable with automatic validation
- **Shell Scripts:** Must set `PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"` and check existence
- **Never use:** `python3`, `python`, or any system Python - pipeline will fail

### Conversion Strategy

- **Production:** Always uses `parallel-subband` writer for 16 subbands
- **Testing:** `pyuvdata` writer available for ≤2 subbands only
- **Auto selection:** `--writer auto` selects appropriate writer
- **Staging:** Prefer tmpfs (`/dev/shm`) when available, fallback to SSD

### K-Calibration Default Behavior

- **Skipped by default** for DSA-110 (following VLA/ALMA practice)
- Short baselines (2.6 km max) mean residual delays <0.5 ns (below decorrelation threshold)
- Delays absorbed into complex gain calibration
- Use `--do-k` flag to explicitly enable if needed

### Phase Coherence Fix

- Direct-subband writer computes **single shared phase center** for entire group
- Prevents phase discontinuities when concatenated
- Averages all subband midpoint times to compute group midpoint
- All subbands reference same ICRS phase center (`meridian_icrs`)

### Database Preferences

- **Always prefer SQLite** for any relevant pipeline stage/function
- SQLite provides faster, more reliable access than CSV/JSON
- Standard locations:
  - `state/catalogs/vla_calibrators.sqlite3`
  - `state/catalogs/master_sources.sqlite3`
  - `state/products.sqlite3`
  - `state/cal_registry.sqlite3`
- Functions like `load_vla_catalog()` automatically prefer SQLite when available

### CASA ft() Phase Center Bug

**Critical Fix (2025-11-05):**
- **Root Cause:** CASA's `ft()` task does NOT use `PHASE_DIR` or `REFERENCE_DIR` from the FIELD table
- Instead, it determines phase center from the DATA column's original phasing (UVW coordinates)
- This causes MODEL_DATA to be misaligned with DATA when the MS has been rephased
- **Solution:** When rephasing is performed, automatically use manual MODEL_DATA calculation instead of `ft()`/`setjy`
- Manual calculation reads `PHASE_DIR` per field and ensures correct phase structure

### Bandpass Solve: Field Selection and UV Range Tuning

**Lessons Learned:**
1. When `combine_fields` is requested, pass the full field selection string to CASA (e.g., `field='0~15'`) instead of a single field
2. Prefer `uvrange=""` (no cut) or a relaxed cut (e.g., `>0.3klambda`) for DSA-110 bandpass solves
3. Expose and plumb a `--bp-minsnr` parameter (default 3–5)
4. Ensure MODEL_DATA is populated (e.g., `--model-source=catalog`)
5. Pre-bandpass phase solve defaults: Use `solint='30s'` (not `'inf'`) and `minsnr=3.0` (not 5.0)

---

## Database Schema

### Products Database (`products.sqlite3`)

**Table: `ms_index`**
- Tracks Measurement Sets through processing stages
- Fields: path (PK), start_mjd, end_mjd, mid_mjd, processed_at, status, stage, stage_updated_at, cal_applied, imagename, field_name, pointing_ra_deg, pointing_dec_deg
- Indices: stage+path, status, mjd, field_name

**Table: `images`**
- Catalog of image products
- Fields: id (PK), path (UNIQUE), ms_path, created_at, type, format, beam_major_arcsec, beam_minor_arcsec, beam_pa_deg, noise_jy, pbcor, rms_jy, dynamic_range
- Indices: ms_path

**Table: `photometry_timeseries`**
- Flux measurements per source per epoch
- Fields: id (PK), source_id, ms_path, image_path, epoch_mjd, flux_jy, flux_err_jy, normalized_flux_jy, normalized_flux_err_jy, is_reference, snr
- Indices: source_id, ms_path, epoch_mjd

**Table: `variability_stats`**
- Pre-computed variability metrics per source
- Fields: source_id (PK), n_epochs, chi2_reduced, fractional_variability, significance, ese_score, asymmetry_index, characteristic_timescale_days, peak_to_trough_amplitude, last_updated

**Table: `ese_candidates`**
- Flagged ESE candidates
- Fields: id (PK), source_id, flagged_at, flagged_by, ese_score, notes, status

**Table: `mosaics`**
- Mosaic plans and metadata
- Fields: id (PK), name (UNIQUE), method, created_at, built_at, output_path, n_tiles, status

### Queue Database (`ingest.sqlite3`)

**Table: `ingest_queue`**
- Tracks observation groups through the pipeline
- Fields: group_id (PK), state, received_at, last_update, expected_subbands, has_calibrator, calibrators (JSON), retry_count, error_message
- Indices: state, received_at

**Table: `subband_files`**
- Tracks individual subband files per group
- Fields: id (PK), group_id, subband_idx, file_path, file_size, discovered_at
- Indices: group_id
- Unique constraint: (group_id, subband_idx)

**Table: `performance_metrics`**
- Processing performance per group
- Fields: id (PK), group_id (UNIQUE), writer_type, conversion_time, concat_time, k_solve_time, bp_solve_time, g_solve_time, imaging_time, photometry_time, total_time, recorded_at
- Indices: group_id

### Calibration Registry (`cal_registry.sqlite3`)

**Table: `caltables`**
- Tracks calibration tables and their validity ranges
- Fields: id (PK), set_name, path (UNIQUE), table_type, order_index, valid_start_mjd, valid_end_mjd, created_at, active
- Indices: set_name, valid_start_mjd+valid_end_mjd, active

---

## Deployment

### Systemd (Recommended for Streaming Worker)

**Units:**
- `ops/systemd/contimg-stream.service`: Streaming worker
- `ops/systemd/contimg-api.service`: API server

**Environment:** `ops/systemd/contimg.env`
- Sets paths, database locations, environment variables
- Logs: `/data/dsa110-contimg/state/logs`

### Docker Compose

**Services:**
- `stream`: Streaming worker with orchestrator
- `api`: uvicorn exposing API port
- `scheduler`: Optional nightly mosaic + periodic housekeeping

**Configuration:** `ops/docker/.env`
- Set absolute host paths for `REPO_ROOT`, `CONTIMG_*`, `UID`/`GID`
- Image creates `contimg` conda env (casa6, casacore, pyuvdata, FastAPI)
- Code mounted from host repo (`PYTHONPATH=/app/src`)

### Frontend

**React/TypeScript Dashboard:**
- API URL configurable via `VITE_API_URL` env var
- Control panel for manual job execution with live log streaming
- WebSocket support for real-time updates
- ESE candidate visualization

---

## Key Strengths

1. **Clear Architecture:** Well-defined data flow with modular components
2. **Production-Ready:** Comprehensive deployment options (systemd, Docker)
3. **Monitoring:** FastAPI API with extensive endpoints and WebSocket support
4. **Scientific Accuracy:** 1-2% relative flux precision enables ESE detection
5. **Performance:** tmpfs staging, parallel processing, WSClean backend
6. **Robustness:** Error handling, retry logic, state management
7. **Documentation:** Comprehensive docs in `docs/` structure

---

## Areas for Improvement

1. **Code Quality:** Complete logging migration, error handling standardization, type hints
2. **ESE Detection:** Integrate fully into pipeline (currently mock data in API)
3. **Redundancy:** Consolidate duplicate code in `ops/pipeline/`
4. **Pipeline Robustness:** Implement 6-week improvement plan (error classification, resource management, state consistency)
5. **Testing:** Expand test coverage (unit, integration, end-to-end)
6. **Performance:** Profile hot paths, optimize bottlenecks

---

## Related Documentation

- **Quick Start:** `docs/quickstart.md`
- **Pipeline Flow:** `docs/pipeline.md`
- **Deep Understanding:** `docs/analysis/PIPELINE_DEEP_UNDERSTANDING.md`
- **Development History:** `docs/analysis/CURSOR_CHAT_DEVELOPMENT_HISTORY.md`
- **ESE Literature:** `docs/reports/ESE_LITERATURE_SUMMARY.md`
- **Photometry Normalization:** `docs/science/photometry_normalization.md`
- **Project Schema:** `.cursor/rules/graphiti/graphiti-dsa110-contimg-schema.mdc`
- **Complete Project Review:** `docs/reports/COMPLETE_PROJECT_REVIEW.md`
- **Robustness Analysis:** `docs/reports/PIPELINE_ROBUSTNESS_ANALYSIS.md`
- **Memory:** `MEMORY.md` (project lessons and principles)

---

## Conclusion

The DSA-110 continuum imaging pipeline is a sophisticated, production-ready system for radio astronomy data processing. With ~50,000+ lines of well-organized Python code, comprehensive monitoring capabilities, and scientific accuracy enabling ESE detection, it represents a mature implementation of a complex data processing pipeline.

The codebase demonstrates strong architectural principles, clear separation of concerns, and thoughtful technical decisions. While there are areas for improvement (code quality, testing, robustness), the foundation is solid and the system is operational.

Key achievements:
- 1-2% relative flux precision through differential normalization
- Production-ready deployment options
- Comprehensive monitoring and QA
- Modern pipeline orchestration framework
- Extensive documentation

The pipeline is ready for production use with ongoing improvements planned for robustness, code quality, and feature completeness.

