# DSA-110 Continuum Imaging Pipeline - Deep Understanding

**Generated:** 2025-01-XX  
**Purpose:** Comprehensive understanding of pipeline architecture, data flow, and key components

---

## Executive Summary

The DSA-110 continuum imaging pipeline is a **production-ready radio astronomy data processing system** that converts raw UVH5 visibility data into calibrated, deconvolved continuum images for Extreme Scattering Event (ESE) detection. The pipeline achieves **1-2% relative flux precision** through differential photometry normalization, enabling detection of 10-50% flux variations at 5-10σ significance.

**Core Pipeline Flow:**
```
UVH5 Files → Conversion → Calibration → Imaging → Photometry → ESE Detection
  (16 sb)      (MS)      ({K}/BP/G)      (tclean)    (normalize)   (variability)
```

---

## Architecture Overview

### High-Level Components

1. **Streaming Converter** (`conversion/streaming/streaming_converter.py`)
   - Watches `/data/incoming/` for `*_sb??.hdf5` files
   - Groups by timestamp (5-minute windows, 16 subbands expected)
   - State machine: `collecting` → `pending` → `in_progress` → `completed`
   - Persists queue state in SQLite (`state/ingest.sqlite3`)

2. **Conversion Layer** (`conversion/strategies/`)
   - **Orchestrator** (`hdf5_orchestrator.py`): Primary entry point
   - **Writers**:
     - `direct_subband.py`: Production path - parallel per-subband writes, then CASA concat
     - `pyuvdata_monolithic.py`: Testing only (≤2 subbands)
   - Operations:
     - Sets telescope identity (`DSA_110`)
     - Phases to meridian at midpoint
     - Computes UVW coordinates
     - Initializes imaging columns (`MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM`)

3. **Calibration Layer** (`calibration/`)
   - **K-calibration** (delay): Frequency-independent delays per antenna
     - **Default: SKIPPED** for DSA-110 (short 2.6 km baselines)
   - **BP-calibration** (bandpass): Frequency-dependent gains
   - **G-calibration** (gain): Time-variable atmospheric effects
   - Auto calibrator field selection from VLA catalog
   - Calibration table registry (`state/cal_registry.sqlite3`) tracks validity windows

4. **Imaging Layer** (`imaging/`)
   - CASA `tclean` or WSClean (WSClean default, 2-5x faster)
   - NVSS sky model seeding (≥10 mJy sources)
   - Primary beam correction
   - Quality tiers: `development`, `standard`, `high_precision`

5. **Photometry & Normalization** (`photometry/`)
   - **Forced photometry** (`forced.py`): Measure peak flux at catalog positions
   - **Differential normalization** (`normalize.py`): Achieves 1-2% relative precision
     - Uses ensemble of stable reference sources (NVSS, SNR≥50)
     - Computes correction factor from reference flux ratios
     - Normalizes target sources by correction factor
     - Robust outlier rejection (3σ clipping)

6. **ESE Detection** (`database/migrations.py`, `api/routes.py`)
   - Variability statistics: χ²_reduced, fractional variability, significance
   - ESE-specific morphology: asymmetry, timescale (14-180 days), amplitude (10-50%)
   - Database tables: `variability_stats`, `ese_candidates`, `photometry_timeseries`

7. **API & Monitoring** (`api/`)
   - FastAPI REST endpoints
   - Background job execution with SSE log streaming
   - Control panel for manual job execution
   - Status, products, QA views

8. **Database Layer** (`database/`)
   - **Products DB** (`state/products.sqlite3`): MS metadata, images, photometry
   - **Queue DB** (`state/ingest.sqlite3`): Group state, file arrivals, performance metrics
   - **Cal Registry DB** (`state/cal_registry.sqlite3`): Calibration table registry

---

## Data Flow Through Pipeline

### Stage 1: File Ingestion & Grouping

**Input:** `*_sb??.hdf5` files in `/data/incoming/`

**Process:**
1. Streaming converter watches directory (using `watchdog` if available)
2. Files parsed by timestamp pattern: `YYYY-MM-DDTHH:MM:SS_sbNN.hdf5`
3. Groups created by timestamp (5-minute windows)
4. Complete groups (16 subbands) transition: `collecting` → `pending`
5. State persisted in `ingest_queue` table

**Key Files:**
- `conversion/streaming/streaming_converter.py`: Queue management, file watching
- `conversion/strategies/hdf5_orchestrator.py`: Group discovery logic

### Stage 2: UVH5 → Measurement Set Conversion

**Input:** Complete subband group (16 UVH5 files)

**Process:**
1. **Orchestrator** (`hdf5_orchestrator.py`) discovers groups
2. **Writer selection**:
   - Production: `direct_subband` (parallel per-subband writes)
   - Testing: `pyuvdata_monolithic` (≤2 subbands only)
3. **Per-subband conversion**:
   - Read UVH5 via `pyuvdata`
   - Set telescope identity (`DSA_110`)
   - Phase to meridian (RA=LST(t), Dec from UVH5)
   - Compute UVW coordinates
   - Write to temporary MS per subband
4. **Concatenation**: CASA `concat` merges subbands into single MS
5. **Finalization**:
   - Initialize imaging columns (`MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM`)
   - Set antenna positions and diameters
   - Validate phase center coherence
   - Update `ms_index` in products DB

**Key Files:**
- `conversion/strategies/hdf5_orchestrator.py`: Orchestration logic
- `conversion/strategies/direct_subband.py`: Production writer
- `conversion/helpers.py`: Phasing, antenna setup, UVW computation
- `conversion/ms_utils.py`: MS configuration for imaging

**Output:** Single Measurement Set (MS) directory

### Stage 3: Calibration

**Input:** Measurement Set

**Process:**

#### 3.1 Pre-Calibration Flagging
- Reset flags
- Flag zero-value data (correlator failures)
- Optional RFI flagging (`tfcrop` + `rflag`)

#### 3.2 Model Data Population
- **Default source**: `--model-source catalog` (VLA calibrator catalog)
- **Method**: pyradiosky (default) or componentlist
- **Process**:
  1. Auto-select calibrator field (if `--auto-fields`)
  2. Rephase MS to calibrator position (unless `--skip-rephase`)
  3. Create sky model from catalog
  4. Populate `MODEL_DATA` via CASA `ft()`
- **Critical**: `MODEL_DATA` must contain actual visibility predictions, not just zeros

#### 3.3 Calibration Solving

**K-Calibration (Delay)** - **SKIPPED BY DEFAULT**
- Frequency-independent delays per antenna
- Skipped for DSA-110 (short baselines, delays <0.5 ns absorbed into gains)
- Use `--do-k` to explicitly enable

**BP-Calibration (Bandpass)**
- Frequency-dependent gains
- Default: `combine_fields=False` (single peak field)
- Default: `uvrange='>1klambda'` (may be too aggressive)
- Default: `minsnr=3.0`
- **Critical**: When `combine_fields=True`, pass full field range (e.g., `'0~15'`)

**Pre-Bandpass Phase** (optional)
- Time-variable phase correction before bandpass
- Default: `solint='30s'` (not `'inf'` to avoid decorrelation)
- Default: `minsnr=3.0`

**G-Calibration (Gain)**
- Time-variable atmospheric effects
- Default: `solint='inf'` (phase-only mode `'p'`)
- Default: `calmode='ap'` (amplitude + phase)

#### 3.4 Calibration Table Registration
- Tables registered in `cal_registry.sqlite3`
- Validity windows tracked (MJD start/end)
- Apply order: K → BA → BP → GA → GP → 2G → FLUX

**Key Files:**
- `calibration/cli_calibrate.py`: Main calibration CLI
- `calibration/calibration.py`: Core solving functions (`solve_bandpass`, `solve_gains`, `solve_delay`)
- `calibration/model.py`: Sky model population (pyradiosky, componentlist)
- `calibration/flagging.py`: Pre-calibration flagging
- `database/registry.py`: Calibration table registry

**Output:** Calibration tables (`.bpcal`, `.gpcal`, etc.) + registry entries

### Stage 4: Calibration Application

**Input:** MS + Calibration tables

**Process:**
1. Query `cal_registry.sqlite3` for active tables valid at MS observation time
2. Apply tables in order via CASA `applycal`
3. Write to `CORRECTED_DATA` column
4. Verify application (check non-zero `CORRECTED_DATA`)

**Key Files:**
- `calibration/apply_service.py`: Calibration application service
- `calibration/applycal.py`: CASA `applycal` wrapper

**Output:** MS with `CORRECTED_DATA` populated

### Stage 5: Imaging

**Input:** Calibrated MS

**Process:**
1. **Detect datacolumn**: Prefer `CORRECTED_DATA`, fallback to `DATA`
2. **NVSS sky model seeding**:
   - Query NVSS catalog for sources ≥10 mJy within FoV
   - Populate `MODEL_DATA` with point sources
   - Used as initial model for deconvolution
3. **Deconvolution**:
   - **Backend**: WSClean (default, 2-5x faster) or CASA `tclean`
   - **Quality tiers**:
     - `development`: 4x coarser cell, max 300 iterations (testing only)
     - `standard`: Full quality (recommended)
     - `high_precision`: 2000+ iterations, 5 mJy NVSS threshold
   - **Parameters**: Briggs weighting (robust=0.0), Hogbom deconvolver, primary beam correction
4. **FITS Export**: Convert CASA images to FITS format
5. **QA Metrics**: Beam size, noise, dynamic range
6. **Database Update**: Insert into `images` table

**Key Files:**
- `imaging/cli_imaging.py`: Main imaging function (`image_ms`)
- `imaging/nvss_tools.py`: NVSS catalog querying and seeding
- `imaging/export.py`: FITS export

**Output:** CASA images (`.image`, `.image.pbcor`, `.residual`, `.psf`, `.pb`) + FITS files

### Stage 6: Photometry & Normalization

**Input:** Primary beam corrected FITS images (`.pbcor.fits`)

**Process:**

#### 6.1 Forced Photometry
- Measure peak flux at catalog positions
- Box photometry with annulus background subtraction
- Store in `photometry_timeseries` table

#### 6.2 Differential Normalization

**Baseline Establishment (Epochs 0-10):**
- For each reference source: `F_baseline = median(F[epochs 0:10])`
- Robust scatter: `σ_baseline = 1.4826 × MAD(F[epochs 0:10])`

**Per-Epoch Correction:**
1. Measure all reference sources
2. Compute ratios: `R[i] = F_current[i] / F_baseline[i]`
3. Reject outliers (3σ clipping)
4. Compute ensemble correction: `C = median(R[valid])`
5. Normalize targets: `F_norm = F_raw / C`

**Error Propagation:**
```
σ_norm² = (σ_raw / C)² + (F_raw × σ_C / C²)²
```

**Reference Source Selection:**
- NVSS SNR ≥ 50
- Spectral index: -1.2 < α < 0.2 (flat spectrum)
- Unresolved morphology
- Distributed across FoV
- 10-20 sources optimal

**Key Files:**
- `photometry/forced.py`: Forced photometry measurement
- `photometry/normalize.py`: Differential normalization algorithm

**Output:** Normalized flux measurements in `photometry_timeseries` table

### Stage 7: ESE Detection

**Input:** Normalized photometry timeseries

**Process:**
1. **Variability Analysis** (for sources with N_epochs > 20):
   - Compute χ²_reduced, fractional variability (V), significance
   - Flag as variable if χ²_ν > 3 or V > 0.05
2. **ESE-Specific Morphology**:
   - Asymmetry index (sharp rise/slow fall or vice versa)
   - Characteristic timescale: 14 days < τ_char < 180 days
   - Peak-to-trough amplitude: 0.2 < amplitude < 2.0
3. **ESE Score**: Weighted combination of metrics
4. **Flagging**: Auto-flag if ESE_score > 0.6

**Key Files:**
- `database/migrations.py`: Variability statistics computation
- `api/routes.py`: ESE candidates endpoint (`/api/ese/candidates`)

**Output:** ESE candidates in `ese_candidates` table

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
    source_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_jy REAL NOT NULL,
    flux_err_jy REAL,
    normalized_flux_jy REAL,
    normalized_flux_err_jy REAL,
    epoch_mjd REAL NOT NULL,
    is_baseline INTEGER DEFAULT 0
)
```

**`variability_stats` Table:**
```sql
CREATE TABLE variability_stats (
    source_id INTEGER PRIMARY KEY,
    n_epochs INTEGER NOT NULL,
    chi2_reduced REAL,
    fractional_variability REAL,
    significance REAL,
    ese_score REAL,
    updated_at REAL NOT NULL
)
```

**`ese_candidates` Table:**
```sql
CREATE TABLE ese_candidates (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL,
    ese_score REAL NOT NULL,
    flagged_at REAL NOT NULL,
    flagged_by TEXT,
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
    expected_subbands INTEGER,
    retry_count INTEGER NOT NULL DEFAULT 0,
    error TEXT,
    checkpoint_path TEXT,
    processing_stage TEXT DEFAULT 'collecting',
    chunk_minutes REAL
)
```

**`subband_files` Table:**
```sql
CREATE TABLE subband_files (
    group_id TEXT NOT NULL,
    subband_idx INTEGER NOT NULL,
    path TEXT NOT NULL,
    PRIMARY KEY (group_id, subband_idx)
)
```

**`performance_metrics` Table:**
```sql
CREATE TABLE performance_metrics (
    group_id TEXT NOT NULL,
    load_time REAL,
    phase_time REAL,
    write_time REAL,
    total_time REAL,
    writer_type TEXT,
    recorded_at REAL NOT NULL,
    PRIMARY KEY (group_id)
)
```

### Calibration Registry (`state/cal_registry.sqlite3`)

**`caltables` Table:**
```sql
CREATE TABLE caltables (
    id INTEGER PRIMARY KEY,
    set_name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    table_type TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    cal_field TEXT,
    refant TEXT,
    created_at REAL NOT NULL,
    valid_start_mjd REAL,
    valid_end_mjd REAL,
    status TEXT NOT NULL,
    notes TEXT
)
```

---

## Pipeline Framework

### New Pipeline Framework (`pipeline/`)

The pipeline includes a **declarative orchestration framework** for dependency-based stage execution:

**Key Components:**
- `PipelineOrchestrator`: Executes stages respecting dependencies
- `PipelineContext`: Immutable context passed between stages
- `PipelineStage`: Base class for all stages
- `StageDefinition`: Stage metadata (dependencies, retry policies)

**Stage Implementations:**
- `ConversionStage`: UVH5 → MS conversion
- `CalibrationSolveStage`: Calibration solving
- `CalibrationStage`: Calibration application
- `ImagingStage`: MS → Images

**Benefits:**
- Automatic dependency resolution (topological sort)
- Built-in retry policies
- Structured error handling
- Direct function calls (no subprocess overhead)
- Type-safe context passing

**Usage:**
- The new pipeline framework is now the default and only execution mode
- Legacy subprocess-based code has been archived to `archive/legacy/api/job_runner_legacy.py`

---

## Key Technical Decisions

### Python Environment: casa6 is MANDATORY

**CRITICAL:** ALL Python execution MUST use `/opt/miniforge/envs/casa6/bin/python`

- **Why**: System Python (3.6.9) lacks CASA dependencies, required Python features, scientific packages
- **Makefile**: Uses `CASA6_PYTHON` variable with automatic validation
- **Never use**: `python3`, `python`, or any system Python

### Conversion Strategy

- **Production**: Always uses `direct-subband` writer for 16 subbands
- **Testing**: `pyuvdata` writer available for ≤2 subbands only
- **Staging**: Prefer tmpfs (`/dev/shm`) when available, fallback to SSD

### K-Calibration Default Behavior

- **Skipped by default** for DSA-110 (following VLA/ALMA practice)
- Short baselines (2.6 km max) mean residual delays <0.5 ns
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

### MODEL_DATA: Column Structure vs. Sky Model Content

**Critical Distinction:**
- `configure_ms_for_imaging()` only creates the **column structure** (zeros)
- **Not** the same as populating with actual sky model
- Sky model population requires separate step:
  - `setjy` for standard calibrators
  - `ft()` with component lists (NVSS catalog)
  - `write_point_model_with_ft()` for point source models

**Pipeline Order:**
1. Conversion: Creates MS with `MODEL_DATA` column structure (zeros)
2. MODEL_DATA Population: Populate with sky model ← **Required before calibration**
3. Calibration: Uses populated `MODEL_DATA` to solve for gains/delays/bandpass
4. Apply Calibration: Writes to `CORRECTED_DATA`
5. Imaging: Uses `CORRECTED_DATA` (or `DATA` if uncalibrated)

### CASA Calibration Tables Are Directories

- CASA calibration tables (`.bpcal`, `.gpcal`, etc.) are **directories**, not files
- Validation must check `os.path.isdir()`, not `os.path.isfile()`

---

## API Endpoints

### Status & Monitoring
- `GET /api/status`: Queue stats, recent groups, calibration sets
- `GET /api/products`: Recent products (MS, images)
- `GET /api/ms_index`: Filtered MS index entries
- `GET /api/images`: List images for SkyView
- `GET /api/qa`: QA artifacts

### Job Execution
- `POST /api/jobs`: Create new job (convert, calibrate, image, workflow)
- `GET /api/jobs/{job_id}`: Get job status
- `GET /api/jobs/{job_id}/logs`: Stream job logs (SSE)
- `POST /api/reprocess/{group_id}`: Reprocess a group

### ESE Detection
- `GET /api/ese/candidates`: List ESE candidates
- `GET /api/ese/sources/{source_id}/timeseries`: Source flux timeseries

### Streaming Control
- `GET /api/streaming/status`: Streaming service status
- `POST /api/streaming/control`: Start/stop streaming service

---

## Deployment

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

## Critical Lessons Learned

### Bandpass Solve: Field Selection and UV Range Tuning

- **Problem**: >50% of solutions flagged (low SNR)
- **Root Causes**:
  - Field selection bug: Using single peak field even when `combine_fields=True`
  - Default `uvrange='>1klambda'` too aggressive for DSA-110
  - Pre-bandpass phase defaults suboptimal (`solint='inf'`, `minsnr=5.0`)
- **Solutions**:
  - When `combine_fields=True`, pass full field range (e.g., `'0~15'`)
  - Prefer `uvrange=""` or relaxed cut (`>0.3klambda`) for DSA-110
  - Pre-bandpass phase: `solint='30s'`, `minsnr=3.0`

### CASA ft() Phase Center Bug

- **Root Cause**: CASA's `ft()` task does NOT use `PHASE_DIR` from FIELD table
- **Impact**: MODEL_DATA misaligned with DATA when MS has been rephased
- **Solution**: Use manual MODEL_DATA calculation when rephasing is performed
- **Best Practice**: When rephasing MS, use `--model-source catalog` with calibrator coordinates

### Phase Angle Handling

- When converting phases from radians to degrees, wrap to [-180, 180) to avoid artificial scatter
- Use `dsa110_contimg.utils.angles.wrap_phase_deg()` for consistent wrapping

---

## Related Documentation

- **Quick Start**: `docs/quickstart.md`
- **Pipeline Flow**: `docs/pipeline.md`
- **ESE Literature Summary**: `docs/reports/ESE_LITERATURE_SUMMARY.md`
- **Photometry Normalization**: `docs/science/photometry_normalization.md`
- **Project Knowledge Graph Schema**: `docs/reference/knowledge-graph-schema.md`
- **Control Panel**: `docs/guides/control-panel/`
- **Complete Project Review**: `docs/reports/COMPLETE_PROJECT_REVIEW.md`
- **Test Suite**: `tests/README.md`
- **Robustness Analysis**: `docs/reports/PIPELINE_ROBUSTNESS_ANALYSIS.md`

---

## Summary

The DSA-110 continuum imaging pipeline is a sophisticated, production-ready system that:

1. **Streams** incoming UVH5 subband files and groups them by timestamp
2. **Converts** UVH5 to CASA Measurement Sets with proper phasing and antenna setup
3. **Calibrates** using bandpass and gain solutions (K-calibration optional)
4. **Images** using WSClean or CASA tclean with NVSS sky model seeding
5. **Normalizes** photometry using differential techniques to achieve 1-2% precision
6. **Detects** ESE candidates through variability analysis

The pipeline is designed for **robustness**, **observability**, and **scientific rigor**, with comprehensive error handling, QA metrics, and database tracking throughout.
