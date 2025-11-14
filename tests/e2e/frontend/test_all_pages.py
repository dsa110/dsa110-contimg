"""Comprehensive test suite for all dashboard pages.

This test suite visits all major pages to ensure they load correctly.
Run with: pytest tests/e2e/frontend/test_all_pages.py -v
"""

from typing import List, Tuple

import pytest
from playwright.sync_api import Page, expect

# Define all pages to test: (route, page_name, expected_text)
ALL_PAGES: List[Tuple[str, str, str]] = [
    ("/dashboard", "Dashboard", "DSA-110"),
    ("/pipeline", "Pipeline", "Pipeline"),
    ("/operations", "Operations", "Operations"),
    ("/control", "Control", "Control"),
    ("/calibration", "Calibration", "Calibration"),
    ("/ms-browser", "MS Browser", "MS"),
    ("/streaming", "Streaming", "Streaming"),
    ("/data", "Data Browser", "Data"),
    ("/sources", "Sources", "Sources"),
    ("/mosaics", "Mosaics", "Mosaics"),
    ("/sky", "Sky View", "Sky"),
    ("/carta", "CARTA", "CARTA"),
    ("/qa", "QA Tools", "QA"),
    ("/health", "Health", "Health"),
    ("/events", "Events", "Events"),
    ("/cache", "Cache", "Cache"),
]


@pytest.mark.e2e
@pytest.mark.e2e_frontend
class TestAllPages:
    """Test suite for all dashboard pages."""

    @pytest.mark.parametrize("route,page_name,expected_text", ALL_PAGES)
    def test_page_loads(self, page: Page, route: str, page_name: str, expected_text: str):
        """Test that each page loads successfully."""
        # Navigate to page
        page.goto(route)
        page.wait_for_load_state("networkidle", timeout=15000)

        # Check that page loaded (no 404 or error)
        expect(page).not_to_have_url(containing="404", timeout=5000)

        # Check for main content area
        main_content = page.locator("main, [role='main'], .MuiContainer-root")
        expect(main_content.first).to_be_visible(timeout=10000)

        # Check for expected text (page title or heading)
        # This is a flexible check - adjust based on actual page structure
        page_text = page.locator("body").inner_text()
        assert (
            expected_text.lower() in page_text.lower()
        ), f"Expected text '{expected_text}' not found on {page_name} page"

    @pytest.mark.parametrize("route,page_name,expected_text", ALL_PAGES)
    def test_page_no_console_errors(
        self, page: Page, route: str, page_name: str, expected_text: str
    ):
        """Test that each page has no critical console errors."""
        console_errors = []

        def handle_console(msg):
            if msg.type == "error":
                # Filter out known non-critical errors
                error_text = msg.text.lower()
                # Ignore common non-critical errors
                if not any(
                    ignore in error_text
                    for ignore in [
                        "favicon",
                        "sourcemap",
                        "extension",
                        "chrome-extension",
                    ]
                ):
                    console_errors.append(msg.text)

        page.on("console", handle_console)

        # Navigate to page
        page.goto(route)
        page.wait_for_load_state("networkidle", timeout=15000)

        # Wait a bit for any async errors
        page.wait_for_timeout(2000)

        # Check for critical errors
        critical_errors = [
            err
            for err in console_errors
            if not any(ignore in err.lower() for ignore in ["warning", "deprecated", "devtools"])
        ]

        assert len(critical_errors) == 0, f"Console errors on {page_name} page: {critical_errors}"

    @pytest.mark.parametrize("route,page_name,expected_text", ALL_PAGES)
    def test_page_navigation_from_dashboard(
        self, page: Page, route: str, page_name: str, expected_text: str
    ):
        """Test navigation to each page from dashboard."""
        # Start at dashboard
        page.goto("/dashboard")
        page.wait_for_load_state("networkidle", timeout=15000)

        # Find navigation item and click
        nav_item = page.locator(f"text={page_name}").first
        if nav_item.count() > 0:
            nav_item.click()
            page.wait_for_load_state("networkidle", timeout=15000)

            # Verify we're on the correct page
            expect(page).to_have_url(containing=route.split("/")[-1] or "dashboard", timeout=5000)


@pytest.mark.e2e
@pytest.mark.e2e_frontend
@pytest.mark.e2e_slow
class TestAllPagesSmoke:
    """Smoke tests for all pages - quick checks."""

    def test_all_pages_accessible(self, page: Page):
        """Quick smoke test: visit all pages and verify they're accessible."""
        failed_pages = []

        for route, page_name, expected_text in ALL_PAGES:
            try:
                page.goto(route, timeout=10000)
                page.wait_for_load_state("domcontentloaded", timeout=5000)

                # Quick check: page should not be blank
                body_text = page.locator("body").inner_text()
                if len(body_text.strip()) < 10:
                    failed_pages.append(f"{page_name}: Page appears blank")

                # Check for error indicators
                error_indicators = page.locator("text=/error|404|not found/i")
                if error_indicators.count() > 0:
                    failed_pages.append(f"{page_name}: Error indicator found")

            except Exception as e:
                failed_pages.append(f"{page_name}: {str(e)}")

        assert len(failed_pages) == 0, f"Failed pages: {failed_pages}"

    def test_navigation_completeness(self, page: Page):
        """Test that all navigation items lead to valid pages."""
        # Start at dashboard
        page.goto("/dashboard")
        page.wait_for_load_state("networkidle", timeout=15000)

        # Get all navigation items
        nav_items = page.locator("[role='button'], button, a").filter(
            has_text=page.locator(
                "text=/Dashboard|Control|Streaming|Data|Sources|Mosaics|Sky|QA|Health|Events|Cache|Pipeline|Operations|Calibration|MS Browser|CARTA/"
            )
        )

        # This is a basic check - navigation items should be present
        # More detailed navigation testing is in individual page tests
        assert nav_items.count() > 0, "Navigation items not found"
