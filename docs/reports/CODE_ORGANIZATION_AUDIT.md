# Code Organization Audit - Misorganized Functions

**Date:** 2025-11-05  
**Scope:** Complete codebase review for organizational issues  
**Status:** Analysis Complete

---

## Executive Summary

This audit identifies functions and modules that are misorganized, poorly placed, or should be consolidated. The goal is to improve code maintainability, reduce duplication, and clarify module boundaries.

---

## Critical Issues (High Priority)

### 1. **`calibration/imaging.py` - Misplaced Module** ⚠️

**Location:** `src/dsa110_contimg/calibration/imaging.py` (34 lines)

**Issue:** This module contains imaging functionality (`quick_image()`) but is in the `calibration/` package. It should be in `imaging/` or removed if redundant.

**Functions:**
- `quick_image()` - Wrapper around `tclean` for quick imaging

**Recommendation:**
- **Option A:** Move to `imaging/cli.py` or `imaging/worker.py` if used
- **Option B:** Remove if redundant with `imaging/cli.py` functionality
- **Option C:** Move to `imaging/quicklooks.py` if quick-look specific

**Action:** Check if `imaging/cli.py` already provides this functionality.

---

### 2. **`calibration/qa.py` - Overlaps with `qa/calibration_quality.py`** ⚠️

**Location:** `src/dsa110_contimg/calibration/qa.py` (497 lines)

**Issue:** This module contains QA functionality that overlaps with `qa/calibration_quality.py`. There's unclear separation of concerns.

**Functions in `calibration/qa.py`:**
- `check_upstream_delay_correction()` - Checks if delays are corrected upstream

**Functions in `qa/calibration_quality.py`:**
- `validate_caltable_quality()` - Validates calibration table quality
- `check_corrected_data_quality()` - Checks CORRECTED_DATA quality

**Recommendation:**
- **Consolidate** delay checking into `qa/calibration_quality.py`
- Keep `calibration/qa.py` only if it contains calibration-specific utilities not suitable for general QA
- **OR** rename `calibration/qa.py` to `calibration/delay_checking.py` to be more specific

**Action:** Review both modules and consolidate or clarify separation.

---

### 3. **Duplicate Antenna Position Utilities** ✅ **RESOLVED**

**Location:**
- ~~`src/dsa110_contimg/utils/antpos.py`~~ (already removed)
- `src/dsa110_contimg/utils/antpos_local/utils.py` (126 lines) - **KEPT**

**Status:** ✅ Already resolved - `utils/antpos.py` has been removed. All imports now use `antpos_local`.

**Note:** The redundancy analysis document may be outdated. Current codebase only has `antpos_local/utils.py`.

---

### 4. **Duplicate CSV Data Files** ⚠️

**Location:**
- `src/dsa110_contimg/utils/antpos_local/data/DSA110_Station_Coordinates.csv`
- `src/dsa110_contimg/utils/data/DSA110_Station_Coordinates.csv`

**Issue:** Same antenna coordinate data in two locations.

**Recommendation:**
- **Keep:** `antpos_local/data/` (used by modern implementation)
- **Archive:** `utils/data/DSA110_Station_Coordinates.csv` → `archive/legacy/utils/data/DSA110_Station_Coordinates.csv`
- **Update:** Any code that references `utils/data/` to use `antpos_local/data/`

---

## Medium Priority Issues

### 5. **Ops Pipeline Script Duplication** ⚠️

**Location:** `ops/pipeline/` scripts

**Issue:** Multiple scripts have duplicate helper functions:

**Duplicated Functions:**
- `_load_ra_dec()` - Appears in 3+ files
- `_load_flux_jy()` - Appears in 2+ files
- `_group_id_from_path()` - Appears in 4 files
- `_write_ms_group_via_uvh5_to_ms()` - Appears in 4 files (~300 lines each)

**Files:**
- `ops/pipeline/build_central_calibrator_group.py`
- `ops/pipeline/build_calibrator_transit_offsets.py`
- `ops/pipeline/image_groups_in_timerange.py`
- `ops/pipeline/curate_transit.py`

**Recommendation:**
- **Create:** `ops/pipeline/calibrator_helpers.py` for catalog loading
- **Create:** `ops/pipeline/group_helpers.py` for group ID parsing
- **Create:** `ops/pipeline/ms_conversion_helpers.py` for MS writing (or use orchestrator CLI)
- **Consolidate:** All duplicate functions into shared modules

**Impact:** Reduces ~500+ lines of duplicate code

---

### 6. **Progress Reporting Duplication** ⚠️

**Location:**
- `src/dsa110_contimg/utils/progress.py` - `should_disable_progress()`
- `src/dsa110_contimg/utils/cli_helpers.py` - `should_show_progress()`

**Issue:** Two functions that check the same flags but return opposite boolean values.

**Recommendation:**
- **Consolidate:** Keep `should_disable_progress()` in `utils/progress.py`
- **Remove:** `should_show_progress()` from `cli_helpers.py`
- **Update:** Use `not should_disable_progress()` where needed

---

### 7. **CASA Log Directory Setup Duplication** ⚠️

**Location:** Repeated in 5+ CLI files:
- `calibration/cli.py`
- `imaging/cli.py`
- `pointing/cli.py`
- `conversion/cli.py`
- `qa/casa_ms_qa.py`

**Pattern:**
```python
try:
    from dsa110_contimg.utils.tempdirs import derive_casa_log_dir
    casa_log_dir = derive_casa_log_dir()
    os.chdir(str(casa_log_dir))
except Exception:
    pass
```

**Recommendation:**
- **Already solved:** `setup_casa_environment()` in `utils/cli_helpers.py` handles this
- **Action:** Verify all CLIs use `setup_casa_environment()` instead of inline code
- **Remove:** Duplicate inline setups

---

### 8. **Large CLI Files - Should Be Split** ⚠️

**Location:**
- `calibration/cli.py` - 2430 lines (very large)
- `imaging/cli.py` - ~1000 lines
- `conversion/strategies/hdf5_orchestrator.py` - 964 lines

**Issue:** Large files mixing validation, execution, and argument parsing.

**Recommendation:**
- **Split `calibration/cli.py`:**
  - `calibration/cli_calibrate.py` - Main calibration command
  - `calibration/cli_apply.py` - Apply calibration command
  - `calibration/cli_validate.py` - Validation commands
  - Keep `cli.py` as thin orchestrator
- **Split `imaging/cli.py`:**
  - `imaging/cli_image.py` - Image command
  - `imaging/cli_export.py` - Export command
  - Keep `cli.py` as thin orchestrator
- **Extract validation** from CLI files into separate modules

**Priority:** Medium (works but could be better organized)

---

### 9. **Validation Module Organization** ⚠️

**Location:**
- `src/dsa110_contimg/utils/validation.py` (402 lines) - General-purpose
- `src/dsa110_contimg/conversion/validation.py` (459 lines) - Conversion-specific
- `src/dsa110_contimg/mosaic/validation.py` (1067 lines) - Mosaic-specific

**Issue:** Three separate validation modules with some overlap.

**Status:** **Justified** - Different return types and use cases:
- `utils/validation.py` - Exception-based design
- `conversion/validation.py` - Returns dataclass results
- `mosaic/validation.py` - Uses caching, returns metrics objects

**Recommendation:**
- **Keep separate** - These serve distinct purposes
- **However:** Consider consolidating basic file/directory validation into `utils/validation.py`
- **Action:** Create shared base validation module for common checks

---

### 10. **Progress Reporting Duplication** ⚠️

**Location:**
- `src/dsa110_contimg/utils/progress.py` - tqdm-based iteration progress
- `src/dsa110_contimg/conversion/progress.py` - Workflow step tracking

**Status:** **Justified** - Different purposes:
- `utils/progress.py` - Iteration progress bars (tqdm)
- `conversion/progress.py` - High-level workflow steps

**Recommendation:**
- **Keep separate** - Different purposes
- **Clarify:** Document the distinction in both modules

---

## Low Priority Issues

### 11. **Notebook Helper in Wrong Location** ⚠️

**Location:** `src/dsa110_contimg/notebooks/calibrator_helper.py`

**Issue:** This is in the source package but seems to be for notebooks only.

**Recommendation:**
- **Move to:** `notebooks/` directory (not in `src/`)
- **OR** rename to `calibration/notebook_helpers.py` if used by notebooks

---

### 12. **Pointing Module Has Plotting Function** ⚠️

**Location:** `src/dsa110_contimg/pointing/plot_dec_history.py`

**Status:** Already archived with redirect to `scripts/plot_observation_timeline.py`

**Action:** ✓ Already handled

---

### 13. **Conversion Helpers Module is Large** ⚠️

**Location:** `src/dsa110_contimg/conversion/helpers.py` (1250 lines)

**Issue:** Very large helpers module with many functions.

**Functions Include:**
- `get_meridian_coords()` - Coordinate calculations
- `set_antenna_positions()` - Antenna position setting
- `phase_to_meridian()` - Phasing functions
- `configure_ms_for_imaging()` - MS configuration
- Many more...

**Recommendation:**
- **Split into:**
  - `conversion/helpers_coordinates.py` - Coordinate/astronomy calculations
  - `conversion/helpers_phasing.py` - Phasing functions
  - `conversion/helpers_ms.py` - MS configuration/utilities
  - Keep `helpers.py` for general utilities

**Priority:** Low (works fine, just organization)

---

## Summary of Actions

### High Priority (Do First)
1. ✅ **Duplicate `utils/antpos.py`** - Already resolved (removed, only `antpos_local` remains)
2. ⚠️ **Archive duplicate CSV data file** → `archive/legacy/utils/data/DSA110_Station_Coordinates.csv`
3. ⚠️ **Move or archive `calibration/imaging.py`** → `archive/legacy/calibration/imaging.py` or move to `imaging/`
4. ⚠️ **Consolidate `calibration/qa.py` with `qa/calibration_quality.py`** (archive if redundant)

### Medium Priority (Do Next)
5. ⚠️ **Consolidate ops pipeline helper functions**
6. ⚠️ **Fix progress reporting duplication** (`should_disable_progress` vs `should_show_progress`)
7. ⚠️ **Remove duplicate CASA log directory setup** (use `setup_casa_environment()`)
8. ⚠️ **Split large CLI files** (calibration/cli.py, imaging/cli.py)

### Low Priority (Nice to Have)
9. ⚠️ **Move notebook helper out of src/**
10. ⚠️ **Split large conversion/helpers.py**

---

## Metrics

- **Total duplicate code:** ~700+ lines
- **Files to consolidate:** 8-10 files
- **Large files to split:** 3 files
- **Modules to relocate:** 2-3 modules

---

## Implementation Plan

### Phase 1: Archive Duplicates (High Priority)
1. ✅ **Already resolved** - `utils/antpos.py` doesn't exist (removed previously)
2. ✅ **Archived** - Duplicate CSV file → `archive/legacy/utils/data/DSA110_Station_Coordinates.csv`
   - ✅ **Removed from source** - Code now uses `antpos_local/data/` version
3. ✅ **Archived** - `calibration/imaging.py` → `archive/legacy/calibration/imaging.py`
   - ✅ **Removed from source** - Code updated to use `imaging/cli.py` instead
   - ✅ **Updated imports:**
     - `imaging/worker.py` now uses `image_ms()` from `imaging/cli.py`
     - `tests/utils/cal_ms_demo.py` now uses `image_ms()` from `imaging/cli.py`
4. ✅ **Consolidated** - `calibration/qa.py` → `qa/calibration_quality.py`
   - ✅ **Archived** - `calibration/qa.py` → `archive/legacy/calibration/qa.py`
   - ✅ **Moved functions:**
     - `check_upstream_delay_correction()` → `qa/calibration_quality.py`
     - `verify_kcal_delays()` → `qa/calibration_quality.py`
     - `inspect_kcal_simple()` → `qa/calibration_quality.py`
   - ✅ **Updated imports:**
     - `calibration/cli.py` - Updated to use `qa.calibration_quality`
     - `qa/__init__.py` - Exported delay QA functions

### Phase 2: Consolidate Helpers (Medium Priority)
5. ✅ **Created shared ops pipeline helpers** - `helpers_catalog.py`, `helpers_group.py`, `helpers_ms_conversion.py`
   - ✅ Updated `build_central_calibrator_group.py`
   - ✅ Updated `build_calibrator_transit_offsets.py`
   - ✅ Updated `image_groups_in_timerange.py`
   - ✅ Updated `curate_transit.py`
   - ✅ Updated `run_next_field_after_central.py`
   - **Impact:** Removed ~500+ lines of duplicate code across 5 pipeline scripts
6. ✅ **Progress reporting duplication** - False alarm, `should_show_progress()` does not exist
7. ✅ **Removed duplicate CASA setup code** - Updated `streaming_converter.py` to use `setup_casa_environment()`
   - ✅ All other files already use `setup_casa_environment()` correctly

### Phase 3: Refactor Large Files (Low Priority)
8. ✅ **Fully split calibration CLI** - Extracted all subcommand handlers
   - ✅ Created `calibration/cli_utils.py` with `rephase_ms_to_calibrator()` and `clear_all_calibration_artifacts()` (298 lines)
   - ✅ Created `calibration/cli_calibrate.py` with calibrate subcommand (1685 lines)
   - ✅ Created `calibration/cli_apply.py` with apply subcommand (30 lines)
   - ✅ Created `calibration/cli_flag.py` with flag subcommand (378 lines)
   - ✅ Created `calibration/cli_qa.py` with QA/diagnostic subcommands (301 lines)
   - ✅ **Main CLI reduced from 2143 → 151 lines** (93% reduction!)
   - **Benefit:** Improved maintainability, clear separation of concerns
9. ✅ **Split imaging CLI** - Extracted all subcommand handlers
   - ✅ Created `imaging/cli_utils.py` with `detect_datacolumn()` and `default_cell_arcsec()` (135 lines)
   - ✅ Created `imaging/cli_imaging.py` with `image_ms()` and `run_wsclean()` (595 lines)
   - ✅ **Main CLI reduced to 324 lines** (from original 1008 lines, 68% reduction)
   - **Benefit:** Improved maintainability, clear separation of concerns
10. ✅ **Split conversion/helpers.py** - Extracted all specialized helpers
    - ✅ Created `conversion/helpers_antenna.py` with antenna position functions (116 lines)
    - ✅ Created `conversion/helpers_coordinates.py` with coordinate and phase functions (227 lines)
    - ✅ Created `conversion/helpers_model.py` with model and UVW functions (128 lines)
    - ✅ Created `conversion/helpers_validation.py` with validation functions (619 lines)
    - ✅ Created `conversion/helpers_telescope.py` with telescope utility functions (150 lines)
    - ✅ **Main helpers.py reduced to 64 lines** (backward compatibility wrapper)
    - ✅ **Original file reduced from 1249 → 64 lines** (95% reduction!)
    - **Benefit:** Improved organization, specialized modules for each concern
11. ✅ **Moved notebook helper** - `src/dsa110_contimg/notebooks/calibrator_helper.py` → `docs/notebooks/calibrator_helper.py`
   - ✅ File moved out of `src/` to `docs/` where notebook utilities belong
   - ✅ **Fixed broken imports** - Moved `load_pointing()` to `pointing/utils.py` for source code use
   - ✅ Updated all source imports: `pointing/cli.py`, `catalog/build_nvss_strip_cli.py`, `pointing/backfill_pointing.py`, `pointing/monitor.py`
   - ✅ Notebook helper re-exports `load_pointing` from `pointing.utils` for backward compatibility

---

## Notes

- Some duplication is intentional (e.g., validation modules serve different purposes)
- Some large files are acceptable if they have clear single responsibilities
- Focus on removing true redundancy and improving discoverability

