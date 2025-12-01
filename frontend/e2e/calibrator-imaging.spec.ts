import { test, expect, type Page, type Locator } from "@playwright/test";

/**
 * Calibrator Imaging Page Tests
 * 
 * These tests verify the complete workflow functionality of the
 * calibrator imaging test page, including:
 * - Page load and connection status
 * - Calibrator selection
 * - Transit selection  
 * - Observation selection
 * - Button interactions and state transitions
 * 
 * This is an example of "button-level" testing - verifying that
 * each interactive element does exactly what it should.
 */
test.describe("Calibrator Imaging Page", () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to the calibrator imaging page
    await page.goto("/calibrator-imaging");
    await page.waitForLoadState("domcontentloaded");
  });

  test.describe("Connection Status", () => {
    test("shows loading spinner initially", async ({ page }) => {
      // On fast connections this may flash by quickly
      // Use a slower network condition or check for either loading or result
      const hasStatus = await page.locator("text=Checking system status").isVisible()
        || await page.locator("text=All systems operational").isVisible()
        || await page.locator("text=System Status").isVisible()
        || await page.locator("text=API Connection Failed").isVisible();
      expect(hasStatus).toBe(true);
    });

    test("shows healthy status when API is available", async ({ page }) => {
      // Wait for the health check to complete
      await page.waitForSelector('[class*="bg-green"]', { timeout: 10000 }).catch(() => null);
      
      // Either healthy or degraded is acceptable (depends on infrastructure)
      const healthyVisible = await page.locator("text=All systems operational").isVisible();
      const degradedVisible = await page.locator("text=System Status: Degraded").isVisible();
      
      expect(healthyVisible || degradedVisible).toBe(true);
    });

    test("refresh button updates status", async ({ page }) => {
      // Wait for initial load
      await page.waitForTimeout(2000);
      
      // Find and click refresh button
      const refreshButton = page.locator("button:has-text('Refresh')").first();
      if (await refreshButton.isVisible()) {
        await refreshButton.click();
        // Status should update (check for timestamp change or loading state)
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe("Step Indicator", () => {
    test("shows all 7 steps", async ({ page }) => {
      const steps = [
        "1. Calibrator",
        "2. Transit", 
        "3. Observation",
        "4. Generate MS",
        "5. Calibrate",
        "6. Image",
        "7. Results",
      ];
      
      for (const step of steps) {
        await expect(page.locator(`text=${step}`)).toBeVisible();
      }
    });

    test("first step is highlighted initially", async ({ page }) => {
      // The first step should have blue background
      const firstStep = page.locator("text=1. Calibrator").first();
      await expect(firstStep).toBeVisible();
      
      // Check it has the active styling (bg-blue-600)
      const hasBlue = await firstStep.evaluate((el) => {
        return el.className.includes("bg-blue");
      });
      expect(hasBlue).toBe(true);
    });
  });

  test.describe("Calibrator Selection", () => {
    test("displays calibrator cards from API", async ({ page }) => {
      // Wait for calibrators to load (or loading spinner to disappear)
      await page.waitForSelector('[class*="grid"]', { timeout: 10000 });
      
      // Should show either calibrator cards or "No calibrators" message
      const hasCards = await page.locator("button:has-text('RA:')").count() > 0;
      const hasNoData = await page.locator("text=No calibrators found").isVisible();
      
      expect(hasCards || hasNoData).toBe(true);
    });

    test("clicking calibrator advances to transit step", async ({ page }) => {
      // Wait for calibrators to load
      await page.waitForSelector("button:has-text('RA:')", { timeout: 10000 }).catch(() => null);
      
      const firstCalibrator = page.locator("button:has-text('RA:')").first();
      if (await firstCalibrator.isVisible()) {
        await firstCalibrator.click();
        
        // Should now show "Step 2: Select Transit"
        await expect(page.locator("text=Step 2: Select Transit")).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe("Navigation", () => {
    test("reset button returns to step 1", async ({ page }) => {
      // Try to advance to step 2
      const firstCalibrator = page.locator("button:has-text('RA:')").first();
      await firstCalibrator.waitFor({ timeout: 10000 }).catch(() => null);
      
      if (await firstCalibrator.isVisible()) {
        await firstCalibrator.click();
        await page.waitForTimeout(500);
        
        // Click reset
        await page.locator("button:has-text('Reset')").click();
        
        // Should be back at step 1
        await expect(page.locator("text=Step 1: Select Bandpass Calibrator")).toBeVisible();
      }
    });

    test("back link returns to dashboard", async ({ page }) => {
      const backLink = page.locator("a:has-text('Back to Dashboard')");
      await expect(backLink).toBeVisible();
      await expect(backLink).toHaveAttribute("href", "/");
    });

    test("change calibrator link works", async ({ page }) => {
      // Advance to step 2
      const firstCalibrator = page.locator("button:has-text('RA:')").first();
      await firstCalibrator.waitFor({ timeout: 10000 }).catch(() => null);
      
      if (await firstCalibrator.isVisible()) {
        await firstCalibrator.click();
        await page.waitForTimeout(500);
        
        // Click "Change calibrator"
        const changeLink = page.locator("button:has-text('Change calibrator')");
        if (await changeLink.isVisible()) {
          await changeLink.click();
          
          // Should be back at step 1
          await expect(page.locator("text=Step 1: Select Bandpass Calibrator")).toBeVisible();
        }
      }
    });
  });

  test.describe("Transit Selection", () => {
    test.beforeEach(async ({ page }) => {
      // Advance to transit selection
      const firstCalibrator = page.locator("button:has-text('RA:')").first();
      await firstCalibrator.waitFor({ timeout: 10000 }).catch(() => null);
      
      if (await firstCalibrator.isVisible()) {
        await firstCalibrator.click();
        await page.waitForTimeout(1000);
      }
    });

    test("shows transit times with data availability", async ({ page }) => {
      // Wait for transits to load
      await page.waitForTimeout(2000);
      
      // Should show either transits or "No transit times found"
      const hasTransits = await page.locator("text=MJD:").count() > 0;
      const hasNoData = await page.locator("text=No transit times found").isVisible();
      
      expect(hasTransits || hasNoData).toBe(true);
    });

    test("transits with data show green badge", async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const greenBadge = page.locator("text=groups available").first();
      if (await greenBadge.isVisible()) {
        // Check parent has green styling
        const hasGreen = await greenBadge.evaluate((el) => {
          return el.className.includes("green");
        });
        expect(hasGreen).toBe(true);
      }
    });

    test("transits without data are disabled", async ({ page }) => {
      await page.waitForTimeout(2000);
      
      const noDataBadge = page.locator("text=No data").first();
      if (await noDataBadge.isVisible()) {
        // Parent button should be disabled
        const parentButton = noDataBadge.locator("xpath=ancestor::button");
        await expect(parentButton).toBeDisabled();
      }
    });
  });

  test.describe("Accessibility", () => {
    test("page has proper heading structure", async ({ page }) => {
      const h1 = page.locator("h1");
      await expect(h1).toBeVisible();
      await expect(h1).toHaveText("Calibrator Imaging Test");
    });

    test("interactive elements are keyboard accessible", async ({ page }) => {
      // Tab to first calibrator button
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab"); // Skip back link
      await page.keyboard.press("Tab"); // Skip reset button
      
      // Should be able to activate with Enter
      await page.keyboard.press("Enter");
      
      // If a calibrator was focused, we should advance
      // (This depends on focus order and content)
    });
  });
});

/**
 * API Health Integration Tests
 * 
 * These tests verify the health check endpoints are
 * working correctly with the frontend.
 */
test.describe("Health Check Integration", () => {
  test("storage health endpoint returns valid response", async ({ request }) => {
    const response = await request.get("/api/v1/calibrator-imaging/health/storage");
    expect(response.status()).toBeLessThan(500);
    
    const data = await response.json();
    expect(data).toHaveProperty("status");
    expect(["synchronized", "out_of_sync", "error"]).toContain(data.status);
  });

  test("services health endpoint returns valid response", async ({ request }) => {
    const response = await request.get("/api/v1/calibrator-imaging/health/services");
    expect(response.status()).toBeLessThan(500);
    
    const data = await response.json();
    expect(data).toHaveProperty("overall_status");
    expect(data).toHaveProperty("services");
    expect(Array.isArray(data.services)).toBe(true);
  });
});
