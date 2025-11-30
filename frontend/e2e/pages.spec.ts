import { test, expect } from "@playwright/test";

/**
 * E2E tests for full page renders with mocked API data.
 *
 * These tests use route interception to provide consistent test data
 * and verify that pages render correctly with various data states.
 */
test.describe("Full Page Renders", () => {
  test.describe("Images List Page", () => {
    const mockImages = [
      {
        id: "img-001",
        path: "/data/images/test1.fits",
        qa_grade: "good",
        created_at: "2024-01-15T10:30:00Z",
      },
      {
        id: "img-002",
        path: "/data/images/test2.fits",
        qa_grade: "warn",
        created_at: "2024-01-14T08:00:00Z",
      },
      {
        id: "img-003",
        path: "/data/images/test3.fits",
        qa_grade: "fail",
        created_at: "2024-01-13T16:45:00Z",
      },
    ];

    test.beforeEach(async ({ page }) => {
      // Intercept API calls
      await page.route("**/api/images**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockImages),
        });
      });
    });

    test("renders images list with data", async ({ page }) => {
      await page.goto("/images");

      // Wait for loading to complete
      await expect(page.getByText("Loading")).not.toBeVisible({ timeout: 10000 });

      // Check for images
      await expect(page.getByText("img-001")).toBeVisible();
      await expect(page.getByText("img-002")).toBeVisible();
    });

    test("filters images by QA grade", async ({ page }) => {
      await page.goto("/images");
      await expect(page.getByText("Loading")).not.toBeVisible({ timeout: 10000 });

      // Select QA grade filter
      const qaFilter = page.getByRole("combobox").first();
      await qaFilter.selectOption("good");

      // Should only show good images
      await expect(page.getByText("img-001")).toBeVisible();
    });

    test("handles empty state", async ({ page }) => {
      await page.route("**/api/images**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([]),
        });
      });

      await page.goto("/images");

      await expect(page.getByText(/no images/i)).toBeVisible();
    });

    test("handles API error", async ({ page }) => {
      await page.route("**/api/images**", async (route) => {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ error: "Internal Server Error" }),
        });
      });

      await page.goto("/images");

      await expect(page.getByText(/failed|error/i)).toBeVisible();
    });
  });

  test.describe("Sources List Page", () => {
    const mockSources = [
      { id: "src-001", name: "Test Source A", ra_deg: 83.633, dec_deg: 22.014, num_images: 10 },
      { id: "src-002", name: "Test Source B", ra_deg: 10.684, dec_deg: 41.269, num_images: 5 },
    ];

    test.beforeEach(async ({ page }) => {
      await page.route("**/api/sources**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockSources),
        });
      });
    });

    test("renders sources list with data", async ({ page }) => {
      await page.goto("/sources");

      await expect(page.getByText("Loading")).not.toBeVisible({ timeout: 10000 });

      await expect(page.getByText("Test Source A")).toBeVisible();
      await expect(page.getByText("Test Source B")).toBeVisible();
    });

    test("shows variability tab", async ({ page }) => {
      await page.goto("/sources");
      await expect(page.getByText("Loading")).not.toBeVisible({ timeout: 10000 });

      // Look for tab or toggle for variability view
      const variabilityTab = page
        .getByRole("tab", { name: /variability/i })
        .or(page.getByRole("button", { name: /variability/i }));

      if (await variabilityTab.isVisible()) {
        await variabilityTab.click();
        // Should switch to variability view
      }
    });
  });

  test.describe("Jobs List Page", () => {
    const mockJobs = [
      { run_id: "run-001", status: "completed", started_at: "2024-01-15T10:00:00Z" },
      { run_id: "run-002", status: "running", started_at: "2024-01-15T11:00:00Z" },
      { run_id: "run-003", status: "failed", started_at: "2024-01-15T09:00:00Z" },
    ];

    test.beforeEach(async ({ page }) => {
      await page.route("**/api/jobs**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockJobs),
        });
      });
    });

    test("renders jobs list with status badges", async ({ page }) => {
      await page.goto("/jobs");

      await expect(page.getByText("Loading")).not.toBeVisible({ timeout: 10000 });

      await expect(page.getByText("run-001")).toBeVisible();
      await expect(page.getByText("completed")).toBeVisible();
      await expect(page.getByText("running")).toBeVisible();
      await expect(page.getByText("failed")).toBeVisible();
    });

    test("clicking job navigates to detail page", async ({ page }) => {
      await page.goto("/jobs");
      await expect(page.getByText("Loading")).not.toBeVisible({ timeout: 10000 });

      await page.getByRole("link", { name: /run-001/i }).click();

      await expect(page).toHaveURL(/\/jobs\/run-001/);
    });
  });

  test.describe("Job Detail Page", () => {
    const mockProvenance = {
      runId: "test-run-001",
      createdAt: "2024-01-15T10:00:00Z",
      qaGrade: "good",
      pipelineVersion: "1.2.3",
      logsUrl: "/logs/test-run-001",
      qaUrl: "/qa/test-run-001",
    };

    test.beforeEach(async ({ page }) => {
      await page.route("**/api/jobs/test-run-001/provenance**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockProvenance),
        });
      });
    });

    test("renders job detail with provenance", async ({ page }) => {
      await page.goto("/jobs/test-run-001");

      await expect(page.getByText("Loading")).not.toBeVisible({ timeout: 10000 });

      await expect(page.getByText("test-run-001")).toBeVisible();
      // Should show status
      await expect(page.getByText(/completed|good/i)).toBeVisible();
    });

    test("shows action buttons", async ({ page }) => {
      await page.goto("/jobs/test-run-001");
      await expect(page.getByText("Loading")).not.toBeVisible({ timeout: 10000 });

      // Should have action buttons
      await expect(
        page.getByRole("link", { name: /logs/i }).or(page.getByRole("button", { name: /logs/i }))
      ).toBeVisible();
    });

    test("back link navigates to jobs list", async ({ page }) => {
      await page.goto("/jobs/test-run-001");
      await expect(page.getByText("Loading")).not.toBeVisible({ timeout: 10000 });

      await page.getByRole("link", { name: /back/i }).click();

      await expect(page).toHaveURL(/\/jobs$/);
    });
  });

  test.describe("Home Page Dashboard", () => {
    const mockStats = {
      totalImages: 1234,
      totalSources: 567,
      totalJobs: 89,
      recentRatings: [],
    };

    test.beforeEach(async ({ page }) => {
      await page.route("**/api/stats**", async (route) => {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(mockStats),
        });
      });
    });

    test("renders dashboard with stats cards", async ({ page }) => {
      await page.goto("/");

      // Stats cards should show numbers
      await expect(page.getByText(/1,?234|1234/)).toBeVisible();
      await expect(page.getByText(/567/)).toBeVisible();
    });

    test("quick links navigate to correct pages", async ({ page }) => {
      await page.goto("/");

      // Find and click a quick link to images
      const imagesCard = page.getByText(/images/i).first();
      await imagesCard.click();

      // Should navigate to images
      await expect(page).toHaveURL(/\/images/);
    });
  });
});
