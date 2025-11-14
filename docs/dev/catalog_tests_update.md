# Catalog Query Tests Update

## Summary

Updated unit and smoke tests to cover the new `use_csv_fallback` parameter
behavior. Tests are intelligently placed in appropriate test files.

## Test Organization

### Unit Tests (`tests/unit/calibration/`)

1. **`test_query_nvss_sources.py`** (Updated)
   - `TestQueryNVSSSourcesCSVFallback` - Tests CSV fallback when
     `use_csv_fallback=True`
   - `TestQueryNVSSSourcesNoFallback` - Tests default behavior when
     `use_csv_fallback=False`
   - `TestQueryNVSSSourcesSmoke` - Smoke tests including CSV fallback disabled
     by default

2. **`test_query_rax_sources.py`** (New)
   - `TestQueryRAXSourcesSQLite` - SQLite query tests
   - `TestQueryRAXSourcesCSVFallback` - CSV fallback tests
   - `TestQueryRAXSourcesNoFallback` - No fallback tests

3. **`test_query_vlass_sources.py`** (New)
   - `TestQueryVLASSSourcesSQLite` - SQLite query tests
   - `TestQueryVLASSSourcesCSVFallback` - CSV fallback tests
   - `TestQueryVLASSSourcesNoFallback` - No fallback tests

## Test Coverage

### CSV Fallback Tests (`use_csv_fallback=True`)

- ✅ CSV fallback when SQLite fails
- ✅ CSV fallback with flux filtering
- ✅ CSV fallback with max_sources limit
- ✅ Error logging when CSV fallback is used

### No Fallback Tests (`use_csv_fallback=False`, default)

- ✅ Returns empty DataFrame when SQLite fails
- ✅ Error logging when SQLite fails
- ✅ Print statement when CSV fallback disabled
- ✅ Smoke test for default behavior

### Smoke Tests

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

## Running Tests

```bash
# Run all catalog query tests
pytest tests/unit/calibration/test_query_*_sources.py -v

# Run specific test class
pytest tests/unit/calibration/test_query_nvss_sources.py::TestQueryNVSSSourcesNoFallback -v

# Run smoke tests only
pytest tests/unit/calibration/test_query_nvss_sources.py::TestQueryNVSSSourcesSmoke -v
```

## Test Results

All tests pass successfully:

- ✅ 27 NVSS tests (including 3 new no-fallback tests)
- ✅ 6 RAX tests (new file)
- ✅ 6 VLASS tests (new file)
- ✅ Total: 39 catalog query tests

## Key Test Patterns

### Mocking SQLite Failures

```python
@patch("sqlite3.connect")
@patch("dsa110_contimg.calibration.catalogs.Path.exists")
def test_no_fallback_returns_empty(self, mock_exists, mock_connect):
    mock_exists.return_value = True  # Path found
    mock_connect.side_effect = Exception("Database connection failed")
    # Test behavior
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
    # Test CSV fallback behavior
```

## Related Documentation

- [CSV Fallback Disabled](csv_fallback_disabled.md) - Implementation details
- [Catalog Logging Migration](catalog_logging_migration.md) - Logging
  improvements
