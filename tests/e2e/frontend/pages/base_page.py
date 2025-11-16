"""Base page class for Page Object Model."""

from typing import Optional

from playwright.sync_api import Locator, Page


class BasePage:
    """Base class for all page objects."""

    def __init__(self, page: Page):
        self.page = page
        # Get base_url from environment or use default
        import os

        self.base_url = os.getenv("FRONTEND_BASE_URL", "http://localhost:5174")

    def goto(self, path: str = "/") -> None:
        """Navigate to a page."""
        # Construct full URL if path is relative
        if path.startswith("/"):
            url = f"{self.base_url}{path}"
        elif path.startswith("http"):
            url = path
        else:
            url = f"{self.base_url}/{path}"
        self.page.goto(url)
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
            lambda response: url_pattern in response.url, timeout=timeout
        ):
            pass

    def check_no_console_errors(self) -> list:
        """Check for console errors (returns list of errors)."""
        console_errors = []
        self.page.on(
            "console",
            lambda msg: console_errors.append(msg) if msg.type == "error" else None,
        )
        return console_errors
