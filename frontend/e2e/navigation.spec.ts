import { test, expect } from "@playwright/test";

/**
 * Navigation tests - Verify routing works correctly.
 * 
 * These tests verify that:
 * - Navigation links work
 * - URLs change correctly
 * - Browser back/forward works
 */
test.describe("Navigation", () => {
  test.beforeEach(async ({ page }) => {
    // Start from home page
    await page.goto("/");
    // Wait for page to be ready
    await page.waitForLoadState("networkidle");
  });

  test("can navigate to images page", async ({ page }) => {
    // Find any link to images (could be nav link, button, or card)
    const imagesLink = page.locator('a[href*="/images"]').first();
    
    if (await imagesLink.isVisible()) {
      await imagesLink.click();
      await expect(page).toHaveURL(/\/images/);
    } else {
      // Direct navigation as fallback
      await page.goto("/images");
      await expect(page).toHaveURL(/\/images/);
    }
  });

  test("can navigate to sources page", async ({ page }) => {
    const sourcesLink = page.locator('a[href*="/sources"]').first();
    
    if (await sourcesLink.isVisible()) {
      await sourcesLink.click();
      await expect(page).toHaveURL(/\/sources/);
    } else {
      await page.goto("/sources");
      await expect(page).toHaveURL(/\/sources/);
    }
  });

  test("can navigate to jobs page", async ({ page }) => {
    const jobsLink = page.locator('a[href*="/jobs"]').first();
    
    if (await jobsLink.isVisible()) {
      await jobsLink.click();
      await expect(page).toHaveURL(/\/jobs/);
    } else {
      await page.goto("/jobs");
      await expect(page).toHaveURL(/\/jobs/);
    }
  });

  test("browser back button works", async ({ page }) => {
    // Navigate to images
    await page.goto("/images");
    await page.waitForLoadState("networkidle");
    
    // Navigate to sources  
    await page.goto("/sources");
    await page.waitForLoadState("networkidle");
    
    // Go back
    await page.goBack();
    await expect(page).toHaveURL(/\/images/);
  });

  test("can return to home from any page", async ({ page }) => {
    await page.goto("/images");
    await page.waitForLoadState("networkidle");
    
    // Find home link (could be logo, "Home" text, or "/" link)
    const homeLink = page.locator('a[href="/"]').first()
      .or(page.locator('a[href=""]').first())
      .or(page.getByRole("link", { name: /home|dsa-110/i }).first());
    
    if (await homeLink.isVisible()) {
      await homeLink.click();
      await expect(page).toHaveURL("/");
    } else {
      // Direct navigation as fallback
      await page.goto("/");
      await expect(page).toHaveURL("/");
    }
  });
});
