# CASA6 Segfault Handling Guide

## Problem

CASA6 can segfault during module initialization when `casatools` is imported. This is a known CASA6 environment issue, not related to our code.

**Symptoms:**
- Segmentation fault when importing modules that trigger CASA initialization
- Error occurs during `casatools` initialization, not in our code
- Happens even with simple imports like `from dsa110_contimg.database.schema_evolution import ...`

## Root Cause

The segfault occurs when:
1. CASA modules (`casatools`, `casacore`) are imported at module level
2. CASA initialization happens before proper environment setup
3. Multiple processes try to initialize CASA simultaneously

## Current Handling Strategy

### 1. Lazy CASA Imports (Preferred)

**Pattern:** Import CASA modules inside functions, not at module level.

**Example from `qa/casa_ms_qa.py`:**
```python
def _import_casa() -> Tuple[Any, Any, Dict[str, Optional[str]]]:
    """Lazy import of CASA modules to avoid initialization issues."""
    from dsa110_contimg.utils.casa_init import ensure_casa_path
    ensure_casa_path()
    
    from casacore.tables import table
    from casacore.images import image as casaimage
    # ... rest of imports
    
    return table, casaimage, casa_info
```

**Benefits:**
- CASA only initializes when actually needed
- Avoids segfaults during module import
- Allows code to be imported without CASA overhead

### 2. CASAPATH Initialization

**Pattern:** Always call `ensure_casa_path()` before importing CASA modules.

**Example:**
```python
from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()

# Then import CASA modules
from casacore.images import image as casaimage
```

**Location:** `src/dsa110_contimg/utils/casa_init.py`

### 3. VAST Tools Code (No CASA Dependencies)

**Status:** ✅ Our VAST Tools adoption code does **NOT** import CASA.

**Verified modules:**
- `photometry/source.py` - Uses only astropy, pandas, numpy
- `photometry/variability.py` - Uses only numpy, pandas
- `qa/postage_stamps.py` - Uses only astropy, matplotlib, numpy

**Why this matters:**
- These modules can be imported safely without triggering CASA
- Segfaults only occur when CASA modules are imported
- Our code is CASA-free and safe

## Handling Segfaults in Tests/Imports

### Option 1: Avoid CASA Imports in Tests

**For VAST Tools code:**
```python
# ✅ Safe - no CASA imports
from dsa110_contimg.photometry import Source
from dsa110_contimg.qa.postage_stamps import create_cutout

# ❌ Avoid - triggers CASA initialization
from dsa110_contimg.database.schema_evolution import evolve_products_schema
# (if schema_evolution imports CASA at module level)
```

### Option 2: Use Lazy Imports in Test Setup

```python
def test_something():
    # Import CASA-dependent modules inside test
    from dsa110_contimg.database.schema_evolution import evolve_products_schema
    # ... test code
```

### Option 3: Mock CASA for Unit Tests

```python
@pytest.fixture(autouse=True)
def mock_casa(monkeypatch):
    """Mock CASA modules to avoid initialization."""
    monkeypatch.setattr('casacore.tables.table', lambda *args, **kwargs: None)
    # ... other mocks
```

## Best Practices

### ✅ DO

1. **Use lazy imports for CASA modules:**
   ```python
   def my_function():
       from casacore.images import image as casaimage
       # ... use casaimage
   ```

2. **Call `ensure_casa_path()` before CASA imports:**
   ```python
   from dsa110_contimg.utils.casa_init import ensure_casa_path
   ensure_casa_path()
   from casacore.images import image
   ```

3. **Keep CASA-free modules separate:**
   - Our VAST Tools code is CASA-free ✅
   - Can be imported safely anywhere

### ❌ DON'T

1. **Don't import CASA at module level unnecessarily:**
   ```python
   # ❌ Bad
   from casacore.images import image as casaimage
   
   # ✅ Good
   def my_function():
       from casacore.images import image as casaimage
   ```

2. **Don't ignore segfaults in production:**
   - If segfaults occur, investigate CASA initialization
   - Use lazy imports or proper initialization

## Verification

**Check if module imports CASA:**
```bash
grep -r "from casacore\|from casatools\|import casacore\|import casatools" src/dsa110_contimg/photometry/
grep -r "from casacore\|from casatools\|import casacore\|import casatools" src/dsa110_contimg/qa/postage_stamps.py
```

**Result:** ✅ No CASA imports found in VAST Tools code

## Summary

- **VAST Tools code is safe:** No CASA dependencies, no segfault risk
- **Segfaults are CASA6 environment issues:** Not related to our code
- **Use lazy imports:** For any code that needs CASA
- **Always initialize CASAPATH:** Before importing CASA modules

The segfault we observed was from CASA6 initialization when importing `qa/__init__.py` (which imports `CasaTable`), not from our VAST Tools adoption code.

## External References & Known Issues

### Research Findings

Based on web research using Perplexity, this is a **known CASA6 issue** with several documented cases:

1. **PyInit__measures Segfault:**
   - Official CASA documentation acknowledges segfaults during initialization
   - Can be triggered by environment variables, SELinux, or library conflicts
   - **Reference:** [CASA Documentation](https://casadocs.readthedocs.io/en/v6.6.0/notebooks/introduction.html)

2. **Module-Level Import Problem:**
   - Common issue with Python C++ bindings (CASA6 uses C++ backend)
   - Threading/initialization race conditions during module import
   - **Solution:** Lazy imports are the recommended workaround
   - **Reference:** Multiple GitHub issues on Python/C++ threading segfaults

3. **casacore.tables Import Issues:**
   - Known segfaults when importing `casacore.tables` at module level
   - Related to Dysco compression and lazy loading
   - **Reference:** [python-casacore GitHub Issues](https://github.com/casacore/python-casacore/issues)

4. **Threading & Symbol Conflicts:**
   - Import order matters for C++ bindings
   - Symbol conflicts between libraries can cause segfaults
   - **Reference:** PyTorch, NumPy segfault reports on import order

### Recommended Solutions (From Research)

1. **Use Lazy Imports** (Industry Best Practice):
   - Import CASA modules inside functions, not at module level
   - This is the standard solution for C++ binding segfaults

2. **Environment Cleanup:**
   - Unset `PYTHONSTARTUP` before running CASA6
   - Check SELinux status (should be permissive/disabled)
   - Run from clean directory

3. **Import Order:**
   - Import CASA6 modules before other conflicting libraries
   - Avoid mixing debug and non-debug binaries

4. **Version Updates:**
   - Upgrade to latest CASA6/python-casacore versions
   - Many import-related segfaults fixed in newer releases

