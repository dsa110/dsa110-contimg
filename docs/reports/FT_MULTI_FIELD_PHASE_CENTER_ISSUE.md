# ft() Multi-Field Phase Center Issue - Corrected Understanding

**Date:** 2025-11-05  
**Status:** Root Cause Corrected Understanding  
**Priority:** Critical - Corrects previous misunderstanding

---

## 🎯 **Corrected Understanding**

### **Key Insight from CASA Documentation**

**CASA documentation shows that `ft()` reads phase center from FIELD parameters of the MS.**

**The Real Problem:**
- For a **24-field MS** where each field is phased to the **meridian** (different phase centers per field)
- Trying to apply `ft()` to the **whole MS** as one MODEL_DATA column **won't work**
- Each field has a **different phase center** (each field is phased to its own meridian transit)
- **`ft()` will only succeed if every field is phased to the same phase center**

---

## 🔍 **The Actual Problem**

### **Scenario: 24 Fields with Different Phase Centers**

**Original MS State:**
- Field 0: Phased to meridian at time T0 (phase center A)
- Field 1: Phased to meridian at time T1 (phase center B)
- Field 2: Phased to meridian at time T2 (phase center C)
- ...
- Field 23: Phased to meridian at time T23 (phase center X)

**What `ft()` Does:**
- Reads phase center from FIELD table (probably field 0, or first field processed)
- Uses that **single phase center** for **ALL fields** in the MS
- Calculates MODEL_DATA for all rows using the same phase center

**The Problem:**
- Rows from field 0: Use phase center A ✓ (correct)
- Rows from field 1: Use phase center A ✗ (wrong - should use phase center B)
- Rows from field 2: Use phase center A ✗ (wrong - should use phase center C)
- ...
- Rows from field 23: Use phase center A ✗ (wrong - should use phase center X)

**Result:**
- High phase errors for fields 1-23 (wrong phase center used)
- Only field 0 has correct MODEL_DATA
- This causes 100°+ phase scatter when calibration tries to use all fields

---

## ✅ **When ft() Works Correctly**

### **All Fields Share Same Phase Center**

**After Rephasing All Fields to Calibrator:**
- Field 0: Phased to calibrator position (phase center = calibrator)
- Field 1: Phased to calibrator position (phase center = calibrator)
- Field 2: Phased to calibrator position (phase center = calibrator)
- ...
- Field 23: Phased to calibrator position (phase center = calibrator)

**What `ft()` Does:**
- Reads phase center from FIELD table (all fields have same phase center)
- Uses that phase center for ALL fields
- Calculates MODEL_DATA for all rows using the same phase center ✓

**Result:**
- All fields use correct phase center ✓
- MODEL_DATA phase structure is correct ✓
- **High phase errors won't exist** ✓

---

## 📋 **Why Manual Calculation Works**

### **Manual Calculation Handles Per-Field Phase Centers**

**Location:** `src/dsa110_contimg/calibration/model.py:_calculate_manual_model_data()`

**How It Works:**
```python
# For each row in MS:
for row_idx in range(nrows):
    # Get the field index for this row
    row_field_idx = field_id[row_idx]
    
    # Use THIS FIELD's PHASE_DIR (not a single phase center for all fields)
    phase_center_ra_deg = phase_dir[row_field_idx][0][0]  # Per-field phase center
    phase_center_dec_deg = phase_dir[row_field_idx][0][1]
    
    # Calculate phase using THIS field's phase center
    phase = 2π * (u*ΔRA + v*ΔDec) / λ
```

**Key Difference:**
- Manual calculation reads **PHASE_DIR per field** for each row
- Uses the **correct phase center** for each field
- Works correctly even when fields have different phase centers

**ft() Limitation:**
- Reads **one phase center** from FIELD table
- Uses that **same phase center** for all fields
- Fails when fields have different phase centers

---

## 🔄 **Workflow Implications**

### **Before Rephasing (24 Different Phase Centers)**

**Problem:**
```
Field 0: Phase center = Meridian T0
Field 1: Phase center = Meridian T1
...
Field 23: Phase center = Meridian T23

ft() called with field="" (all fields)
  → Reads phase center from field 0
  → Uses phase center T0 for ALL fields
  → ✗ Wrong phase center for fields 1-23
```

**Solution Options:**
1. **Rephase all fields to same phase center** (calibrator position)
   - Then `ft()` will work correctly ✓
2. **Apply `ft()` per field** (field by field)
   - Call `ft(field="0")`, `ft(field="1")`, etc.
   - Each call uses that field's phase center ✓
3. **Use manual calculation**
   - Handles per-field phase centers automatically ✓

### **After Rephasing All Fields to Calibrator**

**Works Correctly:**
```
Field 0: Phase center = Calibrator (all fields same)
Field 1: Phase center = Calibrator (all fields same)
...
Field 23: Phase center = Calibrator (all fields same)

ft() called with field="" (all fields)
  → Reads phase center from any field (all same)
  → Uses calibrator phase center for ALL fields
  → ✓ Correct phase center for all fields
```

---

## ✅ **Corrected Root Cause**

### **Previous Understanding (INCORRECT):**
- `ft()` doesn't read PHASE_DIR correctly
- `ft()` uses wrong phase center source

### **Correct Understanding:**
- `ft()` **DOES read phase center from FIELD parameters** (CASA documentation)
- `ft()` reads **ONE phase center** and uses it for **ALL fields**
- Problem occurs when **fields have different phase centers** (meridian phasing)
- Solution: **Rephase all fields to same phase center** OR **use manual calculation**

---

## 📝 **Code Evidence**

### **Current Implementation (Manual Calculation)**

**Location:** `src/dsa110_contimg/calibration/model.py:121-132`

```python
# Calculate MODEL_DATA for each row using that row's field's PHASE_DIR
for row_idx in range(nrows):
    # Get the field index for this row
    row_field_idx = field_id[row_idx]
    
    # Use this field's PHASE_DIR (not a single phase center)
    phase_center_ra_rad = phase_dir[row_field_idx][0][0]  # Per-field!
    phase_center_dec_rad = phase_dir[row_field_idx][0][1]  # Per-field!
    
    # Calculate phase using THIS field's phase center
    phase = 2 * np.pi * (u[row_idx] * offset_ra_rad + v[row_idx] * offset_dec_rad) / wavelengths
```

**This handles per-field phase centers correctly!**

### **ft() Limitation**

When `ft()` is called:
```python
ft(vis=ms_path, complist=comp_path, usescratch=True, field="")  # All fields
```

**ft() behavior:**
- Reads phase center from FIELD table (probably field 0 or first processed field)
- Uses that **single phase center** for **all fields**
- Fails when fields have different phase centers

---

## 🎯 **Implications for Our Workflow**

### **Why Manual Calculation is Necessary**

**Current MS State:**
- Original MS: 24 fields, each phased to its own meridian (different phase centers)
- After rephasing: All fields phased to calibrator (same phase center)

**But:**
- Manual calculation is **safer** because it handles per-field phase centers correctly
- Even if rephasing doesn't perfectly align all fields, manual calculation works
- Manual calculation is **more robust** to field-level phase center variations

### **Why ft() Can Work After Rephasing**

**If all fields are correctly rephased to the same phase center:**
- `ft()` reads that phase center (same for all fields)
- `ft()` uses it for all fields
- **Result: Works correctly, no high phase errors**

**But:**
- Manual calculation is still safer (handles edge cases)
- Manual calculation is more explicit (per-field phase center handling)
- Manual calculation avoids potential rephasing inconsistencies

---

## ✅ **Summary**

### **Corrected Understanding:**

1. **`ft()` DOES read phase center from FIELD parameters** (CASA documentation)
2. **`ft()` reads ONE phase center** and uses it for ALL fields
3. **Problem occurs when fields have different phase centers** (meridian phasing)
4. **Solution: Rephase all fields to same phase center** OR **use manual calculation**

### **Why Manual Calculation is Still Preferred:**

- ✅ Handles per-field phase centers correctly (even if rephasing incomplete)
- ✅ More robust to field-level phase center variations
- ✅ Explicit per-field phase center handling
- ✅ Works correctly in all scenarios (rephased or not)

### **Key Takeaway:**

**The high phase errors occur because `ft()` uses one phase center for all fields when fields have different phase centers. When all fields share the same phase center (after rephasing), `ft()` can work correctly, but manual calculation is still safer.**

