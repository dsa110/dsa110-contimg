# SwigPy Deprecation Warnings Investigation Summary

## Question

Are SwigPy deprecation warnings truly unavoidable?

## Answer

**Partially correct:** The warnings CAN be suppressed, but require suppression at Python startup (command-line or environment variable) because they're emitted during module import time before Python code executes.

## Investigation Results

### Root Cause Confirmed ✅

- **Source:** SWIG-generated Python bindings in CASA/casacore
- **Issue:** Missing `__module__` attributes on SWIG types (`SwigPyPacked`, `SwigPyObject`, `swigvarlink`)
- **SWIG Issue:** Tracked in [swig/swig#2881](https://github.com/swig/swig/issues/2881)
- **Fix Status:** Fixed in SWIG 4.4+ (not yet widely released)

### Suppression Methods Tested

1. **`warnings.filterwarnings()` in code** ⚠️ **Partial**
   - Added to `casa_init.py`
   - **Limitation:** Warnings emitted during import time (`<frozen importlib._bootstrap>`) appear before Python code runs
   - **Result:** Some warnings still appear

2. **Command-line flag** ✅ **Complete**
   - `python -W ignore::DeprecationWarning script.py`
   - **Result:** All warnings suppressed
   - **Recommendation:** Use this for scripts

3. **Environment variable** ✅ **Complete**
   - `export PYTHONWARNINGS="ignore::DeprecationWarning"`
   - **Result:** All warnings suppressed
   - **Recommendation:** Use this for development environment

## Updated Assessment

### Original Statement
> "Cannot be fixed (CASA library internals)" - **PARTIALLY INCORRECT**

### Corrected Statement
> "Can be suppressed via command-line flag or environment variable. Warnings are emitted during import time, so code-based suppression may not catch all warnings."

## Implementation

### Code Changes
- ✅ Added suppression to `casa_init.py` (catches warnings after import)
- ✅ Documented command-line and environment variable methods

### Recommended Usage

**For scripts:**
```bash
/opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning script.py
```

**For development:**
```bash
export PYTHONWARNINGS="ignore::DeprecationWarning"
```

**For Makefile:**
```makefile
CASA6_PYTHON := /opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning
```

## Impact

- **Functionality:** None (warnings are cosmetic)
- **Performance:** None
- **Noise:** High (can clutter logs)
- **Suppression:** Effective with command-line flag or environment variable

## Conclusion

The warnings are **suppressible** but require suppression at Python startup (command-line flag or environment variable) because they're emitted during module import time. Code-based suppression in `casa_init.py` helps but may not catch all warnings.

**Recommendation:** Use command-line flag (`-W ignore::DeprecationWarning`) for scripts, or set environment variable for development sessions.

