# Unanticipated Issues: Trial and Error Discoveries

**Date:** 2025-01-XX  
**Purpose:** Document issues that required trial and error to resolve, even if documented elsewhere

---

## Critical Issues Requiring Multiple Attempts

### 1. CASA TIME Epoch Conversion Bug
- **Issue:** Assumed CASA TIME was seconds since MJD 51544.0, but pyuvdata writer uses seconds since MJD 0
- **Impact:** Phase centers calculated for wrong year (2166 instead of 2025), RA ~170° instead of ~129°
- **Discovery:** Calibrator auto-selection failed despite MS being 1 minute from transit (calculated 23° separation instead of 0.19°)
- **Attempts:** Multiple debugging sessions tracing phase center calculations
- **Fix:** Created `detect_casa_time_format()` utility and updated `_fix_field_phase_centers_from_times()` to use it

### 2. Silent Failure of `configure_ms_for_imaging()`
- **Issue:** Function could fail silently, leaving MS files without MODEL_DATA and CORRECTED_DATA columns
- **Impact:** Pipeline-generated MS files were 2.1 GB vs CLI-generated 5.1 GB (missing critical columns)
- **Discovery:** File size discrepancy investigation revealed missing columns
- **Attempts:** Initially thought it was a configuration difference, then discovered exceptions were being caught and only logged
- **Fix:** Added robust validation, explicit error raising (`ConversionError`), and fail-fast behavior in `hdf5_orchestrator.py`

### 3. Calibration Table Registration Missing
- **Issue:** `CalibrationSolveStage` created calibration tables but didn't register them in registry database
- **Impact:** `CalibrationStage` couldn't find tables via registry lookup ("No calibration tables available")
- **Discovery:** Pipeline failed at calibration application stage despite successful solve
- **Attempts:** Initially thought it was a path issue, then discovered tables weren't registered at all
- **Fix:** Added registration logic to `CalibrationSolveStage` using `register_set_from_prefix()`

### 4. Calibration Table Validity Window Too Narrow
- **Issue:** Initially used only MS time range for validity window (~5 minutes)
- **Impact:** Tables not discoverable for other MS files in the 60-minute observation window
- **Discovery:** Tables registered but not found when applying to other MS files
- **Attempts:** Initially thought it was a registry lookup issue, then discovered validity window was too restrictive
- **Fix:** Extended validity window to ±1 hour around MS time range

### 5. Duplicate/Legacy MS File Discovery
- **Issue:** `ConversionStage` discovered legacy MS files (`.phased.ms`, `.phased_concat.ms`) that shouldn't be processed
- **Impact:** Pipeline attempted to process more MS files than generated, some failing with permission errors
- **Discovery:** User noticed "we are running this on more MS than we generated initially"
- **Attempts:** Initially thought it was a discovery logic issue, then discovered recursive glob was finding legacy files
- **Fix:** Added filename pattern filtering (`YYYY-MM-DDTHH:MM:SS.ms`) and excluded subdirectories

### 6. Calibration Table Prefix Extraction
- **Issue:** Needed to extract common prefix from calibration table filenames (remove suffixes like `_bpcal`, `_gpcal`)
- **Impact:** Registration failed because prefix didn't match actual table filenames
- **Discovery:** `register_set_from_prefix()` couldn't find tables with provided prefix
- **Attempts:** Multiple regex patterns tried to extract correct prefix
- **Fix:** Used regex to remove table type suffixes: `re.sub(r'_(bpcal|gpcal|gacal|2gcal|kcal|bacal|flux)$', '', name)`

### 7. Missing `populate_model_from_catalog()` Function
- **Issue:** `CalibrationSolveStage` called `populate_model_from_catalog()` but function didn't exist
- **Impact:** ImportError during calibration solve stage
- **Discovery:** Direct import error when running pipeline
- **Attempts:** Initially thought it was an import path issue, then discovered function was missing entirely
- **Fix:** Created `populate_model_from_catalog()` in `calibration/model.py` with catalog lookup and manual MODEL_DATA calculation

### 8. Autocorrelation Flagging API Mismatch
- **Issue:** Called `flag_antenna(ms_path, autocorr=True)` but function doesn't accept `autocorr` parameter
- **Impact:** TypeError during calibration solve stage
- **Discovery:** Direct error when running pipeline with `flag_autocorr=True`
- **Attempts:** Initially thought it was a parameter name issue, then discovered need to use CASA `flagdata` directly
- **Fix:** Replaced with `from casatasks import flagdata; flagdata(vis=str(ms_path), autocorr=True, flagbackup=False)`

### 9. ConversionStage Only Returning Single MS Path
- **Issue:** `ConversionStage.execute()` only returned first MS path, not all discovered MS files
- **Impact:** `milestone1_pipeline.py` had to manually call `discover_ms_files()` again, breaking "pure pipeline" requirement
- **Discovery:** Script needed to discover MS files manually despite conversion stage already discovering them
- **Attempts:** Initially thought it was a design limitation, then realized stage should return all MS paths
- **Fix:** Modified `ConversionStage` to return `ms_paths` list in addition to `ms_path` for backward compatibility

### 10. Calibration Parameters Not Passed to Model Population
- **Issue:** `CalibrationSolveStage` didn't pass calibrator name/coordinates to `populate_model_from_catalog()`
- **Impact:** Model population might fail or use wrong calibrator
- **Discovery:** After creating `populate_model_from_catalog()`, realized parameters weren't being passed
- **Attempts:** Initially thought function would auto-detect, then realized explicit parameters needed
- **Fix:** Updated `CalibrationSolveStage` to extract and pass `calibrator_name`, `cal_ra_deg`, `cal_dec_deg`, `cal_flux_jy` from `calibration_params`

### 11. MS File Time Range Extraction for Group Conversion
- **Issue:** `milestone1_60min_mosaic.py` set `end_time = start_time` when calling `convert_subband_groups_to_ms()`
- **Impact:** Validation error: "start_time must be before end_time"
- **Discovery:** Direct validation error when running script
- **Attempts:** Initially thought it was a time calculation bug, then discovered need to read actual time ranges from HDF5 files
- **Fix:** Modified script to read `time_array` from all HDF5 files in group and ensure `end_time > start_time` (add 1 second if equal)

### 12. Internal Group Re-Discovery in `convert_subband_groups_to_ms()`
- **Issue:** Function internally re-discovers groups based on `start_time`/`end_time`, which might not match filename timestamps
- **Impact:** No groups found even with corrected time ranges
- **Discovery:** Function returned empty list despite groups existing
- **Attempts:** Initially thought it was a time range issue, then discovered function re-discovers groups internally
- **Fix:** Bypassed `convert_subband_groups_to_ms()` and used `write_ms_from_subbands()` directly with explicit file list

### 13. Missing Import: `EarthLocation` in `hdf5_orchestrator.py`
- **Issue:** `_peek_uvh5_phase_and_midtime()` used `EarthLocation` without importing it
- **Impact:** NameError during HDF5 peek operation
- **Discovery:** Direct error when running conversion
- **Attempts:** Initially thought it was a namespace issue, then discovered missing import
- **Fix:** Added `from astropy.coordinates import EarthLocation` inside function

### 14. Missing Import: `Dict`, `List`, `Optional` in `flagging.py`
- **Issue:** Type hints used without imports
- **Impact:** NameError during calibration flagging
- **Discovery:** Direct error when running calibration
- **Attempts:** Initially thought it was a Python version issue, then discovered missing imports
- **Fix:** Added `from typing import Dict, List, Optional`

### 15. Registration Verification Not Implemented Initially
- **Issue:** No verification that registered tables are actually discoverable
- **Impact:** Tables could be registered but not findable, causing silent failures later
- **Discovery:** After implementing registration, realized no verification step existed
- **Attempts:** Initially thought registration was sufficient, then realized need for verification
- **Fix:** Created `register_and_verify_caltables()` helper that verifies tables are discoverable and exist on filesystem

### 16. No Rollback Mechanism for Failed Registration
- **Issue:** If registration succeeded but verification failed, tables remained registered but unusable
- **Impact:** Invalid tables could be used by downstream stages
- **Discovery:** After implementing verification, realized need for rollback
- **Attempts:** Initially thought verification failure should just raise error, then realized need to clean up
- **Fix:** Added rollback logic that retires calibration set if verification fails

### 17. Calibration Registry DB Path Determination
- **Issue:** Registry DB path needed to be determined consistently across CLI and pipeline
- **Impact:** CLI and pipeline might use different registry databases
- **Discovery:** After implementing registration in both places, realized path determination was inconsistent
- **Attempts:** Initially hardcoded paths, then realized need for environment variable support
- **Fix:** Used consistent logic: `CAL_REGISTRY_DB` env var → `PIPELINE_STATE_DIR` env var → default path

### 18. Error Handling: Registration Failures Should Be Fatal
- **Issue:** Initially registration failures were logged as warnings (non-fatal)
- **Impact:** Pipeline could continue without registered tables, causing failures later
- **Discovery:** Pipeline failed at calibration application stage despite "successful" solve
- **Attempts:** Initially thought warnings were sufficient, then realized need for fail-fast behavior
- **Fix:** Made registration failures raise `RuntimeError` (fatal) in pipeline, warnings (non-fatal) in CLI

---

## Design Decisions That Required Iteration

### 19. Calibration Workflow: Solve Once vs Solve Per MS
- **Issue:** Initially unclear whether to solve calibration on each MS or once on peak transit MS
- **Impact:** Affected pipeline design and calibration table validity windows
- **Discovery:** Realized solving once on peak transit and applying to all MS files is more efficient
- **Attempts:** Initially considered solving on each MS, then realized need for single solve + apply pattern
- **Fix:** Designed workflow: solve once on peak transit MS, then apply to all MS files

### 20. MS File Discovery: Pattern vs Recursive Glob
- **Issue:** Initially used recursive glob (`**/*.ms`) which found legacy files
- **Impact:** Processed unintended MS files
- **Discovery:** User noticed more MS files than expected
- **Attempts:** Initially thought recursive search was correct, then realized need for pattern filtering
- **Fix:** Changed to pattern-based filtering: `YYYY-MM-DDTHH:MM:SS.ms` in main directory only

### 21. Calibration Table Set Naming
- **Issue:** Needed unique but meaningful set names for calibration tables
- **Impact:** Set names needed to be unique but also human-readable
- **Discovery:** After implementing registration, realized need for consistent naming scheme
- **Attempts:** Initially used MS filename only, then realized need for time component
- **Fix:** Used format: `{ms_base}_{mid_mjd:.6f}` (e.g., `2025-10-29T13:54:17_60320.123456`)

---

## Lessons Learned

1. **Silent failures are worse than explicit failures** - Always validate critical operations and fail fast
2. **Verification is as important as registration** - Don't assume registration succeeded without verification
3. **Pattern matching is safer than recursive globs** - Explicit patterns prevent unintended file discovery
4. **TIME format detection is critical** - Never assume TIME format, always detect it
5. **Rollback mechanisms prevent partial failures** - If verification fails, clean up registration
6. **Consistent path determination prevents confusion** - Use environment variables and defaults consistently
7. **Fail-fast behavior catches issues early** - Better to fail immediately than fail later with confusing errors
8. **Idempotent operations prevent duplicate work** - Use upsert patterns for registration
9. **Explicit parameters prevent auto-detection failures** - Don't rely on auto-detection when explicit values are available
10. **Helper functions centralize logic** - Extract common patterns into reusable helpers

---

## Recommendations for Future Development

1. **Add unit tests for TIME format detection** - Test both CASA TIME formats
2. **Add integration tests for calibration registration** - Test registration + verification + rollback
3. **Add validation checks at stage boundaries** - Verify outputs before passing to next stage
4. **Document expected file patterns** - Clearly document MS filename patterns and calibration table naming
5. **Add monitoring/alerting for registration failures** - Track registration success rates
6. **Consider transaction-like semantics** - Make registration + verification atomic where possible
7. **Add dry-run mode for registration** - Allow testing registration without committing
8. **Document calibration workflow patterns** - Clearly document solve-once vs solve-per-MS patterns

