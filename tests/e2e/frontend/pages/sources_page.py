"""Page Object Model for Sources Monitoring Page."""

import re

from playwright.sync_api import Locator, Page

from tests.e2e.frontend.pages.base_page import BasePage


class SourcesPage(BasePage):
    """Page object for the Sources Monitoring page."""

    def __init__(self, page: Page):
        super().__init__(page)
        self.route = "/sources"

    def navigate(self) -> None:
        """Navigate to the Sources page."""
        self.goto(self.route)

    def get_source_id_input(self) -> Locator:
        """Get the Source ID input field."""
        # Try to find input near "Source ID" label
        return (
            self.page.locator('label').filter(has_text=re.compile(r'Source ID', re.I)).locator('..').locator('input[type="text"]').first
            .or_(self.page.locator('input[placeholder*="Source ID" i]'))
            .or_(self.page.locator('input[type="text"]').first)
        )

    def get_search_button(self) -> Locator:
        """Get the Search button."""
        return self.page.locator('button:has-text("Search")')

    def get_clear_button(self) -> Locator:
        """Get the Clear button (if visible)."""
        return self.page.locator('button:has-text("Clear")')

    def get_advanced_filters_toggle(self) -> Locator:
        """Get the Show/Hide Advanced Filters button."""
        # Try multiple selectors to find the toggle button
        return self.page.locator('button').filter(has_text=re.compile(r'Show|Hide.*Advanced Filters', re.I)).first

    def get_variability_threshold_slider(self) -> Locator:
        """Get the variability threshold slider."""
        return self.page.locator('input[type="range"]').first

    def get_ese_only_checkbox(self) -> Locator:
        """Get the ESE only checkbox."""
        # Find checkbox near the ESE candidates label
        return self.page.locator('label').filter(has_text=re.compile(r'ESE candidates', re.I)).locator('..').locator('input[type="checkbox"]').first

    def get_results_table(self) -> Locator:
        """Get the AG Grid results table."""
        # The grid container has class ag-theme-alpine-dark
        return self.page.locator('.ag-theme-alpine-dark')
    
    def wait_for_grid_ready(self, timeout: int = 10000) -> None:
        """Wait for the AG Grid to be ready."""
        # The grid is inside a Paper component, then a Box with class ag-theme-alpine-dark
        # Wait for the Paper component first (more reliable)
        paper = self.page.locator('div[class*="MuiPaper"]').filter(has_text=re.compile(r'sources|search', re.I)).first
        paper.wait_for(state='visible', timeout=timeout)
        
        # Then wait for the grid container
        grid_container = self.page.locator('.ag-theme-alpine-dark')
        grid_container.wait_for(state='visible', timeout=timeout)
        # Wait a bit more for the grid to fully initialize and render content
        self.page.wait_for_timeout(1000)

    def get_empty_state(self) -> Locator:
        """Get the empty state message."""
        # Empty state is inside the AG Grid overlay
        return self.page.locator('.ag-theme-alpine-dark').locator('text=/Search for sources|No sources found/i').first
    
    def get_initial_empty_state(self) -> Locator:
        """Get the initial empty state (before any search)."""
        # Empty state is inside the grid's noRowsOverlayComponent
        # Look for the text anywhere on the page first, then narrow down
        return self.page.get_by_text(re.compile(r'Search for sources', re.I)).first
    
    def get_no_results_empty_state(self) -> Locator:
        """Get the empty state shown when search returns no results."""
        # Empty state is inside the grid's noRowsOverlayComponent
        return self.page.get_by_text(re.compile(r'No sources found', re.I)).first

    def get_error_alert(self) -> Locator:
        """Get the error alert if present."""
        return self.page.locator('[role="alert"]').filter(has_text=re.compile(r'error', re.I)).first

    def get_loading_indicator(self) -> Locator:
        """Get the loading indicator."""
        return self.page.locator('text=/Loading sources/i')

    def enter_source_id(self, source_id: str) -> None:
        """Enter a source ID in the search field."""
        # Try multiple selectors to find the input
        input_field = (
            self.page.locator('label:has-text("Source ID")')
            .locator('..')
            .locator('input')
            .first
        )
        if not input_field.is_visible(timeout=2000):
            # Fallback: find by placeholder or nearby text
            input_field = self.page.locator('input[placeholder*="Source ID"], input[placeholder*="NVSS"]').first
        input_field.fill(source_id)

    def click_search(self) -> None:
        """Click the Search button."""
        self.get_search_button().click()

    def click_clear(self) -> None:
        """Click the Clear button."""
        self.get_clear_button().click()

    def toggle_advanced_filters(self) -> None:
        """Toggle the advanced filters section."""
        self.get_advanced_filters_toggle().click()

    def set_variability_threshold(self, value: float) -> None:
        """Set the variability threshold slider value."""
        slider = self.get_variability_threshold_slider()
        # Playwright's fill doesn't work well with range inputs
        # Use keyboard navigation or direct value setting
        self.page.evaluate(
            f"""
            const slider = document.querySelector('input[type="range"]');
            if (slider) {{
                slider.value = {value};
                slider.dispatchEvent(new Event('input', {{ bubbles: true }}));
                slider.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
            """
        )

    def set_ese_only(self, checked: bool) -> None:
        """Set the ESE only checkbox."""
        checkbox = self.get_ese_only_checkbox()
        if checkbox.is_checked() != checked:
            checkbox.click()

    def wait_for_search_results(self, timeout: int = 10000) -> None:
        """Wait for search results to load."""
        # Wait for either results table or empty state
        self.page.wait_for_load_state("networkidle", timeout=timeout)
        # Additional wait for AG Grid to render
        self.page.wait_for_timeout(1000)

    def is_search_button_disabled(self) -> bool:
        """Check if the Search button is disabled."""
        return self.get_search_button().is_disabled()

    def get_table_row_count(self) -> int:
        """Get the number of rows in the results table."""
        rows = self.page.locator('.ag-row, [role="row"]')
        return rows.count()

    def get_table_headers(self) -> list[str]:
        """Get the table column headers."""
        headers = self.page.locator('.ag-header-cell, [role="columnheader"]')
        return [h.inner_text() for h in headers.all()]

