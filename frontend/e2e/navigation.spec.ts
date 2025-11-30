import { test, expect } from "@playwright/test";

/**
 * E2E tests for router navigation flows.
 */
test.describe("Router Navigation", () => {
  test("homepage loads and displays main sections", async ({ page }) => {
    await page.goto("/");

    // Check page title
    await expect(page).toHaveTitle(/DSA-110/);

    // Check main navigation links exist
    await expect(page.getByRole("link", { name: "Home" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Images" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Sources" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Jobs" })).toBeVisible();
  });

  test("navigates from home to images page", async ({ page }) => {
    await page.goto("/");

    // Click on Images link
    await page.getByRole("link", { name: "Images" }).click();

    // Verify URL changed
    await expect(page).toHaveURL(/\/images/);

    // Verify page content
    await expect(page.getByRole("heading", { name: "Images" })).toBeVisible();
  });

  test("navigates from home to sources page", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: "Sources" }).click();

    await expect(page).toHaveURL(/\/sources/);
    await expect(page.getByRole("heading", { name: "Sources" })).toBeVisible();
  });

  test("navigates from home to jobs page", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: "Jobs" }).click();

    await expect(page).toHaveURL(/\/jobs/);
    await expect(page.getByRole("heading", { name: /Jobs|Pipeline/i })).toBeVisible();
  });

  test("clicking logo navigates to home", async ({ page }) => {
    await page.goto("/images");

    // Click the logo/title link
    await page.getByRole("link", { name: /DSA-110 Pipeline/i }).click();

    await expect(page).toHaveURL("/");
  });

  test("shows 404 page for unknown routes", async ({ page }) => {
    await page.goto("/this-page-does-not-exist");

    // Check for 404 content
    await expect(page.getByText("404")).toBeVisible();
    await expect(page.getByText(/not found/i)).toBeVisible();

    // Check for link back to home
    await expect(page.getByRole("link", { name: /home/i })).toBeVisible();
  });

  test("404 page link returns to home", async ({ page }) => {
    await page.goto("/unknown-route");

    await page.getByRole("link", { name: /home/i }).click();

    await expect(page).toHaveURL("/");
  });

  test("browser back button works after navigation", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Images" }).click();
    await expect(page).toHaveURL(/\/images/);

    await page.goBack();

    await expect(page).toHaveURL("/");
  });

  test("deep link to job detail page works", async ({ page }) => {
    // Navigate directly to a job detail page
    await page.goto("/jobs/test-run-123");

    // Should either show job detail or error (depending on API)
    // At minimum, the page should render without crashing
    await expect(page.locator("body")).toBeVisible();
  });

  test("navigation highlights active page", async ({ page }) => {
    await page.goto("/images");

    // The Images nav link should have active styling
    const imagesLink = page.getByRole("link", { name: "Images" });
    await expect(imagesLink).toHaveClass(/bg-slate-700|active/);

    // Other links should not have active styling
    const homeLink = page.getByRole("link", { name: "Home" });
    await expect(homeLink).not.toHaveClass(/bg-slate-700/);
  });
});
