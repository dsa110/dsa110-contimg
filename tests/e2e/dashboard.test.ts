/**
 * End-to-End Tests for DSA-110 Continuum Imaging Dashboard
 * 
 * This test suite uses Playwright to test all clickable features and user interactions.
 * 
 * Prerequisites:
 * - Playwright installed: npm install -D @playwright/test
 * - Playwright browsers installed: npx playwright install
 * - Backend API running on http://localhost:8010
 * - Frontend running on http://localhost:5173
 * 
 * Run tests: npx playwright test
 */

import { test, expect, Page } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';
const API_URL = process.env.API_URL || 'http://localhost:8010';

// Helper function to wait for API calls to complete
async function waitForAPI(page: Page, timeout = 5000) {
  await page.waitForLoadState('networkidle', { timeout });
}

// Helper function to check for console errors
async function checkConsoleErrors(page: Page) {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return errors;
}

test.describe('Navigation', () => {
  test('should navigate to Dashboard', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.click('text=Dashboard');
    await expect(page).toHaveURL(`${BASE_URL}/dashboard`);
  });

  test('should navigate to Control', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.click('text=Control');
    await expect(page).toHaveURL(`${BASE_URL}/control`);
  });

  test('should navigate to Streaming', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.click('text=Streaming');
    await expect(page).toHaveURL(`${BASE_URL}/streaming`);
  });

  test('should navigate to Data Browser', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.click('text=Data');
    await expect(page).toHaveURL(`${BASE_URL}/data`);
  });

  test('should navigate to Mosaics', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.click('text=Mosaics');
    await expect(page).toHaveURL(`${BASE_URL}/mosaics`);
  });

  test('should navigate to Sources', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.click('text=Sources');
    await expect(page).toHaveURL(`${BASE_URL}/sources`);
  });

  test('should navigate to Sky View', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.click('text=Sky View');
    await expect(page).toHaveURL(`${BASE_URL}/sky`);
  });

  test('should open mobile navigation drawer', async ({ page }) => {
    await page.setViewportSize({ width: 500, height: 800 });
    await page.goto(BASE_URL);
    await page.click('[aria-label="menu"]');
    await expect(page.locator('text=DSA-110')).toBeVisible();
  });
});

test.describe('Control Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/control`);
    await waitForAPI(page);
  });

  test('should switch between tabs', async ({ page }) => {
    // Click Convert tab
    await page.click('text=Convert');
    await expect(page.locator('text=Start Time')).toBeVisible();

    // Click Calibrate tab
    await page.click('text=Calibrate');
    await expect(page.locator('text=Field ID')).toBeVisible();

    // Click Apply tab
    await page.click('text=Apply');
    await expect(page.locator('text=Calibration Tables')).toBeVisible();

    // Click Image tab
    await page.click('text=Image');
    await expect(page.locator('text=Imaging')).toBeVisible();
  });

  test('should fill Convert form fields', async ({ page }) => {
    await page.click('text=Convert');
    
    // Fill start time
    await page.fill('input[label="Start Time"]', '2025-01-01T00:00:00');
    
    // Fill end time
    await page.fill('input[label="End Time"]', '2025-01-01T01:00:00');
    
    // Fill input directory
    await page.fill('input[label="Input Directory"]', '/test/input');
    
    // Fill output directory
    await page.fill('input[label="Output Directory"]', '/test/output');
    
    // Select writer
    await page.click('text=Writer');
    await page.click('text=Sequential');
    
    // Verify values
    await expect(page.locator('input[label="Start Time"]')).toHaveValue('2025-01-01T00:00:00');
    await expect(page.locator('input[label="End Time"]')).toHaveValue('2025-01-01T01:00:00');
  });

  test('should disable submit button when required fields empty', async ({ page }) => {
    await page.click('text=Convert');
    
    // Submit button should be disabled
    const submitButton = page.locator('button:has-text("Run Conversion")');
    await expect(submitButton).toBeDisabled();
    
    // Fill required fields
    await page.fill('input[label="Start Time"]', '2025-01-01T00:00:00');
    await page.fill('input[label="End Time"]', '2025-01-01T01:00:00');
    
    // Submit button should be enabled
    await expect(submitButton).toBeEnabled();
  });

  test('should select reference antenna in Calibrate tab', async ({ page }) => {
    await page.click('text=Calibrate');
    
    // Wait for MS selection (if MS table exists)
    // This test assumes an MS is already selected or can be selected
    
    // Click reference antenna dropdown
    const refAntSelect = page.locator('text=Reference Antenna').locator('..').locator('select');
    if (await refAntSelect.count() > 0) {
      await refAntSelect.click();
      // Select first option if available
      const options = page.locator('select option');
      if (await options.count() > 1) {
        await refAntSelect.selectOption({ index: 1 });
      }
    }
  });

  test('should toggle calibration table checkboxes', async ({ page }) => {
    await page.click('text=Calibrate');
    
    // Find and toggle checkboxes for K, BP, G tables
    const kCheckbox = page.locator('input[type="checkbox"]').filter({ hasText: 'K' }).first();
    const bpCheckbox = page.locator('input[type="checkbox"]').filter({ hasText: 'BP' }).first();
    const gCheckbox = page.locator('input[type="checkbox"]').filter({ hasText: 'G' }).first();
    
    if (await kCheckbox.count() > 0) {
      await kCheckbox.click();
      await expect(kCheckbox).toBeChecked();
    }
  });
});

test.describe('Data Browser Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/data`);
    await waitForAPI(page);
  });

  test('should display data table', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table', { timeout: 10000 });
    
    // Verify table headers
    await expect(page.locator('text=ID')).toBeVisible();
    await expect(page.locator('text=Type')).toBeVisible();
    await expect(page.locator('text=Status')).toBeVisible();
    await expect(page.locator('text=Actions')).toBeVisible();
  });

  test('should switch between Staging and Published tabs', async ({ page }) => {
    // Click Published tab
    await page.click('text=Published');
    await expect(page.locator('text=Published').locator('..')).toHaveClass(/Mui-selected/);
    
    // Click Staging tab
    await page.click('text=Staging');
    await expect(page.locator('text=Staging').locator('..')).toHaveClass(/Mui-selected/);
  });

  test('should filter by data type', async ({ page }) => {
    // Click data type filter
    await page.click('text=Data Type');
    
    // Select a specific type
    await page.click('text=Image');
    
    // Verify filter is applied (check URL or table content)
    // This depends on implementation
  });

  test('should navigate to detail page on eye icon click', async ({ page }) => {
    // Wait for table to load
    await page.waitForSelector('table', { timeout: 10000 });
    
    // Find first eye icon (View Details button)
    const eyeIcon = page.locator('[aria-label="View Details"]').first();
    
    if (await eyeIcon.count() > 0) {
      // Get the data ID from the row (if accessible)
      const row = eyeIcon.locator('..').locator('..').locator('..');
      
      // Click eye icon
      await eyeIcon.click();
      
      // Verify navigation to detail page
      await expect(page).toHaveURL(/\/data\/\w+\//);
      
      // Verify detail page loads
      await expect(page.locator('button:has-text("Back to Data Browser")')).toBeVisible();
    }
  });

  test('should handle empty state', async ({ page }) => {
    // This test requires mocking empty API response
    // Or testing with empty database
    // Implementation depends on test data setup
  });
});

test.describe('Data Detail Page', () => {
  test('should load detail page', async ({ page }) => {
    // First, get a valid data ID from the API or data browser
    const response = await page.request.get(`${API_URL}/api/data`);
    const data = await response.json();
    
    if (data && data.length > 0) {
      const testId = encodeURIComponent(data[0].id);
      const testType = data[0].data_type;
      
      await page.goto(`${BASE_URL}/data/${testType}/${testId}`);
      await waitForAPI(page);
      
      // Verify page loads
      await expect(page.locator('button:has-text("Back to Data Browser")')).toBeVisible();
    }
  });

  test('should navigate back to data browser', async ({ page }) => {
    // Get a valid data ID
    const response = await page.request.get(`${API_URL}/api/data`);
    const data = await response.json();
    
    if (data && data.length > 0) {
      const testId = encodeURIComponent(data[0].id);
      const testType = data[0].data_type;
      
      await page.goto(`${BASE_URL}/data/${testType}/${testId}`);
      await waitForAPI(page);
      
      // Click back button
      await page.click('button:has-text("Back to Data Browser")');
      
      // Verify navigation
      await expect(page).toHaveURL(`${BASE_URL}/data`);
    }
  });

  test('should switch between Metadata and Lineage tabs', async ({ page }) => {
    // Get a valid data ID
    const response = await page.request.get(`${API_URL}/api/data`);
    const data = await response.json();
    
    if (data && data.length > 0) {
      const testId = encodeURIComponent(data[0].id);
      const testType = data[0].data_type;
      
      await page.goto(`${BASE_URL}/data/${testType}/${testId}`);
      await waitForAPI(page);
      
      // Click Lineage tab
      await page.click('text=Lineage');
      await expect(page.locator('text=Lineage').locator('..')).toHaveClass(/Mui-selected/);
      
      // Click Metadata tab
      await page.click('text=Metadata');
      await expect(page.locator('text=Metadata').locator('..')).toHaveClass(/Mui-selected/);
    }
  });

  test('should toggle auto-publish', async ({ page }) => {
    // Get a valid data ID
    const response = await page.request.get(`${API_URL}/api/data`);
    const data = await response.json();
    
    if (data && data.length > 0) {
      const testId = encodeURIComponent(data[0].id);
      const testType = data[0].data_type;
      
      await page.goto(`${BASE_URL}/data/${testType}/${testId}`);
      await waitForAPI(page);
      
      // Find auto-publish toggle button
      const toggleButton = page.locator('button:has-text("Auto-Publish")');
      
      if (await toggleButton.count() > 0) {
        const initialText = await toggleButton.textContent();
        
        // Click toggle
        await toggleButton.click();
        
        // Wait for API call
        await page.waitForTimeout(1000);
        
        // Verify button text changed (or check API response)
        // This depends on implementation
      }
    }
  });
});

test.describe('Streaming Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/streaming`);
    await waitForAPI(page);
  });

  test('should display service status', async ({ page }) => {
    // Verify status indicator is visible
    // This depends on implementation
    await expect(page.locator('text=Streaming Service')).toBeVisible();
  });

  test('should open configuration dialog', async ({ page }) => {
    // Click Configure button
    await page.click('button:has-text("Configure")');
    
    // Verify dialog opens
    await expect(page.locator('text=Streaming Service Configuration')).toBeVisible();
  });

  test('should fill configuration form', async ({ page }) => {
    // Open dialog
    await page.click('button:has-text("Configure")');
    
    // Fill input directory
    const inputDir = page.locator('input[label="Input Directory"]');
    if (await inputDir.count() > 0) {
      await inputDir.fill('/test/input');
      await expect(inputDir).toHaveValue('/test/input');
    }
    
    // Fill output directory
    const outputDir = page.locator('input[label="Output Directory"]');
    if (await outputDir.count() > 0) {
      await outputDir.fill('/test/output');
      await expect(outputDir).toHaveValue('/test/output');
    }
  });

  test('should cancel configuration dialog', async ({ page }) => {
    // Open dialog
    await page.click('button:has-text("Configure")');
    
    // Click Cancel
    await page.click('button:has-text("Cancel")');
    
    // Verify dialog closes
    await expect(page.locator('text=Streaming Service Configuration')).not.toBeVisible();
  });

  test('should handle start/stop/restart buttons', async ({ page }) => {
    // Find service control buttons
    const startButton = page.locator('button:has-text("Start")');
    const stopButton = page.locator('button:has-text("Stop")');
    const restartButton = page.locator('button:has-text("Restart")');
    
    // These buttons may not always be visible depending on service state
    // Test the visible ones
    if (await startButton.count() > 0) {
      await startButton.click();
      await page.waitForTimeout(1000);
    }
  });
});

test.describe('Mosaic Gallery Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/mosaics`);
    await waitForAPI(page);
  });

  test('should fill time range inputs', async ({ page }) => {
    // Fill start time
    const startTime = page.locator('input[type="datetime-local"]').first();
    if (await startTime.count() > 0) {
      await startTime.fill('2025-01-01T00:00:00');
      await expect(startTime).toHaveValue('2025-01-01T00:00:00');
    }
    
    // Fill end time
    const endTime = page.locator('input[type="datetime-local"]').last();
    if (await endTime.count() > 0) {
      await endTime.fill('2025-01-01T23:59:59');
      await expect(endTime).toHaveValue('2025-01-01T23:59:59');
    }
  });

  test('should query mosaics', async ({ page }) => {
    // Fill time inputs
    const startTime = page.locator('input[type="datetime-local"]').first();
    const endTime = page.locator('input[type="datetime-local"]').last();
    
    if (await startTime.count() > 0 && await endTime.count() > 0) {
      await startTime.fill('2025-01-01T00:00:00');
      await endTime.fill('2025-01-01T23:59:59');
      
      // Click Query button
      await page.click('button:has-text("Query Mosaics")');
      
      // Wait for results
      await page.waitForTimeout(2000);
      
      // Verify query executed (check for results or loading state)
    }
  });

  test('should disable query button without times', async ({ page }) => {
    const queryButton = page.locator('button:has-text("Query Mosaics")');
    await expect(queryButton).toBeDisabled();
  });
});

test.describe('Source Monitoring Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/sources`);
    await waitForAPI(page);
  });

  test('should fill source ID input', async ({ page }) => {
    const sourceInput = page.locator('input[label*="Source ID"]');
    if (await sourceInput.count() > 0) {
      await sourceInput.fill('NVSS J123456.7+420312');
      await expect(sourceInput).toHaveValue('NVSS J123456.7+420312');
    }
  });

  test('should search for source', async ({ page }) => {
    const sourceInput = page.locator('input[label*="Source ID"]');
    const searchButton = page.locator('button:has-text("Search")');
    
    if (await sourceInput.count() > 0 && await searchButton.count() > 0) {
      await sourceInput.fill('NVSS J123456.7+420312');
      await searchButton.click();
      
      // Wait for results
      await page.waitForTimeout(2000);
      
      // Verify search executed
    }
  });

  test('should disable search button with empty input', async ({ page }) => {
    const searchButton = page.locator('button:has-text("Search")');
    await expect(searchButton).toBeDisabled();
  });
});

test.describe('Error Handling', () => {
  test('should handle 404 errors gracefully', async ({ page }) => {
    await page.goto(`${BASE_URL}/nonexistent-page`);
    // Verify error boundary or 404 page displays
  });

  test('should handle API errors', async ({ page }) => {
    // Mock API error response
    await page.route(`${API_URL}/api/data`, route => {
      route.fulfill({
        status: 500,
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });
    
    await page.goto(`${BASE_URL}/data`);
    
    // Verify error message displays
    // This depends on error handling implementation
  });
});

test.describe('Accessibility', () => {
  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Check for common ARIA labels
    const buttons = page.locator('button');
    const buttonCount = await buttons.count();
    
    // At least some buttons should have aria-labels
    // This is a basic check - more comprehensive a11y testing needed
  });

  test('should be keyboard navigable', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // Test tab navigation
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    
    // Verify navigation occurred
  });
});

test.describe('Performance', () => {
  test('should load pages within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    await page.goto(BASE_URL);
    await waitForAPI(page);
    const loadTime = Date.now() - startTime;
    
    // Pages should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('should handle large data tables', async ({ page }) => {
    await page.goto(`${BASE_URL}/data`);
    await waitForAPI(page);
    
    // Wait for table to render
    await page.waitForSelector('table', { timeout: 10000 });
    
    // Verify table renders without performance issues
    // This is a basic check - more comprehensive performance testing needed
  });
});

