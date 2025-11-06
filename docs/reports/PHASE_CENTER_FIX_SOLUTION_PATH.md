# Most Efficient Path to Fix 100.1° Phase Scatter

**Date:** 2025-11-05  
**Priority:** CRITICAL - Root cause of 100.1° phase scatter  
**Status:** Updated Based on Diagnostic Results

---

## IMPORTANT UPDATE: Phase Centers Are Correctly Aligned

**Diagnostic Results:** All 24 fields have phase centers correctly aligned (within 0.00 arcmin of calibrator)

**Implication:** Phase center incoherence is **NOT** the root cause of 100.1° phase scatter.

**New Root Cause Hypothesis:** The scatter is likely due to:
1. MODEL_DATA phase structure issues (even with correct phase centers)
2. UVW/DATA transformation issues (DATA column may not be correctly phased)
3. Frequency-dependent phase variation (normal, but larger than typical)
4. Antenna-to-antenna variations (normal, but larger than typical)

---

## Most Efficient Solution Path (UPDATED)

### Step 1: Verify MODEL_DATA Phase Structure (10 minutes)

**Action:** Check MODEL_DATA phase scatter and DATA vs MODEL_DATA alignment

**Script:**
```bash
python /data/dsa110-contimg/scripts/check_model_data_phase.py \
    /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    128.7287 55.5725
```

**Expected Output:**
- MODEL_DATA phase scatter: < 10° (acceptable)
- DATA vs MODEL_DATA phase difference scatter: < 20° (aligned)

**If MODEL_DATA scatter > 10°:** Proceed to Step 2

---

### Step 2: Verify DATA Column Phasing (10 minutes)

**Action:** Check if DATA column is correctly phased despite correct FIELD table metadata

**Action:** Sample DATA column and check phase structure

**Verification:**
- Check if DATA column phase structure matches expected for calibrator at phase center
- Verify UVW coordinates are correctly transformed
- Check if DATA vs MODEL_DATA phase difference is reasonable

**If DATA column is NOT correctly phased:** Proceed to Step 3

---

### Step 3: Re-run phaseshift (if needed) (15-30 minutes)

**Action:** Check if UVW coordinates and DATA column are correctly phased

**Key Question:** Are UVW coordinates and DATA column phased to calibrator position, or still phased to original meridian?

**Verification:**
```python
from casacore.tables import table
import numpy as np

ms_path = "/scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms"

# Sample UVW coordinates
with table(ms_path, readonly=True) as tb:
    n_sample = min(1000, tb.nrows())
    uvw = tb.getcol("UVW", startrow=0, nrow=n_sample)
    field_id = tb.getcol("FIELD_ID", startrow=0, nrow=n_sample)
    
    # Check UVW for different fields
    unique_fields = np.unique(field_id)
    print(f"Sample UVW coordinates by field:")
    for field_idx in unique_fields[:5]:  # Check first 5 fields
        field_mask = field_id == field_idx
        field_uvw = uvw[field_mask]
        print(f"Field {field_idx}: u_range=[{field_uvw[:, 0].min():.2f}, {field_uvw[:, 0].max():.2f}] m")
```

**If UVW/DATA are NOT correctly phased:** Run `phaseshift` again (Step 4)

**If UVW/DATA ARE correctly phased:** Skip to Step 5

---

**Action:** Re-run `phaseshift` ONLY if DATA column is not correctly phased

**Code Location:** `src/dsa110_contimg/calibration/cli.py` function `_rephase_ms_to_calibrator()`

**Method:** Call calibration CLI with `--rephase` flag, or manually run:

```python
from casatasks import phaseshift
from astropy.coordinates import Angle

ms_path = "/scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms"
ms_phased = ms_path + ".rephased"

cal_ra_deg = 128.7287
cal_dec_deg = 55.5725

ra_hms = Angle(cal_ra_deg, unit='deg').to_string(unit='hour', precision=2)
dec_dms = Angle(cal_dec_deg, unit='deg').to_string(unit='deg', precision=2)
phasecenter_str = f"J2000 {ra_hms} {dec_dms}"

phaseshift(
    vis=ms_path,
    outputvis=ms_phased,
    phasecenter=phasecenter_str
)

# Then update REFERENCE_DIR for all fields (as in Step 2)
# Then replace original MS with rephased version
```

**After phaseshift:** Verify phase centers again (Step 1)

---

### Step 4: Recalculate MODEL_DATA (if needed) (5 minutes)

**Action:** Clear old MODEL_DATA and recalculate using manual method

**Code Location:** `src/dsa110_contimg/calibration/model.py` function `_calculate_manual_model_data()`

**Method:** Call calibration CLI with MODEL_DATA population step, or manually:

```python
from dsa110_contimg.calibration.model import _calculate_manual_model_data

ms_path = "/scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms"
cal_ra_deg = 128.7287
cal_dec_deg = 55.5725
flux_jy = 2.5  # From calibrator catalog

# Clear old MODEL_DATA first
from casacore.tables import table
import numpy as np
with table(ms_path, readonly=False) as tb:
    if "MODEL_DATA" in tb.colnames():
        zeros = np.zeros(tb.getcol("MODEL_DATA").shape, dtype=np.complex64)
        tb.putcol("MODEL_DATA", zeros)

# Recalculate MODEL_DATA for all fields
_calculate_manual_model_data(ms_path, cal_ra_deg, cal_dec_deg, flux_jy, field=None)
```

**Verify:** Check MODEL_DATA phase scatter should be < 10° for point source at phase center

---

### Step 5: Re-run Calibration (20-30 minutes)

**Action:** Re-run pre-bandpass phase and bandpass calibration

**Expected Results:**
- Phase scatter should drop from 100.1° to < 50° (ideally < 30°)
- Flagging rate should drop from 44.2% to < 20%
- SNR should improve significantly

**Command:**
```bash
python /scratch/dsa110-contimg/run_calibration_steps.py prebp-phase \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --refant 103 \
    --combine-fields \
    --combine-spw

python /scratch/dsa110-contimg/run_calibration_steps.py bandpass \
    --ms /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    --field 0 \
    --refant 103 \
    --combine-fields \
    --combine-spw \
    --prebp-phase-cal /scratch/dsa110-contimg/ms/2025-10-29T13:54:17_0~23_prebp_phase
```

---

## Most Efficient Path (UPDATED)

**Step 1: Check MODEL_DATA phase scatter** (10 min)
- Run `scripts/check_model_data_phase.py`
- If MODEL_DATA scatter > 10° → investigate MODEL_DATA calculation

**Step 2: Check DATA column phasing** (10 min)
- Verify DATA vs MODEL_DATA alignment
- If misaligned → DATA column not correctly phased

**Step 3: Re-run phaseshift (if needed)** (15-30 min)
- Only if DATA column is not correctly phased
- Re-transform UVW coordinates and DATA column

**Step 4: Recalculate MODEL_DATA (if needed)** (5 min)
- Only if MODEL_DATA scatter is high
- Use manual calculation method

**Step 5: Re-run calibration** (20-30 min)
- Re-run pre-bandpass phase and bandpass calibration
- Expected: phase scatter should improve

**Time Estimate:** 30-60 minutes total (if fixes needed)

---

## Why This Path is Most Efficient

1. **Root Cause Focus:** Phase centers are correct, so focus on MODEL_DATA/DATA alignment
2. **Minimal Changes:** Only verify and fix if needed
3. **Fast Verification:** Each step has clear verification criteria
4. **Immediate Feedback:** Can verify improvement after each step
5. **No Code Changes Required:** Uses existing tools and functions

---

## Expected Outcome

After verification and fixes (if needed):
- ✅ MODEL_DATA phase scatter < 10° (if currently high)
- ✅ DATA vs MODEL_DATA aligned (phase difference scatter < 20°)
- ✅ Bandpass phase scatter drops from 100.1° to < 50° (ideally < 30°)
- ✅ Flagging rate drops from 44.2% to < 20%
- ✅ SNR improves significantly

**Total Time:** 30-60 minutes (if fixes needed)  
**Complexity:** Low (mostly verification)  
**Risk:** Low (can verify after each step)

---

## Alternative Hypothesis: Frequency-Dependent Scatter is Normal

**If MODEL_DATA and DATA are both correct**, the 100.1° scatter may be:
- Primarily frequency-dependent (normal for bandpass across 48 channels)
- Antenna-to-antenna variations (normal for 117 antennas)
- Combined effect of both (expected for this array configuration)

**Action:** Compare with other observations to determine if 100.1° is acceptable for DSA-110 array

