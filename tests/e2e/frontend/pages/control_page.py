"""Control page object."""

from playwright.sync_api import Locator, Page

from tests.e2e.frontend.pages.base_page import BasePage


class ControlPage(BasePage):
    """Page object for the Control page."""

    # Selectors
    PAGE_TITLE = "h1, h2"
    MS_TABLE = "table, [role='table'], .MuiTable-root"
    WORKFLOW_TABS = "[role='tab']"
    TEMPLATES_TAB = "text=Templates"
    CONVERT_TAB = "text=Convert"
    CALIBRATE_TAB = "text=Calibrate"
    IMAGE_TAB = "text=Image"

    def __init__(self, page: Page):
        super().__init__(page)
        self.page = page

    def navigate(self) -> None:
        """Navigate to control page."""
        self.goto("/control")
        self.wait_for_page_load()

    def wait_for_page_load(self) -> None:
        """Wait for control page to fully load."""
        # Wait for main content
        self.page.wait_for_selector("main, [role='main']", timeout=10000)
        # Wait for MS table to load
        self.page.wait_for_selector(self.MS_TABLE, timeout=15000)
        self.page.wait_for_load_state("networkidle", timeout=15000)

    def get_ms_table(self) -> Locator:
        """Get the MS table locator."""
        return self.page.locator(self.MS_TABLE).first

    def select_ms(self, index: int = 0) -> None:
        """Select an MS by row index."""
        table = self.get_ms_table()
        rows = table.locator("tbody tr")
        if rows.count() > index:
            rows.nth(index).click()
            self.page.wait_for_timeout(500)  # Wait for selection to register

    def click_workflow_tab(self, tab_name: str) -> None:
        """Click a workflow tab (Templates, Convert, Calibrate, Image)."""
        tab = self.page.locator(f"text={tab_name}").first
        if tab.count() > 0:
            tab.click()
            self.page.wait_for_timeout(500)  # Wait for tab content to load
