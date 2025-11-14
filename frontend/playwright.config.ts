import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright Configuration for DSA-110 Dashboard E2E Tests
 *
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: "/app/tests/e2e", // Absolute path to E2E tests

  /* Only match Playwright test files */
  testMatch: /.*\.(test|spec)\.(js|ts|tsx)$/,

  /* Ignore Vitest test files */
  testIgnore: [
    "**/node_modules/**",
    "**/src/**/*.test.tsx",
    "**/src/**/*.test.ts",
    "**/src/**/__tests__/**",
  ],

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Parallel execution: Use more workers locally, fewer on CI */
  workers: process.env.CI ? 2 : 4, // Increased from 1 to 2 on CI, 4 locally

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [["html"], ["list"], ["json", { outputFile: "test-results/results.json" }]],

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.BASE_URL || "http://localhost:5173",

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: "on-first-retry",

    /* Screenshot on failure */
    screenshot: "only-on-failure",

    /* Video on failure */
    video: "retain-on-failure",
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        args: ["--no-sandbox", "--disable-setuid-sandbox"], // Required for Docker
      },
    },

    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },

    {
      name: "webkit",
      use: { ...devices["Desktop Safari"] },
    },

    /* Test against mobile viewports. */
    {
      name: "Mobile Chrome",
      use: { ...devices["Pixel 5"] },
    },
    {
      name: "Mobile Safari",
      use: { ...devices["iPhone 12"] },
    },
  ],
});
