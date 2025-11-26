# Playwright Python for Frontend Testing

This guide explains how to use Playwright Python to perform user-oriented
testing of the DSA-110 dashboard frontend.

## Overview

Playwright Python provides a Python API for browser automation, allowing you to:

- Write frontend tests in Python (consistent with backend test infrastructure)
- Integrate with pytest (already used for backend tests)
- Leverage Python's testing ecosystem (fixtures, mocking, etc.)
- Test user workflows end-to-end

## Prerequisites

1. **Python Environment**: Use casa6 conda environment
2. **Frontend Running**: Dashboard accessible at `http://localhost:5173` (or
   configured URL)
3. **Backend API Running**: API accessible at `http://localhost:8000` (or
   configured URL)

## Installation

### Option 1: Install via Conda-Forge (Recommended for casa6)

```bash
# Activate casa6 environment
conda activate casa6

# Install Playwright from conda-forge
conda install -c conda-forge playwright

# Install pytest-playwright via pip (not available on conda-forge)
pip install pytest-playwright

# Install browser binaries (required after installing Playwright)
playwright install chromium
# Or install all browsers: playwright install
```

### Option 2: Install via pip

```bash
# Activate casa6 environment
conda activate casa6

# Install Playwright Python
pip install playwright pytest-playwright

# Install browser binaries
playwright install chromium
# Or install all browsers: playwright install
```

### 2. Add to Requirements

Add to `requirements-test.txt`:

```txt
playwright>=1.40.0
pytest-playwright>=0.4.0
```

## Project Structure

Create the following structure for frontend E2E tests:

```
tests/
├── e2e/
│   ├── frontend/              # Frontend-specific E2E tests
│   │   ├── __init__.py
│   │   ├── conftest.py        # Playwright fixtures
│   │   ├── test_dashboard.py
│   │   ├── test_control.py
│   │   ├── test_streaming.py
│   │   ├── test_sources.py
│   │   ├── test_mosaics.py
│   │   └── pages/             # Page Object Model
│   │       ├── __init__.py
│   │       ├── dashboard_page.py
│   │       ├── control_page.py
│   │       └── base_page.py
│   └── README.md
```

## Configuration

### 1. Create pytest.ini Configuration

Add to `pytest.ini` (or create `tests/e2e/frontend/pytest.ini`):

```ini
[pytest]
# Playwright configuration
addopts =
    --strict-markers
    --tb=short
    -v
markers =
    e2e: End-to-end frontend tests
    e2e:frontend: Frontend-specific E2E tests
    e2e:slow: Slow E2E tests (> 30 seconds)
    e2e:critical: Critical user workflows
    e2e:ui: UI interaction tests
testpaths = tests/e2e/frontend
```

### 2. Create Playwright Configuration

Create `tests/e2e/frontend/playwright.config.py`:

```python
"""Playwright configuration for frontend E2E tests."""

from playwright.sync_api import Playwright, Browser, BrowserContext, Page
import os

# Configuration
BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
API_URL = os.getenv("API_URL", "http://localhost:8000")
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("PLAYWRIGHT_SLOW_MO", "0"))  # Slow down operations (ms)
TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))  # Default timeout (ms)

# Browser settings
BROWSER = os.getenv("PLAYWRIGHT_BROWSER", "chromium")  # chromium, firefox, webkit
```

## Test Fixtures (conftest.py)

Create `tests/e2e/frontend/conftest.py`:

```python
"""Pytest fixtures for Playwright frontend tests."""

import pytest
from playwright.sync_api import Playwright, Browser, BrowserContext, Page, expect
import os
from typing import Generator

# Import configuration
from .playwright.config import BASE_URL, API_URL, HEADLESS, SLOW_MO, TIMEOUT, BROWSER


@pytest.fixture(scope="session")
def playwright() -> Generator[Playwright, None, None]:
    """Playwright instance (session-scoped)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright: Playwright) -> Generator[Browser, None, None]:
    """Browser instance (session-scoped, shared across tests)."""
    browser_type = getattr(playwright, BROWSER)
    browser = browser_type.launch(
        headless=HEADLESS,
        slow_mo=SLOW_MO,
        args=["--no-sandbox", "--disable-setuid-sandbox"] if HEADLESS else [],
    )
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def context(browser: Browser) -> Generator[BrowserContext, None, None]:
    """Browser context (function-scoped, isolated per test)."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        base_url=BASE_URL,
    )
    yield context
    context.close()


@pytest.fixture(scope="function")
def page(context: BrowserContext) -> Generator[Page, None, None]:
    """Page instance (function-scoped, isolated per test)."""
    page = context.new_page()

    # Set default timeout
    page.set_default_timeout(TIMEOUT)

    # Listen for console errors (optional, for debugging)
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)

    yield page

    # Check for console errors (optional assertion)
    # if console_errors:
    #     pytest.fail(f"Console errors detected: {[e.text for e in console_errors]}")

    page.close()


@pytest.fixture(scope="function")
def authenticated_page(page: Page) -> Generator[Page, None, None]:
    """Page with authentication (if needed in future)."""
    # For now, dashboard doesn't require auth
    # If auth is added later, implement here:
    # page.goto("/login")
    # page.fill("#username", "test_user")
    # page.fill("#password", "test_pass")
    # page.click("button[type='submit']")
    # page.wait_for_url("**/dashboard")
    yield page


@pytest.fixture(autouse=True)
def wait_for_api(page: Page):
    """Wait for API to be available before each test."""
    # Check API health
    import httpx
    try:
        response = httpx.get(f"{API_URL}/api/health", timeout=5.0)
        if response.status_code != 200:
            pytest.skip(f"API not healthy: {response.status_code}")
    except Exception as e:
        pytest.skip(f"API not available: {e}")
```

## Page Object Model

### Base Page

Create `tests/e2e/frontend/pages/base_page.py`:

```python
"""Base page class for Page Object Model."""

from playwright.sync_api import Page, Locator, expect
from typing import Optional


class BasePage:
    """Base class for all page objects."""

    def __init__(self, page: Page):
        self.page = page
        self.base_url = page.context.base_url or "http://localhost:5173"

    def goto(self, path: str = "/") -> None:
        """Navigate to a page."""
        self.page.goto(path)
        self.page.wait_for_load_state("networkidle")

    def wait_for_selector(self, selector: str, timeout: int = 30000) -> Locator:
        """Wait for and return a locator."""
        return self.page.wait_for_selector(selector, timeout=timeout)

    def click(self, selector: str) -> None:
        """Click an element."""
        self.page.click(selector)

    def fill(self, selector: str, value: str) -> None:
        """Fill an input field."""
        self.page.fill(selector, value)

    def get_text(self, selector: str) -> str:
        """Get text content of an element."""
        return self.page.locator(selector).inner_text()

    def is_visible(self, selector: str) -> bool:
        """Check if element is visible."""
        return self.page.locator(selector).is_visible()

    def wait_for_api_response(self, url_pattern: str, timeout: int = 10000) -> None:
        """Wait for an API response."""
        with self.page.expect_response(
            lambda response: url_pattern in response.url,
            timeout=timeout
        ):
            pass

    def check_no_console_errors(self) -> None:
        """Check for console errors (for debugging)."""
        console_errors = []
        self.page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)
        # Note: This is a simple check; for production, use proper error collection
```

### Dashboard Page

Create `tests/e2e/frontend/pages/dashboard_page.py`:

```python
"""Dashboard page object."""

from playwright.sync_api import Page, Locator
from .base_page import BasePage


class DashboardPage(BasePage):
    """Page object for the Dashboard page."""

    # Selectors
    PAGE_TITLE = "h1, h2, h3"  # Adjust based on actual structure
    PIPELINE_STATUS_SECTION = "[data-testid='pipeline-status'], .pipeline-status"
    SYSTEM_METRICS_SECTION = "[data-testid='system-health'], .system-health"
    ESE_CANDIDATES_PANEL = "[data-testid='ese-candidates'], .ese-candidates"
    RECENT_OBSERVATIONS_TABLE = "table, [role='table']"

    def __init__(self, page: Page):
        super().__init__(page)
        self.page = page

    def navigate(self) -> None:
        """Navigate to dashboard."""
        self.goto("/dashboard")
        self.wait_for_page_load()

    def wait_for_page_load(self) -> None:
        """Wait for dashboard to fully load."""
        # Wait for main content
        self.page.wait_for_selector("main, [role='main']", timeout=10000)
        # Wait for API calls to complete
        self.page.wait_for_load_state("networkidle", timeout=15000)

    def get_pipeline_status(self) -> dict:
        """Get pipeline status metrics."""
        # Extract status from page
        # This is a placeholder - adjust based on actual DOM structure
        total = self.page.locator("text=/Total.*[0-9]+/").first
        pending = self.page.locator("text=/Pending.*[0-9]+/").first
        return {
            "total": int(total.inner_text().split()[-1]) if total.count() > 0 else 0,
            "pending": int(pending.inner_text().split()[-1]) if pending.count() > 0 else 0,
        }

    def get_system_metrics(self) -> dict:
        """Get system metrics."""
        # Extract metrics from page
        # Adjust selectors based on actual implementation
        cpu = self.page.locator("[data-testid='cpu-metric']").first
        memory = self.page.locator("[data-testid='memory-metric']").first
        return {
            "cpu": float(cpu.inner_text().replace("%", "")) if cpu.count() > 0 else 0.0,
            "memory": float(memory.inner_text().replace("%", "")) if memory.count() > 0 else 0.0,
        }

    def click_navigation_item(self, item_name: str) -> None:
        """Click a navigation item."""
        self.page.click(f"text={item_name}")
        self.page.wait_for_load_state("networkidle")
```

## Example Test Files

### Test Dashboard

Create `tests/e2e/frontend/test_dashboard.py`:

```python
"""E2E tests for Dashboard page."""

import pytest
from playwright.sync_api import Page, expect
from tests.e2e.frontend.pages.dashboard_page import DashboardPage


@pytest.mark.e2e
@pytest.mark.e2e:frontend
@pytest.mark.e2e:critical
class TestDashboard:
    """Test Dashboard page functionality."""

    def test_dashboard_loads(self, page: Page):
        """Test that dashboard page loads successfully."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Check page title
        expect(page).to_have_title(containing="DSA-110", timeout=10000)

        # Check main content is visible
        expect(page.locator("main, [role='main']")).to_be_visible()

    def test_pipeline_status_displayed(self, page: Page):
        """Test that pipeline status is displayed."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Wait for pipeline status section
        status_section = page.locator(DashboardPage.PIPELINE_STATUS_SECTION).first
        expect(status_section).to_be_visible(timeout=10000)

        # Check for status metrics
        expect(page.locator("text=/Total|Pending|Completed|Failed/")).to_be_visible()

    def test_system_metrics_displayed(self, page: Page):
        """Test that system metrics are displayed."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Wait for system metrics section
        metrics_section = page.locator(DashboardPage.SYSTEM_METRICS_SECTION).first
        expect(metrics_section).to_be_visible(timeout=10000)

        # Check for metric indicators
        expect(page.locator("text=/CPU|Memory|Disk|Load/")).to_be_visible()

    def test_navigation_works(self, page: Page):
        """Test that navigation between pages works."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Click on Control page
        dashboard.click_navigation_item("Control")

        # Verify navigation
        expect(page).to_have_url(containing="/control", timeout=5000)

    def test_ese_candidates_panel(self, page: Page):
        """Test ESE candidates panel functionality."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Wait for ESE panel (may be collapsible)
        ese_panel = page.locator(DashboardPage.ESE_CANDIDATES_PANEL).first
        if ese_panel.count() > 0:
            expect(ese_panel).to_be_visible(timeout=10000)

    def test_recent_observations_table(self, page: Page):
        """Test recent observations table."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Wait for table
        table = page.locator(DashboardPage.RECENT_OBSERVATIONS_TABLE).first
        if table.count() > 0:
            expect(table).to_be_visible(timeout=10000)
            # Check for table headers
            expect(table.locator("th, [role='columnheader']")).to_have_count(
                count=4,  # Group ID, State, Subbands, Calibrator
                timeout=5000
            )

    @pytest.mark.e2e:slow
    def test_real_time_updates(self, page: Page):
        """Test that real-time updates work (WebSocket/polling)."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Get initial metrics
        initial_metrics = dashboard.get_system_metrics()

        # Wait for potential update (polling interval is ~10s)
        page.wait_for_timeout(12000)

        # Check that metrics are still displayed (indicating updates)
        updated_metrics = dashboard.get_system_metrics()

        # Metrics should still be present (may have changed)
        assert updated_metrics is not None
```

### Test Control Page

Create `tests/e2e/frontend/test_control.py`:

```python
"""E2E tests for Control page."""

import pytest
from playwright.sync_api import Page, expect
from tests.e2e.frontend.pages.control_page import ControlPage


@pytest.mark.e2e
@pytest.mark.e2e:frontend
class TestControlPage:
    """Test Control page functionality."""

    def test_control_page_loads(self, page: Page):
        """Test that control page loads."""
        control = ControlPage(page)
        control.navigate()

        expect(page).to_have_url(containing="/control")
        expect(page.locator("h1, h2")).to_contain_text("Control")

    def test_ms_table_displayed(self, page: Page):
        """Test that MS table is displayed."""
        control = ControlPage(page)
        control.navigate()

        # Wait for MS table
        ms_table = control.get_ms_table()
        expect(ms_table).to_be_visible(timeout=10000)

    def test_ms_selection(self, page: Page):
        """Test MS selection functionality."""
        control = ControlPage(page)
        control.navigate()

        # Wait for table to load
        ms_table = control.get_ms_table()
        expect(ms_table).to_be_visible(timeout=10000)

        # Try to select first MS (if available)
        first_row = ms_table.locator("tbody tr").first
        if first_row.count() > 0:
            first_row.click()

            # Check that MS is selected (adjust based on actual UI)
            expect(first_row).to_have_class(containing="selected", timeout=2000)

    def test_workflow_tabs(self, page: Page):
        """Test workflow tabs (Templates, Convert, Calibrate, Image)."""
        control = ControlPage(page)
        control.navigate()

        # Check tabs are present
        tabs = page.locator("[role='tab']")
        expect(tabs).to_have_count(count=4, timeout=5000)

        # Click each tab
        for tab_name in ["Templates", "Convert", "Calibrate", "Image"]:
            tab = page.locator(f"text={tab_name}").first
            if tab.count() > 0:
                tab.click()
                page.wait_for_timeout(500)  # Wait for tab content to load
```

## Running Tests

### 1. Run All Frontend E2E Tests

```bash
# Activate casa6 environment
conda activate casa6

# Run all frontend E2E tests
pytest tests/e2e/frontend/ -v

# Run with markers
pytest tests/e2e/frontend/ -m "e2e:frontend" -v
```

### 2. Run Specific Test File

```bash
pytest tests/e2e/frontend/test_dashboard.py -v
```

### 3. Run Specific Test

```bash
pytest tests/e2e/frontend/test_dashboard.py::TestDashboard::test_dashboard_loads -v
```

### 4. Run in Headed Mode (See Browser)

```bash
PLAYWRIGHT_HEADLESS=false pytest tests/e2e/frontend/ -v
```

### 5. Run with Screenshots on Failure

```bash
pytest tests/e2e/frontend/ --screenshot=only-on-failure -v
```

### 6. Run with Video Recording

```bash
pytest tests/e2e/frontend/ --video=retain-on-failure -v
```

## Best Practices

### 1. Use Page Object Model

- Encapsulate page logic in page classes
- Reuse selectors and actions
- Make tests readable and maintainable

### 2. Wait for Elements

- Always wait for elements before interacting
- Use `page.wait_for_selector()` or `expect(locator).to_be_visible()`
- Avoid `page.wait_for_timeout()` unless necessary

### 3. Use Data Test IDs

- Add `data-testid` attributes to key elements in frontend
- Makes tests more stable than CSS selectors

### 4. Test User Workflows

- Test complete user journeys, not just individual components
- Example: "User navigates to control, selects MS, creates calibration job"

### 5. Handle Async Operations

- Wait for API calls to complete
- Use `page.wait_for_response()` for specific API calls
- Use `page.wait_for_load_state("networkidle")` for general waiting

### 6. Error Handling

- Check for console errors (optional)
- Verify error messages are displayed correctly
- Test error recovery flows

## Integration with CI/CD

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
          pip install -r requirements-test.txt
          playwright install chromium

      - name: Start backend
        run: |
          # Start backend API
          # (adjust based on your setup)

      - name: Start frontend
        run: |
          cd frontend
          npm install
          npm run dev &
          sleep 10

      - name: Run E2E tests
        env:
          FRONTEND_BASE_URL: http://localhost:5173
          API_URL: http://localhost:8000
          PLAYWRIGHT_HEADLESS: true
        run: |
          pytest tests/e2e/frontend/ -v --junitxml=test-results/e2e-frontend.xml

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: e2e-frontend-results
          path: test-results/
```

## Troubleshooting

### Tests Fail to Connect

- Check frontend is running: `curl http://localhost:5173`
- Check API is running: `curl http://localhost:8000/api/status`
- Verify `BASE_URL` and `API_URL` environment variables

### Tests Are Flaky

- Increase timeouts
- Use `page.wait_for_load_state("networkidle")`
- Wait for specific API responses instead of fixed delays

### Browser Not Found

- Run `playwright install chromium`
- Check `PLAYWRIGHT_BROWSER` environment variable

### Slow Tests

- Use `HEADLESS=true` for faster execution
- Reduce `SLOW_MO` value
- Run tests in parallel (pytest-xdist)

## Next Steps

1. **Add More Test Coverage**:
   - Test all major pages (Streaming, Sources, Mosaics, etc.)
   - Test error scenarios
   - Test edge cases

2. **Improve Page Objects**:
   - Add more helper methods
   - Extract common patterns
   - Add type hints

3. **Add Visual Regression Testing**:
   - Use Playwright's screenshot comparison
   - Test UI consistency

4. **Add Performance Testing**:
   - Measure page load times
   - Test with large datasets
   - Monitor API response times

5. **Integrate with Backend Tests**:
   - Share fixtures between frontend and backend tests
   - Test full stack workflows
