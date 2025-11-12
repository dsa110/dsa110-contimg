import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for DSA-110 Dashboard E2E Tests
 * 
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: '/app/tests/e2e', // Absolute path to E2E tests
  
  /* Only match Playwright test files */
  testMatch: /.*\.(test|spec)\.(js|ts|tsx)$/,
  
  /* Ignore Vitest test files */
  testIgnore: [
    '**/node_modules/**',
    '**/src/**/*.test.tsx',
    '**/src/**/*.test.ts',
    '**/src/**/__tests__/**',
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
  reporter: [
    ['html'],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
  ],
  
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    /* When running in Docker container, use 5173 (internal port) */
    /* When running on host, use 5174 (mapped port) */
    baseURL: process.env.BASE_URL || (process.env.DOCKER_CONTAINER ? 'http://localhost:5173' : 'http://localhost:5174'),
    
    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',
    
    /* Screenshot on failure */
    screenshot: 'only-on-failure',
    
    /* Video on failure */
    video: 'retain-on-failure',
  },

  /* No webServer - we use Docker Compose to run the dev server */
  // webServer is intentionally not configured - server runs via docker compose

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { 
        ...devices['Desktop Chrome'],
        // Use system Chromium on Alpine Linux (musl libc incompatible with Playwright's glibc binaries)
        // Force use of system Chromium by setting both channel and executablePath
        channel: undefined, // Don't use Playwright's channel system
        executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || '/usr/bin/chromium-browser',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--headless'], // Required for Docker
      },
    },

    {
      name: 'firefox',
      use: { 
        ...devices['Desktop Firefox'],
        // Use system Firefox on Alpine Linux if available
        executablePath: process.env.PLAYWRIGHT_FIREFOX_EXECUTABLE_PATH || (process.platform === 'linux' ? '/usr/bin/firefox' : undefined),
        args: ['--headless'],
      },
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },

    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

});

