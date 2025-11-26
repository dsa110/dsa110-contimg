import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /.*\.(test|spec)\.(js|ts|tsx)$/,
  testIgnore: ["**/node_modules/**", "**/src/**/*.test.tsx"],

  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: "html",

  use: {
    baseURL: "http://localhost:3210",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off", // Disabled to avoid FFmpeg dependency
  },

  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        channel: "chrome", // Use system Chrome
      },
    },
  ],

  webServer: {
    command: 'echo "Frontend should be running on port 3210"',
    port: 3210,
    reuseExistingServer: !process.env.CI,
  },
});
