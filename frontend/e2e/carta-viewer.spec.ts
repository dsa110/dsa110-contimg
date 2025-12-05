import { test, expect } from "@playwright/test";

/**
 * E2E Tests for CARTA Viewer Integration
 *
 * Tests the CARTA viewer page and related functionality:
 * - CARTAViewerPage navigation and rendering
 * - Status checking and availability states
 * - Query parameter handling (?ms= and ?file=)
 * - Integration with MSDetailPage "Open in CARTA" button
 */

// Mock CARTA status responses
const mockCARTAAvailable = {
  available: true,
  version: "4.0.0",
  url: "http://carta.local:3000",
  sessions_active: 2,
  max_sessions: 10,
};

const mockCARTAUnavailable = {
  available: false,
  message: "CARTA server is not currently running",
};

test.describe("CARTA Viewer Page", () => {
  test.describe("when CARTA is available", () => {
    test.beforeEach(async ({ page }) => {
      // Mock CARTA status endpoint to return available
      await page.route("**/api/**/carta/status", (route) =>
        route.fulfill({ status: 200, json: mockCARTAAvailable })
      );
    });

    test("displays viewer when file is specified via ?ms=", async ({
      page,
    }) => {
      await page.goto(
        "/viewer/carta?ms=/stage/dsa110-contimg/ms/2025-01-15.ms"
      );
      await page.waitForLoadState("networkidle");

      // Should display the CARTA viewer header
      await expect(page.locator("h1")).toContainText("CARTA Viewer");

      // Should display the file path
      await expect(page.locator("body")).toContainText(
        "/stage/dsa110-contimg/ms/2025-01-15.ms"
      );

      // Should have iframe for CARTA
      const iframe = page.locator('iframe[title="CARTA Viewer"]');
      await expect(iframe).toBeVisible();
    });

    test("displays viewer when file is specified via ?file=", async ({
      page,
    }) => {
      await page.goto(
        "/viewer/carta?file=/stage/dsa110-contimg/images/test.fits"
      );
      await page.waitForLoadState("networkidle");

      // Should display the file path
      await expect(page.locator("body")).toContainText("test.fits");

      // Should have iframe
      const iframe = page.locator('iframe[title="CARTA Viewer"]');
      await expect(iframe).toBeVisible();
    });

    test("displays version when available", async ({ page }) => {
      await page.goto("/viewer/carta?ms=/data/test.ms");
      await page.waitForLoadState("networkidle");

      // Should show version from mock
      await expect(page.locator("body")).toContainText("v4.0.0");
    });

    test("has open in new tab link", async ({ page }) => {
      await page.goto("/viewer/carta?ms=/data/test.ms");
      await page.waitForLoadState("networkidle");

      const newTabLink = page.getByRole("link", { name: /open in new tab/i });
      await expect(newTabLink).toBeVisible();
      await expect(newTabLink).toHaveAttribute("target", "_blank");
    });

    test("shows no file state when no parameters provided", async ({
      page,
    }) => {
      await page.goto("/viewer/carta");
      await page.waitForLoadState("networkidle");

      // Should show "No File Specified" message
      await expect(page.locator("h2")).toContainText("No File Specified");

      // Should have link to browse images
      const browseLink = page.getByRole("link", { name: /browse images/i });
      await expect(browseLink).toBeVisible();
      await expect(browseLink).toHaveAttribute("href", "/images");
    });
  });

  test.describe("when CARTA is unavailable", () => {
    test.beforeEach(async ({ page }) => {
      // Mock CARTA status endpoint to return unavailable
      await page.route("**/api/**/carta/status", (route) =>
        route.fulfill({ status: 200, json: mockCARTAUnavailable })
      );
    });

    test("displays unavailable message", async ({ page }) => {
      await page.goto("/viewer/carta?ms=/data/test.ms");
      await page.waitForLoadState("networkidle");

      // Should show unavailable heading
      await expect(page.locator("h2")).toContainText(
        "CARTA Viewer Unavailable"
      );

      // Should show the custom message from API
      await expect(page.locator("body")).toContainText(
        "CARTA server is not currently running"
      );
    });

    test("has return to dashboard link", async ({ page }) => {
      await page.goto("/viewer/carta?ms=/data/test.ms");
      await page.waitForLoadState("networkidle");

      const dashboardLink = page.getByRole("link", {
        name: /return to dashboard/i,
      });
      await expect(dashboardLink).toBeVisible();
      await expect(dashboardLink).toHaveAttribute("href", "/");
    });

    test("navigates back to dashboard when link clicked", async ({ page }) => {
      await page.goto("/viewer/carta?ms=/data/test.ms");
      await page.waitForLoadState("networkidle");

      await page.getByRole("link", { name: /return to dashboard/i }).click();

      // Should navigate to home
      await expect(page).toHaveURL("/");
    });
  });

  test.describe("when CARTA status check fails", () => {
    test("handles network error gracefully", async ({ page }) => {
      // Mock status endpoint to fail
      await page.route("**/api/**/carta/status", (route) =>
        route.fulfill({ status: 500, json: { error: "Server error" } })
      );

      await page.goto("/viewer/carta?ms=/data/test.ms");
      await page.waitForLoadState("networkidle");

      // Should fall back to unavailable state
      await expect(page.locator("h2")).toContainText(
        "CARTA Viewer Unavailable"
      );
    });

    test("handles 404 gracefully", async ({ page }) => {
      // Mock status endpoint to return 404 (CARTA not deployed)
      await page.route("**/api/**/carta/status", (route) =>
        route.fulfill({ status: 404, json: { error: "Not found" } })
      );

      await page.goto("/viewer/carta?ms=/data/test.ms");
      await page.waitForLoadState("networkidle");

      // Should fall back to unavailable state
      await expect(page.locator("h2")).toContainText(
        "CARTA Viewer Unavailable"
      );
    });
  });
});

test.describe("MSDetailPage CARTA Integration", () => {
  test.beforeEach(async ({ page }) => {
    // Mock MS API
    await page.route("**/api/**/ms/**", (route) =>
      route.fulfill({
        status: 200,
        json: {
          path: "/stage/dsa110-contimg/ms/2025-01-15T14-30-00.ms",
          pointing_ra_deg: 180.5,
          pointing_dec_deg: 45.25,
          created_at: "2025-01-15T14:30:00Z",
          qa_grade: "good",
          qa_summary: "All calibrations passed",
          calibrator_matches: [],
        },
      })
    );
  });

  test("has Open in CARTA button", async ({ page }) => {
    await page.goto("/ms/2025-01-15T14-30-00.ms");
    await page.waitForLoadState("networkidle");

    const cartaButton = page.getByRole("button", { name: /open in carta/i });
    await expect(cartaButton).toBeVisible();
  });

  test("CARTA button navigates to viewer with correct MS path", async ({
    page,
  }) => {
    // Mock CARTA as available for the viewer page
    await page.route("**/api/**/carta/status", (route) =>
      route.fulfill({ status: 200, json: mockCARTAAvailable })
    );

    await page.goto("/ms/2025-01-15T14-30-00.ms");
    await page.waitForLoadState("networkidle");

    // Click should open in new tab, but for testing we intercept
    const cartaButton = page.getByRole("button", { name: /open in carta/i });

    // Get the click action and check what URL it would open
    // Since it uses window.open, we need to handle the popup
    const [popup] = await Promise.all([
      page.waitForEvent("popup"),
      cartaButton.click(),
    ]);

    // Verify the popup URL contains the correct path
    const popupUrl = popup.url();
    expect(popupUrl).toContain("/viewer/carta");
    expect(popupUrl).toContain("ms=");
  });
});

test.describe("CARTA Viewer Accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/**/carta/status", (route) =>
      route.fulfill({ status: 200, json: mockCARTAAvailable })
    );
  });

  test("iframe has accessible title", async ({ page }) => {
    await page.goto("/viewer/carta?ms=/data/test.ms");
    await page.waitForLoadState("networkidle");

    const iframe = page.locator("iframe");
    await expect(iframe).toHaveAttribute("title", "CARTA Viewer");
  });

  test("page has proper heading structure", async ({ page }) => {
    await page.goto("/viewer/carta?ms=/data/test.ms");
    await page.waitForLoadState("networkidle");

    // Should have h1 heading
    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toBeVisible();
  });

  test("links have proper attributes for external opening", async ({
    page,
  }) => {
    await page.goto("/viewer/carta?ms=/data/test.ms");
    await page.waitForLoadState("networkidle");

    const newTabLink = page.getByRole("link", { name: /open in new tab/i });
    await expect(newTabLink).toHaveAttribute("rel", "noopener noreferrer");
  });
});
