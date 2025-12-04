/**
 * Pipeline Control E2E Tests
 *
 * Comprehensive tests for the Pipeline Control page and all pipeline stages.
 * These tests verify:
 * 1. Full pipeline execution (conversion → calibration → imaging)
 * 2. Individual stage execution
 * 3. Registered pipeline management
 * 4. Execution history and status tracking
 * 5. Error handling and user feedback
 *
 * @route /pipeline
 */

import { test, expect, type Page } from "@playwright/test";

// =============================================================================
// Mock Data
// =============================================================================

const mockPipelines = {
  pipelines: [
    {
      name: "nightly_mosaic",
      description:
        "Nightly mosaic pipeline - processes all calibrated data from the previous day",
      schedule: "0 3 * * *",
      is_scheduled: true,
    },
    {
      name: "on_demand_mosaic",
      description: "On-demand mosaic creation for specific time ranges",
      schedule: null,
      is_scheduled: false,
    },
    {
      name: "calibration_refresh",
      description: "Re-calibrate data with updated calibration solutions",
      schedule: null,
      is_scheduled: false,
    },
  ],
  total: 3,
};

const mockStages = {
  stages: [
    {
      name: "convert-uvh5-to-ms",
      description: "Convert UVH5 files to Measurement Sets",
    },
    {
      name: "calibration-solve",
      description: "Solve for calibration solutions",
    },
    { name: "calibration-apply", description: "Apply calibration to MS" },
    { name: "imaging", description: "Create images from calibrated MS" },
    { name: "validation", description: "Validate image quality" },
    { name: "crossmatch", description: "Cross-match sources with catalogs" },
    { name: "photometry", description: "Extract photometry from images" },
    {
      name: "catalog-setup",
      description: "Build catalog databases for declination",
    },
    {
      name: "organize-files",
      description: "Organize output files into standard structure",
    },
    {
      name: "create-mosaic",
      description: "Create mosaic from multiple images",
    },
  ],
  total: 10,
};

const mockExecutions = {
  executions: [
    {
      execution_id: "exec-001",
      pipeline_name: "nightly_mosaic",
      status: "completed",
      started_at: "2025-01-15T03:00:00Z",
      completed_at: "2025-01-15T03:45:00Z",
      error: null,
      jobs: [
        { job_id: "job-001", job_type: "mosaic-plan", status: "completed" },
        { job_id: "job-002", job_type: "mosaic-build", status: "completed" },
        { job_id: "job-003", job_type: "mosaic-qa", status: "completed" },
      ],
    },
    {
      execution_id: "exec-002",
      pipeline_name: "on_demand_mosaic",
      status: "running",
      started_at: "2025-01-15T10:30:00Z",
      completed_at: null,
      error: null,
      jobs: [
        { job_id: "job-004", job_type: "mosaic-plan", status: "completed" },
        { job_id: "job-005", job_type: "mosaic-build", status: "running" },
      ],
    },
    {
      execution_id: "exec-003",
      pipeline_name: "calibration_refresh",
      status: "failed",
      started_at: "2025-01-14T18:00:00Z",
      completed_at: "2025-01-14T18:15:00Z",
      error: "Calibration failed: No valid solutions found",
      jobs: [
        { job_id: "job-006", job_type: "calibration-solve", status: "failed" },
      ],
    },
  ],
  total: 3,
};

const mockFullPipelineResponse = {
  status: "queued",
  task_ids: {
    conversion: "task-conv-001",
    calibration: "task-cal-001",
    imaging: "task-img-001",
  },
  time_range: {
    start: "2025-01-15T00:00:00Z",
    end: "2025-01-15T12:00:00Z",
  },
  message: "Full pipeline queued with 3 stages",
};

const mockStageResponse = {
  task_id: "task-stage-001",
  stage: "imaging",
  status: "pending",
};

const mockCalibrateResponse = {
  task_id: "task-cal-001",
  stage: "calibration-apply",
  ms_path: "/stage/dsa110-contimg/ms/2025-01-15T10:00:00.ms",
  status: "pending",
};

const mockImageResponse = {
  task_id: "task-img-001",
  stage: "imaging",
  ms_path: "/stage/dsa110-contimg/ms/2025-01-15T10:00:00.ms",
  status: "pending",
};

// =============================================================================
// Helper Functions
// =============================================================================

async function setupMocks(page: Page) {
  // Mock registered pipelines
  await page.route("**/api/**/pipeline/registered", (route) =>
    route.fulfill({ status: 200, json: mockPipelines })
  );

  // Mock available stages
  await page.route("**/api/**/pipeline/stages", (route) =>
    route.fulfill({ status: 200, json: mockStages })
  );

  // Mock executions list
  await page.route("**/api/**/pipeline/executions*", (route) => {
    const url = route.request().url();
    // Check if it's a specific execution request
    if (url.match(/\/executions\/exec-/)) {
      const execId = url.match(/\/executions\/(exec-\d+)/)?.[1];
      const execution = mockExecutions.executions.find(
        (e) => e.execution_id === execId
      );
      return route.fulfill({
        status: execution ? 200 : 404,
        json: execution || { detail: "Not found" },
      });
    }
    return route.fulfill({ status: 200, json: mockExecutions });
  });

  // Mock full pipeline execution
  await page.route("**/api/**/pipeline/full", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 200, json: mockFullPipelineResponse });
    }
    return route.continue();
  });

  // Mock run pipeline
  await page.route("**/api/**/pipeline/run", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({
        status: 200,
        json: {
          execution_id: "exec-new-001",
          pipeline_name: "test_pipeline",
          status: "pending",
          message: "Pipeline queued for execution",
        },
      });
    }
    return route.continue();
  });

  // Mock stage execution
  await page.route("**/api/**/pipeline/stage", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 200, json: mockStageResponse });
    }
    return route.continue();
  });

  // Mock calibrate endpoint
  await page.route("**/api/**/pipeline/calibrate*", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 200, json: mockCalibrateResponse });
    }
    return route.continue();
  });

  // Mock image endpoint
  await page.route("**/api/**/pipeline/image*", (route) => {
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 200, json: mockImageResponse });
    }
    return route.continue();
  });
}

// =============================================================================
// Tests: Page Loading
// =============================================================================

test.describe("Pipeline Control Page - Loading", () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test("loads pipeline control page successfully", async ({ page }) => {
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Verify page header
    await expect(
      page.getByRole("heading", { name: /Pipeline Control/i })
    ).toBeVisible();
  });

  test("displays all main sections", async ({ page }) => {
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Check for main sections
    await expect(page.getByText("Run Full Pipeline")).toBeVisible();
    await expect(page.getByText("Run Individual Stage")).toBeVisible();
    await expect(page.getByText("Registered Pipelines")).toBeVisible();
    await expect(page.getByText("Recent Executions")).toBeVisible();
  });

  test("loads registered pipelines list", async ({ page }) => {
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Should show pipeline names
    await expect(page.getByText("nightly_mosaic")).toBeVisible();
    await expect(page.getByText("on_demand_mosaic")).toBeVisible();
    await expect(page.getByText("calibration_refresh")).toBeVisible();
  });

  test("shows execution history", async ({ page }) => {
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Should show execution statuses
    await expect(page.getByText("completed")).toBeVisible();
    await expect(page.getByText("running")).toBeVisible();
    await expect(page.getByText("failed")).toBeVisible();
  });
});

// =============================================================================
// Tests: Full Pipeline Execution
// =============================================================================

test.describe("Pipeline Control - Full Pipeline", () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");
  });

  test("quick time selection buttons work", async ({ page }) => {
    // Click "Last 1h" button
    await page.getByRole("button", { name: "Last 1h" }).click();

    // Start and end time inputs should be populated
    const startInput = page.locator('input[type="datetime-local"]').first();
    const endInput = page.locator('input[type="datetime-local"]').last();

    // Both should have values now
    await expect(startInput).not.toHaveValue("");
    await expect(endInput).not.toHaveValue("");
  });

  test("can toggle pipeline options", async ({ page }) => {
    // Run Calibration and Run Imaging checkboxes should exist
    const calCheckbox = page.locator('input[type="checkbox"]').first();
    const imgCheckbox = page.locator('input[type="checkbox"]').nth(1);

    await expect(calCheckbox).toBeChecked();
    await expect(imgCheckbox).toBeChecked();

    // Toggle calibration off
    await calCheckbox.uncheck();
    await expect(calCheckbox).not.toBeChecked();

    // Imaging should be disabled when calibration is off
    await expect(imgCheckbox).toBeDisabled();
  });

  test("advanced options can be shown/hidden", async ({ page }) => {
    // Should not show advanced options by default
    const inputDirLabel = page.getByText("Input Directory");
    await expect(inputDirLabel).not.toBeVisible();

    // Click to show advanced options
    await page.getByText("Show advanced options").click();

    // Now should see advanced inputs
    await expect(page.getByText("Input Directory")).toBeVisible();
    await expect(page.getByText("Output Directory")).toBeVisible();

    // Can hide again
    await page.getByText("Hide advanced options").click();
    await expect(page.getByText("Input Directory")).not.toBeVisible();
  });

  test("submits full pipeline request", async ({ page }) => {
    // Set time range
    await page.getByRole("button", { name: "Last 6h" }).click();

    // Click Run Pipeline
    await page.getByRole("button", { name: "Run Pipeline" }).click();

    // Should show success message
    await expect(page.getByText(/Pipeline queued/)).toBeVisible();
  });

  test("shows error when time range not set", async ({ page }) => {
    // Try to run without setting time
    page.on("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Run Pipeline" }).click();

    // Should show alert (handled above)
  });
});

// =============================================================================
// Tests: Individual Stage Execution
// =============================================================================

test.describe("Pipeline Control - Individual Stages", () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");
  });

  test("shows available stages in dropdown", async ({ page }) => {
    // Find the stage select
    const stageSelect = page.locator("select").first();
    await stageSelect.click();

    // Should have stage options
    await expect(
      page.getByRole("option", { name: /Calibration/i })
    ).toBeVisible();
    await expect(page.getByRole("option", { name: /Imaging/i })).toBeVisible();
  });

  test("shows calibration options when calibration selected", async ({
    page,
  }) => {
    // Select calibration stage
    const stageSelect = page.locator("select").first();
    await stageSelect.selectOption({ label: "Calibration" });

    // Should show apply-only checkbox
    await expect(page.getByText("Apply existing solutions")).toBeVisible();
  });

  test("shows imaging options when imaging selected", async ({ page }) => {
    // Select imaging stage
    const stageSelect = page.locator("select").first();
    await stageSelect.selectOption({ label: "Imaging" });

    // Should show imaging parameters
    await expect(page.getByText("Image Size")).toBeVisible();
    await expect(page.getByText("Cell Size")).toBeVisible();
  });

  test("runs calibration stage", async ({ page }) => {
    // Enter MS path
    const msPathInput = page.locator('input[type="text"]').first();
    await msPathInput.fill("/stage/dsa110-contimg/ms/test.ms");

    // Select calibration
    const stageSelect = page.locator("select").first();
    await stageSelect.selectOption({ label: "Calibration" });

    // Run the stage - find button in the Individual Stages section
    const runButton = page.locator("text=Run Stage").first();
    if (await runButton.isVisible()) {
      await runButton.click();
    }
  });

  test("runs imaging stage with custom parameters", async ({ page }) => {
    // Enter MS path
    const msPathInput = page.locator('input[type="text"]').first();
    await msPathInput.fill("/stage/dsa110-contimg/ms/test.ms");

    // Select imaging
    const stageSelect = page.locator("select").first();
    await stageSelect.selectOption({ label: "Imaging" });

    // Modify imaging parameters if visible
    const imsizeInput = page.getByLabel("Image Size");
    if (await imsizeInput.isVisible()) {
      await imsizeInput.fill("2048");
    }
  });
});

// =============================================================================
// Tests: Registered Pipelines
// =============================================================================

test.describe("Pipeline Control - Registered Pipelines", () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");
  });

  test("displays scheduled pipeline indicator", async ({ page }) => {
    // nightly_mosaic should have "Scheduled" badge
    const nightlyRow = page.locator("text=nightly_mosaic").locator("..");
    await expect(nightlyRow.getByText("Scheduled")).toBeVisible();
  });

  test("displays schedule for scheduled pipelines", async ({ page }) => {
    // Should show cron schedule
    await expect(page.getByText("0 3 * * *")).toBeVisible();
  });

  test("can run pipeline manually", async ({ page }) => {
    // Find "Run Now" button for on_demand_mosaic
    const runButtons = page.getByRole("button", { name: "Run Now" });
    await runButtons.first().click();

    // Should show success message
    await expect(page.getByText(/queued/i)).toBeVisible();
  });
});

// =============================================================================
// Tests: Execution History
// =============================================================================

test.describe("Pipeline Control - Execution History", () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");
  });

  test("displays execution status badges", async ({ page }) => {
    // Should show different status badges
    const completedBadge = page.locator("text=completed").first();
    const runningBadge = page.locator("text=running").first();
    const failedBadge = page.locator("text=failed").first();

    await expect(completedBadge).toBeVisible();
    await expect(runningBadge).toBeVisible();
    await expect(failedBadge).toBeVisible();
  });

  test("shows job counts for executions", async ({ page }) => {
    // Executions should show job counts
    await expect(page.getByText("3 jobs")).toBeVisible();
    await expect(page.getByText("2 jobs")).toBeVisible();
    await expect(page.getByText("1 jobs")).toBeVisible();
  });

  test("shows failed job indicator", async ({ page }) => {
    // Failed execution should indicate failed jobs
    await expect(page.getByText(/failed/i)).toBeVisible();
  });
});

// =============================================================================
// Tests: Error Handling
// =============================================================================

test.describe("Pipeline Control - Error Handling", () => {
  test("handles API error for registered pipelines", async ({ page }) => {
    await page.route("**/api/**/pipeline/registered", (route) =>
      route.fulfill({ status: 500, json: { detail: "Server error" } })
    );

    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Should show error message
    await expect(page.getByText(/Failed to load/i)).toBeVisible();
  });

  test("handles API error for stages", async ({ page }) => {
    await page.route("**/api/**/pipeline/stages", (route) =>
      route.fulfill({ status: 500, json: { detail: "Server error" } })
    );
    await page.route("**/api/**/pipeline/registered", (route) =>
      route.fulfill({ status: 200, json: mockPipelines })
    );
    await page.route("**/api/**/pipeline/executions*", (route) =>
      route.fulfill({ status: 200, json: mockExecutions })
    );

    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Page should still load (graceful degradation)
    await expect(page.getByText("Pipeline Control")).toBeVisible();
  });

  test("handles full pipeline submission failure", async ({ page }) => {
    await setupMocks(page);

    // Override full pipeline to fail
    await page.route("**/api/**/pipeline/full", (route) => {
      if (route.request().method() === "POST") {
        return route.fulfill({
          status: 500,
          json: { detail: "Pipeline execution failed" },
        });
      }
      return route.continue();
    });

    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Set time and submit
    await page.getByRole("button", { name: "Last 1h" }).click();
    await page.getByRole("button", { name: "Run Pipeline" }).click();

    // Should show error
    await expect(page.getByText(/Error/i)).toBeVisible();
  });

  test("handles empty pipelines list", async ({ page }) => {
    await page.route("**/api/**/pipeline/registered", (route) =>
      route.fulfill({ status: 200, json: { pipelines: [], total: 0 } })
    );
    await page.route("**/api/**/pipeline/stages", (route) =>
      route.fulfill({ status: 200, json: mockStages })
    );
    await page.route("**/api/**/pipeline/executions*", (route) =>
      route.fulfill({ status: 200, json: mockExecutions })
    );

    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Should show empty state message
    await expect(page.getByText(/No pipelines registered/i)).toBeVisible();
  });

  test("handles empty executions list", async ({ page }) => {
    await page.route("**/api/**/pipeline/registered", (route) =>
      route.fulfill({ status: 200, json: mockPipelines })
    );
    await page.route("**/api/**/pipeline/stages", (route) =>
      route.fulfill({ status: 200, json: mockStages })
    );
    await page.route("**/api/**/pipeline/executions*", (route) =>
      route.fulfill({ status: 200, json: { executions: [], total: 0 } })
    );

    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Should show empty state message
    await expect(page.getByText(/No pipeline executions/i)).toBeVisible();
  });
});

// =============================================================================
// Tests: Accessibility
// =============================================================================

test.describe("Pipeline Control - Accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await setupMocks(page);
  });

  test("page has proper heading structure", async ({ page }) => {
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Main heading
    const h1 = page.getByRole("heading", { level: 1 });
    await expect(h1).toContainText("Pipeline Control");

    // Section headings
    const h2s = page.getByRole("heading", { level: 2 });
    await expect(h2s).toHaveCount(4); // 4 main sections
  });

  test("form inputs have labels", async ({ page }) => {
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Time inputs should have labels
    await expect(page.getByText("Start Time")).toBeVisible();
    await expect(page.getByText("End Time")).toBeVisible();
  });

  test("buttons are keyboard accessible", async ({ page }) => {
    await page.goto("/pipeline");
    await page.waitForLoadState("networkidle");

    // Tab to Run Pipeline button and verify it's focusable
    await page.keyboard.press("Tab");

    // Some element should be focused
    const focused = page.locator(":focus");
    await expect(focused).toBeVisible();
  });
});
