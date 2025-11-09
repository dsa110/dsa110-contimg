# Safeguard Integration Quick Reference

## Summary: ~25 Files Need Safeguards

---

## 🔴 CRITICAL PRIORITY (Do First)

### 1. Pipeline Stages (`pipeline/stages_impl.py`)
- **Add**: `@require_casa6_python` to all stage classes
- **Add**: `@progress_monitor` to all `run()`/`execute()` methods
- **Impact**: Prevents wrong Python environment, adds progress visibility
- **Lines**: ~26, ~264, ~691, ~894, ~1302, ~1452

### 2. Catalog Validation (`qa/catalog_validation.py`)
- **Add**: Safe WCS conversion functions
- **Replace**: Manual `wcs.wcs_pix2world()` and `wcs.wcs_world2pix()` calls
- **Impact**: Prevents 4D WCS errors
- **Lines**: ~201, ~274, ~341, ~505, ~740

### 3. MS Conversion (`conversion/ms_utils.py`)
- **Add**: `@require_casa6_python` to CASA-dependent functions
- **Impact**: Ensures CASA environment for MS operations
- **Lines**: ~251, ~580

### 4. Imaging (`imaging/cli_imaging.py`)
- **Add**: `@require_casa6_python` to imaging functions
- **Impact**: Ensures CASA environment for imaging
- **Lines**: ~13-17

---

## 🟠 HIGH PRIORITY (Do Second)

### 5. Mosaic Operations (`mosaic/cli.py`)
- **Add**: Safe WCS conversion for corner calculations
- **Impact**: Prevents 4D WCS errors in mosaic
- **Lines**: ~612

### 6. Photometry (`photometry/adaptive_photometry.py`)
- **Add**: Non-finite value filtering
- **Impact**: Prevents fitting errors from NaN/Inf
- **Lines**: Throughout

### 7. Photometry (`photometry/forced.py`)
- **Add**: Non-finite value filtering
- **Impact**: Prevents flux calculation errors
- **Lines**: Throughout

### 8. UVH5 Conversion (`conversion/uvh5_to_ms.py`)
- **Add**: `@progress_monitor` to conversion functions
- **Impact**: Progress visibility for long conversions
- **Lines**: ~956, ~1170

### 9. Mosaic Streaming (`mosaic/streaming_mosaic.py`)
- **Add**: `@progress_monitor` to mosaic operations
- **Impact**: Progress visibility for long mosaics
- **Lines**: Throughout

---

## 🟡 MEDIUM PRIORITY (Do Third)

### 10. Sky Model (`calibration/skymodel_image.py`)
- **Add**: Safe WCS conversion
- **Impact**: Prevents WCS errors in sky model generation
- **Lines**: ~81

### 11. Image Export (`imaging/export.py`)
- **Add**: FITS validation
- **Impact**: Better error handling for FITS operations
- **Lines**: ~54

### 12. Image Quality (`qa/image_quality.py`)
- **Add**: Non-finite value filtering
- **Impact**: Prevents quality metric errors
- **Lines**: Throughout

### 13. Mosaic Validation (`mosaic/validation.py`)
- **Add**: Non-finite value filtering (already has some)
- **Impact**: More robust validation
- **Lines**: ~1091

### 14. Batch Jobs (`api/batch_jobs.py`)
- **Add**: Input validation
- **Impact**: Better error messages for invalid jobs
- **Lines**: Throughout

### 15. CLI Modules
- **Files**: `imaging/cli.py`, `photometry/cli.py`, `mosaic/cli.py`, `calibration/cli_calibrate.py`
- **Add**: Input validation
- **Impact**: Better CLI error handling

---

## 🟢 LOW PRIORITY (Do When Time Permits)

### 16. Parallel Processing (`utils/parallel.py`)
- **Add**: Progress monitoring for parallel operations
- **Impact**: Better visibility into parallel work

### 17. HTML Reports (`qa/html_reports.py`)
- **Add**: Basic FITS validation
- **Impact**: Better error handling

### 18. Merge SPWs (`conversion/merge_spws.py`)
- **Add**: `@require_casa6_python` to CASA functions
- **Impact**: Ensures CASA environment
- **Lines**: ~127

### 19. Telescope Helpers (`conversion/helpers_telescope.py`)
- **Add**: `@require_casa6_python` to CASA functions
- **Impact**: Ensures CASA environment
- **Lines**: ~21

---

## Safeguard Types by File

### WCS Safeguards Needed:
- `qa/catalog_validation.py` ⭐⭐⭐
- `mosaic/cli.py` ⭐⭐
- `calibration/skymodel_image.py` ⭐

### Non-Finite Safeguards Needed:
- `photometry/adaptive_photometry.py` ⭐⭐
- `photometry/forced.py` ⭐⭐
- `qa/image_quality.py` ⭐
- `mosaic/validation.py` ⭐
- `mosaic/cli.py` ⭐

### CASA Environment Safeguards Needed:
- `pipeline/stages_impl.py` ⭐⭐⭐
- `conversion/ms_utils.py` ⭐⭐⭐
- `imaging/cli_imaging.py` ⭐⭐⭐
- `conversion/merge_spws.py` ⭐
- `conversion/helpers_telescope.py` ⭐

### Progress Monitoring Needed:
- `pipeline/stages_impl.py` ⭐⭐⭐
- `conversion/uvh5_to_ms.py` ⭐⭐
- `mosaic/streaming_mosaic.py` ⭐⭐
- `photometry/adaptive_photometry.py` ⭐
- `utils/parallel.py` ⭐

### FITS Validation Needed:
- `imaging/export.py` ⭐
- `photometry/aegean_fitting.py` ⭐
- `qa/html_reports.py` ⭐

### Input Validation Needed:
- `api/batch_jobs.py` ⭐
- CLI modules ⭐

---

## Integration Order (Recommended)

### Week 1: Critical Pipeline
1. `pipeline/stages_impl.py` - CASA + Progress
2. `conversion/ms_utils.py` - CASA
3. `imaging/cli_imaging.py` - CASA

### Week 2: WCS & Data Quality
4. `qa/catalog_validation.py` - WCS
5. `mosaic/cli.py` - WCS
6. `photometry/adaptive_photometry.py` - Non-finite
7. `photometry/forced.py` - Non-finite

### Week 3: Long Operations
8. `conversion/uvh5_to_ms.py` - Progress
9. `mosaic/streaming_mosaic.py` - Progress
10. `photometry/adaptive_photometry.py` - Progress

### Week 4: Remaining
11. `calibration/skymodel_image.py` - WCS
12. `imaging/export.py` - FITS validation
13. `qa/image_quality.py` - Non-finite
14. `api/batch_jobs.py` - Input validation
15. CLI modules - Input validation

---

## Quick Stats

- **Total Files**: ~25
- **Critical**: 4 files
- **High Priority**: 5 files
- **Medium Priority**: 7 files
- **Low Priority**: 4 files

- **WCS Safeguards**: 3 files
- **Non-Finite Safeguards**: 5 files
- **CASA Safeguards**: 5 files
- **Progress Monitoring**: 5 files
- **FITS Validation**: 3 files
- **Input Validation**: 4 files

---

## See Also

- `SAFEGUARD_INTEGRATION_PLAN.md` - Detailed strategy
- `SAFEGUARD_INTEGRATION_LOCATIONS.md` - Specific line numbers
- `SAFEGUARD_INTEGRATION_EXPANDED.md` - Full analysis
- `RUNTIME_SAFEGUARDS_USAGE.md` - How to use safeguards

