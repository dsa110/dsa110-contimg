"""Pytest fixtures for Playwright frontend tests."""

# Import configuration
import sys
from pathlib import Path
from typing import Generator

import httpx
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, Playwright

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from tests.e2e.frontend.playwright_config import (
        API_URL,
        BASE_URL,
        BROWSER,
        HEADLESS,
        SLOW_MO,
        TIMEOUT,
    )
except ImportError:
    # Fallback: import directly
    import os

    BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5174")
    API_URL = os.getenv("API_URL", "http://localhost:8000")
    HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
    SLOW_MO = int(os.getenv("PLAYWRIGHT_SLOW_MO", "0"))
    TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))
    BROWSER = os.getenv("PLAYWRIGHT_BROWSER", "chromium")


@pytest.fixture(scope="session")
def playwright() -> Generator[Playwright, None, None]:
    """Playwright instance (session-scoped)."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        yield p


@pytest.fixture(scope="session")
def browser(playwright: Playwright) -> Generator[Browser, None, None]:
    """Browser instance (session-scoped, shared across tests)."""
    import os

    browser_type = getattr(playwright, BROWSER)

    # For Ubuntu 18.04, try to use system browser if Playwright browsers aren't available
    launch_options = {
        "headless": HEADLESS,
        "slow_mo": SLOW_MO,
        "args": ["--no-sandbox", "--disable-setuid-sandbox"] if HEADLESS else [],
    }

    # Try to use system Chromium on Ubuntu 18.04
    if BROWSER == "chromium":
        system_chromium = (
            os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or "/usr/bin/chromium-browser"
        )
        if os.path.exists(system_chromium):
            launch_options["executable_path"] = system_chromium

    try:
        browser = browser_type.launch(**launch_options)
    except Exception as e:
        # If launch fails, try with system browser
        if BROWSER == "chromium" and "executable_path" not in launch_options:
            system_chromium = "/usr/bin/chromium-browser"
            if os.path.exists(system_chromium):
                launch_options["executable_path"] = system_chromium
                browser = browser_type.launch(**launch_options)
            else:
                raise
        else:
            raise

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
    # Uncomment to fail tests on console errors:
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
    try:
        response = httpx.get(f"{API_URL}/api/health", timeout=5.0)
        if response.status_code != 200:
            pytest.skip(f"API not healthy: {response.status_code}")
    except Exception as e:
        pytest.skip(f"API not available: {e}")
