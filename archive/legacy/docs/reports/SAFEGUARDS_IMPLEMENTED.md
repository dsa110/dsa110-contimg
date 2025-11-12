# User Safeguards Implementation Summary

**Date:** 2025-11-05  
**Status:** ✅ Phase 1 Critical Safeguards Implemented

---

## ✅ **Implemented Safeguards**

### **1. Catalog Model Default (HIGH PRIORITY) - ✅ IMPLEMENTED**

**Change:** Made `--model-source` default to `"catalog"`

**Location:** `src/dsa110_contimg/calibration/cli.py:713-722`

**Before:**
```python
pc.add_argument("--model-source", choices=[...], help=...)
```

**After:**
```python
pc.add_argument(
    "--model-source",
    choices=["catalog", "setjy", "component", "image"],
    default="catalog",  # ✅ ADDED DEFAULT
    help=(
        "Populate MODEL_DATA before bandpass using the specified strategy. "
        "Default: 'catalog' (recommended for production, uses manual calculation). "
        "Use 'setjy' only if calibrator is at phase center and no rephasing is needed."
    ),
)
```

**Impact:**
- ✅ Users no longer need to specify `--model-source` (it just works)
- ✅ Defaults to safest option (catalog model → manual calculation)
- ✅ Prevents accidental use of `setjy` (edge case)

---

### **2. Early Validation for Problematic Combinations (HIGH PRIORITY) - ✅ IMPLEMENTED**

**Change:** Added validation before MODEL_DATA population that prevents `setjy`+rephasing

**Location:** `src/dsa110_contimg/calibration/cli.py:1502-1529`

**Implementation:**
```python
# Validate model source usage BEFORE populating MODEL_DATA
# This prevents problematic combinations (e.g., setjy with rephasing)
if needs_model and args.model_source:
    # Check for problematic setjy usage
    if args.model_source == "setjy":
        if ms_was_rephased:
            p.error(
                "ERROR: --model-source=setjy cannot be used with rephasing.\n"
                "Reason: setjy uses ft() internally, which has phase center bugs after rephasing.\n"
                "Solution: Use --model-source=catalog (default) instead.\n"
                "Or: Use --skip-rephase if calibrator is at meridian phase center.\n"
                "For more information, see: docs/reports/EDGE_CASE_DOCUMENTATION.md"
            )
        if not (hasattr(args, 'cal_ra_deg') and args.cal_ra_deg):
            logger.warning(
                "WARNING: --model-source=setjy without explicit coordinates may have phase issues.\n"
                "Recommendation: Provide --cal-ra-deg and --cal-dec-deg for accurate MODEL_DATA.\n"
                "Or: Use --model-source=catalog (default) which handles this automatically."
            )
    
    # Inform about catalog model default behavior
    if args.model_source == "catalog":
        if not (hasattr(args, 'cal_ra_deg') and args.cal_ra_deg):
            logger.info(
                "INFO: Using catalog model without explicit coordinates.\n"
                "Will attempt --auto-fields to find calibrator in MS field of view.\n"
                "For best results, provide --cal-ra-deg, --cal-dec-deg, --cal-flux-jy."
            )
```

**Impact:**
- ✅ Prevents `setjy`+rephasing combination before execution (hard error)
- ✅ Warns about `setjy` without explicit coordinates
- ✅ Guides users to correct workflow

---

### **3. Better Error Messages with Solutions (MEDIUM PRIORITY) - ✅ IMPLEMENTED**

**Change:** Improved error message for missing calibrator info

**Location:** `src/dsa110_contimg/calibration/cli.py:1817-1827`

**Before:**
```python
p.error("Catalog model requested but calibrator info unavailable...")
```

**After:**
```python
p.error(
    "ERROR: Catalog model requires calibrator information.\n\n"
    "Options:\n"
    "  1. Use --auto-fields (finds calibrator in MS field of view)\n"
    "     python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms --auto-fields\n\n"
    "  2. Provide explicit coordinates (recommended for production)\n"
    "     python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms --cal-ra-deg <RA> --cal-dec-deg <DEC> --cal-flux-jy <FLUX>\n\n"
    "  3. Use --model-source=setjy (only if calibrator at phase center, no rephasing)\n"
    "     python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms --model-source=setjy --model-field 0\n\n"
    "For more information, see: docs/howto/CALIBRATION_DETAILED_PROCEDURE.md"
)
```

**Impact:**
- ✅ Users see clear solutions, not just problems
- ✅ Copy-paste ready commands
- ✅ Links to documentation

---

## 📋 **Remaining Safeguards (Future)**

### **Phase 2: Important (Next Sprint)**
- ⚠️ **Workflow presets** (2-3 hours) - Not yet implemented
- ⚠️ **Documentation links in errors** (1 hour) - Partially implemented

### **Phase 3: Nice to Have (Future)**
- 📋 **Interactive wizard** (1-2 days) - Not yet implemented
- 📋 **Parameter recommendations** (2-3 hours) - Not yet implemented

---

## 🎯 **Expected Impact**

### **Before Safeguards:**
- ❌ Users must know to specify `--model-source=catalog`
- ❌ Users can accidentally use `setjy` with rephasing (gets warnings, still runs)
- ❌ Users see generic errors without solutions
- ❌ Users must understand all parameters

### **After Safeguards (Phase 1):**
- ✅ `--model-source` defaults to safe option (catalog)
- ✅ Error prevents `setjy`+rephasing before execution
- ✅ Error messages include solutions with copy-paste commands
- ✅ Users guided to correct workflow

---

## 📝 **Example: Before vs After**

### **Before (Current):**
```bash
# User tries:
python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms

# Gets error:
ERROR: --model-source is required

# User confused - which one to use?
```

### **After (With Safeguards):**
```bash
# User tries:
python -m dsa110_contimg.calibration.cli calibrate --ms MS.ms

# Works! Uses catalog model by default
# If calibrator info missing, gets helpful error:
ERROR: Catalog model requires calibrator information.

Options:
  1. Use --auto-fields (finds calibrator in MS)
  2. Provide explicit coordinates (recommended)
  3. Use --model-source=setjy (only if at phase center)

# User knows what to do
```

---

## ✅ **Summary**

**Status:** ✅ **Phase 1 Critical Safeguards Implemented**

**Key Safeguards:**
1. ✅ **Default to catalog model** - Prevents accidental use of setjy
2. ✅ **Early validation** - Prevents problematic combinations before execution
3. ✅ **Better error messages** - Users see solutions, not just problems

**Implementation Time:** ~1 hour (completed)

**Expected Outcome:** Users can't accidentally use known-incorrect workflows

**Next Steps:**
- Test safeguards with real user scenarios
- Implement Phase 2 safeguards (workflow presets) if needed
- Gather user feedback on effectiveness

