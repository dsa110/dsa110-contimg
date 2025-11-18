# Strategic Test Failure Analysis

## Environment Verification

✅ **Python Environment**: Tests are running in casa6 conda environment

- Python executable: `/opt/miniforge/envs/casa6/bin/python`
- Python version: 3.11.13
- Environment path includes `casa6` ✓

✅ **Playwright**: Package is installed, but browsers need to be installed

- Playwright package: Installed ✓
- Browser executables: Missing ✗
- Fix needed: `playwright install chromium`

## Failure Categories Identified

### 1. Frontend/E2E Tests (Environment Setup Issue)

**Count**: ~50+ tests  
**Error Pattern**:
`playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist`

**Root Cause**: Playwright browsers not installed  
**Fix**:

```bash
/opt/miniforge/envs/casa6/bin/python -m playwright install chromium
```

**Affected Tests**:

- `tests/e2e/frontend/test_all_pages.py` (all tests)
- `tests/e2e/frontend/test_control.py` (all tests)
- `tests/e2e/frontend/test_dashboard.py` (all tests)
- `tests/e2e/frontend/test_sources.py` (all tests)
- `tests/e2e/frontend/test_page_smoke.py` (all tests)

**Priority**: Medium (these are integration tests, not unit tests)

---

### 2. Mock Setup Issues (Test Code Issue)

**Count**: ~10-15 tests  
**Error Pattern**: `AssertionError: assert <MagicMock ...> is None` or
`assert <MagicMock ...> == ...`

**Root Cause**: Tests using mocks incorrectly - mocks returning MagicMock
objects instead of expected values

**Affected Tests**:

- `tests/calibration/test_vla_catalogs.py::TestCSVCatalogFallback::test_csv_fallback_is_disabled_in_service`
  ✅ **FIXED** (now passes)
- `tests/conversion/test_calibrator_ms_service.py` (multiple tests)

**Example Issue**:

```python
# Test expects None but gets MagicMock
assert result is None  # Fails because result is MagicMock
```

**Fix Strategy**:

- Review mock patches in test files
- Ensure mocks return `None` when expected, not MagicMock objects
- Use `return_value=None` explicitly in mock configurations

**Priority**: High (these are unit tests that should pass)

---

### 3. Database/File Missing (Test Fixture Issue)

**Count**: ~10-20 tests  
**Error Pattern**: `FileNotFoundError`, database connection errors, SQLite
errors

**Root Cause**: Test fixtures not creating required databases/files

**Affected Tests**:

- `tests/conversion/test_hdf5_grouping.py` (multiple tests)
- `tests/database/test_hdf5_index.py::test_get_group_count_empty_db`

**Fix Strategy**:

- Review test fixtures
- Ensure fixtures create required databases/files before tests run
- Check if fixtures are being called correctly

**Priority**: High (these are unit tests)

---

### 4. Assertion Failures (Test Logic Issue)

**Count**: ~50+ tests  
**Error Pattern**: `AssertionError` with various messages

**Root Cause**: Test expectations may not match current code behavior

**Examples**:

- Tests expecting specific return values that have changed
- Tests expecting specific data structures that have been modified
- Tests expecting specific behavior that has been updated

**Fix Strategy**:

- Review failing assertions one by one
- Determine if code changed or test is wrong
- Update tests to match current code behavior

**Priority**: Medium-High (depends on whether code or tests need updating)

---

### 5. Import Errors (Environment/Dependency Issue)

**Count**: Minimal (if any)  
**Error Pattern**: `ImportError`, `ModuleNotFoundError`

**Status**: Not a major issue - casa6 environment appears to have required
packages

---

## Test Status Summary

From recent test run:

- **Total Tests**: ~1505 tests
- **Passed**: 1128 tests (75%)
- **Failed**: 199 tests (13%)
- **Errors**: 159 tests (11%)
- **Skipped**: 19 tests (1%)

## Recommended Action Plan

### Phase 1: Environment Setup (Quick Wins)

1. ✅ Install Playwright browsers
   ```bash
   /opt/miniforge/envs/casa6/bin/python -m playwright install chromium
   ```
   **Expected Impact**: Fixes ~50 frontend/e2e tests

### Phase 2: Mock Fixes (High Priority)

1. Fix mock configurations in `test_calibrator_ms_service.py`
2. Review and fix other mock-related failures **Expected Impact**: Fixes ~10-15
   unit tests

### Phase 3: Test Fixtures (High Priority)

1. Review and fix database/file fixture issues
2. Ensure all required test data is created **Expected Impact**: Fixes ~10-20
   tests

### Phase 4: Assertion Review (Medium Priority)

1. Systematically review assertion failures
2. Update tests to match current code behavior **Expected Impact**: Fixes
   remaining ~50+ tests

## Next Steps

1. **Immediate**: Install Playwright browsers to fix e2e tests
2. **Short-term**: Fix mock setup issues in unit tests
3. **Medium-term**: Review and fix test fixtures
4. **Long-term**: Review assertion failures systematically

## Notes

- Tests are confirmed to be running in casa6 environment ✓
- Many failures are environment setup issues, not code bugs
- Mock-related failures are test code issues, not production code issues
- Some tests may need updating after recent code changes (e.g., catalog loading
  changes)
