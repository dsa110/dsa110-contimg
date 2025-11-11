# DSA-110 Continuum Imaging Pipeline - Codebase Understanding

**Last Updated:** 2025-11-09  
**Purpose:** Record lessons and principles discovered during codebase exploration for future reference

---

## Executive Summary

The DSA-110 continuum imaging pipeline is a **production-ready radio astronomy data processing system** designed to:
1. Convert raw UVH5 subband visibility data into calibrated, deconvolved continuum images
2. Search for **Extreme Scattering Events (ESEs)** - plasma lensing events in the interstellar medium that cause 10-50% flux variations over weeks to months

The pipeline achieves **1-2% relative flux precision** (vs ~5-10% absolute) through differential photometry normalization, enabling detection of ESE flux variations at 5-10σ significance.

---

## Pipeline Architecture

### Core Processing Flow

```
UVH5 Files → Conversion → Calibration → Imaging → Photometry → ESE Detection
  (16 sb)      (MS)      ({K}/BP/G)      (tclean)    (normalize)   (variability)

{} = optional, not default
```

### Key Components

1. **Streaming Converter** (`conversion/streaming/streaming_converter.py`)
   - Watches for incoming `*_sb??.hdf5` files
   - Groups by timestamp (5-minute windows, 16 subbands)
   - State machine: `collecting` → `pending` → `in_progress` → `completed`
   - Persists queue in SQLite (`state/ingest.sqlite3`)

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
   - Performance: tmpfs staging (`/dev/shm`) for 3-5x speedup

3. **Calibration Layer** (`calibration/`)
   - **K-calibration** (delay): Frequency-independent delays per antenna
     - **Default: SKIPPED** for DSA-110 (short 2.6 km baselines, delays <0.5 ns absorbed into gains)
     - Use `--do-k` to explicitly enable if needed
   - **BP-calibration** (bandpass): Frequency-dependent gains; use “G” (polarization/time-dependent) mode.
   - **G-calibration** (gain): Time-variable atmospheric effects; use “p” (phase-only) mode.
   - Fast mode: time/channel binning, phase-only gains, uvrange cuts
   - Auto calibrator field selection from VLA catalog
   - Calibration table registry (`state/cal_registry.sqlite3`) tracks validity windows

4. **Imaging Layer** (`imaging/`)
   - CASA `tclean` with primary beam correction
   - NVSS sky model seeding (≥10 mJy sources)
   - Quick-look mode: smaller imsize, fewer iterations
   - Optional FITS export skipping for speed

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
   - Database tables:
     - `variability_stats`: Pre-computed statistics per source
     - `ese_candidates`: Flagged candidates (auto or user-flagged)
     - `photometry_timeseries`: Normalized flux measurements
   - API endpoint: `GET /api/ese/candidates` (currently mock data)

7. **API & Monitoring** (`api/`)
   - FastAPI REST endpoints
   - Background job execution with SSE log streaming
   - Control panel for manual job execution
   - Status, products, QA views

8. **Database Layer** (`database/`)
   - **Products DB** (`state/products.sqlite3`):
     - `ms_index`: MS metadata (path, timestamps, status, calibration applied)
     - `images`: Image metadata (path, beam, noise, PB correction)
     - `photometry_timeseries`: Flux measurements per source per epoch
     - `variability_stats`: Pre-computed variability metrics
     - `ese_candidates`: Flagged ESE candidates
   - **Queue DB** (`state/ingest.sqlite3`): Group state, file arrivals, performance metrics
   - **Cal Registry DB** (`state/cal_registry.sqlite3`): Calibration table registry

9. **Quality Assurance** (`qa/`)
   - MS validation after conversion
   - Calibration quality assessment
   - Image quality metrics
   - Diagnostic plots and thumbnails

---

## Key Technical Decisions

### Python Environment: casa6 is MANDATORY

**CRITICAL: ALL Python execution MUST use casa6 environment at `/opt/miniforge/envs/casa6/bin/python`**

- **Path**: `/opt/miniforge/envs/casa6/bin/python` (Python 3.11.13)
- **Why**: System Python (3.6.9) lacks CASA dependencies, required Python features, and scientific packages
- **Makefile**: Uses `CASA6_PYTHON` variable with automatic validation
- **Shell Scripts**: Must set `PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"` and check existence
- **Never use**: `python3`, `python`, or any system Python - pipeline will fail
- **Documentation**: See `docs/CRITICAL_PYTHON_ENVIRONMENT.md` for complete guidelines
- **For AI Agents**: Always reference casa6 path explicitly - never assume system Python works

### Conversion Strategy
- **Production**: Always uses `parallel-subband` writer for 16 subbands
- **Testing**: `pyuvdata` writer available for ≤2 subbands only
- **Auto selection**: `--writer auto` selects appropriate writer
- **Staging**: Prefer tmpfs (`/dev/shm`) when available, fallback to SSD

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

### Transit Time Calculation
- **Proper method** for end-to-end testing:
  1. Load calibrator coordinates via `load_vla_catalog()` (SQLite preferred)
  2. Calculate transit times using `previous_transits()` from `dsa110_contimg.calibration.schedule`
  3. Calculate search window (±30-60 minutes around transit)
  4. **CRITICAL**: Verify data exists using `find_subband_groups()` from orchestrator
  5. Use `hdf5_orchestrator` CLI with `--start-time` and `--end-time` flags
- **Never use simplified time-based searches** - this bypasses actual pipeline components

---

## ESE Detection Methodology

### Physical Phenomenon
- **Cause**: Plasma lensing by ionized structures in the interstellar medium
- **Mechanism**: Time-varying magnification/demagnification as Earth moves relative to ISM lens
- **Frequency dependence**: Nearly achromatic (ν^0 to ν^-0.2)

### Observational Signatures
- **Timescales**: Weeks to months (typical: 30-90 days)
- **Morphology**: 
  - Phase 1: Gradual flux decrease (lens approaching)
  - Phase 2: Sharp caustic-crossing peaks (lens in beam)
  - Phase 3: Gradual recovery (lens departing)
- **Amplitude**: 10-50% typical, can reach factors of 2-3
- **Rare**: ~0.5-1 event per source per century

### Detection Algorithm

**Per-Image Processing:**
1. Load FITS image (`.pbcor.fits`)
2. Query reference sources from `master_sources.sqlite3` within FoV
3. Perform forced photometry on N_ref references
4. Check if baselines exist (first 10 epochs):
   - If no: store measurements, flag as baseline establishment
   - If yes: compute correction factor from reference ensemble
5. Perform forced photometry on target sources (all NVSS in FoV)
6. Apply normalization to targets
7. Store in `photometry_timeseries` table

**Variability Analysis:**
- For each source with N_epochs > 20:
  - Compute χ²_reduced, fractional variability (V), significance
  - If variable (χ²_ν > 3 or V > 0.05):
    - Fit morphology (asymmetry, timescale, amplitude)
    - Compute ESE_score (weighted combination of metrics)
    - Flag if ESE_score > 0.6
  - Update `variability_stats` table

### Detection Metrics
- **Reduced χ²**: χ²_ν > 5 flags as variable
- **Fractional Variability**: V > 0.10 flags as significant
- **ESE-Specific**:
  - Asymmetry index (sharp rise/slow fall or vice versa)
  - Characteristic timescale: 14 days < τ_char < 180 days
  - Peak-to-trough amplitude: 0.2 < amplitude < 2.0

### Normalization Algorithm
- **Baseline establishment**: Median of first 10 epochs for each reference source
- **Correction factor**: Median of reference flux ratios (ratio = current/baseline)
- **Outlier rejection**: 3σ clipping on reference ensemble
- **Error propagation**: Accounts for measurement error and correction uncertainty
- **Result**: 1-2% relative precision vs 5-10% absolute precision

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

## Codebase Structure

### Main Directories
- `src/dsa110_contimg/`: Core Python package
  - `conversion/`: UVH5 → MS conversion
  - `calibration/`: CASA-based calibration (K/BP/G)
  - `imaging/`: tclean CLI and worker
  - `photometry/`: Forced photometry and normalization
  - `database/`: SQLite helpers and migrations
  - `api/`: FastAPI application
  - `qa/`: Quality assurance plots and helpers
  - `mosaic/`: Mosaic planner/builder
- `scripts/`: Operational scripts
- `ops/`: Deployment configs (systemd, docker)
- `docs/`: Comprehensive documentation
- `state/`: Default location for databases and artifacts
- `config/`: Pipeline configuration templates

### Key Entry Points
- Streaming: `python -m dsa110_contimg.conversion.streaming.streaming_converter`
- Orchestrator: `python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator`
- Calibration: `python -m dsa110_contimg.calibration.cli`
- Imaging: `python -m dsa110_contimg.imaging.cli`
- API: `uvicorn dsa110_contimg.api.routes:app`

---

## Important Notes for Future Work

1. When extracting or organizing cross-cutting project knowledge, follow the internal schema guidance.

2. **Database migrations**: Run `python -m dsa110_contimg.database.migrations migrate_all` to ensure schema is up-to-date

3. **ESE detection currently uses mock data**: Real implementation needs to:
   - Connect `variability_stats` computation to actual photometry pipeline
   - Implement ESE_score calculation
   - Hook up automatic flagging based on thresholds

4. **Photometry normalization**: Fully implemented but needs integration with imaging pipeline to run automatically after each image is created

5. **Frontend ESE panel**: Currently shows mock candidates; needs backend connection to real `ese_candidates` table

6. **Reference source selection**: Currently manual/CLI-based; could be automated as part of imaging pipeline

---

## Key Design Principles

1. **Modular architecture**: Clear separation between conversion, calibration, imaging, QA
2. **Strategy pattern**: Writer selection based on use case (production vs testing)
3. **SQLite-first**: All persistent state in SQLite databases for fast, reliable access
4. **Performance optimization**: tmpfs staging, fast calibration modes, quick imaging options
5. **Robustness**: Outlier rejection, error propagation, validation at each stage
6. **Observability**: Comprehensive logging, QA plots, API monitoring endpoints

---

## Critical Lessons Learned

### MODEL_DATA: Column Structure vs. Sky Model Content

**Critical Distinction (2025-11-03):**

The `configure_ms_for_imaging()` function (and its helper `_ensure_imaging_columns_populated()`) only creates the **column structure** for `MODEL_DATA` - it initializes the column with zeros to match the shape of the `DATA` column. This is **not** the same as populating it with an actual sky model.

**What `configure_ms_for_imaging()` does:**
- Creates `MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM` columns if missing
- Fills them with zeros to match `DATA` shape/dtype
- Ensures structural integrity for imaging operations

**What calibration requires:**
- `MODEL_DATA` must contain **actual visibility predictions** from a sky model
- This requires a separate step using:
  - `setjy` for standard calibrators (e.g., 0834+555)
  - `ft()` with component lists (NVSS catalog sources)
  - `write_point_model_with_ft()` for point source models
  - `write_setjy_model()` for standard calibrator models

**Pipeline Order:**
1. **Conversion**: Creates MS with `MODEL_DATA` column structure (zeros)
2. **MODEL_DATA Population**: Populate with sky model (NVSS catalog, setjy, etc.) ← **Required before calibration**
3. **Calibration**: Uses populated `MODEL_DATA` to solve for gains/delays/bandpass
4. **Apply Calibration**: Writes to `CORRECTED_DATA`
5. **Imaging**: Uses `CORRECTED_DATA` (or `DATA` if uncalibrated) for deconvolution

**Why this matters:**
- `solve_bandpass()`, `solve_gains()`, and `solve_delay()` all check that `MODEL_DATA` is populated (not all zeros) as a precondition
- Without a sky model in `MODEL_DATA`, calibration cannot determine what signal to calibrate against
- The imaging stage can populate `MODEL_DATA` with NVSS sources, but this happens **after** calibration in the standard pipeline flow

### CASA Calibration Tables Are Directories

**Critical Fix (2025-11-03):**

CASA calibration tables (`.bpcal`, `.gpcal`, `.kcal`, etc.) are **directories**, not files, just like Measurement Sets. This is a fundamental CASA table storage format.

**Validation Bug Fixed:**
- **Before**: `validate_caltable_exists()` checked `os.path.isfile()` - failed for caltables
- **After**: Changed to `os.path.isdir()` - correctly validates CASA table directories

**Impact:**
- All calibration table validation functions must check for directories, not files
- This affects `validate_caltable_exists()`, `validate_caltables_for_use()`, and any code that validates caltable paths
- The fix ensures calibration tables are recognized correctly throughout the pipeline

**Files affected:**
- `src/dsa110_contimg/calibration/validate.py`: `validate_caltable_exists()` function

### Bandpass Solve: Field Selection and UV Range Tuning (2025-11-04)

- Problem observed: During bandpass(), >50% of solutions flagged (low SNR). Root causes in code/config:
  - `solve_bandpass()` and `solve_gains()` reduce `field` to a single "peak" field by taking the last index of a range (e.g., `0~15 -> 15`), which defeats `combine_fields` and reduces SNR.
  - Default `uvrange='>1klambda'` is too aggressive for DSA-110; it removes many short baselines, further lowering SNR.
  - `job_runner` does not pass `--model-source` or `--bp-combine-field`, risking missing MODEL_DATA and reduced SNR even when UI supports these options.
  - **Pre-bandpass phase solve also had field selection bug** - using peak_field even when `combine_fields=True`, reducing SNR for phase correction.
  - **Pre-bandpass phase defaults were suboptimal** - `solint='inf'` causes decorrelation, and `minsnr=5.0` is too strict.

- Lessons/Guidelines:
  1. When `combine_fields` is requested, pass the full field selection string to CASA (e.g., `field='0~15'`) instead of a single field. Only reduce to a single peak field when not combining. **This applies to both bandpass AND pre-bandpass phase solves.**
  2. Prefer `uvrange=""` (no cut) or a relaxed cut (e.g., `>0.3klambda`) for DSA-110 bandpass solves unless the calibrator is strongly resolved on short baselines.
  3. Expose and plumb a `--bp-minsnr` parameter (default 3–5) to trade off solution retention vs robustness; use 3.0 for marginal SNR cases.
  4. Ensure MODEL_DATA is populated (e.g., `--model-source=catalog`) and consider rephasing to the calibrator before `ft()` to maximize SNR.
  5. Integrate `--refant-ranking` input to avoid poor/flagged reference antennas.
  6. **Pre-bandpass phase solve defaults**: Use `solint='30s'` (not `'inf'`) to handle time-variable phase drifts, and `minsnr=3.0` (not 5.0) to match bandpass threshold since phase-only solve is more robust.

- Actionable code pointers:
  - `src/dsa110_contimg/calibration/calibration.py`: update `solve_bandpass()` and `solve_gains()` to honor `combine_fields` by using the full `cal_field` string for CASA `field` selection when combining. **FIXED: Also updated `solve_prebandpass_phase()` to use full field range when `combine_fields=True`.**
  - `src/dsa110_contimg/calibration/cli.py`: when auto-selecting fields, pass the computed peak field for single-field solves; pass full selection when combining; add `--bp-minsnr` and plumb through. **FIXED: Updated default `--prebp-solint` to `'30s'` and `--prebp-minsnr` to `3.0`.**
  - `src/dsa110_contimg/api/job_runner.py`: pass `--model-source=catalog`, `--bp-combine-field`, and optional `--uvrange`/`--bp-minsnr` from UI params.

---

## Test Organization

**Location**: `tests/` directory (consolidated from `tests/` and `scripts/tests/` in 2025-01-15)

**Structure**:
- `tests/unit/` - Pytest unit tests (API routes, module validation)
- `tests/integration/` - Integration tests (end-to-end pipeline test)
- `tests/scripts/` - Standalone test/diagnostic scripts (run directly, not via pytest)
- `tests/utils/` - Test utilities and helper scripts

**Key Principles**:
- **Pytest tests** (`tests/unit/`, `tests/integration/`) use pytest fixtures and are discovered automatically
- **Standalone scripts** (`tests/scripts/`) are run directly: `python tests/scripts/test_*.py`
- **Path references**: All scripts use `parent.parent.parent` or equivalent to find repo root
- **Configuration**: `pytest.ini` configured to discover tests in `tests/unit` and `tests/integration`

**Running Tests**:
- Pytest: `pytest` or `pytest tests/unit/`
- End-to-end: `bash tests/integration/test_pipeline_end_to_end.sh`
- Standalone: `python tests/scripts/test_suite_comprehensive.py`

---

## Agent Rules Effectiveness (2025-01-XX)

**Lesson:** Concise, action-oriented rules in `.cursorrules` are highly effective at guiding agent behavior.

**Problem:** Agents were repeatedly using system Python (`python3`) instead of casa6, despite existing rules.

**Solution:** Updated `.cursorrules` with:
- Ultra-concise format (3-4 lines max for critical info)
- Action-oriented language ("BEFORE ANY PYTHON EXECUTION")
- Explicit prohibition ("NEVER use python/python3")
- Prominent placement (warning emoji, at top)

**Result:** ✅ Test validated - new agent automatically used casa6 without explicit instruction.

**Key Principles:**
- Keep critical rules SHORT (agents skip verbose text)
- Use action verbs ("BEFORE", "NEVER", "ALWAYS")
- Place most critical info FIRST
- Link to details rather than embedding them

**Reference:** `docs/TEST_AGENT_PYTHON_ENV.md` for test script and validation results.

---

## Documentation Organization (2025-01-XX)

**CRITICAL RULE:** All markdown documentation files MUST be placed in the `docs/` directory structure, NOT in the root directory.

**Root directory should only contain:**
- `README.md` - Main project README
- `MEMORY.md` - Agent memory file (this file)
- `TODO.md` - Active TODO list

**All other documentation goes in `docs/`:**
- User-facing docs: `docs/how-to/`, `docs/concepts/`, `docs/reference/`, `docs/tutorials/`
- Development notes: `internal/docs/dev/status/`, `internal/docs/dev/analysis/`, `internal/docs/dev/notes/`
- Historical: `docs/archive/`

**Before creating any markdown file:**
1. Check [`docs/DOCUMENTATION_QUICK_REFERENCE.md`](docs/DOCUMENTATION_QUICK_REFERENCE.md) for where to put it
2. Use lowercase_with_underscores naming (not UPPERCASE)
3. Never create files in root directory

**See also:**
- [Documentation Consolidation Strategy](docs/DOCUMENTATION_CONSOLIDATION_STRATEGY.md)
- [Documentation Quick Reference](docs/DOCUMENTATION_QUICK_REFERENCE.md)
- [Cursor Rule: Documentation Location](.cursor/rules/documentation-location.mdc)

---

## Related Documentation

- **Quick Start**: `docs/quickstart.md`
- **Pipeline Flow**: `docs/pipeline.md`
- **Deep Understanding**: `docs/analysis/PIPELINE_DEEP_UNDERSTANDING.md` - Comprehensive architecture and data flow documentation
- **Development History**: `docs/analysis/CURSOR_CHAT_DEVELOPMENT_HISTORY.md` - Key development decisions, bug fixes, and implementation details from AI-assisted development sessions
- **ESE Literature Summary**: `docs/reports/ESE_LITERATURE_SUMMARY.md`
- **Photometry Normalization**: `docs/science/photometry_normalization.md`
- See internal documentation for schema and guardrails.
- **Control Panel**: `docs/guides/control-panel/`
- **Complete Project Review**: `docs/reports/COMPLETE_PROJECT_REVIEW.md`
- **Test Suite**: `tests/README.md`
- **Robustness Analysis**: `docs/reports/PIPELINE_ROBUSTNESS_ANALYSIS.md` - Comprehensive analysis of pipeline robustness with actionable recommendations for error handling, resource management, state consistency, and observability

---

## Redundancies and Confusion Risks (2025-11-04)

- Unifying CASA logging helpers: `dsa110_contimg.utils.cli_helpers.casa_log_environment` duplicates `dsa110_contimg.utils.tempdirs.casa_log_environment`. Prefer a single source of truth (recommend `utils.tempdirs`) and update imports; optionally re-export from `cli_helpers` to avoid breaking changes. Also align `setup_casa_environment()`/`setup_casa_logging()` semantics under one API.
- Headless CASA setup is applied ad hoc across modules (`calibration/cli.py`, `calibration/flagging.py`, `qa/casa_ms_qa.py`, `qa/plotting.py`, `qa/sanity_plotms.py`, some tests). Centralize headless config (e.g., `utils.casa_env.ensure_headless()`), and call it consistently early in CLIs and any CASA-using code.
- CLI consistency gaps: Some CLIs use shared helpers (`conversion/cli.py`, `calibration/cli.py`, `imaging/cli.py`, `pointing/cli.py`), while others don’t (`mosaic/cli.py`, `beam/cli.py`). Adopt `add_common_logging_args()` and `configure_logging_from_args()` everywhere; consider adding `add_progress_flag()` + `utils.progress.should_disable_progress()` usage or removing the unused helper.
- Repeated CASA log env setup in `api/job_runner.py` (multiple places set `CASALOGFILE` and chdir). Factor into a helper (e.g., `_with_casa_log_env(env)` or reuse `utils.tempdirs.setup_casa_logging()` + `casa_log_environment()` for subprocess cwd).
- Duplicate antenna coordinate CSVs: both `src/dsa110_contimg/utils/antpos_local/data/DSA110_Station_Coordinates.csv` and `src/dsa110_contimg/utils/data/DSA110_Station_Coordinates.csv` exist. Consolidate to one authoritative path and update code/docs accordingly.
- Outdated notebook reference: `docs/notebooks/ms_staging_workflow.ipynb` still references `dsa110_contimg.conversion.uvh5_to_ms_converter_v2` (removed). Update to `conversion.strategies.hdf5_orchestrator` or `conversion.cli` to match current docs.
- `__main__` exit patterns are inconsistent (`main()` vs `raise SystemExit(main())`). Standardize to ensure exit codes propagate correctly, especially for scripts used in automation.
- Avoid changing CWD at import time: several CLIs call `setup_casa_environment()` at module import, which changes the working directory globally on import. Move to `main()` or use `casa_log_environment()` around CASA task calls.
- Env var namespaces: mixture of `CONTIMG_*` and `PIPELINE_*`. Backward-compat is fine (e.g., `derive_casa_log_dir()` honors both), but document precedence and prefer `CONTIMG_*` in new code.

These should reduce drift, improve predictability, and make the CLIs/API easier to maintain.

---

## Ops Directory Redundancies (2025-01-XX)

### Legacy Systemd Service File

**Problem:** Duplicate streaming converter service files:
- `ops/pipeline/dsa110-streaming-converter.service` (legacy, hardcoded paths)
- `ops/systemd/contimg-stream.service` (current, uses environment file)

**Key Lessons:**
- **Use `ops/systemd/contimg-stream.service`** as the canonical service file
- **Legacy file** uses hardcoded paths and old module structure
- **Current file** uses environment variables and modern configuration
- **Action:** Archive or remove legacy file, document canonical service in INSTALL.md

### Duplicate Helper Functions in ops/pipeline/

**Problem:** Multiple scripts duplicate identical helper functions:

**Catalog Loading Functions:**
- `_load_ra_dec()` appears in 3+ files with slight variations
- `_load_flux_jy()` appears in 2+ files with slight variations
- Some files have DB-aware versions, others don't

**MS Writing Functions:**
- `_write_ms_group_via_uvh5_to_ms()` appears in 4 files with ~300 lines of duplicated code
- All use `uvh5_to_ms` directly instead of orchestrator (production path)

**Group ID Parsing:**
- `_group_id_from_path()` appears in 4 files with identical logic

**Key Lessons:**
- **Create shared helpers**: `ops/pipeline/calibrator_helpers.py` for catalog loading
- **Prefer orchestrator**: Use `hdf5_orchestrator` CLI instead of direct `uvh5_to_ms` calls
- **Consolidate logic**: Reduces ~500 lines of duplicated code across scripts

### Overlapping Cleanup Routines

**Problem:** Multiple cleanup scripts with overlapping functionality:
- `ops/pipeline/housekeeping.py` - Queue recovery, temp dir cleanup
- `ops/pipeline/cleanup_old_data.py` - MS file deletion, log compression
- `ops/pipeline/scheduler.py` - Calls housekeeping, also does mosaicking

**Key Lessons:**
- **Integrate cleanup_old_data.py into housekeeping.py** for unified cleanup
- **Update scheduler.py** to call all cleanup functions
- **Single entry point** for all cleanup tasks improves maintainability

### Similar Calibrator Processing Scripts

**Problem:** Two scripts with ~400 lines of duplicated calibration logic:
- `ops/pipeline/build_central_calibrator_group.py` - Single central group
- `ops/pipeline/build_calibrator_transit_offsets.py` - Multiple groups in window

**Key Lessons:**
- **Extract shared calibration pipeline** to `ops/pipeline/calibrator_pipeline.py`
- **Keep scripts as thin wrappers** that find groups and call shared pipeline
- **Reduces duplication** by ~400 lines, improves maintainability

See `docs/OPS_REDUNDANCY_ANALYSIS.md` for comprehensive analysis and recommendations.

---

## New Lessons (2025-11-05)

- Phase angle handling: When converting phases from radians to degrees for QA metrics or plotting, wrap to [-180, 180) to avoid artificial scatter and discontinuities at ±180°. A new helper `dsa110_contimg.utils.angles.wrap_phase_deg()` provides consistent wrapping; use this instead of raw `np.degrees()` outputs for phase statistics and plots.
- Implementation notes:
  - QA: `qa/calibration_quality.py` now wraps phases before computing median/std/RMS.
  - API plots: `api/routes.py` wraps phases in `phase_vs_time` and `phase_vs_freq` plots.
  - Keep RA/Dec handling unchanged (astropy Angle or simple degrees is fine); wrapping is primarily for phases.

- **CRITICAL: CASA ft() Phase Center Bug (2025-11-05):**
  - **Root Cause:** CASA's `ft()` task (used by `setjy` internally) does NOT use `PHASE_DIR` or `REFERENCE_DIR` from the FIELD table. Instead, it determines phase center from the DATA column's original phasing (UVW coordinates). This causes MODEL_DATA to be misaligned with DATA when the MS has been rephased, leading to 100°+ phase scatter and calibration failures.
  - **Solution:** When rephasing is performed, automatically use manual MODEL_DATA calculation instead of `ft()`/`setjy`. Manual calculation reads `PHASE_DIR` per field and ensures correct phase structure.
  - **Implementation:**
    - `--model-source catalog`: Already uses manual calculation when rephasing is done ✓
    - `--model-source setjy`: Now detects if MS was rephased and uses manual calculation if calibrator coordinates are available (`--cal-ra-deg`, `--cal-dec-deg`, `--cal-flux-jy`)
    - `--model-source component/image`: Still uses `ft()` (no easy conversion); warnings added
  - **Best Practice:** When rephasing MS, use `--model-source catalog` with calibrator coordinates, or provide coordinates when using `--model-source setjy`. Avoid component/image models when rephasing.
  - **Verification:** Test script `scripts/test_ft_phase_dir_corrected.py` confirms ft() doesn't use PHASE_DIR (104.5° scatter even when component is at PHASE_DIR position).
  - **References:** `docs/reports/FT_PHASE_CENTER_FIX.md`, `docs/reports/FT_PHASE_CENTER_TEST_RESULTS.md`

- **AOFlagger Docker Installation (2025-01-XX):**
  - AOFlagger installed via Docker to resolve Ubuntu 18.x compatibility issues (CMake version conflicts with pybind11)
  - Dockerfile pattern mirrors WSClean installation (`~/proj/wsclean/Dockerfile.everybeam-0.7.4`)
  - **Location:** `~/proj/aoflagger/Dockerfile` and `~/proj/aoflagger/build-docker.sh`
  - **Base image:** Ubuntu 24.04 (modern CMake, GCC 13) to avoid host system CMake version issues
  - **Dependencies:** casacore (built from source), HDF5, CFITSIO, FFTW3, GSL, Boost, Lua 5.3, Python/pybind11, PNG
  - **GUI disabled:** Built with `-DENABLE_GUI=OFF` to avoid GTKMM dependency
  - **Image tag:** `aoflagger:latest` (version 3.4, 2023-10-06)
  - **Usage:** `docker run --rm -v /scratch:/scratch -v /data:/data aoflagger:latest aoflagger <args>`
  - **Integration:** Can be used as alternative to CASA `flagdata` for RFI flagging (see `docs/reports/ALTERNATIVE_RFI_FLAGGING_METHODS.md`)
  - **Note:** Similar to WSClean, this must run in Docker container on Ubuntu 18.x hosts due to glibc version requirements

## Streaming Mode Procedure (2025-11-06)
- **Description**: Real-time processing of incoming UVH5 subband files: watches input directory, groups by timestamp and subband, converts to MS using hdf5_orchestrator.
- **Scope**: conversion
- **Parameters**: input_dir, ms_dir, group_timeout, max_retries
- **Preferences**:
  - Name: streaming/tmpfs_staging
  - Key: stage_to_tmpfs
  - Value: true
  - Category: performance
  - Applies to: procedure
- **Relationships**:
  - Procedure:streaming/conversion --HAS_PREFERENCE--> Preference:streaming/tmpfs_staging
  - Procedure:streaming/conversion --REQUIRES_HONING--> automation, error_recovery, scalability

### Workflow
1. Deploy via systemd or Docker to watch input directory.
2. Group arriving *_sb??.hdf5 files by 5-min timestamp windows (16 subbands).
3. Convert complete groups to MS using direct_subband writer (parallel + CASA concat).
4. Optionally trigger downstream calibration/imaging via API/scripts.

### Readiness
- Core machinery (watcher, queuing, conversion) is functional and tested.
- Needs honing: automate downstream triggering, improve error recovery, scale testing for high-volume streams.
- Open TODO: Automate full streaming with ESE flagging; optimize for low-latency previews.

## CASA-mpi Evaluation (2025-01-XX)

**Context**: Evaluated CASA-mpi for MPI parallelization on remote HPC server.

**Key Findings**:
- **Recommendation: NOT RECOMMENDED** for current pipeline
- **Primary reason**: Pipeline uses WSClean (2-5x faster than tclean), not CASA tclean
- **Infrastructure blocker**: HPC has OpenMPI 2.1.1, but CASA-mpi requires OpenMPI >= 5.0
- **Limited benefit**: Current parallelization (ProcessPoolExecutor) already handles independent MS operations efficiently
- **Complexity cost**: Would require MPI upgrade + code changes for marginal gains

**When to reconsider**:
- If switching to tclean as primary backend (unlikely given WSClean performance)
- If processing large spectral cubes (not current use case)
- If HPC infrastructure upgraded and multi-node MPI needed

**Current parallelization strategy** (sufficient):
- Conversion: Parallel per-subband writes (16 workers)
- Independent MS: ProcessPoolExecutor (2-4x speedup)
- Imaging: WSClean with OpenMP threads (no MPI needed)

**Documentation**: See `docs/reports/CASA_MPI_EVALUATION.md` for complete analysis.

## Deep Dive Issues Analysis (2025-01-XX)

**Comprehensive codebase analysis** identified critical security vulnerabilities, resource management issues, and areas for improvement.

**Critical Findings:**

1. **SQL Injection Vulnerabilities** (CRITICAL):
   - Dynamic SQL construction using f-strings in multiple files
   - Table/column names interpolated directly from user input
   - Affected files: `api/routes.py`, `database/data_registry.py`, `database/jobs.py`, `mosaic/validation.py`, `catalog/build_master.py`
   - **Fix**: Use parameterized queries, whitelist table/column names, never interpolate table names directly

2. **Thread Safety Issues** (CRITICAL):
   - SQLite connections with `check_same_thread=False` but shared across threads
   - Lock protects individual operations but not multi-step transactions
   - Risk of database corruption with concurrent writes
   - **Fix**: Use per-operation connections or WAL mode, implement proper transaction boundaries

3. **Resource Leak Risks** (HIGH):
   - Database connections not always closed in error paths
   - Temporary files may not be cleaned up if exceptions occur
   - CASA file handles can leak if cleanup not called
   - **Fix**: Use context managers consistently, ensure cleanup in all error paths

4. **Path Traversal Vulnerability** (HIGH):
   - API endpoint `/qa/file/{group}/{name}` has fallback path check vulnerable to symlink attacks
   - No validation that path components don't contain separators
   - **Fix**: Validate input format, use safe path operations, handle symlinks correctly

5. **Error Handling Inconsistencies** (HIGH):
   - 265+ broad `except Exception:` clauses
   - Missing cleanup in error paths
   - Error context may be lost
   - **Fix**: Catch specific exceptions, use exception chaining, ensure cleanup

**Medium Priority Issues (FIXED):**
- Configuration validation gaps (env vars used without validation) - **FIXED**: Added safe_int/safe_float helpers with type and range validation
- File locking issues (stale locks, no cleanup) - **FIXED**: Added cleanup_stale_locks() function with PID validation and timeout
- Race conditions in concurrent database operations - **FIXED**: Already addressed in CRITICAL fixes (WAL mode, explicit transactions)
- Performance bottlenecks (queries fetching all rows, missing indexes) - **VERIFIED**: All queries use WHERE clauses properly, no issues found

**Documentation**: See `docs/reports/MEDIUM_PRIORITY_FIXES_SUMMARY.md` for complete details.

**Reassessment**: See `docs/reports/REASSESSED_ISSUES_PRIORITY.md` for updated priority classification after fixes.

**Full Report**: `docs/reports/DEEP_DIVE_ISSUES_REPORT.md`

## Post-Fix Reassessment (2025-01-XX)

**Priority Reclassification** completed after applying fixes:

**CRITICAL Issues:** ✅ All fixed (2/2)
- SQL injection vulnerabilities - FIXED
- Thread safety issues - FIXED

**HIGH Priority Issues Remaining:** 1/4
- ✅ Path traversal vulnerability - FIXED
- ✅ Resource cleanup (partial) - IMPROVED
- ⚠️ Error handling inconsistencies - REMAINING (731 broad exception catches across 114 files)
- ⚠️ CASA file handle leaks - DOWNGRADED to MEDIUM (mitigation exists)

**MEDIUM Priority Issues:** 3/5 remaining
- ✅ Configuration validation - FIXED
- ✅ File locking issues - FIXED
- ✅ Database query patterns - VERIFIED (no issues)
- ⚠️ Path validation at config load - PARTIAL (function exists, not auto-called)
- ⚠️ Missing default values documentation - REMAINING

**Key Insights:**
- Most critical security issues resolved
- Error handling remains the largest operational concern (HIGH priority)
- CASA file handle management downgraded to MEDIUM (mitigation exists, low probability)
- Mosaic validation dynamic IN clause verified safe (uses parameterized queries)

**Next Steps:**
1. ✅ Address error handling inconsistencies systematically (HIGH priority) - DONE
2. ✅ Add CASA context manager wrapper (MEDIUM priority) - DONE
3. ✅ Add automatic path validation to config loading (MEDIUM priority) - DONE
4. ✅ Create comprehensive configuration documentation (MEDIUM priority) - DONE

## Code Quality Improvements (2025-01-XX)

**High-priority work completed** for systematic code quality improvements across the codebase.

**Completed:**
1. **Logging Consistency** - Fixed critical paths
   - `direct_subband.py`: Replaced 10+ `print()` statements with logger calls
   - `catalog/build_master.py`: Added logging alongside user-facing print statements
   - Established patterns for remaining 28 files

2. **Error Message Consistency** - Standardized exception handling
   - `orchestrator.py`: More specific exception catching, better error context
   - `api/job_adapters.py`: All job functions now use unified exception hierarchy
     - `run_convert_job()`: Uses `ValidationError` and `ConversionError`
     - `run_calibrate_job()`: Uses `ValidationError` with specific exception catching
     - `run_apply_job()`: Uses `ValidationError` with specific exception catching
     - `run_image_job()`: Uses `ValidationError` and `ImagingError`
   - All exceptions now include context and actionable suggestions

3. **Type Safety** - Cleanup and verification
   - Removed unused imports from `job_adapters.py`
   - Verified database functions have proper type hints
   - Created guide for addressing remaining `# type: ignore` comments

**Documentation:**
- `docs/reports/CODE_QUALITY_IMPROVEMENTS_GUIDE.md` - Comprehensive guide with patterns and priorities
- `docs/reports/CODE_QUALITY_COMPLETION_SUMMARY.md` - Summary and remaining work tracking
- `docs/reports/CODE_QUALITY_WORK_COMPLETED.md` - Detailed completion report

**Additional Work Completed:**
- `calibration/cli_calibrate.py`: Added logging alongside user-facing print statements
- `conversion/cli.py`: Added logging module and logger calls
- `imaging/cli.py`: Added logger calls for warnings
- `calibration/calibration.py`: Replaced print() with logger.info()
- `conversion/strategies/hdf5_orchestrator.py`: Replaced print() with logger.debug()

Immediate next steps:
Complete qa/calibration_quality.py logging (highest impact)
Standardize exceptions in core conversion modules
Add type hints to helper functions**Low Priority Work Completed:**
- `qa/calibration_quality.py`: Replaced print() with logger calls in key functions
- `mosaic/cli.py`: Added logger calls alongside user-facing print statements

**Remaining Work (Low Priority):**
- **Logging:** 579 print() statements across 44 files (~7% complete)
  - `qa/calibration_quality.py`: ~95 print() statements remaining (highest priority)
  - CLI tools: ~15 files with user-facing print() statements (medium priority)
  - Utility/test files: ~20 files (low priority)
- **Error messages:** 258 generic exceptions across 47 files (~4% complete)
  - Core conversion/calibration: ~10 files (high priority)
  - Supporting modules: ~15 files (medium priority)
  - Utility modules: ~20 files (low priority)
- **Type safety:** 101 `# type: ignore` comments across 35 files (~5% complete)
  - ~60 acceptable (CASA libraries without stubs)
  - ~40 can be improved (helper functions, CLI parsing)

**Progress Report:** See `docs/reports/CODE_QUALITY_PROGRESS_REPORT.md` for detailed status

**Impact:**
- Critical paths now use proper logging infrastructure
- Better error messages with actionable suggestions
- Consistent exception handling patterns established
- Foundation ready for incremental improvements

**Action Items:**
1. Fix SQL injection vulnerabilities immediately (CRITICAL)
2. Fix thread safety issues before production deployment (CRITICAL)
3. Add resource cleanup guarantees (HIGH)
4. Improve path traversal protection (HIGH)
5. Standardize error handling (HIGH)

---

## Mosaic Construction Workflow

### Building 60-Minute Mosaics Around VLA Calibrators

**Key Concept:** A mosaic combines multiple 5-minute tiles (images) into a single larger image covering a wider field of view. For a 60-minute mosaic around VLA calibrator 0834+555:

1. **Transit Time Calculation**
   - Use `dsa110_contimg.calibration.schedule.previous_transits()` to find transit times
   - Transit occurs when source RA equals Local Sidereal Time (LST)
   - Example: `previous_transits(ra_deg, start_time=Time("2025-11-02 23:59:59"), n=10)`
   - Returns list of transit Time objects

2. **Time Window Selection**
   - 60-minute window = ±30 minutes around transit
   - Convert to Unix timestamps for mosaic CLI: `int(time.unix)`
   - Window should span 12 complete 5-minute groups

3. **Data Processing Pipeline** (if tiles don't exist)
   - **Conversion**: HDF5 groups → MS files (`hdf5_orchestrator.py`)
   - **Calibration**: BP + G calibration (`calibration.cli calibrate`)
   - **Imaging**: MS → PB-corrected images (`imaging.cli image --pbcor`)
   - **Registration**: Images registered in products DB

4. **Mosaic Planning**
   - Query products DB for PB-corrected tiles in time window
   - Use `mosaic.cli plan` with `--since` and `--until` epoch timestamps
   - Method options: `pbweighted` (recommended), `weighted`, `mean`
   - Plan stored in `mosaics` table in products DB

5. **Mosaic Building**
   - Use `mosaic.cli build` with planned mosaic name
   - Validates tiles (grid consistency, astrometry, calibration, PB)
   - Computes pixel-by-pixel weights: `weight = pb^2 / noise_variance`
   - Combines tiles: `mosaic = sum(weight * tile) / sum(weight)`
   - Exports FITS file for analysis

**Key Files:**
- `scripts/build_0834_transit_mosaic.py`: Simple script for 0834+555 mosaics
- `scripts/build_60min_mosaic.py`: Comprehensive end-to-end workflow
- `src/dsa110_contimg/mosaic/cli.py`: Mosaic planning and building CLI
- `src/dsa110_contimg/mosaic/cli.py:_build_weighted_mosaic()`: PB-weighted combination logic

**Important Notes:**
- All tiles must be PB-corrected (`pbcor=1` in products DB)
- Tiles must have consistent grids (same pixel scale, alignment)
- PB images must exist for PB-weighted method
- Validation checks ensure science quality before building
- Use `--dry-run` to validate without building

**Quick Reference:**
```bash
# Find transit and plan mosaic
python scripts/build_0834_transit_mosaic.py

# Or step-by-step:
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since <start_epoch> --until <end_epoch> \
    --method pbweighted

python -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image
```

## Deep Study Summary (2025-01-XX)

**Comprehensive Codebase Analysis:**

A deep study of the entire dsa110-contimg codebase was conducted, covering architecture, implementation patterns, database schema, deployment options, and key technical decisions.

**Key Findings:**

1. **Architecture Overview:**
   - Production-ready radio astronomy pipeline with 8 core components
   - Streaming converter → Conversion → Calibration → Imaging → Photometry → ESE Detection
   - ~50,000+ lines of Python code, well-organized modular structure
   - Comprehensive FastAPI monitoring API (4000+ lines in routes.py)
   - 169+ Python modules, 883+ classes and functions, 1,265+ import statements
   - Modern React/TypeScript frontend with WebSocket support for real-time updates

2. **Database Schema:**
   - Products DB: `ms_index` (renamed to `ms_all`), `images` (renamed to `images_all`), `photometry_timeseries`, `variability_stats`, `ese_candidates`, `mosaics`, `regions`, `alert_history`
   - Queue DB: `ingest_queue`, `subband_files`, `performance_metrics`
   - Cal Registry DB: `caltables` with validity windows and apply order
   - Catalog DBs: `vla_calibrators.sqlite3`, `master_sources.sqlite3`
   - Storage location registry: `storage_locations` table tracks base directories

3. **Technical Patterns:**
   - Strategy pattern for writer selection (production vs testing)
   - Pipeline orchestration framework with dependency resolution (`pipeline/orchestrator.py`)
   - SQLite-first approach for all persistent state
   - tmpfs staging for 3-5x conversion speedup (`/dev/shm`)
   - Factory pattern for writer creation (`get_writer()`)
   - Repository pattern for database access (`database/products.py`, `database/registry.py`)
   - Observer pattern for pipeline observability (`pipeline/observability.py`)
   - Stage-based execution with retry policies and error recovery

4. **Critical Technical Decisions:**
   - casa6 Python environment is MANDATORY (never use system Python)
   - K-calibration skipped by default for DSA-110 (short baselines <2.6 km)
   - WSClean default backend (2-5x faster than tclean)
   - Differential photometry normalization achieves 1-2% relative precision
   - Single shared phase center for entire group (prevents discontinuities)
   - CASA ft() phase center bug fixed (manual MODEL_DATA calculation when rephased)
   - MS files written directly to organized locations (`ms/science/YYYY-MM-DD/`, `ms/calibrators/YYYY-MM-DD/`)

5. **Code Quality Status:**
   - Critical security issues fixed (SQL injection, thread safety)
   - Logging consistency: ~7% complete (579 print() statements remaining across 44 files)
   - Error handling: ~4% complete (258 generic exceptions remaining across 47 files)
   - Type safety: ~5% complete (101 `# type: ignore` comments across 35 files)
   - Remaining: 731 broad exception catches across 114 files (HIGH priority)

6. **Deployment Options:**
   - Systemd (recommended for streaming worker)
   - Docker Compose (good for API and reproducible deployments)
   - Frontend: React/TypeScript dashboard with WebSocket support
   - Scheduler service for automated housekeeping and nightly mosaics

7. **Frontend Architecture:**
   - React 18+ with TypeScript
   - Vite build system
   - WebSocket for real-time pipeline status updates
   - JS9 integration for image visualization
   - Component structure: Pages → Components → API layer
   - Key pages: Dashboard, Control Panel, Sky Viewer, Source Monitoring, Mosaic Gallery

8. **Pipeline Orchestration Framework:**
   - Declarative stage definitions with dependencies
   - Topological sorting for execution order
   - Retry policies with exponential backoff
   - Context passing between stages
   - Observability hooks for metrics and logging
   - Standard workflows: `standard_imaging_workflow()`, `quicklook_workflow()`

**Documentation:**
- Complete deep study summary: `docs/analysis/DEEP_STUDY_COMPREHENSIVE.md` (new comprehensive version)
- Previous summary: `docs/analysis/DEEP_STUDY_SUMMARY.md`
- Comprehensive architecture details: `docs/analysis/PIPELINE_DEEP_UNDERSTANDING.md`
- Pipeline flow visualization: `docs/concepts/pipeline_overview.md`
- Directory architecture: `docs/concepts/DIRECTORY_ARCHITECTURE.md`

**Key Strengths:**
- Clear architecture with well-defined data flow
- Production-ready deployment options
- Comprehensive monitoring and QA
- Scientific accuracy (1-2% relative flux precision)
- Modern pipeline orchestration framework
- Extensive documentation structure
- Organized file structure (date-based MS organization)
- Real-time frontend with WebSocket support

**Areas for Improvement:**
- Complete code quality improvements (logging, error handling, type safety)
- Integrate ESE detection fully into pipeline (currently mock data in API)
- Consolidate redundant code in ops/pipeline/
- Complete pipeline robustness improvements (6-week plan)
- Expand test coverage (unit, integration, end-to-end)
- Complete CARTA Phase 3 (progressive loading, WebGL rendering)


---

## Measurement Set Permissions

### Critical: MS Files Must Be Writable

**Issue Discovered:** 2025-11-09

Measurement Sets (MS) must **never** be read-only. CASA tasks require write access to:
- Modify `MODEL_DATA` column (for skymodel seeding)
- Update `CORRECTED_DATA` column (during calibration)
- Write flagging information
- Update weight columns

**Symptoms:**
- CASA `ft()` task fails with: "Please make sure MS is writable when using Imager::ft"
- NVSS skymodel seeding skipped
- Non-fatal for read-only imaging, but prevents calibration and model updates

**Root Cause:**
- `table.dat` files owned by `root:root` instead of `ubuntu:ubuntu`
- Likely caused by running CASA commands or scripts with `sudo`
- All affected files modified on same date/time (batch operation)

**Fix:**
```bash
# Find and fix all root-owned files in MS directories
find /stage/dsa110-contimg/ms -type f ! -user ubuntu -exec sudo chown ubuntu:ubuntu {} \;
```

**Prevention:**
- Never run CASA commands or pipeline scripts with `sudo`
- Ensure all systemd services run as `ubuntu` user (already configured)
- Verify MS permissions after any batch operations
- Check ownership before running calibration or imaging tasks

**Verification:**
```bash
# Check for root-owned files
find /stage/dsa110-contimg/ms -type f ! -user ubuntu | wc -l
# Should return 0

# Verify specific MS
ls -lh /path/to/ms/table.dat

---

## CASA Table Locking and Concurrent Access

### Critical: MS Cannot Be Accessed Concurrently for Write Operations

**Date:** 2025-11-09  
**Issue:** CASA's table locking mechanism prevents concurrent write access to the same Measurement Set.

### Problem

When multiple processes try to access the same MS simultaneously (e.g., parallel adaptive binning on multiple sources), CASA throws **resource deadlock errors**:

```
Error (Resource deadlock avoided) when acquiring lock on 
/path/to/ms/table.lock
```

### Root Cause

- CASA `tclean` requires **write access** to the MS (to write MODEL_DATA column)
- CASA's table locking mechanism (`table.lock` file) doesn't support concurrent write access
- Multiple processes accessing the same MS simultaneously conflict on the lock
- Even read operations can conflict if another process has a write lock

### Impact

- Parallel processing of multiple sources on the same MS causes lock conflicts
- Many SPW imaging attempts fail initially, requiring retries
- Warning messages: "Failed to clear MODEL_DATA before ft()"
- Inefficient processing due to lock contention

### Solutions

1. **Serialize MS Access (Recommended)**
   - Process multiple sources sequentially
   - Or implement a file lock mechanism to serialize access:
   ```python
   import fcntl
   lock_file = f"{ms_path}.lock"
   with open(lock_file, 'w') as lock:
       fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
       # Process MS
   ```

2. **Copy MS for Each Process**
   - Create a copy of the MS for each parallel process
   - Expensive but avoids conflicts
   - Only practical for small MS files

3. **Use WSClean Backend**
   - WSClean reads the MS but doesn't write MODEL_DATA
   - May avoid some locking issues
   - However, WSClean doesn't support SPW selection directly

4. **Accept Sequential Processing**
   - For multiple sources on the same MS, process sequentially
   - Simpler but slower

### Best Practices

- **For production:** Implement MS access serialization when processing multiple sources on the same MS
- **For testing:** Process sources sequentially or use separate MS files for parallel testing
- **Consider:** Adding a `--serialize-ms-access` flag to imaging/photometry CLIs

### Related Files

- `src/dsa110_contimg/imaging/spw_imaging.py`: SPW imaging (uses `image_ms` which calls `tclean`)
- `src/dsa110_contimg/photometry/adaptive_photometry.py`: Adaptive binning photometry
- `docs/testing/PHASE1_MULTIPLE_SOURCES_TEST_RESULTS.md`: Test results documenting this issue

---

## VAST Tools Comparison and Adoption Recommendations

**Date:** 2025-01-XX  
**Reference:** `/data/dsa110-contimg/archive/references/vast-tools`

### Key Findings

DSA-110 has strong foundations (photometry, normalization, database) but lacks the rich source analysis interface and visualization tools that VAST Tools provides. Adopting VAST patterns would significantly improve ESE candidate analysis workflows.

### Current State vs. VAST Tools

**DSA-110 Strengths:**
- ✅ Forced photometry (`photometry/forced.py`)
- ✅ Differential normalization (`photometry/normalize.py`) - achieves 1-2% precision
- ✅ Database storage (`photometry_timeseries`, `variability_stats` tables)
- ✅ Basic variability metrics (V metric, χ²)

**DSA-110 Gaps:**
- ❌ No Source class pattern (only database queries)
- ❌ No light curve plotting (essential for ESE visualization)
- ❌ Missing variability metrics (η metric, Vs metric, m metric)
- ❌ No postage stamp visualization
- ⚠️ Limited external catalog integration (NVSS/VLASS only, missing SIMBAD/NED/Gaia)

### Recommended Adoptions (Priority Order)

#### 1. Source Class Pattern (High Priority)
**Why:** Clean interface for ESE candidate analysis, encapsulates measurements/plotting/analysis  
**Implementation:** Create `src/dsa110_contimg/photometry/source.py`  
**Timeline:** 2-3 weeks  
**Adopt from:** `vasttools/source.py::Source`

**Key Features:**
- Load measurements from `photometry_timeseries` table
- Properties: `coord`, `n_epochs`, `detections`
- Methods: `plot_lightcurve()`, `calc_variability_metrics()`, `show_all_cutouts()`

#### 2. Light Curve Plotting (High Priority)
**Why:** Essential for ESE candidate visualization and verification  
**Implementation:** Add to Source class or create `qa/lightcurves.py`  
**Timeline:** 1 week  
**Adopt from:** `vasttools/source.py::Source.plot_lightcurve()`

**ESE-Specific Features:**
- Highlight baseline period (first 10 epochs)
- Highlight ESE candidate period (14-180 days)
- Normalized flux plotting
- Error bars and detection/limit distinction

#### 3. Variability Metrics (Medium Priority)
**Why:** Complementary to χ² for variability detection  
**Implementation:** Create `photometry/variability.py`  
**Timeline:** 1 week  
**Adopt from:** `vasttools/utils.py`

**Metrics to Add:**
- **η metric**: Weighted variance (`pipeline_get_eta_metric()`)
- **Vs metric**: Two-epoch t-statistic (`calculate_vs_metric()`)
- **m metric**: Modulation index (`calculate_m_metric()`)

**Database Update:** Add `eta_metric` column to `variability_stats` table

#### 4. Postage Stamp Visualization (Medium Priority)
**Why:** Visual verification of ESE candidates, quality assessment  
**Implementation:** Create `qa/postage_stamps.py`  
**Timeline:** 2 weeks  
**Adopt from:** `vasttools/source.py::Source.show_all_png_cutouts()`

**Features:**
- Image cutout creation around source position
- All-epoch grid visualization
- Z-scale normalization
- Customizable size and layout

#### 5. External Catalog Integration (Low-Medium Priority)
**Why:** Better source identification and crossmatching  
**Implementation:** Create `catalog/external.py`  
**Timeline:** 1-2 weeks  
**Adopt from:** `vasttools/utils.py::simbad_search()`, `vasttools/source.py`

**Catalogs to Add:**
- SIMBAD (object identification)
- NED (extragalactic database)
- Gaia (astrometry)

### Implementation Pattern

**Source Class Structure:**
```python
class Source:
    def __init__(self, source_id, ra_deg, dec_deg, products_db):
        self.source_id = source_id
        self.measurements = self._load_measurements()
    
    @property
    def coord(self) -> SkyCoord:
        return SkyCoord(self.ra_deg, self.dec_deg, unit=(u.deg, u.deg))
    
    def plot_lightcurve(self, highlight_baseline=True, ...) -> Figure:
        # Adopt from VAST with ESE-specific features
    
    def calc_variability_metrics(self) -> dict:
        # Include η, Vs, m metrics
```

### Integration Points

**API Endpoints:**
- `GET /api/sources/{source_id}/lightcurve` → Source.plot_lightcurve()
- `GET /api/sources/{source_id}/variability` → Source.calc_variability_metrics()
- `GET /api/sources/{source_id}/postage_stamps` → Source.show_all_cutouts()

**ESE Detection Workflow:**
```python
def analyze_ese_candidate(source_id: str):
    source = Source(source_id=source_id, products_db=products_db)
    lightcurve = source.plot_lightcurve(highlight_ese_period=True)
    metrics = source.calc_variability_metrics()
    return {'metrics': metrics, 'lightcurve': lightcurve}
```

### Dependencies

**Required:**
- `astroquery` (for external catalog queries)

**Optional:**
- `bokeh` (for interactive plots, can add later)

### Timeline

- **Phase 1 (High Priority):** 2-3 weeks (Source class + light curves + basic metrics)
- **Phase 2 (Medium Priority):** 2 weeks (Postage stamps + enhanced metrics)
- **Phase 3 (Low-Medium Priority):** 1-2 weeks (External catalogs)
- **Total:** 5-7 weeks

### Risk Assessment

- **Low Risk:** Adopting well-tested patterns from VAST Tools
- **Non-Breaking:** Can be added incrementally without breaking existing code
- **High Value:** Significantly improves ESE analysis workflow

### Related Documentation

- **Detailed Comparison:** `docs/analysis/VAST_TOOLS_DSA110_DETAILED_COMPARISON.md`
- **Adoption Summary:** `docs/analysis/VAST_TOOLS_ADOPTION_SUMMARY.md`
- **VAST Tools Review:** `archive/references/vast-tools/VAST_TOOLS_CODEBASE_REVIEW.md`
- **VAST Tools Code:** `archive/references/vast-tools/vasttools/`

## Streaming Test Run Lessons Learned (2025-11-10)

**Context:** First trial autonomous streaming run from conversion to mosaic creation failed due to multiple issues, but revealed critical lessons about validation, workflow integration, and expected behaviors.

### Key Mistakes and Fixes

1. **Phase Center Validation: Expected Behavior Treated as Error**
   - **Mistake:** Phase center validation failed with 2583.71 arcsec separation (vs 2.00 arcsec tolerance), halting test run
   - **Root Cause:** DSA-110 uses meridian-tracking phasing (RA = LST), causing phase centers to be incoherent across fields (EXPECTED)
   - **Fix:** Created `conversion/README.md` documenting expected behavior, updated validation to detect time-dependent phasing, added tolerance for large separations (>60 arcsec)
   - **Lesson:** Document expected behaviors prominently - don't bury in function docstrings. Validation should distinguish expected vs. error conditions.

2. **File Existence Validation Gaps**
   - **Mistake:** MS files not verified to exist before processing in multiple locations (`run_first_mosaic.py`, `streaming_mosaic.py`)
   - **Root Cause:** Assumed database paths always correct, no validation against filesystem
   - **Fix:** Added file existence checks before all MS operations, validated database paths against filesystem
   - **Lesson:** Always verify file existence before operations - don't trust database paths blindly. Validate database paths against filesystem, especially after organization.

3. **Race Condition: Processing Before Conversion Completes**
   - **Mistake:** `process_one_group()` returned immediately after calling conversion, tried to process MS before it existed
   - **Root Cause:** Conversion runs asynchronously, no wait mechanism for completion
   - **Fix:** Added explicit wait for conversion completion, file existence verification, retry logic
   - **Lesson:** Synchronize async operations - don't assume completion, verify before proceeding.

4. **Incorrect Time Fallback Logic**
   - **Mistake:** Used `time.time() / 86400.0` (current time) as fallback instead of observation time from filename
   - **Root Cause:** Fallback logic didn't extract observation time from filename when MS metadata unavailable
   - **Fix:** Fixed time extraction fallback to use observation time from filename, added multiple fallback mechanisms
   - **Lesson:** Use observation time for calibration validity windows - not current time. Multiple fallback mechanisms: filename → metadata → current time (last resort).

5. **Missing Mosaic Registration and Finalization**
   - **Mistake:** Mosaics created but never registered in `data_registry`, never finalized, stayed in staging forever
   - **Root Cause:** Missing calls to `register_mosaic_in_data_registry()` and `finalize_mosaic()`, QA/validation status never set
   - **Fix:** Added registration and finalization steps, set QA/validation status, added error handling and retry logic
   - **Lesson:** Complete the entire workflow - don't stop at creation, register and finalize. Set all required status fields for auto-publish.

### Critical Principles for Autonomous Runs

1. **Document Expected Behaviors Prominently**
   - Create module-level READMEs for expected behaviors (e.g., `conversion/README.md`)
   - Don't bury important information in function docstrings
   - Reference documentation in error messages

2. **Distinguish Expected vs. Error Conditions**
   - Validation should detect expected behaviors before failing
   - Add tolerance for expected variations (phase center separations, time-dependent phasing)
   - Guide users in error messages - reference documentation, explain why behavior is expected

3. **Always Verify File Existence**
   - Check file existence before all MS operations
   - Validate database paths against filesystem
   - Handle missing files gracefully with clear error messages

4. **Handle Race Conditions Explicitly**
   - Wait for conversion completion before processing
   - Verify file existence, not just process exit code
   - Add retry logic with timeout for transient failures

5. **Complete the Entire Workflow**
   - Don't stop at creation - register and finalize
   - Set all required status fields (QA/validation status, processing stage)
   - Trigger auto-publish by ensuring criteria are met

6. **Use Observation Time, Not Current Time**
   - Extract observation time from filename when MS metadata unavailable
   - Use observation time for calibration validity windows
   - Multiple fallback mechanisms: filename → metadata → current time (last resort)

### Pre-Flight Checklist for Autonomous Runs

Before running autonomous test:
- [ ] Verify all expected behaviors are documented (phase centers, validation tolerances)
- [ ] Check file existence validation is in place for all MS operations
- [ ] Verify race condition handling (wait for conversion completion)
- [ ] Validate database paths match filesystem
- [ ] Test time extraction fallback logic
- [ ] Verify mosaic registration and finalization workflow

### Additional Safeguards Implemented

After initial review, implemented 5 critical safeguards:

1. **Group ID Collision Prevention** - SHA256 hash + microsecond timestamp prevents collisions
2. **Total Time Span Validation** - Ensures mosaics from contiguous observations (< 60 min span)
3. **MS Files Stage Validation** - Only groups from fully processed (imaged) MS files
4. **Calibration Table Existence Validation** - Verifies tables exist before applying
5. **Image File Existence Validation** - Verifies all images exist before mosaic creation

### Related Documentation

- **Full Review:** `docs/reports/streaming_test_run_review_2025-11-10.md` - Comprehensive analysis of mistakes and fixes
- **Safeguards Implemented:** `docs/reports/safeguards_implemented_2025-11-10.md` - Details of safeguards added
- **Additional Safeguards Needed:** `docs/reports/additional_safeguards_needed_2025-11-10.md` - Lower priority issues
- **Conversion README:** `src/dsa110_contimg/conversion/README.md` - Expected behaviors and troubleshooting
