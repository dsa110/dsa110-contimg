"""Playwright configuration for frontend E2E tests."""

import os

# Configuration
BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5174")
API_URL = os.getenv("API_URL", "http://localhost:8000")
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
SLOW_MO = int(os.getenv("PLAYWRIGHT_SLOW_MO", "0"))  # Slow down operations (ms)
TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))  # Default timeout (ms)

# Browser settings
BROWSER = os.getenv("PLAYWRIGHT_BROWSER", "chromium")  # chromium, firefox, webkit
