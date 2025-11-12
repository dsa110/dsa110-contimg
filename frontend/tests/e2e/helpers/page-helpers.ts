import { Page, expect } from '@playwright/test';

/**
 * Helper functions for common page interactions and assertions
 */

/**
 * Wait for the dashboard to be fully loaded
 */
export async function waitForDashboardLoad(page: Page, timeout = 30000): Promise<void> {
  // Wait for React to be ready
  await page.waitForLoadState('networkidle', { timeout });
  
  // Wait for any loading indicators to disappear
  await page.waitForSelector('[data-testid="loading"]', { state: 'hidden', timeout: 5000 }).catch(() => {});
}

/**
 * Navigate to a dashboard page and wait for it to load
 */
export async function navigateToPage(page: Page, path: string): Promise<void> {
  await page.goto(path);
  await waitForDashboardLoad(page);
}

/**
 * Wait for API requests to complete
 */
export async function waitForAPILoad(page: Page, timeout = 10000): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Check if an element is visible and not hidden
 */
export async function isElementVisible(page: Page, selector: string): Promise<boolean> {
  try {
    const element = page.locator(selector).first();
    await expect(element).toBeVisible({ timeout: 5000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Wait for text to appear on the page
 */
export async function waitForText(page: Page, text: string, timeout = 10000): Promise<void> {
  await page.waitForSelector(`text=${text}`, { timeout, state: 'visible' });
}

/**
 * Get console errors (for debugging)
 */
export async function getConsoleErrors(page: Page): Promise<string[]> {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });
  return errors;
}

/**
 * Take a screenshot with a descriptive name
 */
export async function takeScreenshot(page: Page, name: string): Promise<void> {
  await page.screenshot({ 
    path: `test-results/screenshots/${name}-${Date.now()}.png`,
    fullPage: true 
  });
}

/**
 * Check for MUI Grid deprecation warnings
 */
export async function checkMUIDeprecationWarnings(page: Page): Promise<string[]> {
  const warnings: string[] = [];
  page.on('console', (msg) => {
    const text = msg.text();
    if (text.includes('MUI Grid') && (text.includes('deprecated') || text.includes('item prop'))) {
      warnings.push(text);
    }
  });
  return warnings;
}

/**
 * Wait for JS9 to be initialized
 */
export async function waitForJS9Ready(page: Page, displayId: string, timeout = 15000): Promise<void> {
  await page.waitForFunction(
    (id) => {
      return typeof window !== 'undefined' && 
             typeof (window as any).JS9 !== 'undefined' &&
             (window as any).JS9.GetDisplayID(id) !== null;
    },
    displayId,
    { timeout }
  );
}

/**
 * Check if API endpoint responded successfully
 */
export async function verifyAPIResponse(
  page: Page, 
  endpointPattern: string | RegExp, 
  expectedStatus = 200
): Promise<boolean> {
  const response = await page.waitForResponse(
    (response) => {
      const url = response.url();
      const matches = typeof endpointPattern === 'string' 
        ? url.includes(endpointPattern)
        : endpointPattern.test(url);
      return matches && response.status() === expectedStatus;
    },
    { timeout: 10000 }
  ).catch(() => null);
  
  return response !== null;
}

