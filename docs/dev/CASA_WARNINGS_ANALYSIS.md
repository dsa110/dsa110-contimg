# CASA Warnings Analysis and Fixes

**Date:** 2025-11-10  
**Status:** Actionable fixes identified  
**Priority:** Medium (warnings don't break functionality but should be addressed)

---

## Summary

During mosaic building, CASA produces several warnings that are actionable:

1. **FITS CDELT format warning**: FITS cards written with high precision that don't conform to FITS fixed format
2. **Observatories table missing**: CASA cannot find the Observatories data table due to missing CASAPATH environment variable

---

## Issue 1: FITS CDELT Format Warning

### Symptom
```
INFO: FITS card 27: CDELT1  = -0.000555555555555556
INFO: Numeric value does not conform to FITS fixed format.
```

### Root Cause
FITS images are written with CDELT values using high precision (16+ decimal places). CASA's FITS reader expects values in FITS "fixed format" which has specific formatting requirements.

**Current CDELT values:**
- CDELT1: -0.000555555555555556 (2 arcsec/pixel = 2/3600 degrees)
- CDELT2: 0.000555555555555556

### Impact
- **Severity:** Low - CASA can still read the images correctly
- **Effect:** Cosmetic warning only, no functional impact
- **Frequency:** Every time CASA reads a FITS image

### Fix Options

**Option A: Round CDELT values when writing FITS (Recommended)**
- Round to 8-10 decimal places when writing FITS headers
- Ensures FITS format compliance
- Minimal code changes needed

**Option B: Ignore (Current approach)**
- Warnings are harmless
- No code changes needed
- Acceptable for now

**Recommended:** Implement Option A in image writing code (e.g., `imaging/cli_imaging.py`, `mosaic/cli.py`)

---

## Issue 2: Observatories Table Missing

### Symptom
```
WARN: MeasIERS::findTab - Requested data table Observatories cannot be found
SEVERE: MeasTable::doInitObservatories() - Cannot read table of Observatories
WARN: ObsInfo::setTelescope - Cannot read table of Observatories, continuing without telescope position
```

### Root Cause
CASA's `casacore.measures` module cannot find the Observatories data table because:
1. `CASAPATH` environment variable is not set
2. CASA searches in hardcoded paths that don't exist:
   - `/opt/miniforge/envs/casa6/lib/python3.11/site-packages/casacore/data/geodetic/` (missing)
   - `/opt/miniforge/envs/casa6/lib/casa/data/geodetic/` (missing)

**Actual location:**
- `/opt/miniforge/envs/casa6/share/casa/data/geodetic/Observatories` (exists)
- `/opt/miniforge/envs/casa6/lib/python3.11/site-packages/casadata/__data__/geodetic/Observatories` (exists)

### Impact
- **Severity:** Medium - Telescope position information unavailable
- **Effect:** 
  - ObsInfo cannot set telescope position
  - May affect coordinate transformations that depend on observatory location
  - Most imaging operations work fine without this
- **Frequency:** Every time CASA initializes measures/coordinates

### Fix

**Set CASAPATH environment variable:**

```bash
export CASAPATH=/opt/miniforge/envs/casa6/share/casa
```

**Or in Python before importing CASA:**

```python
import os
os.environ['CASAPATH'] = '/opt/miniforge/envs/casa6/share/casa'
```

**Recommended locations to set this:**
1. System-wide: `/etc/environment` or shell profile (`.bashrc`, `.profile`)
2. Pipeline scripts: Set in `scripts/` or `ops/` startup scripts
3. Python code: Set before importing CASA modules (e.g., in `conftest.py`, `__init__.py`)

---

## Implementation Plan

### Priority 1: Fix Observatories Table (Medium Priority)
1. Add `CASAPATH` to environment setup
2. Update pipeline startup scripts
3. Set in Python before CASA imports
4. Test that warnings disappear

### Priority 2: Fix FITS CDELT Format (Low Priority)
1. Identify all FITS writing code paths
2. Add CDELT rounding/formatting
3. Test FITS compliance
4. Verify CASA can still read images correctly

---

## Testing

After implementing fixes:

```bash
# Test Observatories fix
python -c "
import os
os.environ['CASAPATH'] = '/opt/miniforge/envs/casa6/share/casa'
from casacore.measures import measures
dm = measures()
# Should not produce Observatories warnings
"

# Test FITS format fix
# Read/write a test image and check for CDELT warnings
```

---

## References

- CASA Data Directory: `/opt/miniforge/envs/casa6/share/casa/data/`
- FITS Standard: https://fits.gsfc.nasa.gov/fits_standard.html
- CASA Measures Documentation: https://casa.nrao.edu/docs/casaref/measures.html

---

**Last Updated:** 2025-11-10

