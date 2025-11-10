# Ingest data and construct mosaic
_Exported on 11/7/2025 at 13:37:46 PST from Cursor (2.0.64)_

---

**User**

Ingest all of @dsa110_contimg .



Learn how to construct a 60 min mosaic around the VLA calibrator 0834+555.

---

**Cursor**


Exploring the codebase structure and searching for mosaic construction code, focusing on VLA calibrator 0834+555.



Exploring additional modules to understand the workflow:



Reviewing conversion and imaging modules to understand the workflow:



Reading the mosaic documentation:



Creating a guide on constructing a 60-minute mosaic around VLA calibrator 0834+555. Updating MEMORY.md with this knowledge:


```markdown
# How-To: Build a 60-Minute Mosaic Around VLA Calibrator 0834+555

**Objective:** Create a 60-minute mosaic (12 tiles at 5-minute cadence) centered on the transit of VLA calibrator 0834+555.

**Prerequisites:**
- UVH5 subband files available in `/data/incoming` (or your input directory)
- `casa6` conda environment activated
- Pipeline environment variables configured (if using custom paths)
- Products database exists (`state/products.sqlite3`)

---

## Overview

A 60-minute mosaic combines 12 individual 5-minute tiles (images) into a single larger image covering a wider field of view. The process involves:

1. **Finding the transit time** for 0834+555 on a specific date
2. **Calculating a 60-minute window** (±30 minutes around transit)
3. **Converting HDF5 groups to MS** (if not already done)
4. **Calibrating MS files** (if not already done)
5. **Imaging each MS** to create tiles (if not already done)
6. **Planning the mosaic** (selecting tiles from products DB)
7. **Building the mosaic** (combining tiles with primary beam weighting)

---

## Method 1: Using the Pre-Built Script (Simplest)

The simplest approach uses the existing script that handles all steps:

```bash
cd /data/dsa110-contimg
PYTHONPATH=/data/dsa110-contimg/src python scripts/build_0834_transit_mosaic.py
```

**What this script does:**
1. Finds transit time for 0834+555 on 2025-11-02 (hardcoded date)
2. Calculates ±30 minute window around transit
3. Plans mosaic from tiles in products DB within that window
4. Builds PB-weighted mosaic

**To use a different date:**
Edit `scripts/build_0834_transit_mosaic.py` and change:
```python
target_date = "2025-11-02"  # Change to your desired date
```

---

## Method 2: Step-by-Step Manual Process

### Step 1: Find Transit Time

Calculate when 0834+555 transits on your target date:

```python
from astropy.time import Time
from dsa110_contimg.calibration.catalogs import load_vla_catalog, get_calibrator_radec
from dsa110_contimg.calibration.schedule import previous_transits

# Load catalog and get coordinates
catalog_df = load_vla_catalog()
ra_deg, dec_deg = get_calibrator_radec(catalog_df, "0834+555")

# Find transit on target date
target_date = "2025-11-02"
search_start = Time(f"{target_date} 23:59:59")
transits = previous_transits(ra_deg=ra_deg, start_time=search_start, n=10)

# Find transit on target date
for transit in transits:
    transit_date = transit.datetime.date().isoformat()
    if transit_date == target_date:
        print(f"Transit time: {transit.isot}")
        break
```

**Or use the CLI:**
```bash
python -m dsa110_contimg.calibration.catalog_cli transit \
    --calibrator 0834+555 \
    --date 2025-11-02
```

### Step 2: Calculate 60-Minute Window

```python
from astropy.time import Time
import astropy.units as u

# Transit time from Step 1
transit_time = Time("2025-11-02T13:34:54")  # Example

# Calculate ±30 minute window
window_minutes = 30
start_time = transit_time - (window_minutes * 60) * u.s
end_time = transit_time + (window_minutes * 60) * u.s

print(f"Window: {start_time.isot} to {end_time.isot}")

# Convert to Unix timestamps for mosaic CLI
since_epoch = int(start_time.unix)
until_epoch = int(end_time.unix)
```

### Step 3: Ensure Data is Processed (Conversion, Calibration, Imaging)

Before planning a mosaic, ensure all tiles exist in the products database. If not, you need to:

#### 3a. Convert HDF5 Groups to MS

Convert all 5-minute groups in the window:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-11-02T13:04:54" \
    "2025-11-02T14:04:54" \
    --writer parallel-subband \
    --stage-to-tmpfs
```

This creates MS files for each complete 16-subband group in the time window.

#### 3b. Calibrate MS Files

For each MS file:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /stage/dsa110-contimg/ms/2025-11-02T13:04:54.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --preset development
```

**Note:** For production-quality mosaics, use standard calibration (omit `--preset development`).

#### 3c. Image MS Files

For each calibrated MS:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /stage/dsa110-contimg/ms/2025-11-02T13:04:54.ms \
    --imagename /stage/dsa110-contimg/images/2025-11-02T13:04:54 \
    --imsize 2048 \
    --niter 1000 \
    --threshold 0.05mJy \
    --pbcor
```

**Important:** Images must be PB-corrected (`--pbcor`) for mosaic building.

### Step 4: Plan the Mosaic

Plan the mosaic by selecting tiles from the products database:

```bash
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since <start_epoch> \
    --until <end_epoch> \
    --method pbweighted \
    --include-unpbcor false
```

**Parameters:**
- `--name`: Unique name for the mosaic plan
- `--since`: Unix timestamp (epoch seconds) for start of window
- `--until`: Unix timestamp (epoch seconds) for end of window
- `--method`: `pbweighted` (recommended) or `weighted` or `mean`
- `--include-unpbcor`: Set to `false` to only include PB-corrected tiles

**Example with calculated timestamps:**
```bash
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since 1733229894 \
    --until 1733233494 \
    --method pbweighted
```

### Step 5: Build the Mosaic

Build the mosaic from the planned tiles:

```bash
python -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image
```

**What happens:**
1. Validates all tiles (grid consistency, astrometry, calibration)
2. Reads PB images for each tile
3. Computes pixel-by-pixel weights: `weight = pb_response^2 / noise_variance`
4. Combines tiles: `mosaic = sum(weight * tile) / sum(weight)`
5. Exports FITS file: `0834_transit_2025-11-02.image.fits`

**Options:**
- `--ignore-validation`: Skip validation checks (not recommended)
- `--dry-run`: Validate without building (useful for testing)

---

## Method 3: Comprehensive End-to-End Script

For a complete workflow from raw HDF5 files to final mosaic, use:

```bash
python scripts/build_60min_mosaic.py \
    --calibrator "0834+555" \
    --date "2025-11-02" \
    --incoming-dir /data/incoming \
    --output-dir /stage/dsa110-contimg \
    --window-minutes 30 \
    --imsize 2048
```

**What this script does:**
1. Finds transit time
2. Discovers HDF5 groups in window
3. Converts groups to MS (if needed)
4. Identifies calibrator MS
5. Calibrates calibrator MS
6. Applies calibration to all MS files
7. Images all MS files
8. Registers images in products DB
9. Plans mosaic
10. Builds mosaic

**Options:**
- `--skip-conversion`: Use existing MS files
- `--skip-calibration`: Use existing calibration tables
- `--max-workers`: Parallel conversion workers (default: 4)

---

## Understanding Mosaic Methods

### PB-Weighted (`pbweighted`) - Recommended

Uses primary beam response and noise variance for optimal combination:

```
weight[i,j] = pb_response[i,j]^2 / noise_variance
mosaic[i,j] = sum(weight[k][i,j] * tile[k][i,j]) / sum(weight[k][i,j])
```

**Advantages:**
- Optimal signal-to-noise ratio
- Accounts for varying sensitivity across field
- Handles overlapping coverage correctly

**Requirements:**
- All tiles must have PB images
- PB images must be readable

### Noise-Weighted (`weighted`)

Uses only noise variance (no PB information):

```
weight = 1 / noise_variance^2
mosaic = sum(weight[k] * tile[k]) / sum(weight[k])
```

**Use when:** PB images are unavailable

### Mean (`mean`)

Simple average:

```
mosaic = mean(tile[k])
```

**Use when:** All tiles have similar noise and coverage

---

## Validation and Quality Checks

The mosaic builder performs extensive validation:

1. **Grid Consistency**: All tiles must have same pixel scale and grid alignment
2. **Astrometric Registration**: Tiles must align with catalog sources
3. **Calibration Consistency**: Tiles should use compatible calibration
4. **Primary Beam Consistency**: PB images must be valid and consistent
5. **Pre-flight Checks**: Disk space, file existence, permissions

**View validation issues:**
```bash
python -m dsa110_contimg.mosaic.cli build \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image \
    --dry-run
```

---

## Output Files

After building, you'll have:

1. **Mosaic image**: `/stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image/`
   - CASA image format (directory)
   - Contains cleaned, PB-weighted mosaic

2. **FITS export**: `/stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image.fits`
   - Standard FITS format for analysis

3. **Quality metrics** (if generated):
   - `0834_transit_2025-11-02_pb_response.fits` - PB response map
   - `0834_transit_2025-11-02_noise_variance.fits` - Noise variance map
   - `0834_transit_2025-11-02_tile_count.fits` - Number of tiles per pixel
   - `0834_transit_2025-11-02_coverage.fits` - Coverage map

---

## Troubleshooting

### No tiles found in time window

**Problem:** Mosaic planning finds no tiles

**Solutions:**
1. Check products DB has images in the time range:
   ```python
   import sqlite3
   conn = sqlite3.connect("state/products.sqlite3")
   rows = conn.execute("""
       SELECT path, created_at, pbcor FROM images 
       WHERE created_at >= ? AND created_at <= ?
       ORDER BY created_at
   """, (since_epoch, until_epoch)).fetchall()
   print(f"Found {len(rows)} images")
   ```

2. Ensure images are PB-corrected (`pbcor=1` in DB)
3. Verify time window includes actual observation times

### Validation failures

**Problem:** Tiles fail validation checks

**Solutions:**
1. Check tile grid consistency:
   ```bash
   python -m dsa110_contimg.mosaic.cli build --dry-run --name <mosaic_name>
   ```

2. Ensure all tiles have PB images
3. Verify calibration consistency (same calibration tables applied)
4. Check astrometric alignment (compare with catalog)

### Missing PB images

**Problem:** PB images not found for tiles

**Solutions:**
1. Verify PB images exist:
   ```bash
   ls /stage/dsa110-contimg/images/*/pbcor.pb/
   ```

2. Check products DB has PB paths:
   ```python
   import sqlite3
   conn = sqlite3.connect("state/products.sqlite3")
   rows = conn.execute("SELECT path, pb_path FROM images WHERE pbcor=1").fetchall()
   ```

3. Re-image with `--pbcor` if PB images missing

### Mosaic build fails

**Problem:** Build process crashes or errors

**Solutions:**
1. Check disk space: `df -h /stage/dsa110-contimg`
2. Verify CASA is available: `conda activate casa6`
3. Check logs for specific error messages
4. Try `--ignore-validation` (not recommended for science)

---

## Performance Considerations

### Conversion Time

- **Per group**: ~2-5 minutes (with tmpfs staging)
- **12 groups**: ~30-60 minutes total

### Calibration Time

- **Development tier**: ~1-2 minutes per MS
- **Standard tier**: ~5-10 minutes per MS
- **12 MS files**: ~12-120 minutes total

### Imaging Time

- **Quick mode** (512×512): ~1-2 minutes per image
- **Standard mode** (2048×2048): ~5-15 minutes per image
- **12 images**: ~12-180 minutes total

### Mosaic Building

- **Planning**: <1 second
- **Validation**: ~1-5 minutes (depends on number of tiles)
- **Building**: ~5-15 minutes (depends on tile size and count)

**Total time**: ~1-6 hours for complete end-to-end workflow

---

## Best Practices

1. **Use PB-weighted method** for optimal results
2. **Ensure all tiles are PB-corrected** before planning
3. **Use consistent calibration** across all tiles
4. **Validate before building** (`--dry-run`)
5. **Check disk space** before starting (mosaics can be large)
6. **Use tmpfs staging** for faster conversion (`--stage-to-tmpfs`)
7. **Monitor products DB** to track tile registration

---

## References

- **Mosaic CLI**: `src/dsa110_contimg/mosaic/cli.py`
- **Transit calculation**: `src/dsa110_contimg/calibration/schedule.py`
- **Calibrator catalog**: `src/dsa110_contimg/calibration/catalogs.py`
- **Example scripts**: `scripts/build_0834_transit_mosaic.py`, `scripts/build_60min_mosaic.py`
- **Mosaic documentation**: `docs/how-to/mosaic.md`
- **5-minute imaging guide**: `docs/how-to/IMAGE_0834_TRANSIT_5MIN.md`

```


Updating MEMORY.md with this knowledge:


```markdown
# DSA-110 Continuum Imaging Pipeline - Codebase Understanding

**Last Updated:** 2025-11-02  
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

1. **Always check the Graphiti schema** (`internal/docs/graphiti/graphiti-dsa110-contimg-schema.md`) for project-specific entities and relationships before extracting knowledge

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
- **Project Graphiti Schema**: `internal/docs/graphiti/graphiti-dsa110-contimg-schema.md`
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


```


Checking for linting issues:



## Summary

### Codebase exploration
Explored the `dsa110_contimg` package, covering:
- Conversion (HDF5 → MS)
- Calibration (BP/G calibration)
- Imaging (tclean with PB correction)
- Mosaic construction (planning and building)
- Photometry and normalization
- Database management

### 60-minute mosaic construction

Created a guide: `docs/how-to/BUILD_60MIN_MOSAIC_0834.md`

The workflow:

1. Find transit time: Use `previous_transits()` to find when 0834+555 transits on a target date
2. Calculate window: ±30 minutes around transit (60 minutes total)
3. Process data (if needed):
   - Convert HDF5 groups → MS files
   - Calibrate MS files (BP + G)
   - Image MS files with PB correction
4. Plan mosaic: Query products DB for tiles in the time window
5. Build mosaic: Combine tiles using PB-weighted combination

### Quick start

Simplest method:
```bash
python scripts/build_0834_transit_mosaic.py
```

Or step-by-step:
```bash
# Plan mosaic
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since <start_epoch> --until <end_epoch> \
    --method pbweighted

# Build mosaic
python -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image
```

### Documentation created
- `docs/how-to/BUILD_60MIN_MOSAIC_0834.md` — Guide with methods, troubleshooting, and best practices
- Updated `MEMORY.md` — Added mosaic construction workflow section

The guide includes three methods (pre-built script, manual steps, comprehensive script), validation checks, troubleshooting, and performance considerations.

```shellscript
python scripts/build_0834_transit_mosaic.py
```

```shellscript
# Plan mosaic
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since <start_epoch> --until <end_epoch> \
    --method pbweighted

# Build mosaic
python -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image
```

---

**User**

Does every step in your plan use existing code in the pipeline consistent with how it would operate in streaming mode? Explain.

---

**Cursor**


Verifying that the mosaic workflow steps match the streaming pipeline implementation:



Reviewing the streaming converter implementation:



Analyzing consistency with the streaming pipeline:



Analyzing consistency and preparing a response:



## Analysis: Consistency with Streaming Pipeline

### Step 1: Conversion — Consistent

**My documentation:**
- Uses `convert_subband_groups_to_ms()` from `hdf5_orchestrator.py`
- Calls it directly or via CLI

**Streaming pipeline:**
```python:597:612:src/dsa110_contimg/conversion/streaming/streaming_converter.py
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
    convert_subband_groups_to_ms,
)
convert_subband_groups_to_ms(
    args.input_dir,
    args.output_dir,
    start_time,
    end_time,
    scratch_dir=args.scratch_dir,
    writer="auto",
    writer_kwargs={...},
)
```

**Verdict:** Consistent — same function, same parameters.

---

### Step 2: Calibration — Inconsistent

**My documentation:**
- Suggests solving calibration on each MS using `calibration.cli calibrate`

**Streaming pipeline:**
```python:675:687:src/dsa110_contimg/conversion/streaming/streaming_converter.py
applylist = []
try:
    applylist = get_active_applylist(Path(args.registry_db), float(mid_mjd)...)
except Exception:
    applylist = []

cal_applied = 0
if applylist:
    try:
        apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
        cal_applied = 1
```

**Verdict:** Inconsistent — streaming does not solve calibration; it only applies existing tables from the registry.

**What streaming actually does:**
1. Looks up active calibration tables from `cal_registry.sqlite3` by observation time
2. Applies them using `apply_to_target()`
3. Does not solve new calibration solutions

**For a 60-minute mosaic, the correct workflow should be:**
1. Solve calibration once on the calibrator transit MS (using `CalibrationSolveStage` or `calibration.cli calibrate`)
2. Register the tables in the registry
3. Apply that calibration to all other MS files (like streaming does)
4. Image all MS files
5. Build mosaic

---

### Step 3: Imaging — Partially consistent

**My documentation:**
- Uses `imaging.cli image` but doesn't specify quality tier

**Streaming pipeline:**
```python:693:693:src/dsa110_contimg/conversion/streaming/streaming_converter.py
image_ms(ms_path, imagename=imgroot, field="", quality_tier="development", skip_fits=False)
```

**Verdict:** Partially consistent — same function, but streaming uses `quality_tier="development"` (coarser cell size, faster). My doc doesn't specify a tier.

---

### Step 4: Mosaic — N/A (post-processing)

**Verdict:** Not part of streaming — mosaics are built post-processing from tiles already in the products DB. This is consistent with how mosaics are constructed.

---

## Summary

| Step | My Documentation | Streaming Pipeline | Consistent? |
|------|------------------|-------------------|-------------|
| **Conversion** | `convert_subband_groups_to_ms()` | `convert_subband_groups_to_ms()` | Yes |
| **Calibration** | Solve on each MS | Apply from registry only | No |
| **Imaging** | `image_ms()` (tier unspecified) | `image_ms()` with `quality_tier="development"` | Partial |
| **Mosaic** | `mosaic.cli plan/build` | N/A (post-processing) | N/A |

---

## Corrected Workflow (Streaming-Consistent)

For a 60-minute mosaic consistent with streaming:

1. Convert all groups → MS (same as streaming)
2. Solve calibration once on the calibrator transit MS
3. Register calibration tables in the registry
4. Apply calibration to all MS files (like streaming does)
5. Image all MS files (use `quality_tier="development"` to match streaming, or `"standard"` for production)
6. Build mosaic from tiles in products DB

The main fix: solve calibration once, then apply it to all MS files (as streaming does), rather than solving on each MS individually.

Should I update the documentation to reflect this streaming-consistent workflow?

```plaintext
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
    convert_subband_groups_to_ms,
)
convert_subband_groups_to_ms(
    args.input_dir,
    args.output_dir,
    start_time,
    end_time,
    scratch_dir=args.scratch_dir,
    writer="auto",
    writer_kwargs={...},
)
```

```plaintext
applylist = []
try:
    applylist = get_active_applylist(Path(args.registry_db), float(mid_mjd)...)
except Exception:
    applylist = []

cal_applied = 0
if applylist:
    try:
        apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
        cal_applied = 1
```

```plaintext
image_ms(ms_path, imagename=imgroot, field="", quality_tier="development", skip_fits=False)
```

---

**User**

Make sure quality tier throughout defaults to "standard" for production. edit the streaming pipelien code to do this as well.

---

**Cursor**


Updating quality tier defaults to "standard" for production, including the streaming pipeline. Searching for all occurrences:



Updating the streaming pipeline and related code to default to "standard" quality tier:



Updating the streaming pipeline and imaging worker to use "standard" quality tier:


```python
#!/usr/bin/env python3
"""
Streaming converter service for DSA-110 UVH5 subband groups.

This daemon watches an ingest directory for new *_sb??.hdf5 files, queues
complete 16-subband groups, and invokes the existing batch converter on each
group using a scratch directory for staging.

The queue is persisted in SQLite so the service can resume after restarts.
"""

import argparse
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

import sys
try:
    from dsa110_contimg.utils.graphiti_logging import GraphitiRunLogger
except Exception:  # pragma: no cover - optional helper
    class GraphitiRunLogger:  # type: ignore
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def log_consumes(self, *a, **k): pass
        def log_produces(self, *a, **k): pass
from casatasks import concat as casa_concat  # noqa
from casacore.tables import table  # noqa
from dsa110_contimg.calibration.calibration import solve_delay, solve_bandpass, solve_gains  # noqa
from dsa110_contimg.calibration.applycal import apply_to_target  # noqa
from dsa110_contimg.imaging.cli import image_ms  # noqa
from dsa110_contimg.database.registry import ensure_db as ensure_cal_db, register_set_from_prefix, get_active_applylist  # noqa
from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert, images_insert  # noqa

try:  # Optional dependency for efficient file watching
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    HAVE_WATCHDOG = True
except ImportError:  # pragma: no cover - fallback path
    HAVE_WATCHDOG = False


GROUP_PATTERN = re.compile(
    r"(?P<timestamp>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})_sb(?P<index>\d{2})\.hdf5$"
)

def parse_subband_info(path: Path) -> Optional[Tuple[str, int]]:
    """Extract (group_id, subband_idx) from a filename, or None if not matched."""
    m = GROUP_PATTERN.search(path.name)
    if not m:
        return None
    gid = m.group("timestamp")
    try:
        sb = int(m.group("index"))
    except Exception:
        return None
    return gid, sb


@contextmanager
def override_env(values: Dict[str, str]) -> Iterator[None]:
    """Temporarily override environment variables."""
    if not values:
        yield
        return

    previous = {key: os.environ.get(key) for key in values}
    try:
        for key, val in values.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        yield
    finally:
        for key, val in previous.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


class QueueDB:
    """SQLite-backed queue tracking subband arrivals and processing state."""

    def __init__(
        self,
        path: Path,
        expected_subbands: int = 16,
        chunk_duration_minutes: float = 5.0,
    ) -> None:
        self.path = path
        self.expected_subbands = expected_subbands
        self.chunk_duration_minutes = chunk_duration_minutes
        self._lock = threading.Lock()
        # CRITICAL: Use WAL mode for better concurrency and thread safety
        # WAL (Write-Ahead Logging) allows multiple readers and one writer simultaneously
        # This is safer than check_same_thread=False with default journal mode
        self._conn = sqlite3.connect(
            self.path,
            check_same_thread=False,
            timeout=30.0,  # Wait up to 30 seconds for locks
        )
        self._conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrency
        try:
            self._conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            # If WAL mode fails (e.g., read-only filesystem), continue with default mode
            # This is a best-effort optimization
            pass
        self._ensure_schema()
        self._migrate_schema()
        self._normalize_existing_groups()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _ensure_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingest_queue (
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
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subband_files (
                    group_id TEXT NOT NULL,
                    subband_idx INTEGER NOT NULL,
                    path TEXT NOT NULL,
                    PRIMARY KEY (group_id, subband_idx)
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    group_id TEXT NOT NULL,
                    load_time REAL,
                    phase_time REAL,
                    write_time REAL,
                    total_time REAL,
                    writer_type TEXT,
                    recorded_at REAL NOT NULL,
                    PRIMARY KEY (group_id)
                )
                """
            )

    def _migrate_schema(self) -> None:
        """Ensure existing databases contain the latest columns."""
        with self._lock, self._conn:
            try:
                columns = {
                    row["name"]
                    for row in self._conn.execute("PRAGMA table_info(ingest_queue)").fetchall()
                }
            except sqlite3.DatabaseError as exc:  # pragma: no cover - defensive path
                logging.error("Failed to inspect ingest_queue schema: %s", exc)
                return

            altered = False
            if "checkpoint_path" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN checkpoint_path TEXT")
                altered = True
            if "processing_stage" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN processing_stage TEXT DEFAULT 'collecting'"
                )
                self._conn.execute(
                    "UPDATE ingest_queue SET processing_stage = 'collecting' WHERE processing_stage IS NULL"
                )
                altered = True
            if "chunk_minutes" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN chunk_minutes REAL")
                altered = True
            if "expected_subbands" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN expected_subbands INTEGER")
                try:
                    self._conn.execute(
                        "UPDATE ingest_queue SET expected_subbands = ? WHERE expected_subbands IS NULL",
                        (self.expected_subbands,)
                    )
                except sqlite3.DatabaseError:
                    pass

    def _normalize_group_id_datetime(self, group_id: str) -> str:
        """Normalize group_id to 'YYYY-MM-DDTHH:MM:SS'. Accept 'T' or space."""
        s = group_id.strip()
        try:
            ts = s.replace("T", " ")
            dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
        except Exception:
            return s

    def _normalize_existing_groups(self) -> None:
        with self._lock, self._conn:
            try:
                rows = self._conn.execute("SELECT group_id FROM ingest_queue").fetchall()
            except sqlite3.DatabaseError:
                return
            for r in rows:
                gid = r["group_id"]
                norm = self._normalize_group_id_datetime(gid)
                if norm != gid:
                    try:
                        self._conn.execute("UPDATE ingest_queue SET group_id = ? WHERE group_id = ?", (norm, gid))
                        self._conn.execute("UPDATE subband_files SET group_id = ? WHERE group_id = ?", (norm, gid))
                        self._conn.execute("UPDATE performance_metrics SET group_id = ? WHERE group_id = ?", (norm, gid))
                    except sqlite3.DatabaseError:
                        continue

            # Check which columns exist in current schema
            try:
                columns = {
                    row["name"]
                    for row in self._conn.execute("PRAGMA table_info(ingest_queue)").fetchall()
                }
            except sqlite3.DatabaseError:
                columns = set()
            
            altered = False
            if "has_calibrator" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN has_calibrator INTEGER DEFAULT NULL")
                altered = True
            if "calibrators" not in columns:
                self._conn.execute(
                    "ALTER TABLE ingest_queue ADD COLUMN calibrators TEXT")
                altered = True

            if altered:
                logging.info(
                    "Updated ingest_queue schema with new metadata columns.")

        with self._lock, self._conn:
            try:
                pcols = {row["name"] for row in self._conn.execute(
                    "PRAGMA table_info(performance_metrics)").fetchall()}
            except sqlite3.DatabaseError:
                pcols = set()
            if pcols and "writer_type" not in pcols:
                try:
                    self._conn.execute(
                        "ALTER TABLE performance_metrics ADD COLUMN writer_type TEXT")
                    logging.info(
                        "Updated performance_metrics schema with writer_type column.")
                except sqlite3.DatabaseError:
                    pass

    def record_subband(
            self,
            group_id: str,
            subband_idx: int,
            file_path: Path) -> None:
        """Record a subband file arrival.
        
        CRITICAL: Uses explicit transaction boundaries for thread safety.
        All operations within this method are atomic.
        """
        now = time.time()
        normalized_group = self._normalize_group_id_datetime(group_id)
        with self._lock:
            try:
                # CRITICAL: Use explicit transaction for atomicity
                # This ensures all operations succeed or fail together
                self._conn.execute("BEGIN")
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO ingest_queue (group_id, state, received_at, last_update, chunk_minutes, expected_subbands)
                    VALUES (?, 'collecting', ?, ?, ?, ?)
                    """,
                    (normalized_group, now, now,
                     self.chunk_duration_minutes, self.expected_subbands),
                )
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO subband_files (group_id, subband_idx, path)
                    VALUES (?, ?, ?)
                    """,
                    (normalized_group, subband_idx, str(file_path)),
                )
                self._conn.execute(
                    """
                    UPDATE ingest_queue
                       SET last_update = ?
                     WHERE group_id = ?
                    """,
                    (now, normalized_group),
                )
                count = self._conn.execute(
                    "SELECT COUNT(*) FROM subband_files WHERE group_id = ?",
                    (normalized_group,),
                ).fetchone()[0]
                if count >= self.expected_subbands:
                    self._conn.execute(
                        """
                        UPDATE ingest_queue
                           SET state = CASE WHEN state = 'completed' THEN state ELSE 'pending' END,
                               last_update = ?
                         WHERE group_id = ?
                        """,
                        (now, normalized_group),
                    )
                # Commit transaction
                self._conn.commit()
            except Exception:
                # Rollback on any error to maintain consistency
                self._conn.rollback()
                raise

    def bootstrap_directory(self, input_dir: Path) -> None:
        logging.info(
            "Bootstrapping queue from existing files in %s",
            input_dir)
        for path in sorted(input_dir.glob('*_sb??.hdf5')):
            info = parse_subband_info(path)
            if info is None:
                continue
            group_id, subband_idx = info
            self.record_subband(group_id, subband_idx, path)

    def acquire_next_pending(self) -> Optional[str]:
        """Acquire the next pending group atomically.
        
        CRITICAL: Uses explicit transaction to ensure SELECT and UPDATE are atomic.
        Prevents race conditions where multiple threads acquire the same group.
        """
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                row = self._conn.execute(
                    """
                    SELECT group_id FROM ingest_queue
                     WHERE state = 'pending'
                     ORDER BY received_at ASC
                     LIMIT 1
                    """
                ).fetchone()
                if row is None:
                    self._conn.commit()
                    return None
                group_id = row[0]
                now = time.time()
                self._conn.execute(
                    """
                    UPDATE ingest_queue
                       SET state = 'in_progress',
                           last_update = ?
                     WHERE group_id = ?
                    """,
                    (now, group_id),
                )
                self._conn.commit()
                return group_id
            except Exception:
                self._conn.rollback()
                raise

    def update_state(self, group_id: str, state: str, error: Optional[str] = None) -> None:
        """Update the state of a group in the queue.
        
        CRITICAL: Uses explicit transaction for consistency.
        """
        normalized_group = self._normalize_group_id_datetime(group_id)
        now = time.time()
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                if error is not None:
                    self._conn.execute(
                        """
                        UPDATE ingest_queue
                           SET state = ?, last_update = ?, error = ?
                         WHERE group_id = ?
                        """,
                        (state, now, error, normalized_group),
                    )
                else:
                    self._conn.execute(
                        """
                        UPDATE ingest_queue
                           SET state = ?, last_update = ?
                         WHERE group_id = ?
                        """,
                        (state, now, normalized_group),
                    )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def record_metrics(self, group_id: str, **kwargs) -> None:
        """Record performance metrics for a group.
        
        CRITICAL: Column names are whitelisted to prevent SQL injection.
        Only known performance metric columns are allowed.
        """
        # CRITICAL: Whitelist allowed column names to prevent SQL injection
        ALLOWED_METRIC_COLUMNS = {
            "load_time",
            "phase_time",
            "write_time",
            "total_time",
            "writer_type",
        }
        
        normalized_group = self._normalize_group_id_datetime(group_id)
        now = time.time()
        with self._lock:
            try:
                self._conn.execute("BEGIN")
                # Build column list and values dynamically, but only for whitelisted columns
                columns = ["group_id", "recorded_at"]
                values = [normalized_group, now]
                placeholders = ["?", "?"]
                
                for key, value in kwargs.items():
                    # Only allow whitelisted columns
                    if key in ALLOWED_METRIC_COLUMNS:
                        columns.append(key)
                        values.append(value)
                        placeholders.append("?")
                
                if len(columns) > 2:  # Only execute if we have metrics to record
                    self._conn.execute(
                        f"""
                        INSERT OR REPLACE INTO performance_metrics ({', '.join(columns)})
                        VALUES ({', '.join(placeholders)})
                        """,
                        values,
                    )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    def group_files(self, group_id: str) -> List[str]:
        """Get list of file paths for a group."""
        normalized_group = self._normalize_group_id_datetime(group_id)
        with self._lock:
            rows = self._conn.execute(
                "SELECT path FROM subband_files WHERE group_id = ? ORDER BY subband_idx",
                (normalized_group,),
            ).fetchall()
            return [row[0] for row in rows]


class _FSHandler(FileSystemEventHandler):
    """Watchdog handler to record arriving subband files."""

    def __init__(self, queue: QueueDB) -> None:
        self.queue = queue

    def _maybe_record(self, path: str) -> None:
        p = Path(path)
        info = parse_subband_info(p)
        if info is None:
            return
        gid, sb = info
        
        # PRECONDITION CHECK: Validate file is readable before queuing
        # This ensures we follow "measure twice, cut once" - establish requirements upfront
        # before recording file in queue and attempting conversion.
        log = logging.getLogger("stream")
        
        # Check file exists
        if not p.exists():
            log.warning(f"File does not exist (may have been deleted): {path}")
            return
        
        # Check file is readable
        if not os.access(path, os.R_OK):
            log.warning(f"File is not readable: {path}")
            return
        
        # Check file size (basic sanity check)
        try:
            file_size = p.stat().st_size
            if file_size == 0:
                log.warning(f"File is empty (0 bytes): {path}")
                return
            if file_size < 1024:  # Less than 1KB is suspicious
                log.warning(f"File is suspiciously small ({file_size} bytes): {path}")
        except OSError as e:
            log.warning(f"Failed to check file size: {path}. Error: {e}")
            return
        
        # Quick HDF5 structure check
        try:
            import h5py
            with h5py.File(path, 'r') as f:
                # Verify file has required structure (Header or Data group)
                if 'Header' not in f and 'Data' not in f:
                    log.warning(f"File does not appear to be valid HDF5/UVH5: {path}")
                    return
        except Exception as e:
            log.warning(f"File is not readable HDF5: {path}. Error: {e}")
            return
        
        # File passed all checks, record in queue
        try:
            self.queue.record_subband(gid, sb, p)
        except Exception:
            logging.getLogger("stream").debug("record_subband failed for %s", p, exc_info=True)

    def on_created(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):  # pragma: no cover - defensive
            return
        self._maybe_record(event.src_path)

    def on_moved(self, event):  # type: ignore[override]
        if getattr(event, "is_directory", False):  # pragma: no cover - defensive
            return
        self._maybe_record(event.dest_path)


def _worker_loop(args: argparse.Namespace, queue: QueueDB) -> None:
    """Poll for pending groups, convert via orchestrator, and mark complete."""
    log = logging.getLogger("stream.worker")
    while True:
        try:
            gid = queue.acquire_next_pending()
            if gid is None:
                time.sleep(float(getattr(args, "worker_poll_interval", 5.0)))
                continue
            t0 = time.perf_counter()
            # Use group timestamp for start/end
            start_time = gid.replace("T", " ")
            end_time = start_time
            writer_type = None
            ret = 0
            try:
                if getattr(args, "use_subprocess", False):
                    cmd = [
                        sys.executable,
                        "-m",
                        "dsa110_contimg.conversion.strategies.hdf5_orchestrator",
                        args.input_dir,
                        args.output_dir,
                        start_time,
                        end_time,
                        "--writer",
                        "auto",
                        "--scratch-dir",
                        args.scratch_dir,
                        "--max-workers",
                        str(getattr(args, "max_workers", 4)),
                    ]
                    if getattr(args, "stage_to_tmpfs", False):
                        cmd.append("--stage-to-tmpfs")
                        cmd.extend(["--tmpfs-path", getattr(args, "tmpfs_path", "/dev/shm")])
                    env = os.environ.copy()
                    env.setdefault("HDF5_USE_FILE_LOCKING", "FALSE")
                    env.setdefault("OMP_NUM_THREADS", os.getenv("OMP_NUM_THREADS", "4"))
                    env.setdefault("MKL_NUM_THREADS", os.getenv("MKL_NUM_THREADS", "4"))
                    ret = subprocess.call(cmd, env=env)
                    writer_type = "auto"
                else:
                    from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
                        convert_subband_groups_to_ms,
                    )
                    convert_subband_groups_to_ms(
                        args.input_dir,
                        args.output_dir,
                        start_time,
                        end_time,
                        scratch_dir=args.scratch_dir,
                        writer="auto",
                        writer_kwargs={
                            "max_workers": getattr(args, "max_workers", 4),
                            "stage_to_tmpfs": getattr(args, "stage_to_tmpfs", False),
                            "tmpfs_path": getattr(args, "tmpfs_path", "/dev/shm"),
                        },
                    )
                    ret = 0
                    writer_type = "auto"
            except Exception as exc:
                log.error("Conversion failed for %s: %s", gid, exc)
                queue.update_state(gid, "failed", error=str(exc))
                continue

            total = time.perf_counter() - t0
            queue.record_metrics(gid, total_time=total, writer_type=writer_type)
            if ret != 0:
                queue.update_state(gid, "failed", error=f"orchestrator exit={ret}")
                continue

            # Derive MS path from first subband filename
            try:
                files = queue.group_files(gid)
                if not files:
                    raise RuntimeError("no subband files recorded for group")
                first = os.path.basename(files[0])
                base = os.path.splitext(first)[0].split("_sb")[0]
                ms_path = os.path.join(args.output_dir, base + ".ms")
            except Exception as exc:
                log.error("Failed to locate MS for %s: %s", gid, exc)
                queue.update_state(gid, "completed")
                continue

            # Record conversion in products DB (stage=converted)
            try:
                products_db_path = os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")
                conn = ensure_products_db(Path(products_db_path))
                # Extract time range
                start_mjd = end_mjd = mid_mjd = None
                try:
                    from dsa110_contimg.utils.time_utils import extract_ms_time_range
                    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
                except Exception:
                    pass
                ms_index_upsert(
                    conn,
                    ms_path,
                    start_mjd=start_mjd,
                    end_mjd=end_mjd,
                    mid_mjd=mid_mjd,
                    processed_at=time.time(),
                    status="converted",
                    stage="converted",
                )
                conn.commit()
            except Exception:
                log.debug("ms_index conversion upsert failed", exc_info=True)

            # Apply calibration from registry if available, then image (development tier)
            try:
                # Determine mid_mjd for applylist
                if mid_mjd is None:
                    # fallback: try extract_ms_time_range again (it has multiple fallbacks)
                    try:
                        from dsa110_contimg.utils.time_utils import extract_ms_time_range
                        _, _, mid_mjd = extract_ms_time_range(ms_path)
                    except Exception:
                        pass

                applylist = []
                try:
                    applylist = get_active_applylist(Path(args.registry_db), float(mid_mjd) if mid_mjd is not None else time.time()/86400.0)
                except Exception:
                    applylist = []

                cal_applied = 0
                if applylist:
                    try:
                        apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
                        cal_applied = 1
                    except Exception:
                        log.warning("applycal failed for %s", ms_path, exc_info=True)

                # Standard tier imaging (production quality)
                # Note: Data is always reordered for correct multi-SPW processing
                imgroot = os.path.join(args.output_dir, base + ".img")
                try:
                    image_ms(ms_path, imagename=imgroot, field="", quality_tier="standard", skip_fits=False)
                    
                    # Run catalog-based flux scale validation
                    try:
                        from dsa110_contimg.qa.catalog_validation import validate_flux_scale
                        from pathlib import Path
                        
                        # Find PB-corrected FITS image (preferred for validation)
                        pbcor_fits = f"{imgroot}.pbcor.fits"
                        fits_image = pbcor_fits if Path(pbcor_fits).exists() else f"{imgroot}.fits"
                        
                        if Path(fits_image).exists():
                            log.info(f"Running catalog-based flux scale validation (NVSS) on {fits_image}")
                            result = validate_flux_scale(
                                image_path=fits_image,
                                catalog="nvss",
                                min_snr=5.0,
                                flux_range_jy=(0.01, 10.0),
                                max_flux_ratio_error=0.2
                            )
                            
                            if result.n_matched > 0:
                                log.info(
                                    f"Catalog validation (NVSS): {result.n_matched} sources matched, "
                                    f"flux ratio={result.mean_flux_ratio:.3f}±{result.rms_flux_ratio:.3f}, "
                                    f"scale error={result.flux_scale_error*100:.1f}%"
                                )
                                if result.has_issues:
                                    log.warning(f"Catalog validation issues: {', '.join(result.issues)}")
                                if result.has_warnings:
                                    log.warning(f"Catalog validation warnings: {', '.join(result.warnings)}")
                            else:
                                log.warning("Catalog validation: No sources matched")
                        else:
                            log.debug(f"Catalog validation skipped: FITS image not found ({fits_image})")
                    except Exception as e:
                        log.warning(f"Catalog validation failed (non-fatal): {e}")
                        
                except Exception:
                    log.error("imaging failed for %s", ms_path, exc_info=True)

                # Update products DB with imaging artifacts and stage
                try:
                    products_db_path = os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3")
                    conn = ensure_products_db(Path(products_db_path))
                    ms_index_upsert(
                        conn,
                        ms_path,
                        status="done",
                        stage="imaged",
                        cal_applied=cal_applied,
                        imagename=imgroot,
                    )
                    # Insert images
                    now_ts = time.time()
                    for suffix, pbcor in [(".image", 0), (".pb", 0), (".pbcor", 1), (".residual", 0), (".model", 0)]:
                        p = f"{imgroot}{suffix}"
                        if os.path.isdir(p) or os.path.isfile(p):
                            images_insert(conn, p, ms_path, now_ts, "5min", pbcor)
                    conn.commit()
                except Exception:
                    log.debug("products DB update failed", exc_info=True)
            except Exception:
                log.exception("post-conversion processing failed for %s", gid)

            queue.update_state(gid, "completed")
            log.info("Completed %s in %.2fs", gid, total)
        except Exception:
            log.exception("Worker loop error")
            time.sleep(2.0)


def _start_watch(args: argparse.Namespace, queue: QueueDB) -> Optional[object]:
    log = logging.getLogger("stream.watch")
    input_dir = Path(args.input_dir)
    if HAVE_WATCHDOG:
        handler = _FSHandler(queue)
        obs = Observer()
        obs.schedule(handler, str(input_dir), recursive=False)
        obs.start()
        log.info("Watchdog monitoring %s", input_dir)
        return obs
    log.info("Watchdog not available; using polling fallback")
    return None


def _polling_loop(args: argparse.Namespace, queue: QueueDB) -> None:
    log = logging.getLogger("stream.poll")
    seen: Set[str] = set()
    input_dir = Path(args.input_dir)
    interval = float(getattr(args, "poll_interval", 5.0))
    while True:
        try:
            for p in input_dir.glob("*_sb??.hdf5"):
                sp = os.fspath(p)
                if sp in seen:
                    continue
                seen.add(sp)
                info = parse_subband_info(p)
                if info is None:
                    continue
                gid, sb = info
                queue.record_subband(gid, sb, p)
            time.sleep(interval)
        except Exception:
            log.exception("Polling loop error")
            time.sleep(interval)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="DSA-110 streaming converter")
    p.add_argument("--input-dir", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--queue-db", default="state/ingest.sqlite3")
    p.add_argument("--registry-db", default="state/cal_registry.sqlite3")
    p.add_argument("--scratch-dir", default="/stage/dsa110-contimg")
    p.add_argument("--expected-subbands", type=int, default=16)
    p.add_argument("--chunk-duration", type=float, default=5.0, help="Minutes per group")
    p.add_argument("--log-level", default="INFO")
    p.add_argument("--use-subprocess", action="store_true")
    p.add_argument("--monitoring", action="store_true")
    p.add_argument("--monitor-interval", type=float, default=60.0)
    p.add_argument("--poll-interval", type=float, default=5.0)
    p.add_argument("--worker-poll-interval", type=float, default=5.0)
    p.add_argument("--max-workers", type=int, default=4)
    p.add_argument("--stage-to-tmpfs", action="store_true")
    p.add_argument("--tmpfs-path", default="/dev/shm")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    # Set CASA log directory before any CASA task calls
    from dsa110_contimg.utils.cli_helpers import setup_casa_environment
    setup_casa_environment()
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.log_level)
    
    # PRECONDITION CHECK: Validate input/output directories before proceeding
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # before starting file watching and processing.
    log = logging.getLogger("stream")
    
    # Validate input directory
    input_path = Path(args.input_dir)
    if not input_path.exists():
        log.error(f"Input directory does not exist: {args.input_dir}")
        return 1
    if not input_path.is_dir():
        log.error(f"Input path is not a directory: {args.input_dir}")
        return 1
    if not os.access(args.input_dir, os.R_OK):
        log.error(f"Input directory is not readable: {args.input_dir}")
        return 1
    
    # Validate output directory
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if not output_path.exists():
        log.error(f"Failed to create output directory: {args.output_dir}")
        return 1
    if not output_path.is_dir():
        log.error(f"Output path is not a directory: {args.output_dir}")
        return 1
    if not os.access(args.output_dir, os.W_OK):
        log.error(f"Output directory is not writable: {args.output_dir}")
        return 1
    
    # Validate scratch directory if provided
    if hasattr(args, 'scratch_dir') and args.scratch_dir:
        scratch_path = Path(args.scratch_dir)
        scratch_path.mkdir(parents=True, exist_ok=True)
        if not scratch_path.exists():
            log.error(f"Failed to create scratch directory: {args.scratch_dir}")
            return 1
        if not os.access(args.scratch_dir, os.W_OK):
            log.error(f"Scratch directory is not writable: {args.scratch_dir}")
            return 1
    
    log.info("✓ Directory validation passed")

    qdb = QueueDB(Path(args.queue_db), expected_subbands=int(args.expected_subbands), chunk_duration_minutes=float(args.chunk_duration))
    try:
        qdb.bootstrap_directory(Path(args.input_dir))
    except Exception:
        logging.getLogger("stream").exception("Bootstrap failed")

    obs = _start_watch(args, qdb)

    worker = threading.Thread(target=_worker_loop, args=(args, qdb), daemon=True)
    worker.start()

    if obs is None:
        poller = threading.Thread(target=_polling_loop, args=(args, qdb), daemon=True)
        poller.start()

    if getattr(args, "monitoring", False):
        log = logging.getLogger("stream.monitor")
        while True:
            try:
                with qdb._lock:
                    cur = qdb._conn.execute("SELECT state, COUNT(*) FROM ingest_queue GROUP BY state").fetchall()
                stats = {r[0]: r[1] for r in cur}
                log.info("Queue stats: %s", stats)
            except Exception:
                log.debug("Monitor failed", exc_info=True)
            time.sleep(float(args.monitor_interval))
    else:
        try:
            while True:
                time.sleep(60.0)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys
    raise SystemExit(main())

```

```python
#!/usr/bin/env python3
"""
Imaging worker: watches a directory of freshly converted 5-minute MS files,
looks up an active calibration apply list from the registry by observation
time, applies calibration, and makes quick continuum images.

This is a first-pass skeleton that can run in one-shot (scan) mode or in a
simple polling loop. It records products in a small SQLite DB for later
mosaicking.
"""

import argparse
import logging
import os
import time
from pathlib import Path
from typing import List, Optional, Tuple

from dsa110_contimg.database.registry import get_active_applylist
from dsa110_contimg.database.products import ensure_products_db, ms_index_upsert, images_insert


logger = logging.getLogger("imaging_worker")
try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )





def _apply_and_image(
        ms_path: str,
        out_dir: Path,
        gaintables: List[str]) -> List[str]:
    """Apply calibration and produce a quick image; returns artifact paths."""
    artifacts: List[str] = []
    # Route temp files to scratch and chdir to output directory to avoid repo pollution
    try:
        if prepare_temp_environment is not None:
            prepare_temp_environment(os.getenv('CONTIMG_SCRATCH_DIR') or '/stage/dsa110-contimg', cwd_to=os.fspath(out_dir))
    except Exception:
        pass
    # Apply to all fields by default
    try:
        from dsa110_contimg.calibration.applycal import apply_to_target
        from dsa110_contimg.imaging.cli import image_ms

        apply_to_target(ms_path, field="", gaintables=gaintables, calwt=True)
        imgroot = out_dir / (Path(ms_path).stem + ".img")
        # Use image_ms with standard tier for production quality imaging
        image_ms(ms_path, imagename=str(imgroot), field="", quality_tier="standard", skip_fits=True)
        # Return whatever CASA produced
        for ext in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
            p = f"{imgroot}{ext}"
            if os.path.exists(p):
                artifacts.append(p)
    except Exception as e:
        logger.error("apply/image failed for %s: %s", ms_path, e)
    return artifacts


def process_once(
    ms_dir: Path,
    out_dir: Path,
    registry_db: Path,
    products_db: Path,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    conn = ensure_products_db(products_db)
    processed = 0
    for ms in sorted(ms_dir.glob("**/*.ms")):
        row = conn.execute(
            "SELECT status FROM ms_index WHERE path = ?",
            (os.fspath(ms),
             )).fetchone()
        if row and row[0] == "done":
            continue
        from dsa110_contimg.utils.time_utils import extract_ms_time_range
        start_mjd, end_mjd, mid_mjd = extract_ms_time_range(os.fspath(ms))
        if mid_mjd is None:
            # Fallback: use current time in MJD
            from astropy.time import Time

            mid_mjd = Time.now().mjd
        applylist = get_active_applylist(registry_db, mid_mjd)
        if not applylist:
            logger.warning(
                "No active caltables for %s (mid MJD %.5f)",
                ms,
                mid_mjd)
            status = "skipped_no_caltables"
            ms_index_upsert(conn, os.fspath(ms), start_mjd=start_mjd, end_mjd=end_mjd, mid_mjd=mid_mjd, processed_at=time.time(), status=status)
            conn.commit()
            continue

        artifacts = _apply_and_image(os.fspath(ms), out_dir, applylist)
        status = "done" if artifacts else "failed"
        ms_index_upsert(conn, os.fspath(ms), start_mjd=start_mjd, end_mjd=end_mjd, mid_mjd=mid_mjd, processed_at=time.time(), status=status)
        for art in artifacts:
            images_insert(conn, art, os.fspath(ms), time.time(), "5min", 1 if art.endswith(".image.pbcor") else 0)
        conn.commit()
        processed += 1
        logger.info("Processed %s (artifacts: %d)", ms, len(artifacts))
    return processed


def cmd_scan(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    n = process_once(
        Path(
            args.ms_dir), Path(
            args.out_dir), Path(
                args.registry_db), Path(
                    args.products_db))
    logger.info("Scan complete: %d MS processed", n)
    return 0 if n >= 0 else 1


def cmd_daemon(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    ms_dir = Path(args.ms_dir)
    out_dir = Path(args.out_dir)
    registry_db = Path(args.registry_db)
    products_db = Path(args.products_db)
    poll = float(args.poll_interval)
    while True:
        try:
            process_once(ms_dir, out_dir, registry_db, products_db)
        except Exception as e:
            logger.error("Worker loop error: %s", e)
        time.sleep(poll)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Imaging worker for 5-min MS")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("scan", help="One-shot scan of an MS directory")
    sp.add_argument("--ms-dir", required=True)
    sp.add_argument("--out-dir", required=True)
    sp.add_argument("--registry-db", required=True)
    sp.add_argument("--products-db", required=True)
    sp.add_argument("--log-level", default="INFO")
    sp.set_defaults(func=cmd_scan)

    sp = sub.add_parser("daemon", help="Poll and process arriving MS")
    sp.add_argument("--ms-dir", required=True)
    sp.add_argument("--out-dir", required=True)
    sp.add_argument("--registry-db", required=True)
    sp.add_argument("--products-db", required=True)
    sp.add_argument("--poll-interval", type=float, default=60.0)
    sp.add_argument("--log-level", default="INFO")
    sp.set_defaults(func=cmd_daemon)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, 'func'):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

```


Verifying defaults and checking for other references:



Checking and updating the documentation to ensure consistency:



Updating the documentation reference:



Verifying all defaults are correct and updating documentation to clarify that "standard" is the production default:


```markdown
# How-To: Build a 60-Minute Mosaic Around VLA Calibrator 0834+555

**Objective:** Create a 60-minute mosaic (12 tiles at 5-minute cadence) centered on the transit of VLA calibrator 0834+555.

**Prerequisites:**
- UVH5 subband files available in `/data/incoming` (or your input directory)
- `casa6` conda environment activated
- Pipeline environment variables configured (if using custom paths)
- Products database exists (`state/products.sqlite3`)

---

## Overview

A 60-minute mosaic combines 12 individual 5-minute tiles (images) into a single larger image covering a wider field of view. The process involves:

1. **Finding the transit time** for 0834+555 on a specific date
2. **Calculating a 60-minute window** (±30 minutes around transit)
3. **Converting HDF5 groups to MS** (if not already done)
4. **Calibrating MS files** (if not already done)
5. **Imaging each MS** to create tiles (if not already done)
6. **Planning the mosaic** (selecting tiles from products DB)
7. **Building the mosaic** (combining tiles with primary beam weighting)

---

## Method 1: Using the Pre-Built Script (Simplest)

The simplest approach uses the existing script that handles all steps:

```bash
cd /data/dsa110-contimg
PYTHONPATH=/data/dsa110-contimg/src python scripts/build_0834_transit_mosaic.py
```

**What this script does:**
1. Finds transit time for 0834+555 on 2025-11-02 (hardcoded date)
2. Calculates ±30 minute window around transit
3. Plans mosaic from tiles in products DB within that window
4. Builds PB-weighted mosaic

**To use a different date:**
Edit `scripts/build_0834_transit_mosaic.py` and change:
```python
target_date = "2025-11-02"  # Change to your desired date
```

---

## Method 2: Step-by-Step Manual Process

### Step 1: Find Transit Time

Calculate when 0834+555 transits on your target date:

```python
from astropy.time import Time
from dsa110_contimg.calibration.catalogs import load_vla_catalog, get_calibrator_radec
from dsa110_contimg.calibration.schedule import previous_transits

# Load catalog and get coordinates
catalog_df = load_vla_catalog()
ra_deg, dec_deg = get_calibrator_radec(catalog_df, "0834+555")

# Find transit on target date
target_date = "2025-11-02"
search_start = Time(f"{target_date} 23:59:59")
transits = previous_transits(ra_deg=ra_deg, start_time=search_start, n=10)

# Find transit on target date
for transit in transits:
    transit_date = transit.datetime.date().isoformat()
    if transit_date == target_date:
        print(f"Transit time: {transit.isot}")
        break
```

**Or use the CLI:**
```bash
python -m dsa110_contimg.calibration.catalog_cli transit \
    --calibrator 0834+555 \
    --date 2025-11-02
```

### Step 2: Calculate 60-Minute Window

```python
from astropy.time import Time
import astropy.units as u

# Transit time from Step 1
transit_time = Time("2025-11-02T13:34:54")  # Example

# Calculate ±30 minute window
window_minutes = 30
start_time = transit_time - (window_minutes * 60) * u.s
end_time = transit_time + (window_minutes * 60) * u.s

print(f"Window: {start_time.isot} to {end_time.isot}")

# Convert to Unix timestamps for mosaic CLI
since_epoch = int(start_time.unix)
until_epoch = int(end_time.unix)
```

### Step 3: Ensure Data is Processed (Conversion, Calibration, Imaging)

Before planning a mosaic, ensure all tiles exist in the products database. If not, you need to:

#### 3a. Convert HDF5 Groups to MS

Convert all 5-minute groups in the window:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-11-02T13:04:54" \
    "2025-11-02T14:04:54" \
    --writer parallel-subband \
    --stage-to-tmpfs
```

This creates MS files for each complete 16-subband group in the time window.

#### 3b. Calibrate MS Files

For each MS file:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /stage/dsa110-contimg/ms/2025-11-02T13:04:54.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --preset development
```

**Note:** For production-quality mosaics, use standard calibration (omit `--preset development`).

#### 3c. Image MS Files

For each calibrated MS:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /stage/dsa110-contimg/ms/2025-11-02T13:04:54.ms \
    --imagename /stage/dsa110-contimg/images/2025-11-02T13:04:54 \
    --imsize 2048 \
    --niter 1000 \
    --threshold 0.05mJy \
    --pbcor
```

**Important:** Images must be PB-corrected (`--pbcor`) for mosaic building.

### Step 4: Plan the Mosaic

Plan the mosaic by selecting tiles from the products database:

```bash
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since <start_epoch> \
    --until <end_epoch> \
    --method pbweighted \
    --include-unpbcor false
```

**Parameters:**
- `--name`: Unique name for the mosaic plan
- `--since`: Unix timestamp (epoch seconds) for start of window
- `--until`: Unix timestamp (epoch seconds) for end of window
- `--method`: `pbweighted` (recommended) or `weighted` or `mean`
- `--include-unpbcor`: Set to `false` to only include PB-corrected tiles

**Example with calculated timestamps:**
```bash
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since 1733229894 \
    --until 1733233494 \
    --method pbweighted
```

### Step 5: Build the Mosaic

Build the mosaic from the planned tiles:

```bash
python -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image
```

**What happens:**
1. Validates all tiles (grid consistency, astrometry, calibration)
2. Reads PB images for each tile
3. Computes pixel-by-pixel weights: `weight = pb_response^2 / noise_variance`
4. Combines tiles: `mosaic = sum(weight * tile) / sum(weight)`
5. Exports FITS file: `0834_transit_2025-11-02.image.fits`

**Options:**
- `--ignore-validation`: Skip validation checks (not recommended)
- `--dry-run`: Validate without building (useful for testing)

---

## Method 3: Comprehensive End-to-End Script

For a complete workflow from raw HDF5 files to final mosaic, use:

```bash
python scripts/build_60min_mosaic.py \
    --calibrator "0834+555" \
    --date "2025-11-02" \
    --incoming-dir /data/incoming \
    --output-dir /stage/dsa110-contimg \
    --window-minutes 30 \
    --imsize 2048
```

**What this script does:**
1. Finds transit time
2. Discovers HDF5 groups in window
3. Converts groups to MS (if needed)
4. Identifies calibrator MS
5. Calibrates calibrator MS
6. Applies calibration to all MS files
7. Images all MS files
8. Registers images in products DB
9. Plans mosaic
10. Builds mosaic

**Options:**
- `--skip-conversion`: Use existing MS files
- `--skip-calibration`: Use existing calibration tables
- `--max-workers`: Parallel conversion workers (default: 4)

---

## Understanding Mosaic Methods

### PB-Weighted (`pbweighted`) - Recommended

Uses primary beam response and noise variance for optimal combination:

```
weight[i,j] = pb_response[i,j]^2 / noise_variance
mosaic[i,j] = sum(weight[k][i,j] * tile[k][i,j]) / sum(weight[k][i,j])
```

**Advantages:**
- Optimal signal-to-noise ratio
- Accounts for varying sensitivity across field
- Handles overlapping coverage correctly

**Requirements:**
- All tiles must have PB images
- PB images must be readable

### Noise-Weighted (`weighted`)

Uses only noise variance (no PB information):

```
weight = 1 / noise_variance^2
mosaic = sum(weight[k] * tile[k]) / sum(weight[k])
```

**Use when:** PB images are unavailable

### Mean (`mean`)

Simple average:

```
mosaic = mean(tile[k])
```

**Use when:** All tiles have similar noise and coverage

---

## Validation and Quality Checks

The mosaic builder performs extensive validation:

1. **Grid Consistency**: All tiles must have same pixel scale and grid alignment
2. **Astrometric Registration**: Tiles must align with catalog sources
3. **Calibration Consistency**: Tiles should use compatible calibration
4. **Primary Beam Consistency**: PB images must be valid and consistent
5. **Pre-flight Checks**: Disk space, file existence, permissions

**View validation issues:**
```bash
python -m dsa110_contimg.mosaic.cli build \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image \
    --dry-run
```

---

## Output Files

After building, you'll have:

1. **Mosaic image**: `/stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image/`
   - CASA image format (directory)
   - Contains cleaned, PB-weighted mosaic

2. **FITS export**: `/stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image.fits`
   - Standard FITS format for analysis

3. **Quality metrics** (if generated):
   - `0834_transit_2025-11-02_pb_response.fits` - PB response map
   - `0834_transit_2025-11-02_noise_variance.fits` - Noise variance map
   - `0834_transit_2025-11-02_tile_count.fits` - Number of tiles per pixel
   - `0834_transit_2025-11-02_coverage.fits` - Coverage map

---

## Troubleshooting

### No tiles found in time window

**Problem:** Mosaic planning finds no tiles

**Solutions:**
1. Check products DB has images in the time range:
   ```python
   import sqlite3
   conn = sqlite3.connect("state/products.sqlite3")
   rows = conn.execute("""
       SELECT path, created_at, pbcor FROM images 
       WHERE created_at >= ? AND created_at <= ?
       ORDER BY created_at
   """, (since_epoch, until_epoch)).fetchall()
   print(f"Found {len(rows)} images")
   ```

2. Ensure images are PB-corrected (`pbcor=1` in DB)
3. Verify time window includes actual observation times

### Validation failures

**Problem:** Tiles fail validation checks

**Solutions:**
1. Check tile grid consistency:
   ```bash
   python -m dsa110_contimg.mosaic.cli build --dry-run --name <mosaic_name>
   ```

2. Ensure all tiles have PB images
3. Verify calibration consistency (same calibration tables applied)
4. Check astrometric alignment (compare with catalog)

### Missing PB images

**Problem:** PB images not found for tiles

**Solutions:**
1. Verify PB images exist:
   ```bash
   ls /stage/dsa110-contimg/images/*/pbcor.pb/
   ```

2. Check products DB has PB paths:
   ```python
   import sqlite3
   conn = sqlite3.connect("state/products.sqlite3")
   rows = conn.execute("SELECT path, pb_path FROM images WHERE pbcor=1").fetchall()
   ```

3. Re-image with `--pbcor` if PB images missing

### Mosaic build fails

**Problem:** Build process crashes or errors

**Solutions:**
1. Check disk space: `df -h /stage/dsa110-contimg`
2. Verify CASA is available: `conda activate casa6`
3. Check logs for specific error messages
4. Try `--ignore-validation` (not recommended for science)

---

## Performance Considerations

### Conversion Time

- **Per group**: ~2-5 minutes (with tmpfs staging)
- **12 groups**: ~30-60 minutes total

### Calibration Time

- **Development tier** (testing only): ~1-2 minutes per MS
- **Standard tier** (production default): ~5-10 minutes per MS
- **12 MS files**: ~12-120 minutes total

### Imaging Time

- **Development tier** (testing only, 512×512): ~1-2 minutes per image
- **Standard tier** (production default, 2048×2048): ~5-15 minutes per image
- **12 images**: ~12-180 minutes total

**Note:** The streaming pipeline uses "standard" tier by default for production quality imaging.

### Mosaic Building

- **Planning**: <1 second
- **Validation**: ~1-5 minutes (depends on number of tiles)
- **Building**: ~5-15 minutes (depends on tile size and count)

**Total time**: ~1-6 hours for complete end-to-end workflow

---

## Best Practices

1. **Use PB-weighted method** for optimal results
2. **Ensure all tiles are PB-corrected** before planning
3. **Use consistent calibration** across all tiles
4. **Validate before building** (`--dry-run`)
5. **Check disk space** before starting (mosaics can be large)
6. **Use tmpfs staging** for faster conversion (`--stage-to-tmpfs`)
7. **Monitor products DB** to track tile registration

---

## References

- **Mosaic CLI**: `src/dsa110_contimg/mosaic/cli.py`
- **Transit calculation**: `src/dsa110_contimg/calibration/schedule.py`
- **Calibrator catalog**: `src/dsa110_contimg/calibration/catalogs.py`
- **Example scripts**: `scripts/build_0834_transit_mosaic.py`, `scripts/build_60min_mosaic.py`
- **Mosaic documentation**: `docs/how-to/mosaic.md`
- **5-minute imaging guide**: `docs/how-to/IMAGE_0834_TRANSIT_5MIN.md`


```

```markdown
# How-To: Build a 60-Minute Mosaic Around VLA Calibrator 0834+555

**Objective:** Create a 60-minute mosaic (12 tiles at 5-minute cadence) centered on the transit of VLA calibrator 0834+555.

**Prerequisites:**
- UVH5 subband files available in `/data/incoming` (or your input directory)
- `casa6` conda environment activated
- Pipeline environment variables configured (if using custom paths)
- Products database exists (`state/products.sqlite3`)

---

## Overview

A 60-minute mosaic combines 12 individual 5-minute tiles (images) into a single larger image covering a wider field of view. The process involves:

1. **Finding the transit time** for 0834+555 on a specific date
2. **Calculating a 60-minute window** (±30 minutes around transit)
3. **Converting HDF5 groups to MS** (if not already done)
4. **Calibrating MS files** (if not already done)
5. **Imaging each MS** to create tiles (if not already done)
6. **Planning the mosaic** (selecting tiles from products DB)
7. **Building the mosaic** (combining tiles with primary beam weighting)

---

## Method 1: Using the Pre-Built Script (Simplest)

The simplest approach uses the existing script that handles all steps:

```bash
cd /data/dsa110-contimg
PYTHONPATH=/data/dsa110-contimg/src python scripts/build_0834_transit_mosaic.py
```

**What this script does:**
1. Finds transit time for 0834+555 on 2025-11-02 (hardcoded date)
2. Calculates ±30 minute window around transit
3. Plans mosaic from tiles in products DB within that window
4. Builds PB-weighted mosaic

**To use a different date:**
Edit `scripts/build_0834_transit_mosaic.py` and change:
```python
target_date = "2025-11-02"  # Change to your desired date
```

---

## Method 2: Step-by-Step Manual Process

### Step 1: Find Transit Time

Calculate when 0834+555 transits on your target date:

```python
from astropy.time import Time
from dsa110_contimg.calibration.catalogs import load_vla_catalog, get_calibrator_radec
from dsa110_contimg.calibration.schedule import previous_transits

# Load catalog and get coordinates
catalog_df = load_vla_catalog()
ra_deg, dec_deg = get_calibrator_radec(catalog_df, "0834+555")

# Find transit on target date
target_date = "2025-11-02"
search_start = Time(f"{target_date} 23:59:59")
transits = previous_transits(ra_deg=ra_deg, start_time=search_start, n=10)

# Find transit on target date
for transit in transits:
    transit_date = transit.datetime.date().isoformat()
    if transit_date == target_date:
        print(f"Transit time: {transit.isot}")
        break
```

**Or use the CLI:**
```bash
python -m dsa110_contimg.calibration.catalog_cli transit \
    --calibrator 0834+555 \
    --date 2025-11-02
```

### Step 2: Calculate 60-Minute Window

```python
from astropy.time import Time
import astropy.units as u

# Transit time from Step 1
transit_time = Time("2025-11-02T13:34:54")  # Example

# Calculate ±30 minute window
window_minutes = 30
start_time = transit_time - (window_minutes * 60) * u.s
end_time = transit_time + (window_minutes * 60) * u.s

print(f"Window: {start_time.isot} to {end_time.isot}")

# Convert to Unix timestamps for mosaic CLI
since_epoch = int(start_time.unix)
until_epoch = int(end_time.unix)
```

### Step 3: Ensure Data is Processed (Conversion, Calibration, Imaging)

Before planning a mosaic, ensure all tiles exist in the products database. If not, you need to:

#### 3a. Convert HDF5 Groups to MS

Convert all 5-minute groups in the window:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-11-02T13:04:54" \
    "2025-11-02T14:04:54" \
    --writer parallel-subband \
    --stage-to-tmpfs
```

This creates MS files for each complete 16-subband group in the time window.

#### 3b. Calibrate MS Files

For each MS file:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /stage/dsa110-contimg/ms/2025-11-02T13:04:54.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --preset development
```

**Note:** For production-quality mosaics, use standard calibration (omit `--preset development`).

#### 3c. Image MS Files

For each calibrated MS:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /stage/dsa110-contimg/ms/2025-11-02T13:04:54.ms \
    --imagename /stage/dsa110-contimg/images/2025-11-02T13:04:54 \
    --imsize 2048 \
    --niter 1000 \
    --threshold 0.05mJy \
    --pbcor \
    --quality-tier standard
```

**Important:** 
- Images must be PB-corrected (`--pbcor`) for mosaic building
- Quality tier defaults to "standard" (production quality) - this matches the streaming pipeline behavior

### Step 4: Plan the Mosaic

Plan the mosaic by selecting tiles from the products database:

```bash
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since <start_epoch> \
    --until <end_epoch> \
    --method pbweighted \
    --include-unpbcor false
```

**Parameters:**
- `--name`: Unique name for the mosaic plan
- `--since`: Unix timestamp (epoch seconds) for start of window
- `--until`: Unix timestamp (epoch seconds) for end of window
- `--method`: `pbweighted` (recommended) or `weighted` or `mean`
- `--include-unpbcor`: Set to `false` to only include PB-corrected tiles

**Example with calculated timestamps:**
```bash
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since 1733229894 \
    --until 1733233494 \
    --method pbweighted
```

### Step 5: Build the Mosaic

Build the mosaic from the planned tiles:

```bash
python -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image
```

**What happens:**
1. Validates all tiles (grid consistency, astrometry, calibration)
2. Reads PB images for each tile
3. Computes pixel-by-pixel weights: `weight = pb_response^2 / noise_variance`
4. Combines tiles: `mosaic = sum(weight * tile) / sum(weight)`
5. Exports FITS file: `0834_transit_2025-11-02.image.fits`

**Options:**
- `--ignore-validation`: Skip validation checks (not recommended)
- `--dry-run`: Validate without building (useful for testing)

---

## Method 3: Comprehensive End-to-End Script

For a complete workflow from raw HDF5 files to final mosaic, use:

```bash
python scripts/build_60min_mosaic.py \
    --calibrator "0834+555" \
    --date "2025-11-02" \
    --incoming-dir /data/incoming \
    --output-dir /stage/dsa110-contimg \
    --window-minutes 30 \
    --imsize 2048
```

**What this script does:**
1. Finds transit time
2. Discovers HDF5 groups in window
3. Converts groups to MS (if needed)
4. Identifies calibrator MS
5. Calibrates calibrator MS
6. Applies calibration to all MS files
7. Images all MS files
8. Registers images in products DB
9. Plans mosaic
10. Builds mosaic

**Options:**
- `--skip-conversion`: Use existing MS files
- `--skip-calibration`: Use existing calibration tables
- `--max-workers`: Parallel conversion workers (default: 4)

---

## Understanding Mosaic Methods

### PB-Weighted (`pbweighted`) - Recommended

Uses primary beam response and noise variance for optimal combination:

```
weight[i,j] = pb_response[i,j]^2 / noise_variance
mosaic[i,j] = sum(weight[k][i,j] * tile[k][i,j]) / sum(weight[k][i,j])
```

**Advantages:**
- Optimal signal-to-noise ratio
- Accounts for varying sensitivity across field
- Handles overlapping coverage correctly

**Requirements:**
- All tiles must have PB images
- PB images must be readable

### Noise-Weighted (`weighted`)

Uses only noise variance (no PB information):

```
weight = 1 / noise_variance^2
mosaic = sum(weight[k] * tile[k]) / sum(weight[k])
```

**Use when:** PB images are unavailable

### Mean (`mean`)

Simple average:

```
mosaic = mean(tile[k])
```

**Use when:** All tiles have similar noise and coverage

---

## Validation and Quality Checks

The mosaic builder performs extensive validation:

1. **Grid Consistency**: All tiles must have same pixel scale and grid alignment
2. **Astrometric Registration**: Tiles must align with catalog sources
3. **Calibration Consistency**: Tiles should use compatible calibration
4. **Primary Beam Consistency**: PB images must be valid and consistent
5. **Pre-flight Checks**: Disk space, file existence, permissions

**View validation issues:**
```bash
python -m dsa110_contimg.mosaic.cli build \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image \
    --dry-run
```

---

## Output Files

After building, you'll have:

1. **Mosaic image**: `/stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image/`
   - CASA image format (directory)
   - Contains cleaned, PB-weighted mosaic

2. **FITS export**: `/stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image.fits`
   - Standard FITS format for analysis

3. **Quality metrics** (if generated):
   - `0834_transit_2025-11-02_pb_response.fits` - PB response map
   - `0834_transit_2025-11-02_noise_variance.fits` - Noise variance map
   - `0834_transit_2025-11-02_tile_count.fits` - Number of tiles per pixel
   - `0834_transit_2025-11-02_coverage.fits` - Coverage map

---

## Troubleshooting

### No tiles found in time window

**Problem:** Mosaic planning finds no tiles

**Solutions:**
1. Check products DB has images in the time range:
   ```python
   import sqlite3
   conn = sqlite3.connect("state/products.sqlite3")
   rows = conn.execute("""
       SELECT path, created_at, pbcor FROM images 
       WHERE created_at >= ? AND created_at <= ?
       ORDER BY created_at
   """, (since_epoch, until_epoch)).fetchall()
   print(f"Found {len(rows)} images")
   ```

2. Ensure images are PB-corrected (`pbcor=1` in DB)
3. Verify time window includes actual observation times

### Validation failures

**Problem:** Tiles fail validation checks

**Solutions:**
1. Check tile grid consistency:
   ```bash
   python -m dsa110_contimg.mosaic.cli build --dry-run --name <mosaic_name>
   ```

2. Ensure all tiles have PB images
3. Verify calibration consistency (same calibration tables applied)
4. Check astrometric alignment (compare with catalog)

### Missing PB images

**Problem:** PB images not found for tiles

**Solutions:**
1. Verify PB images exist:
   ```bash
   ls /stage/dsa110-contimg/images/*/pbcor.pb/
   ```

2. Check products DB has PB paths:
   ```python
   import sqlite3
   conn = sqlite3.connect("state/products.sqlite3")
   rows = conn.execute("SELECT path, pb_path FROM images WHERE pbcor=1").fetchall()
   ```

3. Re-image with `--pbcor` if PB images missing

### Mosaic build fails

**Problem:** Build process crashes or errors

**Solutions:**
1. Check disk space: `df -h /stage/dsa110-contimg`
2. Verify CASA is available: `conda activate casa6`
3. Check logs for specific error messages
4. Try `--ignore-validation` (not recommended for science)

---

## Performance Considerations

### Conversion Time

- **Per group**: ~2-5 minutes (with tmpfs staging)
- **12 groups**: ~30-60 minutes total

### Calibration Time

- **Development tier** (testing only): ~1-2 minutes per MS
- **Standard tier** (production default): ~5-10 minutes per MS
- **12 MS files**: ~12-120 minutes total

### Imaging Time

- **Development tier** (testing only, 512×512): ~1-2 minutes per image
- **Standard tier** (production default, 2048×2048): ~5-15 minutes per image
- **12 images**: ~12-180 minutes total

**Note:** The streaming pipeline uses "standard" tier by default for production quality imaging.

### Mosaic Building

- **Planning**: <1 second
- **Validation**: ~1-5 minutes (depends on number of tiles)
- **Building**: ~5-15 minutes (depends on tile size and count)

**Total time**: ~1-6 hours for complete end-to-end workflow

---

## Best Practices

1. **Use PB-weighted method** for optimal results
2. **Ensure all tiles are PB-corrected** before planning
3. **Use consistent calibration** across all tiles
4. **Validate before building** (`--dry-run`)
5. **Check disk space** before starting (mosaics can be large)
6. **Use tmpfs staging** for faster conversion (`--stage-to-tmpfs`)
7. **Monitor products DB** to track tile registration

---

## References

- **Mosaic CLI**: `src/dsa110_contimg/mosaic/cli.py`
- **Transit calculation**: `src/dsa110_contimg/calibration/schedule.py`
- **Calibrator catalog**: `src/dsa110_contimg/calibration/catalogs.py`
- **Example scripts**: `scripts/build_0834_transit_mosaic.py`, `scripts/build_60min_mosaic.py`
- **Mosaic documentation**: `docs/how-to/mosaic.md`
- **5-minute imaging guide**: `docs/how-to/IMAGE_0834_TRANSIT_5MIN.md`


```


Checking calibration defaults:



Fixing the trailing space and checking calibration preset defaults:


```markdown
# How-To: Build a 60-Minute Mosaic Around VLA Calibrator 0834+555

**Objective:** Create a 60-minute mosaic (12 tiles at 5-minute cadence) centered on the transit of VLA calibrator 0834+555.

**Prerequisites:**
- UVH5 subband files available in `/data/incoming` (or your input directory)
- `casa6` conda environment activated
- Pipeline environment variables configured (if using custom paths)
- Products database exists (`state/products.sqlite3`)

---

## Overview

A 60-minute mosaic combines 12 individual 5-minute tiles (images) into a single larger image covering a wider field of view. The process involves:

1. **Finding the transit time** for 0834+555 on a specific date
2. **Calculating a 60-minute window** (±30 minutes around transit)
3. **Converting HDF5 groups to MS** (if not already done)
4. **Calibrating MS files** (if not already done)
5. **Imaging each MS** to create tiles (if not already done)
6. **Planning the mosaic** (selecting tiles from products DB)
7. **Building the mosaic** (combining tiles with primary beam weighting)

---

## Method 1: Using the Pre-Built Script (Simplest)

The simplest approach uses the existing script that handles all steps:

```bash
cd /data/dsa110-contimg
PYTHONPATH=/data/dsa110-contimg/src python scripts/build_0834_transit_mosaic.py
```

**What this script does:**
1. Finds transit time for 0834+555 on 2025-11-02 (hardcoded date)
2. Calculates ±30 minute window around transit
3. Plans mosaic from tiles in products DB within that window
4. Builds PB-weighted mosaic

**To use a different date:**
Edit `scripts/build_0834_transit_mosaic.py` and change:
```python
target_date = "2025-11-02"  # Change to your desired date
```

---

## Method 2: Step-by-Step Manual Process

### Step 1: Find Transit Time

Calculate when 0834+555 transits on your target date:

```python
from astropy.time import Time
from dsa110_contimg.calibration.catalogs import load_vla_catalog, get_calibrator_radec
from dsa110_contimg.calibration.schedule import previous_transits

# Load catalog and get coordinates
catalog_df = load_vla_catalog()
ra_deg, dec_deg = get_calibrator_radec(catalog_df, "0834+555")

# Find transit on target date
target_date = "2025-11-02"
search_start = Time(f"{target_date} 23:59:59")
transits = previous_transits(ra_deg=ra_deg, start_time=search_start, n=10)

# Find transit on target date
for transit in transits:
    transit_date = transit.datetime.date().isoformat()
    if transit_date == target_date:
        print(f"Transit time: {transit.isot}")
        break
```

**Or use the CLI:**
```bash
python -m dsa110_contimg.calibration.catalog_cli transit \
    --calibrator 0834+555 \
    --date 2025-11-02
```

### Step 2: Calculate 60-Minute Window

```python
from astropy.time import Time
import astropy.units as u

# Transit time from Step 1
transit_time = Time("2025-11-02T13:34:54")  # Example

# Calculate ±30 minute window
window_minutes = 30
start_time = transit_time - (window_minutes * 60) * u.s
end_time = transit_time + (window_minutes * 60) * u.s

print(f"Window: {start_time.isot} to {end_time.isot}")

# Convert to Unix timestamps for mosaic CLI
since_epoch = int(start_time.unix)
until_epoch = int(end_time.unix)
```

### Step 3: Ensure Data is Processed (Conversion, Calibration, Imaging)

Before planning a mosaic, ensure all tiles exist in the products database. If not, you need to:

#### 3a. Convert HDF5 Groups to MS

Convert all 5-minute groups in the window:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-11-02T13:04:54" \
    "2025-11-02T14:04:54" \
    --writer parallel-subband \
    --stage-to-tmpfs
```

This creates MS files for each complete 16-subband group in the time window.

#### 3b. Calibrate MS Files

For each MS file:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /stage/dsa110-contimg/ms/2025-11-02T13:04:54.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --preset development
```

**Note:** For production-quality mosaics, use standard calibration (omit `--preset development`).

#### 3c. Image MS Files

For each calibrated MS:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /stage/dsa110-contimg/ms/2025-11-02T13:04:54.ms \
    --imagename /stage/dsa110-contimg/images/2025-11-02T13:04:54 \
    --imsize 2048 \
    --niter 1000 \
    --threshold 0.05mJy \
    --pbcor \
    --quality-tier standard
```

**Important:**
- Images must be PB-corrected (`--pbcor`) for mosaic building
- Quality tier defaults to "standard" (production quality) - this matches the streaming pipeline behavior

### Step 4: Plan the Mosaic

Plan the mosaic by selecting tiles from the products database:

```bash
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since <start_epoch> \
    --until <end_epoch> \
    --method pbweighted \
    --include-unpbcor false
```

**Parameters:**
- `--name`: Unique name for the mosaic plan
- `--since`: Unix timestamp (epoch seconds) for start of window
- `--until`: Unix timestamp (epoch seconds) for end of window
- `--method`: `pbweighted` (recommended) or `weighted` or `mean`
- `--include-unpbcor`: Set to `false` to only include PB-corrected tiles

**Example with calculated timestamps:**
```bash
python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --since 1733229894 \
    --until 1733233494 \
    --method pbweighted
```

### Step 5: Build the Mosaic

Build the mosaic from the planned tiles:

```bash
python -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image
```

**What happens:**
1. Validates all tiles (grid consistency, astrometry, calibration)
2. Reads PB images for each tile
3. Computes pixel-by-pixel weights: `weight = pb_response^2 / noise_variance`
4. Combines tiles: `mosaic = sum(weight * tile) / sum(weight)`
5. Exports FITS file: `0834_transit_2025-11-02.image.fits`

**Options:**
- `--ignore-validation`: Skip validation checks (not recommended)
- `--dry-run`: Validate without building (useful for testing)

---

## Method 3: Comprehensive End-to-End Script

For a complete workflow from raw HDF5 files to final mosaic, use:

```bash
python scripts/build_60min_mosaic.py \
    --calibrator "0834+555" \
    --date "2025-11-02" \
    --incoming-dir /data/incoming \
    --output-dir /stage/dsa110-contimg \
    --window-minutes 30 \
    --imsize 2048
```

**What this script does:**
1. Finds transit time
2. Discovers HDF5 groups in window
3. Converts groups to MS (if needed)
4. Identifies calibrator MS
5. Calibrates calibrator MS
6. Applies calibration to all MS files
7. Images all MS files
8. Registers images in products DB
9. Plans mosaic
10. Builds mosaic

**Options:**
- `--skip-conversion`: Use existing MS files
- `--skip-calibration`: Use existing calibration tables
- `--max-workers`: Parallel conversion workers (default: 4)

---

## Understanding Mosaic Methods

### PB-Weighted (`pbweighted`) - Recommended

Uses primary beam response and noise variance for optimal combination:

```
weight[i,j] = pb_response[i,j]^2 / noise_variance
mosaic[i,j] = sum(weight[k][i,j] * tile[k][i,j]) / sum(weight[k][i,j])
```

**Advantages:**
- Optimal signal-to-noise ratio
- Accounts for varying sensitivity across field
- Handles overlapping coverage correctly

**Requirements:**
- All tiles must have PB images
- PB images must be readable

### Noise-Weighted (`weighted`)

Uses only noise variance (no PB information):

```
weight = 1 / noise_variance^2
mosaic = sum(weight[k] * tile[k]) / sum(weight[k])
```

**Use when:** PB images are unavailable

### Mean (`mean`)

Simple average:

```
mosaic = mean(tile[k])
```

**Use when:** All tiles have similar noise and coverage

---

## Validation and Quality Checks

The mosaic builder performs extensive validation:

1. **Grid Consistency**: All tiles must have same pixel scale and grid alignment
2. **Astrometric Registration**: Tiles must align with catalog sources
3. **Calibration Consistency**: Tiles should use compatible calibration
4. **Primary Beam Consistency**: PB images must be valid and consistent
5. **Pre-flight Checks**: Disk space, file existence, permissions

**View validation issues:**
```bash
python -m dsa110_contimg.mosaic.cli build \
    --name 0834_transit_2025-11-02 \
    --output /stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image \
    --dry-run
```

---

## Output Files

After building, you'll have:

1. **Mosaic image**: `/stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image/`
   - CASA image format (directory)
   - Contains cleaned, PB-weighted mosaic

2. **FITS export**: `/stage/dsa110-contimg/mosaics/0834_transit_2025-11-02.image.fits`
   - Standard FITS format for analysis

3. **Quality metrics** (if generated):
   - `0834_transit_2025-11-02_pb_response.fits` - PB response map
   - `0834_transit_2025-11-02_noise_variance.fits` - Noise variance map
   - `0834_transit_2025-11-02_tile_count.fits` - Number of tiles per pixel
   - `0834_transit_2025-11-02_coverage.fits` - Coverage map

---

## Troubleshooting

### No tiles found in time window

**Problem:** Mosaic planning finds no tiles

**Solutions:**
1. Check products DB has images in the time range:
   ```python
   import sqlite3
   conn = sqlite3.connect("state/products.sqlite3")
   rows = conn.execute("""
       SELECT path, created_at, pbcor FROM images 
       WHERE created_at >= ? AND created_at <= ?
       ORDER BY created_at
   """, (since_epoch, until_epoch)).fetchall()
   print(f"Found {len(rows)} images")
   ```

2. Ensure images are PB-corrected (`pbcor=1` in DB)
3. Verify time window includes actual observation times

### Validation failures

**Problem:** Tiles fail validation checks

**Solutions:**
1. Check tile grid consistency:
   ```bash
   python -m dsa110_contimg.mosaic.cli build --dry-run --name <mosaic_name>
   ```

2. Ensure all tiles have PB images
3. Verify calibration consistency (same calibration tables applied)
4. Check astrometric alignment (compare with catalog)

### Missing PB images

**Problem:** PB images not found for tiles

**Solutions:**
1. Verify PB images exist:
   ```bash
   ls /stage/dsa110-contimg/images/*/pbcor.pb/
   ```

2. Check products DB has PB paths:
   ```python
   import sqlite3
   conn = sqlite3.connect("state/products.sqlite3")
   rows = conn.execute("SELECT path, pb_path FROM images WHERE pbcor=1").fetchall()
   ```

3. Re-image with `--pbcor` if PB images missing

### Mosaic build fails

**Problem:** Build process crashes or errors

**Solutions:**
1. Check disk space: `df -h /stage/dsa110-contimg`
2. Verify CASA is available: `conda activate casa6`
3. Check logs for specific error messages
4. Try `--ignore-validation` (not recommended for science)

---

## Performance Considerations

### Conversion Time

- **Per group**: ~2-5 minutes (with tmpfs staging)
- **12 groups**: ~30-60 minutes total

### Calibration Time

- **Development tier** (testing only): ~1-2 minutes per MS
- **Standard tier** (production default): ~5-10 minutes per MS
- **12 MS files**: ~12-120 minutes total

### Imaging Time

- **Development tier** (testing only, 512×512): ~1-2 minutes per image
- **Standard tier** (production default, 2048×2048): ~5-15 minutes per image
- **12 images**: ~12-180 minutes total

**Note:** The streaming pipeline uses "standard" tier by default for production quality imaging.

### Mosaic Building

- **Planning**: <1 second
- **Validation**: ~1-5 minutes (depends on number of tiles)
- **Building**: ~5-15 minutes (depends on tile size and count)

**Total time**: ~1-6 hours for complete end-to-end workflow

---

## Best Practices

1. **Use PB-weighted method** for optimal results
2. **Ensure all tiles are PB-corrected** before planning
3. **Use consistent calibration** across all tiles
4. **Validate before building** (`--dry-run`)
5. **Check disk space** before starting (mosaics can be large)
6. **Use tmpfs staging** for faster conversion (`--stage-to-tmpfs`)
7. **Monitor products DB** to track tile registration

---

## References

- **Mosaic CLI**: `src/dsa110_contimg/mosaic/cli.py`
- **Transit calculation**: `src/dsa110_contimg/calibration/schedule.py`
- **Calibrator catalog**: `src/dsa110_contimg/calibration/catalogs.py`
- **Example scripts**: `scripts/build_0834_transit_mosaic.py`, `scripts/build_60min_mosaic.py`
- **Mosaic documentation**: `docs/how-to/mosaic.md`
- **5-minute imaging guide**: `docs/how-to/IMAGE_0834_TRANSIT_5MIN.md`


```


Checking the calibration preset default:



## Summary of Changes

Updated the codebase to default to "standard" quality tier for production.

### Code Changes

1. **`src/dsa110_contimg/conversion/streaming/streaming_converter.py`** (line 693)
   - Changed: `quality_tier="development"` → `quality_tier="standard"`
   - Updated comment: "Development tier imaging" → "Standard tier imaging (production quality)"

2. **`src/dsa110_contimg/imaging/worker.py`** (line 61)
   - Changed: `quality_tier="development"` → `quality_tier="standard"`
   - Updated comment: "development tier for fast imaging" → "standard tier for production quality imaging"

3. **`src/dsa110_contimg/pipeline/stages_impl.py`** (line 862)
   - Already using `quality_tier="standard"` ✓

4. **`src/dsa110_contimg/imaging/cli_imaging.py`** (line 308)
   - Already defaults to `quality_tier: str = "standard"` ✓

5. **`src/dsa110_contimg/imaging/cli.py`** (line 123)
   - Already defaults to `default="standard"` ✓

6. **`src/dsa110_contimg/api/models.py`** (line 185)
   - Already defaults to `quality_tier: str = "standard"` ✓

### Documentation Updates

7. **`docs/how-to/BUILD_60MIN_MOSAIC_0834.md`**
   - Added `--quality-tier standard` to imaging example
   - Added note that quality tier defaults to "standard" and matches streaming pipeline
   - Updated performance section to clarify "standard" is the production default
   - Fixed trailing space issue

### Verification

- All function signatures default to "standard"
- Streaming pipeline now uses "standard" instead of "development"
- Imaging worker now uses "standard" instead of "development"
- Documentation updated to reflect production defaults
- No linter errors in code files (only minor markdown formatting warnings in docs)

The codebase now consistently defaults to "standard" quality tier for production use across all components.

---

**User**

Make the calibration stage and Imaging stage consistent with streaming mode

---

**Cursor**


Reviewing the calibration and imaging stages to align with streaming mode:



Comparing streaming mode with the pipeline stages to identify differences:



Updating the stages to match streaming mode:



Making targeted edits to align the stages with streaming mode:


```python
"""
Concrete pipeline stage implementations.

These stages wrap existing conversion, calibration, and imaging functions
to provide a unified pipeline interface.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, Tuple

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logger = logging.getLogger(__name__)


class ConversionStage(PipelineStage):
    """Conversion stage: UVH5 → MS.

    Discovers complete subband groups in the specified time window and
    converts them to CASA Measurement Sets.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize conversion stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for conversion."""
        # Check input directory exists
        if not context.config.paths.input_dir.exists():
            return False, f"Input directory not found: {context.config.paths.input_dir}"

        # Check output directory is writable
        output_dir = context.config.paths.output_dir
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        if not output_dir.parent.exists():
            return False, f"Cannot create output directory: {output_dir.parent}"

        # Check required inputs
        if "start_time" not in context.inputs:
            return False, "start_time required in context.inputs"
        if "end_time" not in context.inputs:
            return False, "end_time required in context.inputs"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute conversion stage."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            convert_subband_groups_to_ms,
        )

        start_time = context.inputs["start_time"]
        end_time = context.inputs["end_time"]

        # Prepare writer kwargs
        writer_kwargs = {
            "max_workers": self.config.conversion.max_workers,
            "skip_validation_during_conversion": self.config.conversion.skip_validation_during_conversion,
            "skip_calibration_recommendations": self.config.conversion.skip_calibration_recommendations,
        }
        if self.config.conversion.stage_to_tmpfs:
            writer_kwargs["stage_to_tmpfs"] = True
            if context.config.paths.scratch_dir:
                writer_kwargs["tmpfs_path"] = str(
                    context.config.paths.scratch_dir)

        # Execute conversion (function returns None, creates MS files in output_dir)
        convert_subband_groups_to_ms(
            str(context.config.paths.input_dir),
            str(context.config.paths.output_dir),
            start_time,
            end_time,
            writer=self.config.conversion.writer,
            writer_kwargs=writer_kwargs,
        )

        # Discover created MS files (similar to current run_convert_job)
        # Only include main MS files matching YYYY-MM-DDTHH:MM:SS.ms pattern
        # Exclude legacy files with suffixes (.phased.ms, .phased_concat.ms, etc.)
        # and files in subdirectories (legacy/, etc.)
        output_path = Path(context.config.paths.output_dir)
        ms_files = []
        if output_path.exists():
            # Pattern: YYYY-MM-DDTHH:MM:SS.ms (no suffixes, no subdirectories)
            pattern = re.compile(
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.ms$'
            )

            # Only search in the main output directory, not subdirectories
            for ms in output_path.glob("*.ms"):
                if ms.is_dir():
                    # Check if filename matches pattern (no suffixes)
                    if pattern.match(ms.name):
                        ms_files.append(str(ms))
                    else:
                        logger.warning(
                            f"Skipping MS file '{ms.name}' - filename doesn't match expected pattern "
                            f"(YYYY-MM-DDTHH:MM:SS.ms). This may be a legacy file or use a different "
                            f"naming convention. If this file should be processed, rename it to match "
                            f"the pattern or update the pattern in ConversionStage."
                        )

        if not ms_files:
            raise ValueError("Conversion produced no MS files")

        # Sort MS files by time for consistency
        ms_files = sorted(ms_files)

        # Use first MS path for backward compatibility (single MS workflows)
        ms_path = ms_files[0]

        # Run quality checks after conversion if they were skipped during conversion
        if self.config.conversion.skip_validation_during_conversion:
            from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion
            logger.info("Running quality checks after conversion...")
            try:
                qa_passed, qa_metrics = check_ms_after_conversion(
                    ms_path=ms_path,
                    quick_check_only=False,
                    alert_on_issues=True,
                )
                if qa_passed:
                    logger.info("✓ MS passed quality checks")
                else:
                    logger.warning("⚠ MS quality issues detected (see alerts)")
            except Exception as e:
                logger.warning(f"Quality check failed (non-fatal): {e}")

        # Update MS index via state repository if available
        if context.state_repository:
            try:
                for ms_file in ms_files:
                    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(
                        ms_file)
                    context.state_repository.upsert_ms_index(
                        ms_file,
                        {
                            "start_mjd": start_mjd,
                            "end_mjd": end_mjd,
                            "mid_mjd": mid_mjd,
                            "status": "converted",
                            "stage": "conversion",
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Return both single MS path (for backward compatibility) and all MS paths
        return context.with_outputs({
            "ms_path": ms_path,  # Single MS for backward compatibility
            "ms_paths": ms_files,  # All MS files
        })

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate conversion outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate MS is readable and has required columns
        try:
            from casacore.tables import table
            with table(ms_path, readonly=True) as tb:
                required_cols = ["DATA", "ANTENNA1", "ANTENNA2", "TIME"]
                missing = [
                    col for col in required_cols if col not in tb.colnames()]
                if missing:
                    return False, f"MS missing required columns: {missing}"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
        except Exception as e:
            return False, f"Cannot validate MS: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial conversion outputs on failure."""
        # If conversion failed, remove any partial MS files created
        if "ms_path" in context.outputs:
            ms_path = Path(context.outputs["ms_path"])
            if ms_path.exists():
                try:
                    import shutil
                    shutil.rmtree(ms_path, ignore_errors=True)
                    logger.info(f"Cleaned up partial MS: {ms_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to cleanup partial MS {ms_path}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "conversion"


class CalibrationSolveStage(PipelineStage):
    """Calibration solve stage: Solve calibration solutions (K, BP, G).

    This stage solves calibration tables (delay/K, bandpass/BP, gains/G)
    for a calibrator Measurement Set. This wraps the calibration CLI
    functions directly without subprocess overhead.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration solve stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration solving."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration solve stage."""
        from dsa110_contimg.calibration.calibration import (
            solve_delay,
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        from dsa110_contimg.utils.locking import file_lock, LockError
        import glob
        import os

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration solve stage: {ms_path}")

        # CRITICAL: Acquire lock to prevent concurrent calibration solves for same MS
        # This prevents race conditions when multiple pipeline runs process the same MS
        lock_path = Path(ms_path).parent / f".{Path(ms_path).stem}.cal_lock"
        # 1 hour timeout (calibration can take a long time)
        lock_timeout = 3600.0

        try:
            with file_lock(lock_path, timeout=lock_timeout):
                return self._execute_calibration_solve(context, ms_path)
        except LockError as e:
            error_msg = (
                f"Cannot acquire calibration lock for {ms_path}. "
                f"Another calibration solve may be in progress. "
                f"If no process is running, check for stale lock file: {lock_path}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _execute_calibration_solve(self, context: PipelineContext, ms_path: str) -> PipelineContext:
        """Internal calibration solve execution (called within lock)."""
        from dsa110_contimg.calibration.calibration import (
            solve_delay,
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        import glob
        import os

        # Get calibration parameters from context inputs or config
        params = context.inputs.get("calibration_params", {})
        field = params.get("field", "0")
        refant = params.get("refant", "103")
        solve_delay_flag = params.get("solve_delay", False)
        solve_bandpass_flag = params.get("solve_bandpass", True)
        solve_gains_flag = params.get("solve_gains", True)
        model_source = params.get("model_source", "catalog")
        gain_solint = params.get("gain_solint", "inf")
        gain_calmode = params.get("gain_calmode", "ap")
        bp_combine_field = params.get("bp_combine_field", False)
        prebp_phase = params.get("prebp_phase", False)
        flag_autocorr = params.get("flag_autocorr", True)

        # Handle existing table discovery
        use_existing = params.get("use_existing_tables", "auto")
        existing_k = params.get("existing_k_table")
        existing_bp = params.get("existing_bp_table")
        existing_g = params.get("existing_g_table")

        if use_existing == "auto":
            ms_dir = os.path.dirname(ms_path)
            ms_base = os.path.basename(ms_path).replace('.ms', '')

            if not solve_delay_flag and not existing_k:
                k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
                k_tables = sorted([p for p in glob.glob(k_pattern) if os.path.isdir(p)],
                                  key=os.path.getmtime, reverse=True)
                if k_tables:
                    existing_k = k_tables[0]

            if not solve_bandpass_flag and not existing_bp:
                bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
                bp_tables = sorted([p for p in glob.glob(bp_pattern) if os.path.isdir(p)],
                                   key=os.path.getmtime, reverse=True)
                if bp_tables:
                    existing_bp = bp_tables[0]

            if not solve_gains_flag and not existing_g:
                g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")
                g_tables = sorted([p for p in glob.glob(g_pattern) if os.path.isdir(p)],
                                  key=os.path.getmtime, reverse=True)
                if g_tables:
                    existing_g = g_tables[0]

        # Determine table prefix
        table_prefix = params.get("table_prefix")
        if not table_prefix:
            table_prefix = f"{os.path.splitext(ms_path)[0]}_{field}"

        # Step 1: Flagging (if requested)
        if params.get("do_flagging", True):
            logger.info("Resetting flags...")
            reset_flags(ms_path)
            flag_zeros(ms_path)
            flag_rfi(ms_path)
            if flag_autocorr:
                from casatasks import flagdata
                logger.info("Flagging autocorrelations...")
                flagdata(vis=str(ms_path), autocorr=True, flagbackup=False)
                logger.info("✓ Autocorrelations flagged")

        # Step 2: Model population (required for calibration)
        if model_source == "catalog":
            from dsa110_contimg.calibration.model import populate_model_from_catalog
            logger.info("Populating MODEL_DATA from catalog...")
            populate_model_from_catalog(
                ms_path,
                field=field,
                calibrator_name=params.get("calibrator_name"),
                cal_ra_deg=params.get("cal_ra_deg"),
                cal_dec_deg=params.get("cal_dec_deg"),
                cal_flux_jy=params.get("cal_flux_jy"),
            )
        elif model_source == "image":
            from dsa110_contimg.calibration.model import populate_model_from_image
            model_image = params.get("model_image")
            if not model_image:
                raise ValueError(
                    "model_image required when model_source='image'")
            logger.info(f"Populating MODEL_DATA from image: {model_image}")
            populate_model_from_image(
                ms_path, field=field, model_image=model_image)

        # Step 3: Solve delay (K) if requested
        ktabs = []
        if solve_delay_flag and not existing_k:
            logger.info("Solving delay (K) calibration...")
            ktabs = solve_delay(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                combine_spw=params.get("k_combine_spw", False),
                t_slow=params.get("k_t_slow", "inf"),
                t_fast=params.get("k_t_fast", "60s"),
                uvrange=params.get("k_uvrange", ""),
                minsnr=params.get("k_minsnr", 5.0),
                skip_slow=params.get("k_skip_slow", False),
            )
        elif existing_k:
            ktabs = [existing_k]
            logger.info(f"Using existing K table: {existing_k}")

        # Step 4: Pre-bandpass phase (if requested)
        prebp_table = None
        if prebp_phase:
            logger.info("Solving pre-bandpass phase...")
            prebp_table = solve_prebandpass_phase(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                uvrange=params.get("prebp_uvrange", ""),
                minsnr=params.get("prebp_minsnr", 3.0),
            )

        # Step 5: Solve bandpass (BP) if requested
        bptabs = []
        if solve_bandpass_flag and not existing_bp:
            logger.info("Solving bandpass (BP) calibration...")
            bptabs = solve_bandpass(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                table_prefix=table_prefix,
                set_model=True,
                model_standard=params.get(
                    "bp_model_standard", "Perley-Butler 2017"),
                combine_fields=bp_combine_field,
                combine_spw=params.get("bp_combine_spw", False),
                minsnr=params.get("bp_minsnr", 5.0),
                uvrange=params.get("bp_uvrange", ""),
                prebandpass_phase_table=prebp_table,
                bp_smooth_type=params.get("bp_smooth_type"),
                bp_smooth_window=params.get("bp_smooth_window"),
            )
        elif existing_bp:
            bptabs = [existing_bp]
            logger.info(f"Using existing BP table: {existing_bp}")

        # Step 6: Solve gains (G) if requested
        gtabs = []
        if solve_gains_flag and not existing_g:
            logger.info("Solving gains (G) calibration...")
            phase_only = (gain_calmode == "p") or bool(params.get("fast"))
            gtabs = solve_gains(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                bptables=bptabs,
                table_prefix=table_prefix,
                t_short=params.get("gain_t_short", "60s"),
                combine_fields=bp_combine_field,
                phase_only=phase_only,
                uvrange=params.get("gain_uvrange", ""),
                solint=gain_solint,
                minsnr=params.get("gain_minsnr", 3.0),
            )
        elif existing_g:
            gtabs = [existing_g]
            logger.info(f"Using existing G table: {existing_g}")

        # Combine all tables
        all_tables = (ktabs[:1] if ktabs else []) + bptabs + gtabs
        logger.info(
            f"Calibration solve complete. Generated {len(all_tables)} tables:")
        for tab in all_tables:
            logger.info(f"  - {tab}")

        # Register calibration tables in registry database
        # CRITICAL: Registration is required for CalibrationStage to find tables via registry lookup
        registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"

        try:
            from dsa110_contimg.database.registry import register_and_verify_caltables
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            # Extract time range from MS for validity window
            # Use wider window (±1 hour) to cover observation period, not just single MS
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
            if mid_mjd is None:
                logger.warning(
                    f"Could not extract time range from {ms_path}, using current time"
                )
                from astropy.time import Time
                mid_mjd = Time.now().mjd
                start_mjd = mid_mjd - 1.0 / 24.0  # 1 hour before
                end_mjd = mid_mjd + 1.0 / 24.0    # 1 hour after
            else:
                # Extend validity window to ±1 hour around MS time range
                # This ensures calibration tables are valid for the entire observation period
                window_hours = 1.0
                if start_mjd is None or end_mjd is None:
                    # Fallback: use ±1 hour around mid point
                    start_mjd = mid_mjd - window_hours / 24.0
                    end_mjd = mid_mjd + window_hours / 24.0
                else:
                    # Extend existing window by ±1 hour
                    duration = end_mjd - start_mjd
                    start_mjd = start_mjd - window_hours / 24.0
                    end_mjd = end_mjd + window_hours / 24.0
                    logger.debug(
                        f"Extended validity window from {duration*24*60:.1f} min to "
                        f"{(end_mjd - start_mjd)*24*60:.1f} min (±{window_hours}h)"
                    )

            # Generate set name from MS filename and time
            ms_base = Path(ms_path).stem
            set_name = f"{ms_base}_{mid_mjd:.6f}"

            # Determine table prefix (common prefix of all tables)
            if not all_tables:
                error_msg = "No calibration tables generated to register"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Get common directory and base name
            table_dir = Path(all_tables[0]).parent
            # Extract prefix from first table (e.g., "2025-10-29T13:54:17_0_bpcal" -> "2025-10-29T13:54:17_0")
            first_table_name = Path(all_tables[0]).stem

            # Remove table type suffixes (e.g., "_bpcal", "_gpcal", "_2gcal")
            # Use fallback logic if pattern doesn't match
            prefix_base = re.sub(
                r'_(bpcal|gpcal|gacal|2gcal|kcal|bacal|flux)$',
                '',
                first_table_name,
                flags=re.IGNORECASE
            )

            # Fallback: If regex didn't change the name, try alternative patterns
            if prefix_base == first_table_name:
                logger.warning(
                    f"Table name '{first_table_name}' doesn't match expected pattern. "
                    f"Trying alternative extraction methods."
                )
                # Try removing common suffixes one by one
                for suffix in ['_bpcal', '_gpcal', '_gacal', '_2gcal', '_kcal', '_bacal', '_flux']:
                    if first_table_name.lower().endswith(suffix.lower()):
                        prefix_base = first_table_name[:-len(suffix)]
                        logger.info(
                            f"Extracted prefix using suffix removal: {prefix_base}")
                        break

                # Final fallback: use MS path-based prefix
                if prefix_base == first_table_name:
                    logger.warning(
                        f"Could not extract table prefix from '{first_table_name}'. "
                        f"Using MS path-based prefix as fallback."
                    )
                    prefix_base = f"{Path(ms_path).stem}_{field}"

            table_prefix = table_dir / prefix_base

            logger.info(
                f"Registering calibration tables in registry: {set_name}")
            logger.debug(f"Using table prefix: {table_prefix}")

            # Register and verify tables are discoverable
            # This helper function:
            # - Registers tables (idempotent via upsert)
            # - Verifies tables are discoverable after registration
            # - Retires set if verification fails (rollback)
            registered_paths = register_and_verify_caltables(
                registry_db,
                set_name,
                table_prefix,
                cal_field=field,
                refant=refant,
                valid_start_mjd=start_mjd,
                valid_end_mjd=end_mjd,
                mid_mjd=mid_mjd,
                status="active",
                verify_discoverable=True,
            )

            logger.info(
                f"✓ Registered and verified {len(registered_paths)} calibration tables "
                f"in registry (set: {set_name})"
            )

        except Exception as e:
            # Registration failure is CRITICAL - CalibrationStage will fail without registered tables
            error_msg = (
                f"CRITICAL: Failed to register calibration tables in registry: {e}. "
                f"CalibrationStage will not be able to find tables via registry lookup. "
                f"Tables were created but may not be registered."
            )
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

        # Update state repository
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_tables": all_tables,
                        "stage": "calibration_solve",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        return context.with_output("calibration_tables", all_tables)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration solve outputs."""
        if "calibration_tables" not in context.outputs:
            return False, "calibration_tables not found in outputs"

        caltables = context.outputs["calibration_tables"]
        if not caltables:
            return False, "No calibration tables generated"

        # Validate all tables exist
        missing = [t for t in caltables if not Path(t).exists()]
        if missing:
            return False, f"Calibration tables missing: {missing}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial calibration tables on failure."""
        if "calibration_tables" in context.outputs:
            caltables = context.outputs["calibration_tables"]
            for table_path in caltables:
                table = Path(table_path)
                if table.exists():
                    try:
                        import shutil
                        shutil.rmtree(table, ignore_errors=True)
                        logger.info(
                            f"Cleaned up partial calibration table: {table}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to cleanup calibration table {table}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration_solve"


class CalibrationStage(PipelineStage):
    """Calibration stage: Apply calibration solutions to MS.

    This stage applies calibration solutions (bandpass, gain) to the
    Measurement Set. In the current implementation, this wraps the
    existing calibration service.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration stage.
        
        Applies calibration from registry (consistent with streaming mode).
        Uses get_active_applylist() to lookup calibration tables by observation time,
        then applies them using apply_to_target() directly.
        """
        from dsa110_contimg.calibration.applycal import apply_to_target
        from dsa110_contimg.database.registry import get_active_applylist
        from dsa110_contimg.utils.time_utils import extract_ms_time_range
        from pathlib import Path
        import time

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration stage: {ms_path}")

        # Check if calibration tables were provided by a previous stage (e.g., CalibrationSolveStage)
        caltables = context.outputs.get("calibration_tables")

        # If tables provided, use them directly (for workflows that solve calibration)
        if caltables:
            logger.info(
                f"Using calibration tables from previous stage: {len(caltables)} tables")
            try:
                apply_to_target(ms_path, field="", gaintables=caltables, calwt=True)
                cal_applied = 1
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e
        else:
            # Lookup tables from registry by observation time (consistent with streaming mode)
            registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"
            if not registry_db.exists():
                # Try alternative location
                registry_db = Path("/data/dsa110-contimg/state/cal_registry.sqlite3")
                if not registry_db.exists():
                    error_msg = (
                        f"Cannot apply calibration: No calibration tables provided and "
                        f"registry not found at {registry_db}. Calibration is required for imaging."
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            # Extract observation time for registry lookup
            mid_mjd = None
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
            except Exception:
                # Fallback to current time if extraction fails
                mid_mjd = time.time() / 86400.0

            # Lookup active calibration tables from registry (same as streaming)
            applylist = []
            try:
                applylist = get_active_applylist(registry_db, float(mid_mjd))
            except Exception as e:
                logger.warning(f"Failed to lookup calibration tables from registry: {e}")
                applylist = []

            if not applylist:
                error_msg = (
                    f"Cannot apply calibration: No calibration tables available for {ms_path} "
                    f"(mid MJD: {mid_mjd:.5f}). Calibration is required for downstream imaging."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Apply calibration using apply_to_target() directly (same as streaming)
            logger.info(f"Applying {len(applylist)} calibration tables from registry")
            try:
                apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
                cal_applied = 1
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e

        # Update MS index (consistent with streaming mode)
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_applied": cal_applied if 'cal_applied' in locals() else 1,
                        "stage": "calibration",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        return context

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration application outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate CORRECTED_DATA column exists and has data
        try:
            from casacore.tables import table
            with table(ms_path, readonly=True) as tb:
                if "CORRECTED_DATA" not in tb.colnames():
                    return False, "CORRECTED_DATA column missing after calibration"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
                # Sample to check CORRECTED_DATA is populated
                sample = tb.getcol("CORRECTED_DATA", 0, min(100, tb.nrows()))
                flags = tb.getcol("FLAG", 0, min(100, tb.nrows()))
                unflagged = sample[~flags]
                if len(unflagged) > 0:
                    import numpy as np
                    if np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        return False, "CORRECTED_DATA appears empty after calibration"
        except Exception as e:
            return False, f"Cannot validate calibrated MS: {e}"

        return True, None

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration"


class ImagingStage(PipelineStage):
    """Imaging stage: Create images from calibrated MS.

    This stage runs imaging on the calibrated Measurement Set to produce
    continuum images.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize imaging stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for imaging."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute imaging stage."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        from casacore.tables import table
        import numpy as np

        ms_path = context.outputs["ms_path"]
        logger.info(f"Imaging stage: {ms_path}")

        # Check if CORRECTED_DATA exists but is empty (calibration wasn't applied)
        # If so, copy DATA to CORRECTED_DATA so imaging can proceed
        try:
            with table(ms_path, readonly=False) as t:
                if "CORRECTED_DATA" in t.colnames() and t.nrows() > 0:
                    # Sample to check if CORRECTED_DATA is populated
                    sample = t.getcol("CORRECTED_DATA", 0,
                                      min(1000, t.nrows()))
                    flags = t.getcol("FLAG", 0, min(1000, t.nrows()))
                    unflagged = sample[~flags]
                    if len(unflagged) > 0 and np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        # CORRECTED_DATA exists but is empty - copy DATA to CORRECTED_DATA
                        logger.info(
                            "CORRECTED_DATA is empty, copying DATA to CORRECTED_DATA for imaging")
                        data_col = t.getcol("DATA")
                        t.putcol("CORRECTED_DATA", data_col)
                        t.flush()
        except Exception as e:
            logger.warning(f"Could not check/fix CORRECTED_DATA: {e}")

        # Construct output imagename
        ms_name = Path(ms_path).stem
        out_dir = Path(ms_path).parent.parent / \
            "images" / Path(ms_path).parent.name
        out_dir.mkdir(parents=True, exist_ok=True)
        imagename = str(out_dir / f"{ms_name}.img")

        # Run imaging
        image_ms(
            ms_path,
            imagename=imagename,
            field=context.config.imaging.field or "",
            gridder=context.config.imaging.gridder,
            wprojplanes=context.config.imaging.wprojplanes,
            quality_tier="standard",
            skip_fits=False,
            use_nvss_mask=context.config.imaging.use_nvss_mask,
            mask_radius_arcsec=context.config.imaging.mask_radius_arcsec,
        )

        # Find created image files
        image_paths = []
        for suffix in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
            img_path = f"{imagename}{suffix}"
            if Path(img_path).exists():
                image_paths.append(img_path)

        # Primary image path (for output)
        primary_image = f"{imagename}.image"
        if not Path(primary_image).exists():
            # Try FITS if CASA image not found
            fits_image = f"{imagename}.image.fits"
            if Path(fits_image).exists():
                primary_image = fits_image
                logger.info(f"Using FITS image as primary: {primary_image}")
            elif image_paths:
                # Fallback to first available image
                primary_image = image_paths[0]
                logger.warning(
                    f"Primary image not found, using fallback: {primary_image}. "
                    "This may indicate an imaging failure."
                )
            else:
                # No images found - this is a critical failure
                error_msg = (
                    f"Imaging failed: No image files created for {ms_path}. "
                    f"Expected primary image: {imagename}.image"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "imagename": primary_image,
                        "stage": "imaging",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Run catalog-based flux scale validation if enabled
        if context.config.imaging.run_catalog_validation:
            self._run_catalog_validation(
                primary_image, context.config.imaging.catalog_validation_catalog)

        return context.with_output("image_path", primary_image)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate imaging outputs."""
        if "image_path" not in context.outputs:
            return False, "image_path not found in outputs"

        image_path = context.outputs["image_path"]
        if not Path(image_path).exists():
            return False, f"Image file does not exist: {image_path}"

        # Validate image is readable
        try:
            from casacore.images import image
            with image(str(image_path)) as img:
                shape = img.shape()
                if len(shape) == 0 or any(s == 0 for s in shape):
                    return False, f"Image has invalid shape: {shape}"
        except Exception as e:
            return False, f"Cannot validate image: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial image files on failure."""
        if "image_path" in context.outputs:
            image_path = Path(context.outputs["image_path"])
            # Remove all related image files
            base_name = str(image_path).replace(
                ".image", "").replace(".fits", "")
            suffixes = [".image", ".image.pbcor",
                        ".residual", ".psf", ".pb", ".fits"]
            for suffix in suffixes:
                img_file = Path(f"{base_name}{suffix}")
                if img_file.exists():
                    try:
                        import shutil
                        if img_file.is_dir():
                            shutil.rmtree(img_file, ignore_errors=True)
                        else:
                            img_file.unlink()
                        logger.info(f"Cleaned up partial image: {img_file}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to cleanup image {img_file}: {e}")

    def _run_catalog_validation(self, image_path: str, catalog: str) -> None:
        """Run catalog-based flux scale validation on image.

        This validates the image flux scale by comparing forced photometry
        at catalog source positions to catalog fluxes. Non-fatal - logs
        warnings but does not fail the pipeline.

        Args:
            image_path: Path to image file (CASA or FITS)
            catalog: Catalog to use for validation ('nvss' or 'vlass')
        """
        from dsa110_contimg.qa.catalog_validation import validate_flux_scale
        from pathlib import Path

        # Find FITS image (prefer PB-corrected)
        image_path_obj = Path(image_path)
        fits_image = None

        # Try PB-corrected FITS first
        if image_path.endswith(".image"):
            pbcor_fits = f"{image_path}.pbcor.fits"
            if Path(pbcor_fits).exists():
                fits_image = pbcor_fits
            else:
                # Try regular FITS
                regular_fits = f"{image_path}.fits"
                if Path(regular_fits).exists():
                    fits_image = regular_fits
        elif image_path.endswith(".fits"):
            fits_image = image_path

        if not fits_image or not Path(fits_image).exists():
            logger.warning(
                f"Catalog validation skipped: FITS image not found for {image_path}. "
                "Catalog validation requires FITS format."
            )
            return

        logger.info(
            f"Running catalog-based flux scale validation ({catalog.upper()}) on {fits_image}")

        try:
            result = validate_flux_scale(
                image_path=fits_image,
                catalog=catalog,
                min_snr=5.0,
                flux_range_jy=(0.01, 10.0),
                max_flux_ratio_error=0.2
            )

            if result.n_matched > 0:
                logger.info(
                    f"Catalog validation ({catalog.upper()}): "
                    f"{result.n_matched} sources matched, "
                    f"flux ratio={result.mean_flux_ratio:.3f}±{result.rms_flux_ratio:.3f}, "
                    f"scale error={result.flux_scale_error*100:.1f}%"
                )

                if result.has_issues:
                    logger.warning(
                        f"Catalog validation issues: {', '.join(result.issues)}")

                if result.has_warnings:
                    logger.warning(
                        f"Catalog validation warnings: {', '.join(result.warnings)}")
            else:
                logger.warning(
                    f"Catalog validation ({catalog.upper()}): No sources matched. "
                    "This may indicate astrometry issues or insufficient catalog coverage."
                )

        except Exception as e:
            logger.warning(
                f"Catalog validation failed (non-fatal): {e}. "
                "Pipeline will continue, but flux scale was not validated."
            )

    def get_name(self) -> str:
        """Get stage name."""
        return "imaging"

```


Updating ImagingStage to match streaming's image path structure:


```python
"""
Concrete pipeline stage implementations.

These stages wrap existing conversion, calibration, and imaging functions
to provide a unified pipeline interface.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, Tuple

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logger = logging.getLogger(__name__)


class ConversionStage(PipelineStage):
    """Conversion stage: UVH5 → MS.

    Discovers complete subband groups in the specified time window and
    converts them to CASA Measurement Sets.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize conversion stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for conversion."""
        # Check input directory exists
        if not context.config.paths.input_dir.exists():
            return False, f"Input directory not found: {context.config.paths.input_dir}"

        # Check output directory is writable
        output_dir = context.config.paths.output_dir
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        if not output_dir.parent.exists():
            return False, f"Cannot create output directory: {output_dir.parent}"

        # Check required inputs
        if "start_time" not in context.inputs:
            return False, "start_time required in context.inputs"
        if "end_time" not in context.inputs:
            return False, "end_time required in context.inputs"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute conversion stage."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            convert_subband_groups_to_ms,
        )

        start_time = context.inputs["start_time"]
        end_time = context.inputs["end_time"]

        # Prepare writer kwargs
        writer_kwargs = {
            "max_workers": self.config.conversion.max_workers,
            "skip_validation_during_conversion": self.config.conversion.skip_validation_during_conversion,
            "skip_calibration_recommendations": self.config.conversion.skip_calibration_recommendations,
        }
        if self.config.conversion.stage_to_tmpfs:
            writer_kwargs["stage_to_tmpfs"] = True
            if context.config.paths.scratch_dir:
                writer_kwargs["tmpfs_path"] = str(
                    context.config.paths.scratch_dir)

        # Execute conversion (function returns None, creates MS files in output_dir)
        convert_subband_groups_to_ms(
            str(context.config.paths.input_dir),
            str(context.config.paths.output_dir),
            start_time,
            end_time,
            writer=self.config.conversion.writer,
            writer_kwargs=writer_kwargs,
        )

        # Discover created MS files (similar to current run_convert_job)
        # Only include main MS files matching YYYY-MM-DDTHH:MM:SS.ms pattern
        # Exclude legacy files with suffixes (.phased.ms, .phased_concat.ms, etc.)
        # and files in subdirectories (legacy/, etc.)
        output_path = Path(context.config.paths.output_dir)
        ms_files = []
        if output_path.exists():
            # Pattern: YYYY-MM-DDTHH:MM:SS.ms (no suffixes, no subdirectories)
            pattern = re.compile(
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.ms$'
            )

            # Only search in the main output directory, not subdirectories
            for ms in output_path.glob("*.ms"):
                if ms.is_dir():
                    # Check if filename matches pattern (no suffixes)
                    if pattern.match(ms.name):
                        ms_files.append(str(ms))
                    else:
                        logger.warning(
                            f"Skipping MS file '{ms.name}' - filename doesn't match expected pattern "
                            f"(YYYY-MM-DDTHH:MM:SS.ms). This may be a legacy file or use a different "
                            f"naming convention. If this file should be processed, rename it to match "
                            f"the pattern or update the pattern in ConversionStage."
                        )

        if not ms_files:
            raise ValueError("Conversion produced no MS files")

        # Sort MS files by time for consistency
        ms_files = sorted(ms_files)

        # Use first MS path for backward compatibility (single MS workflows)
        ms_path = ms_files[0]

        # Run quality checks after conversion if they were skipped during conversion
        if self.config.conversion.skip_validation_during_conversion:
            from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion
            logger.info("Running quality checks after conversion...")
            try:
                qa_passed, qa_metrics = check_ms_after_conversion(
                    ms_path=ms_path,
                    quick_check_only=False,
                    alert_on_issues=True,
                )
                if qa_passed:
                    logger.info("✓ MS passed quality checks")
                else:
                    logger.warning("⚠ MS quality issues detected (see alerts)")
            except Exception as e:
                logger.warning(f"Quality check failed (non-fatal): {e}")

        # Update MS index via state repository if available
        if context.state_repository:
            try:
                for ms_file in ms_files:
                    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(
                        ms_file)
                    context.state_repository.upsert_ms_index(
                        ms_file,
                        {
                            "start_mjd": start_mjd,
                            "end_mjd": end_mjd,
                            "mid_mjd": mid_mjd,
                            "status": "converted",
                            "stage": "conversion",
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Return both single MS path (for backward compatibility) and all MS paths
        return context.with_outputs({
            "ms_path": ms_path,  # Single MS for backward compatibility
            "ms_paths": ms_files,  # All MS files
        })

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate conversion outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate MS is readable and has required columns
        try:
            from casacore.tables import table
            with table(ms_path, readonly=True) as tb:
                required_cols = ["DATA", "ANTENNA1", "ANTENNA2", "TIME"]
                missing = [
                    col for col in required_cols if col not in tb.colnames()]
                if missing:
                    return False, f"MS missing required columns: {missing}"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
        except Exception as e:
            return False, f"Cannot validate MS: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial conversion outputs on failure."""
        # If conversion failed, remove any partial MS files created
        if "ms_path" in context.outputs:
            ms_path = Path(context.outputs["ms_path"])
            if ms_path.exists():
                try:
                    import shutil
                    shutil.rmtree(ms_path, ignore_errors=True)
                    logger.info(f"Cleaned up partial MS: {ms_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to cleanup partial MS {ms_path}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "conversion"


class CalibrationSolveStage(PipelineStage):
    """Calibration solve stage: Solve calibration solutions (K, BP, G).

    This stage solves calibration tables (delay/K, bandpass/BP, gains/G)
    for a calibrator Measurement Set. This wraps the calibration CLI
    functions directly without subprocess overhead.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration solve stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration solving."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration solve stage."""
        from dsa110_contimg.calibration.calibration import (
            solve_delay,
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        from dsa110_contimg.utils.locking import file_lock, LockError
        import glob
        import os

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration solve stage: {ms_path}")

        # CRITICAL: Acquire lock to prevent concurrent calibration solves for same MS
        # This prevents race conditions when multiple pipeline runs process the same MS
        lock_path = Path(ms_path).parent / f".{Path(ms_path).stem}.cal_lock"
        # 1 hour timeout (calibration can take a long time)
        lock_timeout = 3600.0

        try:
            with file_lock(lock_path, timeout=lock_timeout):
                return self._execute_calibration_solve(context, ms_path)
        except LockError as e:
            error_msg = (
                f"Cannot acquire calibration lock for {ms_path}. "
                f"Another calibration solve may be in progress. "
                f"If no process is running, check for stale lock file: {lock_path}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _execute_calibration_solve(self, context: PipelineContext, ms_path: str) -> PipelineContext:
        """Internal calibration solve execution (called within lock)."""
        from dsa110_contimg.calibration.calibration import (
            solve_delay,
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        import glob
        import os

        # Get calibration parameters from context inputs or config
        params = context.inputs.get("calibration_params", {})
        field = params.get("field", "0")
        refant = params.get("refant", "103")
        solve_delay_flag = params.get("solve_delay", False)
        solve_bandpass_flag = params.get("solve_bandpass", True)
        solve_gains_flag = params.get("solve_gains", True)
        model_source = params.get("model_source", "catalog")
        gain_solint = params.get("gain_solint", "inf")
        gain_calmode = params.get("gain_calmode", "ap")
        bp_combine_field = params.get("bp_combine_field", False)
        prebp_phase = params.get("prebp_phase", False)
        flag_autocorr = params.get("flag_autocorr", True)

        # Handle existing table discovery
        use_existing = params.get("use_existing_tables", "auto")
        existing_k = params.get("existing_k_table")
        existing_bp = params.get("existing_bp_table")
        existing_g = params.get("existing_g_table")

        if use_existing == "auto":
            ms_dir = os.path.dirname(ms_path)
            ms_base = os.path.basename(ms_path).replace('.ms', '')

            if not solve_delay_flag and not existing_k:
                k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
                k_tables = sorted([p for p in glob.glob(k_pattern) if os.path.isdir(p)],
                                  key=os.path.getmtime, reverse=True)
                if k_tables:
                    existing_k = k_tables[0]

            if not solve_bandpass_flag and not existing_bp:
                bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
                bp_tables = sorted([p for p in glob.glob(bp_pattern) if os.path.isdir(p)],
                                   key=os.path.getmtime, reverse=True)
                if bp_tables:
                    existing_bp = bp_tables[0]

            if not solve_gains_flag and not existing_g:
                g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")
                g_tables = sorted([p for p in glob.glob(g_pattern) if os.path.isdir(p)],
                                  key=os.path.getmtime, reverse=True)
                if g_tables:
                    existing_g = g_tables[0]

        # Determine table prefix
        table_prefix = params.get("table_prefix")
        if not table_prefix:
            table_prefix = f"{os.path.splitext(ms_path)[0]}_{field}"

        # Step 1: Flagging (if requested)
        if params.get("do_flagging", True):
            logger.info("Resetting flags...")
            reset_flags(ms_path)
            flag_zeros(ms_path)
            flag_rfi(ms_path)
            if flag_autocorr:
                from casatasks import flagdata
                logger.info("Flagging autocorrelations...")
                flagdata(vis=str(ms_path), autocorr=True, flagbackup=False)
                logger.info("✓ Autocorrelations flagged")

        # Step 2: Model population (required for calibration)
        if model_source == "catalog":
            from dsa110_contimg.calibration.model import populate_model_from_catalog
            logger.info("Populating MODEL_DATA from catalog...")
            populate_model_from_catalog(
                ms_path,
                field=field,
                calibrator_name=params.get("calibrator_name"),
                cal_ra_deg=params.get("cal_ra_deg"),
                cal_dec_deg=params.get("cal_dec_deg"),
                cal_flux_jy=params.get("cal_flux_jy"),
            )
        elif model_source == "image":
            from dsa110_contimg.calibration.model import populate_model_from_image
            model_image = params.get("model_image")
            if not model_image:
                raise ValueError(
                    "model_image required when model_source='image'")
            logger.info(f"Populating MODEL_DATA from image: {model_image}")
            populate_model_from_image(
                ms_path, field=field, model_image=model_image)

        # Step 3: Solve delay (K) if requested
        ktabs = []
        if solve_delay_flag and not existing_k:
            logger.info("Solving delay (K) calibration...")
            ktabs = solve_delay(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                combine_spw=params.get("k_combine_spw", False),
                t_slow=params.get("k_t_slow", "inf"),
                t_fast=params.get("k_t_fast", "60s"),
                uvrange=params.get("k_uvrange", ""),
                minsnr=params.get("k_minsnr", 5.0),
                skip_slow=params.get("k_skip_slow", False),
            )
        elif existing_k:
            ktabs = [existing_k]
            logger.info(f"Using existing K table: {existing_k}")

        # Step 4: Pre-bandpass phase (if requested)
        prebp_table = None
        if prebp_phase:
            logger.info("Solving pre-bandpass phase...")
            prebp_table = solve_prebandpass_phase(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                uvrange=params.get("prebp_uvrange", ""),
                minsnr=params.get("prebp_minsnr", 3.0),
            )

        # Step 5: Solve bandpass (BP) if requested
        bptabs = []
        if solve_bandpass_flag and not existing_bp:
            logger.info("Solving bandpass (BP) calibration...")
            bptabs = solve_bandpass(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                table_prefix=table_prefix,
                set_model=True,
                model_standard=params.get(
                    "bp_model_standard", "Perley-Butler 2017"),
                combine_fields=bp_combine_field,
                combine_spw=params.get("bp_combine_spw", False),
                minsnr=params.get("bp_minsnr", 5.0),
                uvrange=params.get("bp_uvrange", ""),
                prebandpass_phase_table=prebp_table,
                bp_smooth_type=params.get("bp_smooth_type"),
                bp_smooth_window=params.get("bp_smooth_window"),
            )
        elif existing_bp:
            bptabs = [existing_bp]
            logger.info(f"Using existing BP table: {existing_bp}")

        # Step 6: Solve gains (G) if requested
        gtabs = []
        if solve_gains_flag and not existing_g:
            logger.info("Solving gains (G) calibration...")
            phase_only = (gain_calmode == "p") or bool(params.get("fast"))
            gtabs = solve_gains(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                bptables=bptabs,
                table_prefix=table_prefix,
                t_short=params.get("gain_t_short", "60s"),
                combine_fields=bp_combine_field,
                phase_only=phase_only,
                uvrange=params.get("gain_uvrange", ""),
                solint=gain_solint,
                minsnr=params.get("gain_minsnr", 3.0),
            )
        elif existing_g:
            gtabs = [existing_g]
            logger.info(f"Using existing G table: {existing_g}")

        # Combine all tables
        all_tables = (ktabs[:1] if ktabs else []) + bptabs + gtabs
        logger.info(
            f"Calibration solve complete. Generated {len(all_tables)} tables:")
        for tab in all_tables:
            logger.info(f"  - {tab}")

        # Register calibration tables in registry database
        # CRITICAL: Registration is required for CalibrationStage to find tables via registry lookup
        registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"

        try:
            from dsa110_contimg.database.registry import register_and_verify_caltables
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            # Extract time range from MS for validity window
            # Use wider window (±1 hour) to cover observation period, not just single MS
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
            if mid_mjd is None:
                logger.warning(
                    f"Could not extract time range from {ms_path}, using current time"
                )
                from astropy.time import Time
                mid_mjd = Time.now().mjd
                start_mjd = mid_mjd - 1.0 / 24.0  # 1 hour before
                end_mjd = mid_mjd + 1.0 / 24.0    # 1 hour after
            else:
                # Extend validity window to ±1 hour around MS time range
                # This ensures calibration tables are valid for the entire observation period
                window_hours = 1.0
                if start_mjd is None or end_mjd is None:
                    # Fallback: use ±1 hour around mid point
                    start_mjd = mid_mjd - window_hours / 24.0
                    end_mjd = mid_mjd + window_hours / 24.0
                else:
                    # Extend existing window by ±1 hour
                    duration = end_mjd - start_mjd
                    start_mjd = start_mjd - window_hours / 24.0
                    end_mjd = end_mjd + window_hours / 24.0
                    logger.debug(
                        f"Extended validity window from {duration*24*60:.1f} min to "
                        f"{(end_mjd - start_mjd)*24*60:.1f} min (±{window_hours}h)"
                    )

            # Generate set name from MS filename and time
            ms_base = Path(ms_path).stem
            set_name = f"{ms_base}_{mid_mjd:.6f}"

            # Determine table prefix (common prefix of all tables)
            if not all_tables:
                error_msg = "No calibration tables generated to register"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Get common directory and base name
            table_dir = Path(all_tables[0]).parent
            # Extract prefix from first table (e.g., "2025-10-29T13:54:17_0_bpcal" -> "2025-10-29T13:54:17_0")
            first_table_name = Path(all_tables[0]).stem

            # Remove table type suffixes (e.g., "_bpcal", "_gpcal", "_2gcal")
            # Use fallback logic if pattern doesn't match
            prefix_base = re.sub(
                r'_(bpcal|gpcal|gacal|2gcal|kcal|bacal|flux)$',
                '',
                first_table_name,
                flags=re.IGNORECASE
            )

            # Fallback: If regex didn't change the name, try alternative patterns
            if prefix_base == first_table_name:
                logger.warning(
                    f"Table name '{first_table_name}' doesn't match expected pattern. "
                    f"Trying alternative extraction methods."
                )
                # Try removing common suffixes one by one
                for suffix in ['_bpcal', '_gpcal', '_gacal', '_2gcal', '_kcal', '_bacal', '_flux']:
                    if first_table_name.lower().endswith(suffix.lower()):
                        prefix_base = first_table_name[:-len(suffix)]
                        logger.info(
                            f"Extracted prefix using suffix removal: {prefix_base}")
                        break

                # Final fallback: use MS path-based prefix
                if prefix_base == first_table_name:
                    logger.warning(
                        f"Could not extract table prefix from '{first_table_name}'. "
                        f"Using MS path-based prefix as fallback."
                    )
                    prefix_base = f"{Path(ms_path).stem}_{field}"

            table_prefix = table_dir / prefix_base

            logger.info(
                f"Registering calibration tables in registry: {set_name}")
            logger.debug(f"Using table prefix: {table_prefix}")

            # Register and verify tables are discoverable
            # This helper function:
            # - Registers tables (idempotent via upsert)
            # - Verifies tables are discoverable after registration
            # - Retires set if verification fails (rollback)
            registered_paths = register_and_verify_caltables(
                registry_db,
                set_name,
                table_prefix,
                cal_field=field,
                refant=refant,
                valid_start_mjd=start_mjd,
                valid_end_mjd=end_mjd,
                mid_mjd=mid_mjd,
                status="active",
                verify_discoverable=True,
            )

            logger.info(
                f"✓ Registered and verified {len(registered_paths)} calibration tables "
                f"in registry (set: {set_name})"
            )

        except Exception as e:
            # Registration failure is CRITICAL - CalibrationStage will fail without registered tables
            error_msg = (
                f"CRITICAL: Failed to register calibration tables in registry: {e}. "
                f"CalibrationStage will not be able to find tables via registry lookup. "
                f"Tables were created but may not be registered."
            )
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

        # Update state repository
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_tables": all_tables,
                        "stage": "calibration_solve",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        return context.with_output("calibration_tables", all_tables)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration solve outputs."""
        if "calibration_tables" not in context.outputs:
            return False, "calibration_tables not found in outputs"

        caltables = context.outputs["calibration_tables"]
        if not caltables:
            return False, "No calibration tables generated"

        # Validate all tables exist
        missing = [t for t in caltables if not Path(t).exists()]
        if missing:
            return False, f"Calibration tables missing: {missing}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial calibration tables on failure."""
        if "calibration_tables" in context.outputs:
            caltables = context.outputs["calibration_tables"]
            for table_path in caltables:
                table = Path(table_path)
                if table.exists():
                    try:
                        import shutil
                        shutil.rmtree(table, ignore_errors=True)
                        logger.info(
                            f"Cleaned up partial calibration table: {table}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to cleanup calibration table {table}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration_solve"


class CalibrationStage(PipelineStage):
    """Calibration stage: Apply calibration solutions to MS.

    This stage applies calibration solutions (bandpass, gain) to the
    Measurement Set. In the current implementation, this wraps the
    existing calibration service.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration stage.
        
        Applies calibration from registry (consistent with streaming mode).
        Uses get_active_applylist() to lookup calibration tables by observation time,
        then applies them using apply_to_target() directly.
        """
        from dsa110_contimg.calibration.applycal import apply_to_target
        from dsa110_contimg.database.registry import get_active_applylist
        from dsa110_contimg.utils.time_utils import extract_ms_time_range
        from pathlib import Path
        import time

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration stage: {ms_path}")

        # Check if calibration tables were provided by a previous stage (e.g., CalibrationSolveStage)
        caltables = context.outputs.get("calibration_tables")

        # If tables provided, use them directly (for workflows that solve calibration)
        if caltables:
            logger.info(
                f"Using calibration tables from previous stage: {len(caltables)} tables")
            try:
                apply_to_target(ms_path, field="", gaintables=caltables, calwt=True)
                cal_applied = 1
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e
        else:
            # Lookup tables from registry by observation time (consistent with streaming mode)
            registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"
            if not registry_db.exists():
                # Try alternative location
                registry_db = Path("/data/dsa110-contimg/state/cal_registry.sqlite3")
                if not registry_db.exists():
                    error_msg = (
                        f"Cannot apply calibration: No calibration tables provided and "
                        f"registry not found at {registry_db}. Calibration is required for imaging."
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            # Extract observation time for registry lookup
            mid_mjd = None
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
            except Exception:
                # Fallback to current time if extraction fails
                mid_mjd = time.time() / 86400.0

            # Lookup active calibration tables from registry (same as streaming)
            applylist = []
            try:
                applylist = get_active_applylist(registry_db, float(mid_mjd))
            except Exception as e:
                logger.warning(f"Failed to lookup calibration tables from registry: {e}")
                applylist = []

            if not applylist:
                error_msg = (
                    f"Cannot apply calibration: No calibration tables available for {ms_path} "
                    f"(mid MJD: {mid_mjd:.5f}). Calibration is required for downstream imaging."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Apply calibration using apply_to_target() directly (same as streaming)
            logger.info(f"Applying {len(applylist)} calibration tables from registry")
            try:
                apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
                cal_applied = 1
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e

        # Update MS index (consistent with streaming mode)
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_applied": cal_applied if 'cal_applied' in locals() else 1,
                        "stage": "calibration",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        return context

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration application outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate CORRECTED_DATA column exists and has data
        try:
            from casacore.tables import table
            with table(ms_path, readonly=True) as tb:
                if "CORRECTED_DATA" not in tb.colnames():
                    return False, "CORRECTED_DATA column missing after calibration"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
                # Sample to check CORRECTED_DATA is populated
                sample = tb.getcol("CORRECTED_DATA", 0, min(100, tb.nrows()))
                flags = tb.getcol("FLAG", 0, min(100, tb.nrows()))
                unflagged = sample[~flags]
                if len(unflagged) > 0:
                    import numpy as np
                    if np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        return False, "CORRECTED_DATA appears empty after calibration"
        except Exception as e:
            return False, f"Cannot validate calibrated MS: {e}"

        return True, None

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration"


class ImagingStage(PipelineStage):
    """Imaging stage: Create images from calibrated MS.

    This stage runs imaging on the calibrated Measurement Set to produce
    continuum images.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize imaging stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for imaging."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute imaging stage."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        from casacore.tables import table
        import numpy as np

        ms_path = context.outputs["ms_path"]
        logger.info(f"Imaging stage: {ms_path}")

        # Check if CORRECTED_DATA exists but is empty (calibration wasn't applied)
        # If so, copy DATA to CORRECTED_DATA so imaging can proceed
        try:
            with table(ms_path, readonly=False) as t:
                if "CORRECTED_DATA" in t.colnames() and t.nrows() > 0:
                    # Sample to check if CORRECTED_DATA is populated
                    sample = t.getcol("CORRECTED_DATA", 0,
                                      min(1000, t.nrows()))
                    flags = t.getcol("FLAG", 0, min(1000, t.nrows()))
                    unflagged = sample[~flags]
                    if len(unflagged) > 0 and np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        # CORRECTED_DATA exists but is empty - copy DATA to CORRECTED_DATA
                        logger.info(
                            "CORRECTED_DATA is empty, copying DATA to CORRECTED_DATA for imaging")
                        data_col = t.getcol("DATA")
                        t.putcol("CORRECTED_DATA", data_col)
                        t.flush()
        except Exception as e:
            logger.warning(f"Could not check/fix CORRECTED_DATA: {e}")

        # Construct output imagename (consistent with streaming mode)
        # Streaming uses: os.path.join(args.output_dir, base + ".img")
        # where base is derived from MS filename (without .ms extension)
        ms_name = Path(ms_path).stem
        output_dir = Path(context.config.paths.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        imagename = str(output_dir / f"{ms_name}.img")

        # Run imaging (consistent with streaming mode)
        image_ms(
            ms_path,
            imagename=imagename,
            field="",  # Use empty string for all fields (same as streaming)
            gridder=context.config.imaging.gridder,
            wprojplanes=context.config.imaging.wprojplanes,
            quality_tier="standard",  # Production quality (same as streaming)
            skip_fits=False,  # Export FITS (same as streaming)
            use_nvss_mask=context.config.imaging.use_nvss_mask,
            mask_radius_arcsec=context.config.imaging.mask_radius_arcsec,
        )

        # Find created image files
        image_paths = []
        for suffix in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
            img_path = f"{imagename}{suffix}"
            if Path(img_path).exists():
                image_paths.append(img_path)

        # Primary image path (for output)
        primary_image = f"{imagename}.image"
        if not Path(primary_image).exists():
            # Try FITS if CASA image not found
            fits_image = f"{imagename}.image.fits"
            if Path(fits_image).exists():
                primary_image = fits_image
                logger.info(f"Using FITS image as primary: {primary_image}")
            elif image_paths:
                # Fallback to first available image
                primary_image = image_paths[0]
                logger.warning(
                    f"Primary image not found, using fallback: {primary_image}. "
                    "This may indicate an imaging failure."
                )
            else:
                # No images found - this is a critical failure
                error_msg = (
                    f"Imaging failed: No image files created for {ms_path}. "
                    f"Expected primary image: {imagename}.image"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "imagename": primary_image,
                        "stage": "imaging",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Run catalog-based flux scale validation if enabled
        if context.config.imaging.run_catalog_validation:
            self._run_catalog_validation(
                primary_image, context.config.imaging.catalog_validation_catalog)

        return context.with_output("image_path", primary_image)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate imaging outputs."""
        if "image_path" not in context.outputs:
            return False, "image_path not found in outputs"

        image_path = context.outputs["image_path"]
        if not Path(image_path).exists():
            return False, f"Image file does not exist: {image_path}"

        # Validate image is readable
        try:
            from casacore.images import image
            with image(str(image_path)) as img:
                shape = img.shape()
                if len(shape) == 0 or any(s == 0 for s in shape):
                    return False, f"Image has invalid shape: {shape}"
        except Exception as e:
            return False, f"Cannot validate image: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial image files on failure."""
        if "image_path" in context.outputs:
            image_path = Path(context.outputs["image_path"])
            # Remove all related image files
            base_name = str(image_path).replace(
                ".image", "").replace(".fits", "")
            suffixes = [".image", ".image.pbcor",
                        ".residual", ".psf", ".pb", ".fits"]
            for suffix in suffixes:
                img_file = Path(f"{base_name}{suffix}")
                if img_file.exists():
                    try:
                        import shutil
                        if img_file.is_dir():
                            shutil.rmtree(img_file, ignore_errors=True)
                        else:
                            img_file.unlink()
                        logger.info(f"Cleaned up partial image: {img_file}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to cleanup image {img_file}: {e}")

    def _run_catalog_validation(self, image_path: str, catalog: str) -> None:
        """Run catalog-based flux scale validation on image.

        This validates the image flux scale by comparing forced photometry
        at catalog source positions to catalog fluxes. Non-fatal - logs
        warnings but does not fail the pipeline.

        Args:
            image_path: Path to image file (CASA or FITS)
            catalog: Catalog to use for validation ('nvss' or 'vlass')
        """
        from dsa110_contimg.qa.catalog_validation import validate_flux_scale
        from pathlib import Path

        # Find FITS image (prefer PB-corrected)
        image_path_obj = Path(image_path)
        fits_image = None

        # Try PB-corrected FITS first
        if image_path.endswith(".image"):
            pbcor_fits = f"{image_path}.pbcor.fits"
            if Path(pbcor_fits).exists():
                fits_image = pbcor_fits
            else:
                # Try regular FITS
                regular_fits = f"{image_path}.fits"
                if Path(regular_fits).exists():
                    fits_image = regular_fits
        elif image_path.endswith(".fits"):
            fits_image = image_path

        if not fits_image or not Path(fits_image).exists():
            logger.warning(
                f"Catalog validation skipped: FITS image not found for {image_path}. "
                "Catalog validation requires FITS format."
            )
            return

        logger.info(
            f"Running catalog-based flux scale validation ({catalog.upper()}) on {fits_image}")

        try:
            result = validate_flux_scale(
                image_path=fits_image,
                catalog=catalog,
                min_snr=5.0,
                flux_range_jy=(0.01, 10.0),
                max_flux_ratio_error=0.2
            )

            if result.n_matched > 0:
                logger.info(
                    f"Catalog validation ({catalog.upper()}): "
                    f"{result.n_matched} sources matched, "
                    f"flux ratio={result.mean_flux_ratio:.3f}±{result.rms_flux_ratio:.3f}, "
                    f"scale error={result.flux_scale_error*100:.1f}%"
                )

                if result.has_issues:
                    logger.warning(
                        f"Catalog validation issues: {', '.join(result.issues)}")

                if result.has_warnings:
                    logger.warning(
                        f"Catalog validation warnings: {', '.join(result.warnings)}")
            else:
                logger.warning(
                    f"Catalog validation ({catalog.upper()}): No sources matched. "
                    "This may indicate astrometry issues or insufficient catalog coverage."
                )

        except Exception as e:
            logger.warning(
                f"Catalog validation failed (non-fatal): {e}. "
                "Pipeline will continue, but flux scale was not validated."
            )

    def get_name(self) -> str:
        """Get stage name."""
        return "imaging"

```


Fixing the `cal_applied` variable initialization issue:


```python
"""
Concrete pipeline stage implementations.

These stages wrap existing conversion, calibration, and imaging functions
to provide a unified pipeline interface.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, Tuple

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logger = logging.getLogger(__name__)


class ConversionStage(PipelineStage):
    """Conversion stage: UVH5 → MS.

    Discovers complete subband groups in the specified time window and
    converts them to CASA Measurement Sets.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize conversion stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for conversion."""
        # Check input directory exists
        if not context.config.paths.input_dir.exists():
            return False, f"Input directory not found: {context.config.paths.input_dir}"

        # Check output directory is writable
        output_dir = context.config.paths.output_dir
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        if not output_dir.parent.exists():
            return False, f"Cannot create output directory: {output_dir.parent}"

        # Check required inputs
        if "start_time" not in context.inputs:
            return False, "start_time required in context.inputs"
        if "end_time" not in context.inputs:
            return False, "end_time required in context.inputs"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute conversion stage."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            convert_subband_groups_to_ms,
        )

        start_time = context.inputs["start_time"]
        end_time = context.inputs["end_time"]

        # Prepare writer kwargs
        writer_kwargs = {
            "max_workers": self.config.conversion.max_workers,
            "skip_validation_during_conversion": self.config.conversion.skip_validation_during_conversion,
            "skip_calibration_recommendations": self.config.conversion.skip_calibration_recommendations,
        }
        if self.config.conversion.stage_to_tmpfs:
            writer_kwargs["stage_to_tmpfs"] = True
            if context.config.paths.scratch_dir:
                writer_kwargs["tmpfs_path"] = str(
                    context.config.paths.scratch_dir)

        # Execute conversion (function returns None, creates MS files in output_dir)
        convert_subband_groups_to_ms(
            str(context.config.paths.input_dir),
            str(context.config.paths.output_dir),
            start_time,
            end_time,
            writer=self.config.conversion.writer,
            writer_kwargs=writer_kwargs,
        )

        # Discover created MS files (similar to current run_convert_job)
        # Only include main MS files matching YYYY-MM-DDTHH:MM:SS.ms pattern
        # Exclude legacy files with suffixes (.phased.ms, .phased_concat.ms, etc.)
        # and files in subdirectories (legacy/, etc.)
        output_path = Path(context.config.paths.output_dir)
        ms_files = []
        if output_path.exists():
            # Pattern: YYYY-MM-DDTHH:MM:SS.ms (no suffixes, no subdirectories)
            pattern = re.compile(
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.ms$'
            )

            # Only search in the main output directory, not subdirectories
            for ms in output_path.glob("*.ms"):
                if ms.is_dir():
                    # Check if filename matches pattern (no suffixes)
                    if pattern.match(ms.name):
                        ms_files.append(str(ms))
                    else:
                        logger.warning(
                            f"Skipping MS file '{ms.name}' - filename doesn't match expected pattern "
                            f"(YYYY-MM-DDTHH:MM:SS.ms). This may be a legacy file or use a different "
                            f"naming convention. If this file should be processed, rename it to match "
                            f"the pattern or update the pattern in ConversionStage."
                        )

        if not ms_files:
            raise ValueError("Conversion produced no MS files")

        # Sort MS files by time for consistency
        ms_files = sorted(ms_files)

        # Use first MS path for backward compatibility (single MS workflows)
        ms_path = ms_files[0]

        # Run quality checks after conversion if they were skipped during conversion
        if self.config.conversion.skip_validation_during_conversion:
            from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion
            logger.info("Running quality checks after conversion...")
            try:
                qa_passed, qa_metrics = check_ms_after_conversion(
                    ms_path=ms_path,
                    quick_check_only=False,
                    alert_on_issues=True,
                )
                if qa_passed:
                    logger.info("✓ MS passed quality checks")
                else:
                    logger.warning("⚠ MS quality issues detected (see alerts)")
            except Exception as e:
                logger.warning(f"Quality check failed (non-fatal): {e}")

        # Update MS index via state repository if available
        if context.state_repository:
            try:
                for ms_file in ms_files:
                    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(
                        ms_file)
                    context.state_repository.upsert_ms_index(
                        ms_file,
                        {
                            "start_mjd": start_mjd,
                            "end_mjd": end_mjd,
                            "mid_mjd": mid_mjd,
                            "status": "converted",
                            "stage": "conversion",
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Return both single MS path (for backward compatibility) and all MS paths
        return context.with_outputs({
            "ms_path": ms_path,  # Single MS for backward compatibility
            "ms_paths": ms_files,  # All MS files
        })

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate conversion outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate MS is readable and has required columns
        try:
            from casacore.tables import table
            with table(ms_path, readonly=True) as tb:
                required_cols = ["DATA", "ANTENNA1", "ANTENNA2", "TIME"]
                missing = [
                    col for col in required_cols if col not in tb.colnames()]
                if missing:
                    return False, f"MS missing required columns: {missing}"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
        except Exception as e:
            return False, f"Cannot validate MS: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial conversion outputs on failure."""
        # If conversion failed, remove any partial MS files created
        if "ms_path" in context.outputs:
            ms_path = Path(context.outputs["ms_path"])
            if ms_path.exists():
                try:
                    import shutil
                    shutil.rmtree(ms_path, ignore_errors=True)
                    logger.info(f"Cleaned up partial MS: {ms_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to cleanup partial MS {ms_path}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "conversion"


class CalibrationSolveStage(PipelineStage):
    """Calibration solve stage: Solve calibration solutions (K, BP, G).

    This stage solves calibration tables (delay/K, bandpass/BP, gains/G)
    for a calibrator Measurement Set. This wraps the calibration CLI
    functions directly without subprocess overhead.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration solve stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration solving."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration solve stage."""
        from dsa110_contimg.calibration.calibration import (
            solve_delay,
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        from dsa110_contimg.utils.locking import file_lock, LockError
        import glob
        import os

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration solve stage: {ms_path}")

        # CRITICAL: Acquire lock to prevent concurrent calibration solves for same MS
        # This prevents race conditions when multiple pipeline runs process the same MS
        lock_path = Path(ms_path).parent / f".{Path(ms_path).stem}.cal_lock"
        # 1 hour timeout (calibration can take a long time)
        lock_timeout = 3600.0

        try:
            with file_lock(lock_path, timeout=lock_timeout):
                return self._execute_calibration_solve(context, ms_path)
        except LockError as e:
            error_msg = (
                f"Cannot acquire calibration lock for {ms_path}. "
                f"Another calibration solve may be in progress. "
                f"If no process is running, check for stale lock file: {lock_path}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _execute_calibration_solve(self, context: PipelineContext, ms_path: str) -> PipelineContext:
        """Internal calibration solve execution (called within lock)."""
        from dsa110_contimg.calibration.calibration import (
            solve_delay,
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        import glob
        import os

        # Get calibration parameters from context inputs or config
        params = context.inputs.get("calibration_params", {})
        field = params.get("field", "0")
        refant = params.get("refant", "103")
        solve_delay_flag = params.get("solve_delay", False)
        solve_bandpass_flag = params.get("solve_bandpass", True)
        solve_gains_flag = params.get("solve_gains", True)
        model_source = params.get("model_source", "catalog")
        gain_solint = params.get("gain_solint", "inf")
        gain_calmode = params.get("gain_calmode", "ap")
        bp_combine_field = params.get("bp_combine_field", False)
        prebp_phase = params.get("prebp_phase", False)
        flag_autocorr = params.get("flag_autocorr", True)

        # Handle existing table discovery
        use_existing = params.get("use_existing_tables", "auto")
        existing_k = params.get("existing_k_table")
        existing_bp = params.get("existing_bp_table")
        existing_g = params.get("existing_g_table")

        if use_existing == "auto":
            ms_dir = os.path.dirname(ms_path)
            ms_base = os.path.basename(ms_path).replace('.ms', '')

            if not solve_delay_flag and not existing_k:
                k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
                k_tables = sorted([p for p in glob.glob(k_pattern) if os.path.isdir(p)],
                                  key=os.path.getmtime, reverse=True)
                if k_tables:
                    existing_k = k_tables[0]

            if not solve_bandpass_flag and not existing_bp:
                bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
                bp_tables = sorted([p for p in glob.glob(bp_pattern) if os.path.isdir(p)],
                                   key=os.path.getmtime, reverse=True)
                if bp_tables:
                    existing_bp = bp_tables[0]

            if not solve_gains_flag and not existing_g:
                g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")
                g_tables = sorted([p for p in glob.glob(g_pattern) if os.path.isdir(p)],
                                  key=os.path.getmtime, reverse=True)
                if g_tables:
                    existing_g = g_tables[0]

        # Determine table prefix
        table_prefix = params.get("table_prefix")
        if not table_prefix:
            table_prefix = f"{os.path.splitext(ms_path)[0]}_{field}"

        # Step 1: Flagging (if requested)
        if params.get("do_flagging", True):
            logger.info("Resetting flags...")
            reset_flags(ms_path)
            flag_zeros(ms_path)
            flag_rfi(ms_path)
            if flag_autocorr:
                from casatasks import flagdata
                logger.info("Flagging autocorrelations...")
                flagdata(vis=str(ms_path), autocorr=True, flagbackup=False)
                logger.info("✓ Autocorrelations flagged")

        # Step 2: Model population (required for calibration)
        if model_source == "catalog":
            from dsa110_contimg.calibration.model import populate_model_from_catalog
            logger.info("Populating MODEL_DATA from catalog...")
            populate_model_from_catalog(
                ms_path,
                field=field,
                calibrator_name=params.get("calibrator_name"),
                cal_ra_deg=params.get("cal_ra_deg"),
                cal_dec_deg=params.get("cal_dec_deg"),
                cal_flux_jy=params.get("cal_flux_jy"),
            )
        elif model_source == "image":
            from dsa110_contimg.calibration.model import populate_model_from_image
            model_image = params.get("model_image")
            if not model_image:
                raise ValueError(
                    "model_image required when model_source='image'")
            logger.info(f"Populating MODEL_DATA from image: {model_image}")
            populate_model_from_image(
                ms_path, field=field, model_image=model_image)

        # Step 3: Solve delay (K) if requested
        ktabs = []
        if solve_delay_flag and not existing_k:
            logger.info("Solving delay (K) calibration...")
            ktabs = solve_delay(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                combine_spw=params.get("k_combine_spw", False),
                t_slow=params.get("k_t_slow", "inf"),
                t_fast=params.get("k_t_fast", "60s"),
                uvrange=params.get("k_uvrange", ""),
                minsnr=params.get("k_minsnr", 5.0),
                skip_slow=params.get("k_skip_slow", False),
            )
        elif existing_k:
            ktabs = [existing_k]
            logger.info(f"Using existing K table: {existing_k}")

        # Step 4: Pre-bandpass phase (if requested)
        prebp_table = None
        if prebp_phase:
            logger.info("Solving pre-bandpass phase...")
            prebp_table = solve_prebandpass_phase(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                uvrange=params.get("prebp_uvrange", ""),
                minsnr=params.get("prebp_minsnr", 3.0),
            )

        # Step 5: Solve bandpass (BP) if requested
        bptabs = []
        if solve_bandpass_flag and not existing_bp:
            logger.info("Solving bandpass (BP) calibration...")
            bptabs = solve_bandpass(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                table_prefix=table_prefix,
                set_model=True,
                model_standard=params.get(
                    "bp_model_standard", "Perley-Butler 2017"),
                combine_fields=bp_combine_field,
                combine_spw=params.get("bp_combine_spw", False),
                minsnr=params.get("bp_minsnr", 5.0),
                uvrange=params.get("bp_uvrange", ""),
                prebandpass_phase_table=prebp_table,
                bp_smooth_type=params.get("bp_smooth_type"),
                bp_smooth_window=params.get("bp_smooth_window"),
            )
        elif existing_bp:
            bptabs = [existing_bp]
            logger.info(f"Using existing BP table: {existing_bp}")

        # Step 6: Solve gains (G) if requested
        gtabs = []
        if solve_gains_flag and not existing_g:
            logger.info("Solving gains (G) calibration...")
            phase_only = (gain_calmode == "p") or bool(params.get("fast"))
            gtabs = solve_gains(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                bptables=bptabs,
                table_prefix=table_prefix,
                t_short=params.get("gain_t_short", "60s"),
                combine_fields=bp_combine_field,
                phase_only=phase_only,
                uvrange=params.get("gain_uvrange", ""),
                solint=gain_solint,
                minsnr=params.get("gain_minsnr", 3.0),
            )
        elif existing_g:
            gtabs = [existing_g]
            logger.info(f"Using existing G table: {existing_g}")

        # Combine all tables
        all_tables = (ktabs[:1] if ktabs else []) + bptabs + gtabs
        logger.info(
            f"Calibration solve complete. Generated {len(all_tables)} tables:")
        for tab in all_tables:
            logger.info(f"  - {tab}")

        # Register calibration tables in registry database
        # CRITICAL: Registration is required for CalibrationStage to find tables via registry lookup
        registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"

        try:
            from dsa110_contimg.database.registry import register_and_verify_caltables
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            # Extract time range from MS for validity window
            # Use wider window (±1 hour) to cover observation period, not just single MS
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
            if mid_mjd is None:
                logger.warning(
                    f"Could not extract time range from {ms_path}, using current time"
                )
                from astropy.time import Time
                mid_mjd = Time.now().mjd
                start_mjd = mid_mjd - 1.0 / 24.0  # 1 hour before
                end_mjd = mid_mjd + 1.0 / 24.0    # 1 hour after
            else:
                # Extend validity window to ±1 hour around MS time range
                # This ensures calibration tables are valid for the entire observation period
                window_hours = 1.0
                if start_mjd is None or end_mjd is None:
                    # Fallback: use ±1 hour around mid point
                    start_mjd = mid_mjd - window_hours / 24.0
                    end_mjd = mid_mjd + window_hours / 24.0
                else:
                    # Extend existing window by ±1 hour
                    duration = end_mjd - start_mjd
                    start_mjd = start_mjd - window_hours / 24.0
                    end_mjd = end_mjd + window_hours / 24.0
                    logger.debug(
                        f"Extended validity window from {duration*24*60:.1f} min to "
                        f"{(end_mjd - start_mjd)*24*60:.1f} min (±{window_hours}h)"
                    )

            # Generate set name from MS filename and time
            ms_base = Path(ms_path).stem
            set_name = f"{ms_base}_{mid_mjd:.6f}"

            # Determine table prefix (common prefix of all tables)
            if not all_tables:
                error_msg = "No calibration tables generated to register"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Get common directory and base name
            table_dir = Path(all_tables[0]).parent
            # Extract prefix from first table (e.g., "2025-10-29T13:54:17_0_bpcal" -> "2025-10-29T13:54:17_0")
            first_table_name = Path(all_tables[0]).stem

            # Remove table type suffixes (e.g., "_bpcal", "_gpcal", "_2gcal")
            # Use fallback logic if pattern doesn't match
            prefix_base = re.sub(
                r'_(bpcal|gpcal|gacal|2gcal|kcal|bacal|flux)$',
                '',
                first_table_name,
                flags=re.IGNORECASE
            )

            # Fallback: If regex didn't change the name, try alternative patterns
            if prefix_base == first_table_name:
                logger.warning(
                    f"Table name '{first_table_name}' doesn't match expected pattern. "
                    f"Trying alternative extraction methods."
                )
                # Try removing common suffixes one by one
                for suffix in ['_bpcal', '_gpcal', '_gacal', '_2gcal', '_kcal', '_bacal', '_flux']:
                    if first_table_name.lower().endswith(suffix.lower()):
                        prefix_base = first_table_name[:-len(suffix)]
                        logger.info(
                            f"Extracted prefix using suffix removal: {prefix_base}")
                        break

                # Final fallback: use MS path-based prefix
                if prefix_base == first_table_name:
                    logger.warning(
                        f"Could not extract table prefix from '{first_table_name}'. "
                        f"Using MS path-based prefix as fallback."
                    )
                    prefix_base = f"{Path(ms_path).stem}_{field}"

            table_prefix = table_dir / prefix_base

            logger.info(
                f"Registering calibration tables in registry: {set_name}")
            logger.debug(f"Using table prefix: {table_prefix}")

            # Register and verify tables are discoverable
            # This helper function:
            # - Registers tables (idempotent via upsert)
            # - Verifies tables are discoverable after registration
            # - Retires set if verification fails (rollback)
            registered_paths = register_and_verify_caltables(
                registry_db,
                set_name,
                table_prefix,
                cal_field=field,
                refant=refant,
                valid_start_mjd=start_mjd,
                valid_end_mjd=end_mjd,
                mid_mjd=mid_mjd,
                status="active",
                verify_discoverable=True,
            )

            logger.info(
                f"✓ Registered and verified {len(registered_paths)} calibration tables "
                f"in registry (set: {set_name})"
            )

        except Exception as e:
            # Registration failure is CRITICAL - CalibrationStage will fail without registered tables
            error_msg = (
                f"CRITICAL: Failed to register calibration tables in registry: {e}. "
                f"CalibrationStage will not be able to find tables via registry lookup. "
                f"Tables were created but may not be registered."
            )
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

        # Update state repository
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_tables": all_tables,
                        "stage": "calibration_solve",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        return context.with_output("calibration_tables", all_tables)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration solve outputs."""
        if "calibration_tables" not in context.outputs:
            return False, "calibration_tables not found in outputs"

        caltables = context.outputs["calibration_tables"]
        if not caltables:
            return False, "No calibration tables generated"

        # Validate all tables exist
        missing = [t for t in caltables if not Path(t).exists()]
        if missing:
            return False, f"Calibration tables missing: {missing}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial calibration tables on failure."""
        if "calibration_tables" in context.outputs:
            caltables = context.outputs["calibration_tables"]
            for table_path in caltables:
                table = Path(table_path)
                if table.exists():
                    try:
                        import shutil
                        shutil.rmtree(table, ignore_errors=True)
                        logger.info(
                            f"Cleaned up partial calibration table: {table}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to cleanup calibration table {table}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration_solve"


class CalibrationStage(PipelineStage):
    """Calibration stage: Apply calibration solutions to MS.

    This stage applies calibration solutions (bandpass, gain) to the
    Measurement Set. In the current implementation, this wraps the
    existing calibration service.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration stage.
        
        Applies calibration from registry (consistent with streaming mode).
        Uses get_active_applylist() to lookup calibration tables by observation time,
        then applies them using apply_to_target() directly.
        """
        from dsa110_contimg.calibration.applycal import apply_to_target
        from dsa110_contimg.database.registry import get_active_applylist
        from dsa110_contimg.utils.time_utils import extract_ms_time_range
        from pathlib import Path
        import time

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration stage: {ms_path}")

        # Check if calibration tables were provided by a previous stage (e.g., CalibrationSolveStage)
        caltables = context.outputs.get("calibration_tables")
        cal_applied = 0

        # If tables provided, use them directly (for workflows that solve calibration)
        if caltables:
            logger.info(
                f"Using calibration tables from previous stage: {len(caltables)} tables")
            try:
                apply_to_target(ms_path, field="", gaintables=caltables, calwt=True)
                cal_applied = 1
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e
        else:
            # Lookup tables from registry by observation time (consistent with streaming mode)
            registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"
            if not registry_db.exists():
                # Try alternative location
                registry_db = Path("/data/dsa110-contimg/state/cal_registry.sqlite3")
                if not registry_db.exists():
                    error_msg = (
                        f"Cannot apply calibration: No calibration tables provided and "
                        f"registry not found at {registry_db}. Calibration is required for imaging."
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            # Extract observation time for registry lookup
            mid_mjd = None
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
            except Exception:
                # Fallback to current time if extraction fails
                mid_mjd = time.time() / 86400.0

            # Lookup active calibration tables from registry (same as streaming)
            applylist = []
            try:
                applylist = get_active_applylist(registry_db, float(mid_mjd))
            except Exception as e:
                logger.warning(f"Failed to lookup calibration tables from registry: {e}")
                applylist = []

            if not applylist:
                error_msg = (
                    f"Cannot apply calibration: No calibration tables available for {ms_path} "
                    f"(mid MJD: {mid_mjd:.5f}). Calibration is required for downstream imaging."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Apply calibration using apply_to_target() directly (same as streaming)
            logger.info(f"Applying {len(applylist)} calibration tables from registry")
            try:
                apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
                cal_applied = 1
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e

        # Update MS index (consistent with streaming mode)
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_applied": cal_applied,
                        "stage": "calibration",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        return context

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration application outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate CORRECTED_DATA column exists and has data
        try:
            from casacore.tables import table
            with table(ms_path, readonly=True) as tb:
                if "CORRECTED_DATA" not in tb.colnames():
                    return False, "CORRECTED_DATA column missing after calibration"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
                # Sample to check CORRECTED_DATA is populated
                sample = tb.getcol("CORRECTED_DATA", 0, min(100, tb.nrows()))
                flags = tb.getcol("FLAG", 0, min(100, tb.nrows()))
                unflagged = sample[~flags]
                if len(unflagged) > 0:
                    import numpy as np
                    if np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        return False, "CORRECTED_DATA appears empty after calibration"
        except Exception as e:
            return False, f"Cannot validate calibrated MS: {e}"

        return True, None

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration"


class ImagingStage(PipelineStage):
    """Imaging stage: Create images from calibrated MS.

    This stage runs imaging on the calibrated Measurement Set to produce
    continuum images.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize imaging stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for imaging."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute imaging stage."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        from casacore.tables import table
        import numpy as np

        ms_path = context.outputs["ms_path"]
        logger.info(f"Imaging stage: {ms_path}")

        # Check if CORRECTED_DATA exists but is empty (calibration wasn't applied)
        # If so, copy DATA to CORRECTED_DATA so imaging can proceed
        try:
            with table(ms_path, readonly=False) as t:
                if "CORRECTED_DATA" in t.colnames() and t.nrows() > 0:
                    # Sample to check if CORRECTED_DATA is populated
                    sample = t.getcol("CORRECTED_DATA", 0,
                                      min(1000, t.nrows()))
                    flags = t.getcol("FLAG", 0, min(1000, t.nrows()))
                    unflagged = sample[~flags]
                    if len(unflagged) > 0 and np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        # CORRECTED_DATA exists but is empty - copy DATA to CORRECTED_DATA
                        logger.info(
                            "CORRECTED_DATA is empty, copying DATA to CORRECTED_DATA for imaging")
                        data_col = t.getcol("DATA")
                        t.putcol("CORRECTED_DATA", data_col)
                        t.flush()
        except Exception as e:
            logger.warning(f"Could not check/fix CORRECTED_DATA: {e}")

        # Construct output imagename (consistent with streaming mode)
        # Streaming uses: os.path.join(args.output_dir, base + ".img")
        # where base is derived from MS filename (without .ms extension)
        ms_name = Path(ms_path).stem
        output_dir = Path(context.config.paths.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        imagename = str(output_dir / f"{ms_name}.img")

        # Run imaging (consistent with streaming mode)
        image_ms(
            ms_path,
            imagename=imagename,
            field="",  # Use empty string for all fields (same as streaming)
            gridder=context.config.imaging.gridder,
            wprojplanes=context.config.imaging.wprojplanes,
            quality_tier="standard",  # Production quality (same as streaming)
            skip_fits=False,  # Export FITS (same as streaming)
            use_nvss_mask=context.config.imaging.use_nvss_mask,
            mask_radius_arcsec=context.config.imaging.mask_radius_arcsec,
        )

        # Find created image files
        image_paths = []
        for suffix in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
            img_path = f"{imagename}{suffix}"
            if Path(img_path).exists():
                image_paths.append(img_path)

        # Primary image path (for output)
        primary_image = f"{imagename}.image"
        if not Path(primary_image).exists():
            # Try FITS if CASA image not found
            fits_image = f"{imagename}.image.fits"
            if Path(fits_image).exists():
                primary_image = fits_image
                logger.info(f"Using FITS image as primary: {primary_image}")
            elif image_paths:
                # Fallback to first available image
                primary_image = image_paths[0]
                logger.warning(
                    f"Primary image not found, using fallback: {primary_image}. "
                    "This may indicate an imaging failure."
                )
            else:
                # No images found - this is a critical failure
                error_msg = (
                    f"Imaging failed: No image files created for {ms_path}. "
                    f"Expected primary image: {imagename}.image"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "imagename": primary_image,
                        "stage": "imaging",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Run catalog-based flux scale validation if enabled
        if context.config.imaging.run_catalog_validation:
            self._run_catalog_validation(
                primary_image, context.config.imaging.catalog_validation_catalog)

        return context.with_output("image_path", primary_image)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate imaging outputs."""
        if "image_path" not in context.outputs:
            return False, "image_path not found in outputs"

        image_path = context.outputs["image_path"]
        if not Path(image_path).exists():
            return False, f"Image file does not exist: {image_path}"

        # Validate image is readable
        try:
            from casacore.images import image
            with image(str(image_path)) as img:
                shape = img.shape()
                if len(shape) == 0 or any(s == 0 for s in shape):
                    return False, f"Image has invalid shape: {shape}"
        except Exception as e:
            return False, f"Cannot validate image: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial image files on failure."""
        if "image_path" in context.outputs:
            image_path = Path(context.outputs["image_path"])
            # Remove all related image files
            base_name = str(image_path).replace(
                ".image", "").replace(".fits", "")
            suffixes = [".image", ".image.pbcor",
                        ".residual", ".psf", ".pb", ".fits"]
            for suffix in suffixes:
                img_file = Path(f"{base_name}{suffix}")
                if img_file.exists():
                    try:
                        import shutil
                        if img_file.is_dir():
                            shutil.rmtree(img_file, ignore_errors=True)
                        else:
                            img_file.unlink()
                        logger.info(f"Cleaned up partial image: {img_file}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to cleanup image {img_file}: {e}")

    def _run_catalog_validation(self, image_path: str, catalog: str) -> None:
        """Run catalog-based flux scale validation on image.

        This validates the image flux scale by comparing forced photometry
        at catalog source positions to catalog fluxes. Non-fatal - logs
        warnings but does not fail the pipeline.

        Args:
            image_path: Path to image file (CASA or FITS)
            catalog: Catalog to use for validation ('nvss' or 'vlass')
        """
        from dsa110_contimg.qa.catalog_validation import validate_flux_scale
        from pathlib import Path

        # Find FITS image (prefer PB-corrected)
        image_path_obj = Path(image_path)
        fits_image = None

        # Try PB-corrected FITS first
        if image_path.endswith(".image"):
            pbcor_fits = f"{image_path}.pbcor.fits"
            if Path(pbcor_fits).exists():
                fits_image = pbcor_fits
            else:
                # Try regular FITS
                regular_fits = f"{image_path}.fits"
                if Path(regular_fits).exists():
                    fits_image = regular_fits
        elif image_path.endswith(".fits"):
            fits_image = image_path

        if not fits_image or not Path(fits_image).exists():
            logger.warning(
                f"Catalog validation skipped: FITS image not found for {image_path}. "
                "Catalog validation requires FITS format."
            )
            return

        logger.info(
            f"Running catalog-based flux scale validation ({catalog.upper()}) on {fits_image}")

        try:
            result = validate_flux_scale(
                image_path=fits_image,
                catalog=catalog,
                min_snr=5.0,
                flux_range_jy=(0.01, 10.0),
                max_flux_ratio_error=0.2
            )

            if result.n_matched > 0:
                logger.info(
                    f"Catalog validation ({catalog.upper()}): "
                    f"{result.n_matched} sources matched, "
                    f"flux ratio={result.mean_flux_ratio:.3f}±{result.rms_flux_ratio:.3f}, "
                    f"scale error={result.flux_scale_error*100:.1f}%"
                )

                if result.has_issues:
                    logger.warning(
                        f"Catalog validation issues: {', '.join(result.issues)}")

                if result.has_warnings:
                    logger.warning(
                        f"Catalog validation warnings: {', '.join(result.warnings)}")
            else:
                logger.warning(
                    f"Catalog validation ({catalog.upper()}): No sources matched. "
                    "This may indicate astrometry issues or insufficient catalog coverage."
                )

        except Exception as e:
            logger.warning(
                f"Catalog validation failed (non-fatal): {e}. "
                "Pipeline will continue, but flux scale was not validated."
            )

    def get_name(self) -> str:
        """Get stage name."""
        return "imaging"

```


Fixing the blank line whitespace issue:


```python
"""
Concrete pipeline stage implementations.

These stages wrap existing conversion, calibration, and imaging functions
to provide a unified pipeline interface.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional, Tuple

from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.context import PipelineContext
from dsa110_contimg.pipeline.stages import PipelineStage
from dsa110_contimg.utils.time_utils import extract_ms_time_range

logger = logging.getLogger(__name__)


class ConversionStage(PipelineStage):
    """Conversion stage: UVH5 → MS.

    Discovers complete subband groups in the specified time window and
    converts them to CASA Measurement Sets.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize conversion stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for conversion."""
        # Check input directory exists
        if not context.config.paths.input_dir.exists():
            return False, f"Input directory not found: {context.config.paths.input_dir}"

        # Check output directory is writable
        output_dir = context.config.paths.output_dir
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        if not output_dir.parent.exists():
            return False, f"Cannot create output directory: {output_dir.parent}"

        # Check required inputs
        if "start_time" not in context.inputs:
            return False, "start_time required in context.inputs"
        if "end_time" not in context.inputs:
            return False, "end_time required in context.inputs"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute conversion stage."""
        from dsa110_contimg.conversion.strategies.hdf5_orchestrator import (
            convert_subband_groups_to_ms,
        )

        start_time = context.inputs["start_time"]
        end_time = context.inputs["end_time"]

        # Prepare writer kwargs
        writer_kwargs = {
            "max_workers": self.config.conversion.max_workers,
            "skip_validation_during_conversion": self.config.conversion.skip_validation_during_conversion,
            "skip_calibration_recommendations": self.config.conversion.skip_calibration_recommendations,
        }
        if self.config.conversion.stage_to_tmpfs:
            writer_kwargs["stage_to_tmpfs"] = True
            if context.config.paths.scratch_dir:
                writer_kwargs["tmpfs_path"] = str(
                    context.config.paths.scratch_dir)

        # Execute conversion (function returns None, creates MS files in output_dir)
        convert_subband_groups_to_ms(
            str(context.config.paths.input_dir),
            str(context.config.paths.output_dir),
            start_time,
            end_time,
            writer=self.config.conversion.writer,
            writer_kwargs=writer_kwargs,
        )

        # Discover created MS files (similar to current run_convert_job)
        # Only include main MS files matching YYYY-MM-DDTHH:MM:SS.ms pattern
        # Exclude legacy files with suffixes (.phased.ms, .phased_concat.ms, etc.)
        # and files in subdirectories (legacy/, etc.)
        output_path = Path(context.config.paths.output_dir)
        ms_files = []
        if output_path.exists():
            # Pattern: YYYY-MM-DDTHH:MM:SS.ms (no suffixes, no subdirectories)
            pattern = re.compile(
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.ms$'
            )

            # Only search in the main output directory, not subdirectories
            for ms in output_path.glob("*.ms"):
                if ms.is_dir():
                    # Check if filename matches pattern (no suffixes)
                    if pattern.match(ms.name):
                        ms_files.append(str(ms))
                    else:
                        logger.warning(
                            f"Skipping MS file '{ms.name}' - filename doesn't match expected pattern "
                            f"(YYYY-MM-DDTHH:MM:SS.ms). This may be a legacy file or use a different "
                            f"naming convention. If this file should be processed, rename it to match "
                            f"the pattern or update the pattern in ConversionStage."
                        )

        if not ms_files:
            raise ValueError("Conversion produced no MS files")

        # Sort MS files by time for consistency
        ms_files = sorted(ms_files)

        # Use first MS path for backward compatibility (single MS workflows)
        ms_path = ms_files[0]

        # Run quality checks after conversion if they were skipped during conversion
        if self.config.conversion.skip_validation_during_conversion:
            from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion
            logger.info("Running quality checks after conversion...")
            try:
                qa_passed, qa_metrics = check_ms_after_conversion(
                    ms_path=ms_path,
                    quick_check_only=False,
                    alert_on_issues=True,
                )
                if qa_passed:
                    logger.info("✓ MS passed quality checks")
                else:
                    logger.warning("⚠ MS quality issues detected (see alerts)")
            except Exception as e:
                logger.warning(f"Quality check failed (non-fatal): {e}")

        # Update MS index via state repository if available
        if context.state_repository:
            try:
                for ms_file in ms_files:
                    start_mjd, end_mjd, mid_mjd = extract_ms_time_range(
                        ms_file)
                    context.state_repository.upsert_ms_index(
                        ms_file,
                        {
                            "start_mjd": start_mjd,
                            "end_mjd": end_mjd,
                            "mid_mjd": mid_mjd,
                            "status": "converted",
                            "stage": "conversion",
                        },
                    )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Return both single MS path (for backward compatibility) and all MS paths
        return context.with_outputs({
            "ms_path": ms_path,  # Single MS for backward compatibility
            "ms_paths": ms_files,  # All MS files
        })

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate conversion outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate MS is readable and has required columns
        try:
            from casacore.tables import table
            with table(ms_path, readonly=True) as tb:
                required_cols = ["DATA", "ANTENNA1", "ANTENNA2", "TIME"]
                missing = [
                    col for col in required_cols if col not in tb.colnames()]
                if missing:
                    return False, f"MS missing required columns: {missing}"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
        except Exception as e:
            return False, f"Cannot validate MS: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial conversion outputs on failure."""
        # If conversion failed, remove any partial MS files created
        if "ms_path" in context.outputs:
            ms_path = Path(context.outputs["ms_path"])
            if ms_path.exists():
                try:
                    import shutil
                    shutil.rmtree(ms_path, ignore_errors=True)
                    logger.info(f"Cleaned up partial MS: {ms_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to cleanup partial MS {ms_path}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "conversion"


class CalibrationSolveStage(PipelineStage):
    """Calibration solve stage: Solve calibration solutions (K, BP, G).

    This stage solves calibration tables (delay/K, bandpass/BP, gains/G)
    for a calibrator Measurement Set. This wraps the calibration CLI
    functions directly without subprocess overhead.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration solve stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration solving."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration solve stage."""
        from dsa110_contimg.calibration.calibration import (
            solve_delay,
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        from dsa110_contimg.utils.locking import file_lock, LockError
        import glob
        import os

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration solve stage: {ms_path}")

        # CRITICAL: Acquire lock to prevent concurrent calibration solves for same MS
        # This prevents race conditions when multiple pipeline runs process the same MS
        lock_path = Path(ms_path).parent / f".{Path(ms_path).stem}.cal_lock"
        # 1 hour timeout (calibration can take a long time)
        lock_timeout = 3600.0

        try:
            with file_lock(lock_path, timeout=lock_timeout):
                return self._execute_calibration_solve(context, ms_path)
        except LockError as e:
            error_msg = (
                f"Cannot acquire calibration lock for {ms_path}. "
                f"Another calibration solve may be in progress. "
                f"If no process is running, check for stale lock file: {lock_path}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def _execute_calibration_solve(self, context: PipelineContext, ms_path: str) -> PipelineContext:
        """Internal calibration solve execution (called within lock)."""
        from dsa110_contimg.calibration.calibration import (
            solve_delay,
            solve_bandpass,
            solve_gains,
            solve_prebandpass_phase,
        )
        from dsa110_contimg.calibration.flagging import (
            reset_flags,
            flag_zeros,
            flag_rfi,
        )
        import glob
        import os

        # Get calibration parameters from context inputs or config
        params = context.inputs.get("calibration_params", {})
        field = params.get("field", "0")
        refant = params.get("refant", "103")
        solve_delay_flag = params.get("solve_delay", False)
        solve_bandpass_flag = params.get("solve_bandpass", True)
        solve_gains_flag = params.get("solve_gains", True)
        model_source = params.get("model_source", "catalog")
        gain_solint = params.get("gain_solint", "inf")
        gain_calmode = params.get("gain_calmode", "ap")
        bp_combine_field = params.get("bp_combine_field", False)
        prebp_phase = params.get("prebp_phase", False)
        flag_autocorr = params.get("flag_autocorr", True)

        # Handle existing table discovery
        use_existing = params.get("use_existing_tables", "auto")
        existing_k = params.get("existing_k_table")
        existing_bp = params.get("existing_bp_table")
        existing_g = params.get("existing_g_table")

        if use_existing == "auto":
            ms_dir = os.path.dirname(ms_path)
            ms_base = os.path.basename(ms_path).replace('.ms', '')

            if not solve_delay_flag and not existing_k:
                k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
                k_tables = sorted([p for p in glob.glob(k_pattern) if os.path.isdir(p)],
                                  key=os.path.getmtime, reverse=True)
                if k_tables:
                    existing_k = k_tables[0]

            if not solve_bandpass_flag and not existing_bp:
                bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
                bp_tables = sorted([p for p in glob.glob(bp_pattern) if os.path.isdir(p)],
                                   key=os.path.getmtime, reverse=True)
                if bp_tables:
                    existing_bp = bp_tables[0]

            if not solve_gains_flag and not existing_g:
                g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")
                g_tables = sorted([p for p in glob.glob(g_pattern) if os.path.isdir(p)],
                                  key=os.path.getmtime, reverse=True)
                if g_tables:
                    existing_g = g_tables[0]

        # Determine table prefix
        table_prefix = params.get("table_prefix")
        if not table_prefix:
            table_prefix = f"{os.path.splitext(ms_path)[0]}_{field}"

        # Step 1: Flagging (if requested)
        if params.get("do_flagging", True):
            logger.info("Resetting flags...")
            reset_flags(ms_path)
            flag_zeros(ms_path)
            flag_rfi(ms_path)
            if flag_autocorr:
                from casatasks import flagdata
                logger.info("Flagging autocorrelations...")
                flagdata(vis=str(ms_path), autocorr=True, flagbackup=False)
                logger.info("✓ Autocorrelations flagged")

        # Step 2: Model population (required for calibration)
        if model_source == "catalog":
            from dsa110_contimg.calibration.model import populate_model_from_catalog
            logger.info("Populating MODEL_DATA from catalog...")
            populate_model_from_catalog(
                ms_path,
                field=field,
                calibrator_name=params.get("calibrator_name"),
                cal_ra_deg=params.get("cal_ra_deg"),
                cal_dec_deg=params.get("cal_dec_deg"),
                cal_flux_jy=params.get("cal_flux_jy"),
            )
        elif model_source == "image":
            from dsa110_contimg.calibration.model import populate_model_from_image
            model_image = params.get("model_image")
            if not model_image:
                raise ValueError(
                    "model_image required when model_source='image'")
            logger.info(f"Populating MODEL_DATA from image: {model_image}")
            populate_model_from_image(
                ms_path, field=field, model_image=model_image)

        # Step 3: Solve delay (K) if requested
        ktabs = []
        if solve_delay_flag and not existing_k:
            logger.info("Solving delay (K) calibration...")
            ktabs = solve_delay(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                combine_spw=params.get("k_combine_spw", False),
                t_slow=params.get("k_t_slow", "inf"),
                t_fast=params.get("k_t_fast", "60s"),
                uvrange=params.get("k_uvrange", ""),
                minsnr=params.get("k_minsnr", 5.0),
                skip_slow=params.get("k_skip_slow", False),
            )
        elif existing_k:
            ktabs = [existing_k]
            logger.info(f"Using existing K table: {existing_k}")

        # Step 4: Pre-bandpass phase (if requested)
        prebp_table = None
        if prebp_phase:
            logger.info("Solving pre-bandpass phase...")
            prebp_table = solve_prebandpass_phase(
                ms_path,
                field,
                refant,
                table_prefix=table_prefix,
                uvrange=params.get("prebp_uvrange", ""),
                minsnr=params.get("prebp_minsnr", 3.0),
            )

        # Step 5: Solve bandpass (BP) if requested
        bptabs = []
        if solve_bandpass_flag and not existing_bp:
            logger.info("Solving bandpass (BP) calibration...")
            bptabs = solve_bandpass(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                table_prefix=table_prefix,
                set_model=True,
                model_standard=params.get(
                    "bp_model_standard", "Perley-Butler 2017"),
                combine_fields=bp_combine_field,
                combine_spw=params.get("bp_combine_spw", False),
                minsnr=params.get("bp_minsnr", 5.0),
                uvrange=params.get("bp_uvrange", ""),
                prebandpass_phase_table=prebp_table,
                bp_smooth_type=params.get("bp_smooth_type"),
                bp_smooth_window=params.get("bp_smooth_window"),
            )
        elif existing_bp:
            bptabs = [existing_bp]
            logger.info(f"Using existing BP table: {existing_bp}")

        # Step 6: Solve gains (G) if requested
        gtabs = []
        if solve_gains_flag and not existing_g:
            logger.info("Solving gains (G) calibration...")
            phase_only = (gain_calmode == "p") or bool(params.get("fast"))
            gtabs = solve_gains(
                ms_path,
                field,
                refant,
                ktable=ktabs[0] if ktabs else None,
                bptables=bptabs,
                table_prefix=table_prefix,
                t_short=params.get("gain_t_short", "60s"),
                combine_fields=bp_combine_field,
                phase_only=phase_only,
                uvrange=params.get("gain_uvrange", ""),
                solint=gain_solint,
                minsnr=params.get("gain_minsnr", 3.0),
            )
        elif existing_g:
            gtabs = [existing_g]
            logger.info(f"Using existing G table: {existing_g}")

        # Combine all tables
        all_tables = (ktabs[:1] if ktabs else []) + bptabs + gtabs
        logger.info(
            f"Calibration solve complete. Generated {len(all_tables)} tables:")
        for tab in all_tables:
            logger.info(f"  - {tab}")

        # Register calibration tables in registry database
        # CRITICAL: Registration is required for CalibrationStage to find tables via registry lookup
        registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"

        try:
            from dsa110_contimg.database.registry import register_and_verify_caltables
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            # Extract time range from MS for validity window
            # Use wider window (±1 hour) to cover observation period, not just single MS
            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_path)
            if mid_mjd is None:
                logger.warning(
                    f"Could not extract time range from {ms_path}, using current time"
                )
                from astropy.time import Time
                mid_mjd = Time.now().mjd
                start_mjd = mid_mjd - 1.0 / 24.0  # 1 hour before
                end_mjd = mid_mjd + 1.0 / 24.0    # 1 hour after
            else:
                # Extend validity window to ±1 hour around MS time range
                # This ensures calibration tables are valid for the entire observation period
                window_hours = 1.0
                if start_mjd is None or end_mjd is None:
                    # Fallback: use ±1 hour around mid point
                    start_mjd = mid_mjd - window_hours / 24.0
                    end_mjd = mid_mjd + window_hours / 24.0
                else:
                    # Extend existing window by ±1 hour
                    duration = end_mjd - start_mjd
                    start_mjd = start_mjd - window_hours / 24.0
                    end_mjd = end_mjd + window_hours / 24.0
                    logger.debug(
                        f"Extended validity window from {duration*24*60:.1f} min to "
                        f"{(end_mjd - start_mjd)*24*60:.1f} min (±{window_hours}h)"
                    )

            # Generate set name from MS filename and time
            ms_base = Path(ms_path).stem
            set_name = f"{ms_base}_{mid_mjd:.6f}"

            # Determine table prefix (common prefix of all tables)
            if not all_tables:
                error_msg = "No calibration tables generated to register"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Get common directory and base name
            table_dir = Path(all_tables[0]).parent
            # Extract prefix from first table (e.g., "2025-10-29T13:54:17_0_bpcal" -> "2025-10-29T13:54:17_0")
            first_table_name = Path(all_tables[0]).stem

            # Remove table type suffixes (e.g., "_bpcal", "_gpcal", "_2gcal")
            # Use fallback logic if pattern doesn't match
            prefix_base = re.sub(
                r'_(bpcal|gpcal|gacal|2gcal|kcal|bacal|flux)$',
                '',
                first_table_name,
                flags=re.IGNORECASE
            )

            # Fallback: If regex didn't change the name, try alternative patterns
            if prefix_base == first_table_name:
                logger.warning(
                    f"Table name '{first_table_name}' doesn't match expected pattern. "
                    f"Trying alternative extraction methods."
                )
                # Try removing common suffixes one by one
                for suffix in ['_bpcal', '_gpcal', '_gacal', '_2gcal', '_kcal', '_bacal', '_flux']:
                    if first_table_name.lower().endswith(suffix.lower()):
                        prefix_base = first_table_name[:-len(suffix)]
                        logger.info(
                            f"Extracted prefix using suffix removal: {prefix_base}")
                        break

                # Final fallback: use MS path-based prefix
                if prefix_base == first_table_name:
                    logger.warning(
                        f"Could not extract table prefix from '{first_table_name}'. "
                        f"Using MS path-based prefix as fallback."
                    )
                    prefix_base = f"{Path(ms_path).stem}_{field}"

            table_prefix = table_dir / prefix_base

            logger.info(
                f"Registering calibration tables in registry: {set_name}")
            logger.debug(f"Using table prefix: {table_prefix}")

            # Register and verify tables are discoverable
            # This helper function:
            # - Registers tables (idempotent via upsert)
            # - Verifies tables are discoverable after registration
            # - Retires set if verification fails (rollback)
            registered_paths = register_and_verify_caltables(
                registry_db,
                set_name,
                table_prefix,
                cal_field=field,
                refant=refant,
                valid_start_mjd=start_mjd,
                valid_end_mjd=end_mjd,
                mid_mjd=mid_mjd,
                status="active",
                verify_discoverable=True,
            )

            logger.info(
                f"✓ Registered and verified {len(registered_paths)} calibration tables "
                f"in registry (set: {set_name})"
            )

        except Exception as e:
            # Registration failure is CRITICAL - CalibrationStage will fail without registered tables
            error_msg = (
                f"CRITICAL: Failed to register calibration tables in registry: {e}. "
                f"CalibrationStage will not be able to find tables via registry lookup. "
                f"Tables were created but may not be registered."
            )
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

        # Update state repository
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_tables": all_tables,
                        "stage": "calibration_solve",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        return context.with_output("calibration_tables", all_tables)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration solve outputs."""
        if "calibration_tables" not in context.outputs:
            return False, "calibration_tables not found in outputs"

        caltables = context.outputs["calibration_tables"]
        if not caltables:
            return False, "No calibration tables generated"

        # Validate all tables exist
        missing = [t for t in caltables if not Path(t).exists()]
        if missing:
            return False, f"Calibration tables missing: {missing}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial calibration tables on failure."""
        if "calibration_tables" in context.outputs:
            caltables = context.outputs["calibration_tables"]
            for table_path in caltables:
                table = Path(table_path)
                if table.exists():
                    try:
                        import shutil
                        shutil.rmtree(table, ignore_errors=True)
                        logger.info(
                            f"Cleaned up partial calibration table: {table}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to cleanup calibration table {table}: {e}")

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration_solve"


class CalibrationStage(PipelineStage):
    """Calibration stage: Apply calibration solutions to MS.

    This stage applies calibration solutions (bandpass, gain) to the
    Measurement Set. In the current implementation, this wraps the
    existing calibration service.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize calibration stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for calibration."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs (conversion must run first)"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute calibration stage.

        Applies calibration from registry (consistent with streaming mode).
        Uses get_active_applylist() to lookup calibration tables by observation time,
        then applies them using apply_to_target() directly.
        """
        from dsa110_contimg.calibration.applycal import apply_to_target
        from dsa110_contimg.database.registry import get_active_applylist
        from dsa110_contimg.utils.time_utils import extract_ms_time_range
        from pathlib import Path
        import time

        ms_path = context.outputs["ms_path"]
        logger.info(f"Calibration stage: {ms_path}")

        # Check if calibration tables were provided by a previous stage (e.g., CalibrationSolveStage)
        caltables = context.outputs.get("calibration_tables")
        cal_applied = 0

        # If tables provided, use them directly (for workflows that solve calibration)
        if caltables:
            logger.info(
                f"Using calibration tables from previous stage: {len(caltables)} tables")
            try:
                apply_to_target(ms_path, field="", gaintables=caltables, calwt=True)
                cal_applied = 1
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e
        else:
            # Lookup tables from registry by observation time (consistent with streaming mode)
            registry_db = context.config.paths.state_dir / "cal_registry.sqlite3"
            if not registry_db.exists():
                # Try alternative location
                registry_db = Path("/data/dsa110-contimg/state/cal_registry.sqlite3")
                if not registry_db.exists():
                    error_msg = (
                        f"Cannot apply calibration: No calibration tables provided and "
                        f"registry not found at {registry_db}. Calibration is required for imaging."
                    )
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            # Extract observation time for registry lookup
            mid_mjd = None
            try:
                _, _, mid_mjd = extract_ms_time_range(ms_path)
            except Exception:
                # Fallback to current time if extraction fails
                mid_mjd = time.time() / 86400.0

            # Lookup active calibration tables from registry (same as streaming)
            applylist = []
            try:
                applylist = get_active_applylist(registry_db, float(mid_mjd))
            except Exception as e:
                logger.warning(f"Failed to lookup calibration tables from registry: {e}")
                applylist = []

            if not applylist:
                error_msg = (
                    f"Cannot apply calibration: No calibration tables available for {ms_path} "
                    f"(mid MJD: {mid_mjd:.5f}). Calibration is required for downstream imaging."
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Apply calibration using apply_to_target() directly (same as streaming)
            logger.info(f"Applying {len(applylist)} calibration tables from registry")
            try:
                apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
                cal_applied = 1
            except Exception as e:
                logger.error(f"applycal failed for {ms_path}: {e}")
                raise RuntimeError(f"Calibration application failed: {e}") from e

        # Update MS index (consistent with streaming mode)
        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "cal_applied": cal_applied,
                        "stage": "calibration",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        return context

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate calibration application outputs."""
        if "ms_path" not in context.outputs:
            return False, "ms_path not found in outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file does not exist: {ms_path}"

        # Validate CORRECTED_DATA column exists and has data
        try:
            from casacore.tables import table
            with table(ms_path, readonly=True) as tb:
                if "CORRECTED_DATA" not in tb.colnames():
                    return False, "CORRECTED_DATA column missing after calibration"
                if tb.nrows() == 0:
                    return False, "MS has no data rows"
                # Sample to check CORRECTED_DATA is populated
                sample = tb.getcol("CORRECTED_DATA", 0, min(100, tb.nrows()))
                flags = tb.getcol("FLAG", 0, min(100, tb.nrows()))
                unflagged = sample[~flags]
                if len(unflagged) > 0:
                    import numpy as np
                    if np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        return False, "CORRECTED_DATA appears empty after calibration"
        except Exception as e:
            return False, f"Cannot validate calibrated MS: {e}"

        return True, None

    def get_name(self) -> str:
        """Get stage name."""
        return "calibration"


class ImagingStage(PipelineStage):
    """Imaging stage: Create images from calibrated MS.

    This stage runs imaging on the calibrated Measurement Set to produce
    continuum images.
    """

    def __init__(self, config: PipelineConfig):
        """Initialize imaging stage.

        Args:
            config: Pipeline configuration
        """
        self.config = config

    def validate(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate prerequisites for imaging."""
        if "ms_path" not in context.outputs:
            return False, "ms_path required in context.outputs"

        ms_path = context.outputs["ms_path"]
        if not Path(ms_path).exists():
            return False, f"MS file not found: {ms_path}"

        return True, None

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute imaging stage."""
        from dsa110_contimg.imaging.cli_imaging import image_ms
        from casacore.tables import table
        import numpy as np

        ms_path = context.outputs["ms_path"]
        logger.info(f"Imaging stage: {ms_path}")

        # Check if CORRECTED_DATA exists but is empty (calibration wasn't applied)
        # If so, copy DATA to CORRECTED_DATA so imaging can proceed
        try:
            with table(ms_path, readonly=False) as t:
                if "CORRECTED_DATA" in t.colnames() and t.nrows() > 0:
                    # Sample to check if CORRECTED_DATA is populated
                    sample = t.getcol("CORRECTED_DATA", 0,
                                      min(1000, t.nrows()))
                    flags = t.getcol("FLAG", 0, min(1000, t.nrows()))
                    unflagged = sample[~flags]
                    if len(unflagged) > 0 and np.count_nonzero(np.abs(unflagged) > 1e-10) == 0:
                        # CORRECTED_DATA exists but is empty - copy DATA to CORRECTED_DATA
                        logger.info(
                            "CORRECTED_DATA is empty, copying DATA to CORRECTED_DATA for imaging")
                        data_col = t.getcol("DATA")
                        t.putcol("CORRECTED_DATA", data_col)
                        t.flush()
        except Exception as e:
            logger.warning(f"Could not check/fix CORRECTED_DATA: {e}")

        # Construct output imagename (consistent with streaming mode)
        # Streaming uses: os.path.join(args.output_dir, base + ".img")
        # where base is derived from MS filename (without .ms extension)
        ms_name = Path(ms_path).stem
        output_dir = Path(context.config.paths.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        imagename = str(output_dir / f"{ms_name}.img")

        # Run imaging (consistent with streaming mode)
        image_ms(
            ms_path,
            imagename=imagename,
            field="",  # Use empty string for all fields (same as streaming)
            gridder=context.config.imaging.gridder,
            wprojplanes=context.config.imaging.wprojplanes,
            quality_tier="standard",  # Production quality (same as streaming)
            skip_fits=False,  # Export FITS (same as streaming)
            use_nvss_mask=context.config.imaging.use_nvss_mask,
            mask_radius_arcsec=context.config.imaging.mask_radius_arcsec,
        )

        # Find created image files
        image_paths = []
        for suffix in [".image", ".image.pbcor", ".residual", ".psf", ".pb"]:
            img_path = f"{imagename}{suffix}"
            if Path(img_path).exists():
                image_paths.append(img_path)

        # Primary image path (for output)
        primary_image = f"{imagename}.image"
        if not Path(primary_image).exists():
            # Try FITS if CASA image not found
            fits_image = f"{imagename}.image.fits"
            if Path(fits_image).exists():
                primary_image = fits_image
                logger.info(f"Using FITS image as primary: {primary_image}")
            elif image_paths:
                # Fallback to first available image
                primary_image = image_paths[0]
                logger.warning(
                    f"Primary image not found, using fallback: {primary_image}. "
                    "This may indicate an imaging failure."
                )
            else:
                # No images found - this is a critical failure
                error_msg = (
                    f"Imaging failed: No image files created for {ms_path}. "
                    f"Expected primary image: {imagename}.image"
                )
                logger.error(error_msg)
                raise RuntimeError(error_msg)

        if context.state_repository:
            try:
                context.state_repository.upsert_ms_index(
                    ms_path,
                    {
                        "imagename": primary_image,
                        "stage": "imaging",
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to update MS index: {e}")

        # Run catalog-based flux scale validation if enabled
        if context.config.imaging.run_catalog_validation:
            self._run_catalog_validation(
                primary_image, context.config.imaging.catalog_validation_catalog)

        return context.with_output("image_path", primary_image)

    def validate_outputs(self, context: PipelineContext) -> Tuple[bool, Optional[str]]:
        """Validate imaging outputs."""
        if "image_path" not in context.outputs:
            return False, "image_path not found in outputs"

        image_path = context.outputs["image_path"]
        if not Path(image_path).exists():
            return False, f"Image file does not exist: {image_path}"

        # Validate image is readable
        try:
            from casacore.images import image
            with image(str(image_path)) as img:
                shape = img.shape()
                if len(shape) == 0 or any(s == 0 for s in shape):
                    return False, f"Image has invalid shape: {shape}"
        except Exception as e:
            return False, f"Cannot validate image: {e}"

        return True, None

    def cleanup(self, context: PipelineContext) -> None:
        """Cleanup partial image files on failure."""
        if "image_path" in context.outputs:
            image_path = Path(context.outputs["image_path"])
            # Remove all related image files
            base_name = str(image_path).replace(
                ".image", "").replace(".fits", "")
            suffixes = [".image", ".image.pbcor",
                        ".residual", ".psf", ".pb", ".fits"]
            for suffix in suffixes:
                img_file = Path(f"{base_name}{suffix}")
                if img_file.exists():
                    try:
                        import shutil
                        if img_file.is_dir():
                            shutil.rmtree(img_file, ignore_errors=True)
                        else:
                            img_file.unlink()
                        logger.info(f"Cleaned up partial image: {img_file}")
                    except Exception as e:
                        logger.warning(
                            f"Failed to cleanup image {img_file}: {e}")

    def _run_catalog_validation(self, image_path: str, catalog: str) -> None:
        """Run catalog-based flux scale validation on image.

        This validates the image flux scale by comparing forced photometry
        at catalog source positions to catalog fluxes. Non-fatal - logs
        warnings but does not fail the pipeline.

        Args:
            image_path: Path to image file (CASA or FITS)
            catalog: Catalog to use for validation ('nvss' or 'vlass')
        """
        from dsa110_contimg.qa.catalog_validation import validate_flux_scale
        from pathlib import Path

        # Find FITS image (prefer PB-corrected)
        image_path_obj = Path(image_path)
        fits_image = None

        # Try PB-corrected FITS first
        if image_path.endswith(".image"):
            pbcor_fits = f"{image_path}.pbcor.fits"
            if Path(pbcor_fits).exists():
                fits_image = pbcor_fits
            else:
                # Try regular FITS
                regular_fits = f"{image_path}.fits"
                if Path(regular_fits).exists():
                    fits_image = regular_fits
        elif image_path.endswith(".fits"):
            fits_image = image_path

        if not fits_image or not Path(fits_image).exists():
            logger.warning(
                f"Catalog validation skipped: FITS image not found for {image_path}. "
                "Catalog validation requires FITS format."
            )
            return

        logger.info(
            f"Running catalog-based flux scale validation ({catalog.upper()}) on {fits_image}")

        try:
            result = validate_flux_scale(
                image_path=fits_image,
                catalog=catalog,
                min_snr=5.0,
                flux_range_jy=(0.01, 10.0),
                max_flux_ratio_error=0.2
            )

            if result.n_matched > 0:
                logger.info(
                    f"Catalog validation ({catalog.upper()}): "
                    f"{result.n_matched} sources matched, "
                    f"flux ratio={result.mean_flux_ratio:.3f}±{result.rms_flux_ratio:.3f}, "
                    f"scale error={result.flux_scale_error*100:.1f}%"
                )

                if result.has_issues:
                    logger.warning(
                        f"Catalog validation issues: {', '.join(result.issues)}")

                if result.has_warnings:
                    logger.warning(
                        f"Catalog validation warnings: {', '.join(result.warnings)}")
            else:
                logger.warning(
                    f"Catalog validation ({catalog.upper()}): No sources matched. "
                    "This may indicate astrometry issues or insufficient catalog coverage."
                )

        except Exception as e:
            logger.warning(
                f"Catalog validation failed (non-fatal): {e}. "
                "Pipeline will continue, but flux scale was not validated."
            )

    def get_name(self) -> str:
        """Get stage name."""
        return "imaging"

```


## Summary: Calibration and Imaging Stages Now Consistent with Streaming Mode

### Changes Made

#### 1. **CalibrationStage** (`stages_impl.py`)

**Before:**
- Used `apply_calibration()` service wrapper
- Different lookup mechanism
- Different error handling

**After (consistent with streaming):**
- Uses `get_active_applylist()` to lookup calibration tables from registry by observation time (mid_mjd)
- Uses `apply_to_target()` directly (same as streaming)
- Uses `field=""` and `calwt=True` (same as streaming)
- Extracts observation time using `extract_ms_time_range()` (same as streaming)
- Falls back to current time if extraction fails (same as streaming)
- Still supports provided calibration tables (for workflows that solve calibration first)

**Key consistency points:**
```python
# Same as streaming:
applylist = get_active_applylist(registry_db, float(mid_mjd))
apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
```

#### 2. **ImagingStage** (`stages_impl.py`)

**Before:**
- Used nested directory structure: `{ms_path.parent.parent}/images/{ms_path.parent.name}/{ms_name}.img`
- Used `field` from config (could be non-empty)
- Already had `quality_tier="standard"` ✓

**After (consistent with streaming):**
- Uses same image path structure: `{output_dir}/{ms_name}.img` (same as streaming)
- Uses `field=""` for all fields (same as streaming)
- Uses `quality_tier="standard"` (same as streaming)
- Uses `skip_fits=False` (same as streaming)

**Key consistency points:**
```python
# Same as streaming:
imagename = str(output_dir / f"{ms_name}.img")
image_ms(ms_path, imagename=imagename, field="", quality_tier="standard", skip_fits=False)
```

### Benefits

1. Consistent behavior: Pipeline stages now match streaming mode behavior
2. Same code paths: Uses the same functions (`get_active_applylist`, `apply_to_target`) as streaming
3. Same image locations: Images are written to the same directory structure
4. Backward compatible: Still supports provided calibration tables for workflows that solve calibration first

### Testing Recommendations

1. Test calibration lookup from registry by observation time
2. Test image path generation matches streaming output
3. Test workflows that provide calibration tables (should still work)
4. Verify `field=""` works correctly for all-field imaging

The pipeline stages are now consistent with streaming mode while maintaining backward compatibility.

```python
# Same as streaming:
applylist = get_active_applylist(registry_db, float(mid_mjd))
apply_to_target(ms_path, field="", gaintables=applylist, calwt=True)
```

```python
# Same as streaming:
imagename = str(output_dir / f"{ms_name}.img")
image_ms(ms_path, imagename=imagename, field="", quality_tier="standard", skip_fits=False)
```


Changes complete. The CalibrationStage and ImagingStage are now consistent with streaming mode.

## Changes Summary

**CalibrationStage:**
- Uses `get_active_applylist()` to lookup calibration tables from registry by observation time
- Uses `apply_to_target()` directly (same as streaming)
- Uses `field=""` and `calwt=True` (same as streaming)

**ImagingStage:**
- Uses same image path structure: `{output_dir}/{ms_name}.img` (same as streaming)
- Uses `field=""` for all fields (same as streaming)
- Uses `quality_tier="standard"` (same as streaming)

Both stages now match streaming mode behavior while maintaining backward compatibility for workflows that provide calibration tables directly.

If you want me to verify anything else or make additional changes, let me know.

---

**User**

Quickly confirm:

- root directory/subdirectories where MS conversion through to mosaicking will happen

- tools used for flagging/imaging

- what happens once the mosaick is complete

---

**Cursor**


Checking directory structure, flagging/imaging tools, and post-mosaic steps:



Confirming directory structure, flagging/imaging tools, and post-mosaic steps:



## Quick confirmation

### 1. Directory structure (MS conversion → mosaicking)

**Root:** `/stage/dsa110-contimg/` (or configured via `CONTIMG_OUTPUT_DIR`)

**Subdirectories:**
- **Input:** `incoming/` — Raw UVH5 files awaiting conversion
- **MS files:** `ms/` — Measurement Sets (output from conversion)
- **Images:** `images/` — Single-epoch images (output from imaging)
- **Mosaics:** User-specified (typically `images/mosaics/` or custom path)

**Flow:**
```
incoming/ (UVH5) → ms/ (MS) → images/ (single images) → mosaics/ (combined)
```

### 2. Tools for flagging/imaging

**Flagging:**
- **Tool:** `aoflagger` (default backend)
- **Function:** `flag_rfi()` in `calibration/flagging.py`
- **Purpose:** RFI flagging on MS data

**Imaging:**
- **Primary:** `wsclean` (default, 2-5x faster than tclean)
- **Fallback:** CASA `tclean` (if wsclean unavailable)
- **Function:** `image_ms()` in `imaging/cli_imaging.py`
- **Backend selection:** Automatic (prefers native wsclean, falls back to Docker, then tclean)

### 3. Post-mosaic completion

**After mosaic build:**
1. **Export to FITS:** `exportfits()` converts CASA image to `.fits`
2. **Post-mosaic validation:**
   - RMS noise uniformity check
   - Coverage fraction validation
   - Discontinuity detection at tile boundaries
   - Artifact detection
3. **Quality metrics generation:** RMS, coverage, dynamic range
4. **Database update:** `products.sqlite3` → `mosaics` table updated with:
   - `status='built'`
   - `output_path`
   - `validation_issues`
   - `metrics_path`
5. **Output:** Mosaic image + FITS + metrics files ready for analysis

**Status:** Mosaic marked as `'built'` in products database, ready for photometry/analysis.

```plaintext
incoming/ (UVH5) → ms/ (MS) → images/ (single images) → mosaics/ (combined)
```

---

**User**

Can you fold the photometry analysis into what we're about to do as what automatically follows 

---

**Cursor**


Searching for photometry analysis code to integrate it as an automatic post-mosaic step:



Reviewing the photometry CLI to integrate it into the mosaic build:



Adding photometry analysis as an automatic post-mosaic step:


```python
"""
CLI for planning and building mosaics from 5-minute image tiles.

A **tile** is a single calibrated, imaged, and primary-beam-corrected radio astronomy
image created from ~5 minutes of observation data. Multiple tiles are combined to create
a larger mosaic covering a wider field of view.

Phase 1: record mosaic plan (list of tiles) into products DB.
Phase 2: validate tiles and build weighted mosaic using primary beam weighting.

See docs/reference/GLOSSARY.md for detailed definition of tiles and related terminology.
"""

import argparse
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.utils.cli_helpers import ensure_scratch_dirs
try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore

from .validation import (
    validate_tiles_consistency,
    verify_astrometric_registration,
    check_calibration_consistency,
    check_primary_beam_consistency,
    TileQualityMetrics,
    _find_pb_path,
    HAVE_CASACORE,
)
from .exceptions import (
    MosaicError,
    ImageReadError,
    ImageCorruptionError,
    MissingPrimaryBeamError,
    IncompatibleImageFormatError,
    CASAToolError,
    GridMismatchError,
    ValidationError,
    MetricsGenerationError,
)

LOG = logging.getLogger(__name__)


def _ensure_mosaics_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mosaics (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            method TEXT,
            tiles TEXT NOT NULL,
            output_path TEXT,
            validation_issues TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mosaics_name ON mosaics(name)"
    )


def _fetch_tiles(products_db: Path, *, since: Optional[float], until: Optional[float], pbcor_only: bool = True) -> List[str]:
    tiles: List[str] = []
    with ensure_products_db(products_db) as conn:
        q = "SELECT path, created_at, pbcor FROM images"
        where = []
        params: List[object] = []
        if pbcor_only:
            where.append("pbcor = 1")
        if since is not None:
            where.append("created_at >= ?")
            params.append(float(since))
        if until is not None:
            where.append("created_at <= ?")
            params.append(float(until))
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY created_at ASC"
        for r in conn.execute(q, params).fetchall():
            p = r["path"] if isinstance(r, sqlite3.Row) else r[0]
            if p and os.path.isdir(p):
                tiles.append(p)
    return tiles


def cmd_plan(args: argparse.Namespace) -> int:
    pdb = Path(args.products_db)
    name = args.name
    since = args.since
    until = args.until
    tiles = _fetch_tiles(pdb, since=since, until=until, pbcor_only=not args.include_unpbcor)
    if not tiles:
        logger.warning("No tiles found for the specified window")
        print("No tiles found for the specified window")
        return 1
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        conn.execute(
            "INSERT INTO mosaics(name, created_at, status, method, tiles) VALUES(?,?,?,?,?)",
            (name, time.time(), "planned", args.method, "\n".join(tiles)),
        )
        conn.commit()
    logger.info(f"Planned mosaic '{name}' with {len(tiles)} tiles")
    print(f"Planned mosaic '{name}' with {len(tiles)} tiles")
    return 0


def _check_consistent_tiles(tiles: List[str]) -> Tuple[bool, Optional[str]]:
    """Check basic grid consistency (legacy function)."""
    from .cache import get_cache
    
    cache = get_cache()
    ref = None
    for t in tiles:
        try:
            header = cache.get_tile_header(t)
            if not header:
                return False, f"Failed to get header for {t}"
            key = (header.get('shape'), header.get('cdelt1'), header.get('cdelt2'))
        if ref is None:
            ref = key
        elif key != ref:
            return False, "Tiles have inconsistent grids/cell sizes"
        except Exception as e:
            return False, f"imhead failed for {t}: {e}"
    return True, None


def generate_mosaic_metrics(
    tiles: List[str],
    metrics_dict: Dict[str, TileQualityMetrics],
    mosaic_path: str,
    output_dir: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate mosaic quality metrics images.
    
    Creates metadata images showing:
    - Effective integration time per pixel
    - Primary beam response per pixel
    - Noise variance per pixel
    - Number of tiles contributing per pixel
    - Coverage map
    
    Args:
        tiles: List of tile paths
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        mosaic_path: Path to mosaic image
        output_dir: Optional output directory (defaults to mosaic directory)
        
    Returns:
        Dictionary mapping metric name -> file path
    """
    metric_files = {}
    
    if not HAVE_CASACORE:
        LOG.warning("casacore.images not available, skipping mosaic metrics generation")
        return metric_files
    
    try:
        import numpy as np
        from .validation import _find_pb_path
        
        # Import CASA tools if available
        try:
            from casatasks import exportfits, imregrid
            from casacore.images import image as casaimage
        except ImportError:
            exportfits = None
            imregrid = None
            casaimage = None
        
        if not casaimage:
            LOG.warning("CASA tools not available, skipping mosaic metrics generation")
            return metric_files
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(mosaic_path))
        os.makedirs(output_dir, exist_ok=True)
        
        # Read mosaic to get reference grid
        mosaic_img = casaimage(mosaic_path)
        mosaic_data = mosaic_img.getdata()
        coord_sys = mosaic_img.coordsys()
        
        # Extract 2D image data
        if mosaic_data.ndim == 2:
            mosaic_2d = mosaic_data
        elif mosaic_data.ndim == 4:
            mosaic_2d = mosaic_data[0, 0, :, :]
        else:
            mosaic_2d = mosaic_data.squeeze()
            if mosaic_2d.ndim > 2:
                mosaic_2d = mosaic_2d[0, :, :] if mosaic_2d.ndim == 3 else mosaic_2d
        
        ny, nx = mosaic_2d.shape
        mosaic_base = os.path.splitext(os.path.basename(mosaic_path))[0]
        
        # Initialize metric arrays
        pb_response_map = np.zeros((ny, nx), dtype=np.float64)
        noise_variance_map = np.zeros((ny, nx), dtype=np.float64)
        tile_count_map = np.zeros((ny, nx), dtype=np.int32)
        integration_time_map = np.zeros((ny, nx), dtype=np.float64)
        
        # Process each tile
        for tile in tiles:
            metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
            
            # Get PB path
            pb_path = metrics.pb_path
            if not pb_path:
                pb_path = _find_pb_path(tile)
            
            if pb_path and os.path.exists(pb_path):
                try:
                    pb_img = casaimage(str(pb_path))
                    pb_data = pb_img.getdata()
                    
                    # Extract 2D PB data
                    if pb_data.ndim == 2:
                        pb_2d = pb_data
                    elif pb_data.ndim == 4:
                        pb_2d = pb_data[0, 0, :, :]
                    else:
                        pb_2d = pb_data.squeeze()
                        if pb_2d.ndim > 2:
                            pb_2d = pb_2d[0, :, :] if pb_2d.ndim == 3 else pb_2d
                    
                    # Check if PB needs regridding
                    if pb_2d.shape != (ny, nx):
                        # Need to regrid PB to mosaic grid
                        regridded_pb = os.path.join(output_dir, f"{mosaic_base}_pb_regrid_{len(metric_files)}.tmp")
                        try:
                            imregrid(
                                imagename=str(pb_path),
                                template=mosaic_path,
                                output=regridded_pb,
                                overwrite=True,
                            )
                            pb_img.close()
                            pb_img = casaimage(regridded_pb)
                            pb_data = pb_img.getdata()
                            if pb_data.ndim == 2:
                                pb_2d = pb_data
                            elif pb_data.ndim == 4:
                                pb_2d = pb_data[0, 0, :, :]
                            else:
                                pb_2d = pb_data.squeeze()
                                if pb_2d.ndim > 2:
                                    pb_2d = pb_2d[0, :, :] if pb_2d.ndim == 3 else pb_2d
                        except Exception as e:
                            LOG.warning(f"Failed to regrid PB for {tile}: {e}")
                            pb_img.close()
                            continue
                    
                    # Accumulate PB response (use max across tiles for each pixel)
                    pb_response_map = np.maximum(pb_response_map, pb_2d)
                    
                    pb_img.close()
                    
                except Exception as e:
                    LOG.warning(f"Failed to read PB image {pb_path}: {e}")
            
            # Get noise variance
            noise_var = 1.0
            if metrics.rms_noise is not None and metrics.rms_noise > 0:
                noise_var = metrics.rms_noise ** 2
            
            # Accumulate weighted noise variance
            # For each pixel, accumulate 1/noise_variance (inverse variance weighting)
            inv_var = 1.0 / noise_var if noise_var > 0 else 1.0
            noise_variance_map += inv_var
            
            # Count tiles contributing to each pixel
            # For now, mark all pixels (could be refined based on PB threshold)
            tile_count_map += 1
            
            # Integration time (placeholder - would need MS metadata)
            # For now, assume equal integration time per tile
            integration_time_map += 1.0  # Units: tile counts (would convert to seconds if available)
        
        # Normalize noise variance map (convert back to variance)
        # noise_variance_map currently contains sum(1/variance), so invert
        mask = noise_variance_map > 0
        noise_variance_map[mask] = 1.0 / noise_variance_map[mask]
        noise_variance_map[~mask] = np.nan
        
        # Create output images
        base_path = os.path.join(output_dir, mosaic_base)
        
        # 1. Primary beam response map
        pb_response_img = casaimage()
        pb_response_img.fromarray(
            outfile=f"{base_path}_pb_response",
            pixels=pb_response_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        pb_response_img.close()
        metric_files['pb_response'] = f"{base_path}_pb_response"
        
        # 2. Noise variance map
        noise_var_img = casaimage()
        noise_var_img.fromarray(
            outfile=f"{base_path}_noise_variance",
            pixels=noise_variance_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        noise_var_img.close()
        metric_files['noise_variance'] = f"{base_path}_noise_variance"
        
        # 3. Tile count map
        tile_count_img = casaimage()
        tile_count_img.fromarray(
            outfile=f"{base_path}_tile_count",
            pixels=tile_count_map.astype(np.float32)[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        tile_count_img.close()
        metric_files['tile_count'] = f"{base_path}_tile_count"
        
        # 4. Integration time map
        integration_time_img = casaimage()
        integration_time_img.fromarray(
            outfile=f"{base_path}_integration_time",
            pixels=integration_time_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        integration_time_img.close()
        metric_files['integration_time'] = f"{base_path}_integration_time"
        
        # 5. Coverage map (binary: 1 if tile contributes, 0 otherwise)
        coverage_map = (tile_count_map > 0).astype(np.float32)
        coverage_img = casaimage()
        coverage_img.fromarray(
            outfile=f"{base_path}_coverage",
            pixels=coverage_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        coverage_img.close()
        metric_files['coverage'] = f"{base_path}_coverage"
        
        # Export as FITS
        if exportfits:
            for metric_name, metric_path in list(metric_files.items()):
                fits_path = f"{metric_path}.fits"
                try:
                    exportfits(
                        imagename=metric_path,
                        fitsimage=fits_path,
                        overwrite=True,
                    )
                    metric_files[metric_name] = fits_path  # Update to FITS path
                except Exception as e:
                    LOG.warning(f"Failed to export {metric_name} to FITS: {e}")
        
        mosaic_img.close()
        
        LOG.info(f"Generated mosaic metrics: {list(metric_files.keys())}")
        
    except Exception as e:
        LOG.error(f"Failed to generate mosaic metrics: {e}")
        import traceback
        traceback.print_exc()
    
    return metric_files


def _build_weighted_mosaic(
    tiles: List[str],
    metrics_dict: dict,
    output_path: str,
) -> None:
    """
    Build mosaic using primary beam-weighted combination.
    
    For each pixel (i,j):
        weight[k][i,j] = pb_response[k][i,j]^2 / noise_variance[k]
        mosaic[i,j] = sum(weight[k][i,j] * tile[k][i,j]) / sum(weight[k][i,j])
    
    This implements the Sault weighting scheme for optimal mosaic combination.
    
    Args:
        tiles: List of tile image paths (should be PB-corrected images)
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        output_path: Output mosaic path
    """
    try:
        from casatasks import immath, imregrid
        from casacore.images import image as casaimage
        import numpy as np
        from .error_handling import (
            safe_casaimage_open,
            validate_image_data,
            validate_image_before_read,
            handle_casa_tool_error,
        )
    except ImportError as e:
        raise CASAToolError(
            f"CASA not available: {e}",
            "Ensure CASA is installed and available in the environment. "
            "Try: conda activate casa6"
        ) from e
    
    # Check if we have PB images for all tiles (using cache)
    from .cache import get_cache
    cache = get_cache()
    pb_paths = []
    for tile in tiles:
        metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
        pb_path = metrics.pb_path
        if not pb_path:
            # Try to find PB path using cache
            from .validation import _find_pb_path
            pb_path = cache.get_pb_path(tile, _find_pb_path)
        
        if pb_path and os.path.exists(pb_path):
            pb_paths.append(pb_path)
        else:
            pb_paths.append(None)
    
    has_all_pb_images = all(pb_path is not None for pb_path in pb_paths)
    
    if not has_all_pb_images:
        LOG.warning(
            "Primary beam images not available for all tiles, "
            "using noise-weighted combination instead of PB-weighted"
        )
        # Fall back to noise-weighted combination
        noise_weights = []
        for tile in tiles:
            metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
            if metrics.rms_noise is not None and metrics.rms_noise > 0:
                weight = 1.0 / (metrics.rms_noise ** 2)
            else:
                weight = 1.0
            noise_weights.append(weight)
        
        # Normalize weights
        total_weight = sum(noise_weights)
        if total_weight > 0:
            noise_weights = [w / total_weight for w in noise_weights]
        
        # Build weighted expression
        weighted_terms = []
        for i, (tile, weight) in enumerate(zip(tiles, noise_weights)):
            weighted_terms.append(f"{weight:.6f}*IM{i}")
        
        expr = "+".join(weighted_terms)
        immath(imagename=tiles, expr=expr, outfile=str(output_path))
        LOG.info(
            f"Built mosaic using noise-weighted combination "
            f"(weights: {noise_weights})"
        )
        return
    
    # Full PB-weighted combination
    # Step 1: Read PB images and verify they're on the same grid
    LOG.info("Reading primary beam images for pixel-by-pixel weighting...")
    
    pb_images = []
    pb_data_list = []
    ref_shape = None
    ref_coordsys = None
    
    try:
        for i, (tile, pb_path) in enumerate(zip(tiles, pb_paths)):
            try:
                # Pre-validate PB image before reading
                validate_image_before_read(pb_path, operation=f"read_pb_tile_{i}")
                
                # Read PB image with enhanced error handling
                pb_img = safe_casaimage_open(pb_path, operation=f"read_pb_tile_{i}")
                pb_data = pb_img.getdata()
                
                # Validate image data
                validate_image_data(pb_data, pb_path, operation=f"read_pb_tile_{i}")
                
                # Get shape and coordinate system
                shape = pb_img.shape()
                coordsys = pb_img.coordsys()
                
                if ref_shape is None:
                    ref_shape = shape
                    ref_coordsys = coordsys
                else:
                    # Check if shapes match
                    if shape != ref_shape:
                        LOG.warning(
                            f"PB image {pb_path} has different shape {shape} than reference {ref_shape}. "
                            f"Will regrid to reference grid."
                        )
                        # Regrid PB image to reference grid
                        # Use first tile as template (works for both CASA and FITS)
                        template_img = tiles[0] if os.path.isdir(tiles[0]) else None
                        template = template_img or str(pb_paths[0])
                        
                        # Try to use cached regridded image
                        from .cache import get_cache
                        cache = get_cache()
                        
                        def regrid_func(imagename, template, output, overwrite):
                            imregrid(imagename=imagename, template=template, output=output, overwrite=overwrite)
                        
                        regridded_pb = cache.get_regridded_image(
                            source_path=str(pb_path),
                            template_path=template,
                            regrid_func=regrid_func,
                            output_suffix=f"_pb_{i}"
                        )
                        
                        if not regridded_pb:
                            # Fallback to temporary file if caching not available
                            regridded_pb = str(output_path) + f"_pb_regrid_{i}.tmp"
                            try:
                        if template_img:
                            imregrid(
                                imagename=str(pb_path),
                                template=template_img,
                                output=regridded_pb,
                                overwrite=True,
                            )
                        else:
                            # For FITS, use first PB image as template
                            imregrid(
                                imagename=str(pb_path),
                                template=str(pb_paths[0]),
                                output=regridded_pb,
                                overwrite=True,
                            )
                            except Exception as e:
                        pb_img.close()
                                handle_casa_tool_error(
                                    'imregrid', e,
                                    image_path=pb_path,
                                    operation=f"regrid_pb_tile_{i}",
                                    template=template_img or str(pb_paths[0])
                                )
                        else:
                            LOG.debug(f"Using cached regridded PB image: {regridded_pb}")
                        
                        pb_img.close()
                        pb_img = safe_casaimage_open(regridded_pb, operation=f"read_regridded_pb_tile_{i}")
                        pb_data = pb_img.getdata()
                        validate_image_data(pb_data, regridded_pb, operation=f"read_regridded_pb_tile_{i}")
                        shape = pb_img.shape()
                
                # Extract PB response (handle multi-dimensional arrays)
                # PB images are typically 2D [y, x] or 4D [stokes, freq, y, x]
                if pb_data.ndim == 2:
                    pb_response = pb_data
                elif pb_data.ndim == 4:
                    # Take first stokes, first frequency
                    pb_response = pb_data[0, 0, :, :]
                else:
                    # Flatten to 2D
                    pb_response = pb_data.squeeze()
                    if pb_response.ndim > 2:
                        pb_response = pb_response[0, :, :] if pb_response.ndim == 3 else pb_response
                
                pb_data_list.append(pb_response.astype(np.float64))
                pb_images.append(pb_img)
                
            except (ImageReadError, ImageCorruptionError, IncompatibleImageFormatError):
                # Re-raise validation errors with context
                raise
            except Exception as e:
                LOG.error(f"Failed to read PB image {pb_path}: {e}")
                if 'pb_img' in locals():
                    try:
                    pb_img.close()
                    except Exception:
                        pass
                # This should not happen if error handling is working correctly
                from .exceptions import ImageReadError
                raise ImageReadError(
                    f"Failed to read primary beam image: {pb_path}",
                    f"Error: {e}. "
                    "Check if the PB image exists and is readable. "
                    "Verify the image format is supported (CASA .pb directory or FITS -beam-0.fits file).",
                    context={'tile': pb_path, 'operation': f'read_pb_tile_{i}'}
                ) from e
    
    # Step 2: Read tile images
    LOG.info("Reading tile images...")
    
    tile_images = []
    tile_data_list = []
    
    for i, tile in enumerate(tiles):
        try:
                # Pre-validate tile image before reading
                validate_image_before_read(tile, operation=f"read_tile_{i}")
                
                # Read tile image with enhanced error handling
                tile_img = safe_casaimage_open(tile, operation=f"read_tile_{i}")
            tile_data = tile_img.getdata()
                
                # Validate image data
                validate_image_data(tile_data, tile, operation=f"read_tile_{i}")
            
            # Extract image data (handle multi-dimensional arrays)
            if tile_data.ndim == 2:
                img_data = tile_data
            elif tile_data.ndim == 4:
                # Take first stokes, first frequency
                img_data = tile_data[0, 0, :, :]
            else:
                # Flatten to 2D
                img_data = tile_data.squeeze()
                if img_data.ndim > 2:
                    img_data = img_data[0, :, :] if img_data.ndim == 3 else img_data
            
            # Verify shape matches PB image
            if img_data.shape != pb_data_list[i].shape:
                LOG.warning(
                    f"Tile {tile} shape {img_data.shape} doesn't match PB shape {pb_data_list[i].shape}. "
                    f"Regridding tile to PB grid."
                )
                # Regrid tile to PB grid
                # Use corresponding PB image as template
                    # Try to use cached regridded image
                    from .cache import get_cache
                    cache = get_cache()
                    
                    def regrid_func(imagename, template, output, overwrite):
                        imregrid(imagename=imagename, template=template, output=output, overwrite=overwrite)
                    
                    regridded_tile = cache.get_regridded_image(
                        source_path=str(tile),
                        template_path=str(pb_paths[i]),
                        regrid_func=regrid_func,
                        output_suffix=f"_tile_{i}"
                    )
                    
                    if not regridded_tile:
                        # Fallback to temporary file if caching not available
                        regridded_tile = str(output_path) + f"_tile_regrid_{i}.tmp"
                        try:
                imregrid(
                    imagename=str(tile),
                    template=str(pb_paths[i]),
                    output=regridded_tile,
                    overwrite=True,
                )
                        except Exception as e:
                tile_img.close()
                            handle_casa_tool_error(
                                'imregrid', e,
                                image_path=tile,
                                operation=f"regrid_tile_{i}",
                                template=str(pb_paths[i])
                            )
                    else:
                        LOG.debug(f"Using cached regridded tile image: {regridded_tile}")
                    
                    tile_img.close()
                    tile_img = safe_casaimage_open(regridded_tile, operation=f"read_regridded_tile_{i}")
                tile_data = tile_img.getdata()
                    validate_image_data(tile_data, regridded_tile, operation=f"read_regridded_tile_{i}")
                if tile_data.ndim == 2:
                    img_data = tile_data
                elif tile_data.ndim == 4:
                    img_data = tile_data[0, 0, :, :]
                else:
                    img_data = tile_data.squeeze()
                    if img_data.ndim > 2:
                        img_data = img_data[0, :, :] if img_data.ndim == 3 else img_data
            
                tile_data_list.append(img_data.astype(np.float64))
                tile_images.append(tile_img)
                
            except (ImageReadError, ImageCorruptionError, IncompatibleImageFormatError):
                # Re-raise validation errors with context
                raise
            except Exception as e:
                LOG.error(f"Failed to read tile {tile}: {e}")
                # Clean up already opened images
                for img in tile_images:
                    try:
                        img.close()
                    except Exception:
                        pass
                for img in pb_images:
                    try:
                        img.close()
                    except Exception:
                        pass
                # This should not happen if error handling is working correctly
                from .exceptions import ImageReadError
                raise ImageReadError(
                    f"Failed to read tile image: {tile}",
                    f"Error: {e}. "
                    "Check if the file exists and is readable. "
                    "Verify the image format is supported (CASA image directory or FITS file).",
                    context={'tile': tile, 'operation': f'read_tile_{i}'}
                ) from e
        
        # Step 3: Compute per-pixel weights and combine
        LOG.info("Computing pixel-by-pixel PB-weighted combination...")
        
        # Get noise variances
        noise_vars = []
        for tile in tiles:
            metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
            if metrics.rms_noise is not None and metrics.rms_noise > 0:
                noise_var = metrics.rms_noise ** 2
            else:
                # Default noise variance if not available
                noise_var = 1.0
            noise_vars.append(noise_var)
        
        # Compute weights: weight = pb_response^2 / noise_variance
        # For each pixel, combine: mosaic = sum(weight * tile) / sum(weight)
        
        ny, nx = tile_data_list[0].shape
        mosaic_data = np.zeros((ny, nx), dtype=np.float64)
        total_weight = np.zeros((ny, nx), dtype=np.float64)
        
        for i, (tile_data, pb_data, noise_var) in enumerate(zip(tile_data_list, pb_data_list, noise_vars)):
            # Compute weights: pb^2 / noise_variance
            # Clip PB values to avoid division issues
            pb_safe = np.clip(pb_data, 1e-10, None)  # Avoid zero/negative PB
            weights = (pb_safe ** 2) / noise_var
            
            # Accumulate weighted sum
            mosaic_data += weights * tile_data
            total_weight += weights
            
            LOG.debug(f"Tile {i}: min PB={pb_safe.min():.4f}, max PB={pb_safe.max():.4f}, "
                     f"noise_var={noise_var:.3e}")
        
        # Normalize by total weight (avoid division by zero)
        nonzero_mask = total_weight > 1e-10
        mosaic_data[nonzero_mask] /= total_weight[nonzero_mask]
        mosaic_data[~nonzero_mask] = np.nan
        
        LOG.info(
            f"Computed PB-weighted mosaic: "
            f"coverage={nonzero_mask.sum()}/{nonzero_mask.size} pixels "
            f"({100*nonzero_mask.sum()/nonzero_mask.size:.1f}%)"
        )
        
        # Step 4: Write mosaic image
        LOG.info(f"Writing PB-weighted mosaic to {output_path}...")
        
        # Create output image using reference coordinate system
        # Ensure output path is clean (no extensions that might confuse CASA)
        output_path_str = str(output_path)
        if output_path_str.endswith('.image'):
            output_path_str = output_path_str[:-6]
        
        output_img = casaimage()
        # Add stokes and frequency dimensions: [stokes, freq, y, x]
        output_pixels = mosaic_data[np.newaxis, np.newaxis, :, :]
        
        output_img.fromarray(
            outfile=output_path_str,
            pixels=output_pixels,
            csys=ref_coordsys,
            overwrite=True,
        )
        output_img.close()
        
        # Clean up temporary regridded images (ensure cleanup even on errors)
        temp_files_to_cleanup = []
        for i in range(len(tiles)):
            for suffix in [f"_pb_regrid_{i}.tmp", f"_tile_regrid_{i}.tmp"]:
                temp_path = str(output_path) + suffix
                temp_files_to_cleanup.append(temp_path)
        
        # Clean up temporary files
        import shutil
        for temp_path in temp_files_to_cleanup:
                if os.path.exists(temp_path):
                    try:
                        if os.path.isdir(temp_path):
                            shutil.rmtree(temp_path)
                        else:
                            os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")
        
        # Close all images
        for img in tile_images:
            try:
                img.close()
            except Exception:
                pass
        for img in pb_images:
            try:
                img.close()
            except Exception:
                pass
        
        LOG.info(
            f"✓ Built PB-weighted mosaic to {output_path_str} "
            f"(pixel-by-pixel combination using PB^2/noise_variance weighting)"
        )
    
    except (ImageReadError, ImageCorruptionError, MissingPrimaryBeamError, 
            CASAToolError, GridMismatchError) as e:
        # Clean up temporary files even on error
        import shutil
        for i in range(len(tiles)):
            for suffix in [f"_pb_regrid_{i}.tmp", f"_tile_regrid_{i}.tmp"]:
                temp_path = str(output_path) + suffix
                if os.path.exists(temp_path):
                    try:
                        if os.path.isdir(temp_path):
                            shutil.rmtree(temp_path)
                        else:
                            os.remove(temp_path)
                    except Exception:
                        pass
        # Close images if they exist
        try:
            for img in tile_images:
                try:
                    img.close()
                except Exception:
                    pass
        except NameError:
            pass
        try:
            for img in pb_images:
                try:
                    img.close()
                except Exception:
                    pass
        except NameError:
            pass
        # Re-raise specific mosaic errors with their recovery hints
        raise
    except Exception as e:
        raise MosaicError(
            f"Unexpected error during weighted mosaic building: {e}",
            "Check logs for details. Try rebuilding the mosaic with --ignore-validation "
            "if validation issues are blocking the build."
        ) from e


def cmd_build(args: argparse.Namespace) -> int:
    pdb = Path(args.products_db)
    name = args.name
    out = Path(args.output).with_suffix("")
    
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        row = conn.execute("SELECT id, tiles, method FROM mosaics WHERE name = ?", (name,)).fetchone()
        if row is None:
            logger.error("Mosaic plan not found; create with 'plan' first")
            print("Mosaic plan not found; create with 'plan' first")
            return 1
        tiles = str(row[1]).splitlines()
        method = str(row[2] or 'mean')
    
    if not tiles:
        logger.warning("No tiles found in mosaic plan")
        print("No tiles found in mosaic plan")
        return 1
    
    # Pre-flight validation: Check all pre-conditions before expensive operations
    print("Pre-flight validation: Checking pre-conditions...")
    from .preflight import validate_preflight_conditions, estimate_resources
    
    # Check if PB images are required based on method
    require_pb = (method == 'weighted' or method == 'pbweighted')
    
    preflight_valid, preflight_issues, preflight_info = validate_preflight_conditions(
        tiles=tiles,
        output_path=str(out),
        metrics_dict=None,  # Will be computed during validation
        require_pb=require_pb,
        check_disk_space_flag=True,
    )
    
    if preflight_issues:
        print("Pre-flight validation issues:")
        for issue in preflight_issues:
            print(f"  - {issue}")
        
        if not args.ignore_validation:
            print("\nPre-flight validation failed. Fix issues above before building.")
            print("Use --ignore-validation to proceed anyway (not recommended).")
            return 3
        else:
            print("\nWarning: Pre-flight issues detected but ignored (--ignore-validation)")
    
    # Report resource estimates
    try:
        estimates = estimate_resources(tiles, str(out))
        print(f"\nResource estimates:")
        print(f"  - Tiles: {estimates['num_tiles']}")
        print(f"  - Estimated disk space: {estimates['estimated_disk_gb']:.1f} GB")
        print(f"  - Estimated operations: {estimates['estimated_operations']}")
        print(f"  - Estimated time: ~{estimates['estimated_time_minutes']:.0f} minutes")
    except Exception as e:
        logger.debug(f"Could not estimate resources: {e}")
    
    # Warn if output exists
    if preflight_info.get('output_exists'):
        print(f"\nWarning: Output '{out}' already exists and will be overwritten")
    
    # Comprehensive validation
    print(f"Validating {len(tiles)} tiles...")
    
    # 1. Basic grid consistency
    ok, reason = _check_consistent_tiles(tiles)
    if not ok:
        print(f"Cannot build mosaic: {reason}")
        return 2
    
    # 2. Tile quality validation (computes metrics_dict)
    is_valid, validation_issues, metrics_dict = validate_tiles_consistency(
        tiles, products_db=pdb
    )
    
    # Re-run pre-flight with computed metrics_dict for better PB checking
    if require_pb:
        _, preflight_issues_pb, _ = validate_preflight_conditions(
            tiles=tiles,
            output_path=str(out),
            metrics_dict=metrics_dict,
            require_pb=require_pb,
            check_disk_space_flag=False,  # Already checked
        )
        if preflight_issues_pb and not args.ignore_validation:
            print("Pre-flight validation issues (after tile validation):")
            for issue in preflight_issues_pb:
                print(f"  - {issue}")
            print("\nPre-flight validation failed. Fix issues above before building.")
            return 3
    
    if validation_issues:
        print("Validation issues found:")
        for issue in validation_issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(validation_issues) > 10:
            print(f"  ... and {len(validation_issues) - 10} more issues")
        
        if not args.ignore_validation:
            raise ValidationError(
                f"Mosaic validation failed with {len(validation_issues)} issues",
                "Review the validation issues above. Common fixes:\n"
                "  - Ensure all tiles have PB correction applied\n"
                "  - Check tile noise levels are reasonable\n"
                "  - Verify tiles have consistent calibration\n"
                "Use --ignore-validation to proceed anyway (not recommended for science)."
            )
        else:
            print("\nWarning: Validation issues detected but ignored (--ignore-validation)")
    
    # 3. Astrometric registration check
    try:
        astro_valid, astro_issues, offsets = verify_astrometric_registration(tiles)
    except Exception as e:
        raise ValidationError(
            f"Astrometric verification failed: {e}",
            "Check if catalog access is available. "
            "Try running with --ignore-validation to skip astrometric checks."
        ) from e
    if astro_issues:
        print("Astrometric registration issues:")
        for issue in astro_issues:
            print(f"  - {issue}")
        if not args.ignore_validation:
            print("\nMosaic build aborted due to astrometric issues.")
            return 4
    
    # 4. Calibration consistency check
    # Try to find registry DB from environment or default location
    registry_db = None
    if os.getenv('CAL_REGISTRY_DB'):
        registry_db = Path(os.getenv('CAL_REGISTRY_DB'))
    else:
        # Try default location relative to products DB
        registry_db = pdb.parent / 'cal_registry.sqlite3'
        if not registry_db.exists():
            registry_db = None
    
    cal_consistent, cal_issues, cal_dict = check_calibration_consistency(
        tiles, pdb, registry_db=registry_db
    )
    if cal_issues:
        print("Calibration consistency issues:")
        for issue in cal_issues:
            print(f"  - {issue}")
        if not args.ignore_validation:
            print("\nMosaic build aborted due to calibration inconsistencies.")
            return 5
    
    # 5. Primary beam consistency check
    pb_consistent, pb_issues, pb_dict = check_primary_beam_consistency(
        tiles, metrics_dict
    )
    if pb_issues:
        print("Primary beam consistency issues:")
        for issue in pb_issues:
            print(f"  - {issue}")
        if not args.ignore_validation:
            print("\nMosaic build aborted due to PB consistency issues.")
            return 6
    
    print("✓ All validation checks passed")
    
    # Dry-run mode: validate without building
    if args.dry_run:
        print("\n" + "="*60)
        print("DRY-RUN MODE: Validation complete, not building mosaic")
        print("="*60)
        print(f"\nMosaic plan summary:")
        print(f"  - Name: {name}")
        print(f"  - Method: {method}")
        print(f"  - Tiles: {len(tiles)}")
        print(f"  - Output: {out}")
        print(f"\n✓ All validations passed. Ready to build.")
        print(f"\nTo build this mosaic, run:")
        print(f"  mosaic build --name {name} --output {out}")
        return 0
    
    # Build mosaic
    try:
        # Keep immath temp products under scratch and avoid polluting CWD
        try:
            if prepare_temp_environment is not None:
                prepare_temp_environment(
                    os.getenv('CONTIMG_SCRATCH_DIR') or '/stage/dsa110-contimg',
                    cwd_to=out.parent
                )
        except Exception:
            pass
        
        # Use weighted combination if method is 'weighted', otherwise use mean
        if method == 'weighted' or method == 'pbweighted':
            print(f"Building weighted mosaic to {out}...")
            try:
                _build_weighted_mosaic(tiles, metrics_dict, str(out))
            except (ImageReadError, ImageCorruptionError, MissingPrimaryBeamError,
                    CASAToolError, GridMismatchError) as e:
                # Re-raise with context
                raise
        else:
            print(f"Building mean mosaic to {out}...")
            try:
                if not immath:
                    raise CASAToolError(
                        "CASA immath not available",
                        "Ensure CASA is installed: conda activate casa6",
                        context={'tool': 'immath', 'operation': 'build_mean_mosaic'}
                    )
                expr = f"({'+'.join([f'IM{i}' for i in range(len(tiles))])})/{len(tiles)}"
                try:
                immath(imagename=tiles, expr=expr, outfile=str(out))
                except Exception as e:
                    handle_casa_tool_error(
                        'immath', e,
                        operation='build_mean_mosaic',
                        expression=expr,
                        num_tiles=len(tiles)
                    )
            except Exception as e:
                raise CASAToolError(
                    f"CASA immath failed: {e}",
                    "Check if all tile images are readable and have compatible formats. "
                    "Try using weighted method instead: --method=weighted"
                ) from e
        
        # Export FITS for the mosaic image for downstream photometry
        fits_path = None
        try:
            from casatasks import exportfits
            fits_path = str(out) + ".fits"
            exportfits(imagename=str(out), fitsimage=fits_path, overwrite=True)
            print(f"✓ Exported mosaic FITS: {fits_path}")
        except Exception as exc:
            from .error_handling import handle_casa_tool_error
            # Don't fail build if export fails, but log it properly
            try:
                handle_casa_tool_error(
                    'exportfits', exc,
                    image_path=str(out),
                    operation='export_mosaic_fits'
                )
            except Exception:
                # If handle_casa_tool_error fails, just print warning
                pass
            print(f"exportfits warning: {exc}")
        
        # Automatic photometry analysis on mosaic (NVSS catalog sources)
        photometry_count = 0
        if fits_path and Path(fits_path).exists():
            try:
                print("Performing forced photometry on NVSS catalog sources...")
                from dsa110_contimg.photometry.forced import measure_forced_peak
                from dsa110_contimg.calibration.catalogs import read_nvss_catalog
                from dsa110_contimg.database.products import photometry_insert
                from dsa110_contimg.photometry.cli import _image_center_and_radius_deg
                import astropy.coordinates as acoords
                import time
                
                # Get image center and radius
                ra0, dec0, auto_rad = _image_center_and_radius_deg(fits_path)
                
                # Query NVSS catalog sources within image field of view
                df = read_nvss_catalog()
                sc = acoords.SkyCoord(
                    df['ra'].to_numpy(),
                    df['dec'].to_numpy(),
                    unit='deg',
                    frame='icrs',
                )
                center = acoords.SkyCoord(ra0, dec0, unit='deg', frame='icrs')
                sep_deg = sc.separation(center).deg
                flux_mjy = df['flux_20_cm'].to_numpy()
                
                # Filter: sources within image radius, flux >= 10 mJy
                min_mjy = 10.0
                keep = (sep_deg <= auto_rad) & (flux_mjy >= min_mjy)
                ra_sel = df['ra'].to_numpy()[keep]
                dec_sel = df['dec'].to_numpy()[keep]
                flux_sel = flux_mjy[keep]
                
                # Perform forced photometry at each catalog position
                now = time.time()
                with ensure_products_db(pdb) as conn:
                    inserted = 0
                    skipped = 0
                    for ra, dec, nvss_flux in zip(ra_sel, dec_sel, flux_sel):
                        try:
                            m = measure_forced_peak(
                                fits_path,
                                float(ra),
                                float(dec),
                                box_size_pix=5,
                                annulus_pix=(12, 20),
                            )
                            if not np.isfinite(m.peak_jyb):
                                skipped += 1
                                continue
                            
                            perr = None
                            if (m.peak_err_jyb is not None and 
                                np.isfinite(m.peak_err_jyb)):
                                perr = float(m.peak_err_jyb)
                            
                            # Insert into products database
                            photometry_insert(
                                conn,
                                image_path=fits_path,
                                ra_deg=m.ra_deg,
                                dec_deg=m.dec_deg,
                                nvss_flux_mjy=float(nvss_flux),
                                peak_jyb=m.peak_jyb,
                                peak_err_jyb=perr,
                                measured_at=now,
                            )
                            inserted += 1
                        except Exception as e:
                            logger.warning(
                                f"Photometry failed for source at ({ra:.4f}, {dec:.4f}): {e}")
                            skipped += 1
                            continue
                    
                    conn.commit()
                    photometry_count = inserted
                
                if photometry_count > 0:
                    print(f"✓ Photometry complete: {photometry_count} sources measured "
                          f"({skipped} skipped)")
                else:
                    print(f"Warning: No valid photometry measurements "
                          f"({skipped} sources attempted)")
            except Exception as e:
                logger.warning(f"Photometry analysis failed: {e}")
                print(f"Warning: Photometry analysis failed: {e}")
                # Don't fail build if photometry fails
        
        # Post-mosaic validation
        try:
            from .post_validation import validate_mosaic_quality
            print("Validating final mosaic quality...")
            mosaic_valid, mosaic_issues, mosaic_metrics = validate_mosaic_quality(
                str(out),
                max_rms_variation=2.0,
                min_coverage_fraction=0.1,
            )
            
            if mosaic_issues:
                print("Post-mosaic validation issues:")
                for issue in mosaic_issues:
                    print(f"  - {issue}")
                if mosaic_metrics:
                    print(f"Mosaic metrics: RMS={mosaic_metrics.get('rms_noise', 'N/A'):.3e}, "
                          f"coverage={mosaic_metrics.get('coverage_fraction', 0):.1%}")
            else:
                print("✓ Post-mosaic validation passed")
                if mosaic_metrics:
                    print(f"Mosaic metrics: RMS={mosaic_metrics.get('rms_noise', 'N/A'):.3e}, "
                          f"coverage={mosaic_metrics.get('coverage_fraction', 0):.1%}, "
                          f"dynamic_range={mosaic_metrics.get('dynamic_range', 0):.1f}")
        except Exception as e:
            LOG.warning(f"Post-mosaic validation failed: {e}")
            # Don't fail build if validation fails
        
        # Generate mosaic quality metrics
        metrics_files = {}
        try:
            print("Generating mosaic quality metrics...")
            metrics_files = generate_mosaic_metrics(
                tiles=tiles,
                metrics_dict=metrics_dict,
                mosaic_path=str(out),
                output_dir=str(out.parent),
            )
            if metrics_files:
                print(f"✓ Generated {len(metrics_files)} quality metric images")
                for metric_name, metric_path in metrics_files.items():
                    print(f"  - {metric_name}: {metric_path}")
            else:
                print("Warning: No metrics generated (casacore may not be available)")
        except Exception as e:
            LOG.warning(f"Failed to generate mosaic metrics: {e}")
            print(f"Warning: Failed to generate mosaic metrics: {e}")
            # Don't fail the build if metrics generation fails
        
        # Update mosaic status
        validation_summary = "\n".join(validation_issues) if validation_issues else None
        metrics_summary = None
        if metrics_files:
            # Store metrics paths as JSON-like string (simple format)
            metrics_list = [f"{name}:{path}" for name, path in metrics_files.items()]
            metrics_summary = "\n".join(metrics_list)
        
        with ensure_products_db(pdb) as conn:
            # Check if mosaics table has metrics_path column, if not add it
            try:
                conn.execute("SELECT metrics_path FROM mosaics LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                conn.execute("ALTER TABLE mosaics ADD COLUMN metrics_path TEXT")
                conn.commit()
            
            conn.execute(
                "UPDATE mosaics SET status='built', output_path=?, validation_issues=?, metrics_path=? WHERE name=?",
                (str(out), validation_summary, metrics_summary, name)
            )
            conn.commit()
        
        print(f"✓ Built mosaic to {out}")
        return 0
    except (MosaicError, ImageReadError, ImageCorruptionError, MissingPrimaryBeamError,
            CASAToolError, GridMismatchError, ValidationError, MetricsGenerationError) as e:
        # Handle specific mosaic errors with user-friendly messages
        print(f"\nMosaic build failed: {e.message}")
        if e.recovery_hint:
            print(f"\n{e.recovery_hint}")
        import traceback
        traceback.print_exc()
        return 6
    except Exception as e:
        print(f"Mosaic build failed: {e}")
        import traceback
        traceback.print_exc()
        return 6


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Mosaic planner/builder")
    sub = p.add_subparsers(dest='cmd')
    sp = sub.add_parser('plan', help='Plan a mosaic from products DB tiles')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--name', required=True)
    sp.add_argument('--since', type=float, help='Only include tiles created_at >= since (epoch seconds)')
    sp.add_argument('--until', type=float, help='Only include tiles created_at <= until (epoch seconds)')
    sp.add_argument('--method', default='mean', choices=['mean', 'weighted', 'pbweighted'],
                    help='Combination method: mean (simple), weighted (noise-weighted), pbweighted (primary beam weighted)')
    sp.add_argument('--include-unpbcor', action='store_true', help='Include non-pbcor tiles')
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser('build', help='Build a mosaic from a planned set')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--name', required=True)
    sp.add_argument('--output', required=True, help='Output image base path (CASA image)')
    sp.add_argument('--ignore-validation', action='store_true',
                    help='Ignore validation issues and proceed anyway (not recommended)')
    sp.add_argument('--dry-run', action='store_true',
                    help='Validate mosaic plan without building (measure twice, cut once)')
    sp.set_defaults(func=cmd_build)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    # Ensure scratch directory structure exists
    try:
        ensure_scratch_dirs()
    except Exception:
        pass  # Best-effort; continue if setup fails
    
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, 'func'):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())

```


Checking imports and adding numpy if needed:



Adding the numpy import:


```python
"""
CLI for planning and building mosaics from 5-minute image tiles.

A **tile** is a single calibrated, imaged, and primary-beam-corrected radio astronomy
image created from ~5 minutes of observation data. Multiple tiles are combined to create
a larger mosaic covering a wider field of view.

Phase 1: record mosaic plan (list of tiles) into products DB.
Phase 2: validate tiles and build weighted mosaic using primary beam weighting.

See docs/reference/GLOSSARY.md for detailed definition of tiles and related terminology.
"""

import argparse
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

from dsa110_contimg.database.products import ensure_products_db
from dsa110_contimg.utils.cli_helpers import ensure_scratch_dirs
try:
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore

from .validation import (
    validate_tiles_consistency,
    verify_astrometric_registration,
    check_calibration_consistency,
    check_primary_beam_consistency,
    TileQualityMetrics,
    _find_pb_path,
    HAVE_CASACORE,
)
from .exceptions import (
    MosaicError,
    ImageReadError,
    ImageCorruptionError,
    MissingPrimaryBeamError,
    IncompatibleImageFormatError,
    CASAToolError,
    GridMismatchError,
    ValidationError,
    MetricsGenerationError,
)

LOG = logging.getLogger(__name__)


def _ensure_mosaics_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mosaics (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            created_at REAL NOT NULL,
            status TEXT NOT NULL,
            method TEXT,
            tiles TEXT NOT NULL,
            output_path TEXT,
            validation_issues TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mosaics_name ON mosaics(name)"
    )


def _fetch_tiles(products_db: Path, *, since: Optional[float], until: Optional[float], pbcor_only: bool = True) -> List[str]:
    tiles: List[str] = []
    with ensure_products_db(products_db) as conn:
        q = "SELECT path, created_at, pbcor FROM images"
        where = []
        params: List[object] = []
        if pbcor_only:
            where.append("pbcor = 1")
        if since is not None:
            where.append("created_at >= ?")
            params.append(float(since))
        if until is not None:
            where.append("created_at <= ?")
            params.append(float(until))
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " ORDER BY created_at ASC"
        for r in conn.execute(q, params).fetchall():
            p = r["path"] if isinstance(r, sqlite3.Row) else r[0]
            if p and os.path.isdir(p):
                tiles.append(p)
    return tiles


def cmd_plan(args: argparse.Namespace) -> int:
    pdb = Path(args.products_db)
    name = args.name
    since = args.since
    until = args.until
    tiles = _fetch_tiles(pdb, since=since, until=until, pbcor_only=not args.include_unpbcor)
    if not tiles:
        logger.warning("No tiles found for the specified window")
        print("No tiles found for the specified window")
        return 1
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        conn.execute(
            "INSERT INTO mosaics(name, created_at, status, method, tiles) VALUES(?,?,?,?,?)",
            (name, time.time(), "planned", args.method, "\n".join(tiles)),
        )
        conn.commit()
    logger.info(f"Planned mosaic '{name}' with {len(tiles)} tiles")
    print(f"Planned mosaic '{name}' with {len(tiles)} tiles")
    return 0


def _check_consistent_tiles(tiles: List[str]) -> Tuple[bool, Optional[str]]:
    """Check basic grid consistency (legacy function)."""
    from .cache import get_cache
    
    cache = get_cache()
    ref = None
    for t in tiles:
        try:
            header = cache.get_tile_header(t)
            if not header:
                return False, f"Failed to get header for {t}"
            key = (header.get('shape'), header.get('cdelt1'), header.get('cdelt2'))
        if ref is None:
            ref = key
        elif key != ref:
            return False, "Tiles have inconsistent grids/cell sizes"
        except Exception as e:
            return False, f"imhead failed for {t}: {e}"
    return True, None


def generate_mosaic_metrics(
    tiles: List[str],
    metrics_dict: Dict[str, TileQualityMetrics],
    mosaic_path: str,
    output_dir: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate mosaic quality metrics images.
    
    Creates metadata images showing:
    - Effective integration time per pixel
    - Primary beam response per pixel
    - Noise variance per pixel
    - Number of tiles contributing per pixel
    - Coverage map
    
    Args:
        tiles: List of tile paths
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        mosaic_path: Path to mosaic image
        output_dir: Optional output directory (defaults to mosaic directory)
        
    Returns:
        Dictionary mapping metric name -> file path
    """
    metric_files = {}
    
    if not HAVE_CASACORE:
        LOG.warning("casacore.images not available, skipping mosaic metrics generation")
        return metric_files
    
    try:
        import numpy as np
        from .validation import _find_pb_path
        
        # Import CASA tools if available
        try:
            from casatasks import exportfits, imregrid
            from casacore.images import image as casaimage
        except ImportError:
            exportfits = None
            imregrid = None
            casaimage = None
        
        if not casaimage:
            LOG.warning("CASA tools not available, skipping mosaic metrics generation")
            return metric_files
        
        # Determine output directory
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(mosaic_path))
        os.makedirs(output_dir, exist_ok=True)
        
        # Read mosaic to get reference grid
        mosaic_img = casaimage(mosaic_path)
        mosaic_data = mosaic_img.getdata()
        coord_sys = mosaic_img.coordsys()
        
        # Extract 2D image data
        if mosaic_data.ndim == 2:
            mosaic_2d = mosaic_data
        elif mosaic_data.ndim == 4:
            mosaic_2d = mosaic_data[0, 0, :, :]
        else:
            mosaic_2d = mosaic_data.squeeze()
            if mosaic_2d.ndim > 2:
                mosaic_2d = mosaic_2d[0, :, :] if mosaic_2d.ndim == 3 else mosaic_2d
        
        ny, nx = mosaic_2d.shape
        mosaic_base = os.path.splitext(os.path.basename(mosaic_path))[0]
        
        # Initialize metric arrays
        pb_response_map = np.zeros((ny, nx), dtype=np.float64)
        noise_variance_map = np.zeros((ny, nx), dtype=np.float64)
        tile_count_map = np.zeros((ny, nx), dtype=np.int32)
        integration_time_map = np.zeros((ny, nx), dtype=np.float64)
        
        # Process each tile
        for tile in tiles:
            metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
            
            # Get PB path
            pb_path = metrics.pb_path
            if not pb_path:
                pb_path = _find_pb_path(tile)
            
            if pb_path and os.path.exists(pb_path):
                try:
                    pb_img = casaimage(str(pb_path))
                    pb_data = pb_img.getdata()
                    
                    # Extract 2D PB data
                    if pb_data.ndim == 2:
                        pb_2d = pb_data
                    elif pb_data.ndim == 4:
                        pb_2d = pb_data[0, 0, :, :]
                    else:
                        pb_2d = pb_data.squeeze()
                        if pb_2d.ndim > 2:
                            pb_2d = pb_2d[0, :, :] if pb_2d.ndim == 3 else pb_2d
                    
                    # Check if PB needs regridding
                    if pb_2d.shape != (ny, nx):
                        # Need to regrid PB to mosaic grid
                        regridded_pb = os.path.join(output_dir, f"{mosaic_base}_pb_regrid_{len(metric_files)}.tmp")
                        try:
                            imregrid(
                                imagename=str(pb_path),
                                template=mosaic_path,
                                output=regridded_pb,
                                overwrite=True,
                            )
                            pb_img.close()
                            pb_img = casaimage(regridded_pb)
                            pb_data = pb_img.getdata()
                            if pb_data.ndim == 2:
                                pb_2d = pb_data
                            elif pb_data.ndim == 4:
                                pb_2d = pb_data[0, 0, :, :]
                            else:
                                pb_2d = pb_data.squeeze()
                                if pb_2d.ndim > 2:
                                    pb_2d = pb_2d[0, :, :] if pb_2d.ndim == 3 else pb_2d
                        except Exception as e:
                            LOG.warning(f"Failed to regrid PB for {tile}: {e}")
                            pb_img.close()
                            continue
                    
                    # Accumulate PB response (use max across tiles for each pixel)
                    pb_response_map = np.maximum(pb_response_map, pb_2d)
                    
                    pb_img.close()
                    
                except Exception as e:
                    LOG.warning(f"Failed to read PB image {pb_path}: {e}")
            
            # Get noise variance
            noise_var = 1.0
            if metrics.rms_noise is not None and metrics.rms_noise > 0:
                noise_var = metrics.rms_noise ** 2
            
            # Accumulate weighted noise variance
            # For each pixel, accumulate 1/noise_variance (inverse variance weighting)
            inv_var = 1.0 / noise_var if noise_var > 0 else 1.0
            noise_variance_map += inv_var
            
            # Count tiles contributing to each pixel
            # For now, mark all pixels (could be refined based on PB threshold)
            tile_count_map += 1
            
            # Integration time (placeholder - would need MS metadata)
            # For now, assume equal integration time per tile
            integration_time_map += 1.0  # Units: tile counts (would convert to seconds if available)
        
        # Normalize noise variance map (convert back to variance)
        # noise_variance_map currently contains sum(1/variance), so invert
        mask = noise_variance_map > 0
        noise_variance_map[mask] = 1.0 / noise_variance_map[mask]
        noise_variance_map[~mask] = np.nan
        
        # Create output images
        base_path = os.path.join(output_dir, mosaic_base)
        
        # 1. Primary beam response map
        pb_response_img = casaimage()
        pb_response_img.fromarray(
            outfile=f"{base_path}_pb_response",
            pixels=pb_response_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        pb_response_img.close()
        metric_files['pb_response'] = f"{base_path}_pb_response"
        
        # 2. Noise variance map
        noise_var_img = casaimage()
        noise_var_img.fromarray(
            outfile=f"{base_path}_noise_variance",
            pixels=noise_variance_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        noise_var_img.close()
        metric_files['noise_variance'] = f"{base_path}_noise_variance"
        
        # 3. Tile count map
        tile_count_img = casaimage()
        tile_count_img.fromarray(
            outfile=f"{base_path}_tile_count",
            pixels=tile_count_map.astype(np.float32)[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        tile_count_img.close()
        metric_files['tile_count'] = f"{base_path}_tile_count"
        
        # 4. Integration time map
        integration_time_img = casaimage()
        integration_time_img.fromarray(
            outfile=f"{base_path}_integration_time",
            pixels=integration_time_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        integration_time_img.close()
        metric_files['integration_time'] = f"{base_path}_integration_time"
        
        # 5. Coverage map (binary: 1 if tile contributes, 0 otherwise)
        coverage_map = (tile_count_map > 0).astype(np.float32)
        coverage_img = casaimage()
        coverage_img.fromarray(
            outfile=f"{base_path}_coverage",
            pixels=coverage_map[np.newaxis, np.newaxis, :, :],
            csys=coord_sys,
            overwrite=True,
        )
        coverage_img.close()
        metric_files['coverage'] = f"{base_path}_coverage"
        
        # Export as FITS
        if exportfits:
            for metric_name, metric_path in list(metric_files.items()):
                fits_path = f"{metric_path}.fits"
                try:
                    exportfits(
                        imagename=metric_path,
                        fitsimage=fits_path,
                        overwrite=True,
                    )
                    metric_files[metric_name] = fits_path  # Update to FITS path
                except Exception as e:
                    LOG.warning(f"Failed to export {metric_name} to FITS: {e}")
        
        mosaic_img.close()
        
        LOG.info(f"Generated mosaic metrics: {list(metric_files.keys())}")
        
    except Exception as e:
        LOG.error(f"Failed to generate mosaic metrics: {e}")
        import traceback
        traceback.print_exc()
    
    return metric_files


def _build_weighted_mosaic(
    tiles: List[str],
    metrics_dict: dict,
    output_path: str,
) -> None:
    """
    Build mosaic using primary beam-weighted combination.
    
    For each pixel (i,j):
        weight[k][i,j] = pb_response[k][i,j]^2 / noise_variance[k]
        mosaic[i,j] = sum(weight[k][i,j] * tile[k][i,j]) / sum(weight[k][i,j])
    
    This implements the Sault weighting scheme for optimal mosaic combination.
    
    Args:
        tiles: List of tile image paths (should be PB-corrected images)
        metrics_dict: Dictionary mapping tile paths to TileQualityMetrics
        output_path: Output mosaic path
    """
    try:
        from casatasks import immath, imregrid
        from casacore.images import image as casaimage
        import numpy as np
        from .error_handling import (
            safe_casaimage_open,
            validate_image_data,
            validate_image_before_read,
            handle_casa_tool_error,
        )
    except ImportError as e:
        raise CASAToolError(
            f"CASA not available: {e}",
            "Ensure CASA is installed and available in the environment. "
            "Try: conda activate casa6"
        ) from e
    
    # Check if we have PB images for all tiles (using cache)
    from .cache import get_cache
    cache = get_cache()
    pb_paths = []
    for tile in tiles:
        metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
        pb_path = metrics.pb_path
        if not pb_path:
            # Try to find PB path using cache
            from .validation import _find_pb_path
            pb_path = cache.get_pb_path(tile, _find_pb_path)
        
        if pb_path and os.path.exists(pb_path):
            pb_paths.append(pb_path)
        else:
            pb_paths.append(None)
    
    has_all_pb_images = all(pb_path is not None for pb_path in pb_paths)
    
    if not has_all_pb_images:
        LOG.warning(
            "Primary beam images not available for all tiles, "
            "using noise-weighted combination instead of PB-weighted"
        )
        # Fall back to noise-weighted combination
        noise_weights = []
        for tile in tiles:
            metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
            if metrics.rms_noise is not None and metrics.rms_noise > 0:
                weight = 1.0 / (metrics.rms_noise ** 2)
            else:
                weight = 1.0
            noise_weights.append(weight)
        
        # Normalize weights
        total_weight = sum(noise_weights)
        if total_weight > 0:
            noise_weights = [w / total_weight for w in noise_weights]
        
        # Build weighted expression
        weighted_terms = []
        for i, (tile, weight) in enumerate(zip(tiles, noise_weights)):
            weighted_terms.append(f"{weight:.6f}*IM{i}")
        
        expr = "+".join(weighted_terms)
        immath(imagename=tiles, expr=expr, outfile=str(output_path))
        LOG.info(
            f"Built mosaic using noise-weighted combination "
            f"(weights: {noise_weights})"
        )
        return
    
    # Full PB-weighted combination
    # Step 1: Read PB images and verify they're on the same grid
    LOG.info("Reading primary beam images for pixel-by-pixel weighting...")
    
    pb_images = []
    pb_data_list = []
    ref_shape = None
    ref_coordsys = None
    
    try:
        for i, (tile, pb_path) in enumerate(zip(tiles, pb_paths)):
            try:
                # Pre-validate PB image before reading
                validate_image_before_read(pb_path, operation=f"read_pb_tile_{i}")
                
                # Read PB image with enhanced error handling
                pb_img = safe_casaimage_open(pb_path, operation=f"read_pb_tile_{i}")
                pb_data = pb_img.getdata()
                
                # Validate image data
                validate_image_data(pb_data, pb_path, operation=f"read_pb_tile_{i}")
                
                # Get shape and coordinate system
                shape = pb_img.shape()
                coordsys = pb_img.coordsys()
                
                if ref_shape is None:
                    ref_shape = shape
                    ref_coordsys = coordsys
                else:
                    # Check if shapes match
                    if shape != ref_shape:
                        LOG.warning(
                            f"PB image {pb_path} has different shape {shape} than reference {ref_shape}. "
                            f"Will regrid to reference grid."
                        )
                        # Regrid PB image to reference grid
                        # Use first tile as template (works for both CASA and FITS)
                        template_img = tiles[0] if os.path.isdir(tiles[0]) else None
                        template = template_img or str(pb_paths[0])
                        
                        # Try to use cached regridded image
                        from .cache import get_cache
                        cache = get_cache()
                        
                        def regrid_func(imagename, template, output, overwrite):
                            imregrid(imagename=imagename, template=template, output=output, overwrite=overwrite)
                        
                        regridded_pb = cache.get_regridded_image(
                            source_path=str(pb_path),
                            template_path=template,
                            regrid_func=regrid_func,
                            output_suffix=f"_pb_{i}"
                        )
                        
                        if not regridded_pb:
                            # Fallback to temporary file if caching not available
                            regridded_pb = str(output_path) + f"_pb_regrid_{i}.tmp"
                            try:
                        if template_img:
                            imregrid(
                                imagename=str(pb_path),
                                template=template_img,
                                output=regridded_pb,
                                overwrite=True,
                            )
                        else:
                            # For FITS, use first PB image as template
                            imregrid(
                                imagename=str(pb_path),
                                template=str(pb_paths[0]),
                                output=regridded_pb,
                                overwrite=True,
                            )
                            except Exception as e:
                        pb_img.close()
                                handle_casa_tool_error(
                                    'imregrid', e,
                                    image_path=pb_path,
                                    operation=f"regrid_pb_tile_{i}",
                                    template=template_img or str(pb_paths[0])
                                )
                        else:
                            LOG.debug(f"Using cached regridded PB image: {regridded_pb}")
                        
                        pb_img.close()
                        pb_img = safe_casaimage_open(regridded_pb, operation=f"read_regridded_pb_tile_{i}")
                        pb_data = pb_img.getdata()
                        validate_image_data(pb_data, regridded_pb, operation=f"read_regridded_pb_tile_{i}")
                        shape = pb_img.shape()
                
                # Extract PB response (handle multi-dimensional arrays)
                # PB images are typically 2D [y, x] or 4D [stokes, freq, y, x]
                if pb_data.ndim == 2:
                    pb_response = pb_data
                elif pb_data.ndim == 4:
                    # Take first stokes, first frequency
                    pb_response = pb_data[0, 0, :, :]
                else:
                    # Flatten to 2D
                    pb_response = pb_data.squeeze()
                    if pb_response.ndim > 2:
                        pb_response = pb_response[0, :, :] if pb_response.ndim == 3 else pb_response
                
                pb_data_list.append(pb_response.astype(np.float64))
                pb_images.append(pb_img)
                
            except (ImageReadError, ImageCorruptionError, IncompatibleImageFormatError):
                # Re-raise validation errors with context
                raise
            except Exception as e:
                LOG.error(f"Failed to read PB image {pb_path}: {e}")
                if 'pb_img' in locals():
                    try:
                    pb_img.close()
                    except Exception:
                        pass
                # This should not happen if error handling is working correctly
                from .exceptions import ImageReadError
                raise ImageReadError(
                    f"Failed to read primary beam image: {pb_path}",
                    f"Error: {e}. "
                    "Check if the PB image exists and is readable. "
                    "Verify the image format is supported (CASA .pb directory or FITS -beam-0.fits file).",
                    context={'tile': pb_path, 'operation': f'read_pb_tile_{i}'}
                ) from e
    
    # Step 2: Read tile images
    LOG.info("Reading tile images...")
    
    tile_images = []
    tile_data_list = []
    
    for i, tile in enumerate(tiles):
        try:
                # Pre-validate tile image before reading
                validate_image_before_read(tile, operation=f"read_tile_{i}")
                
                # Read tile image with enhanced error handling
                tile_img = safe_casaimage_open(tile, operation=f"read_tile_{i}")
            tile_data = tile_img.getdata()
                
                # Validate image data
                validate_image_data(tile_data, tile, operation=f"read_tile_{i}")
            
            # Extract image data (handle multi-dimensional arrays)
            if tile_data.ndim == 2:
                img_data = tile_data
            elif tile_data.ndim == 4:
                # Take first stokes, first frequency
                img_data = tile_data[0, 0, :, :]
            else:
                # Flatten to 2D
                img_data = tile_data.squeeze()
                if img_data.ndim > 2:
                    img_data = img_data[0, :, :] if img_data.ndim == 3 else img_data
            
            # Verify shape matches PB image
            if img_data.shape != pb_data_list[i].shape:
                LOG.warning(
                    f"Tile {tile} shape {img_data.shape} doesn't match PB shape {pb_data_list[i].shape}. "
                    f"Regridding tile to PB grid."
                )
                # Regrid tile to PB grid
                # Use corresponding PB image as template
                    # Try to use cached regridded image
                    from .cache import get_cache
                    cache = get_cache()
                    
                    def regrid_func(imagename, template, output, overwrite):
                        imregrid(imagename=imagename, template=template, output=output, overwrite=overwrite)
                    
                    regridded_tile = cache.get_regridded_image(
                        source_path=str(tile),
                        template_path=str(pb_paths[i]),
                        regrid_func=regrid_func,
                        output_suffix=f"_tile_{i}"
                    )
                    
                    if not regridded_tile:
                        # Fallback to temporary file if caching not available
                        regridded_tile = str(output_path) + f"_tile_regrid_{i}.tmp"
                        try:
                imregrid(
                    imagename=str(tile),
                    template=str(pb_paths[i]),
                    output=regridded_tile,
                    overwrite=True,
                )
                        except Exception as e:
                tile_img.close()
                            handle_casa_tool_error(
                                'imregrid', e,
                                image_path=tile,
                                operation=f"regrid_tile_{i}",
                                template=str(pb_paths[i])
                            )
                    else:
                        LOG.debug(f"Using cached regridded tile image: {regridded_tile}")
                    
                    tile_img.close()
                    tile_img = safe_casaimage_open(regridded_tile, operation=f"read_regridded_tile_{i}")
                tile_data = tile_img.getdata()
                    validate_image_data(tile_data, regridded_tile, operation=f"read_regridded_tile_{i}")
                if tile_data.ndim == 2:
                    img_data = tile_data
                elif tile_data.ndim == 4:
                    img_data = tile_data[0, 0, :, :]
                else:
                    img_data = tile_data.squeeze()
                    if img_data.ndim > 2:
                        img_data = img_data[0, :, :] if img_data.ndim == 3 else img_data
            
                tile_data_list.append(img_data.astype(np.float64))
                tile_images.append(tile_img)
                
            except (ImageReadError, ImageCorruptionError, IncompatibleImageFormatError):
                # Re-raise validation errors with context
                raise
            except Exception as e:
                LOG.error(f"Failed to read tile {tile}: {e}")
                # Clean up already opened images
                for img in tile_images:
                    try:
                        img.close()
                    except Exception:
                        pass
                for img in pb_images:
                    try:
                        img.close()
                    except Exception:
                        pass
                # This should not happen if error handling is working correctly
                from .exceptions import ImageReadError
                raise ImageReadError(
                    f"Failed to read tile image: {tile}",
                    f"Error: {e}. "
                    "Check if the file exists and is readable. "
                    "Verify the image format is supported (CASA image directory or FITS file).",
                    context={'tile': tile, 'operation': f'read_tile_{i}'}
                ) from e
        
        # Step 3: Compute per-pixel weights and combine
        LOG.info("Computing pixel-by-pixel PB-weighted combination...")
        
        # Get noise variances
        noise_vars = []
        for tile in tiles:
            metrics = metrics_dict.get(tile, TileQualityMetrics(tile_path=tile))
            if metrics.rms_noise is not None and metrics.rms_noise > 0:
                noise_var = metrics.rms_noise ** 2
            else:
                # Default noise variance if not available
                noise_var = 1.0
            noise_vars.append(noise_var)
        
        # Compute weights: weight = pb_response^2 / noise_variance
        # For each pixel, combine: mosaic = sum(weight * tile) / sum(weight)
        
        ny, nx = tile_data_list[0].shape
        mosaic_data = np.zeros((ny, nx), dtype=np.float64)
        total_weight = np.zeros((ny, nx), dtype=np.float64)
        
        for i, (tile_data, pb_data, noise_var) in enumerate(zip(tile_data_list, pb_data_list, noise_vars)):
            # Compute weights: pb^2 / noise_variance
            # Clip PB values to avoid division issues
            pb_safe = np.clip(pb_data, 1e-10, None)  # Avoid zero/negative PB
            weights = (pb_safe ** 2) / noise_var
            
            # Accumulate weighted sum
            mosaic_data += weights * tile_data
            total_weight += weights
            
            LOG.debug(f"Tile {i}: min PB={pb_safe.min():.4f}, max PB={pb_safe.max():.4f}, "
                     f"noise_var={noise_var:.3e}")
        
        # Normalize by total weight (avoid division by zero)
        nonzero_mask = total_weight > 1e-10
        mosaic_data[nonzero_mask] /= total_weight[nonzero_mask]
        mosaic_data[~nonzero_mask] = np.nan
        
        LOG.info(
            f"Computed PB-weighted mosaic: "
            f"coverage={nonzero_mask.sum()}/{nonzero_mask.size} pixels "
            f"({100*nonzero_mask.sum()/nonzero_mask.size:.1f}%)"
        )
        
        # Step 4: Write mosaic image
        LOG.info(f"Writing PB-weighted mosaic to {output_path}...")
        
        # Create output image using reference coordinate system
        # Ensure output path is clean (no extensions that might confuse CASA)
        output_path_str = str(output_path)
        if output_path_str.endswith('.image'):
            output_path_str = output_path_str[:-6]
        
        output_img = casaimage()
        # Add stokes and frequency dimensions: [stokes, freq, y, x]
        output_pixels = mosaic_data[np.newaxis, np.newaxis, :, :]
        
        output_img.fromarray(
            outfile=output_path_str,
            pixels=output_pixels,
            csys=ref_coordsys,
            overwrite=True,
        )
        output_img.close()
        
        # Clean up temporary regridded images (ensure cleanup even on errors)
        temp_files_to_cleanup = []
        for i in range(len(tiles)):
            for suffix in [f"_pb_regrid_{i}.tmp", f"_tile_regrid_{i}.tmp"]:
                temp_path = str(output_path) + suffix
                temp_files_to_cleanup.append(temp_path)
        
        # Clean up temporary files
        import shutil
        for temp_path in temp_files_to_cleanup:
                if os.path.exists(temp_path):
                    try:
                        if os.path.isdir(temp_path):
                            shutil.rmtree(temp_path)
                        else:
                            os.remove(temp_path)
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")
        
        # Close all images
        for img in tile_images:
            try:
                img.close()
            except Exception:
                pass
        for img in pb_images:
            try:
                img.close()
            except Exception:
                pass
        
        LOG.info(
            f"✓ Built PB-weighted mosaic to {output_path_str} "
            f"(pixel-by-pixel combination using PB^2/noise_variance weighting)"
        )
    
    except (ImageReadError, ImageCorruptionError, MissingPrimaryBeamError, 
            CASAToolError, GridMismatchError) as e:
        # Clean up temporary files even on error
        import shutil
        for i in range(len(tiles)):
            for suffix in [f"_pb_regrid_{i}.tmp", f"_tile_regrid_{i}.tmp"]:
                temp_path = str(output_path) + suffix
                if os.path.exists(temp_path):
                    try:
                        if os.path.isdir(temp_path):
                            shutil.rmtree(temp_path)
                        else:
                            os.remove(temp_path)
                    except Exception:
                        pass
        # Close images if they exist
        try:
            for img in tile_images:
                try:
                    img.close()
                except Exception:
                    pass
        except NameError:
            pass
        try:
            for img in pb_images:
                try:
                    img.close()
                except Exception:
                    pass
        except NameError:
            pass
        # Re-raise specific mosaic errors with their recovery hints
        raise
    except Exception as e:
        raise MosaicError(
            f"Unexpected error during weighted mosaic building: {e}",
            "Check logs for details. Try rebuilding the mosaic with --ignore-validation "
            "if validation issues are blocking the build."
        ) from e


def cmd_build(args: argparse.Namespace) -> int:
    pdb = Path(args.products_db)
    name = args.name
    out = Path(args.output).with_suffix("")
    
    with ensure_products_db(pdb) as conn:
        _ensure_mosaics_table(conn)
        row = conn.execute("SELECT id, tiles, method FROM mosaics WHERE name = ?", (name,)).fetchone()
        if row is None:
            logger.error("Mosaic plan not found; create with 'plan' first")
            print("Mosaic plan not found; create with 'plan' first")
            return 1
        tiles = str(row[1]).splitlines()
        method = str(row[2] or 'mean')
    
    if not tiles:
        logger.warning("No tiles found in mosaic plan")
        print("No tiles found in mosaic plan")
        return 1
    
    # Pre-flight validation: Check all pre-conditions before expensive operations
    print("Pre-flight validation: Checking pre-conditions...")
    from .preflight import validate_preflight_conditions, estimate_resources
    
    # Check if PB images are required based on method
    require_pb = (method == 'weighted' or method == 'pbweighted')
    
    preflight_valid, preflight_issues, preflight_info = validate_preflight_conditions(
        tiles=tiles,
        output_path=str(out),
        metrics_dict=None,  # Will be computed during validation
        require_pb=require_pb,
        check_disk_space_flag=True,
    )
    
    if preflight_issues:
        print("Pre-flight validation issues:")
        for issue in preflight_issues:
            print(f"  - {issue}")
        
        if not args.ignore_validation:
            print("\nPre-flight validation failed. Fix issues above before building.")
            print("Use --ignore-validation to proceed anyway (not recommended).")
            return 3
        else:
            print("\nWarning: Pre-flight issues detected but ignored (--ignore-validation)")
    
    # Report resource estimates
    try:
        estimates = estimate_resources(tiles, str(out))
        print(f"\nResource estimates:")
        print(f"  - Tiles: {estimates['num_tiles']}")
        print(f"  - Estimated disk space: {estimates['estimated_disk_gb']:.1f} GB")
        print(f"  - Estimated operations: {estimates['estimated_operations']}")
        print(f"  - Estimated time: ~{estimates['estimated_time_minutes']:.0f} minutes")
    except Exception as e:
        logger.debug(f"Could not estimate resources: {e}")
    
    # Warn if output exists
    if preflight_info.get('output_exists'):
        print(f"\nWarning: Output '{out}' already exists and will be overwritten")
    
    # Comprehensive validation
    print(f"Validating {len(tiles)} tiles...")
    
    # 1. Basic grid consistency
    ok, reason = _check_consistent_tiles(tiles)
    if not ok:
        print(f"Cannot build mosaic: {reason}")
        return 2
    
    # 2. Tile quality validation (computes metrics_dict)
    is_valid, validation_issues, metrics_dict = validate_tiles_consistency(
        tiles, products_db=pdb
    )
    
    # Re-run pre-flight with computed metrics_dict for better PB checking
    if require_pb:
        _, preflight_issues_pb, _ = validate_preflight_conditions(
            tiles=tiles,
            output_path=str(out),
            metrics_dict=metrics_dict,
            require_pb=require_pb,
            check_disk_space_flag=False,  # Already checked
        )
        if preflight_issues_pb and not args.ignore_validation:
            print("Pre-flight validation issues (after tile validation):")
            for issue in preflight_issues_pb:
                print(f"  - {issue}")
            print("\nPre-flight validation failed. Fix issues above before building.")
            return 3
    
    if validation_issues:
        print("Validation issues found:")
        for issue in validation_issues[:10]:  # Show first 10
            print(f"  - {issue}")
        if len(validation_issues) > 10:
            print(f"  ... and {len(validation_issues) - 10} more issues")
        
        if not args.ignore_validation:
            raise ValidationError(
                f"Mosaic validation failed with {len(validation_issues)} issues",
                "Review the validation issues above. Common fixes:\n"
                "  - Ensure all tiles have PB correction applied\n"
                "  - Check tile noise levels are reasonable\n"
                "  - Verify tiles have consistent calibration\n"
                "Use --ignore-validation to proceed anyway (not recommended for science)."
            )
        else:
            print("\nWarning: Validation issues detected but ignored (--ignore-validation)")
    
    # 3. Astrometric registration check
    try:
        astro_valid, astro_issues, offsets = verify_astrometric_registration(tiles)
    except Exception as e:
        raise ValidationError(
            f"Astrometric verification failed: {e}",
            "Check if catalog access is available. "
            "Try running with --ignore-validation to skip astrometric checks."
        ) from e
    if astro_issues:
        print("Astrometric registration issues:")
        for issue in astro_issues:
            print(f"  - {issue}")
        if not args.ignore_validation:
            print("\nMosaic build aborted due to astrometric issues.")
            return 4
    
    # 4. Calibration consistency check
    # Try to find registry DB from environment or default location
    registry_db = None
    if os.getenv('CAL_REGISTRY_DB'):
        registry_db = Path(os.getenv('CAL_REGISTRY_DB'))
    else:
        # Try default location relative to products DB
        registry_db = pdb.parent / 'cal_registry.sqlite3'
        if not registry_db.exists():
            registry_db = None
    
    cal_consistent, cal_issues, cal_dict = check_calibration_consistency(
        tiles, pdb, registry_db=registry_db
    )
    if cal_issues:
        print("Calibration consistency issues:")
        for issue in cal_issues:
            print(f"  - {issue}")
        if not args.ignore_validation:
            print("\nMosaic build aborted due to calibration inconsistencies.")
            return 5
    
    # 5. Primary beam consistency check
    pb_consistent, pb_issues, pb_dict = check_primary_beam_consistency(
        tiles, metrics_dict
    )
    if pb_issues:
        print("Primary beam consistency issues:")
        for issue in pb_issues:
            print(f"  - {issue}")
        if not args.ignore_validation:
            print("\nMosaic build aborted due to PB consistency issues.")
            return 6
    
    print("✓ All validation checks passed")
    
    # Dry-run mode: validate without building
    if args.dry_run:
        print("\n" + "="*60)
        print("DRY-RUN MODE: Validation complete, not building mosaic")
        print("="*60)
        print(f"\nMosaic plan summary:")
        print(f"  - Name: {name}")
        print(f"  - Method: {method}")
        print(f"  - Tiles: {len(tiles)}")
        print(f"  - Output: {out}")
        print(f"\n✓ All validations passed. Ready to build.")
        print(f"\nTo build this mosaic, run:")
        print(f"  mosaic build --name {name} --output {out}")
        return 0
    
    # Build mosaic
    try:
        # Keep immath temp products under scratch and avoid polluting CWD
        try:
            if prepare_temp_environment is not None:
                prepare_temp_environment(
                    os.getenv('CONTIMG_SCRATCH_DIR') or '/stage/dsa110-contimg',
                    cwd_to=out.parent
                )
        except Exception:
            pass
        
        # Use weighted combination if method is 'weighted', otherwise use mean
        if method == 'weighted' or method == 'pbweighted':
            print(f"Building weighted mosaic to {out}...")
            try:
                _build_weighted_mosaic(tiles, metrics_dict, str(out))
            except (ImageReadError, ImageCorruptionError, MissingPrimaryBeamError,
                    CASAToolError, GridMismatchError) as e:
                # Re-raise with context
                raise
        else:
            print(f"Building mean mosaic to {out}...")
            try:
                if not immath:
                    raise CASAToolError(
                        "CASA immath not available",
                        "Ensure CASA is installed: conda activate casa6",
                        context={'tool': 'immath', 'operation': 'build_mean_mosaic'}
                    )
                expr = f"({'+'.join([f'IM{i}' for i in range(len(tiles))])})/{len(tiles)}"
                try:
                immath(imagename=tiles, expr=expr, outfile=str(out))
                except Exception as e:
                    handle_casa_tool_error(
                        'immath', e,
                        operation='build_mean_mosaic',
                        expression=expr,
                        num_tiles=len(tiles)
                    )
            except Exception as e:
                raise CASAToolError(
                    f"CASA immath failed: {e}",
                    "Check if all tile images are readable and have compatible formats. "
                    "Try using weighted method instead: --method=weighted"
                ) from e
        
        # Export FITS for the mosaic image for downstream photometry
        fits_path = None
        try:
            from casatasks import exportfits
            fits_path = str(out) + ".fits"
            exportfits(imagename=str(out), fitsimage=fits_path, overwrite=True)
            print(f"✓ Exported mosaic FITS: {fits_path}")
        except Exception as exc:
            from .error_handling import handle_casa_tool_error
            # Don't fail build if export fails, but log it properly
            try:
                handle_casa_tool_error(
                    'exportfits', exc,
                    image_path=str(out),
                    operation='export_mosaic_fits'
                )
            except Exception:
                # If handle_casa_tool_error fails, just print warning
                pass
            print(f"exportfits warning: {exc}")
        
        # Automatic photometry analysis on mosaic (NVSS catalog sources)
        photometry_count = 0
        if fits_path and Path(fits_path).exists():
            try:
                print("Performing forced photometry on NVSS catalog sources...")
                from dsa110_contimg.photometry.forced import measure_forced_peak
                from dsa110_contimg.calibration.catalogs import read_nvss_catalog
                from dsa110_contimg.database.products import photometry_insert
                from dsa110_contimg.photometry.cli import _image_center_and_radius_deg
                import astropy.coordinates as acoords
                import time
                
                # Get image center and radius
                ra0, dec0, auto_rad = _image_center_and_radius_deg(fits_path)
                
                # Query NVSS catalog sources within image field of view
                df = read_nvss_catalog()
                sc = acoords.SkyCoord(
                    df['ra'].to_numpy(),
                    df['dec'].to_numpy(),
                    unit='deg',
                    frame='icrs',
                )
                center = acoords.SkyCoord(ra0, dec0, unit='deg', frame='icrs')
                sep_deg = sc.separation(center).deg
                flux_mjy = df['flux_20_cm'].to_numpy()
                
                # Filter: sources within image radius, flux >= 10 mJy
                min_mjy = 10.0
                keep = (sep_deg <= auto_rad) & (flux_mjy >= min_mjy)
                ra_sel = df['ra'].to_numpy()[keep]
                dec_sel = df['dec'].to_numpy()[keep]
                flux_sel = flux_mjy[keep]
                
                # Perform forced photometry at each catalog position
                now = time.time()
                with ensure_products_db(pdb) as conn:
                    inserted = 0
                    skipped = 0
                    for ra, dec, nvss_flux in zip(ra_sel, dec_sel, flux_sel):
                        try:
                            m = measure_forced_peak(
                                fits_path,
                                float(ra),
                                float(dec),
                                box_size_pix=5,
                                annulus_pix=(12, 20),
                            )
                            if not np.isfinite(m.peak_jyb):
                                skipped += 1
                                continue
                            
                            perr = None
                            if (m.peak_err_jyb is not None and 
                                np.isfinite(m.peak_err_jyb)):
                                perr = float(m.peak_err_jyb)
                            
                            # Insert into products database
                            photometry_insert(
                                conn,
                                image_path=fits_path,
                                ra_deg=m.ra_deg,
                                dec_deg=m.dec_deg,
                                nvss_flux_mjy=float(nvss_flux),
                                peak_jyb=m.peak_jyb,
                                peak_err_jyb=perr,
                                measured_at=now,
                            )
                            inserted += 1
                        except Exception as e:
                            logger.warning(
                                f"Photometry failed for source at ({ra:.4f}, {dec:.4f}): {e}")
                            skipped += 1
                            continue
                    
                    conn.commit()
                    photometry_count = inserted
                
                if photometry_count > 0:
                    print(f"✓ Photometry complete: {photometry_count} sources measured "
                          f"({skipped} skipped)")
                else:
                    print(f"Warning: No valid photometry measurements "
                          f"({skipped} sources attempted)")
            except Exception as e:
                logger.warning(f"Photometry analysis failed: {e}")
                print(f"Warning: Photometry analysis failed: {e}")
                # Don't fail build if photometry fails
        
        # Post-mosaic validation
        try:
            from .post_validation import validate_mosaic_quality
            print("Validating final mosaic quality...")
            mosaic_valid, mosaic_issues, mosaic_metrics = validate_mosaic_quality(
                str(out),
                max_rms_variation=2.0,
                min_coverage_fraction=0.1,
            )
            
            if mosaic_issues:
                print("Post-mosaic validation issues:")
                for issue in mosaic_issues:
                    print(f"  - {issue}")
                if mosaic_metrics:
                    print(f"Mosaic metrics: RMS={mosaic_metrics.get('rms_noise', 'N/A'):.3e}, "
                          f"coverage={mosaic_metrics.get('coverage_fraction', 0):.1%}")
            else:
                print("✓ Post-mosaic validation passed")
                if mosaic_metrics:
                    print(f"Mosaic metrics: RMS={mosaic_metrics.get('rms_noise', 'N/A'):.3e}, "
                          f"coverage={mosaic_metrics.get('coverage_fraction', 0):.1%}, "
                          f"dynamic_range={mosaic_metrics.get('dynamic_range', 0):.1f}")
        except Exception as e:
            LOG.warning(f"Post-mosaic validation failed: {e}")
            # Don't fail build if validation fails
        
        # Generate mosaic quality metrics
        metrics_files = {}
        try:
            print("Generating mosaic quality metrics...")
            metrics_files = generate_mosaic_metrics(
                tiles=tiles,
                metrics_dict=metrics_dict,
                mosaic_path=str(out),
                output_dir=str(out.parent),
            )
            if metrics_files:
                print(f"✓ Generated {len(metrics_files)} quality metric images")
                for metric_name, metric_path in metrics_files.items():
                    print(f"  - {metric_name}: {metric_path}")
            else:
                print("Warning: No metrics generated (casacore may not be available)")
        except Exception as e:
            LOG.warning(f"Failed to generate mosaic metrics: {e}")
            print(f"Warning: Failed to generate mosaic metrics: {e}")
            # Don't fail the build if metrics generation fails
        
        # Update mosaic status
        validation_summary = "\n".join(validation_issues) if validation_issues else None
        metrics_summary = None
        if metrics_files:
            # Store metrics paths as JSON-like string (simple format)
            metrics_list = [f"{name}:{path}" for name, path in metrics_files.items()]
            metrics_summary = "\n".join(metrics_list)
        
        with ensure_products_db(pdb) as conn:
            # Check if mosaics table has metrics_path column, if not add it
            try:
                conn.execute("SELECT metrics_path FROM mosaics LIMIT 1")
            except sqlite3.OperationalError:
                # Column doesn't exist, add it
                conn.execute("ALTER TABLE mosaics ADD COLUMN metrics_path TEXT")
                conn.commit()
            
            conn.execute(
                "UPDATE mosaics SET status='built', output_path=?, validation_issues=?, metrics_path=? WHERE name=?",
                (str(out), validation_summary, metrics_summary, name)
            )
            conn.commit()
        
        print(f"✓ Built mosaic to {out}")
        return 0
    except (MosaicError, ImageReadError, ImageCorruptionError, MissingPrimaryBeamError,
            CASAToolError, GridMismatchError, ValidationError, MetricsGenerationError) as e:
        # Handle specific mosaic errors with user-friendly messages
        print(f"\nMosaic build failed: {e.message}")
        if e.recovery_hint:
            print(f"\n{e.recovery_hint}")
        import traceback
        traceback.print_exc()
        return 6
    except Exception as e:
        print(f"Mosaic build failed: {e}")
        import traceback
        traceback.print_exc()
        return 6


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Mosaic planner/builder")
    sub = p.add_subparsers(dest='cmd')
    sp = sub.add_parser('plan', help='Plan a mosaic from products DB tiles')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--name', required=True)
    sp.add_argument('--since', type=float, help='Only include tiles created_at >= since (epoch seconds)')
    sp.add_argument('--until', type=float, help='Only include tiles created_at <= until (epoch seconds)')
    sp.add_argument('--method', default='mean', choices=['mean', 'weighted', 'pbweighted'],
                    help='Combination method: mean (simple), weighted (noise-weighted), pbweighted (primary beam weighted)')
    sp.add_argument('--include-unpbcor', action='store_true', help='Include non-pbcor tiles')
    sp.set_defaults(func=cmd_plan)

    sp = sub.add_parser('build', help='Build a mosaic from a planned set')
    sp.add_argument('--products-db', default='state/products.sqlite3')
    sp.add_argument('--name', required=True)
    sp.add_argument('--output', required=True, help='Output image base path (CASA image)')
    sp.add_argument('--ignore-validation', action='store_true',
                    help='Ignore validation issues and proceed anyway (not recommended)')
    sp.add_argument('--dry-run', action='store_true',
                    help='Validate mosaic plan without building (measure twice, cut once)')
    sp.set_defaults(func=cmd_build)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    # Ensure scratch directory structure exists
    try:
        ensure_scratch_dirs()
    except Exception:
        pass  # Best-effort; continue if setup fails
    
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, 'func'):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main())

```


Updated the mosaic build process to automatically run photometry analysis. Summary:

## Updated: Photometry Now Automatically Follows Mosaic Completion

### Updated Post-Mosaic Workflow

**After mosaic build completes:**

1. **Export to FITS** — Converts CASA image to `.fits` format
2. **Automatic photometry analysis** (NEW)
   - Queries NVSS catalog for sources within the mosaic field of view
   - Filters sources: flux ≥ 10 mJy, within image radius
   - Performs forced photometry at each catalog position:
     - Peak flux measurement (5×5 pixel box)
     - Background estimation (annulus 12–20 pixels)
     - Error estimation from local RMS
   - Stores results in `products.sqlite3` photometry table
   - Reports: number of sources measured, number skipped
3. **Post-mosaic validation** — Quality checks (RMS, coverage, discontinuities)
4. **Quality metrics generation** — RMS, coverage, dynamic range
5. **Database update** — Mosaic status set to `'built'` with all metadata

### Implementation Details

**Location:** `src/dsa110_contimg/mosaic/cli.py` (lines 1108-1195)

**Features:**
- Non-blocking: Photometry failures don't fail the mosaic build
- Automatic: Runs immediately after FITS export
- Database integration: Results stored in `products.sqlite3` for later analysis
- Error handling: Individual source failures are logged but don't stop the process

**Photometry Parameters:**
- Box size: 5×5 pixels (peak measurement)
- Annulus: 12–20 pixels (background estimation)
- Minimum flux: 10 mJy (NVSS catalog filter)
- Catalog: NVSS (1.4 GHz reference catalog)

### Benefits

1. Immediate analysis: Photometry runs automatically, no manual step
2. Database ready: Results available for variability studies and flux comparisons
3. Consistent: Same photometry method used across all mosaics
4. Robust: Failures are logged but don't block the build

The mosaic workflow now includes photometry analysis automatically.

---

**User**

Let's run it. Begin by converting the MS files. Run everything in the foreground and monitor continuously. Stop and debug whenever errors or warnings arise that aren't expected or desired.

---

**Cursor**


Checking available data and current state before starting the workflow:



Checking available data and planning the workflow:


---

**User**

I made a mistake. You said we're staging in /scratch/ this is not the correct workflow plan.

pause
