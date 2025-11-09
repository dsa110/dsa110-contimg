# End-to-End Testing Guide

## Overview

This directory contains end-to-end tests for the DSA-110 Continuum Imaging Dashboard using Playwright.

## Prerequisites

### Docker-Based Testing (Recommended for Ubuntu 18.x)

Since npm/npx requires Docker on Ubuntu 18.x systems, all E2E tests run in Docker containers.

1. **Install Docker**:
   ```bash
   # Ubuntu 18.x
   sudo apt-get update
   sudo apt-get install docker.io docker-compose
   sudo usermod -aG docker $USER
   # Log out and back in for group changes to take effect
   ```

2. **Start Services** (outside Docker or using docker-compose):
   - Backend API: `http://localhost:8010`
   - Frontend: `http://localhost:5173`

### Local Testing (if Node.js 22+ available)

If you have Node.js 22+ installed locally:

1. **Install Playwright**:
   ```bash
   npm install -D @playwright/test
   npx playwright install
   ```

2. **Start Services**:
   - Backend API: `http://localhost:8010`
   - Frontend: `http://localhost:5173`

## Running Tests

### Docker-Based Testing (Ubuntu 18.x)

#### Quick Start
```bash
# Run all tests using Docker
./scripts/run-tests.sh docker-e2e

# Or use Docker Compose for isolated environment
./scripts/run-tests-docker.sh up
```

#### Run Specific Test Suite
```bash
# Using simple Docker script
./scripts/run-tests.sh docker-e2e -- --grep "Navigation"

# Using Docker Compose
./scripts/run-tests-docker.sh up -- --grep "Navigation"
```

#### Run Tests in UI Mode
```bash
./scripts/run-tests-docker.sh ui
```

#### Run Tests in Debug Mode
```bash
# Build image first
./scripts/run-tests-docker.sh build

# Run with debug flags
docker run -it --rm --network host \
  -v "$(pwd)/test-results:/app/test-results" \
  -e BASE_URL="http://localhost:5173" \
  -e API_URL="http://localhost:8010" \
  dsa110-test:latest \
  npx playwright test --debug
```

#### Run Tests in Headed Mode
```bash
docker run -it --rm --network host \
  -v "$(pwd)/test-results:/app/test-results" \
  -e BASE_URL="http://localhost:5173" \
  -e API_URL="http://localhost:8010" \
  dsa110-test:latest \
  npx playwright test --headed
```

### Local Testing (if Node.js available)

#### Run All Tests
```bash
npx playwright test
```

#### Run Specific Test Suite
```bash
npx playwright test navigation
npx playwright test control
npx playwright test data-browser
```

#### Run Tests in UI Mode
```bash
npx playwright test --ui
```

#### Run Tests in Debug Mode
```bash
npx playwright test --debug
```

#### Run Tests in Headed Mode
```bash
npx playwright test --headed
```

#### Run Tests on Specific Browser
```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

#### Run Tests on Mobile Viewport
```bash
npx playwright test --project="Mobile Chrome"
```

## Test Structure

- `dashboard.test.ts`: Main test file with all test suites
- Tests are organized by page/feature:
  - Navigation
  - Control Page
  - Data Browser Page
  - Data Detail Page
  - Streaming Page
  - Mosaic Gallery Page
  - Source Monitoring Page
  - Error Handling
  - Accessibility
  - Performance

## Writing New Tests

### Basic Test Structure
```typescript
test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/path');
  });

  test('should do something', async ({ page }) => {
    // Test implementation
    await page.click('button');
    await expect(page.locator('text=Result')).toBeVisible();
  });
});
```

### Best Practices

1. **Use descriptive test names**: Clearly describe what is being tested
2. **Use beforeEach for setup**: Avoid repeating navigation code
3. **Wait for elements**: Use `waitForSelector` or `waitForLoadState`
4. **Use data-testid**: Add `data-testid` attributes to elements for reliable selection
5. **Clean up**: Reset state between tests if needed
6. **Mock API calls**: Use `page.route()` to mock API responses when needed

### Example Test
```typescript
test('should submit form and show success message', async ({ page }) => {
  await page.goto('/control');
  
  // Fill form
  await page.fill('input[name="startTime"]', '2025-01-01T00:00:00');
  await page.fill('input[name="endTime"]', '2025-01-01T01:00:00');
  
  // Submit
  await page.click('button[type="submit"]');
  
  // Wait for API call
  await page.waitForResponse(response => 
    response.url().includes('/api/jobs') && response.status() === 200
  );
  
  // Verify success
  await expect(page.locator('text=Job created successfully')).toBeVisible();
});
```

## Test Data

### Setting Up Test Data

1. **Database**: Ensure test database has sample data
2. **Files**: Create test MS files, images, etc.
3. **API Mocking**: Use `page.route()` for consistent test data

### Example API Mocking
```typescript
test('should display data table', async ({ page }) => {
  // Mock API response
  await page.route('**/api/data', route => {
    route.fulfill({
      status: 200,
      body: JSON.stringify([
        { id: 'test-1', data_type: 'ms', status: 'staging' },
        { id: 'test-2', data_type: 'image', status: 'published' },
      ]),
    });
  });
  
  await page.goto('/data');
  await expect(page.locator('table')).toBeVisible();
});
```

## Debugging Tests

### View Test Execution
```bash
npx playwright test --ui
```

### Debug Single Test
```bash
npx playwright test --debug test-name
```

### View Trace
```bash
npx playwright show-trace trace.zip
```

### Screenshots and Videos
- Screenshots: Saved to `test-results/` on failure
- Videos: Saved to `test-results/` on failure (if enabled)
- Traces: Saved to `test-results/` on retry

## CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm install
      - run: npx playwright install --with-deps
      - run: npx playwright test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: playwright-report/
```

## Troubleshooting

### Tests Failing Intermittently
- Increase timeouts
- Use `waitForLoadState('networkidle')`
- Add explicit waits for dynamic content

### Element Not Found
- Use `data-testid` attributes
- Check selector specificity
- Wait for element to be visible

### API Calls Failing
- Verify backend is running
- Check API URL configuration
- Mock API responses for consistency

## Coverage Goals

- **Critical Paths**: 100% coverage
- **User Flows**: 100% coverage
- **Edge Cases**: 80%+ coverage
- **Error Handling**: 100% coverage

## Maintenance

- Update tests when features change
- Review test failures regularly
- Remove obsolete tests
- Add tests for new features
- Keep test data up to date

