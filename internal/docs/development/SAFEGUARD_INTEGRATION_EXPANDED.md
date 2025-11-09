# Expanded Safeguard Integration Plan

## Overview

This document identifies **all** locations in the pipeline where runtime safeguards should be integrated, beyond the initial analysis tools.

---

## Category 1: WCS Conversion Safeguards

### High Priority: Files with Manual WCS Handling

#### 1. `qa/catalog_validation.py` (CRITICAL)
**Issues Found**:
- Lines ~201, ~274, ~341, ~505, ~740: Manual `wcs.wcs_pix2world()` and `wcs.wcs_world2pix()` calls
- No 4D WCS handling
- No error handling for WCS failures

**Functions to Update**:
- `find_local_maxima()` - line ~201
- `convert_catalog_to_pixels()` - line ~274
- `get_image_center_wcs()` - line ~341
- `validate_catalog_coverage()` - line ~505
- `validate_catalog_flux_scaling()` - line ~740

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import (
    validate_wcs_4d,
    wcs_pixel_to_world_safe,
    wcs_world_to_pixel_safe,
)

# Replace manual calls with:
wcs, is_4d, defaults = validate_wcs_4d(wcs)
ra, dec = wcs_pixel_to_world_safe(wcs, x, y, is_4d, defaults)
x, y = wcs_world_to_pixel_safe(wcs, ra, dec, is_4d, defaults)
```

---

#### 2. `mosaic/cli.py` (HIGH)
**Issues Found**:
- Line ~612: `wcs.pixel_to_world_values()` for corner calculations
- No 4D WCS handling

**Functions to Update**:
- `_get_image_corners()` or similar function around line ~595

**Safeguards to Add**:
```python
wcs, is_4d, defaults = validate_wcs_4d(wcs)
corners_world = [
    wcs_pixel_to_world_safe(wcs, c[1], c[0], is_4d, defaults)
    for c in corners_pix
]
```

---

#### 3. `calibration/skymodel_image.py` (MEDIUM)
**Issues Found**:
- WCS conversions for sky model generation
- May have 4D WCS issues

**Safeguards to Add**:
- Same pattern as above

---

## Category 2: Non-Finite Value Safeguards

### High Priority: Files with Numerical Operations

#### 4. `photometry/adaptive_photometry.py` (HIGH)
**Issues Found**:
- Likely has numerical operations that could produce NaN/Inf
- Fitting operations that need clean data

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import (
    filter_non_finite_2d,
    validate_numerical_data,
)

# Before fitting/statistics:
data = validate_numerical_data(data, min_finite_ratio=0.5)
```

---

#### 5. `photometry/forced.py` (HIGH)
**Issues Found**:
- FITS file operations
- Flux calculations that could have non-finite values

**Safeguards to Add**:
- Filter non-finite values before flux calculations
- Validate data before statistics

---

#### 6. `mosaic/` modules (MEDIUM)
**Issues Found**:
- Multiple files with numerical operations
- Mosaic combination operations need clean data

**Files to Check**:
- `mosaic/cli.py`
- `mosaic/validation.py`
- `mosaic/streaming_mosaic.py`
- `mosaic/post_validation.py`

**Safeguards to Add**:
- Validate data before mosaic operations
- Filter non-finite values in combination logic

---

#### 7. `qa/image_quality.py` (MEDIUM)
**Issues Found**:
- Image quality metrics calculations
- Statistics that could fail on non-finite data

**Safeguards to Add**:
- Filter non-finite values before quality calculations
- Validate data before statistics

---

## Category 3: CASA Environment Safeguards

### Critical: Files that Require CASA

#### 8. `imaging/cli_imaging.py` (CRITICAL)
**Issues Found**:
- Lines ~13-17: Imports `casatools`
- Critical imaging operations require CASA

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import require_casa6_python

@require_casa6_python
def critical_imaging_function(...):
    from casatools import vpmanager, msmetadata
    # ... function code ...
```

**Functions to Protect**:
- All functions that use CASA tools
- Main imaging pipeline functions

---

#### 9. `conversion/ms_utils.py` (CRITICAL)
**Issues Found**:
- Lines ~251, ~581: Uses `casatasks.initweights`
- Critical MS conversion operations

**Safeguards to Add**:
```python
@require_casa6_python
def configure_ms_for_imaging(...):
    # Uses casatasks.initweights
    ...
```

**Functions to Protect**:
- `configure_ms_for_imaging()` - line ~580
- `_initialize_weight_spectrum()` - line ~251

---

#### 10. `conversion/merge_spws.py` (HIGH)
**Issues Found**:
- Line ~127: Uses `casatools.table`
- MS manipulation operations

**Safeguards to Add**:
```python
@require_casa6_python
def merge_spws(...):
    from casatools import table as casa_table
    # ... function code ...
```

---

#### 11. `conversion/helpers_telescope.py` (MEDIUM)
**Issues Found**:
- Line ~21: Imports `casatools`
- Telescope configuration functions

**Safeguards to Add**:
- Add `@require_casa6_python` to CASA-dependent functions

---

#### 12. `pipeline/stages_impl.py` (CRITICAL)
**Issues Found**:
- Multiple pipeline stages use CASA
- Critical pipeline operations

**Classes to Protect**:
- `ConversionStage` - line ~26
- `CalibrationSolveStage` - line ~264
- `CalibrationStage` - line ~691
- `ImagingStage` - line ~894
- `ValidationStage` - line ~1302
- `AdaptivePhotometryStage` - line ~1452

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import require_casa6_python

class ImagingStage(PipelineStage):
    @require_casa6_python
    def run(self, ...):
        # Uses CASA for imaging
        ...
```

---

## Category 4: Progress Monitoring Safeguards

### High Priority: Long-Running Operations

#### 13. `pipeline/stages_impl.py` (CRITICAL)
**Issues Found**:
- All pipeline stages are long-running
- No progress monitoring

**Safeguards to Add**:
```python
from dsa110_contimg.utils.runtime_safeguards import (
    progress_monitor,
    log_progress,
)

class ConversionStage(PipelineStage):
    @progress_monitor(operation_name="UVH5 to MS Conversion", warn_threshold=300.0)
    def run(self, ...):
        log_progress("Starting conversion...")
        # ... conversion code ...
        log_progress("Conversion complete", start_time)
```

**Stages to Update**:
- `ConversionStage.run()` - UVH5 to MS conversion (long)
- `CalibrationSolveStage.run()` - Calibration solving (long)
- `CalibrationStage.run()` - Calibration application (long)
- `ImagingStage.run()` - Imaging (very long)
- `AdaptivePhotometryStage.run()` - Photometry (long)

---

#### 14. `conversion/uvh5_to_ms.py` (HIGH)
**Issues Found**:
- Line ~956: `convert_single_file()` - long operation
- Line ~1170: `convert_directory()` - very long operation
- No progress monitoring

**Safeguards to Add**:
```python
@progress_monitor(operation_name="UVH5 File Conversion", warn_threshold=60.0)
def convert_single_file(...):
    log_progress(f"Converting {input_file}...")
    # ... conversion code ...
    log_progress(f"Completed {input_file}", start_time)
```

---

#### 15. `mosaic/streaming_mosaic.py` (HIGH)
**Issues Found**:
- Mosaic operations are long-running
- No progress monitoring

**Safeguards to Add**:
- Add `@progress_monitor` to mosaic functions
- Add `log_progress()` calls throughout

---

#### 16. `photometry/adaptive_photometry.py` (MEDIUM)
**Issues Found**:
- Adaptive photometry can be slow
- No progress monitoring

**Safeguards to Add**:
- Add `@progress_monitor` to slow functions
- Add `log_progress()` calls

---

## Category 5: FITS File Operation Safeguards

### Medium Priority: Files with FITS Operations

#### 17. `imaging/export.py` (MEDIUM)
**Issues Found**:
- FITS file reading/writing
- Could benefit from validation

**Safeguards to Add**:
- Validate FITS files before operations
- Check for non-finite values in data

---

#### 18. `photometry/aegean_fitting.py` (MEDIUM)
**Issues Found**:
- Line ~481: FITS file reading
- Aegean output parsing

**Safeguards to Add**:
- Validate FITS structure before reading
- Check for expected extensions

---

#### 19. `qa/html_reports.py` (LOW)
**Issues Found**:
- FITS file reading for reports
- Less critical, but could benefit

**Safeguards to Add**:
- Basic FITS validation

---

## Category 6: Input Validation Safeguards

### Medium Priority: API and CLI Entry Points

#### 20. `api/routes.py` (HIGH)
**Issues Found**:
- API endpoints need input validation
- Already identified for progress monitoring

**Additional Safeguards**:
- Validate image IDs exist
- Validate region coordinates
- Validate fit parameters

---

#### 21. `api/batch_jobs.py` (MEDIUM)
**Issues Found**:
- Batch job submission
- Could benefit from validation

**Safeguards to Add**:
- Validate job parameters
- Check resource availability

---

#### 22. CLI modules (MEDIUM)
**Issues Found**:
- Multiple CLI modules
- Input validation needed

**Files to Check**:
- `imaging/cli.py`
- `photometry/cli.py`
- `mosaic/cli.py`
- `calibration/cli_calibrate.py`

**Safeguards to Add**:
- Validate file paths exist
- Validate parameters are in valid ranges
- Check required dependencies

---

## Category 7: Parallel Processing Safeguards

### Low Priority: Files with Parallel Operations

#### 23. `utils/parallel.py` (LOW)
**Issues Found**:
- Parallel processing utilities
- Could benefit from progress monitoring

**Safeguards to Add**:
- Progress monitoring for parallel operations
- Error handling for worker failures

---

## Integration Priority Summary

### Phase 1: Critical Pipeline Operations (WEEK 1)
1. ✅ `pipeline/stages_impl.py` - Add `@require_casa6_python` to all stages
2. ✅ `pipeline/stages_impl.py` - Add `@progress_monitor` to all `run()` methods
3. ✅ `conversion/ms_utils.py` - Add `@require_casa6_python` to CASA functions
4. ✅ `imaging/cli_imaging.py` - Add `@require_casa6_python` to imaging functions

### Phase 2: WCS and Data Quality (WEEK 2)
5. ✅ `qa/catalog_validation.py` - Replace all WCS calls with safe versions
6. ✅ `mosaic/cli.py` - Fix WCS conversions
7. ✅ `photometry/adaptive_photometry.py` - Add non-finite filtering
8. ✅ `photometry/forced.py` - Add non-finite filtering

### Phase 3: Long-Running Operations (WEEK 3)
9. ✅ `conversion/uvh5_to_ms.py` - Add progress monitoring
10. ✅ `mosaic/streaming_mosaic.py` - Add progress monitoring
11. ✅ `photometry/adaptive_photometry.py` - Add progress monitoring

### Phase 4: API and CLI (WEEK 4)
12. ✅ `api/routes.py` - Already planned (Priority 3)
13. ✅ `api/batch_jobs.py` - Add input validation
14. ✅ CLI modules - Add input validation

### Phase 5: Remaining Files (ONGOING)
15. ✅ `calibration/skymodel_image.py` - WCS fixes
16. ✅ `imaging/export.py` - FITS validation
17. ✅ `qa/image_quality.py` - Non-finite filtering
18. ✅ Other files as needed

---

## Estimated Impact

### Files Requiring Safeguards: **~25 files**

### Breakdown by Category:
- **WCS Safeguards**: 3 files (critical)
- **Non-Finite Safeguards**: 8 files (high priority)
- **CASA Environment**: 6 files (critical)
- **Progress Monitoring**: 5 files (high priority)
- **FITS Validation**: 3 files (medium priority)
- **Input Validation**: 3 files (medium priority)
- **Parallel Processing**: 1 file (low priority)

### Expected Benefits:
- ✅ **Prevent 4D WCS errors** in catalog validation and mosaic operations
- ✅ **Prevent NonFiniteValueError** in photometry and fitting operations
- ✅ **Fail fast** if wrong Python environment (casa6 requirement)
- ✅ **Better user experience** with progress monitoring
- ✅ **More robust** pipeline operations

---

## Testing Strategy

After each phase:
1. Run existing tests
2. Test with real DSA-110 data
3. Verify safeguards trigger appropriately
4. Check performance impact (should be minimal)

---

## Notes

- Safeguards are designed to be **non-breaking** - they warn but don't fail unless critical
- **Performance impact** should be minimal (mostly validation checks)
- **Backward compatibility** maintained - existing code continues to work
- Safeguards can be **gradually enabled** - start with critical paths, expand over time

