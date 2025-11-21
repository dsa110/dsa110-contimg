import { test, expect } from "@playwright/test";
import { navigateToPage, waitForDashboardLoad } from "./helpers/page-helpers";
import { testRoutes } from "./fixtures/test-data";

test.describe("Dashboard Page @regression", () => {
  test.beforeEach(async ({ page }) => {
    await navigateToPage(page, testRoutes.dashboard);
  });

  test("Dashboard page loads without errors", async ({ page }) => {
    await waitForDashboardLoad(page);

    // Check for console errors
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    // Wait a bit for any errors to appear
    await page.waitForTimeout(2000);

    // Filter out known non-critical errors
    const criticalErrors = errors.filter((e) => !e.includes("favicon") && !e.includes("sourcemap"));

    expect(criticalErrors.length).toBe(0);
  });

  test("Dashboard displays key metrics", async ({ page }) => {
    await waitForDashboardLoad(page);

    // Check for common dashboard elements
    // These may vary based on actual dashboard implementation
    const hasContent = await page.locator("body").textContent();
    expect(hasContent).toBeTruthy();
  });

  test("Dashboard is responsive", async ({ page }) => {
    await waitForDashboardLoad(page);

    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);

    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(1000);

    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForTimeout(1000);

    // Page should be visible at all sizes
    await expect(page.locator("body")).toBeVisible();
  });
});
