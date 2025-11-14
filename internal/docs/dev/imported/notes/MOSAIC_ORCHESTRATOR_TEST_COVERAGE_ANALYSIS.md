# Mosaic Orchestrator Test Coverage Analysis

## Overview

This document cross-references potential error scenarios identified in the
execution workflow with existing unit tests to identify:

1. **Coverage gaps**: Error scenarios without unit tests
2. **Ineffective tests**: Tests that don't properly validate error handling
3. **Missing test scenarios**: Critical paths that need additional testing

## Phase-by-Phase Analysis

### PHASE 1: Initialization

#### Potential Errors:

- Database connection failures (products.sqlite3, data_registry.sqlite3)
- Calibrator service initialization failures
- Missing environment variables (CONTIMG_INPUT_DIR, etc.)
- StreamingMosaicManager lazy initialization failures

#### Existing Tests:

- ✅ **test_mosaic_orchestrator.py**: `orchestrator` fixture creates
  orchestrator with temp databases
- ❌ **NO TEST**: Database connection failures
- ❌ **NO TEST**: Calibrator service initialization failures
- ❌ **NO TEST**: Missing environment variables
- ❌ **NO TEST**: StreamingMosaicManager initialization failures

#### Coverage Gap:

**Missing**: Tests for initialization failures. Current tests assume successful
initialization.

---

### PHASE 2: Transit Window Discovery

#### Potential Errors:

- No transits found → script exits with error
- Calibrator name mismatch → lookup fails
- Database connection issues → connection error
- Invalid transit time calculation

#### Existing Tests:

- ✅ **test_mosaic_orchestrator.py**:
  `test_find_earliest_incomplete_window_extracts_dec` - Tests successful Dec
  extraction
- ✅ **test_mosaic_orchestrator.py**:
  `test_find_earliest_incomplete_window_no_dec` - Tests missing Dec handling
- ✅ **test_mosaic_orchestrator.py**:
  `test_find_earliest_incomplete_window_no_bp_calibrator` - Tests missing BP
  calibrator
- ❌ **NO TEST**: `find_transit_centered_window` method (used by
  `create_mosaic_centered_on_calibrator`)
- ❌ **NO TEST**: No transits found scenario
- ❌ **NO TEST**: Calibrator name mismatch
- ❌ **NO TEST**: Database connection errors during transit lookup
- ❌ **NO TEST**: Invalid transit time calculation

#### Coverage Gap:

**CRITICAL**: `find_transit_centered_window` is NOT tested, but it's the core
method used by `create_mosaic_centered_on_calibrator`. Only
`find_earliest_incomplete_window` is tested.

---

### PHASE 3: MS File Availability & Conversion

#### Potential Errors:

- No HDF5 files in `/data/incoming/` for that window → conversion fails
- HDF5 files corrupted → conversion fails
- Disk space issues → conversion fails
- `hdf5_orchestrator` import errors → import failure
- Conversion takes a long time → script waits
- Pointing extraction failures during conversion
- Database update failures after conversion

#### Existing Tests:

- ✅ **test_mosaic_orchestrator.py**: `test_trigger_hdf5_conversion_success` -
  Tests successful conversion trigger (mocked)
- ✅ **test_mosaic_orchestrator.py**: `test_trigger_hdf5_conversion_failure` -
  Tests conversion failure handling (mocked)
- ✅ **test_mosaic_orchestrator.py**:
  `test_ensure_ms_files_in_window_existing_files` - Tests returning existing
  files
- ✅ **test_mosaic_orchestrator.py**:
  `test_ensure_ms_files_in_window_triggers_conversion` - Tests conversion
  triggering
- ✅ **test_products_pointing.py**: Multiple tests for pointing extraction and
  logging
- ❌ **NO TEST**: HDF5 file corruption scenarios
- ❌ **NO TEST**: Disk space issues
- ❌ **NO TEST**: Import errors for hdf5_orchestrator
- ❌ **NO TEST**: Pointing extraction failures during conversion
- ❌ **NO TEST**: Database update failures after conversion
- ❌ **NO TEST**: Conversion timeout scenarios

#### Coverage Gap:

**Partial**: Conversion triggering is tested, but edge cases (corruption, disk
space, import errors) are not. Pointing extraction is tested separately but not
integrated with conversion workflow.

---

### PHASE 4: Group Formation

#### Potential Errors:

- Database lock → SQLite error
- Invalid MS paths → group formation fails
- Missing `mosaic_groups` table → schema error
- Group ID collision
- Data registry registration failures

#### Existing Tests:

- ✅ **test_mosaic_orchestrator.py**:
  `test_create_mosaic_default_behavior_workflow` - Mocks
  `_form_group_from_ms_paths` (doesn't test actual implementation)
- ❌ **NO TEST**: Direct testing of `_form_group_from_ms_paths` method
- ❌ **NO TEST**: Database lock scenarios
- ❌ **NO TEST**: Invalid MS paths
- ❌ **NO TEST**: Missing `mosaic_groups` table
- ❌ **NO TEST**: Group ID collision
- ❌ **NO TEST**: Data registry registration failures

#### Coverage Gap:

**CRITICAL**: `_form_group_from_ms_paths` is mocked but never directly tested.
No error handling tests exist.

---

### PHASE 5: Calibration Solving

#### Potential Errors:

- Calibration MS file missing/corrupted → read error
- CASA tasks fail (`bandpass`, `gaincal`) → calibration error
- Skymodel missing → gain calibration fails
- BP calibrator lookup fails → `get_bandpass_calibrator_for_dec()` returns None
- CASA environment issues → task execution fails
- Calibration table registration failures

#### Existing Tests:

- ✅ **test_calibration_comprehensive.py**: Multiple calibration workflow tests
- ✅ **test_mosaic_orchestrator.py**:
  `test_find_earliest_incomplete_window_no_bp_calibrator` - Tests BP calibrator
  lookup failure
- ❌ **NO TEST**: `solve_calibration_for_group` method (StreamingMosaicManager)
- ❌ **NO TEST**: Calibration MS file corruption
- ❌ **NO TEST**: CASA task failures (bandpass, gaincal)
- ❌ **NO TEST**: Skymodel missing scenarios
- ❌ **NO TEST**: CASA environment issues
- ❌ **NO TEST**: Calibration table registration failures

#### Coverage Gap:

**CRITICAL**: `solve_calibration_for_group` is NOT tested. Calibration
comprehensive tests exist but don't cover StreamingMosaicManager's calibration
solving workflow.

---

### PHASE 6: Calibration Application

#### Potential Errors:

- Calibration tables missing → application fails
- MS file locked → write error
- CASA `applycal` fails → application error
- Database update fails → status inconsistency

#### Existing Tests:

- ❌ **NO TEST**: `apply_calibration_to_group` method (StreamingMosaicManager)
- ❌ **NO TEST**: Missing calibration tables
- ❌ **NO TEST**: MS file lock scenarios
- ❌ **NO TEST**: CASA applycal failures
- ❌ **NO TEST**: Database update failures

#### Coverage Gap:

**CRITICAL**: `apply_calibration_to_group` is NOT tested at all. No error
handling tests exist.

---

### PHASE 7: Imaging

#### Potential Errors:

- WSClean not found → subprocess error
- Insufficient memory → imaging fails
- Disk space issues → write failure
- Image registration fails → database error
- Existing image detection failures

#### Existing Tests:

- ✅ **test_imaging_mocked.py**: Multiple imaging tests with mocked WSClean
- ✅ **test_imaging_mocked.py**: `test_wsclean_command_structure` - Tests
  WSClean command
- ✅ **test_imaging_mocked.py**: `test_wsclean_development_tier_memory` - Tests
  memory handling
- ❌ **NO TEST**: `image_group` method (StreamingMosaicManager)
- ❌ **NO TEST**: WSClean not found scenarios
- ❌ **NO TEST**: Disk space issues
- ❌ **NO TEST**: Image registration failures
- ❌ **NO TEST**: Existing image detection failures

#### Coverage Gap:

**Partial**: Imaging logic is tested, but `image_group` workflow method is not.
Error handling for group imaging is missing.

---

### PHASE 8: Mosaic Creation

#### Potential Errors:

- Images missing → mosaic build fails
- Mosaic planning fails → grid calculation error
- `immath` fails → combination error
- Output directory permissions → write error
- Chronological validation failures

#### Existing Tests:

- ✅ **test_mosaic_bounds_calculation.py**: Mosaic bounds calculation tests
- ✅ **test_mosaic_coordinate_system.py**: Coordinate system tests
- ✅ **test_mosaic_shape_handling.py**: Shape handling tests
- ❌ **NO TEST**: `create_mosaic` method (StreamingMosaicManager)
- ❌ **NO TEST**: Missing images scenario
- ❌ **NO TEST**: Mosaic planning failures
- ❌ **NO TEST**: immath failures
- ❌ **NO TEST**: Output directory permission errors
- ❌ **NO TEST**: Chronological validation failures

#### Coverage Gap:

**CRITICAL**: `create_mosaic` method is NOT tested. Mosaic components are tested
separately but not the full workflow.

---

### PHASE 9: Validation & QA

#### Potential Errors:

- Validation fails → `qa_status='failed'`
- QA checks timeout → validation hangs
- Database update fails → status inconsistency

#### Existing Tests:

- ✅ **test_qa_base.py**: QA base functionality tests
- ✅ **test_qa_config.py**: QA configuration tests
- ✅ **test_data_registry_publish.py**: Multiple data registry tests
- ❌ **NO TEST**: Validation timeout scenarios
- ❌ **NO TEST**: Database update failures during QA

#### Coverage Gap:

**Partial**: QA functionality is tested, but timeout and database update failure
scenarios are not.

---

### PHASE 10: Publishing

#### Potential Errors:

- File move fails → permission error
- Target directory missing → path error
- Disk space on `/data/` → move fails
- Database update fails → status inconsistency

#### Existing Tests:

- ✅ **test_data_registry_publish.py**:
  `test_trigger_auto_publish_checks_max_attempts` - Tests max attempts
- ✅ **test_data_registry_publish.py**:
  `test_trigger_auto_publish_sets_publishing_status` - Tests status setting
- ✅ **test_data_registry_publish.py**:
  `test_trigger_auto_publish_prevents_concurrent_access` - Tests concurrency
- ✅ **test_data_registry_publish.py**:
  `test_successful_publish_clears_attempts` - Tests successful publish
- ❌ **NO TEST**: File move permission errors
- ❌ **NO TEST**: Target directory missing
- ❌ **NO TEST**: Disk space failures
- ❌ **NO TEST**: Database update failures during publish

#### Coverage Gap:

**Partial**: Publishing logic is tested, but file system error scenarios
(permissions, disk space, missing directories) are not.

---

### PHASE 11: Wait for Publication

#### Potential Errors:

- Publishing never completes → timeout after 24 hours
- File exists but status not updated → polling continues
- Database query fails → polling error

#### Existing Tests:

- ✅ **test_mosaic_orchestrator.py**:
  `test_create_mosaic_default_behavior_workflow` - Mocks `wait_for_published`
  (doesn't test actual implementation)
- ❌ **NO TEST**: Direct testing of `wait_for_published` method
- ❌ **NO TEST**: Timeout scenarios
- ❌ **NO TEST**: File exists but status not updated
- ❌ **NO TEST**: Database query failures during polling

#### Coverage Gap:

**CRITICAL**: `wait_for_published` is mocked but never directly tested. No
timeout or polling error tests exist.

---

### PHASE 12: Completion

#### Potential Errors:

- Return value handling failures
- Exit code incorrect

#### Existing Tests:

- ✅ **test_mosaic_orchestrator.py**:
  `test_create_mosaic_default_behavior_workflow` - Tests return value
- ✅ **test_mosaic_orchestrator.py**:
  `test_create_mosaic_default_behavior_no_window` - Tests None return
- ✅ **test_mosaic_orchestrator.py**:
  `test_create_mosaic_default_behavior_insufficient_ms` - Tests failure return
- ✅ **Coverage**: Return value handling is tested

#### Coverage Gap:

**None**: Return value handling is adequately tested.

---

## Summary: Critical Missing Tests

### High Priority (Critical Workflow Methods Not Tested):

1. **`find_transit_centered_window`** - Core method for calibrator-centered
   mosaics
2. **`_form_group_from_ms_paths`** - Group formation logic
3. **`_process_group_workflow`** - Full workflow orchestration
4. **`wait_for_published`** - Publication polling logic
5. **`solve_calibration_for_group`** (StreamingMosaicManager) - Calibration
   solving
6. **`apply_calibration_to_group`** (StreamingMosaicManager) - Calibration
   application
7. **`image_group`** (StreamingMosaicManager) - Group imaging workflow
8. **`create_mosaic`** (StreamingMosaicManager) - Mosaic creation workflow

### Medium Priority (Error Scenarios Not Tested):

1. Database connection failures (all phases)
2. File system errors (permissions, disk space, missing directories)
3. CASA task failures (bandpass, gaincal, applycal, immath)
4. Import errors (hdf5_orchestrator, CASA modules)
5. Timeout scenarios (conversion, validation, publishing)
6. Database lock scenarios
7. Invalid/corrupted file scenarios

### Low Priority (Edge Cases):

1. Environment variable handling
2. Concurrent access scenarios (beyond publishing)
3. Schema migration failures
4. Invalid input validation

## Recommendations

### Immediate Actions:

1. **Add unit tests for `find_transit_centered_window`**:
   - Test successful transit finding
   - Test no transits found
   - Test calibrator name mismatch
   - Test invalid transit time calculation

2. **Add unit tests for `_form_group_from_ms_paths`**:
   - Test successful group formation
   - Test database lock handling
   - Test invalid MS paths
   - Test group ID collision

3. **Add unit tests for `wait_for_published`**:
   - Test successful publication detection
   - Test timeout scenarios
   - Test file exists but status not updated
   - Test database query failures

4. **Add integration tests for StreamingMosaicManager methods**:
   - `solve_calibration_for_group` with mocked CASA tasks
   - `apply_calibration_to_group` with mocked CASA tasks
   - `image_group` with mocked WSClean
   - `create_mosaic` with mocked mosaic.cli

### Test Effectiveness Issues:

1. **Over-mocking**: Many tests mock entire workflows instead of testing actual
   implementations
   - Example: `test_create_mosaic_default_behavior_workflow` mocks all internal
     methods
   - **Fix**: Add integration tests that test actual implementations with mocked
     external dependencies

2. **Missing error path testing**: Most tests only test success paths
   - **Fix**: Add tests for each error scenario identified above

3. **Incomplete coverage**: Critical methods like `find_transit_centered_window`
   are not tested
   - **Fix**: Add tests for all public methods in MosaicOrchestrator

### Testing Strategy:

1. **Unit tests**: Test individual methods with mocked dependencies
2. **Integration tests**: Test method chains with mocked external systems (CASA,
   file system)
3. **Error injection tests**: Test error handling with injected failures
4. **End-to-end tests**: Test full workflow with synthetic data (already exists
   in integration tests)
