# Common Pitfalls and Safeguards

## Overview

This document captures recurring mistakes discovered during development and validation, along with safeguards to prevent them in the future.

## Critical Pitfalls

### 1. Python Environment: Always Use casa6

**Mistake**: Using system Python (`python` or `python3`) instead of casa6 environment.

**Why It Matters**: 
- System Python (3.6.9) lacks CASA dependencies
- Pipeline WILL FAIL without casa6
- Required path: `/opt/miniforge/envs/casa6/bin/python`

**Safeguards**:
- ✅ **Makefile**: Always use `$(CASA6_PYTHON)` variable
- ✅ **Shell scripts**: Set `PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"`
- ✅ **Python scripts**: Add shebang `#!/opt/miniforge/envs/casa6/bin/python`
- ✅ **Validation**: Check `test -x /opt/miniforge/envs/casa6/bin/python || exit 1`

**Checklist**:
- [ ] Script has correct shebang
- [ ] Makefile uses `$(CASA6_PYTHON)`
- [ ] Shell scripts set `PYTHON_BIN` variable
- [ ] Documentation references casa6 path

---

### 2. Output Buffering: Always Use Unbuffered Mode

**Mistake**: Progress monitoring not visible because Python buffers stdout.

**Why It Matters**:
- Long-running operations appear hung
- Users can't see progress
- Debugging becomes difficult

**Safeguards**:
- ✅ **Python scripts**: Use `-u` flag: `python -u script.py`
- ✅ **Environment**: Set `PYTHONUNBUFFERED=1`
- ✅ **Code**: Use `sys.stdout.write()` + `sys.stdout.flush()` for critical messages
- ✅ **Shebang**: Can include `-u` in shebang: `#!/opt/miniforge/envs/casa6/bin/python -u`

**Checklist**:
- [ ] Script runs with `-u` flag or `PYTHONUNBUFFERED=1`
- [ ] Progress logging uses `sys.stdout.flush()`
- [ ] Long operations show progress indicators

**Example**:
```python
import sys
import os
os.environ['PYTHONUNBUFFERED'] = '1'

def log_progress(message: str):
    sys.stdout.write(f"[{timestamp}] {message}\n")
    sys.stdout.flush()
```

---

### 3. WCS Handling: Always Support 4D WCS

**Mistake**: Assuming 2D WCS (RA, Dec) when radio astronomy uses 4D (RA, Dec, Frequency, Stokes).

**Why It Matters**:
- Radio astronomy FITS files standardly use 4D WCS
- 2D-only code will fail with `TypeError` on 4D WCS
- Affects coordinate conversion, region masks, fitting

**Safeguards**:
- ✅ **Always check**: `if hasattr(wcs, 'naxis') and wcs.naxis == 4:`
- ✅ **Use**: `wcs.all_pix2world(x, y, 0, 0, 0)` for 4D (not `pixel_to_world_values`)
- ✅ **Use**: `wcs.all_world2pix([[ra, dec, 0, 0]], 0)` for 4D (not `wcs_world2pix`)
- ✅ **Test**: With real radio astronomy FITS files (not just 2D test data)

**Checklist**:
- [ ] WCS conversion checks for 4D
- [ ] Uses `all_pix2world`/`all_world2pix` for 4D
- [ ] Provides default frequency=0, stokes=0 for extra dimensions
- [ ] Tested with real DSA-110 FITS files

**Example**:
```python
if hasattr(wcs, 'naxis') and wcs.naxis == 4:
    # 4D WCS: RA, Dec, Frequency, Stokes
    world_coords = wcs.all_pix2world(x, y, 0, 0, 0)
    ra, dec = world_coords[0], world_coords[1]
else:
    # 2D WCS: RA, Dec
    sky_coord = wcs.pixel_to_world(x, y)
    ra, dec = sky_coord.ra.deg, sky_coord.dec.deg
```

---

### 4. Function Signatures: Always Check Before Calling

**Mistake**: Calling functions with wrong argument names/types (e.g., `x1, y1` vs `start_coord`, `end_coord`).

**Why It Matters**:
- Causes `TypeError: got unexpected keyword argument`
- Wastes debugging time
- Breaks validation scripts

**Safeguards**:
- ✅ **Before calling**: Read function signature/docstring
- ✅ **Use IDE**: Leverage autocomplete and type hints
- ✅ **Test**: Call functions in isolation first
- ✅ **Documentation**: Keep function signatures up-to-date

**Checklist**:
- [ ] Read function signature before calling
- [ ] Use named arguments (not positional) for clarity
- [ ] Test function calls in isolation
- [ ] Update docstrings when signatures change

**Example**:
```python
# BAD: Assumed signature
profile = extract_line_profile(fits_path, x1, y1, x2, y2)

# GOOD: Checked signature first
profile = extract_line_profile(
    fits_path,
    start_coord=(x1, y1),
    end_coord=(x2, y2),
    coordinate_system="pixel"
)
```

---

### 5. Non-Finite Values: Always Filter Before Fitting

**Mistake**: Passing NaN/Inf values to `astropy.modeling` fitters without filtering.

**Why It Matters**:
- Causes `NonFiniteValueError` from astropy
- Fitting operations fail unexpectedly
- Real astronomical data often contains NaN/Inf

**Safeguards**:
- ✅ **Always filter**: `finite_mask = np.isfinite(data)`
- ✅ **Check count**: `if np.sum(finite_mask) == 0: raise ValueError`
- ✅ **Apply mask**: Use `data[finite_mask]` for fitting
- ✅ **Log warnings**: Inform users about filtered values

**Checklist**:
- [ ] Filter non-finite values before fitting
- [ ] Check that filtered data has sufficient points
- [ ] Log warnings about filtered values
- [ ] Handle edge case of all-NaN data

**Example**:
```python
# Filter non-finite values
finite_mask = np.isfinite(fit_data)
if np.sum(finite_mask) == 0:
    raise ValueError("No finite values in data for fitting")

fit_data = fit_data[finite_mask]
fit_x = fit_x[finite_mask]
fit_y = fit_y[finite_mask]

# Now safe to fit
fitted_model = fitter(model, fit_x, fit_y, fit_data)
```

---

### 6. Performance: Test on Sub-Regions, Not Full Images

**Mistake**: Testing operations on full 6300x6300 images, causing 75+ second waits.

**Why It Matters**:
- Validation becomes impractical
- Can't iterate quickly
- Masks real performance issues

**Safeguards**:
- ✅ **Default to sub-regions**: Use 500x500 pixel sub-regions for testing
- ✅ **Full-image optional**: Only test full images when specifically needed
- ✅ **Progress monitoring**: Always show progress for operations > 1 second
- ✅ **Time limits**: Set timeouts for validation operations

**Checklist**:
- [ ] Use sub-regions (500x500) for initial testing
- [ ] Show progress for operations > 1 second
- [ ] Set reasonable timeouts
- [ ] Document performance characteristics

**Example**:
```python
# BAD: Full image (slow)
fit_result = fit_2d_gaussian(full_image_path, ...)

# GOOD: Sub-region (fast)
sub_size = min(500, nx // 4, ny // 4)
sub_data = data[y_min:y_max, x_min:x_max]
fit_result = fit_2d_gaussian(sub_region_path, ...)
```

---

### 7. Try/Finally Blocks: Structure Correctly

**Mistake**: Putting code after `finally` that should be inside `try` block.

**Why It Matters**:
- Code after `finally` executes even if `try` fails
- Can cause `NameError` if variables undefined
- Logic errors in error handling

**Safeguards**:
- ✅ **Structure**: All dependent code inside `try` block
- ✅ **Finally**: Only cleanup code (file deletion, resource release)
- ✅ **Variables**: Check if variables exist before using after `finally`
- ✅ **Test**: Test both success and failure paths

**Checklist**:
- [ ] All dependent code is inside `try` block
- [ ] `finally` only contains cleanup code
- [ ] Variables checked before use after `finally`
- [ ] Both success and failure paths tested

**Example**:
```python
# BAD: Code after finally
try:
    fit_result = fit_2d_gaussian(...)
finally:
    os.unlink(tmp_file)
if fit_result:  # ERROR: fit_result may not exist
    print("Success")

# GOOD: Code inside try
try:
    fit_result = fit_2d_gaussian(...)
    if fit_result:
        print("Success")
finally:
    os.unlink(tmp_file)
```

---

### 8. Import Order: Dependencies Before Usage

**Mistake**: Importing modules after setting environment variables or after they're needed.

**Why It Matters**:
- `PYTHONUNBUFFERED` must be set before imports
- Some modules need environment setup first
- Can cause subtle bugs

**Safeguards**:
- ✅ **Order**: Environment variables → Imports → Code
- ✅ **Shebang**: Can set environment in shebang
- ✅ **Check**: Verify imports work after environment setup
- ✅ **Document**: Note any special import requirements

**Checklist**:
- [ ] Environment variables set before imports
- [ ] Imports are at top of file (after env setup)
- [ ] No circular dependencies
- [ ] Special requirements documented

**Example**:
```python
#!/opt/miniforge/envs/casa6/bin/python -u
import os
os.environ['PYTHONUNBUFFERED'] = '1'  # BEFORE imports

import numpy as np
from astropy.io import fits
# ... rest of imports
```

---

### 9. Error Messages: Always Include Context

**Mistake**: Generic error messages without context (e.g., "Failed" instead of "Failed to fit Gaussian: ...").

**Why It Matters**:
- Harder to debug
- Users can't understand what went wrong
- Wastes time investigating

**Safeguards**:
- ✅ **Context**: Include operation name, parameters, file paths
- ✅ **Traceback**: Use `traceback.print_exc()` for debugging
- ✅ **User-friendly**: Separate user messages from debug info
- ✅ **Logging**: Use appropriate log levels

**Checklist**:
- [ ] Error messages include operation context
- [ ] Tracebacks logged for debugging
- [ ] User-friendly messages separate from debug info
- [ ] Important parameters included in errors

**Example**:
```python
# BAD
except Exception as e:
    print("Failed")

# GOOD
except Exception as e:
    logger.error(f"Failed to fit {model} to image {image_id}: {e}")
    logger.debug("Traceback:", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail=f"Failed to fit {model} to image {image_id}"
    )
```

---

### 10. Validation: Test Edge Cases

**Mistake**: Only testing happy path, missing edge cases (empty masks, all-NaN data, etc.).

**Why It Matters**:
- Edge cases cause failures in production
- Users encounter unexpected errors
- Harder to debug after deployment

**Safeguards**:
- ✅ **Edge cases**: Empty regions, all-NaN data, zero-size images
- ✅ **Boundary conditions**: Min/max values, empty lists
- ✅ **Error paths**: Invalid inputs, missing files
- ✅ **Documentation**: Document expected behavior for edge cases

**Checklist**:
- [ ] Test with empty regions/masks
- [ ] Test with all-NaN data
- [ ] Test with zero-size or invalid inputs
- [ ] Test error paths (missing files, invalid formats)
- [ ] Document expected behavior

**Example**:
```python
# Test edge cases
if n_pixels == 0:
    logger.warning("Region contains no valid pixels")
    return None  # or handle appropriately

if not np.any(np.isfinite(data)):
    raise ValueError("No finite values in data")
```

---

## Prevention Checklist

Before committing code, verify:

- [ ] **Python environment**: Uses casa6 Python
- [ ] **Output buffering**: Unbuffered mode enabled
- [ ] **WCS handling**: Supports 4D WCS
- [ ] **Function signatures**: Checked before calling
- [ ] **Non-finite values**: Filtered before fitting
- [ ] **Performance**: Tested on sub-regions first
- [ ] **Try/finally**: Correctly structured
- [ ] **Import order**: Environment before imports
- [ ] **Error messages**: Include context
- [ ] **Edge cases**: Tested and handled

## Automated Safeguards

Consider adding:

1. **Pre-commit hooks**: Check Python path, shebang
2. **Linting**: Enforce import order, check for common patterns
3. **Unit tests**: Test edge cases automatically
4. **Performance tests**: Fail if operations exceed thresholds
5. **Type checking**: Catch signature mismatches early

## Documentation Updates

When adding new code:

1. Document WCS dimensionality assumptions
2. Note performance characteristics
3. List edge cases handled
4. Include example usage
5. Document environment requirements

---

## Summary

The most critical safeguards are:
1. **Always use casa6 Python** (pipeline requirement)
2. **Always support 4D WCS** (radio astronomy standard)
3. **Always filter non-finite values** (astropy requirement)
4. **Always show progress** (user experience)
5. **Always test edge cases** (robustness)

These five safeguards prevent the majority of issues encountered during development.


