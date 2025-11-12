# DSA-110 Continuum Imaging Pipeline - Deep Study Summary

**Date:** 2025-11-12  
**Purpose:** Comprehensive analysis of the dsa110-contimg codebase architecture, implementation patterns, and technical decisions

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

## Key Technical Decisions

### Python Environment: casa6 is MANDATORY

**CRITICAL: ALL Python execution MUST use casa6 environment at `/opt/miniforge/envs/casa6/bin/python`**

- **Path:** `/opt/miniforge/envs/casa6/bin/python` (Python 3.11.13)
- **Why:** System Python (3.6.9) lacks CASA dependencies, required Python features, and scientific packages
- **Makefile:** Uses `CASA6_PYTHON` variable with automatic validation
- **Shell Scripts:** Must set `PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"` and check existence
- **Never use:** `python3`, `python`, or any system Python - pipeline will fail
- **Documentation:** See `docs/reference/CRITICAL_PYTHON_ENVIRONMENT.md` for complete guidelines

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

### CASA ft() Phase Center Bug Fix
- **Root Cause:** CASA's `ft()` task does NOT use `PHASE_DIR` or `REFERENCE_DIR` from the FIELD table
- **Solution:** When rephasing is performed, automatically use manual MODEL_DATA calculation instead of `ft()`/`setjy`
- **Implementation:**
  - `--model-source catalog`: Already uses manual calculation when rephasing is done ✓
  - `--model-source setjy`: Now detects if MS was rephased and uses manual calculation if calibrator coordinates are available
  - `--model-source component/image`: Still uses `ft()` (no easy conversion); warnings added
- **Best Practice:** When rephasing MS, use `--model-source catalog` with calibrator coordinates, or provide coordinates when using `--model-source setjy`

---

## Database Schema

### Products Database (`state/products.sqlite3`)

**`ms_index` Table:**
```sql
CREATE TABLE ms_index (
    path TEXT PRIMARY KEY,
    start_mjd REAL,
    end_mjd REAL,
    mid_mjd REAL,
    processed_at REAL,
    status TEXT,
    stage TEXT,
    stage_updated_at REAL,
    cal_applied INTEGER DEFAULT 0,
    imagename TEXT
)
```

**`images` Table:**
```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    ms_path TEXT NOT NULL,
    created_at REAL NOT NULL,
    type TEXT NOT NULL,
    beam_major_arcsec REAL,
    noise_jy REAL,
    pbcor INTEGER DEFAULT 0
)
```

**`photometry_timeseries` Table:**
```sql
CREATE TABLE photometry_timeseries (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,
    image_path TEXT NOT NULL,
    flux_jy REAL NOT NULL,
    flux_err_jy REAL,
    normalized_flux_jy REAL,
    normalized_flux_err_jy REAL,
    measured_at REAL NOT NULL
)
```

**`variability_stats` Table:**
```sql
CREATE TABLE variability_stats (
    source_id TEXT PRIMARY KEY,
    n_epochs INTEGER,
    chi2_reduced REAL,
    fractional_variability REAL,
    significance REAL,
    ese_score REAL,
    last_updated REAL
)
```

**`ese_candidates` Table:**
```sql
CREATE TABLE ese_candidates (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,
    first_detection_at REAL,
    last_detection_at REAL,
    max_sigma_dev REAL,
    status TEXT,
    notes TEXT
)
```

### Queue Database (`state/ingest.sqlite3`)

**`ingest_queue` Table:**
```sql
CREATE TABLE ingest_queue (
    group_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    received_at REAL NOT NULL,
    last_update REAL NOT NULL,
    expected_subbands INTEGER DEFAULT 16,
    has_calibrator INTEGER,
    calibrators TEXT,
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
)
```

**`subband_files` Table:**
```sql
CREATE TABLE subband_files (
    group_id TEXT NOT NULL,
    subband_idx INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    discovered_at REAL NOT NULL,
    FOREIGN KEY (group_id) REFERENCES ingest_queue(group_id),
    UNIQUE(group_id, subband_idx)
)
```

**`performance_metrics` Table:**
```sql
CREATE TABLE performance_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL UNIQUE,
    writer_type TEXT,
    conversion_time REAL,
    concat_time REAL,
    k_solve_time REAL,
    bp_solve_time REAL,
    g_solve_time REAL,
    imaging_time REAL,
    photometry_time REAL,
    total_time REAL,
    recorded_at REAL NOT NULL,
    FOREIGN KEY (group_id) REFERENCES ingest_queue(group_id)
)
```

### Calibration Registry (`state/cal_registry.sqlite3`)

**`caltables` Table:**
```sql
CREATE TABLE caltables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    set_name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    table_type TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    valid_start_mjd REAL NOT NULL,
    valid_end_mjd REAL NOT NULL,
    created_at REAL NOT NULL,
    active INTEGER DEFAULT 1
)
```

---

## Deployment Options

### Systemd (Recommended for Streaming Worker)
- Units: `ops/systemd/contimg-stream.service`, `contimg-api.service`
- Environment: `ops/systemd/contimg.env`
- Logs: `/data/dsa110-contimg/state/logs`

### Docker Compose
- Services: `stream`, `api`, `scheduler` (optional)
- Configuration: `ops/docker/.env`
- Image: Creates `contimg` conda env (casa6, casacore, pyuvdata, FastAPI)

### Frontend
- React/TypeScript dashboard
- API URL configurable via `VITE_API_URL` env var
- Control panel for manual job execution with live log streaming

---

## Code Quality Status

**Current Status:**
- **Logging:** ~7% complete (579 print() statements remaining across 44 files)
- **Error Handling:** ~4% complete (258 generic exceptions remaining across 47 files)
- **Type Safety:** ~5% complete (101 `# type: ignore` comments across 35 files)

**Critical Issues Fixed:**
- SQL injection vulnerabilities (CRITICAL) - FIXED
- Thread safety issues (CRITICAL) - FIXED
- Path traversal vulnerability (HIGH) - FIXED
- Resource cleanup (HIGH) - IMPROVED

**Remaining High Priority:**
- Error handling inconsistencies (731 broad exception catches across 114 files)
- CASA file handle leaks (MEDIUM - mitigation exists)

---

## Key Design Patterns

1. **Strategy Pattern:** Writer selection (production vs testing)
2. **Factory Pattern:** Writer factory (`get_writer()`)
3. **Repository Pattern:** Database access abstraction
4. **Observer Pattern:** Pipeline observability (metrics, logging)
5. **Adapter Pattern:** Legacy workflow adapter for backward compatibility

---

## Directory Architecture

### Code Location
- **Code:** `/data/dsa110-contimg/`
- **Data:** `/stage/dsa110-contimg/` or `/stage/dsa110-contimg/`
- **State DBs:** `/data/dsa110-contimg/state/`

### Data Organization
- **Incoming:** `/stage/dsa110-contimg/incoming/` (raw UVH5 files)
- **MS Files:** `/stage/dsa110-contimg/ms/` (organized by date and type)
  - `calibrators/YYYY-MM-DD/` - Calibrator MS and calibration tables
  - `science/YYYY-MM-DD/` - Science MS files
  - `failed/YYYY-MM-DD/` - Failed conversions
- **Images:** `/stage/dsa110-contimg/images/`
- **Mosaics:** `/stage/dsa110-contimg/mosaics/`

### Staging
- **tmpfs:** `/dev/shm/dsa110-contimg/` (3-5x speedup for conversion)
- **Scratch:** `/stage/dsa110-contimg/tmp/` (fallback if tmpfs unavailable)

---

## Key Lessons Learned

### MODEL_DATA: Column Structure vs. Sky Model Content
- `configure_ms_for_imaging()` only creates the **column structure** for `MODEL_DATA` (zeros)
- This is **not** the same as populating it with an actual sky model
- Calibration requires `MODEL_DATA` to contain **actual visibility predictions** from a sky model
- Pipeline order: Conversion → MODEL_DATA Population → Calibration → Apply → Imaging

### CASA Calibration Tables Are Directories
- CASA calibration tables (`.bpcal`, `.gpcal`, `.kcal`, etc.) are **directories**, not files
- Validation functions must check for directories, not files
- This affects `validate_caltable_exists()`, `validate_caltables_for_use()`, and any code that validates caltable paths

### Bandpass Solve: Field Selection and UV Range Tuning
- When `combine_fields` is requested, pass the full field selection string to CASA (e.g., `field='0~15'`)
- Prefer `uvrange=""` (no cut) or a relaxed cut (e.g., `>0.3klambda`) for DSA-110 bandpass solves
- Pre-bandpass phase solve defaults: Use `solint='30s'` (not `'inf'`) and `minsnr=3.0` (not 5.0)

### Phase Angle Handling
- When converting phases from radians to degrees, wrap to [-180, 180) to avoid artificial scatter
- Use `dsa110_contimg.utils.angles.wrap_phase_deg()` for consistent wrapping

---

## Related Documentation

- **Quick Start:** `docs/quickstart.md`
- **Pipeline Flow:** `docs/pipeline.md`
- **Deep Understanding:** `docs/analysis/PIPELINE_DEEP_UNDERSTANDING.md`
- **Development History:** `docs/analysis/CURSOR_CHAT_DEVELOPMENT_HISTORY.md`
- **ESE Literature Summary:** `docs/reports/ESE_LITERATURE_SUMMARY.md`
- **Photometry Normalization:** `docs/science/photometry_normalization.md`
- **Complete Project Review:** `docs/reports/COMPLETE_PROJECT_REVIEW.md`
- **Robustness Analysis:** `docs/reports/PIPELINE_ROBUSTNESS_ANALYSIS.md`

---

## Summary

The DSA-110 continuum imaging pipeline is a sophisticated, production-ready system for processing radio astronomy data. It demonstrates:

- **Clear architecture** with well-defined data flow
- **Production-ready deployment** options (systemd, Docker)
- **Comprehensive monitoring** and QA
- **Scientific accuracy** (1-2% relative flux precision)
- **Modern pipeline orchestration** framework
- **Extensive documentation** structure

**Areas for Improvement:**
- Complete code quality improvements (logging, error handling, type safety)
- Integrate ESE detection fully into pipeline (currently mock data in API)
- Consolidate redundant code in ops/pipeline/
- Complete pipeline robustness improvements (6-week plan)
- Expand test coverage (unit, integration, end-to-end)
