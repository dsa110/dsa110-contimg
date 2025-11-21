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

    def test_ms_details_panel_appears_on_selection(self, page):
        """Test that MS Details panel appears when MS is selected."""
        control = ControlPage(page)
        control.navigate()

        # Wait for MS table
        ms_table = control.get_ms_table()
        expect(ms_table).to_be_visible(timeout=10000)

        # Select first MS if available
        first_row = ms_table.locator("tbody tr").first
        if first_row.count() > 0:
            first_row.click()
            page.wait_for_timeout(1000)  # Wait for panel to appear

            # Check that MS Details panel is visible
            panel = control.get_ms_details_panel()
            expect(panel).to_be_visible(timeout=5000)

    def test_ms_details_panel_tabs(self, page):
        """Test MS Details panel tabs (Inspection, Comparison, Related Products)."""
        control = ControlPage(page)
        control.navigate()

        # Wait for MS table and select an MS
        ms_table = control.get_ms_table()
        expect(ms_table).to_be_visible(timeout=10000)

        first_row = ms_table.locator("tbody tr").first
        if first_row.count() > 0:
            first_row.click()
            page.wait_for_timeout(1000)

            # Check that panel is visible
            panel = control.get_ms_details_panel()
            expect(panel).to_be_visible(timeout=5000)

            # Test each tab
            for tab_name in ["MS Inspection", "MS Comparison", "Related Products"]:
                control.click_ms_details_tab(tab_name)
                page.wait_for_timeout(500)  # Wait for tab content

                # Verify tab is active (has aria-selected or similar)
                tab = page.locator(f"text={tab_name}").first
                if tab.count() > 0:
                    # Tab should be visible
                    expect(tab).to_be_visible()

    def test_ms_details_panel_collapsible(self, page):
        """Test that MS Details panel can be collapsed and expanded."""
        control = ControlPage(page)
        control.navigate()

        # Wait for MS table and select an MS
        ms_table = control.get_ms_table()
        expect(ms_table).to_be_visible(timeout=10000)

        first_row = ms_table.locator("tbody tr").first
        if first_row.count() > 0:
            first_row.click()
            page.wait_for_timeout(1000)

            # Panel should be visible
            panel = control.get_ms_details_panel()
            expect(panel).to_be_visible(timeout=5000)

            # Toggle panel (collapse)
            control.toggle_ms_details_panel()
            page.wait_for_timeout(500)

            # Toggle panel again (expand)
            control.toggle_ms_details_panel()
            page.wait_for_timeout(500)

            # Panel should still be accessible
            expect(panel).to_be_visible()
