"""Quick smoke tests for all pages - minimal checks for fast execution.

These tests verify pages load without errors but don't test full functionality.
Useful for quick validation of all pages.
"""

import pytest
from playwright.sync_api import Page, expect

# Core pages that must work
CORE_PAGES = [
    "/dashboard",
    "/control",
    "/streaming",
    "/pipeline",
    "/data",
    "/health",
]

# Secondary pages
SECONDARY_PAGES = [
    "/sources",
    "/mosaics",
    "/sky",
    "/qa",
    "/events",
    "/cache",
    "/operations",
    "/calibration",
    "/ms-browser",
    "/carta",
]


@pytest.mark.e2e
@pytest.mark.e2e_frontend
class TestPageSmoke:
    """Quick smoke tests for page accessibility."""

    @pytest.mark.parametrize("route", CORE_PAGES)
    def test_core_page_smoke(self, page: Page, route: str):
        """Quick smoke test for core pages."""
        # Navigate
        response = page.goto(route, wait_until="domcontentloaded", timeout=10000)

        # Should not be 404 or 500
        assert response.status < 400, f"Page {route} returned status {response.status}"

        # Should have content
        body = page.locator("body")
        expect(body).to_be_visible(timeout=5000)
        assert len(body.inner_text()) > 10, f"Page {route} appears empty"

    @pytest.mark.parametrize("route", SECONDARY_PAGES)
    def test_secondary_page_smoke(self, page: Page, route: str):
        """Quick smoke test for secondary pages."""
        # Navigate
        response = page.goto(route, wait_until="domcontentloaded", timeout=10000)

        # Should not be 404 or 500
        assert response.status < 400, f"Page {route} returned status {response.status}"

        # Should have content
        body = page.locator("body")
        expect(body).to_be_visible(timeout=5000)
        assert len(body.inner_text()) > 10, f"Page {route} appears empty"
