# Frontend E2E Tests with Playwright Python

This directory contains end-to-end tests for the DSA-110 dashboard frontend
using Playwright Python.

## Quick Start

### 1. Install Dependencies

**Option A: Using Conda-Forge (Recommended)**

```bash
# Activate casa6 environment
conda activate casa6

# Install Playwright from conda-forge
conda install -c conda-forge playwright

# Install pytest-playwright (not available on conda-forge)
pip install pytest-playwright

# Install browser binaries
playwright install chromium
```

**Option B: Using pip**

```bash
# Activate casa6 environment
conda activate casa6

# Install Playwright Python
pip install playwright pytest-playwright

# Install browser binaries
playwright install chromium
```

### 2. Ensure Services Are Running

- **Frontend Dev**: `http://localhost:5174` (or set `FRONTEND_BASE_URL`)
- **Frontend Production**: `http://localhost:3210`
- **Backend API**: `http://localhost:8000` (or set `API_URL`)

### 3. Run Tests

**Run All Tests Simultaneously (Recommended)**

```bash
# Run all tests in parallel (fastest)
pytest tests/e2e/frontend/ -v -n auto

# Or use the convenience script
./tests/e2e/frontend/run_all_tests.sh
```

**Run Specific Test Suites**

```bash
# Comprehensive test suite (all pages)
pytest tests/e2e/frontend/test_all_pages.py -v

# Quick smoke tests (fast)
pytest tests/e2e/frontend/test_page_smoke.py -v

# Individual page tests
pytest tests/e2e/frontend/test_dashboard.py -v
pytest tests/e2e/frontend/test_control.py -v
```

**Other Options**

```bash
# Run in headed mode (see browser)
PLAYWRIGHT_HEADLESS=false pytest tests/e2e/frontend/ -v

# Run with markers
pytest tests/e2e/frontend/ -m "e2e_frontend" -v

# Run only critical tests
pytest tests/e2e/frontend/ -m "e2e_critical" -v

# Exclude slow tests
pytest tests/e2e/frontend/ -m "not e2e_slow" -v
```

## Test Structure

```
tests/e2e/frontend/
├── __init__.py
├── conftest.py              # Pytest fixtures (browser, page, etc.)
├── playwright_config.py      # Configuration (URLs, timeouts, etc.)
├── test_dashboard.py        # Dashboard page tests
├── test_control.py           # Control page tests
└── pages/                    # Page Object Model
    ├── __init__.py
    ├── base_page.py          # Base page class
    ├── dashboard_page.py     # Dashboard page object
    └── control_page.py       # Control page object
```

## Configuration

Set environment variables to configure test behavior:

```bash
# Frontend URL
export FRONTEND_BASE_URL=http://localhost:5174

# Backend API URL
export API_URL=http://localhost:8000

# Browser settings
export PLAYWRIGHT_HEADLESS=true  # false to see browser
export PLAYWRIGHT_BROWSER=chromium  # chromium, firefox, webkit
export PLAYWRIGHT_SLOW_MO=0  # Slow down operations (ms)
export PLAYWRIGHT_TIMEOUT=30000  # Default timeout (ms)
```

## Writing New Tests

### 1. Create Page Object (if needed)

```python
# tests/e2e/frontend/pages/my_page.py
from tests.e2e.frontend.pages.base_page import BasePage

class MyPage(BasePage):
    def navigate(self):
        self.goto("/my-page")
```

### 2. Write Test

```python
# tests/e2e/frontend/test_my_page.py
import pytest
from playwright.sync_api import expect
from tests.e2e.frontend.pages.my_page import MyPage

@pytest.mark.e2e
@pytest.mark.e2e_frontend
class TestMyPage:
    def test_my_page_loads(self, page):
        my_page = MyPage(page)
        my_page.navigate()
        expect(page).to_have_url(containing="/my-page")
```

## Best Practices

1. **Use Page Object Model**: Encapsulate page logic in page classes
2. **Wait for Elements**: Always wait before interacting
3. **Use Data Test IDs**: Add `data-testid` to key elements in frontend
4. **Test User Workflows**: Test complete journeys, not just components
5. **Handle Async**: Wait for API calls and network idle

## Troubleshooting

### Tests Fail to Connect

- Check frontend: `curl http://localhost:5173`
- Check API: `curl http://localhost:8000/api/status`
- Verify environment variables

### Browser Not Found

```bash
playwright install chromium
```

### Flaky Tests

- Increase timeouts
- Use `page.wait_for_load_state("networkidle")`
- Wait for specific API responses

## Documentation

See
[docs/how-to/playwright-python-frontend-testing.md](../../../docs/how-to/playwright-python-frontend-testing.md)
for complete guide.
