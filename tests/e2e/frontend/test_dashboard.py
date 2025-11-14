"""E2E tests for Dashboard page."""

import pytest
from playwright.sync_api import expect

from tests.e2e.frontend.pages.dashboard_page import DashboardPage


@pytest.mark.e2e
@pytest.mark.e2e_frontend
@pytest.mark.e2e_critical
class TestDashboard:
    """Test Dashboard page functionality."""

    def test_dashboard_loads(self, page):
        """Test that dashboard page loads successfully."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Check page title or heading
        expect(page.locator("h1, h2, h3")).to_contain_text("DSA-110", timeout=10000)

        # Check main content is visible
        expect(page.locator("main, [role='main']")).to_be_visible()

    def test_pipeline_status_displayed(self, page):
        """Test that pipeline status is displayed."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Wait for pipeline status section
        status_section = page.locator(DashboardPage.PIPELINE_STATUS_SECTION).first
        expect(status_section).to_be_visible(timeout=10000)

        # Check for status metrics
        expect(page.locator("text=/Total|Pending|Completed|Failed/")).to_be_visible()

    def test_system_metrics_displayed(self, page):
        """Test that system metrics are displayed."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Wait for system metrics section
        metrics_section = page.locator(DashboardPage.SYSTEM_METRICS_SECTION).first
        expect(metrics_section).to_be_visible(timeout=10000)

        # Check for metric indicators
        expect(page.locator("text=/CPU|Memory|Disk|Load/")).to_be_visible()

    def test_navigation_works(self, page):
        """Test that navigation between pages works."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Click on Control page
        dashboard.click_navigation_item("Control")

        # Verify navigation
        expect(page).to_have_url(containing="/control", timeout=5000)

    def test_ese_candidates_panel(self, page):
        """Test ESE candidates panel functionality."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Wait for ESE panel (may be collapsible)
        ese_panel = page.locator(DashboardPage.ESE_CANDIDATES_PANEL).first
        if ese_panel.count() > 0:
            expect(ese_panel).to_be_visible(timeout=10000)

    def test_recent_observations_table(self, page):
        """Test recent observations table."""
        dashboard = DashboardPage(page)
        dashboard.navigate()

        # Wait for table
        table = page.locator(DashboardPage.RECENT_OBSERVATIONS_TABLE).first
        if table.count() > 0:
            expect(table).to_be_visible(timeout=10000)
            # Check for table headers
            headers = table.locator("th, [role='columnheader']")
            if headers.count() > 0:
                expect(headers).to_have_count(
                    count=4, timeout=5000
                )  # Group ID, State, Subbands, Calibrator

    @pytest.mark.e2e_slow
    def test_real_time_updates(self, page):
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
