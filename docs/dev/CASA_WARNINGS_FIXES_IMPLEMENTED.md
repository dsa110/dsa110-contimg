# CASA Warnings Fixes - Implementation Summary

**Date:** 2025-11-10  
**Status:** Implemented  
**Priority:** High

---

## Summary

Both CASA warnings have been addressed with high-priority fixes:

1. **FITS CDELT Format Warning** - Fixed by rounding CDELT values when writing FITS headers
2. **Observatories Table Missing** - Fixed by setting CASAPATH environment variable before CASA imports

---

## Implementation Details

### 1. CASA Initialization Utility

**File:** `src/dsa110_contimg/utils/casa_init.py`

- Automatically sets `CASAPATH` environment variable if not already set
- Searches common CASA installation paths
- Verifies geodetic data exists before setting
- Should be imported before any CASA modules

**Usage:**
```python
from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()
# Now safe to import CASA modules
from casatasks import ...
```

### 2. FITS Format Utilities

**File:** `src/dsa110_contimg/utils/fits_utils.py`

- `format_fits_header_value()`: Rounds values to 10 decimal places
- `fix_cdelt_in_header()`: Fixes CDELT1/CDELT2 values in existing headers
- `create_fits_hdu()`: Creates PrimaryHDU with properly formatted header
- `write_fits()`: Convenience function for writing FITS files

**Usage:**
```python
from dsa110_contimg.utils.fits_utils import create_fits_hdu

header = wcs.to_header()
hdu = create_fits_hdu(data=image_data, header=header, fix_cdelt=True)
hdu.writeto(output_path, overwrite=True)
```

---

## Files Modified

### CASA Initialization Added To:
1. `src/dsa110_contimg/mosaic/cli.py`
2. `src/dsa110_contimg/imaging/cli_imaging.py`
3. `src/dsa110_contimg/imaging/cli.py`
4. `src/dsa110_contimg/calibration/calibration.py`

### FITS Format Fixes Applied To:
1. `src/dsa110_contimg/calibration/skymodel_image.py`
   - Fixed: `create_skymodel_image()` function
   
2. `src/dsa110_contimg/imaging/nvss_tools.py`
   - Fixed: `create_nvss_mask()` function (2 locations)

---

## Testing

### CASA Initialization Test
```python
from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()
# CASAPATH should be set to /opt/miniforge/envs/casa6/share/casa
```

### FITS Format Test
```python
from dsa110_contimg.utils.fits_utils import format_fits_header_value

# Before: -0.000555555555555556 (16+ decimal places)
# After:  -0.0005555556 (10 decimal places)
formatted = format_fits_header_value(-0.000555555555555556)
```

---

## Expected Results

### Before Fixes:
```
INFO: FITS card 27: CDELT1  = -0.000555555555555556
INFO: Numeric value does not conform to FITS fixed format.
WARN: MeasIERS::findTab - Requested data table Observatories cannot be found
SEVERE: MeasTable::doInitObservatories() - Cannot read table of Observatories
```

### After Fixes:
- No FITS format warnings (CDELT values rounded to 10 decimal places)
- No Observatories warnings (CASAPATH set correctly)
- CASA measures module initializes cleanly

---

## Remaining Work

### Additional CASA Import Locations
The following files import CASA but may not have initialization yet:
- `calibration/cli_calibrate.py`
- `imaging/export.py`
- `pipeline/stages_impl.py`
- `qa/visualization/casatable.py`
- `utils/ms_helpers.py`
- `conversion/uvh5_to_ms.py`

**Note:** These are lower priority as they may import CASA conditionally or in functions. The main entry points (CLI modules) are fixed.

### Additional FITS Writing Locations
Other files that write FITS may need updates:
- Files using `exportfits` from CASA (handled by CASA, but may need header fixes)
- Any other direct FITS writing code

---

## Verification

To verify fixes are working:

1. **Run mosaic build** - Should see reduced/eliminated warnings
2. **Check FITS headers** - CDELT values should be rounded to 10 decimal places
3. **Check CASAPATH** - Should be set before CASA imports

```bash
# Test CASA initialization
python -c "from dsa110_contimg.utils.casa_init import ensure_casa_path; ensure_casa_path(); import os; print(os.getenv('CASAPATH'))"

# Test FITS formatting
python -c "from dsa110_contimg.utils.fits_utils import format_fits_header_value; print(format_fits_header_value(-0.000555555555555556))"
```

---

**Last Updated:** 2025-11-10

