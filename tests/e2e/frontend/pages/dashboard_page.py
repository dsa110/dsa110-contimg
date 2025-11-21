"""Dashboard page object."""

from playwright.sync_api import Page
from tests.e2e.frontend.pages.base_page import BasePage


class DashboardPage(BasePage):
    """Page object for the Dashboard page."""

    # Selectors (adjust based on actual DOM structure)
    PAGE_TITLE = "h1, h2, h3"
    PIPELINE_STATUS_SECTION = (
        "[data-testid='pipeline-status'], .pipeline-status, text=Pipeline Status"
    )
    SYSTEM_METRICS_SECTION = "[data-testid='system-health'], .system-health, text=System Health"
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
        status = {}
        try:
            total_elem = self.page.locator("text=/Total.*[0-9]+/").first
            if total_elem.count() > 0:
                status["total"] = int(total_elem.inner_text().split()[-1])
        except Exception:
            pass

        try:
            pending_elem = self.page.locator("text=/Pending.*[0-9]+/").first
            if pending_elem.count() > 0:
                status["pending"] = int(pending_elem.inner_text().split()[-1])
        except Exception:
            pass

        return status

    def get_system_metrics(self) -> dict:
        """Get system metrics."""
        # Extract metrics from page
        # Adjust selectors based on actual implementation
        metrics = {}
        try:
            cpu_elem = self.page.locator("[data-testid='cpu-metric'], text=/CPU/").first
            if cpu_elem.count() > 0:
                cpu_text = cpu_elem.inner_text()
                # Extract percentage
                import re

                match = re.search(r"(\d+\.?\d*)%", cpu_text)
                if match:
                    metrics["cpu"] = float(match.group(1))
        except Exception:
            pass

        try:
            memory_elem = self.page.locator("[data-testid='memory-metric'], text=/Memory/").first
            if memory_elem.count() > 0:
                memory_text = memory_elem.inner_text()
                import re

                match = re.search(r"(\d+\.?\d*)%", memory_text)
                if match:
                    metrics["memory"] = float(match.group(1))
        except Exception:
            pass

        return metrics

    def click_navigation_item(self, item_name: str) -> None:
        """Click a navigation item."""
        self.page.click(f"text={item_name}")
        self.page.wait_for_load_state("networkidle")
