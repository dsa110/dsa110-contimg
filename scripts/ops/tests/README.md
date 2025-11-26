# Test Scripts

Test scripts and test utilities for the DSA-110 pipeline.

## Running Tests

### Quick Test Commands

```bash
# Run all tests
./utils/run-tests.sh

# Run tests in Docker
./utils/run-tests-docker.sh

# Run Playwright tests
./utils/run-playwright-python-tests.sh

# Run specific test file
python tests/test_pipeline_endpoints.py
```

### Test Organization

- **`organize-tests.sh`** - Organize test files by taxonomy
- **`reorganize-tests-by-taxonomy.sh`** - Reorganize tests into categories
- **`test-organization-enforcer.sh`** - Enforce test organization rules
- **`test-impacted.sh`** - Run tests impacted by changes

### Test Utilities

- **`pytest-safe.sh`** - Safe pytest runner with error detection
- **`test-template.py`** - Template for creating new test files
- **`comprehensive_test.py`** - Comprehensive test suite

## Test Categories

Tests are organized by functionality:

- **API Tests**: `test_*_endpoints.py`, `test_*_api.py`
- **Integration Tests**: `test_*_e2e.py`, `test_end_to_end.sh`
- **Unit Tests**: `test_*.py` (various modules)
- **Playwright Tests**: `test_*_playwright.*`

## Adding New Tests

1. Use `test-template.py` as a starting point
2. Place in appropriate category directory
3. Follow naming convention: `test_<module>_<feature>.py`
4. Run `test-organization-enforcer.sh` to validate organization
