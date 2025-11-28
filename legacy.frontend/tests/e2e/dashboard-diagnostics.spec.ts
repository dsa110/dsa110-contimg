import { test, expect } from "@playwright/test";
import { navigateToPage, waitForDashboardLoad, waitForAPILoad } from "./helpers/page-helpers";
import { testRoutes, testAPIPaths } from "./fixtures/test-data";

/**
 * E2E tests for Dashboard Diagnostics & Alerts section
 *
 * Tests the new consolidated diagnostics section that includes:
 * - Queue Overview Card
 * - Pointing Summary Card
 * - Dead Letter Queue Stats
 * - Circuit Breaker Status
 * - Health Checks
 * - ESE Candidates Panel
 */
test.describe("Dashboard Diagnostics Section @regression", () => {
  test.beforeEach(async ({ page }) => {
    // Set up console error listener
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    // Navigate to dashboard
    await navigateToPage(page, testRoutes.dashboard);
    await waitForDashboardLoad(page);

    // Wait for API calls to complete
    await waitForAPILoad(page, 15000);
  });

  test("Diagnostics & Alerts section is visible", async ({ page }) => {
    // Look for the collapsible section title
    const diagnosticsSection = page.getByRole("heading", { name: /Diagnostics.*Alerts/i });
    await expect(diagnosticsSection).toBeVisible({ timeout: 10000 });
  });

  test("Queue Overview Card displays queue statistics", async ({ page }) => {
    // Wait for queue data to load
    await page
      .waitForResponse(
        (response) => response.url().includes("/api/status") && response.status() === 200,
        { timeout: 10000 }
      )
      .catch(() => {});

    // Check for queue metric cards
    const queueMetrics = ["Total", "Pending", "In Progress", "Completed", "Failed", "Collecting"];

    for (const metric of queueMetrics) {
      const metricCard = page.locator(`text=${metric}`).first();
      await expect(metricCard).toBeVisible({ timeout: 5000 });
    }
  });

  test("Pointing Summary Card displays current pointing", async ({ page }) => {
    // Wait for pointing data API call
    await page
      .waitForResponse(
        (response) => response.url().includes("/api/pointing") && response.status() === 200,
        { timeout: 10000 }
      )
      .catch(() => {});

    // Check for pointing summary card
    const pointingCard = page.getByRole("heading", { name: /Current Pointing/i });
    await expect(pointingCard).toBeVisible({ timeout: 10000 });

    // Check for RA/Dec chips or coordinates
    const hasCoordinates = await page
      .locator("text=/RA:|Dec:/i")
      .first()
      .isVisible()
      .catch(() => false);

    // Either coordinates are visible, or there's a "no data" message
    const hasNoDataMessage = await page
      .locator("text=/No recent pointing|Unable to load/i")
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasCoordinates || hasNoDataMessage).toBe(true);
  });

  test("Dead Letter Queue Stats component renders", async ({ page }) => {
    // Wait for DLQ API call
    await page
      .waitForResponse(
        (response) => response.url().includes("/api/dlq") && response.status() === 200,
        { timeout: 10000 }
      )
      .catch(() => {});

    // Check for DLQ stats heading
    const dlqHeading = page.getByRole("heading", { name: /Dead Letter Queue/i });
    await expect(dlqHeading).toBeVisible({ timeout: 10000 });
  });

  test("Health Checks card displays health status", async ({ page }) => {
    // Wait for health summary API call
    await page
      .waitForResponse(
        (response) => response.url().includes("/api/health") && response.status() === 200,
        { timeout: 10000 }
      )
      .catch(() => {});

    // Check for health checks heading
    const healthChecksHeading = page.getByRole("heading", { name: /Health Checks/i });
    await expect(healthChecksHeading).toBeVisible({ timeout: 10000 });

    // Check for health status chips (Healthy/Investigate)
    const healthStatus = page.locator("text=/Healthy|Investigate/i").first();
    await expect(healthStatus).toBeVisible({ timeout: 5000 });
  });

  test("Circuit Breaker Status component renders", async ({ page }) => {
    // Wait for circuit breaker API call
    await page
      .waitForResponse(
        (response) => response.url().includes("/api/circuit-breakers") && response.status() === 200,
        { timeout: 10000 }
      )
      .catch(() => {});

    // Check for circuit breaker heading
    const cbHeading = page.getByRole("heading", { name: /Circuit Breaker/i });
    await expect(cbHeading).toBeVisible({ timeout: 10000 });
  });

  test("ESE Candidates Panel is visible", async ({ page }) => {
    // Wait for ESE candidates API call
    await page
      .waitForResponse(
        (response) => response.url().includes("/api/ese/candidates") && response.status() === 200,
        { timeout: 10000 }
      )
      .catch(() => {});

    // ESE panel should be visible (it's a component, so check for its content)
    const eseContent = page.locator("text=/ESE|Extreme Scattering/i").first();
    await expect(eseContent).toBeVisible({ timeout: 10000 });
  });

  test("View detailed diagnostics button navigates to health page", async ({ page }) => {
    // Find the button
    const viewDetailsButton = page.getByRole("button", { name: /View detailed diagnostics/i });
    await expect(viewDetailsButton).toBeVisible({ timeout: 5000 });

    // Click and verify navigation
    await viewDetailsButton.click();
    await page.waitForURL("**/health", { timeout: 5000 });
    expect(page.url()).toContain("/health");
  });

  test("Open Health Page button works", async ({ page }) => {
    // Find the button in health checks card
    const openHealthButton = page.getByRole("button", { name: /Open Health Page/i });
    await expect(openHealthButton).toBeVisible({ timeout: 5000 });

    // Click and verify navigation
    await openHealthButton.click();
    await page.waitForURL("**/health", { timeout: 5000 });
    expect(page.url()).toContain("/health");
  });

  test("Open Observing View button works", async ({ page }) => {
    // Find the button in pointing summary card
    const openObservingButton = page.getByRole("button", { name: /Open Observing View/i });
    await expect(openObservingButton).toBeVisible({ timeout: 10000 });

    // Click and verify navigation
    await openObservingButton.click();
    await page.waitForURL("**/observing", { timeout: 5000 });
    expect(page.url()).toContain("/observing");
  });

  test("Diagnostics section handles loading states", async ({ page }) => {
    // Check for skeleton loaders or loading indicators
    // These should appear briefly while data loads
    const hasLoadingState = await page
      .locator('[data-testid="loading"], .MuiSkeleton-root')
      .first()
      .isVisible({ timeout: 2000 })
      .catch(() => false);

    // Loading states are acceptable - just verify they eventually resolve
    await waitForAPILoad(page, 15000);
  });

  test("Diagnostics section is responsive", async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(1000);

    const diagnosticsSection = page.getByRole("heading", { name: /Diagnostics.*Alerts/i });
    await expect(diagnosticsSection).toBeVisible({ timeout: 5000 });

    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(1000);

    await expect(diagnosticsSection).toBeVisible({ timeout: 5000 });

    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForTimeout(1000);

    await expect(diagnosticsSection).toBeVisible({ timeout: 5000 });
  });
});
