/**
 * Page Object Model for Dashboard Page
 * 
 * Provides reusable methods for interacting with the Dashboard page.
 * Reduces code duplication and improves test maintainability.
 */

import { Page, expect } from '@playwright/test';

export class DashboardPage {
  constructor(private page: Page) {}

  async navigate() {
    await this.page.goto('/dashboard');
    await this.page.waitForLoadState('networkidle');
  }

  async waitForAPI(timeout = 5000) {
    await this.page.waitForLoadState('networkidle', { timeout });
  }

  async clickNavigationLink(linkText: string) {
    await this.page.click(`text=${linkText}`);
  }

  async verifyURL(url: string) {
    await expect(this.page).toHaveURL(url);
  }

  async verifyElementVisible(selector: string) {
    await expect(this.page.locator(selector)).toBeVisible();
  }

  async openMobileMenu() {
    await this.page.click('[aria-label="menu"]');
  }

  async setMobileViewport() {
    await this.page.setViewportSize({ width: 500, height: 800 });
  }
}

