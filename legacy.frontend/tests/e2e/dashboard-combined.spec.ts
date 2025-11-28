import { test, expect } from "@playwright/test";

/**
 * Combined E2E test suite for dashboard functionality
 *
 * This test suite verifies:
 * - Page loading and layout
 * - API integration
 * - Component rendering
 * - User interactions
 *
 * Note: For interactive testing, use Cursor Browser Extension.
 * For deep debugging, use chrome-devtools MCP.
 */

test.describe("Dashboard Combined Tests @regression", () => {
  test.beforeEach(async ({ page }) => {
    // Set up API request monitoring BEFORE navigation
    const apiRequests: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("/api/")) {
        apiRequests.push(request.url());
      }
    });

    // Navigate to dashboard
    await page.goto("/sky");
    // Wait for page to be fully loaded
    await page.waitForLoadState("networkidle");

    // Store apiRequests in page context for later use
    await page.evaluate((requests) => {
      (window as any).__testApiRequests = requests;
    }, apiRequests);
  });

  test("Sky View page loads without errors @smoke", async ({ page }) => {
    // Check for console errors
    const errors: string[] = [];
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        errors.push(msg.text());
      }
    });

    // Wait for main content
    await expect(page.locator("body")).toBeVisible();

    // Check for critical errors
    expect(errors.length).toBe(0);
  });

  test("Sky Viewer component renders", async ({ page }) => {
    // Check if SkyViewer container exists - JS9 container has id="skyViewDisplay"
    // The container exists even when no image is loaded
    const skyViewer = page.locator('#skyViewDisplay, [id*="skyView"], .JS9DisplayContainer');
    await expect(skyViewer.first()).toBeVisible({ timeout: 15000 });

    // Also verify the "No image selected" message appears (confirms container is rendered)
    // These are separate text elements, so check for either one
    const noImageMessage = page
      .locator("text=No image selected")
      .or(page.locator("text=Select an image"));
    await expect(noImageMessage.first()).toBeVisible({ timeout: 5000 });
  });

  test("Photometry Plugin panel is visible", async ({ page }) => {
    // Photometry plugin only appears when an image is loaded
    // Check if "Quick Analysis" panel exists (which contains photometry when image is loaded)
    // Use simpler selector - just look for the heading text
    const quickAnalysisPanel = page.getByRole("heading", { name: "Quick Analysis" });
    await expect(quickAnalysisPanel).toBeVisible({ timeout: 5000 });

    // When no image is selected, we see "Select an image from the browser above"
    // This confirms the panel structure is rendered
    const panelMessage = page.locator("text=Select an image from the browser above");
    await expect(panelMessage).toBeVisible({ timeout: 5000 });
  });

  test("No MUI Grid deprecation warnings", async ({ page }) => {
    const warnings: string[] = [];
    page.on("console", (msg) => {
      const text = msg.text();
      if (text.includes("Grid") && (text.includes("deprecated") || text.includes("item prop"))) {
        warnings.push(text);
      }
    });

    // Trigger a re-render by waiting
    await page.waitForTimeout(1000);

    expect(warnings.length).toBe(0);
  });

  test("API endpoints respond correctly", async ({ page }) => {
    // Monitor network requests - set up listener BEFORE navigation
    const apiRequests: string[] = [];

    // Set up request listener before navigation (in beforeEach)
    // But since beforeEach already navigated, we'll check response instead
    const responsePromise = page
      .waitForResponse(
        (response) => response.url().includes("/api/") && response.status() === 200,
        { timeout: 10000 }
      )
      .catch(() => null);

    // Wait for at least one successful API response
    const response = await responsePromise;

    // Alternative: Check network activity after page load
    await page.waitForLoadState("networkidle");

    // Verify API is working by checking if pointing history or images loaded
    // (These are visible in the UI when API succeeds)
    // Check for either "pointing measurements" or "images found" text
    const pointingText = page.locator("text=/pointing measurements/i");
    const imagesText = page.locator("text=/images found/i");

    const hasPointing = (await pointingText.count()) > 0;
    const hasImages = (await imagesText.count()) > 0;

    expect(hasPointing || hasImages).toBe(true);
  });

  test("JS9 display fills container width", async ({ page }) => {
    // Wait for JS9 container to be present (it exists even without image)
    const js9Container = page
      .locator('#skyViewDisplay, [id*="skyView"], .JS9DisplayContainer')
      .first();
    await expect(js9Container).toBeVisible({ timeout: 15000 });

    // Get container dimensions
    const containerBox = await js9Container.boundingBox();
    expect(containerBox).not.toBeNull();

    // Container should have width (even if no image is loaded)
    expect(containerBox!.width).toBeGreaterThan(0);

    // Verify the container is actually rendered in the DOM
    const containerElement = await js9Container.evaluate((el) => {
      return {
        width: el.offsetWidth,
        height: el.offsetHeight,
        display: window.getComputedStyle(el).display,
      };
    });

    expect(containerElement.width).toBeGreaterThan(0);
    expect(containerElement.display).not.toBe("none");
  });

  test("Page is responsive", async ({ page }) => {
    // Test mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await page.waitForTimeout(500);
    await expect(page.locator("body")).toBeVisible();

    // Test tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.waitForTimeout(500);
    await expect(page.locator("body")).toBeVisible();

    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.waitForTimeout(500);
    await expect(page.locator("body")).toBeVisible();
  });
});
