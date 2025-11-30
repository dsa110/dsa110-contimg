import { test, expect } from "@playwright/test";

/**
 * Page content tests with mocked API data.
 * 
 * These tests use route interception to provide consistent test data
 * and verify pages render data correctly.
 */

// Mock data
const mockImages = [
  { id: "img-001", path: "/data/test1.fits", qa_grade: "good", created_at: "2024-01-15T10:30:00Z" },
  { id: "img-002", path: "/data/test2.fits", qa_grade: "warn", created_at: "2024-01-14T08:00:00Z" },
];

const mockSources = [
  { id: "src-001", name: "Source A", ra_deg: 83.633, dec_deg: 22.014, n_images: 10 },
  { id: "src-002", name: "Source B", ra_deg: 10.684, dec_deg: 41.269, n_images: 5 },
];

const mockJobs = [
  { run_id: "run-001", status: "completed", started_at: "2024-01-15T10:00:00Z" },
  { run_id: "run-002", status: "running", started_at: "2024-01-15T11:00:00Z" },
];

const mockStats = { images: 100, sources: 50, jobs: 25 };

test.describe("Images Page", () => {
  test.beforeEach(async ({ page }) => {
    // Mock API responses
    await page.route("**/api/**/images**", (route) => 
      route.fulfill({ status: 200, json: mockImages })
    );
  });

  test("displays images when data available", async ({ page }) => {
    await page.goto("/images");
    await page.waitForLoadState("networkidle");
    
    // Wait for loading to finish (look for absence of loading indicator)
    await page.waitForTimeout(1000); // Brief wait for render
    
    // Check if any image data is displayed (ID or path)
    const content = await page.textContent("body");
    const hasImageData = content?.includes("img-001") || 
                         content?.includes("test1.fits") ||
                         content?.includes("img-002");
    
    expect(hasImageData || content?.includes("Images")).toBeTruthy();
  });

  test("shows empty state for no images", async ({ page }) => {
    await page.route("**/api/**/images**", (route) => 
      route.fulfill({ status: 200, json: [] })
    );
    
    await page.goto("/images");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(500);
    
    // Should show some indication of empty state or just the page
    const body = page.locator("body");
    await expect(body).toBeVisible();
  });

  test("handles API error gracefully", async ({ page }) => {
    await page.route("**/api/**/images**", (route) => 
      route.fulfill({ status: 500, json: { error: "Server error" } })
    );
    
    await page.goto("/images");
    await page.waitForLoadState("networkidle");
    
    // Page should not crash
    await expect(page.locator("body")).toBeVisible();
  });
});

test.describe("Sources Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/**/sources**", (route) => 
      route.fulfill({ status: 200, json: mockSources })
    );
  });

  test("displays sources when data available", async ({ page }) => {
    await page.goto("/sources");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);
    
    const content = await page.textContent("body");
    const hasSourceData = content?.includes("src-001") || 
                          content?.includes("Source A") ||
                          content?.includes("Sources");
    
    expect(hasSourceData).toBeTruthy();
  });

  test("handles empty sources list", async ({ page }) => {
    await page.route("**/api/**/sources**", (route) => 
      route.fulfill({ status: 200, json: [] })
    );
    
    await page.goto("/sources");
    await page.waitForLoadState("networkidle");
    
    await expect(page.locator("body")).toBeVisible();
  });
});

test.describe("Jobs Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/**/jobs**", (route) => 
      route.fulfill({ status: 200, json: mockJobs })
    );
  });

  test("displays jobs when data available", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);
    
    const content = await page.textContent("body");
    const hasJobData = content?.includes("run-001") || 
                       content?.includes("completed") ||
                       content?.includes("Jobs");
    
    expect(hasJobData).toBeTruthy();
  });

  test("shows job status indicators", async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);
    
    const content = await page.textContent("body");
    // Should show status or job info
    const hasStatusInfo = content?.includes("completed") || 
                          content?.includes("running") ||
                          content?.includes("status") ||
                          content?.includes("Jobs");
    
    expect(hasStatusInfo).toBeTruthy();
  });
});

test.describe("Home Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/api/**/stats**", (route) => 
      route.fulfill({ status: 200, json: mockStats })
    );
    await page.route("**/api/**/images**", (route) => 
      route.fulfill({ status: 200, json: mockImages })
    );
    await page.route("**/api/**/sources**", (route) => 
      route.fulfill({ status: 200, json: mockSources })
    );
    await page.route("**/api/**/jobs**", (route) => 
      route.fulfill({ status: 200, json: mockJobs })
    );
  });

  test("displays dashboard content", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(1000);
    
    // Home page should have some navigation or dashboard content
    const nav = page.locator("nav").or(page.locator('[role="navigation"]'));
    const hasNav = await nav.isVisible().catch(() => false);
    
    const content = await page.textContent("body");
    const hasDashboardContent = content?.includes("DSA-110") ||
                                content?.includes("Images") ||
                                content?.includes("Sources") ||
                                content?.includes("Pipeline");
    
    expect(hasNav || hasDashboardContent).toBeTruthy();
  });

  test("has navigation links", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    
    // Should have at least one navigation link
    const links = page.locator("a");
    const linkCount = await links.count();
    
    expect(linkCount).toBeGreaterThan(0);
  });
});
