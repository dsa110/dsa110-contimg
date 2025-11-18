import { test, expect } from "@playwright/test";
import { navigateToPage, waitForDashboardLoad, waitForAPILoad } from "./helpers/page-helpers";
import { testRoutes } from "./fixtures/test-data";

/**
 * E2E tests for Data Browser QA Snapshot Card
 *
 * Tests the new QA Snapshot card in the Published tab that displays:
 * - ESE candidate counts (Active, Resolved, Warnings, Total)
 * - Top 3 ESE candidates table
 * - Refresh and Open QA Tools buttons
 */
test.describe("Data Browser QA Snapshot @regression", () => {
  test.beforeEach(async ({ page }) => {
    // Set up console error listener
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    // Navigate to data browser
    await navigateToPage(page, testRoutes.data);
    await waitForDashboardLoad(page);

    // Switch to Published tab
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    if (await publishedTab.isVisible({ timeout: 5000 }).catch(() => false)) {
      await publishedTab.click();
      await page.waitForTimeout(1000);
    }

    // Wait for API calls to complete
    await waitForAPILoad(page, 15000);
  });

  test("QA Snapshot card is visible in Published tab", async ({ page }) => {
    // Ensure we're on Published tab
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(1000);

    // Wait for ESE candidates API call
    await page
      .waitForResponse(
        (response) => response.url().includes("/api/ese/candidates") && response.status() === 200,
        { timeout: 10000 }
      )
      .catch(() => {});

    // Check for QA Snapshot heading
    const qaSnapshotHeading = page.getByRole("heading", { name: /QA Snapshot/i });
    await expect(qaSnapshotHeading).toBeVisible({ timeout: 10000 });
  });

  test("QA Snapshot displays ESE candidate counts", async ({ page }) => {
    // Ensure Published tab is active
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(1000);

    // Wait for ESE data
    await page
      .waitForResponse(
        (response) => response.url().includes("/api/ese/candidates") && response.status() === 200,
        { timeout: 10000 }
      )
      .catch(() => {});

    // Check for count chips
    const countLabels = ["Active:", "Resolved:", "Warnings:", "Total:"];

    for (const label of countLabels) {
      const chip = page.locator(`text=${label}`).first();
      await expect(chip).toBeVisible({ timeout: 5000 });
    }
  });

  test("QA Snapshot displays top ESE candidates table", async ({ page }) => {
    // Ensure Published tab is active
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(1000);

    // Wait for ESE data
    await waitForAPILoad(page, 15000);

    // Check for table headers
    const tableHeaders = ["Source ID", "Status", "Max σ"];

    for (const header of tableHeaders) {
      const headerCell = page.locator(`text=${header}`).first();
      await expect(headerCell).toBeVisible({ timeout: 5000 });
    }
  });

  test("QA Snapshot handles empty state correctly", async ({ page }) => {
    // Ensure Published tab is active
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(1000);

    // Wait for API call (even if it returns empty)
    await page
      .waitForResponse((response) => response.url().includes("/api/ese/candidates"), {
        timeout: 10000,
      })
      .catch(() => {});

    // Either candidates are shown, or empty state message
    const hasCandidates = await page
      .locator("text=/Source ID|NVSS/i")
      .first()
      .isVisible({ timeout: 3000 })
      .catch(() => false);

    const hasEmptyMessage = await page
      .locator("text=/No QA anomalies detected|New candidates will appear/i")
      .first()
      .isVisible({ timeout: 3000 })
      .catch(() => false);

    // Card should be visible in either case
    const qaSnapshotHeading = page.getByRole("heading", { name: /QA Snapshot/i });
    await expect(qaSnapshotHeading).toBeVisible({ timeout: 10000 });

    expect(hasCandidates || hasEmptyMessage).toBe(true);
  });

  test("Refresh button triggers data refetch", async ({ page }) => {
    // Ensure Published tab is active
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(1000);

    // Find refresh button
    const refreshButton = page.getByRole("button", { name: /Refresh/i });
    await expect(refreshButton).toBeVisible({ timeout: 10000 });

    // Set up response listener
    let apiCallCount = 0;
    page.on("response", (response) => {
      if (response.url().includes("/api/ese/candidates")) {
        apiCallCount++;
      }
    });

    // Click refresh
    await refreshButton.click();
    await page.waitForTimeout(2000);

    // Verify API was called (at least once, possibly more)
    expect(apiCallCount).toBeGreaterThanOrEqual(1);
  });

  test("Open QA Tools button navigates to QA page", async ({ page }) => {
    // Ensure Published tab is active
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(1000);

    // Find Open QA Tools button
    const openQAButton = page.getByRole("button", { name: /Open QA Tools/i });
    await expect(openQAButton).toBeVisible({ timeout: 10000 });

    // Click and verify navigation
    await openQAButton.click();
    await page.waitForURL("**/qa", { timeout: 5000 });
    expect(page.url()).toContain("/qa");
  });

  test("QA Snapshot card handles loading states", async ({ page }) => {
    // Reload page to catch loading states
    await page.reload();
    await waitForDashboardLoad(page);

    // Switch to Published tab
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(500);

    // Check for skeleton loaders
    const hasSkeleton = await page
      .locator(".MuiSkeleton-root")
      .first()
      .isVisible({ timeout: 2000 })
      .catch(() => false);

    // Loading states are acceptable - just verify they resolve
    await waitForAPILoad(page, 15000);

    // After loading, card should be visible
    const qaSnapshotHeading = page.getByRole("heading", { name: /QA Snapshot/i });
    await expect(qaSnapshotHeading).toBeVisible({ timeout: 10000 });
  });

  test("QA Snapshot is positioned above data table", async ({ page }) => {
    // Ensure Published tab is active
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(1000);

    // Find QA Snapshot card
    const qaSnapshotHeading = page.getByRole("heading", { name: /QA Snapshot/i });
    await expect(qaSnapshotHeading).toBeVisible({ timeout: 10000 });

    // Find data table (should be below QA snapshot)
    const dataTable = page.locator('table, [role="table"]').first();
    const tableVisible = await dataTable.isVisible({ timeout: 5000 }).catch(() => false);

    // Verify layout: QA snapshot should be above table
    if (tableVisible) {
      const qaBounds = await qaSnapshotHeading.boundingBox();
      const tableBounds = await dataTable.boundingBox();

      if (qaBounds && tableBounds) {
        // QA snapshot should be above table (smaller Y coordinate)
        expect(qaBounds.y).toBeLessThan(tableBounds.y);
      }
    }
  });

  test("QA Snapshot is responsive", async ({ page }) => {
    // Ensure Published tab is active
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(1000);

    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);

    const qaSnapshotHeading = page.getByRole("heading", { name: /QA Snapshot/i });
    await expect(qaSnapshotHeading).toBeVisible({ timeout: 5000 });

    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(1000);

    await expect(qaSnapshotHeading).toBeVisible({ timeout: 5000 });

    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForTimeout(1000);

    await expect(qaSnapshotHeading).toBeVisible({ timeout: 5000 });
  });

  test("QA Snapshot only appears in Published tab", async ({ page }) => {
    // Check Incoming tab - should NOT have QA snapshot
    const incomingTab = page.getByRole("tab", { name: /Incoming/i });
    await incomingTab.click();
    await page.waitForTimeout(1000);

    const qaSnapshotInIncoming = page
      .getByRole("heading", { name: /QA Snapshot/i })
      .isVisible({ timeout: 2000 })
      .catch(() => false);
    expect(await qaSnapshotInIncoming).toBe(false);

    // Check Staging tab - should NOT have QA snapshot
    const stagingTab = page.getByRole("tab", { name: /Staging/i });
    await stagingTab.click();
    await page.waitForTimeout(1000);

    const qaSnapshotInStaging = page
      .getByRole("heading", { name: /QA Snapshot/i })
      .isVisible({ timeout: 2000 })
      .catch(() => false);
    expect(await qaSnapshotInStaging).toBe(false);

    // Check Published tab - SHOULD have QA snapshot
    const publishedTab = page.getByRole("tab", { name: /Published/i });
    await publishedTab.click();
    await page.waitForTimeout(1000);

    const qaSnapshotHeading = page.getByRole("heading", { name: /QA Snapshot/i });
    await expect(qaSnapshotHeading).toBeVisible({ timeout: 10000 });
  });
});
