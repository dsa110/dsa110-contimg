"""Page Object Model for frontend E2E tests."""

from tests.e2e.frontend.pages.base_page import BasePage
from tests.e2e.frontend.pages.control_page import ControlPage
from tests.e2e.frontend.pages.dashboard_page import DashboardPage

__all__ = ["BasePage", "DashboardPage", "ControlPage"]
