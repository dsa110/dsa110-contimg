# Playwright Python Quick Start Guide

This is a quick reference for using Playwright Python to test the DSA-110
dashboard frontend.

## Installation

### Using Conda-Forge (Recommended)

```bash
# 1. Activate casa6 environment
conda activate casa6

# 2. Install Playwright from conda-forge
conda install -c conda-forge playwright

# 3. Install pytest-playwright (not available on conda-forge)
pip install pytest-playwright

# 4. Install browser binaries
playwright install chromium
```

### Using pip (Alternative)

```bash
# 1. Activate casa6 environment
conda activate casa6

# 2. Install Playwright Python
pip install playwright pytest-playwright

# 3. Install browser binaries
playwright install chromium
```

## Quick Test Run

```bash
# Ensure frontend and backend are running, then:
pytest tests/e2e/frontend/test_dashboard.py -v
```

## What Was Created

### Documentation

- **`docs/how-to/playwright-python-frontend-testing.md`**: Complete guide with
  examples
- **`tests/e2e/frontend/README.md`**: Quick reference for the test directory

### Test Infrastructure

- **`tests/e2e/frontend/conftest.py`**: Pytest fixtures (browser, page, context)
- **`tests/e2e/frontend/playwright_config.py`**: Configuration settings

### Page Objects (Page Object Model)

- **`tests/e2e/frontend/pages/base_page.py`**: Base class for all pages
- **`tests/e2e/frontend/pages/dashboard_page.py`**: Dashboard page object
- **`tests/e2e/frontend/pages/control_page.py`**: Control page object

### Example Tests

- **`tests/e2e/frontend/test_dashboard.py`**: Dashboard page tests
- **`tests/e2e/frontend/test_control.py`**: Control page tests

### Configuration Updates

- **`pytest.ini`**: Added E2E test markers
- **`requirements-test.txt`**: Added Playwright dependencies

## Example Test

```python
import pytest
from playwright.sync_api import expect
from tests.e2e.frontend.pages.dashboard_page import DashboardPage

@pytest.mark.e2e
@pytest.mark.e2e_frontend
def test_dashboard_loads(page):
    """Test that dashboard loads successfully."""
    dashboard = DashboardPage(page)
    dashboard.navigate()
    expect(page).to_have_url(containing="/dashboard")
```

## Common Commands

```bash
# Run all frontend E2E tests
pytest tests/e2e/frontend/ -v

# Run specific test file
pytest tests/e2e/frontend/test_dashboard.py -v

# Run with browser visible
PLAYWRIGHT_HEADLESS=false pytest tests/e2e/frontend/ -v

# Run only critical tests
pytest tests/e2e/frontend/ -m "e2e_critical" -v

# Run with screenshots on failure
pytest tests/e2e/frontend/ --screenshot=only-on-failure -v
```

## Environment Variables

```bash
export FRONTEND_BASE_URL=http://localhost:5173
export API_URL=http://localhost:8000
export PLAYWRIGHT_HEADLESS=true
export PLAYWRIGHT_BROWSER=chromium
```

## Next Steps

1. **Add More Tests**: Create tests for other pages (Streaming, Sources,
   Mosaics, etc.)
2. **Improve Page Objects**: Add more helper methods and better selectors
3. **Add Data Test IDs**: Add `data-testid` attributes to frontend components
   for stable selectors
4. **Test User Workflows**: Test complete user journeys, not just page loads

## See Also

- [Complete Guide](playwright-python-frontend-testing.md): Detailed
  documentation
- [Test Directory README](../../tests/e2e/frontend/README.md): Test directory
  reference
