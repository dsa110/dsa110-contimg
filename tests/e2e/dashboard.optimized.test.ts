/**
 * End-to-End Tests for DSA-110 Continuum Imaging Dashboard - OPTIMIZED VERSION
 * 
 * Optimizations applied:
 * 1. Page Object Model (POM) for reusable page interactions
 * 2. Shared navigation helpers
 * 3. Reduced code duplication
 * 4. Better test organization
 */

import { test, expect } from '@playwright/test';
import { DashboardPage } from './pages/DashboardPage';
import { ControlPage } from './pages/ControlPage';
import { SkyViewPage } from './pages/SkyViewPage';

const BASE_URL = process.env.BASE_URL || 'http://localhost:5173';

test.describe('Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
  });

  // Parameterized test for navigation links
  const navigationTests = [
    { linkText: 'Dashboard', expectedUrl: '/dashboard' },
    { linkText: 'Control', expectedUrl: '/control' },
    { linkText: 'Streaming', expectedUrl: '/streaming' },
    { linkText: 'Data', expectedUrl: '/data' },
    { linkText: 'Mosaics', expectedUrl: '/mosaics' },
    { linkText: 'Sources', expectedUrl: '/sources' },
    { linkText: 'Sky View', expectedUrl: '/sky' },
  ];
  
  for (const { linkText, expectedUrl } of navigationTests) {
    test(`should navigate to ${linkText}`, async ({ page }) => {
      const dashboard = new DashboardPage(page);
      await dashboard.clickNavigationLink(linkText);
      await dashboard.verifyURL(`${BASE_URL}${expectedUrl}`);
    });
  }

  test('should open mobile navigation drawer', async ({ page }) => {
    const dashboard = new DashboardPage(page);
    await dashboard.setMobileViewport();
    await dashboard.openMobileMenu();
    await dashboard.verifyElementVisible('text=DSA-110');
  });
});

test.describe('Control Page', () => {
  test.beforeEach(async ({ page }) => {
    const controlPage = new ControlPage(page);
    await controlPage.navigate();
  });

  // Parameterized test for tab switching
  const tabTests = [
    { tabName: 'Convert', expectedContent: 'Start Time' },
    { tabName: 'Calibrate', expectedContent: 'Field ID' },
  ];
  
  for (const { tabName, expectedContent } of tabTests) {
    test(`should switch to ${tabName} tab`, async ({ page }) => {
      const controlPage = new ControlPage(page);
      await controlPage.clickTab(tabName);
      await controlPage.verifyTabContent(expectedContent);
    });
  }

  test('should fill Convert form fields', async ({ page }) => {
    const controlPage = new ControlPage(page);
    await controlPage.clickTab('Convert');
    await controlPage.fillField('Start Time', '2024-01-01T00:00:00');
    // Add more field fills as needed
  });

  test('should disable submit button when required fields empty', async ({ page }) => {
    const controlPage = new ControlPage(page);
    await controlPage.clickTab('Convert');
    await controlPage.verifySubmitButtonDisabled();
  });

  test('should select reference antenna in Calibrate tab', async ({ page }) => {
    const controlPage = new ControlPage(page);
    await controlPage.clickTab('Calibrate');
    await controlPage.selectOption('Reference Antenna', 'Antenna 1');
  });
});

test.describe('Sky View Page', () => {
  test.beforeEach(async ({ page }) => {
    const skyView = new SkyViewPage(page);
    await skyView.navigate();
  });

  test('should display image statistics plugin', async ({ page }) => {
    const skyView = new SkyViewPage(page);
    // Wait for page to load
    await page.waitForTimeout(1000); // Allow JS9 to initialize
    await skyView.verifyImageStatisticsVisible();
  });

  test('should display photometry plugin', async ({ page }) => {
    const skyView = new SkyViewPage(page);
    await page.waitForTimeout(1000); // Allow JS9 to initialize
    await skyView.verifyPhotometryPluginVisible();
  });
});

