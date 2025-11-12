# Edge Case Documentation: setjy Without Rephasing

**Date:** 2025-11-05  
**Status:** Documented  
**Severity:** Low (uncommon in production)

---

## **Edge Case Description**

When using `--model-source=setjy` without rephasing (`--skip-rephase`), the code still uses CASA's `ft()` function, which has known phase center bugs.

---

## **When This Occurs**

**Conditions:**
1. `--model-source=setjy` is used
2. `--skip-rephase` is used (or rephasing is not performed)
3. Explicit calibrator coordinates (`--cal-ra-deg`, `--cal-dec-deg`) are **not** provided

**Code Location:**
- `src/dsa110_contimg/calibration/cli.py:1876-1883`
- Falls back to `write_setjy_model()` which uses `ft()` internally

---

## **Impact**

**What Happens:**
- `setjy` uses `ft()` internally to populate MODEL_DATA
- `ft()` has bugs with phase center handling (doesn't use `PHASE_DIR` correctly)
- Can result in MODEL_DATA with incorrect phase structure
- Leads to high phase scatter (~100°) in calibration solutions

**Severity:** Low
- **Primary workflow uses catalog model** (not setjy)
- `setjy` without rephasing is uncommon in production
- Easy to work around (use catalog model or provide explicit coordinates)

---

## **Workarounds**

### **Option 1: Use Catalog Model (Recommended)**

```bash
# Use catalog model instead of setjy
python -m dsa110_contimg.calibration.cli calibrate \
  --ms MS.ms \
  --field 0 \
  --refant 106 \
  --model-source catalog \
  --cal-ra-deg 128.7287 \
  --cal-dec-deg 55.5725 \
  --cal-flux-jy 2.5 \
  --skip-rephase
```

**Benefits:**
- ✅ Uses manual MODEL_DATA calculation (bypasses `ft()` bug)
- ✅ Works correctly with or without rephasing
- ✅ Recommended for production

### **Option 2: Provide Explicit Coordinates**

```bash
# Use setjy but provide explicit coordinates
python -m dsa110_contimg.calibration.cli calibrate \
  --ms MS.ms \
  --field 0 \
  --refant 106 \
  --model-source setjy \
  --model-field 0 \
  --cal-ra-deg 128.7287 \
  --cal-dec-deg 55.5725 \
  --cal-flux-jy 2.5 \
  --skip-rephase
```

**Benefits:**
- ✅ Code detects explicit coordinates and uses manual calculation
- ✅ Works with `setjy` model source
- ⚠️ Requires providing coordinates manually

### **Option 3: Rephase to Calibrator**

```bash
# Rephase to calibrator (then setjy works correctly)
python -m dsa110_contimg.calibration.cli calibrate \
  --ms MS.ms \
  --field 0 \
  --refant 106 \
  --model-source setjy \
  --model-field 0 \
  --cal-ra-deg 128.7287 \
  --cal-dec-deg 55.5725
```

**Benefits:**
- ✅ Code detects rephasing and uses manual calculation
- ✅ Works with `setjy` model source
- ⚠️ Requires rephasing (adds processing time)

---

## **Code Logic**

**Current Implementation:**

```python
# In cli.py around line 1834
if ms_was_rephased:
    # MS was rephased - use manual calculation
    if hasattr(args, 'cal_ra_deg') and args.cal_ra_deg:
        # Explicit coordinates provided - use manual calculation
        model_helpers.write_point_model_with_ft(..., use_manual=True)
    else:
        # Warn user about ft() bug
        print("WARNING: setjy uses ft() which has phase center bugs...")
else:
    # MS not rephased - check if explicit coordinates provided
    if hasattr(args, 'cal_ra_deg') and args.cal_ra_deg:
        # Explicit coordinates provided - use manual calculation
        model_helpers.write_point_model_with_ft(..., use_manual=True)
    else:
        # No explicit coordinates - falls back to setjy (uses ft())
        model_helpers.write_setjy_model(...)  # Uses ft() internally
```

---

## **Recommendation**

**For Production:**
- ✅ **Always use `--model-source=catalog`** with explicit coordinates
- ✅ This ensures manual MODEL_DATA calculation is used
- ✅ Avoids `ft()` bugs entirely

**Example Production Command:**
```bash
python -m dsa110_contimg.calibration.cli calibrate \
  --ms MS.ms \
  --field 0 \
  --refant 106 \
  --model-source catalog \
  --cal-ra-deg <RA> \
  --cal-dec-deg <DEC> \
  --cal-flux-jy <FLUX> \
  --skip-rephase  # or omit for rephasing
```

---

## **Future Fix (Optional)**

**To fully fix this edge case:**
- Modify `write_setjy_model()` to always use manual calculation when possible
- Or detect when `ft()` would be used and automatically switch to manual calculation
- **Priority:** Low (workaround exists, primary workflow unaffected)

---

## **Summary**

**Status:** ✅ **Documented and Workaround Available**

**Impact:** Low (uncommon in production)

**Recommendation:** Use catalog model workflow for production

**Edge Case:** `setjy` without rephasing and without explicit coordinates → uses buggy `ft()`

**Workaround:** Use catalog model or provide explicit coordinates

