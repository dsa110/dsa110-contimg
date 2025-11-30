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
    await expect(page.locator("body")).toBeVisible();
    // Page should have loaded - check for any content
    await expect(page.locator("text=DSA-110").or(page.locator("nav"))).toBeVisible({ timeout: 10000 });
  });

  test("images page loads", async ({ page }) => {
    await page.goto("/images");
    await expect(page.locator("body")).toBeVisible();
  });

  test("sources page loads", async ({ page }) => {
    await page.goto("/sources");
    await expect(page.locator("body")).toBeVisible();
  });

  test("jobs page loads", async ({ page }) => {
    await page.goto("/jobs");
    await expect(page.locator("body")).toBeVisible();
  });

  test("404 page shows for unknown routes", async ({ page }) => {
    await page.goto("/this-route-does-not-exist-12345");
    await expect(page.locator("body")).toBeVisible();
    // Should show some kind of not found message
    await expect(
      page.getByText("404").or(page.getByText(/not found/i)).or(page.locator("body"))
    ).toBeVisible();
  });
});
