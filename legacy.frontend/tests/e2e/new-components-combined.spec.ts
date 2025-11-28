import { test, expect } from "@playwright/test";
import { navigateToPage, waitForDashboardLoad } from "./helpers/page-helpers";
import { testRoutes } from "./fixtures/test-data";

/**
 * Combined E2E test suite for all new components
 *
 * This suite runs smoke tests for:
 * - Dashboard Diagnostics section
 * - Control Page Live Operations card
 * - Data Browser QA Snapshot card
 *
 * Use this for quick verification that all new features work together.
 */
test.describe("New Components Combined Smoke Tests @smoke", () => {
  test("All new components load without errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    // Test Dashboard diagnostics
    await navigateToPage(page, testRoutes.dashboard);
    await waitForDashboardLoad(page);
    await page.waitForTimeout(2000);

    const diagnosticsSection = page.getByRole("heading", { name: /Diagnostics.*Alerts/i });
    await expect(diagnosticsSection).toBeVisible({ timeout: 10000 });

    // Test Control page live operations
    await navigateToPage(page, testRoutes.control);
    await waitForDashboardLoad(page);
    await page.waitForTimeout(2000);

    const liveOpsHeading = page.getByRole("heading", { name: /Live Operations/i });
    await expect(liveOpsHeading).toBeVisible({ timeout: 10000 });

    // Test Data Browser QA snapshot
    await navigateToPage(page, testRoutes.data);
    await waitForDashboardLoad(page);
    await page.waitForTimeout(1000);

    // Switch to Published tab
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    if (await publishedTab.isVisible({ timeout: 5000 }).catch(() => false)) {
      await publishedTab.click();
      await page.waitForTimeout(1000);
    }

    const qaSnapshotHeading = page.getByRole("heading", { name: /QA Snapshot/i });
    await expect(qaSnapshotHeading).toBeVisible({ timeout: 10000 });

    // Filter out known non-critical errors
    const criticalErrors = errors.filter(
      (e) =>
        !e.includes("favicon") &&
        !e.includes("sourcemap") &&
        !e.includes("Failed to load resource") &&
        !e.includes("404") &&
        !e.includes("net::ERR_") &&
        !e.includes("ChunkLoadError") &&
        !e.includes("js9") &&
        !e.includes("JS9")
    );

    if (criticalErrors.length > 0) {
      console.log("Critical errors found:", criticalErrors);
    }

    // For smoke test, just verify no critical errors
    expect(criticalErrors.length).toBe(0);
  });

  test("Navigation buttons work correctly", async ({ page }) => {
    // Test Dashboard -> Health navigation
    await navigateToPage(page, testRoutes.dashboard);
    await waitForDashboardLoad(page);

    const viewDetailsButton = page
      .getByRole("button", { name: /View detailed diagnostics/i })
      .first();
    if (await viewDetailsButton.isVisible({ timeout: 5000 }).catch(() => false)) {
      await viewDetailsButton.click();
      await page.waitForURL("**/health", { timeout: 5000 });
      expect(page.url()).toContain("/health");
    }

    // Test Control -> Pipeline navigation
    await navigateToPage(page, testRoutes.control);
    await waitForDashboardLoad(page);

    const openPipelineButton = page.getByRole("button", { name: /Open Pipeline Monitor/i }).first();
    if (await openPipelineButton.isVisible({ timeout: 10000 }).catch(() => false)) {
      await openPipelineButton.click();
      await page.waitForURL("**/pipeline", { timeout: 5000 });
      expect(page.url()).toContain("/pipeline");
    }

    // Test Data Browser -> QA navigation
    await navigateToPage(page, testRoutes.data);
    await waitForDashboardLoad(page);

    const publishedTab = page.getByRole("tab", { name: /Published/i });
    if (await publishedTab.isVisible({ timeout: 5000 }).catch(() => false)) {
      await publishedTab.click();
      await page.waitForTimeout(1000);
    }

    const openQAButton = page.getByRole("button", { name: /Open QA Tools/i }).first();
    if (await openQAButton.isVisible({ timeout: 10000 }).catch(() => false)) {
      await openQAButton.click();
      await page.waitForURL("**/qa", { timeout: 5000 });
      expect(page.url()).toContain("/qa");
    }
  });
});
