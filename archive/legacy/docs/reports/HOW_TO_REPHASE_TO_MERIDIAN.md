# How to Rephase MS Back to Meridian

**Date:** 2025-11-05  
**Purpose:** Guide for rephasing an MS that has been rephased to calibrator position back to meridian phase center

---

## Overview

If your MS has already been rephased to the calibrator position, and you want to use the `--skip-rephase` workflow, you need to rephase it **back to the meridian** first.

---

## Prerequisites

1. **MS file** that has been rephased to calibrator position
2. **UVH5 file** (recommended) - provides accurate pointing declination
   - If UVH5 not available, script will attempt to infer from MS

---

## Usage

### Basic Usage (with UVH5)

```bash
python /data/dsa110-contimg/scripts/rephase_to_meridian.py \
    /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    /scratch/dsa110-contimg/uvh5/2025-10-29T13:54:17.uvh5
```

### Without UVH5 (uses MS metadata)

```bash
python /data/dsa110-contimg/scripts/rephase_to_meridian.py \
    /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms
```

**Warning:** Without UVH5, the script uses the first field's declination, which may be the calibrator declination (not pointing declination). This will produce incorrect meridian coordinates.

---

## What the Script Does

1. **Gets midpoint time** from MS (MJD)
2. **Gets pointing declination** from UVH5 (or MS if UVH5 not available)
3. **Calculates meridian coordinates** using `get_meridian_coords()`:
   - RA = LST at midpoint (meridian)
   - Dec = pointing declination
4. **Rephases MS** using `phaseshift` to meridian coordinates
5. **Updates REFERENCE_DIR** to match PHASE_DIR
6. **Verifies** phase center alignment

---

## Output

The script creates a new MS file with `.meridian.ms` suffix:

```
/scratch/dsa110-contimg/ms/2025-10-29T13:54:17.meridian.ms
```

**Original MS is not modified** - the script creates a new file.

---

## After Rephasing

Once you have the meridian-phased MS, you can use `--skip-rephase`:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.meridian.ms \
    --field 0 \
    --refant 106 \
    --skip-rephase \
    --prebp-phase \
    --prebp-solint 30s \
    --prebp-minsnr 2.0 \
    --prebp-minblperant 4 \
    --prebp-spw 4~11 \
    --prebp-table-name .bpphase.gcal \
    --bp-combine "scan,obs,field"
```

---

## Alternative: Use Default Workflow

**Instead of rephasing back to meridian**, you can use the default workflow with `use_manual=True`:

```bash
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --refant 106 \
    # (no --skip-rephase - uses default workflow)
```

This keeps DATA phased to calibrator and calculates MODEL_DATA manually with correct phase center.

---

## Key Points

1. **Meridian coordinates** = RA (LST at midpoint), Dec (pointing declination)
2. **Original MS is not modified** - new file is created
3. **UVH5 file is recommended** for accurate pointing declination
4. **After rephasing to meridian**, `ft()` will work correctly with `--skip-rephase`
5. **Alternative approach**: Use default workflow with manual MODEL_DATA calculation (no rephasing needed)

---

## Troubleshooting

### "Could not get pointing declination"

**Solution:** Provide UVH5 file path, or verify MS has REFERENCE_DIR or PHASE_DIR columns.

### "Phase center still offset by > 1 arcmin"

**Solution:** Check that pointing declination is correct. If using MS metadata, it may be calibrator declination (wrong).

### "Output MS already exists"

**Solution:** Script will ask if you want to delete and recreate. Answer 'y' to proceed.

---

## See Also

- `IS_IT_SAFE_TO_SKIP_REPHASE.md` - How to check if MS is safe to use with `--skip-rephase`
- `NO_REPHASE_WORKFLOW.md` - Documentation of the `--skip-rephase` workflow

