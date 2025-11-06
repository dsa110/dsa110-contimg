# Is It Safe to Use --skip-rephase?

**Date:** 2025-11-05  
**Question:** Are the phases currently locked in on the calibrator, or is it safe to use --skip-rephase?

---

## Critical Check

**If the MS has already been rephased to the calibrator position**, then using `--skip-rephase` won't help because:

1. **DATA column** is already phased to calibrator position
2. **`ft()` will use** meridian phase center (original)
3. **MODEL_DATA** will be calculated relative to meridian
4. **DATA vs MODEL_DATA** will still be misaligned!

**The MS needs to be at MERIDIAN phase center** for `--skip-rephase` to work.

---

## Diagnostic Script

Run this to check:

```bash
python /data/dsa110-contimg/scripts/check_ms_rephase_status.py \
    /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    128.7287 55.5725
```

**This will tell you:**
- Current MS phase center (meridian vs calibrator)
- Whether rephasing was done
- Whether it's safe to use `--skip-rephase`

---

## Interpretation

### If MS is at Calibrator Position (< 1 arcmin)

**NOT SAFE** to use `--skip-rephase`:
- DATA column is phased to calibrator
- `ft()` will use meridian (wrong!)
- DATA and MODEL_DATA will be misaligned
- **Options:**
  1. Use default workflow (rephasing enabled) - recommended
  2. Rephase BACK to meridian first, then use `--skip-rephase`

### If MS is at Meridian Position (> 10 arcmin from calibrator)

**SAFE** to use `--skip-rephase`:
- DATA column is phased to meridian
- `ft()` will use meridian (correct!)
- DATA and MODEL_DATA will be aligned
- Calibration should work

### If MS is Intermediate (1-10 arcmin from calibrator)

**UNCERTAIN** - check manually:
- May have been partially rephased
- Manual verification needed

---

## Rephasing Back to Meridian

If MS is already phased to calibrator but you want to use `--skip-rephase`, you need to rephase BACK to meridian first:

### Option 1: Use phaseshift to Rephase Back

```python
from casatasks import phaseshift
from casacore.tables import table
import numpy as np

# Get meridian coordinates (need to compute from observation midpoint)
# This is complex - need LST at midpoint, pointing declination

# Or use fixvis to reset REFERENCE_DIR to original
```

### Option 2: Use Original MS (Before Rephasing)

If you have a backup of the MS before rephasing, use that instead.

### Option 3: Don't Skip Rephasing

Just use the default workflow (rephasing enabled) - it's designed to work with calibrator phase center.

---

## Recommendation

**Check the MS first** using the diagnostic script. Then:

1. **If MS is at meridian:** Use `--skip-rephase` ✓
2. **If MS is at calibrator:** Use default workflow (no `--skip-rephase`) ✓
3. **If MS is intermediate:** Verify manually or use default workflow

---

## Key Point

**The workflow matters:**
- **New MS (never rephased):** Use `--skip-rephase` ✓
- **Already rephased MS:** Use default workflow (rephasing enabled) ✓

**You cannot skip rephasing on an already-rephased MS** - the DATA column is already phased to calibrator!

