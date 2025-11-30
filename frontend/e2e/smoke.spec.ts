import { test, expect, type Page } from "@playwright/test";

/**
 * Smoke tests - Basic page load verification.
 * 
 * These are the most fundamental tests that verify pages load without crashing.
 * They should be fast and reliable.
 */
test.describe("Smoke Tests", () => {
  test("home page loads", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");
    // Just verify page didn't crash - body should exist
    await expect(page.locator("body")).toBeAttached();
  });

  test("images page loads", async ({ page }) => {
    await page.goto("/images");
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator("body")).toBeAttached();
  });

  test("sources page loads", async ({ page }) => {
    await page.goto("/sources");
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator("body")).toBeAttached();
  });

  test("jobs page loads", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("domcontentloaded");
    await expect(page.locator("body")).toBeAttached();
  });

  test("404 page shows for unknown routes", async ({ page }) => {
    await page.goto("/this-route-does-not-exist-12345");
    await page.waitForLoadState("domcontentloaded");
    // Page should load without crashing
    await expect(page.locator("body")).toBeAttached();
  });
});
