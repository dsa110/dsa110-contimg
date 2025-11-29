import { test, expect } from "@playwright/test";

test.describe("DSA-110 Pipeline UI", () => {
  test("homepage loads and displays title", async ({ page }) => {
    await page.goto("/");

    // Check the main heading is visible
    await expect(page.getByRole("heading", { name: /DSA-110/i })).toBeVisible();

    // Check navigation bar links exist (using the nav element to be specific)
    const nav = page.locator("nav");
    await expect(nav.getByRole("link", { name: "Home" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Images" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Sources" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Jobs" })).toBeVisible();
  });

  test("can navigate to Images page", async ({ page }) => {
    await page.goto("/");

    // Click on Images link in navigation bar
    await page.locator("nav").getByRole("link", { name: "Images" }).click();

    // Should be on images page
    await expect(page).toHaveURL(/\/images/);
    await expect(page.getByRole("heading", { name: /Images/i })).toBeVisible();
  });

  test("can navigate to Sources page", async ({ page }) => {
    await page.goto("/");

    // Click on Sources link in navigation bar
    await page.locator("nav").getByRole("link", { name: "Sources" }).click();

    // Should be on sources page
    await expect(page).toHaveURL(/\/sources/);
    await expect(page.getByRole("heading", { name: /Sources/i })).toBeVisible();
  });

  test("can navigate to Jobs page", async ({ page }) => {
    await page.goto("/");

    // Click on Jobs link in navigation bar
    await page.locator("nav").getByRole("link", { name: "Jobs" }).click();

    // Should be on jobs page
    await expect(page).toHaveURL(/\/jobs/);
    await expect(page.getByRole("heading", { name: /Pipeline Jobs/i })).toBeVisible();
  });

  test("404 page shows for unknown routes", async ({ page }) => {
    await page.goto("/some-nonexistent-page");

    // Should show 404 content
    await expect(page.getByText("404")).toBeVisible();
    await expect(page.getByText("Page Not Found")).toBeVisible();
  });
});
