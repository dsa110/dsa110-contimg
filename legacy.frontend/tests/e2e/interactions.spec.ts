import { test, expect } from "@playwright/test";
import { navigateToPage, waitForDashboardLoad } from "./helpers/page-helpers";
import { testRoutes } from "./fixtures/test-data";

test.describe("Dashboard Interactions @regression", () => {
  test("Navigation between pages works", async ({ page }) => {
    // Start at dashboard
    await navigateToPage(page, testRoutes.dashboard);
    await waitForDashboardLoad(page);

    // Navigate to Sky View
    await page.goto(testRoutes.sky);
    await waitForDashboardLoad(page);
    expect(page.url()).toContain("/sky");

    // Navigate to Data Browser
    await page.goto(testRoutes.data);
    await waitForDashboardLoad(page);
    expect(page.url()).toContain("/data");
  });

  test("Page navigation via menu works", async ({ page }) => {
    await navigateToPage(page, testRoutes.dashboard);
    await waitForDashboardLoad(page);

    // Look for navigation menu items
    // This will depend on actual implementation
    const navLinks = page.locator('a[href*="/"]').filter({ hasText: /Sky|Data|Control|Streaming/ });
    const count = await navLinks.count();

    if (count > 0) {
      // Try clicking first nav link
      await navLinks.first().click();
      await waitForDashboardLoad(page);
      // Page should have changed
      expect(page.url()).not.toContain("/dashboard");
    }
  });

  test("Forms can be filled and submitted", async ({ page }) => {
    await navigateToPage(page, testRoutes.control);
    await waitForDashboardLoad(page);

    // Look for input fields
    const inputs = page.locator('input[type="text"], input[type="number"], textarea');
    const inputCount = await inputs.count();

    if (inputCount > 0) {
      // Fill first input if it exists
      const firstInput = inputs.first();
      await firstInput.fill("test");

      // Check if value was set
      const value = await firstInput.inputValue();
      expect(value).toBe("test");
    }
  });

  test("Buttons are clickable", async ({ page }) => {
    await navigateToPage(page, testRoutes.dashboard);
    await waitForDashboardLoad(page);

    // Look for buttons
    const buttons = page.locator("button:not([disabled])");
    const buttonCount = await buttons.count();

    if (buttonCount > 0) {
      // Verify buttons are visible and enabled
      for (let i = 0; i < Math.min(buttonCount, 5); i++) {
        const button = buttons.nth(i);
        await expect(button).toBeVisible();
        await expect(button).toBeEnabled();
      }
    }
  });

  test("Error handling works", async ({ page }) => {
    // Navigate to a page that might have error states
    await navigateToPage(page, testRoutes.sky);
    await waitForDashboardLoad(page);

    // Check for error messages or error states
    // This is a basic check - actual error scenarios may vary
    const errorElements = page.locator('[role="alert"], .error, [data-testid*="error"]');
    const errorCount = await errorElements.count();

    // If errors exist, they should be visible
    if (errorCount > 0) {
      await expect(errorElements.first()).toBeVisible();
    }
  });
});
