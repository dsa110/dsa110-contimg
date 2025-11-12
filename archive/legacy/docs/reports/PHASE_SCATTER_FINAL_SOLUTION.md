# Most Efficient Path to Fix 100.1° Phase Scatter - FINAL SOLUTION

**Date:** 2025-11-05  
**Priority:** CRITICAL - Root cause identified  
**Status:** Solution Path Identified

---

## Root Cause Identified

**Diagnostic Results:**
1. ✓ Phase centers are correctly aligned (all 24 fields within 0.00 arcmin)
2. ✗ MODEL_DATA phase scatter: **102.60°** (expected < 10°)
3. ✗ DATA vs MODEL_DATA phase difference: **145.49°** (expected < 20°)
4. ✗ Amplitude ratio (DATA/MODEL): **0.0227** (expected ~0.5-1.0)

**Potential Root Cause:** `use_manual=False` in calibration CLI (line 1695) causes `ft()` to be used instead of manual calculation.

**CASA Documentation Verification (Official CASA Docs via Ref MCP Tool):**
- ✓ **OFFICIALLY CONFIRMED:** Function signature: `ft(vis, field='', spw='', model='', nterms=1, reffreq='', complist='', incremental=False, usescratch=False)`
- ✓ **OFFICIALLY CONFIRMED:** **NO `phasecenter` parameter exists** in the official CASA documentation
- ✓ **CONFIRMED (Perplexity):** "The CASA task **ft** does **not** have a direct **phasecenter** parameter"
- ✓ **CONFIRMED:** Recommended workflow is to use `phaseshift` first, then `ft()` (we already do this)
- ✓ **Previous Investigation:** Tests showed `ft()` doesn't use `REFERENCE_DIR` or `PHASE_DIR` correctly after rephasing

**Conclusion:** We cannot fix `ft()` by passing a `phasecenter` parameter because it doesn't exist. Manual calculation is the correct solution.

**Code Location:** `src/dsa110_contimg/calibration/cli.py` line 1695

---

## Most Efficient Solution Path

### Step 1: Fix Code (COMPLETED - 2 minutes)

**Action:** Change `use_manual=False` to `use_manual=True` in calibration CLI

**File:** `src/dsa110_contimg/calibration/cli.py` line 1695

**Change:**
```python
# Before:
use_manual=False  # Uses ft() which doesn't support phasecenter parameter

# After:
use_manual=True   # Uses manual calculation with correct PHASE_DIR per field
```

**Status:** ✓ **COMPLETED** - Code updated to use manual calculation

**Why This is Correct:**
- CASA documentation confirms `ft()` does NOT have a `phasecenter` parameter
- We cannot fix `ft()` by passing explicit phase center
- Manual calculation is the correct solution (not a workaround)

---

### Step 2: Recalculate MODEL_DATA for Current MS (5 minutes)

**Action:** Recalculate MODEL_DATA using manual calculation method

**Script:**
```bash
python /data/dsa110-contimg/scripts/recalculate_model_data.py \
    /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    128.7287 55.5725 2.5
```

**Expected Results:**
- MODEL_DATA phase scatter: 102.60° → < 10°
- DATA vs MODEL_DATA phase difference: 145.49° → < 20°
- Amplitude ratio: Should improve (if DATA column is correctly phased)

---

### Step 3: Verify Fix (5 minutes)

**Action:** Re-run MODEL_DATA diagnostic to verify improvement

**Script:**
```bash
python /data/dsa110-contimg/scripts/check_model_data_phase.py \
    /scratch/dsa110-contimg/ms/2025-10-29T13:54:17.ms \
    128.7287 55.5725
```

**Expected Output:**
- MODEL_DATA phase scatter: < 10° ✓
- DATA vs MODEL_DATA phase difference: < 20° ✓
- Amplitude ratio: ~0.5-1.0 ✓

---

### Step 4: Re-run Calibration (20-30 minutes)

**Action:** Re-run pre-bandpass phase and bandpass calibration

**Expected Results:**
- Bandpass phase scatter: 100.1° → < 50° (ideally < 30°)
- Flagging rate: 44.2% → < 20%
- SNR: Should improve significantly

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

## Why This Path is Most Efficient

1. **Root Cause Fix:** Changes code to use correct MODEL_DATA calculation method
2. **Immediate Fix:** Recalculates MODEL_DATA for current MS (5 minutes)
3. **Fast Verification:** Scripts provide immediate feedback
4. **Minimal Changes:** Only one line of code changed
5. **Prevents Future Issues:** All future calibrations will use correct method

---

## Expected Outcome

After fixes:
- ✅ MODEL_DATA phase scatter: 102.60° → < 10°
- ✅ DATA vs MODEL_DATA aligned: 145.49° → < 20°
- ✅ Bandpass phase scatter: 100.1° → < 50° (ideally < 30°)
- ✅ Flagging rate: 44.2% → < 20%
- ✅ SNR: Improves significantly

**Total Time:** 30-40 minutes  
**Complexity:** Low (one code change + data recalculation)  
**Risk:** Low (can verify after each step)

---

## Summary

**Root Cause:** `use_manual=False` causes `ft()` to be used, which has phase center issues.

**Solution:**
1. Change `use_manual=False` → `use_manual=True` (code fix - DONE)
2. Recalculate MODEL_DATA for current MS (5 minutes)
3. Re-run calibration (20-30 minutes)

**This is the most efficient path because:**
- Fixes the root cause (code bug)
- Immediate fix for current MS
- Prevents future issues
- Minimal changes required

