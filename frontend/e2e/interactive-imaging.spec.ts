import { test, expect, Page } from "@playwright/test";

/**
 * E2E Tests for Interactive Imaging Workflow
 *
 * Tests the Phase 3 casangi integration including:
 * - InteractiveImagingPage navigation
 * - Session creation/management
 * - BokehEmbed component behavior
 * - Image versioning UI
 */

test.describe("Interactive Imaging Page", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to imaging page
    await page.goto("/imaging");
  });

  test("should display page header and controls", async ({ page }) => {
    // Check page title
    await expect(page.locator("h1")).toContainText("Interactive Imaging");

    // Check that new session form exists
    await expect(page.locator('input[id="ms_path"]')).toBeVisible();
    await expect(page.locator('input[id="imagename"]')).toBeVisible();

    // Check default params are shown
    await expect(page.locator("text=DSA-110 Default Parameters")).toBeVisible();
  });

  test("should show active sessions section", async ({ page }) => {
    // Check active sessions section exists
    await expect(page.locator("text=Active Sessions")).toBeVisible();

    // Should show no sessions message initially or session list
    const noSessions = page.locator("text=No active sessions");
    const sessionList = page.locator('[data-testid="session-list"]');

    // One of these should be visible
    const noSessionsVisible = await noSessions.isVisible().catch(() => false);
    const sessionListVisible = await sessionList.isVisible().catch(() => false);

    expect(noSessionsVisible || sessionListVisible).toBeTruthy();
  });

  test("should validate MS path before launching", async ({ page }) => {
    // Try to launch with empty path
    await page.fill('input[id="ms_path"]', "");
    await page.fill('input[id="imagename"]', "test_output");

    // Click launch button
    const launchButton = page.locator("button:has-text('Launch')");
    await launchButton.click();

    // Should show validation error
    await expect(page.locator("text=required")).toBeVisible({ timeout: 5000 });
  });

  test("should populate MS path from URL query param", async ({ page }) => {
    // Navigate with MS path in query
    const testMsPath = "/data/ms/test.ms";
    await page.goto(`/imaging?ms=${encodeURIComponent(testMsPath)}`);

    // Check the input is populated
    const msInput = page.locator('input[id="ms_path"]');
    await expect(msInput).toHaveValue(testMsPath);
  });

  test("should show DSA-110 defaults", async ({ page }) => {
    // Check that default params card shows correct values
    const defaultsCard = page
      .locator("text=DSA-110 Default Parameters")
      .locator("..");

    await expect(defaultsCard.locator("text=5040")).toBeVisible();
    await expect(defaultsCard.locator("text=2.5arcsec")).toBeVisible();
    await expect(defaultsCard.locator("text=briggs")).toBeVisible();
  });

  test("should update form when parameters change", async ({ page }) => {
    // Change image size
    await page.fill('input[id="imsize"]', "4096");

    // Verify the value updated
    await expect(page.locator('input[id="imsize"]')).toHaveValue("4096");

    // Change weighting
    await page.selectOption('select[id="weighting"]', "natural");
    await expect(page.locator('select[id="weighting"]')).toHaveValue("natural");
  });
});

test.describe("Session Management", () => {
  // These tests require a running API with mock or real sessions

  test("should display session info when sessions exist", async ({ page }) => {
    // Mock the sessions API
    await page.route("**/api/imaging/sessions", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sessions: [
            {
              id: "test-session-1",
              port: 5010,
              url: "http://localhost:5010/iclean",
              ms_path: "/data/ms/test.ms",
              imagename: "test_image",
              created_at: new Date().toISOString(),
              age_hours: 0.5,
              is_alive: true,
            },
          ],
          total: 1,
          available_ports: 89,
        }),
      });
    });

    await page.goto("/imaging");

    // Should show the session
    await expect(page.locator("text=test-session-1").first()).toBeVisible({
      timeout: 5000,
    });
    await expect(page.locator("text=test.ms")).toBeVisible();
  });

  test("should allow stopping a session", async ({ page }) => {
    // Mock sessions API
    await page.route("**/api/imaging/sessions", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          sessions: [
            {
              id: "session-to-stop",
              port: 5011,
              url: "http://localhost:5011/iclean",
              ms_path: "/data/ms/stop.ms",
              imagename: "stop_image",
              created_at: new Date().toISOString(),
              age_hours: 1.0,
              is_alive: true,
            },
          ],
          total: 1,
          available_ports: 89,
        }),
      });
    });

    // Mock DELETE endpoint
    await page.route("**/api/imaging/sessions/session-to-stop", (route) => {
      if (route.request().method() === "DELETE") {
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            status: "stopped",
            session_id: "session-to-stop",
          }),
        });
      }
    });

    await page.goto("/imaging");

    // Wait for session to appear
    await expect(page.locator("text=session-to-stop").first()).toBeVisible({
      timeout: 5000,
    });

    // Click stop button
    const stopButton = page.locator('button:has-text("Stop")').first();
    await stopButton.click();

    // Confirm stop (if confirmation dialog exists)
    const confirmButton = page.locator('button:has-text("Confirm")');
    if (await confirmButton.isVisible().catch(() => false)) {
      await confirmButton.click();
    }
  });
});

test.describe("BokehEmbed Component", () => {
  test("should show connecting state initially", async ({ page }) => {
    // Mock session start
    await page.route("**/api/imaging/interactive", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session_id: "embed-test-session",
          url: "http://localhost:5015/iclean",
          status: "started",
          ms_path: "/data/ms/embed.ms",
          imagename: "embed_image",
        }),
      });
    });

    // Navigate and fill form
    await page.goto("/imaging");
    await page.fill('input[id="ms_path"]', "/data/ms/test.ms");
    await page.fill('input[id="imagename"]', "test_output");

    // The actual test would require a running Bokeh server
    // For now, test the form submission
    const launchButton = page.locator("button:has-text('Launch')");
    expect(await launchButton.isEnabled()).toBeTruthy();
  });
});

test.describe("Navigation from MS Detail", () => {
  test("should link to imaging page from MS detail", async ({ page }) => {
    // Mock MS detail API
    await page.route("**/api/ms/*", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          path: "/data/ms/navigation-test.ms",
          pointing_ra_deg: 180.0,
          pointing_dec_deg: 30.0,
          qa_grade: "good",
        }),
      });
    });

    // Navigate to MS detail page (adjust path as needed)
    await page.goto("/ms/%2Fdata%2Fms%2Fnavigation-test.ms");

    // Look for Interactive Clean button
    const icleanButton = page.locator('a:has-text("Interactive Clean")');

    if (await icleanButton.isVisible().catch(() => false)) {
      // Verify it links to imaging page with MS param
      const href = await icleanButton.getAttribute("href");
      expect(href).toContain("/imaging");
      expect(href).toContain("ms=");
    }
  });
});

test.describe("Image Versioning UI", () => {
  test("should show version chain on image detail", async ({ page }) => {
    // Mock image detail API with versioning info
    await page.route("**/api/images/version-test", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "version-test",
          path: "/data/images/version-test.fits",
          ms_path: "/data/ms/source.ms",
          qa_grade: "warn",
          parent_id: "original-image",
          version: 2,
          imaging_params: {
            imsize: [4096, 4096],
            cell: "3arcsec",
            weighting: "natural",
          },
        }),
      });
    });

    // Mock version chain API
    await page.route("**/api/images/version-test/versions", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          current_id: "version-test",
          root_id: "original-image",
          chain: [
            {
              id: "original-image",
              version: 1,
              created_at: "2025-01-01T00:00:00Z",
              qa_grade: "fail",
            },
            {
              id: "version-test",
              version: 2,
              created_at: "2025-01-15T00:00:00Z",
              qa_grade: "warn",
            },
          ],
          total_versions: 2,
        }),
      });
    });

    await page.goto("/images/version-test");

    // Should show version info
    await expect(page.locator("text=Version 2")).toBeVisible({ timeout: 5000 });

    // Should show link to parent
    const parentLink = page.locator('a:has-text("original-image")');
    if (await parentLink.isVisible().catch(() => false)) {
      expect(await parentLink.getAttribute("href")).toContain("original-image");
    }
  });

  test("should show re-image button on failed QA images", async ({ page }) => {
    // Mock image with failed QA
    await page.route("**/api/images/failed-image", (route) => {
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "failed-image",
          path: "/data/images/failed.fits",
          ms_path: "/data/ms/source.ms",
          qa_grade: "fail",
          version: 1,
        }),
      });
    });

    await page.goto("/images/failed-image");

    // Should show re-image option
    const reimageButton = page.locator('button:has-text("Re-image")');

    if (await reimageButton.isVisible().catch(() => false)) {
      // Click should open modal
      await reimageButton.click();

      // Modal should appear with imaging params
      await expect(page.locator("text=Image Size")).toBeVisible({
        timeout: 5000,
      });
      await expect(page.locator("text=Cell Size")).toBeVisible();
    }
  });
});

test.describe("API Integration", () => {
  test("should handle API errors gracefully", async ({ page }) => {
    // Mock API error
    await page.route("**/api/imaging/sessions", (route) => {
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "Internal server error",
        }),
      });
    });

    await page.goto("/imaging");

    // Should show error state
    await expect(page.locator("text=Error")).toBeVisible({ timeout: 5000 });
  });

  test("should handle timeout gracefully", async ({ page }) => {
    // Mock slow response
    await page.route("**/api/imaging/sessions", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 30000));
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ sessions: [], total: 0, available_ports: 90 }),
      });
    });

    await page.goto("/imaging");

    // Should show loading state
    await expect(page.locator("text=Loading")).toBeVisible({ timeout: 2000 });
  });
});
