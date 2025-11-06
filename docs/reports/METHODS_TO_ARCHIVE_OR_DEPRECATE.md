# Methods to Archive or Deprecate - Faulty Methods Analysis

**Date:** 2025-11-05  
**Status:** Analysis Complete  
**Priority:** Medium - Code cleanup and user safety

---

## 🎯 **Executive Summary**

Several methods in the calibration pipeline use CASA's `ft()` function directly, which has known phase center bugs. While safeguards prevent problematic usage in the main workflow, some methods should be archived or deprecated to prevent future issues.

---

## 📋 **Methods Analysis**

### **1. `write_point_model_quick()` - ARCHIVE ⚠️**

**Location:** `src/dsa110_contimg/calibration/model.py:274-299`

**Status:** Testing-only, not used in production

**Issues:**
- ❌ Marked as "testing only" in docstring
- ❌ No phase calculation (amplitude-only)
- ❌ Not used anywhere in codebase

**Recommendation:** ✅ **ARCHIVE** - Move to `archive/legacy/` or remove

**Action:**
```bash
# Move to archive
mkdir -p archive/legacy/calibration
mv src/dsa110_contimg/calibration/model.py archive/legacy/calibration/model_quick.py
# Or simply delete if not needed for historical reference
```

---

### **2. `write_setjy_model()` - DEPRECATE (Keep with Warnings)**

**Location:** `src/dsa110_contimg/calibration/model.py:326-344`

**Status:** Still used in CLI (with safeguards), but has known bugs

**Issues:**
- ⚠️ Uses `setjy()` which internally calls `ft()` with phase center bugs
- ⚠️ Known to cause 100°+ phase scatter when MS is rephased
- ✅ CLI now prevents problematic usage (blocks `setjy`+rephasing)
- ✅ CLI falls back to manual calculation when possible

**Current Usage:**
- Still called in CLI as fallback when:
  - `setjy` without rephasing AND no explicit coordinates provided
  - Edge case (low priority)

**Recommendation:** ⚠️ **DEPRECATE** (not archive yet)
- Add deprecation warning to function
- Document known issues
- Recommend `write_point_model_with_ft(use_manual=True)` instead
- Keep for backward compatibility but discourage use

**Implementation:**
```python
def write_setjy_model(
    ms_path: str,
    field: str,
    *,
    standard: str = "Perley-Butler 2017",
    spw: str = "",
    usescratch: bool = True,
) -> None:
    """Populate MODEL_DATA via casatasks.setjy for standard calibrators.
    
    .. deprecated:: 2025-11-05
        This function has known phase center bugs when used with rephased MS.
        Use :func:`write_point_model_with_ft` with ``use_manual=True`` instead.
        
        Known Issues:
        - Uses setjy() which internally calls ft() with phase center bugs
        - Causes 100°+ phase scatter when MS is rephased
        - Does not use PHASE_DIR correctly after rephasing
        
        The CLI now prevents problematic usage, but this function is deprecated
        for new code.
    """
    import warnings
    warnings.warn(
        "write_setjy_model() is deprecated. Use write_point_model_with_ft(use_manual=True) instead. "
        "This function has known phase center bugs. See docs/reports/EDGE_CASE_DOCUMENTATION.md",
        DeprecationWarning,
        stacklevel=2
    )
    # ... rest of function
```

---

### **3. `write_component_model_with_ft()` - DEPRECATE (Keep with Warnings)**

**Location:** `src/dsa110_contimg/calibration/model.py:302-311`

**Status:** Still used in CLI for component list models

**Issues:**
- ⚠️ Uses `ft()` directly, which has phase center bugs
- ⚠️ No manual calculation alternative available for component lists
- ✅ Less commonly used (component models are rare)

**Current Usage:**
- Used when `--model-source=component` is specified
- No alternative available (component lists require ft())

**Recommendation:** ⚠️ **DEPRECATE** (not archive yet)
- Add deprecation warning
- Document known issues
- Recommend using catalog model with manual calculation when possible
- Keep for component list support (no alternative)

**Implementation:**
```python
def write_component_model_with_ft(ms_path: str, component_path: str) -> None:
    """Apply an existing CASA component list (.cl) into MODEL_DATA using ft.
    
    .. deprecated:: 2025-11-05
        This function uses ft() which has known phase center bugs.
        For point sources, use :func:`write_point_model_with_ft` with ``use_manual=True`` instead.
        
        Known Issues:
        - Uses ft() which does not use PHASE_DIR correctly after rephasing
        - May cause phase scatter when MS is rephased
        
        This function is kept for component list support (no manual alternative available).
        Use with caution and only when component list is required.
    """
    import warnings
    warnings.warn(
        "write_component_model_with_ft() uses ft() which has known phase center bugs. "
        "For point sources, use write_point_model_with_ft(use_manual=True) instead. "
        "See docs/reports/FT_PHASE_CENTER_FIX.md",
        DeprecationWarning,
        stacklevel=2
    )
    # ... rest of function
```

---

### **4. `write_image_model_with_ft()` - DEPRECATE (Keep with Warnings)**

**Location:** `src/dsa110_contimg/calibration/model.py:314-323`

**Status:** Still used in CLI for image models

**Issues:**
- ⚠️ Uses `ft()` directly, which has phase center bugs
- ⚠️ No manual calculation alternative available for images
- ✅ Less commonly used (image models are rare)

**Current Usage:**
- Used when `--model-source=image` is specified
- No alternative available (images require ft())

**Recommendation:** ⚠️ **DEPRECATE** (not archive yet)
- Add deprecation warning
- Document known issues
- Recommend using catalog model with manual calculation when possible
- Keep for image model support (no alternative)

**Implementation:**
```python
def write_image_model_with_ft(ms_path: str, image_path: str) -> None:
    """Apply a CASA image model into MODEL_DATA using ft.
    
    .. deprecated:: 2025-11-05
        This function uses ft() which has known phase center bugs.
        For point sources, use :func:`write_point_model_with_ft` with ``use_manual=True`` instead.
        
        Known Issues:
        - Uses ft() which does not use PHASE_DIR correctly after rephasing
        - May cause phase scatter when MS is rephased
        
        This function is kept for image model support (no manual alternative available).
        Use with caution and only when image model is required.
    """
    import warnings
    warnings.warn(
        "write_image_model_with_ft() uses ft() which has known phase center bugs. "
        "For point sources, use write_point_model_with_ft(use_manual=True) instead. "
        "See docs/reports/FT_PHASE_CENTER_FIX.md",
        DeprecationWarning,
        stacklevel=2
    )
    # ... rest of function
```

---

### **5. `ft_from_cl()` - KEEP (Add Warnings, No Deprecation)**

**Location:** `src/dsa110_contimg/calibration/skymodels.py:66-126`

**Status:** ✅ **CRITICAL - Still needed for NVSS multi-component models**

**Issues:**
- ⚠️ Uses `ft()` directly, which has phase center bugs
- ⚠️ Known WSClean compatibility issues (double free crashes)
- ⚠️ Warning already exists but not comprehensive
- ✅ **NO ALTERNATIVE AVAILABLE** for multi-component lists

**Current Usage:**
- Used in imaging CLI for NVSS model seeding (multi-component)
- Used for calibrator seeding (single component, but via component list)
- Essential for imaging workflow

**Critical Use Case:**
```python
# From imaging/cli.py:615
# NVSS sources are multi-component (>10 mJy sources in FoV)
make_nvss_component_cl(...)  # Creates component list with multiple sources
ft_from_cl(ms_path, cl_path, ...)  # Applies multi-component model via ft()
```

**Recommendation:** ✅ **KEEP** (do NOT deprecate)
- Upgrade existing warning to be more comprehensive
- Document known phase center issues when MS is rephased
- Document WSClean compatibility issues
- Keep for multi-component model support (no manual alternative)
- **Future enhancement:** Consider implementing manual calculation for multi-component models

**Implementation:**
```python
def ft_from_cl(
    ms_target: str,
    cl_path: str,
    *,
    field: str = "0",
    usescratch: bool = True,
) -> None:
    """Apply a component-list skymodel to MODEL_DATA via CASA ft().
    
    .. deprecated:: 2025-11-05
        This function uses ft() which has known phase center bugs and WSClean compatibility issues.
        For point sources, use :func:`write_point_model_with_ft` with ``use_manual=True`` instead.
        
        Known Issues:
        - Uses ft() which does not use PHASE_DIR correctly after rephasing
        - May cause phase scatter when MS is rephased
        - Known WSClean compatibility issues (double free crashes)
        - Should be called BEFORE WSClean, not after
        
        This function is kept for component list support in imaging workflow.
        Use with caution and ensure proper workflow order.
    """
    import warnings
    warnings.warn(
        "ft_from_cl() is deprecated. Uses ft() which has known phase center bugs. "
        "For point sources, use write_point_model_with_ft(use_manual=True) instead. "
        "See docs/reports/FT_PHASE_CENTER_FIX.md",
        DeprecationWarning,
        stacklevel=2
    )
    # ... rest of function (keep existing warnings about WSClean)
```

---

### **6. `write_point_model_with_ft()` with `use_manual=False` - DOCUMENT (Keep)**

**Location:** `src/dsa110_contimg/calibration/model.py:171-271`

**Status:** ✅ **KEEP** - This is the correct function, but default behavior changed

**Issues:**
- ⚠️ Default `use_manual=False` uses `ft()` (has bugs)
- ✅ CLI now always uses `use_manual=True` when rephasing
- ✅ Manual calculation is the correct approach

**Recommendation:** ✅ **KEEP** but change default
- Change default to `use_manual=True` (safer)
- Document that `use_manual=False` is for compatibility only
- Keep both modes for backward compatibility

**Implementation:**
```python
def write_point_model_with_ft(
    ms_path: str,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    *,
    reffreq_hz: float = 1.4e9,
    spectral_index: Optional[float] = None,
    field: Optional[str] = None,
    use_manual: bool = True,  # CHANGED: Default to True (safer)
) -> None:
    """Write a physically-correct complex point-source model into MODEL_DATA.
    
    Args:
        ...
        use_manual: If True, use manual calculation (recommended, default).
                   If False, use ft() which has known phase center bugs.
                   Use False only for compatibility with legacy code.
    """
```

---

## 📊 **Summary Table**

| Method | Status | Action | Priority |
|--------|--------|--------|----------|
| `write_point_model_quick()` | Testing only | **ARCHIVE** | High |
| `write_setjy_model()` | Used with safeguards | **DEPRECATE** | Medium |
| `write_component_model_with_ft()` | Rarely used | **DEPRECATE** | Low |
| `write_image_model_with_ft()` | Rarely used | **DEPRECATE** | Low |
| `ft_from_cl()` | **CRITICAL - NVSS multi-component** | **KEEP** (add warnings) | N/A |
| `write_point_model_with_ft(use_manual=False)` | Correct function | **CHANGE DEFAULT** | High |

---

## 🎯 **Recommended Actions**

### **Immediate (High Priority)**
1. ✅ **Archive `write_point_model_quick()`** - Not used, testing only
2. ✅ **Change default `use_manual=True`** in `write_point_model_with_ft()` - Safer default

### **Short-term (Medium Priority)**
3. ⚠️ **Deprecate `write_setjy_model()`** - Add deprecation warning
4. ⚠️ **Enhance `ft_from_cl()` warnings** - Document phase center issues (do NOT deprecate - needed for NVSS)

### **Long-term (Low Priority)**
5. ⚠️ **Deprecate component/image model functions** - Add warnings, keep for compatibility
6. 📋 **Consider removing deprecated functions** in future major version (after deprecation period)

---

## ✅ **Implementation Plan**

### **Phase 1: Archive (Immediate)**
- [ ] Move `write_point_model_quick()` to `archive/legacy/` or delete
- [ ] Update imports if any exist

### **Phase 2: Change Defaults (Immediate)**
- [ ] Change `use_manual=True` default in `write_point_model_with_ft()`
- [ ] Update CLI to explicitly use `use_manual=True` (already done)
- [ ] Test backward compatibility

### **Phase 3: Deprecate (Short-term)**
- [ ] Add deprecation warnings to `write_setjy_model()`
- [ ] Add deprecation warnings to `ft_from_cl()`
- [ ] Add deprecation warnings to component/image model functions
- [ ] Update documentation

### **Phase 4: Documentation (Short-term)**
- [ ] Create migration guide for deprecated functions
- [ ] Update API documentation
- [ ] Add examples of correct usage

---

## 📝 **Notes**

- **Keep deprecated functions** for backward compatibility
- **Add clear warnings** to guide users to correct alternatives
- **Document known issues** in docstrings and reports
- **Archive only truly unused** functions
- **Change defaults** to safer options where possible

