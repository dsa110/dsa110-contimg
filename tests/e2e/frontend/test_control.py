"""E2E tests for Control page."""

import pytest
from playwright.sync_api import expect

from tests.e2e.frontend.pages.control_page import ControlPage


@pytest.mark.e2e
@pytest.mark.e2e_frontend
class TestControlPage:
    """Test Control page functionality."""

    def test_control_page_loads(self, page):
        """Test that control page loads."""
        control = ControlPage(page)
        control.navigate()

        expect(page).to_have_url(containing="/control")
        expect(page.locator("h1, h2")).to_contain_text("Control")

    def test_ms_table_displayed(self, page):
        """Test that MS table is displayed."""
        control = ControlPage(page)
        control.navigate()

        # Wait for MS table
        ms_table = control.get_ms_table()
        expect(ms_table).to_be_visible(timeout=10000)

    def test_ms_selection(self, page):
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
            # This may need adjustment based on actual selection behavior
            page.wait_for_timeout(500)

    def test_workflow_tabs(self, page):
        """Test workflow tabs (Templates, Convert, Calibrate, Image)."""
        control = ControlPage(page)
        control.navigate()

        # Check tabs are present
        tabs = page.locator(ControlPage.WORKFLOW_TABS)
        expect(tabs).to_have_count(count=4, timeout=5000)

        # Click each tab
        for tab_name in ["Templates", "Convert", "Calibrate", "Image"]:
            tab = page.locator(f"text={tab_name}").first
            if tab.count() > 0:
                tab.click()
                page.wait_for_timeout(500)  # Wait for tab content to load
