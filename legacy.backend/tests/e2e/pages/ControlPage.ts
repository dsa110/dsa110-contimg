/**
 * Page Object Model for Control Page
 */

import { Page, expect } from '@playwright/test';

export class ControlPage {
  constructor(private page: Page) {}

  async navigate() {
    await this.page.goto('/control');
    await this.page.waitForLoadState('networkidle');
  }

  async clickTab(tabName: string) {
    await this.page.click(`text=${tabName}`);
  }

  async fillField(label: string, value: string) {
    const field = this.page.locator(`label:has-text("${label}")`).locator('..').locator('input, textarea, select').first();
    await field.fill(value);
  }

  async verifyTabContent(visibleText: string) {
    await expect(this.page.locator(`text=${visibleText}`)).toBeVisible();
  }

  async verifySubmitButtonDisabled() {
    const submitButton = this.page.locator('button[type="submit"]');
    await expect(submitButton).toBeDisabled();
  }

  async selectOption(label: string, optionText: string) {
    const select = this.page.locator(`label:has-text("${label}")`).locator('..').locator('select').first();
    await select.selectOption({ label: optionText });
  }

  // MS Details Panel methods
  async getMSDetailsPanel() {
    return this.page.locator('#ms-details-panel');
  }

  async toggleMSDetailsPanel() {
    const toggle = this.page.locator('#ms-details-panel [aria-expanded]').first();
    if (await toggle.count() > 0) {
      await toggle.click();
      await this.page.waitForTimeout(300); // Wait for animation
    }
  }

  async clickMSDetailsTab(tabName: string) {
    await this.page.click(`text=${tabName}`);
    await this.page.waitForTimeout(300); // Wait for tab content to load
  }

  async verifyMSDetailsPanelVisible() {
    const panel = await this.getMSDetailsPanel();
    await expect(panel).toBeVisible();
  }

  async selectMSFromTable(index: number = 0) {
    const table = this.page.locator('table, [role="table"], .MuiTable-root').first();
    const rows = table.locator('tbody tr');
    if (await rows.count() > index) {
      await rows.nth(index).click();
      await this.page.waitForTimeout(1000); // Wait for panel to appear
    }
  }
}

