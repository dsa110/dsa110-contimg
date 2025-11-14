# Warnings and Errors Check-in

**Date:** 2025-01-28  
**Status:** All known warnings addressed or documented

## Summary

### ✓ Addressed Warnings

1. **FITS CDELT Format Warning** ✓ FIXED
   - Root cause: High-precision CDELT values in FITS headers
   - Fix: `utils/fits_utils.py` rounds CDELT to 10 decimal places
   - Status: Applied to all image FITS writing functions

2. **Observatories Table Missing Warning** ✓ FIXED
   - Root cause: `CASAPATH` not set before CASA imports
   - Fix: `utils/casa_init.py` with `ensure_casa_path()` function
   - Status: Applied to 58 files importing CASA modules

3. **CASA API Errors** ✓ FIXED
   - `.coordsys()` → `.coordinates()` (4 locations)
   - `.close()` → `del` for `casaimage` objects
   - Constructor usage corrected

### ⚠️ SwigPy Deprecation Warnings (Now Suppressed)

1. **SwigPy Deprecation Warnings** (CASA Library)
   - **Source:** CASA/casacore internal SWIG bindings
   - **Examples:**
     ```
     DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute
     DeprecationWarning: builtin type SwigPyObject has no __module__ attribute
     ```
   - **Status:** ✅ **SUPPRESSED** in `casa_init.py`
   - **Root Cause:** SWIG-generated bindings missing `__module__` attributes (fixed in SWIG 4.4+)
   - **Impact:** None - does not affect functionality (cosmetic only)
   - **Action:** Suppressed via `warnings.filterwarnings()` in `utils/casa_init.py`
   - **Reference:** See `docs/dev/SWIGPY_WARNINGS_SUPPRESSION.md` for details

### 📝 Intentionally Suppressed Warnings

1. **hashlib DeprecationWarning** (`mosaic/cache.py`)
   - **Reason:** MD5 usage for cache keys (non-cryptographic)
   - **Status:** Documented in code comment
   - **Action:** None required (intentional suppression)

### 🔍 Exception Handling Review

**Pattern:** Broad `except Exception` handlers are used extensively for:
- CASA tool failures (expected, handled gracefully)
- File I/O errors (logged, fallback paths)
- Import errors (optional dependencies)
- Validation failures (logged, continue processing)

**Status:** All exception handlers are intentional and appropriate:
- Log errors appropriately
- Provide fallback paths where available
- Do not silently ignore critical errors
- Use specific exception types where possible (`ImportError`, `RuntimeError`, etc.)

### 📊 Warning Suppression Patterns Found

1. **`warnings.filterwarnings()`** - 1 location
   - `mosaic/cache.py`: Suppresses hashlib deprecation (documented)

2. **`# type: ignore`** - Many locations
   - Used for CASA imports (type stubs unavailable)
   - Used for optional dependencies
   - Status: Appropriate and documented

3. **`# noqa`** - Many locations
   - Used for linter-specific suppressions
   - Status: Appropriate

### ✅ No Unaddressed Issues Found

- All known warnings have been fixed or documented
- No silent error suppression found
- All exception handlers are intentional
- Warning filters are documented

## Recommendations

1. **SwigPy Warnings:** No action needed - these are from CASA library internals
2. **Monitor:** Continue monitoring for new warnings during integration testing
3. **Documentation:** This check-in document serves as record of warning status

## Next Steps

- Monitor warnings during full integration tests with real data
- Update this document if new warnings appear
- Consider adding warning capture to test suite for regression detection

