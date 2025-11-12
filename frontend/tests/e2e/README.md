# E2E Testing Guide

## Overview

This directory contains end-to-end (E2E) tests for the DSA-110 Dashboard using Playwright. The tests verify that the dashboard works correctly from a user's perspective.

**✅ Latest Test Run:** November 11, 2025, 7:55 PM PT - **All 22 tests passing**  
See [TEST_EXECUTION_SUCCESS.md](./TEST_EXECUTION_SUCCESS.md) for details.

## Test Structure

```
tests/e2e/
├── README.md                    # This file
├── NEXT_STEPS.md                # Future testing roadmap
├── combined-testing-strategy.md # Testing strategy document
├── dashboard-combined.spec.ts   # Main dashboard tests (Sky View)
├── dashboard-page.spec.ts       # Dashboard page tests
├── data-browser.spec.ts         # Data Browser page tests
├── interactions.spec.ts         # User interaction tests
├── skyview-fixes.spec.ts        # Sky View specific fixes tests
├── helpers/
│   ├── page-helpers.ts          # Page interaction helpers
│   └── api-helpers.ts           # API testing helpers
└── fixtures/
    └── test-data.ts             # Test data constants
```

## Running Tests

### Prerequisites

- Docker and Docker Compose installed
- Dashboard services running (via `docker compose up`)

### Quick Start

```bash
# Run all E2E tests
npm run test:e2e

# Run tests in UI mode (interactive)
npm run test:e2e:ui

# Run tests in headed mode (see browser)
npm run test:e2e:headed

# Run only smoke tests
npm run test:e2e:smoke

# Debug a specific test
npm run test:e2e:debug
```

### Running in Docker

Tests are designed to run in Docker for consistency:

```bash
cd frontend
docker run --rm \
  -v "$(pwd):/app" \
  -w /app \
  --network host \
  node:22 \
  sh -c "apt-get update -qq && \
         apt-get install -y -qq libnspr4 libnss3 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libxkbcommon0 libasound2 >/dev/null 2>&1 && \
         npx playwright install chromium >/dev/null 2>&1 && \
         npx playwright test --project=chromium"
```

## Test Tags

Tests can be tagged for selective execution:

- `@smoke` - Quick smoke tests for critical functionality
- `@regression` - Full regression test suite
- `@slow` - Long-running tests

Example:
```typescript
test('Critical feature test @smoke', async ({ page }) => {
  // Test code
});
```

Run tagged tests:
```bash
npx playwright test --grep @smoke
```

## Writing Tests

### Basic Test Structure

```typescript
import { test, expect } from '@playwright/test';
import { navigateToPage, waitForDashboardLoad } from './helpers/page-helpers';
import { testRoutes } from './fixtures/test-data';

test.describe('My Feature', () => {
  test.beforeEach(async ({ page }) => {
    await navigateToPage(page, testRoutes.dashboard);
  });

  test('should do something', async ({ page }) => {
    await waitForDashboardLoad(page);
    // Your test code here
  });
});
```

### Using Helpers

**Page Helpers:**
```typescript
import { navigateToPage, waitForAPILoad, isElementVisible } from './helpers/page-helpers';

await navigateToPage(page, '/sky');
await waitForAPILoad(page);
const visible = await isElementVisible(page, '#myElement');
```

**API Helpers:**
```typescript
import { APIMonitor, waitForAPIRequest } from './helpers/api-helpers';

const monitor = new APIMonitor(page);
await waitForAPIRequest(page, '/api/status');
const requests = monitor.getRequests();
```

### Best Practices

1. **Use helpers** - Don't repeat common patterns
2. **Wait for elements** - Use `waitFor` instead of `waitForTimeout`
3. **Use data-testid** - Prefer stable selectors over CSS classes
4. **Test user flows** - Test what users actually do
5. **Keep tests independent** - Each test should work in isolation
6. **Clean up** - Use `afterEach` for cleanup if needed

### Common Patterns

**Waiting for API calls:**
```typescript
await page.waitForResponse(response => 
  response.url().includes('/api/status') && response.status() === 200
);
```

**Checking for errors:**
```typescript
const errors: string[] = [];
page.on('console', (msg) => {
  if (msg.type() === 'error') {
    errors.push(msg.text());
  }
});
// ... do something ...
const criticalErrors = errors.filter(e => !e.includes('favicon'));
expect(criticalErrors.length).toBe(0);
```

**Taking screenshots:**
```typescript
await page.screenshot({ path: 'test-results/screenshot.png', fullPage: true });
```

## Test Reports

After running tests, view the HTML report:

```bash
npm run test:e2e:report
```

Or open `playwright-report/index.html` in a browser.

## CI/CD Integration

Tests run automatically in CI/CD (GitHub Actions) on:
- Push to `main` or `develop` branches
- Pull requests
- Manual workflow dispatch

See `.github/workflows/e2e-tests.yml` for configuration.

## Debugging Tests

### Debug Mode

Run tests in debug mode to step through:
```bash
npm run test:e2e:debug
```

### Headed Mode

See the browser while tests run:
```bash
npm run test:e2e:headed
```

### UI Mode

Interactive test runner:
```bash
npm run test:e2e:ui
```

### Screenshots and Videos

Failed tests automatically capture:
- Screenshots: `test-results/`
- Videos: `test-results/` (if configured)

### Console Logs

Check browser console logs:
```typescript
page.on('console', msg => console.log('Browser:', msg.text()));
```

## Troubleshooting

### Tests fail with "Executable doesn't exist"

Install Playwright browsers:
```bash
npx playwright install chromium
```

### Tests timeout

- Increase timeout: `test.setTimeout(60000)`
- Check if services are running: `docker compose ps`
- Verify dashboard is accessible: `curl http://localhost:5174`

### Flaky tests

- Add explicit waits instead of `waitForTimeout`
- Use `waitForLoadState('networkidle')`
- Check for race conditions
- Use `waitForSelector` with proper state

### Port conflicts

Ensure only one instance of the dashboard is running:
```bash
lsof -i :5174
# Kill if needed
```

## Related Documentation

- [Playwright Documentation](https://playwright.dev/)
- [Testing Strategy](./combined-testing-strategy.md)
- [Next Steps](./NEXT_STEPS.md)
- [Dashboard API Reference](../../../docs/reference/dashboard_backend_api.md)

