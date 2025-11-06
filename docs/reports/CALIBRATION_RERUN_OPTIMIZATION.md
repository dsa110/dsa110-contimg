# Calibration Re-run Optimization Guide

**Date:** 2025-11-05  
**Context:** After fixing `spwmap` issue for `--combine-spw` bandpass tables

---

## Summary

Since the **bandpass calibration failed** for SPWs 1-15 in the previous run (due to missing `spwmap`), you **MUST re-run**:
- ✅ **Bandpass calibration** (this is what failed - now fixed with `spwmap`)
- ✅ **Gain calibration** (depends on bandpass, so must re-run)

However, you can potentially **skip** some steps if they're already done correctly:

---

## Can Skip (with caution)

### 1. Flagging (`--no-flagging`)
**If:** Flags from previous run are correct and you trust them
```bash
--no-flagging
```
**Note:** This also skips `initweights` after flagging. If flags haven't changed, this is safe.

### 2. Rephasing
**If:** MS is already phased to the calibrator position (within 1 arcmin)
- The code checks automatically and skips if already phased
- No flag needed - happens automatically

### 3. MODEL_DATA Population
**If:** MODEL_DATA is already populated correctly for the calibrator
- **Risk:** If MODEL_DATA was written for wrong phase center, calibration will fail
- **Recommendation:** Let the code re-populate it (it's fast, ~1-2 minutes)

---

## Must Re-run (Critical)

### 1. Bandpass Calibration
**Why:** Previous run failed for SPWs 1-15 due to missing `spwmap`
**Fix:** Now automatically detects and applies `spwmap=[0]*16` when `combine_spw=True`
**Action:** Run with `--combine-spw` (or without if you prefer separate SPW solves)

### 2. Gain Calibration
**Why:** Depends on bandpass table, which was incomplete
**Action:** Will run automatically after bandpass succeeds

---

## Recommended Approach

### Option 1: Minimal Re-run (Fastest)
Skip flagging if you're confident it's correct:
```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /data/ms/2025-10-29T13:54:17.ms \
  --field 0 --refant 103 \
  --auto-fields --model-source catalog \
  --combine-spw \
  --no-flagging  # Skip flagging (reuse from previous run)
```

**Pros:** Fastest (~10-15 minutes vs 30-45 minutes)
**Cons:** Risk if flags were incorrect or if data changed

### Option 2: Safe Re-run (Recommended)
Re-run everything except MODEL_DATA if already correct:
```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /data/ms/2025-10-29T13:54:17.ms \
  --field 0 --refant 103 \
  --auto-fields --model-source catalog \
  --combine-spw
  # Let MODEL_DATA re-populate (checks if already phased correctly)
```

**Pros:** Safe, ensures all steps are correct
**Cons:** Slightly slower (~30-45 minutes total)

### Option 3: Full Re-run (Safest)
Re-run everything from scratch:
```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms /data/ms/2025-10-29T13:54:17.ms \
  --field 0 --refant 103 \
  --auto-fields --model-source catalog \
  --combine-spw
  # Full re-run (flagging, rephasing, MODEL_DATA, bandpass, gain)
```

**Pros:** Safest, ensures everything is correct
**Cons:** Slowest (~45-60 minutes)

---

## What Changed in the Fix

The fix automatically detects when a bandpass table has only 1 SPW (from `combine_spw`) and sets `spwmap=[0,0,0,...,0]` to map all MS SPWs to SPW 0 in the bandpass table.

**Previous behavior:**
- Bandpass solve: ✅ Creates table with SPW=0 only
- Gain solve: ❌ Fails for SPWs 1-15 (no `spwmap`)

**New behavior:**
- Bandpass solve: ✅ Creates table with SPW=0 only
- Gain solve: ✅ Automatically applies `spwmap=[0]*16` → All SPWs succeed

---

## Verification

After re-running, verify all SPWs have solutions:
```bash
# Check bandpass table
listcal(vis='/data/ms/2025-10-29T13:54:17_0_bpcal')

# Check gain tables
listcal(vis='/data/ms/2025-10-29T13:54:17_0_gpcal')
```

**Expected:** All SPWs (0-15) should show `[1, 1]` (solutions exist) instead of `[0, 0]` (no solutions).

---

## Time Estimates

| Step | Time (min) | Can Skip? |
|------|------------|-----------|
| Flagging | 2-5 | ✅ Yes (if already correct) |
| Rephasing | 1-3 | ✅ Auto-skip if already phased |
| MODEL_DATA | 1-2 | ✅ Yes (if already correct) |
| **Bandpass** | **15-30** | ❌ **NO - Must re-run** |
| **Gain** | **5-10** | ❌ **NO - Must re-run** |
| **Total** | **~25-50** | |

---

## Recommendation

**Use Option 2 (Safe Re-run):** Let the code re-run flagging, rephasing, and MODEL_DATA (it's fast and ensures correctness), then re-run bandpass and gain with the fix. This gives you the best balance of safety and speed.

