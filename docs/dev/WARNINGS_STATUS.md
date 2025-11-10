# Warnings Encountered During Testing - Status

## Summary of All Warnings

### 1. FITS CDELT Format Warning ✓ FIXED
**Status:** Fully addressed

**Symptom:**
```
INFO: FITS card 27: CDELT1  = -0.000555555555555556
INFO: Numeric value does not conform to FITS fixed format.
```

**Root Cause:** FITS headers written with high-precision CDELT values (16+ decimal places)

**Fix Applied:**
- Created `utils/fits_utils.py` with `create_fits_hdu()` function
- Rounds CDELT1/CDELT2 to 10 decimal places
- Integrated into:
  - `calibration/skymodel_image.py` ✓
  - `imaging/nvss_tools.py` ✓ (2 locations)

**Remaining:** None - all image FITS writing uses `create_fits_hdu()`

**Note:** `photometry/aegean_fitting.py` writes `BinTableHDU` (binary table, not image), so no CDELT values - this is correct.

---

### 2. Observatories Table Missing Warning ✓ FIXED
**Status:** Fully addressed

**Symptom:**
```
WARN: MeasIERS::findTab - Requested data table Observatories cannot be found
SEVERE: MeasTable::doInitObservatories() - Cannot read table of Observatories
WARN: ObsInfo::setTelescope - Cannot read table of Observatories, continuing without telescope position
```

**Root Cause:** `CASAPATH` environment variable not set before CASA imports

**Fix Applied:**
- Created `utils/casa_init.py` with `ensure_casa_path()` function
- Sets `CASAPATH` to `/opt/miniforge/envs/casa6/share/casa` before CASA imports
- Added to **58 files** that import CASA modules ✓

**Remaining:** None - systematic fix applied across codebase

---

### 3. CASA API Errors ✓ FIXED
**Status:** Fully addressed

**Errors Encountered:**
- `AttributeError: 'image' object has no attribute 'close'`
- `AttributeError: 'image' object has no attribute 'coordsys'`
- `TypeError: image.__init__() missing 1 required positional argument: 'imagename'`

**Root Cause:** Incorrect usage of `casacore.images.image` API

**Fix Applied:**
- Replaced `img.close()` → `del img` (4 locations)
- Replaced `img.coordsys()` → `img.coordinates()` (4 locations)
- Fixed `casaimage()` constructor usage (1 location)
- Files fixed:
  - `mosaic/cli.py` ✓
  - `mosaic/post_validation.py` ✓
  - `mosaic/cache.py` ✓
  - `mosaic/validation.py` ✓

**Remaining:** None - all API calls corrected

**Note:** `casatools.image().close()` calls in `api/batch_jobs.py` are correct (different API) ✓

---

### 4. imregrid RuntimeError ✓ HANDLED
**Status:** Gracefully handled with error recovery

**Symptom:**
```
RuntimeError: Exception: All output pixels are masked.
```

**Root Cause:** Regridding operation results in all pixels masked (tile outside valid region)

**Fix Applied:**
- Added try/except blocks around `imregrid` calls
- Skip tiles that fail regridding
- Fall back to noise-weighted combination if PB regridding fails
- Log warnings for failed tiles (intentional - user should know)

**Remaining:** None - error handling in place

**Note:** Warnings logged are intentional and correct - they inform users about skipped tiles.

---

### 5. immath overwrite Parameter ✓ FIXED
**Status:** Fully addressed

**Symptom:**
```
TypeError: _immath.__call__() got an unexpected keyword argument 'overwrite'
```

**Root Cause:** `casatasks.immath` doesn't support `overwrite` parameter

**Fix Applied:**
- Removed `overwrite=True` from all `immath` calls
- Added explicit `shutil.rmtree()` before `immath` to remove existing outputs
- Files fixed:
  - `mosaic/cli.py` ✓ (multiple locations)

**Remaining:** None - all `immath` calls corrected

---

## Verification Status

### Files Checked
- ✓ All FITS image writing uses `create_fits_hdu()` with `fix_cdelt=True`
- ✓ All CASA-importing files have `ensure_casa_path()` initialization
- ✓ All `.coordsys()` calls replaced with `.coordinates()`
- ✓ All `casaimage.close()` calls replaced with `del`
- ✓ All `immath` calls have `overwrite` parameter removed
- ✓ All `imregrid` calls have error handling

### Remaining Issues
**None** - All warnings and errors encountered during testing have been addressed.

---

## Testing Recommendations

1. **Run full mosaic build** - Should see no CASA warnings
2. **Check FITS headers** - CDELT values should be rounded to 10 decimal places
3. **Verify image operations** - All CASA image operations should work correctly
4. **Monitor logs** - Only intentional warnings (skipped tiles) should appear

---

## Notes

- `photometry/aegean_fitting.py` writes binary tables, not images, so no CDELT fix needed ✓
- `casatools.image().close()` calls are correct and were not modified ✓
- Intentional warnings for skipped tiles are logged correctly ✓

