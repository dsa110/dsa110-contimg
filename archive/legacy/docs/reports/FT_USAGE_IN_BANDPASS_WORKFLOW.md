# ft() Usage in Bandpass Calibration Workflow

**Date:** 2025-11-05  
**Status:** Historical Context - ft() is now bypassed with manual calculation

---

## 🎯 **Pipeline Stage: MODEL_DATA Population (Pre-Bandpass)**

**`ft()` was used at Stage 1: MODEL_DATA Population, which happens BEFORE bandpass calibration.**

---

## 📋 **Calibration Workflow Order**

```
1. MODEL_DATA Population (where ft() was used)
   ↓
2. Optional: Pre-bandpass Phase Solve
   ↓
3. Bandpass Calibration (reads MODEL_DATA)
   ↓
4. Gain Calibration (reads MODEL_DATA)
```

---

## 🔍 **Stage 1: MODEL_DATA Population (Where ft() Was Used)**

### **Location in Code:**
- **File:** `src/dsa110_contimg/calibration/cli.py`
- **Lines:** ~1492-1804 (MODEL_DATA population section)
- **Called BEFORE:** Bandpass solve (line ~1694 in `solve_bandpass()`)

### **Purpose:**
- Populate `MODEL_DATA` column with predicted visibilities from calibrator model
- Bandpass calibration requires `MODEL_DATA` to know what signal to calibrate against
- Without `MODEL_DATA`, bandpass solve will fail or produce incorrect solutions

### **How ft() Was Used:**

**Before Fix (Problematic):**
```python
# In cli.py, when --model-source=catalog or --model-source=setjy
write_point_model_with_ft(
    ms_path, ra_deg, dec_deg, flux_jy,
    use_manual=False  # ❌ Uses ft() - has phase center bugs
)
```

**After Fix (Current):**
```python
# In cli.py, when --model-source=catalog (default)
write_point_model_with_ft(
    ms_path, ra_deg, dec_deg, flux_jy,
    use_manual=True  # ✅ Uses manual calculation - bypasses ft()
)
```

---

## ⚠️ **The Problem**

### **When ft() Was Used:**
1. **Catalog model (`--model-source catalog`):**
   - `write_point_model_with_ft()` with `use_manual=False`
   - Created component list (.cl file)
   - Called CASA `ft()` to populate MODEL_DATA
   - **Problem:** `ft()` doesn't use `PHASE_DIR` correctly after rephasing

2. **setjy model (`--model-source setjy`):**
   - `write_setjy_model()` → internally calls `setjy()`
   - `setjy()` internally calls `ft()` to populate MODEL_DATA
   - **Problem:** Same phase center bug as direct `ft()` usage

### **Impact:**
- When MS was rephased to calibrator position, `ft()` still used original meridian phase center
- Result: MODEL_DATA had ~102-104° phase scatter
- Bandpass calibration failed or produced poor solutions (high flagging, low SNR)

---

## ✅ **The Fix**

### **Current Implementation:**

**Stage 1: MODEL_DATA Population (Now Uses Manual Calculation)**

```python
# In cli.py:1795-1804
# Use manual calculation to populate MODEL_DATA (bypasses ft() phase center issues)
# Manual calculation uses PHASE_DIR per field, ensuring correct phase structure
model_helpers.write_point_model_with_ft(
    args.ms, float(ra_deg), float(dec_deg), float(flux_jy),
    field=field_sel, use_manual=True  # ✅ Manual calculation
)
```

**Manual Calculation:**
- Reads `PHASE_DIR` from FIELD table (correct phase center after rephasing)
- Calculates phase directly: `phase = 2π * (u*ΔRA + v*ΔDec) / λ`
- Uses correct phase center per field
- **Result:** MODEL_DATA phase structure matches DATA column exactly

---

## 📊 **Timeline in Pipeline**

### **Full Calibration Workflow:**

```
┌─────────────────────────────────────────────────────────────┐
│ Stage 0: Flagging (optional)                                │
│   - Reset flags, flag zeros, RFI flagging                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: MODEL_DATA Population  ← ft() WAS USED HERE       │
│   - Rephase MS to calibrator (if needed)                    │
│   - Populate MODEL_DATA with calibrator model               │
│   - OLD: ft() via write_point_model_with_ft(use_manual=False)│
│   - NEW: Manual calculation via _calculate_manual_model_data()│
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: Pre-bandpass Phase Solve (optional)                │
│   - solve_prebandpass_phase() - reads MODEL_DATA            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 3: Bandpass Calibration  ← READS MODEL_DATA HERE     │
│   - solve_bandpass() - reads MODEL_DATA                     │
│   - Compares DATA vs MODEL_DATA to derive bandpass          │
│   - Requires MODEL_DATA to be correctly populated           │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 4: Gain Calibration                                    │
│   - solve_gains() - reads MODEL_DATA                        │
│   - Applies bandpass solutions before solving               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 **Key Points**

1. **`ft()` was used at Stage 1: MODEL_DATA Population**
   - This happens **BEFORE** bandpass calibration
   - Bandpass calibration **reads** MODEL_DATA (doesn't populate it)

2. **Why MODEL_DATA is Critical:**
   - Bandpass calibration compares `DATA` column to `MODEL_DATA` column
   - If MODEL_DATA has wrong phase center, bandpass solutions are wrong
   - This causes 100°+ phase scatter in calibration solutions

3. **The Fix:**
   - Manual calculation replaces `ft()` for single point sources
   - Manual calculation uses correct `PHASE_DIR` per field
   - Ensures MODEL_DATA matches DATA column phase structure

4. **Current Status:**
   - ✅ Catalog model uses manual calculation (bypasses ft())
   - ✅ setjy model uses manual calculation when rephased
   - ⚠️ Component/image models still use ft() (no alternative)
   - ✅ NVSS multi-component models use ft() (needed, but documented warnings)

---

## 📝 **Code References**

**MODEL_DATA Population (Stage 1):**
- `src/dsa110_contimg/calibration/cli.py:1492-1804` - MODEL_DATA population logic
- `src/dsa110_contimg/calibration/model.py:171-271` - `write_point_model_with_ft()` function
- `src/dsa110_contimg/calibration/model.py:27-168` - `_calculate_manual_model_data()` function

**Bandpass Calibration (Stage 3):**
- `src/dsa110_contimg/calibration/cli.py:1694` - `solve_bandpass()` call
- `src/dsa110_contimg/calibration/calibration.py:579-740` - `solve_bandpass()` implementation
- `src/dsa110_contimg/calibration/calibration.py:621-640` - MODEL_DATA validation (precondition check)

---

## ✅ **Summary**

**`ft()` was used at Stage 1: MODEL_DATA Population, which happens BEFORE bandpass calibration.**

**Root Cause (Corrected Understanding):**
- `ft()` reads phase center from FIELD parameters (CASA documentation)
- `ft()` uses **ONE phase center** for **ALL fields** in the MS
- When fields have different phase centers (e.g., each field phased to its own meridian), `ft()` uses the wrong phase center for fields 1-23
- When all fields share the same phase center (after rephasing), `ft()` can work correctly

**Current fix:** Manual calculation replaces `ft()` for single point sources, ensuring correct **per-field phase center** handling and preventing the 100°+ phase scatter bug, even when fields have different phase centers.

**Key Insight:** The high phase errors occur because `ft()` uses one phase center for all fields when fields have different phase centers. Manual calculation handles per-field phase centers correctly, making it more robust.

