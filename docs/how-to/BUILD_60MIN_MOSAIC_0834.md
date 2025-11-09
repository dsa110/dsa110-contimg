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

