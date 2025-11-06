# NVSS ft() Usage Analysis: Why We Still Need ft() for Multi-Component Models

**Date:** 2025-11-05  
**Status:** Critical Use Case Identified  
**Priority:** High - Corrects deprecation analysis

---

## 🎯 **Key Finding**

**`ft_from_cl()` is CRITICAL for NVSS multi-component models and should NOT be deprecated.**

---

## 📋 **NVSS Use Case**

### **Imaging Workflow (Multi-Component Models)**

**Location:** `src/dsa110_contimg/imaging/cli.py:568-624`

**Purpose:** Seed MODEL_DATA with NVSS sources (>10 mJy) for guided deconvolution

**Workflow:**
```python
# Step 1: Create multi-component list from NVSS catalog
make_nvss_component_cl(
    ra0_deg, dec0_deg, radius_deg,
    min_mjy=nvss_min_mjy,  # e.g., 10 mJy
    freq_ghz=freq_ghz,
    out_path=cl_path
)
# Result: Component list (.cl) with multiple point sources

# Step 2: Apply component list to MODEL_DATA via ft()
ft_from_cl(ms_path, cl_path, field=field, usescratch=True)
# Result: MODEL_DATA populated with all NVSS sources
```

**Why ft() is Needed:**
- NVSS models are **multi-component** (multiple point sources)
- `make_nvss_component_cl()` creates a CASA component list (.cl file)
- Component lists require `ft()` - no manual alternative exists
- Manual calculation (`_calculate_manual_model_data()`) only supports single point sources

---

## 🔍 **Comparison: Single vs Multi-Component**

### **Single Point Source (Calibrator)**
✅ **Can use manual calculation:**
```python
# Manual calculation available
write_point_model_with_ft(
    ms_path, ra_deg, dec_deg, flux_jy,
    use_manual=True  # ✅ Uses _calculate_manual_model_data()
)
```

### **Multi-Component (NVSS Sources)**
❌ **Must use ft():**
```python
# No manual alternative for multi-component
make_nvss_component_cl(...)  # Creates .cl with multiple sources
ft_from_cl(ms_path, cl_path, ...)  # ✅ Only option - uses ft()
```

---

## ⚠️ **Known Issues with ft() for NVSS**

### **1. Phase Center Bugs (When MS Rephased)**
- `ft()` doesn't use `PHASE_DIR` correctly after rephasing
- Causes phase scatter in MODEL_DATA
- **Impact:** Less critical for NVSS (used for imaging, not calibration)

### **2. WSClean Compatibility**
- `ft()` crashes if MODEL_DATA already contains WSClean data
- Workaround: Clear MODEL_DATA before calling `ft()`
- **Impact:** Workflow order matters (ft() before WSClean)

---

## ✅ **Corrected Recommendation**

### **`ft_from_cl()` - KEEP (Do NOT Deprecate)**

**Reason:**
- ✅ Essential for NVSS multi-component models
- ✅ No alternative available
- ✅ Used in production imaging workflow

**Action:**
- ✅ Keep function as-is
- ⚠️ Enhance warnings about phase center issues
- ⚠️ Document WSClean compatibility requirements
- 📋 Future: Consider implementing manual multi-component calculation

---

## 📋 **Updated Deprecation Strategy**

### **Methods to Deprecate:**
1. ✅ `write_setjy_model()` - Single point, can use manual calculation
2. ✅ `write_component_model_with_ft()` - Single component list, but rare
3. ✅ `write_image_model_with_ft()` - Image model, but rare
4. ✅ `write_point_model_with_ft(use_manual=False)` - Change default

### **Methods to KEEP:**
1. ✅ `ft_from_cl()` - **CRITICAL for NVSS multi-component models**
2. ✅ `make_nvss_component_cl()` - Creates NVSS component lists
3. ✅ `make_point_cl()` - Creates single-component lists (used by NVSS workflow)

---

## 🎯 **Future Enhancement Opportunity**

**Consider implementing manual multi-component calculation:**

```python
def _calculate_manual_multi_component_model_data(
    ms_path: str,
    component_list_path: str,  # Read .cl file
    field: Optional[str] = None,
) -> None:
    """Manual calculation for multi-component models.
    
    Reads CASA component list (.cl) and calculates MODEL_DATA
    for all components using manual phase calculation.
    
    This would bypass ft() phase center bugs while supporting
    multi-component models (like NVSS).
    """
    # Read .cl file to get component list
    # For each component:
    #   - Extract RA, Dec, flux
    #   - Use _calculate_manual_model_data() logic
    #   - Sum contributions from all components
    # Write combined MODEL_DATA
```

**Benefits:**
- ✅ Bypasses ft() phase center bugs
- ✅ Supports multi-component models
- ✅ Same accuracy as single-component manual calculation

**Complexity:**
- ⚠️ Requires parsing CASA .cl file format
- ⚠️ More complex than single-component calculation
- 📋 Lower priority (ft() works for NVSS, phase issues less critical in imaging)

---

## ✅ **Summary**

**`ft_from_cl()` is essential for NVSS multi-component models and should be kept (not deprecated).**

**Key Points:**
- NVSS models are multi-component (multiple sources)
- Manual calculation only supports single point sources
- `ft_from_cl()` is the only way to populate MODEL_DATA for NVSS
- Phase center bugs are less critical for imaging (vs calibration)
- WSClean compatibility issues are handled with clear warnings

**Action:** Keep `ft_from_cl()` but enhance warnings about known issues.

