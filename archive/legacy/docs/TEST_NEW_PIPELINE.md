# Testing the New Pipeline Framework

This guide explains how to test the new pipeline framework with `USE_NEW_PIPELINE=true`.

## Quick Start

1. **Set the environment variable:**
   ```bash
   export USE_NEW_PIPELINE=true
   ```

2. **Run the test script:**
   ```bash
   cd /data/dsa110-contimg
   source /opt/miniforge/etc/profile.d/conda.sh
   conda activate casa6
   export PYTHONPATH=/data/dsa110-contimg/src:$PYTHONPATH
   
   python scripts/test_new_pipeline_e2e.py \
       --input-dir /data/incoming \
       --output-dir /scratch/test-pipeline \
       --start-time 2025-01-15T10:00:00 \
       --end-time 2025-01-15T10:05:00
   ```

## What Gets Tested

The end-to-end test runs the full pipeline workflow:

1. **Conversion Stage**: UVH5 → MS
   - Discovers subband groups in the time window
   - Converts to CASA Measurement Sets
   - Updates MS index in products database

2. **Calibration Stage**: Apply calibration tables
   - Looks up active calibration tables from registry
   - Applies calibration using `applycal`
   - Verifies CORRECTED_DATA is populated
   - Updates MS index with `cal_applied` flag

3. **Imaging Stage**: Create images
   - Runs imaging on the calibrated MS
   - Creates image products (image, pbcor, residual, psf, pb)
   - Updates MS index with imagename

## Prerequisites

- **Input data**: UVH5 files in the input directory for the specified time range
- **Calibration registry**: Optional - if not present, calibration stage will skip gracefully
- **Output directory**: Must be writable
- **Products database**: Will be created if it doesn't exist

## Test Script Options

```bash
python scripts/test_new_pipeline_e2e.py --help
```

Key options:
- `--input-dir`: Directory containing UVH5 files
- `--output-dir`: Output directory for MS and images
- `--start-time`: Start time (ISO format)
- `--end-time`: End time (ISO format)
- `--products-db`: Products database path (default: `state/products.sqlite3`)
- `--writer`: Writer strategy (default: `auto`)
- `--max-workers`: Maximum workers (default: 4)

## Expected Output

On success, you should see:
- Job created in database
- Conversion stage completes (MS files created)
- Calibration stage completes (if calibration tables available)
- Imaging stage completes (image products created)
- Job status: `done`
- Artifacts list with MS and image paths

## Troubleshooting

### "No calibration tables available"
- This is expected if no calibration registry exists
- The pipeline will continue without calibration
- Images will be created from DATA column instead of CORRECTED_DATA

### "Conversion produced no MS files"
- Check that input directory contains UVH5 files for the time range
- Verify time format is correct (ISO format: `YYYY-MM-DDTHH:MM:SS`)

### "MS file not found"
- Check that conversion stage completed successfully
- Verify output directory is writable

## Comparing with Legacy Pipeline

To compare with the legacy pipeline:

1. **Test with legacy (default):**
   ```bash
   unset USE_NEW_PIPELINE
   # or
   export USE_NEW_PIPELINE=false
   python scripts/test_new_pipeline_e2e.py ...
   ```

2. **Test with new framework:**
   ```bash
   export USE_NEW_PIPELINE=true
   python scripts/test_new_pipeline_e2e.py ...
   ```

Both should produce the same results, but the new framework provides:
- Better error handling and retry logic
- Structured logging and observability
- Dependency-based execution
- Immutable context passing

## Next Steps

After successful testing:
1. Monitor job logs in the database
2. Verify image quality
3. Compare performance with legacy pipeline
4. Gradually migrate production workflows

