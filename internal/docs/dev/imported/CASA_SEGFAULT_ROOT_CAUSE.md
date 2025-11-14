# CASA6 Segfault Root Cause Analysis

## The Problem: X = `from dsa110_contimg.qa import create_cutout`

**Root Cause:** Importing `qa/__init__.py` triggers CASA initialization through the import chain.

## Import Chain That Triggers Segfault

```
from dsa110_contimg.qa import create_cutout
  ↓
qa/__init__.py imports:
  ↓
from dsa110_contimg.qa.visualization import CasaTable
  ↓
qa/visualization/__init__.py imports:
  ↓
from dsa110_contimg.qa.visualization.casatable import CasaTable
  ↓
qa/visualization/casatable.py:
  ↓
from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()  # Sets CASAPATH
  ↓
from casacore.tables import table  # MODULE-LEVEL IMPORT
  ↓
casacore initializes → triggers casatools initialization
  ↓
casatools/__casac__/_measures.so initializes
  ↓
SEGFAULT in PyInit__measures
```

## The Exact Trigger

**File:** `src/dsa110_contimg/qa/visualization/casatable.py`

**Lines 22-27:**
```python
# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()

try:
    from casacore.tables import table  # ← MODULE-LEVEL CASA IMPORT
    HAS_CASACORE = True
```

**Problem:** `casatable.py` imports CASA at **module level**, not lazily. When `qa/__init__.py` imports `CasaTable`, it triggers CASA initialization immediately.

## Why It Segfaults

1. **CASA6 Environment Issue:** The segfault occurs in `casatools/__casac__/_measures.so` during `PyInit__measures`
2. **Threading Issue:** Backtrace shows `libpthread.so.0` involvement, suggesting threading/initialization race condition
3. **Memory Issue:** "address not mapped to object at address 0x20" suggests uninitialized pointer

## Solutions

### Option 1: Lazy Import in casatable.py (Recommended)

**Change casatable.py to use lazy imports:**

```python
# Remove module-level import
# from casacore.tables import table  # ❌ REMOVE THIS

HAS_CASACORE = None  # Will be set lazily

def _get_table():
    """Lazy import of casacore.tables."""
    global HAS_CASACORE, table
    if HAS_CASACORE is None:
        from dsa110_contimg.utils.casa_init import ensure_casa_path
        ensure_casa_path()
        try:
            from casacore.tables import table
            HAS_CASACORE = True
        except ImportError:
            HAS_CASACORE = False
            table = None
    return table if HAS_CASACORE else None
```

### Option 2: Lazy Import in qa/__init__.py

**Change qa/__init__.py to import CasaTable lazily:**

```python
# Remove from top-level imports
# from dsa110_contimg.qa.visualization import CasaTable  # ❌ REMOVE

# Add lazy import function
def _get_casa_table():
    """Lazy import of CasaTable to avoid CASA initialization."""
    from dsa110_contimg.qa.visualization.casatable import CasaTable
    return CasaTable

# Or use __getattr__ for lazy module-level access
def __getattr__(name):
    if name == 'CasaTable':
        from dsa110_contimg.qa.visualization.casatable import CasaTable
        return CasaTable
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

### Option 3: Direct Import (Workaround)

**For VAST Tools code, import directly:**

```python
# ✅ Safe - bypasses qa/__init__.py
from dsa110_contimg.qa.postage_stamps import create_cutout

# ❌ Triggers segfault - imports qa/__init__.py
from dsa110_contimg.qa import create_cutout
```

## Verification

**Test the fix:**
```python
# Should NOT trigger CASA initialization
from dsa110_contimg.qa.postage_stamps import create_cutout
from dsa110_contimg.qa import create_cutout  # Should also work after fix
```

## Summary

**X = `from dsa110_contimg.qa import create_cutout`**

**Why:** This imports `qa/__init__.py` → imports `qa.visualization.CasaTable` → imports `casatable.py` → module-level `from casacore.tables import table` → CASA initialization → segfault

**Fix:** Make CASA imports lazy in `casatable.py` or `qa/__init__.py`

## External References & Known Issues

### CASA6 Segfault Issues (From Web Research)

1. **PyInit__measures Segfault:**
   - Known CASA6 initialization issue with `casatools/__casac__/_measures.so`
   - Can be triggered by environment variables (PYTHONSTARTUP), SELinux settings, or library conflicts
   - **Source:** [CASA Documentation](https://casadocs.readthedocs.io/en/v6.6.0/notebooks/introduction.html)

2. **Module-Level Import Segfaults:**
   - Common issue with Python C++ bindings (like CASA6) during module initialization
   - Threading/initialization race conditions can cause segfaults
   - **Solution:** Use lazy imports instead of module-level imports
   - **Source:** Multiple GitHub issues on Python/C++ threading segfaults

3. **casacore.tables Import Issues:**
   - Known segfaults when importing `casacore.tables` at module level
   - Related to Dysco compression support and lazy loading issues
   - **Workaround:** Explicit early imports or disable problematic features
   - **Source:** [python-casacore GitHub Issues](https://github.com/casacore/python-casacore/issues)

4. **Threading & Initialization Order:**
   - C++/Python bindings can segfault due to threading initialization order
   - Symbol conflicts between libraries loaded in wrong order
   - **Solution:** Import CASA6 before other conflicting libraries
   - **Source:** PyTorch, NumPy, and other C++ binding segfault reports

### Recommended Solutions (From Research)

1. **Lazy Imports (Best Practice):**
   ```python
   # ❌ Bad - module-level import
   from casacore.tables import table
   
   # ✅ Good - lazy import
   def get_table():
       from casacore.tables import table
       return table
   ```

2. **Environment Cleanup:**
   - Unset `PYTHONSTARTUP` before running CASA6
   - Check SELinux status (should be permissive/disabled)
   - Run from clean directory without conflicting files

3. **Import Order:**
   - Import CASA6 modules before other libraries that might conflict
   - Avoid mixing debug and non-debug binaries

4. **Version Updates:**
   - Upgrade to latest CASA6/python-casacore versions
   - Many import-related segfaults have been fixed in newer releases

### References

- [CASA Release Notes](https://casadocs.readthedocs.io/en/v6.6.0/notebooks/introduction.html)
- [python-casacore Issues](https://github.com/casacore/python-casacore/issues)
- [CASA GitLab Issues](https://git.astron.nl/RD/rapthor/-/issues/4) - Dysco compression segfaults
- [Python C++ Binding Segfault Patterns](https://github.com/pytorch/pytorch/issues/78829) - Import order issues

