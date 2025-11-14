# SwigPy Deprecation Warnings - Suppression Guide

## Investigation Results

**Status:** ✅ **CAN BE SUPPRESSED** (not truly unavoidable)

### Root Cause

The `DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute` warnings come from:
- **SWIG-generated Python bindings** used by CASA/casacore
- Missing `__module__` attribute on SWIG types (`SwigPyPacked`, `SwigPyObject`, `swigvarlink`)
- Known SWIG issue tracked in [swig/swig#2881](https://github.com/swig/swig/issues/2881)
- Fixed in SWIG 4.4+ (not yet widely released)

### Impact

- **Functionality:** None - warnings are cosmetic
- **Performance:** None - warnings don't affect execution
- **Noise:** High - can clutter logs and output

## Suppression Methods

### Method 1: Suppress in `casa_init.py` (Implemented)

Added to `src/dsa110_contimg/utils/casa_init.py`:

```python
import warnings

# Suppress SWIG-generated deprecation warnings from casacore
warnings.filterwarnings(
    'ignore',
    category=DeprecationWarning,
    message=r'.*builtin type (SwigPyPacked|SwigPyObject|swigvarlink) has no __module__ attribute.*'
)
```

**Status:** ✅ Implemented

**Note:** Warnings emitted during module import time (in `<frozen importlib._bootstrap>`) may still appear because they're emitted before Python code runs. For complete suppression, use Method 2 or 3.

### Method 2: Command-Line Suppression (Recommended for Scripts)

Run Python scripts with:

```bash
python -W ignore::DeprecationWarning your_script.py
```

Or for casa6:

```bash
/opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning your_script.py
```

**Advantages:**
- Suppresses warnings at Python startup (before imports)
- Works for all DeprecationWarnings
- No code changes needed

**Disadvantages:**
- Must be specified for each script execution
- Suppresses ALL DeprecationWarnings (not just SWIG)

### Method 3: Environment Variable (Recommended for Development)

Set in shell profile (`.bashrc`, `.zshrc`):

```bash
export PYTHONWARNINGS="ignore::DeprecationWarning"
```

Or for casa6 specifically:

```bash
export PYTHONWARNINGS="ignore::DeprecationWarning"
alias casa6-python="/opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning"
```

**Advantages:**
- Applies to all Python sessions
- Suppresses warnings at startup
- No code changes needed

**Disadvantages:**
- Suppresses ALL DeprecationWarnings globally
- May hide important warnings

### Method 4: Context Manager (Selective)

```python
import warnings

with warnings.catch_warnings():
    warnings.simplefilter("ignore", DeprecationWarning)
    from casacore.images import image
    # ... CASA code
```

**Advantages:**
- Only suppresses warnings in specific code blocks
- Doesn't affect other code

**Disadvantages:**
- More verbose
- Requires wrapping every CASA import/usage
- May not catch import-time warnings

## Current Implementation

**Status:** ✅ Suppression added to `casa_init.py`

**Limitation:** Warnings emitted during module import (before Python code executes) may still appear. These are emitted by Python's import system itself, not by our code.

**Recommendation:** For complete suppression, use command-line flag (`-W ignore::DeprecationWarning`) or environment variable (`PYTHONWARNINGS="ignore::DeprecationWarning"`).

## Testing

To verify suppression works:

```bash
# Without suppression (warnings appear)
/opt/miniforge/envs/casa6/bin/python -c "from casatools import linearmosaic"

# With suppression (warnings suppressed)
/opt/miniforge/envs/casa6/bin/python -W ignore::DeprecationWarning -c "from casatools import linearmosaic"
```

## Future Fix

- SWIG 4.4+ includes fix for missing `__module__` attributes
- CASA will need to rebuild bindings with SWIG 4.4+ to eliminate warnings
- Until then, suppression is the practical solution

## References

- [SWIG Issue #2881](https://github.com/swig/swig/issues/2881)
- [Python warnings module](https://docs.python.org/3/library/warnings.html)
- [Suppressing SWIG warnings](https://github.com/amaiya/onprem/issues/93)
