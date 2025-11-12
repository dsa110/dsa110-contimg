# Detailed Testing Plan: 0834 Transit End-to-End Pipeline Test

**Date:** 2025-11-02  
**Objective:** Test complete pipeline from MS generation to mosaicking for 0834+555 transit  
**Principle:** Use actual pipeline components at every step - no shortcuts or assumptions

---

## Phase 1: Proper Transit Time Calculation

### Step 1.1: Load Calibrator Coordinates
**Tool:** `dsa110_contimg.calibration.catalogs.load_vla_catalog()`  
**Environment:** `casa6` conda environment  
**Action:**
```python
from dsa110_contimg.calibration.catalogs import load_vla_catalog

# Load catalog (automatically prefers SQLite database)
# Uses: state/catalogs/vla_calibrators.sqlite3
df = load_vla_catalog()

# Get 0834+555 coordinates
ra_deg = float(df.loc['0834+555']['ra_deg'])
dec_deg = float(df.loc['0834+555']['dec_deg'])
```

**Note:** `load_vla_catalog()` automatically resolves to SQLite database (`state/catalogs/vla_calibrators.sqlite3`) if available, otherwise falls back to CSV. This is the preferred method.

**Success Criteria:**
- ✓ RA and Dec successfully loaded
- ✓ Values are finite and reasonable

**Validation:**
- Print RA, Dec values
- Verify RA ~128.73°, Dec ~+55.57°

---

### Step 1.2: Calculate Transit Times Using Proper Method
**Tool:** `dsa110_contimg.calibration.schedule.previous_transits()`  
**Environment:** `casa6` conda environment  
**Action:**
```python
from dsa110_contimg.calibration.schedule import previous_transits
from astropy.time import Time

# Calculate transit times
transits = previous_transits(
    ra_deg=ra_deg,
    start_time=Time.now(),
    n=5  # Get last 5 transits
)

# Select most recent transit
latest_transit = transits[0]
```

**Success Criteria:**
- ✓ Transit times calculated successfully
- ✓ Transit time is within last 14 days
- ✓ Transit time matches expected ~08:34 UTC pattern

**Validation:**
- Print all calculated transit times
- Verify transit time is reasonable (not in future)
- Store transit time for next step

---

### Step 1.3: Calculate Search Window
**Tool:** `astropy.time.Time` arithmetic  
**Environment:** `casa6` conda environment  
**Action:**
```python
from astropy.time import Time
import astropy.units as u

# Search window: ±30 minutes around transit
window_minutes = 60
half = window_minutes // 2

start_time = (latest_transit - half * u.min).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
end_time = (latest_transit + half * u.min).to_datetime().strftime('%Y-%m-%d %H:%M:%S')
```

**Success Criteria:**
- ✓ Start and end times calculated correctly
- ✓ Window is 60 minutes (±30 minutes around transit)
- ✓ Times are in correct format for orchestrator

**Validation:**
- Print start_time and end_time
- Verify format: "YYYY-MM-DD HH:MM:SS"

**Notes:**
- The search window accounts for the fact that files may be timestamped slightly after the actual transit time
- Tolerance is set to account for file processing delays and system clock differences
- Times should be in ISO format for `find_subband_groups()`: "YYYY-MM-DDTHH:MM:SS.sss"

---

### Step 1.4: Verify Data Exists on Disk
**Tool:** `dsa110_contimg.conversion.strategies.hdf5_orchestrator.find_subband_groups()`  
**Environment:** `casa6` conda environment  
**Action:**
```python
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import find_subband_groups
import os

# Verify HDF5 files exist for the calculated time window
input_dir = os.getenv("CONTIMG_INPUT_DIR", "/data/incoming")
groups = find_subband_groups(
    input_dir=input_dir,
    start_time=start_time,  # From Step 1.3 (ISO format: "YYYY-MM-DDTHH:MM:SS.sss")
    end_time=end_time,      # From Step 1.3 (ISO format: "YYYY-MM-DDTHH:MM:SS.sss")
    tolerance_s=30.0
)

if not groups:
    # Try earlier transits if data not found
    print(f"⚠ No data found for transit {latest_transit.isot}")
    print(f"  Trying earlier transit times...")
    for earlier_transit in transits[1:4]:  # Try next 3 transits
        earlier_start = (earlier_transit - half * u.min).isot
        earlier_end = (earlier_transit + half * u.min).isot
        earlier_groups = find_subband_groups(input_dir, earlier_start, earlier_end, tolerance_s=30.0)
        if earlier_groups:
            print(f"✓ Found data for transit {earlier_transit.isot}")
            groups = earlier_groups
            start_time = earlier_start
            end_time = earlier_end
            latest_transit = earlier_transit
            break
    
    if not groups:
        raise RuntimeError(
            f"No complete subband groups found in {input_dir} for any transit in window.\n"
            f"  Searched transits: {[t.isot for t in transits[:5]]}\n"
            f"  Check if data exists in {input_dir}"
        )

print(f"✓ Found {len(groups)} complete subband group(s)")
for i, group in enumerate(groups, 1):
    print(f"  Group {i}: {len(group)} files")
    print(f"    First: {os.path.basename(group[0])}")
    print(f"    Last:  {os.path.basename(group[-1])}")
    # Verify all files exist
    all_exist = all(os.path.exists(f) for f in group)
    if not all_exist:
        missing = [f for f in group if not os.path.exists(f)]
        raise RuntimeError(f"Missing files in group {i}: {len(missing)} files not found")
```

**Success Criteria:**
- ✓ At least one complete subband group found (16 files: sb00 through sb15)
- ✓ All files in group exist on disk and are readable
- ✓ Files are within the calculated time window
- ✓ Transit time selected has corresponding data available

**Failure Handling:**
- If no groups found for most recent transit: Automatically try earlier transits (up to 5 total)
- If no groups found for any transit: Report error with all transit times searched
- If incomplete groups: Check for missing subbands or data gaps
- If files don't exist: Report which files are missing

**Critical Notes:**
- **This step MUST be performed before proceeding to Phase 2** - it's a critical pre-flight check
- If this check fails, the pipeline should NOT proceed to MS generation
- Transit time may need to be adjusted to an earlier transit if data hasn't been written yet
- The function automatically validates that groups contain all 16 subbands
- This verification step is part of the default workflow and should never be skipped

---

## Phase 2: MS Generation Using Actual Pipeline

### Step 2.1: Verify Pre-conditions
**Pre-flight Checks:**
- [x] **Data exists on disk** (verified in Phase 1.4) - ✓ Complete subband groups found
- [ ] Input directory `/data/incoming` exists and is readable
- [ ] Output directory `/scratch/dsa110-contimg/ms/0834_transit` is writable
- [ ] Disk space sufficient (estimate: ~10 GB per MS)
- [ ] tmpfs available (`/dev/shm`) with sufficient space (>20 GB free)
- [ ] Environment variables set:
  - `PYTHONPATH=/data/dsa110-contimg/src`
  - `HDF5_USE_FILE_LOCKING=FALSE`

**Note:** The data existence check (Phase 1.4) must be completed successfully before proceeding to Phase 2. This ensures we don't waste time attempting MS generation when data is unavailable.

**Validation:**
```bash
# Check disk space
df -h /scratch/dsa110-contimg
df -h /dev/shm

# Check permissions
ls -ld /data/incoming
mkdir -p /scratch/dsa110-contimg/ms/0834_transit
```

---

### Step 2.2: Run hdf5_orchestrator CLI
**Tool:** `dsa110_contimg.conversion.strategies.hdf5_orchestrator` CLI  
**Environment:** `casa6` conda environment with `PYTHONPATH` set  
**Action:**
```bash
export PYTHONPATH=/data/dsa110-contimg/src

conda run -n casa6 python3 -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /scratch/dsa110-contimg/ms/0834_transit \
    "$start_time" \
    "$end_time" \
    --writer parallel-subband \
    --stage-to-tmpfs \
    --max-workers 4 \
    --log-level INFO
```

**Parameters:**
- `input_dir`: `/data/incoming` (actual incoming directory)
- `output_dir`: `/scratch/dsa110-contimg/ms/0834_transit`
- `start_time`: From Step 1.3 (properly calculated)
- `end_time`: From Step 1.3 (properly calculated)
- `--writer`: `parallel-subband` (production method for 16 subbands)
- `--stage-to-tmpfs`: Use RAM staging (production default)
- `--max-workers`: 4 (parallel processing)

**Success Criteria:**
- ✓ Orchestrator runs without errors
- ✓ At least one MS file created
- ✓ MS files are readable
- ✓ MS files have required columns (DATA, CORRECTED_DATA, MODEL_DATA, etc.)

**Validation:**
```bash
# Check MS files created
ls -lh /scratch/dsa110-contimg/ms/0834_transit/*.ms

# Verify MS structure
python3 -c "
from casacore.tables import table
ms = '/scratch/dsa110-contimg/ms/0834_transit/<ms_name>.ms'
with table(ms, readonly=True) as tb:
    print(f'Rows: {tb.nrows()}')
    print(f'Columns: {tb.colnames()}')
"
```

**Expected Output:**
- MS files named: `YYYY-MM-DDTHH:MM:SS.ms`
- At least one complete 16-subband group converted
- MS files in output directory

**Known Issues:**
- Intermittent tmpfs file locking errors during concat (see "Error Analysis" section below)
- If failure occurs, retry with cleanup of stale tmpfs directories

---

### Error Analysis: Tmpfs File Locking During Concurrent Operations

**Date:** 2025-11-02  
**Phase:** 2.2 (MS Generation)  
**Status:** Resolved via retry

**Incident:**
During Phase 2.2 execution, 2 out of 10 groups failed during CASA concat operation:
1. Group `2025-11-01T13:22:56`: Error "incorrect number of bytes read" for sb08.ms (recovered/retried)
2. Group `2025-11-01T14:10:49`: Error "cannot be opened for read/write" for sb01.ms (failed completely)

**Root Cause Analysis:**
The successful retry of the failed group (`2025-11-01T14:10:49`) with identical input data revealed:

1. **Not a data corruption issue:**
   - Same input files worked perfectly on retry
   - Error was environmental/system-level, not data-related

2. **Race condition/concurrency issue:**
   - Original run: 10 groups processed sequentially, but tmpfs cleanup may not have completed between groups
   - Retry: Single group in isolation succeeded without interference
   - Suggests cleanup timing/race condition in parallel-subband writer

3. **File handle/locking problem:**
   - Error message: "cannot be opened for read/write" indicates file handle still open
   - Likely cause: CASA file handles from previous concat operation not fully closed
   - Retry succeeded after cleanup cleared stale locks

4. **tmpfs directory state issue:**
   - Stale tmpfs directories found after failure (`/dev/shm/dsa110-contimg/2025-11-01T14:10:49`)
   - Cleanup before retry reset state and resolved issue
   - Indicates cleanup in `direct_subband.py` (lines 289-295) may not always complete or may be interrupted

**Root Cause: Incomplete Cleanup Between Groups**
- The writer cleans up per-subband parts after concat (lines 291-293 in `direct_subband.py`)
- If cleanup fails or is interrupted, stale files/locks remain in tmpfs
- Next group encounters locked files when attempting concat
- Sequential processing amplifies the issue if cleanup doesn't complete

**Impact:**
- Intermittent failures (~10% failure rate observed)
- Success rate: 90% (9/10 groups succeeded on first attempt)
- Retry with cleanup resolves issue, but adds manual intervention

**Workaround:**
- Retry failed groups with cleanup of stale tmpfs directories
- Command: `rm -rf /dev/shm/dsa110-contimg/<group_timestamp>*` before retry
- Retry with narrow time window to isolate the specific group

**Recommendations:**
See follow-up issue: `docs/reports/CONVERSION_ROBUSTNESS_IMPROVEMENTS.md`

---

### Step 2.3: Verify MS Quality
**Tool:** `dsa110_contimg.qa.pipeline_quality.check_ms_after_conversion()`  
**Environment:** `casa6` conda environment  
**Action:**
```python
from dsa110_contimg.qa.pipeline_quality import check_ms_after_conversion

ms_path = "/scratch/dsa110-contimg/ms/0834_transit/<ms_name>.ms"
passed, metrics = check_ms_after_conversion(
    ms_path=ms_path,
    quick_check_only=False,
    alert_on_issues=True
)
```

**Success Criteria:**
- ✓ MS passes quality checks
- ✓ No critical issues (missing columns, zero rows, etc.)
- ✓ Flagging rate < 50%
- ✓ Data statistics reasonable

**Validation:**
- Print quality metrics
- Verify no CRITICAL alerts
- Store metrics for documentation

---

## Phase 3: Calibration Using Actual Pipeline

### Step 3.1: Identify Calibrator Fields
**Tool:** `dsa110_contimg.calibration.selection.select_bandpass_from_catalog()`  
**Environment:** `casa6` conda environment  
**Action:**
```python
from dsa110_contimg.calibration.selection import select_bandpass_from_catalog

ms_path = "/scratch/dsa110-contimg/ms/0834_transit/<ms_name>.ms"
catalog_path = "/data/dsa110-contimg/data-samples/catalogs/vla_calibrators_parsed.csv"

field_name, field_ids, pb_gains, cal_info = select_bandpass_from_catalog(
    ms_path=ms_path,
    catalog_path=catalog_path,
    search_radius_deg=1.0,
    freq_GHz=1.4,
    window=3,
    min_pb=0.5
)
```

**Success Criteria:**
- ✓ Calibrator field identified (should be 0834+555)
- ✓ Field IDs found
- ✓ Primary beam gains reasonable (>0.5)

**Validation:**
- Print field name and IDs
- Verify calibrator is 0834+555
- Store field information for calibration

---

### Step 3.2: Run Calibration Pipeline
**Tool:** `dsa110_contimg.calibration.cli`  
**Environment:** `casa6` conda environment  

**Note:** Run each stage separately (K, BP, G) using `--skip-*` flags to isolate issues.

**Action (K-calibration only):**
```bash
export PYTHONPATH=/data/dsa110-contimg/src

# First ensure MODEL_DATA is populated
# (Use write_point_model_with_ft if needed)

# Then run K-calibration only (with performance optimizations)
conda run -n casa6 python3 -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/0834_transit/<ms_name>.ms \
    --field "$field_id" \
    --refant 103 \
    --skip-bp --skip-g \
    --model-source catalog \
    --fast --uvrange '>1klambda' \
    --combine-spw
```

**Parameters:**
- `--ms`: MS file path from Phase 2
- `--field`: Field ID from Step 3.1 (e.g., "0")
- `--refant`: Reference antenna (103 is standard)
- `--skip-bp --skip-g`: Only run K-calibration
- `--model-source catalog`: Required flag (MODEL_DATA must already be populated)

**Expected Performance:**
- K-calibration (default, 16 SPWs sequential): >15 minutes (too slow)
- K-calibration with `--combine-spw --fast --uvrange '>1klambda'`: 3-5 minutes (optimized, 5-10x faster)
- **Issue Resolved (2025-11-03)**: Performance optimizations implemented:
  - **Added `--combine-spw` flag**: Combines SPWs during solve (one solve instead of 16)
  - Fixed flag validation bottlenecks (bulk read, sampling)
  - Added `uvrange` filtering support (reduces data by 30-50%)
  - Added `minsnr` threshold (skips low-SNR baselines)
  - Skip QA validation in fast mode

**Why `--combine-spw` for K-calibration:**
- Delays are frequency-independent (instrumental cable delays, clock offsets)
- Combining SPWs is scientifically correct AND faster
- Single calibration table (simpler than parallel processing)
- No need for parallel processing (which would create 16 tables and require merging)

**Important:** K-tables solved with `--fast --uvrange` (without timebin/chanbin) CAN be applied to full MS:
  - `--fast --uvrange '>1klambda'` does NOT create subset/averaged MS (only filters by uvrange)
  - K-tables are antenna-based (not baseline-based)
  - `applycal` applies antenna delays to all baselines regardless of uv distance
  - Filtering only affects which baselines are used to SOLVE, not which get APPLIED
  - This is scientifically sound and often preferred for delay calibration
  
  ⚠️ **Note:** If `--fast --timebin` or `--fast --chanbin` is used, a subset/averaged MS is created, and K-table applicability should be verified.

**Success Criteria:**
- ✓ Calibration runs without errors
- ✓ Calibration tables created (.kcal, .bpcal, .gpcal)
- ✓ CORRECTED_DATA column populated
- ✓ Calibration tables registered in cal_registry.sqlite3

**Validation:**
```bash
# Check calibration tables exist
ls -lh /scratch/dsa110-contimg/ms/0834_transit/*.kcal
ls -lh /scratch/dsa110-contimg/ms/0834_transit/*.bpcal
ls -lh /scratch/dsa110-contimg/ms/0834_transit/*.gpcal

# Verify CORRECTED_DATA populated
python3 -c "
from casacore.tables import table
ms = '/scratch/dsa110-contimg/ms/0834_transit/<ms_name>.ms'
with table(ms, readonly=True) as tb:
    if 'CORRECTED_DATA' in tb.colnames():
        data = tb.getcol('CORRECTED_DATA')
        print(f'CORRECTED_DATA shape: {data.shape}')
        print(f'Non-zero values: {np.count_nonzero(data)}')
"
```

---

### Step 3.3: Verify Calibration Quality
**Tool:** `dsa110_contimg.qa.pipeline_quality.check_calibration_quality()`  
**Environment:** `casa6` conda environment  
**Action:**
```python
from dsa110_contimg.qa.pipeline_quality import check_calibration_quality

caltables = {
    'kcal': '/scratch/dsa110-contimg/ms/0834_transit/<ms_name>.kcal',
    'bpcal': '/scratch/dsa110-contimg/ms/0834_transit/<ms_name>.bpcal',
    'gpcal': '/scratch/dsa110-contimg/ms/0834_transit/<ms_name>.gpcal'
}
ms_path = '/scratch/dsa110-contimg/ms/0834_transit/<ms_name>.ms'

passed, metrics = check_calibration_quality(
    caltables=caltables,
    ms_path=ms_path,
    alert_on_issues=True
)
```

**Success Criteria:**
- ✓ Calibration quality checks pass
- ✓ No critical issues (failed solutions, all-zeros, etc.)
- ✓ Flagging rate < 30%
- ✓ Phase scatter reasonable (<90°)

**Validation:**
- Print calibration metrics
- Verify no CRITICAL alerts
- Store metrics for documentation

---

## Phase 4: Imaging Using Actual Pipeline

### Step 4.1: Run Imaging Pipeline
**Tool:** `dsa110_contimg.imaging.cli.image_ms()`  
**Environment:** `casa6` conda environment  
**Action:**
```bash
export PYTHONPATH=/data/dsa110-contimg/src

conda run -n casa6 python3 -m dsa110_contimg.imaging.cli image_ms \
    --ms /scratch/dsa110-contimg/ms/0834_transit/<ms_name>.ms \
    --output /scratch/dsa110-contimg/images/0834_transit/<ms_name>.image \
    --imsize 1024 \
    --cell 1.5arcsec \
    --niter 1000 \
    --pbcor \
    --stokes I \
    --nvss-min-mjy 10.0
```

**Parameters:**
- `--ms`: Calibrated MS file path
- `--output`: Output image path
- `--imsize`: Image size (1024 pixels)
- `--cell`: Pixel size (1.5 arcsec)
- `--niter`: Deconvolution iterations (1000)
- `--pbcor`: Apply primary beam correction
- `--stokes`: Stokes I (total intensity)
- `--nvss-min-mjy`: NVSS sky model seeding (10 mJy threshold)

**Success Criteria:**
- ✓ Imaging runs without errors
- ✓ Image products created (.image, .image.pbcor, .residual, .psf, .pb, .model)
- ✓ Images are readable
- ✓ Images registered in products.sqlite3

**Validation:**
```bash
# Check image products
ls -lh /scratch/dsa110-contimg/images/0834_transit/

# Verify images are readable
python3 -c "
from casacore.images import image as casaimage
img = casaimage('/scratch/dsa110-contimg/images/0834_transit/<ms_name>.image.pbcor')
data = img.getdata()
print(f'Image shape: {data.shape}')
print(f'Data range: {data.min():.3e} to {data.max():.3e}')
"
```

---

### Step 4.2: Verify Image Quality
**Tool:** `dsa110_contimg.qa.pipeline_quality.check_image_quality()`  
**Environment:** `casa6` conda environment  
**Action:**
```python
from dsa110_contimg.qa.pipeline_quality import check_image_quality

image_path = '/scratch/dsa110-contimg/images/0834_transit/<ms_name>.image.pbcor'

passed, metrics = check_image_quality(
    image_path=image_path,
    alert_on_issues=True
)
```

**Success Criteria:**
- ✓ Image quality checks pass
- ✓ Dynamic range > 5
- ✓ Peak SNR > 5
- ✓ No all-NaN or all-zero issues

**Validation:**
- Print image quality metrics
- Verify no CRITICAL alerts
- Store metrics for documentation

---

### Step 4.3: Verify Images Registered in Database
**Tool:** SQLite query  
**Action:**
```python
import sqlite3
from pathlib import Path

db_path = Path('state/products.sqlite3')
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

# Check images registered
rows = conn.execute("""
    SELECT path, type, pbcor, created_at 
    FROM images 
    WHERE path LIKE '%0834_transit%'
    ORDER BY created_at DESC
""").fetchall()

for row in rows:
    print(f"  {row['path']}: type={row['type']}, pbcor={row['pbcor']}")
```

**Success Criteria:**
- ✓ Images registered in products.sqlite3
- ✓ pbcor flag set to 1 (PB-corrected)
- ✓ Type is '5min' (5-minute tile)

---

## Phase 5: Mosaicking Using Actual Pipeline

### Step 5.1: Plan Mosaic
**Tool:** `dsa110_contimg.mosaic.cli plan`  
**Environment:** `casa6` conda environment  
**Action:**
```bash
export PYTHONPATH=/data/dsa110-contimg/src

# Get time range from transit window
transit_start_mjd=$(python3 -c "
from astropy.time import Time
t = Time('$start_time')
print(t.mjd)
")

transit_end_mjd=$(python3 -c "
from astropy.time import Time
t = Time('$end_time')
print(t.mjd)
")

conda run -n casa6 python3 -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name 0834_transit_mosaic \
    --since $transit_start_mjd \
    --until $transit_end_mjd \
    --method pbweighted
```

**Success Criteria:**
- ✓ Mosaic plan created successfully
- ✓ Plan includes tiles from 0834 transit
- ✓ All tiles are PB-corrected (pbcor=1)
- ✓ Plan shows tile count and coverage

**Validation:**
- Print mosaic plan summary
- Verify tiles are from correct time window
- Verify all tiles have PB images

---

### Step 5.2: Dry-Run Validation
**Tool:** `dsa110_contimg.mosaic.cli build --dry-run`  
**Environment:** `casa6` conda environment  
**Action:**
```bash
export PYTHONPATH=/data/dsa110-contimg/src

conda run -n casa6 python3 -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_transit_mosaic \
    --output /scratch/dsa110-contimg/mosaics/0834/mosaic_0834 \
    --dry-run
```

**Success Criteria:**
- ✓ All pre-flight checks pass
- ✓ Tile consistency validation passes
- ✓ No validation errors
- ✓ Resource estimates reasonable

**Validation:**
- Review validation output
- Verify no blocking issues
- Check resource estimates

---

### Step 5.3: Build Mosaic
**Tool:** `dsa110_contimg.mosaic.cli build`  
**Environment:** `casa6` conda environment  
**Action:**
```bash
export PYTHONPATH=/data/dsa110-contimg/src

conda run -n casa6 python3 -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name 0834_transit_mosaic \
    --output /scratch/dsa110-contimg/mosaics/0834/mosaic_0834
```

**Success Criteria:**
- ✓ Mosaic builds successfully
- ✓ Output image exists and is readable
- ✓ Post-mosaic validation passes
- ✓ Metrics generated

**Validation:**
```bash
# Check mosaic exists
ls -lh /scratch/dsa110-contimg/mosaics/0834/mosaic_0834.image

# Verify mosaic is readable
python3 -c "
from casacore.images import image as casaimage
img = casaimage('/scratch/dsa110-contimg/mosaics/0834/mosaic_0834.image')
data = img.getdata()
print(f'Mosaic shape: {data.shape}')
"
```

---

### Step 5.4: Post-Mosaic Validation
**Tool:** `dsa110_contimg.mosaic.post_validation.validate_mosaic_quality()`  
**Environment:** `casa6` conda environment  
**Action:**
```python
from dsa110_contimg.mosaic.post_validation import validate_mosaic_quality

mosaic_path = '/scratch/dsa110-contimg/mosaics/0834/mosaic_0834.image'

valid, issues, metrics = validate_mosaic_quality(
    mosaic_path=mosaic_path,
    max_rms_variation=2.0,
    min_coverage_fraction=0.1,
    check_discontinuities=True,
    check_artifacts=True
)
```

**Success Criteria:**
- ✓ Post-mosaic validation passes
- ✓ Coverage > 10%
- ✓ RMS variation < 2.0
- ✓ No obvious artifacts

**Validation:**
- Print validation results
- Print mosaic metrics
- Store results for documentation

---

## Phase 6: Documentation and Verification

### Step 6.1: Document Results
**Action:**
- Record all transit times calculated
- Document MS files created
- Document calibration tables applied
- Document images created
- Document mosaic quality metrics

### Step 6.2: Verify End-to-End Workflow
**Checklist:**
- [ ] Proper transit calculation used (`previous_transits()`)
- [ ] Actual pipeline CLI used (`hdf5_orchestrator`)
- [ ] Actual calibration CLI used (`calibration.cli`)
- [ ] Actual imaging CLI used (`imaging.cli`)
- [ ] Actual mosaic CLI used (`mosaic.cli`)
- [ ] All components tested are production components
- [ ] No shortcuts or assumptions made

---

## Success Criteria Summary

**Phase 1:** Transit time calculated using `previous_transits()`  
**Phase 2:** MS files created using `hdf5_orchestrator` CLI  
**Phase 3:** Calibration applied using `calibration.cli`  
**Phase 4:** Images created using `imaging.cli`  
**Phase 5:** Mosaic built using `mosaic.cli`  
**Phase 6:** All results documented and verified

**Overall:** Complete end-to-end test using actual pipeline components that will run in streaming.

---

## Environment Setup

**Required Environment Variables:**
```bash
export PYTHONPATH=/data/dsa110-contimg/src
export HDF5_USE_FILE_LOCKING=FALSE
export OMP_NUM_THREADS=4
export MKL_NUM_THREADS=4
```

**Required Conda Environment:**
- `casa6` environment (Python 3.11)
- Contains: casatasks, casacore, pyuvdata, pandas, astropy

**Required Directories:**
- Input: `/data/incoming`
- Output MS: `/scratch/dsa110-contimg/ms/0834_transit`
- Output Images: `/scratch/dsa110-contimg/images/0834_transit`
- Output Mosaic: `/scratch/dsa110-contimg/mosaics/0834/`

---

## Error Handling

**At Each Step:**
1. Check for errors in output/logs
2. Verify success criteria met
3. If error occurs:
   - Document error details
   - Check pre-conditions
   - Verify tool availability
   - Fix issue before proceeding

**Common Issues:**
- Missing dependencies → Check conda environment
- Import errors → Verify PYTHONPATH
- File not found → Verify paths exist
- Permission errors → Check file permissions
- Disk space → Check available space

---

## Notes

- **No shortcuts:** Every step uses actual pipeline components
- **No assumptions:** All calculations use proper methods
- **Proper tools:** All tools are production components
- **Verification:** Each step validated before proceeding
- **Documentation:** All results recorded for review

