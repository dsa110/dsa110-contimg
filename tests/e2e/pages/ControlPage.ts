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
}

