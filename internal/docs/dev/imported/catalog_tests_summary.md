# Catalog Query Tests - Summary

## Test Organization

### Unit Tests (`tests/unit/calibration/`)

All tests are intelligently placed in dedicated test files:

1. **`test_query_nvss_sources.py`** (Updated)
   - `TestQueryNVSSSourcesSQLite` - SQLite query tests (5 tests)
   - `TestQueryNVSSSourcesCSVFallback` - CSV fallback when
     `use_csv_fallback=True` (3 tests)
   - `TestQueryNVSSSourcesNoFallback` - Default behavior when
     `use_csv_fallback=False` (3 tests) ✨ NEW
   - `TestQueryNVSSSourcesErrorHandling` - Error handling tests (5 tests)
   - `TestQueryNVSSSourcesReturnFormat` - Return format validation (3 tests)
   - `TestQueryNVSSSourcesIntegration` - Integration tests (1 test)
   - `TestQueryNVSSSourcesSmoke` - Smoke tests including CSV fallback disabled
     (7 tests)

2. **`test_query_rax_sources.py`** (New)
   - `TestQueryRAXSourcesSQLite` - SQLite query tests (1 test)
   - `TestQueryRAXSourcesCSVFallback` - CSV fallback tests (1 test)
   - `TestQueryRAXSourcesNoFallback` - No fallback tests (2 tests)

3. **`test_query_vlass_sources.py`** (New)
   - `TestQueryVLASSSourcesSQLite` - SQLite query tests (1 test)
   - `TestQueryVLASSSourcesCSVFallback` - CSV fallback tests (1 test)
   - `TestQueryVLASSSourcesNoFallback` - No fallback tests (2 tests)

## Test Coverage Summary

### Total Tests: 35

- **NVSS**: 27 tests (including 3 new no-fallback tests)
- **RAX**: 6 tests (new file)
- **VLASS**: 6 tests (new file)

### Test Categories

#### CSV Fallback Tests (`use_csv_fallback=True`)

- ✅ CSV fallback when SQLite fails
- ✅ CSV fallback with flux filtering
- ✅ CSV fallback with max_sources limit
- ✅ Error logging when CSV fallback is used

#### No Fallback Tests (`use_csv_fallback=False`, default)

- ✅ Returns empty DataFrame when SQLite fails
- ✅ Error logging when SQLite fails
- ✅ Print statement when CSV fallback disabled
- ✅ Handles case when no database path found

#### Smoke Tests

- ✅ CSV fallback disabled by default
- ✅ Basic query functionality
- ✅ Performance characteristics
- ✅ Edge case coordinates
- ✅ Result consistency

## Test Design Principles

1. **Speed**: Tests use mocks to avoid actual database/CSV I/O
2. **Isolation**: Each test is independent with proper fixtures
3. **Targeted**: Tests focus on specific behaviors (fallback vs no fallback)
4. **Error Handling**: Tests verify logging and error messages
5. **Validation**: Tests validate both success and failure paths

## Key Test Patterns

### Mocking SQLite Failures (No Fallback)

```python
@patch("sqlite3.connect")
@patch("dsa110_contimg.calibration.catalogs.Path.exists")
def test_no_fallback_returns_empty(self, mock_exists, mock_connect):
    mock_exists.return_value = True  # Path found
    mock_connect.side_effect = Exception("Database connection failed")
    df = query_nvss_sources(ra_deg=83.5, dec_deg=54.6, radius_deg=0.2)
    assert len(df) == 0  # Empty DataFrame returned
```

### Mocking CSV Fallback

```python
@patch("dsa110_contimg.calibration.catalogs.read_nvss_catalog")
@patch("sqlite3.connect")
@patch("dsa110_contimg.calibration.catalogs.Path.exists")
def test_csv_fallback(self, mock_exists, mock_connect, mock_read_nvss):
    mock_exists.return_value = True
    mock_connect.side_effect = Exception("Database connection failed")
    mock_read_nvss.return_value = mock_df
    df = query_nvss_sources(..., use_csv_fallback=True)
    assert len(df) > 0  # CSV fallback used
```

## Running Tests

```bash
# Run all catalog query tests
pytest tests/unit/calibration/test_query_*_sources.py -v

# Run specific test class
pytest tests/unit/calibration/test_query_nvss_sources.py::TestQueryNVSSSourcesNoFallback -v

# Run smoke tests only
pytest tests/unit/calibration/test_query_nvss_sources.py::TestQueryNVSSSourcesSmoke -v

# Run with coverage
pytest tests/unit/calibration/test_query_*_sources.py --cov=dsa110_contimg.calibration.catalogs
```

## Test Results

✅ **All 35 tests pass successfully**

- 27 NVSS tests (including 3 new no-fallback tests)
- 6 RAX tests (new file)
- 6 VLASS tests (new file)
- 2 tests updated for new behavior

## Test Placement Rationale

### Unit Tests (`tests/unit/calibration/`)

- **Location**: `tests/unit/calibration/test_query_*_sources.py`
- **Rationale**:
  - Tests are unit-level (isolated, mocked dependencies)
  - Tests specific calibration catalog functions
  - Fast execution (<1s per test file)
  - No external dependencies required

### Smoke Tests (within unit test files)

- **Location**: `TestQueryNVSSSourcesSmoke` class in
  `test_query_nvss_sources.py`
- **Rationale**:
  - End-to-end validation of real-world scenarios
  - May use actual databases if available
  - Validates performance and consistency
  - Still fast enough for unit test suite

## Related Documentation

- [CSV Fallback Disabled](csv_fallback_disabled.md) - Implementation details
- [Catalog Logging Migration](catalog_logging_migration.md) - Logging
  improvements
- [Catalog Tests Update](catalog_tests_update.md) - Detailed test update notes
