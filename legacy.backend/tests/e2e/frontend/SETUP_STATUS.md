# Frontend E2E Tests - Setup Status

## Current Status

:white_heavy_check_mark: **Test Infrastructure**: Complete

- Test files created
- Page Object Model implemented
- Fixtures configured
- Test suites ready

:warning: **Browser Installation**: Issue on Ubuntu 18.04

- Playwright doesn't support browser installation on Ubuntu 18.04
- Need to use system browser or Docker

:cross_mark: **Frontend Service**: Not running

- Frontend needs to be started before running tests

:white_heavy_check_mark: **Backend API**: Running

- API is accessible at http://localhost:8000

## What's Ready

### Test Files Created

1. **`test_all_pages.py`**: Comprehensive test suite for all 16 pages
2. **`test_page_smoke.py`**: Quick smoke tests
3. **`test_dashboard.py`**: Dashboard-specific tests
4. **`test_control.py`**: Control page tests

### Infrastructure

- Page Object Model classes
- Pytest fixtures for browser/page management
- Configuration system
- Test runner script

## To Run Tests

### Option 1: Use Docker (Recommended for Ubuntu 18.04)

The frontend already has Docker setup. Use the existing Docker Compose setup:

```bash
cd frontend
docker compose up -d
# Then run tests inside container or from host
```

### Option 2: Use System Browser

If you have a system browser installed:

```bash
# Set environment variable
export PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium-browser

# Or install system Chromium
sudo apt-get update
sudo apt-get install chromium-browser

# Then run tests
pytest tests/e2e/frontend/ -v
```

### Option 3: Start Frontend Manually

```bash
# Start frontend
cd frontend
conda activate casa6
npm run dev

# In another terminal, run tests
conda activate casa6
pytest tests/e2e/frontend/test_page_smoke.py -v
```

## Test Commands (Once Setup Complete)

```bash
# Run all tests in parallel
pytest tests/e2e/frontend/ -v -n auto

# Run comprehensive test suite
pytest tests/e2e/frontend/test_all_pages.py -v

# Run quick smoke tests
pytest tests/e2e/frontend/test_page_smoke.py -v

# Use convenience script
./tests/e2e/frontend/run_all_tests.sh
```

## Next Steps

1. **Start Frontend**: `cd frontend && npm run dev`
2. **Resolve Browser Issue**: Use Docker or system browser
3. **Run Tests**: Execute test commands above

## Notes

- Tests are fully configured and ready
- All test files are syntactically correct
- Page Object Model is implemented
- The only blockers are:
  - Frontend service not running
  - Browser binaries not available on Ubuntu 18.04

Once these are resolved, tests will run successfully.
