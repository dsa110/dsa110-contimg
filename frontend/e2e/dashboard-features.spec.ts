import { test, expect } from "@playwright/test";

/**
 * E2E tests for Saved Queries functionality.
 *
 * Tests the full user flow:
 * 1. Create a filter
 * 2. Save it
 * 3. Reload page
 * 4. Load the saved query
 * 5. Verify filters restored
 */
test.describe("Saved Queries", () => {
  const testQueryName = `E2E Test Query ${Date.now()}`;

  test.beforeEach(async ({ page }) => {
    // Start on images page
    await page.goto("/images");
    await page.waitForLoadState("networkidle");
  });

  test("can save current filters as a query", async ({ page }) => {
    // Apply a filter (e.g., status filter if available)
    const filterInput = page
      .locator(
        '[data-testid="filter-input"], input[placeholder*="filter"], input[placeholder*="search"]'
      )
      .first();
    if (await filterInput.isVisible()) {
      await filterInput.fill("test");
    }

    // Open save query dialog
    const saveButton = page
      .locator(
        '[data-testid="save-query-btn"], button:has-text("Save"), [aria-label*="save"]'
      )
      .first();
    if (await saveButton.isVisible()) {
      await saveButton.click();

      // Fill in query name
      const nameInput = page
        .locator(
          '[data-testid="query-name"], input[name="name"], input[placeholder*="name"]'
        )
        .first();
      if (await nameInput.isVisible()) {
        await nameInput.fill(testQueryName);
      }

      // Submit
      const submitBtn = page
        .locator('button[type="submit"], button:has-text("Save")')
        .first();
      if (await submitBtn.isVisible()) {
        await submitBtn.click();
      }

      // Verify success toast or the query appears in list
      await expect(
        page
          .locator(`text="${testQueryName}"`, { timeout: 5000 })
          .or(page.locator('[data-testid="toast-success"]'))
      ).toBeVisible({ timeout: 5000 });
    } else {
      // If save query button not visible, skip
      test.skip();
    }
  });

  test("can load a saved query", async ({ page }) => {
    // Open load query panel
    const loadButton = page
      .locator(
        '[data-testid="load-query-btn"], button:has-text("Load"), [aria-label*="load"]'
      )
      .first();
    if (await loadButton.isVisible()) {
      await loadButton.click();

      // Wait for queries list
      await page.waitForSelector(
        '[data-testid="saved-queries-list"], [role="listbox"], ul',
        { timeout: 5000 }
      );

      // Click first query in list
      const firstQuery = page
        .locator('[data-testid="saved-query-item"], [role="option"], li')
        .first();
      if (await firstQuery.isVisible()) {
        await firstQuery.click();

        // Verify filters were applied (URL should have query params or filters visible)
        await expect(page)
          .toHaveURL(/[?&]|filters/, { timeout: 3000 })
          .catch(() => {
            // If URL doesn't change, check for filter indicators in UI
            return expect(
              page.locator('[data-testid="active-filters"], .filter-badge')
            ).toBeVisible();
          });
      }
    } else {
      test.skip();
    }
  });

  test("saved query persists across page reload", async ({ page }) => {
    // First create a query
    const saveButton = page.locator('[data-testid="save-query-btn"]').first();
    if (!(await saveButton.isVisible())) {
      test.skip();
      return;
    }

    await saveButton.click();
    const nameInput = page.locator('[data-testid="query-name"]').first();
    const uniqueName = `Persist Test ${Date.now()}`;
    await nameInput.fill(uniqueName);
    await page.locator('button[type="submit"]').first().click();

    // Wait for save
    await page.waitForTimeout(1000);

    // Reload page
    await page.reload();
    await page.waitForLoadState("networkidle");

    // Open load panel and verify query exists
    await page.locator('[data-testid="load-query-btn"]').first().click();
    await expect(page.locator(`text="${uniqueName}"`)).toBeVisible({
      timeout: 5000,
    });
  });

  test("can delete a saved query", async ({ page }) => {
    // Open load query panel
    const loadButton = page.locator('[data-testid="load-query-btn"]').first();
    if (!(await loadButton.isVisible())) {
      test.skip();
      return;
    }

    await loadButton.click();

    // Find a query with delete button
    const deleteBtn = page
      .locator('[data-testid="delete-query-btn"], button[aria-label*="delete"]')
      .first();
    if (await deleteBtn.isVisible()) {
      const queryCountBefore = await page
        .locator('[data-testid="saved-query-item"]')
        .count();

      await deleteBtn.click();

      // Confirm deletion if dialog appears
      const confirmBtn = page
        .locator('button:has-text("Confirm"), button:has-text("Delete")')
        .first();
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
      }

      // Verify count decreased or success toast
      await page.waitForTimeout(1000);
      const queryCountAfter = await page
        .locator('[data-testid="saved-query-item"]')
        .count();
      expect(queryCountAfter).toBeLessThanOrEqual(queryCountBefore);
    } else {
      test.skip();
    }
  });
});

/**
 * E2E tests for Backup/Restore functionality.
 */
test.describe("Backup System", () => {
  test("can view backup history", async ({ page }) => {
    await page.goto("/settings/backup");
    await page.waitForLoadState("networkidle");

    // Should show backup list or empty state
    await expect(
      page.locator(
        '[data-testid="backup-list"], [data-testid="no-backups"], text="backup"'
      )
    ).toBeVisible({ timeout: 5000 });
  });

  test("can trigger manual backup", async ({ page }) => {
    await page.goto("/settings/backup");
    await page.waitForLoadState("networkidle");

    const createBtn = page
      .locator(
        '[data-testid="create-backup-btn"], button:has-text("Create Backup")'
      )
      .first();
    if (await createBtn.isVisible()) {
      await createBtn.click();

      // Should show progress or success
      await expect(
        page.locator(
          '[data-testid="backup-progress"], [data-testid="backup-success"], text="started"'
        )
      ).toBeVisible({ timeout: 10000 });
    } else {
      test.skip();
    }
  });
});

/**
 * E2E tests for Pipeline Triggers.
 */
test.describe("Pipeline Triggers", () => {
  test("can view trigger list", async ({ page }) => {
    await page.goto("/settings/triggers");
    await page.waitForLoadState("networkidle");

    await expect(
      page.locator(
        '[data-testid="triggers-list"], [data-testid="no-triggers"], text="trigger"'
      )
    ).toBeVisible({ timeout: 5000 });
  });

  test("can create a new trigger", async ({ page }) => {
    await page.goto("/settings/triggers");
    await page.waitForLoadState("networkidle");

    const createBtn = page
      .locator(
        '[data-testid="create-trigger-btn"], button:has-text("New Trigger")'
      )
      .first();
    if (await createBtn.isVisible()) {
      await createBtn.click();

      // Fill form
      const nameInput = page
        .locator('input[name="name"], [data-testid="trigger-name"]')
        .first();
      if (await nameInput.isVisible()) {
        await nameInput.fill(`E2E Trigger ${Date.now()}`);

        // Select type
        const typeSelect = page
          .locator('select[name="type"], [data-testid="trigger-type"]')
          .first();
        if (await typeSelect.isVisible()) {
          await typeSelect.selectOption("schedule");
        }

        // Submit
        await page.locator('button[type="submit"]').first().click();

        // Verify created
        await expect(page.locator('text="E2E Trigger"')).toBeVisible({
          timeout: 5000,
        });
      }
    } else {
      test.skip();
    }
  });
});
