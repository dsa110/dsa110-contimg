/**
 * Page Object Model for Sky View Page
 */

import { Page, expect } from '@playwright/test';

export class SkyViewPage {
  constructor(private page: Page) {}

  async navigate() {
    await this.page.goto('/sky');
    await this.page.waitForLoadState('networkidle');
  }

  async waitForImageLoad() {
    // Wait for JS9 to load or image to appear
    await this.page.waitForSelector('#skyViewDisplay canvas, .JS9', { timeout: 10000 });
  }

  async selectImage(imageName: string) {
    await this.page.click(`text=${imageName}`);
  }

  async verifyImageStatisticsVisible() {
    await expect(this.page.locator('text=Image Statistics')).toBeVisible();
  }

  async verifyPhotometryPluginVisible() {
    await expect(this.page.locator('text=DSA Photometry')).toBeVisible();
  }
}

