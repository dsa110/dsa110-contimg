# Running All Frontend Tests Simultaneously

This guide explains how to run all frontend E2E tests simultaneously, including
parallel execution options.

## Quick Start

### Run All Tests (Basic)

```bash
# Activate casa6 environment
conda activate casa6

# Run all frontend E2E tests
pytest tests/e2e/frontend/ -v
```

## Parallel Execution

### Using pytest-xdist (Recommended)

pytest-xdist is already in your `requirements-test.txt`, so you can run tests in
parallel:

```bash
# Run all tests with auto-detected worker count
pytest tests/e2e/frontend/ -v -n auto

# Run with specific number of workers
pytest tests/e2e/frontend/ -v -n 4

# Run with 8 workers (for powerful machines)
pytest tests/e2e/frontend/ -v -n 8
```

### Using the Test Runner Script

A convenience script is provided for running all tests:

```bash
# Run all tests in parallel (default: 4 workers)
./tests/e2e/frontend/run_all_tests.sh

# Run with 8 workers
./tests/e2e/frontend/run_all_tests.sh --workers 8

# Run in headed mode (see browser)
./tests/e2e/frontend/run_all_tests.sh --headed

# Run only critical tests
./tests/e2e/frontend/run_all_tests.sh --markers "e2e_critical"

# Use Firefox browser
./tests/e2e/frontend/run_all_tests.sh --browser firefox
```

## Test Suites

### 1. Comprehensive Test Suite (All Pages)

Tests all pages with full functionality checks:

```bash
pytest tests/e2e/frontend/test_all_pages.py -v
```

This test suite:

- Visits all major pages
- Checks for console errors
- Tests navigation between pages
- Verifies page content loads

### 2. Quick Smoke Tests (Fast)

Quick checks that pages load without errors:

```bash
pytest tests/e2e/frontend/test_page_smoke.py -v
```

This is faster and useful for quick validation.

### 3. Individual Page Tests

Run tests for specific pages:

```bash
# Dashboard tests
pytest tests/e2e/frontend/test_dashboard.py -v

# Control page tests
pytest tests/e2e/frontend/test_control.py -v
```

## Running All Tests with Different Options

### 1. Run All Tests in Parallel

```bash
pytest tests/e2e/frontend/ -v -n auto
```

### 2. Run All Tests with Specific Markers

```bash
# Only critical tests
pytest tests/e2e/frontend/ -v -m "e2e_critical"

# Exclude slow tests
pytest tests/e2e/frontend/ -v -m "not e2e_slow"

# Only UI interaction tests
pytest tests/e2e/frontend/ -v -m "e2e_ui"
```

### 3. Run All Tests with Headed Browser

```bash
PLAYWRIGHT_HEADLESS=false pytest tests/e2e/frontend/ -v
```

### 4. Run All Tests with Screenshots on Failure

```bash
pytest tests/e2e/frontend/ -v --screenshot=only-on-failure
```

### 5. Run All Tests with Video Recording

```bash
pytest tests/e2e/frontend/ -v --video=retain-on-failure
```

### 6. Run All Tests with HTML Report

```bash
pytest tests/e2e/frontend/ -v --html=test-results/report.html --self-contained-html
```

## Complete Test Run Command

Here's a comprehensive command that runs all tests with optimal settings:

```bash
conda activate casa6 && \
pytest tests/e2e/frontend/ \
    -v \
    -n auto \
    --tb=short \
    --maxfail=5 \
    --junitxml=test-results/frontend-e2e.xml \
    --html=test-results/frontend-e2e-report.html \
    --self-contained-html \
    --screenshot=only-on-failure \
    --video=retain-on-failure
```

## Test Organization

Tests are organized as follows:

```
tests/e2e/frontend/
├── test_all_pages.py          # Comprehensive test suite for all pages
├── test_page_smoke.py         # Quick smoke tests
├── test_dashboard.py          # Dashboard-specific tests
├── test_control.py             # Control page tests
└── run_all_tests.sh           # Convenience script
```

## Performance Tips

### 1. Optimal Worker Count

- **4 workers**: Good for most machines
- **8 workers**: For powerful machines with many cores
- **auto**: Let pytest-xdist decide based on CPU count

### 2. Test Selection

- Use markers to run only relevant tests
- Skip slow tests during development: `-m "not e2e_slow"`
- Run smoke tests for quick validation

### 3. Browser Selection

- **Chromium**: Fastest, recommended for most tests
- **Firefox**: For cross-browser testing
- **WebKit**: For Safari compatibility testing

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Frontend E2E Tests

on: [push, pull_request]

jobs:
  frontend-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: |
          conda install -c conda-forge playwright
          pip install -r requirements-test.txt
          playwright install chromium

      - name: Start services
        run: |
          # Start backend and frontend

      - name: Run all E2E tests
        env:
          FRONTEND_BASE_URL: http://localhost:5173
          API_URL: http://localhost:8000
          PLAYWRIGHT_HEADLESS: true
        run: |
          pytest tests/e2e/frontend/ -v -n 4 --junitxml=test-results/e2e.xml
```

## Troubleshooting

### Tests Run Too Slowly

- Increase worker count: `-n 8`
- Skip slow tests: `-m "not e2e_slow"`
- Use smoke tests: `pytest test_page_smoke.py`

### Out of Memory Errors

- Reduce worker count: `-n 2`
- Run tests sequentially: `-n 0`
- Close other applications

### Tests Are Flaky

- Increase timeouts in `playwright_config.py`
- Use `page.wait_for_load_state("networkidle")`
- Add retries: `--reruns 2`

### Browser Not Found

```bash
playwright install chromium
```

## See Also

- [Playwright Python Frontend Testing Guide](../dashboard/run-all-frontend-tests.md)
- [Quick Start Guide](../dashboard/run-all-frontend-tests.md)
- Test Directory README
