# Steps to Produce a 5-Minute Image of 0834+555 Transit

**Objective:** Create a calibrated continuum image from a 5-minute observation containing a transit of the VLA calibrator 0834+555.

**Prerequisites:**
- UVH5 subband files available in `/data/incoming` (or your input directory)
- `casa6` conda environment activated
- Pipeline environment variables configured (if using custom paths)

---

## Step 1: Find and Convert Calibrator Transit Data

### Option A: Using Orchestrator CLI (Recommended)

The orchestrator CLI automatically finds the transit time and converts the matching 5-minute group:

```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --writer parallel-subband \
    --stage-to-tmpfs
```

**What this does:**
- Finds the most recent transit of 0834+555
- Locates the 5-minute group containing that transit time
- Verifies all 16 subband files exist
- Converts UVH5 → MS using the production writer
- Outputs MS to `/stage/dsa110-contimg/ms/<group_id>.ms`

**For a specific date:**
```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30 \
    --writer parallel-subband \
    --stage-to-tmpfs
```

### Option B: Using Unified Conversion CLI

```bash
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --writer parallel-subband \
    --stage-to-tmpfs
```

**Expected output:**
- MS file path: `/stage/dsa110-contimg/ms/2025-10-30T13:34:54.ms` (example)
- Group ID corresponds to the 5-minute window containing the transit

---

## Step 2: Calibrate the Measurement Set (Recommended)

Calibration improves image quality by correcting for frequency-dependent bandpass and time-variable gains.

### Option A: Quick Calibration (Development Tier)

For a quick 5-minute image, use development quality tier:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /stage/dsa110-contimg/ms/2025-10-30T13:34:54.ms \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --fast \
    --timebin 30s \
    --chanbin 4 \
    --uvrange '>1klambda' \
    --prebp-phase \
    --prebp-minsnr 3.0 \
    --prebp-solint 30s
```

**What this does:**
- Performs bandpass (BP) and gain (G) calibration
- Uses development quality tier with time/channel binning
- ⚠️  Creates **NON_SCIENCE_DEVELOPMENT** prefixed calibration tables
- Skips K-calibration (delay) by default (appropriate for DSA-110 short baselines)
- **These tables CANNOT be applied to production data** due to binning mismatches

### Option B: Standard Calibration

For higher quality (slower):

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /stage/dsa110-contimg/ms/2025-10-30T13:34:54.ms \
    --field 0 \
    --refant 103 \
    --auto-fields
```

**Calibration tables created:**
- `/stage/dsa110-contimg/ms/2025-10-30T13:34:54.ms.bpcal`
- `/stage/dsa110-contimg/ms/2025-10-30T13:34:54.ms.gpcal`

**Note:** If calibration tables already exist from a previous calibration run, you can skip this step if you're satisfied with the existing calibration.

### Detailed Calibration Procedure

For a comprehensive explanation of what happens during calibration, see:
- **Complete calibration guide**: `docs/howto/CALIBRATION_DETAILED_PROCEDURE.md`

---

## Step 3: Image the Measurement Set

Create a quick-look image optimized for speed:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /stage/dsa110-contimg/ms/2025-10-30T13:34:54.ms \
    --imagename /stage/dsa110-contimg/images/0834_transit_5min \
    --quick \
    --imsize 512 \
    --niter 300 \
    --threshold 0.1mJy \
    --pbcor
```

**Parameters explained:**
- `--quality-tier development`: Enables development tier (reduces `imsize` and `niter` automatically)
- `--imsize 512`: Image size in pixels (512×512 for quick look)
- `--niter 300`: Maximum iterations (quick mode)
- `--threshold 0.1mJy`: Stopping threshold
- `--pbcor`: Apply primary beam correction

**Alternative: Quick Script**

```bash
scripts/image_ms.sh \
    /stage/dsa110-contimg/ms/2025-10-30T13:34:54.ms \
    /stage/dsa110-contimg/images/0834_transit_5min \
    --quick \
    --skip-fits \
    --uvrange '>1klambda'
```

---

## Step 4: Verify Output

**Image files created:**
- `/stage/dsa110-contimg/images/0834_transit_5min.image/` - Cleaned image
- `/stage/dsa110-contimg/images/0834_transit_5min.pbcor/` - Primary beam corrected image
- `/stage/dsa110-contimg/images/0834_transit_5min.pbcor.fits` - FITS export (if not skipped)

**Check image quality:**
```bash
# View image statistics
python -m dsa110_contimg.qa.image_quality \
    /stage/dsa110-contimg/images/0834_transit_5min.pbcor.fits
```

---

## Complete Workflow Example

Here's a complete end-to-end example:

```bash
# 1. Find and convert transit data
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    --calibrator 0834+555 \
    --transit-date 2025-10-30 \
    --writer parallel-subband \
    --stage-to-tmpfs

# Note the MS path from output (e.g., /stage/dsa110-contimg/ms/2025-10-30T13:34:54.ms)
MS_PATH="/stage/dsa110-contimg/ms/2025-10-30T13:34:54.ms"

# 2. Calibrate (development tier)
python -m dsa110_contimg.calibration.cli calibrate \
    --ms "$MS_PATH" \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --preset development

# 3. Image (development tier)
python -m dsa110_contimg.imaging.cli image \
    --ms "$MS_PATH" \
    --imagename /stage/dsa110-contimg/images/0834_transit_5min \
    --quality-tier development \
    --imsize 512 \
    --niter 300 \
    --threshold 0.1mJy \
    --pbcor
```

---

## Alternative: All-in-One Script

For convenience, you can use a script that combines these steps:

```bash
#!/bin/bash
# Quick 5-minute image of 0834+555 transit

INPUT_DIR="/data/incoming"
OUTPUT_MS_DIR="/stage/dsa110-contimg/ms"
OUTPUT_IMAGE_DIR="/stage/dsa110-contimg/images"
TRANSIT_DATE="${1:-$(date +%Y-%m-%d)}"  # Use today if not specified

# Step 1: Convert
echo "Step 1: Finding and converting transit data..."
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    "$INPUT_DIR" \
    "$OUTPUT_MS_DIR" \
    --calibrator 0834+555 \
    --transit-date "$TRANSIT_DATE" \
    --writer parallel-subband \
    --stage-to-tmpfs

# Find the MS file (most recent in output directory)
MS_PATH=$(ls -t "$OUTPUT_MS_DIR"/*.ms | head -1)
echo "Using MS: $MS_PATH"

# Step 2: Calibrate
echo "Step 2: Calibrating..."
python -m dsa110_contimg.calibration.cli calibrate \
    --ms "$MS_PATH" \
    --field 0 \
    --refant 103 \
    --auto-fields \
    --fast \
    --timebin 30s \
    --chanbin 4

# Step 3: Image
echo "Step 3: Imaging..."
GROUP_ID=$(basename "$MS_PATH" .ms)
python -m dsa110_contimg.imaging.cli image \
    --ms "$MS_PATH" \
    --imagename "$OUTPUT_IMAGE_DIR/${GROUP_ID}_0834" \
    --quick \
    --imsize 512 \
    --niter 300 \
    --threshold 0.1mJy \
    --pbcor

echo "Complete! Image: $OUTPUT_IMAGE_DIR/${GROUP_ID}_0834.pbcor.fits"
```

---

## Notes

1. **Calibration is optional** but recommended for best image quality. Uncalibrated images will use `DATA` column instead of `CORRECTED_DATA`.

2. **Quick mode** (`--quick`) reduces image size and iterations for speed. For higher quality, omit `--quick` and use larger `imsize` (e.g., 1024 or 2048).

3. **Primary beam correction** (`--pbcor`) should always be used for flux-accurate images.

4. **Reference antenna** (`--refant 103`) may need adjustment based on your array configuration. Use `--auto-refant` to select automatically.

5. **Time window**: The orchestrator automatically finds the 5-minute group containing the transit. Each group represents a ~5-minute observation window.

6. **Performance**: Using `--stage-to-tmpfs` speeds up conversion by staging files in RAM (`/dev/shm`) instead of disk.

---

## Troubleshooting

**No transit found:**
- Check that data exists: `ls /data/incoming/*_sb??.hdf5 | head -20`
- Try increasing `--max-days-back` (default: 30 days)
- Verify calibrator name: `0834+555` (not `0834+555` with different formatting)

**Calibration fails:**
- Check that MODEL_DATA is populated (needed for calibration)
- Try different reference antenna: `--auto-refant`
- Reduce UV range cut: `--uvrange ''` (no cut)

**Imaging fails:**
- Verify MS has data: `python -m dsa110_contimg.qa.ms_quality <ms_path>`
- Check disk space: `df -h /stage/dsa110-contimg`
- Reduce image size: `--imsize 256`

---

## References

- **Finding transit data**: `docs/howto/FIND_CALIBRATOR_TRANSIT_DATA.md`
- **Orchestrator CLI**: `docs/howto/USING_ORCHESTRATOR_CLI.md`
- **Calibration guide**: `docs/reference/calibration.md`
- **Imaging guide**: `docs/reference/cli.md`
- **Quick-look workflow**: `docs/quicklook.md`

