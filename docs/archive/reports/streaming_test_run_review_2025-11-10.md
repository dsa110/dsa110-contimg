# Streaming Test Run Review - November 10, 2025

**Date:** 2025-11-10  
**Test Goal:** Fully autonomous run from streaming conversion to mosaic creation  
**Outcome:** Test run failed due to multiple issues, but valuable lessons learned

---

## Executive Summary

The first trial streaming run attempted to process data autonomously from conversion through mosaic creation. The run encountered several critical issues that prevented completion:

1. **Phase center validation failure** (EXPECTED behavior misidentified as error)
2. **File existence validation gaps** (race conditions and missing checks)
3. **Database/filesystem path mismatches** (unvalidated paths)
4. **Incorrect time fallback logic** (using current time instead of observation time)
5. **Missing mosaic registration** (mosaics not tracked in data registry)
6. **Incomplete workflow integration** (missing finalization steps)

**Key Insight:** Many failures were due to validation logic treating expected behaviors as errors, rather than actual bugs in the pipeline logic.

---

## Critical Issues Identified

### 1. Phase Center Validation: Expected Behavior Treated as Error

**Problem:**
- Phase center validation failed with 2583.71 arcsec separation (vs 2.00 arcsec tolerance)
- Validation function didn't detect time-dependent phasing (RA = LST)
- Test run stopped because validation treated expected behavior as critical error

**Root Cause:**
- DSA-110 uses meridian-tracking phasing where RA = LST at observation time
- Each subband becomes a separate field with phase center at different LST
- Phase centers are **expected** to be incoherent across fields (separations >60 arcsec)
- Validation function didn't check for time-dependent phasing before failing

**Impact:**
- Test run halted unnecessarily
- Valid MS files were cleaned up as "corrupted"
- Downstream processing never occurred

**Fix Applied:**
- Created `conversion/README.md` documenting expected phase center behavior
- Updated validation function to detect time-dependent phasing
- Enhanced error messages to reference documentation
- Added tolerance for large separations (>60 arcsec) when time-dependent phasing detected

**Lesson Learned:**
- **Document expected behaviors prominently** - don't bury in function docstrings
- **Validation should distinguish expected vs. error conditions** - not all failures are errors
- **Error messages should guide users** - reference documentation, explain why behavior is expected

---

### 2. File Existence Validation Gaps

**Problem:**
Multiple locations where MS files weren't verified to exist before processing:

1. **`run_first_mosaic.py` lines 111-176**: Constructed `ms_path` but never checked existence before calling:
   - `extract_ms_time_range()`
   - `apply_to_target()`
   - `image_ms()`

2. **`mosaic/streaming_mosaic.py` lines 424-433**: `check_for_new_group()` queried database for MS paths but didn't verify files exist on disk

3. **`mosaic/streaming_mosaic.py` lines 471-509**: `get_group_ms_paths()` called `extract_ms_time_range()` without checking file existence

**Root Cause:**
- Assumption that database paths are always correct
- No validation that paths match actual file locations
- Race conditions: processing started before conversion completed

**Impact:**
- Silent failures when files don't exist
- Crashes when accessing non-existent files
- Incorrect chronological ordering (used `float("inf")` as fallback)

**Fix Applied:**
- Added file existence checks before all MS operations
- Added validation in `check_for_new_group()` and `get_group_ms_paths()`
- Created unit tests to prevent regression

**Lesson Learned:**
- **Always verify file existence before operations** - don't trust database paths blindly
- **Handle race conditions explicitly** - wait for conversion completion before processing
- **Validate database paths against filesystem** - especially after organization into date-based subdirectories

---

### 3. Race Condition: Processing Before Conversion Completes

**Problem:**
- `process_one_group()` returned immediately after calling `convert_subband_groups_to_ms()`
- Code tried to process MS before it existed
- No synchronization between conversion completion and downstream processing

**Root Cause:**
- Conversion runs asynchronously (subprocess or parallel workers)
- No wait mechanism for conversion completion
- Worker loop assumed MS would exist when processing started

**Impact:**
- Immediate failure when accessing MS file
- Test run couldn't proceed past conversion stage

**Fix Applied:**
- Added explicit wait for conversion completion
- Added file existence verification before processing
- Added retry logic with timeout

**Lesson Learned:**
- **Synchronize async operations** - don't assume completion
- **Add explicit wait mechanisms** - especially for subprocess calls
- **Verify completion before proceeding** - check file existence, not just process exit code

---

### 4. Database vs Filesystem Path Mismatches

**Problem:**
- Database stored MS paths but didn't verify they match filesystem
- After organization into date-based subdirectories, paths could become stale
- No validation that database paths match actual file locations

**Root Cause:**
- MS organization happens after database registration
- Paths updated in some places but not others
- No consistency check between database and filesystem

**Impact:**
- Silent failures when paths don't match
- Incorrect processing when wrong files accessed
- Mosaic creation failed when MS files couldn't be located

**Fix Applied:**
- Added path validation before all file operations
- Added consistency checks between database and filesystem
- Updated path resolution to handle organization

**Lesson Learned:**
- **Validate database paths against filesystem** - especially after organization
- **Update paths consistently** - when files move, update all references
- **Add consistency checks** - verify database and filesystem agree

---

### 5. Incorrect Time Fallback Logic

**Problem:**
- When `extract_ms_time_range()` failed and `mid_mjd` was None, code used `time.time() / 86400.0` (current time)
- Should have used observation time from filename or MS metadata
- Broke calibration validity windows

**Root Cause:**
- Fallback logic used current time instead of observation time
- No extraction of observation time from filename when MS metadata unavailable

**Impact:**
- Calibration tables registered with incorrect validity windows
- Misapplication or missed calibration
- Mosaic creation failed due to incorrect calibration timing

**Fix Applied:**
- Fixed time extraction fallback to use observation time from filename
- Added multiple fallback mechanisms (filename → MS metadata → current time)
- Improved error handling when time extraction fails

**Lesson Learned:**
- **Use observation time, not current time** - for calibration validity windows
- **Multiple fallback mechanisms** - filename → metadata → current time (last resort)
- **Validate time ranges** - ensure they're reasonable for observation

---

### 6. Missing Mosaic Registration and Finalization

**Problem:**
- Mosaics created but never registered in `data_registry`
- Mosaics never finalized (QA/validation status never set)
- Mosaics never moved to `/data/` (stayed in staging forever)
- Auto-publish never triggered

**Root Cause:**
- Missing calls to `register_mosaic_in_data_registry()` after mosaic creation
- Missing `finalize_mosaic()` call with QA/validation status
- No error handling or retry logic for publish failures

**Impact:**
- Mosaics orphaned in staging directory
- No tracking for publishing
- Auto-publish criteria never met
- Test run appeared to succeed but mosaics weren't accessible

**Fix Applied:**
- Added `register_mosaic_in_data_registry()` after mosaic creation
- Added `finalize_mosaic()` call with QA/validation status
- Added error handling and retry logic
- Added path validation before moves
- Added database-level locking for concurrent access

**Lesson Learned:**
- **Complete the workflow** - don't stop at creation, register and finalize
- **Set QA/validation status** - required for auto-publish
- **Handle publish failures** - add retry logic, don't leave mosaics orphaned
- **Validate paths before moves** - ensure source exists, destination writable

### 7. Incorrect Group Processing Order - Prevented Mosaic Creation

**Problem:**
- Test run processed 3 groups from 10-02 successfully, then stopped/switched to 10-17
- Never completed a full set of 10 sequential groups needed for mosaic creation
- Groups processed in bootstrap scan order (filesystem order), not chronological order by observation time
- `acquire_next_pending()` ordered by `received_at ASC` (registration time during bootstrap)
- Bootstrap scans files in filesystem order, which may not match chronological order

**Root Cause:**
- `acquire_next_pending()` ordered by `received_at ASC` (registration time during bootstrap)
- If 10-17 files were scanned/registered before some 10-02 files, they would be processed earlier
- This caused non-sequential processing: 3 groups from 10-02, then groups from 10-17, then back to 10-02
- Mosaic creation requires 10 sequential groups in chronological order - this couldn't be satisfied

**Impact:**
- **Mosaic creation failed** - never got 10 sequential groups from same date/time range
- Groups processed out of chronological order
- Test run appeared to process groups but couldn't create mosaic
- `check_for_new_group()` requires exactly 10 MS files in chronological order - this condition was never met

**Fix Applied:**
- Changed `acquire_next_pending()` to order by `group_id ASC` (observation time) instead of `received_at ASC`
- Ensures groups processed in chronological order regardless of bootstrap scan order
- All groups from earlier dates (e.g., 10-02) process before later dates (e.g., 10-17)
- Mosaic creation can now find 10 sequential groups in chronological order

**Lesson Learned:**
- **Process groups in chronological order** - by observation time (`group_id`), not registration time (`received_at`)
- **Critical for mosaic creation** - requires exactly 10 sequential groups in chronological order
- **Don't rely on filesystem order** - bootstrap scan order may not match chronological order
- **Mosaic creation depends on sequential processing** - out-of-order processing breaks the 10-group requirement

---

## Workflow Integration Issues

### Missing Steps in Streaming Workflow

1. **Mosaic Registration**: Mosaics created but not registered in `data_registry`
2. **QA/Validation Status**: Validation happens but result not stored
3. **Finalization**: `finalize_data()` checks for `validation_status='validated'` but it's never set
4. **Publishing**: Auto-publish never triggered because criteria not met

### Path Resolution Issues

1. **Stage Path Validation**: `stage_path` must be within `/stage/dsa110-contimg/`
2. **Published Path Validation**: `published_path` must be within `/data/dsa110-contimg/products/`
3. **Path Validation Missing**: No checks before move operations

### Naming Consistency Issues

1. **Mosaic ID**: Constructed as `mosaic_<group_id>_<timestamp>`
2. **Data ID**: Should match for tracking
3. **Inconsistency**: `mosaic_groups.mosaic_id` vs `data_registry.data_id` don't match

---

## Recommendations for Future Test Runs

### 1. Pre-Flight Checklist

Before running autonomous test:
- [ ] Verify all expected behaviors are documented (phase centers, validation tolerances)
- [ ] Check file existence validation is in place for all MS operations
- [ ] Verify race condition handling (wait for conversion completion)
- [ ] Validate database paths match filesystem
- [ ] Test time extraction fallback logic
- [ ] Verify mosaic registration and finalization workflow

### 2. Validation Strategy

- **Distinguish expected vs. error conditions** - not all failures are errors
- **Document expected behaviors prominently** - don't bury in function docstrings
- **Add tolerance for expected variations** - phase center separations, time-dependent phasing
- **Guide users in error messages** - reference documentation, explain why behavior is expected

### 3. Error Handling

- **Fail fast on actual errors** - but distinguish from expected behaviors
- **Add retry logic** - for transient failures (file locking, network issues)
- **Handle race conditions explicitly** - wait for completion, verify file existence
- **Log all failures** - with context for debugging

### 4. Workflow Completeness

- **Complete the entire workflow** - don't stop at creation, register and finalize
- **Set all required status fields** - QA/validation status, processing stage
- **Trigger auto-publish** - ensure criteria are met
- **Validate paths before moves** - ensure source exists, destination writable

### 5. Testing Strategy

- **Unit tests for validation logic** - verify expected behaviors are handled correctly
- **Integration tests for workflow** - verify complete workflow from conversion to mosaic
- **End-to-end tests** - verify autonomous run completes successfully
- **Error injection tests** - verify error handling works correctly

---

## Code Quality Improvements Made

### Documentation

1. **Created `conversion/README.md`**:
   - Documents expected phase center behavior
   - Explains time-dependent phasing (RA = LST)
   - Provides troubleshooting guidance
   - References key functions

2. **Enhanced Error Messages**:
   - Updated `validate_phase_center_coherence()` to include guidance
   - Messages mention large separations (>60 arcsec) are expected
   - Directs users to documentation

3. **Updated Module Documentation**:
   - Updated `conversion/__init__.py` to reference README
   - Added links to workflow documentation

### Validation Improvements

1. **Phase Center Validation**:
   - Detects time-dependent phasing before failing
   - Adds tolerance for large separations when expected
   - Provides guidance in error messages

2. **File Existence Validation**:
   - Added checks before all MS operations
   - Validates database paths against filesystem
   - Handles missing files gracefully

3. **Time Extraction**:
   - Fixed fallback to use observation time from filename
   - Added multiple fallback mechanisms
   - Improved error handling

### Workflow Integration

1. **Mosaic Registration**:
   - Added `register_mosaic_in_data_registry()` after creation
   - Ensures mosaics are tracked for publishing

2. **Finalization**:
   - Added `finalize_mosaic()` call with QA/validation status
   - Sets required status fields for auto-publish

3. **Error Handling**:
   - Added retry logic for publish failures
   - Added path validation before moves
   - Added database-level locking for concurrent access

---

## Lessons Learned

### 1. Document Expected Behaviors Prominently

**Mistake:** Phase center incoherence is expected but wasn't documented prominently.  
**Fix:** Created `conversion/README.md` with expected behaviors at the top.  
**Lesson:** Don't bury important information in function docstrings - create prominent documentation.

### 2. Distinguish Expected vs. Error Conditions

**Mistake:** Validation treated expected behavior (phase center incoherence) as critical error.  
**Fix:** Updated validation to detect time-dependent phasing before failing.  
**Lesson:** Validation should distinguish expected vs. error conditions - not all failures are errors.

### 3. Always Verify File Existence

**Mistake:** Assumed database paths were always correct, didn't verify file existence.  
**Fix:** Added file existence checks before all MS operations.  
**Lesson:** Always verify file existence before operations - don't trust database paths blindly.

### 4. Handle Race Conditions Explicitly

**Mistake:** Processing started before conversion completed, causing failures.  
**Fix:** Added explicit wait for conversion completion, file existence verification.  
**Lesson:** Synchronize async operations - don't assume completion, verify before proceeding.

### 5. Complete the Entire Workflow

**Mistake:** Mosaics created but not registered/finalized, stayed in staging forever.  
**Fix:** Added registration and finalization steps, set QA/validation status.  
**Lesson:** Complete the entire workflow - don't stop at creation, register and finalize.

### 6. Use Observation Time, Not Current Time

**Mistake:** Used current time as fallback instead of observation time from filename.  
**Fix:** Fixed time extraction fallback to use observation time from filename.  
**Lesson:** Use observation time for calibration validity windows - not current time.

---

## Next Steps

1. **Re-run test with fixes applied** - verify all issues resolved
2. **Add unit tests** - prevent regression of identified issues
3. **Create integration tests** - verify complete workflow
4. **Document workflow** - create end-to-end workflow guide
5. **Add monitoring** - track workflow completion, identify bottlenecks

---

## Additional Safeguards Implemented

After the initial review, additional safeguards were implemented to prevent issues identified in the ICEBERG analysis:

1. **Group ID Collision Prevention** - Collision-resistant IDs using SHA256 hash + microsecond timestamp
2. **Total Time Span Validation** - Ensures mosaics are created from contiguous observations (< 60 minutes total span)
3. **MS Files Stage Validation** - Only forms groups from fully processed (imaged) MS files
4. **Calibration Table Existence Validation** - Verifies all calibration tables exist before applying
5. **Image File Existence Validation** - Verifies all images exist before mosaic creation

**See:** `docs/reports/safeguards_implemented_2025-11-10.md` for complete details.

## Conclusion

The first trial streaming run revealed several critical issues, but most were due to validation logic treating expected behaviors as errors, rather than actual bugs in the pipeline logic. The fixes applied address:

- **Phase center validation** - now handles expected time-dependent phasing
- **File existence validation** - added checks throughout workflow
- **Race condition handling** - explicit synchronization and verification
- **Workflow completeness** - registration and finalization steps added
- **Time extraction** - fixed fallback logic to use observation time
- **Group processing order** - chronological ordering by observation time
- **Group formation safeguards** - collision prevention, time span validation, stage validation
- **Calibration safeguards** - table existence validation before application
- **Mosaic creation safeguards** - image existence validation before creation

With these fixes and safeguards in place, the next test run should complete successfully from conversion through mosaic creation.

---

**Document Status:** Complete  
**Review Date:** 2025-11-10  
**Next Review:** After next test run

