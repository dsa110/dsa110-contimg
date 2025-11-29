// Playwright test script for Operations page (ESM module)
import { chromium } from 'playwright';

(async () => {
  console.log('Starting Playwright browser...');
  const browser = await chromium.launch({ 
    headless: true,  // Run headless since no X server
    executablePath: '/usr/bin/google-chrome',  // Use system Chrome
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });
  const page = await browser.newPage();
  
  try {
    console.log('Navigating to Operations page...');
    await page.goto('http://localhost:5173/operations', { waitUntil: 'networkidle' });
    
    console.log('Waiting for React to render...');
    // Wait for React to hydrate - look for common React/React Query indicators
    await page.waitForSelector('body', { state: 'visible' });
    await page.waitForTimeout(3000);  // Give React time to render
    
    console.log('Checking page title...');
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    // Get page content for debugging
    const bodyText = await page.textContent('body');
    console.log(`Body text length: ${bodyText?.length || 0} characters`);
    console.log(`Body preview: ${bodyText?.substring(0, 200)}...`);
    
    console.log('Taking screenshot...');
    await page.screenshot({ path: 'operations_page.png', fullPage: true });
    
    console.log('\n=== Checking UI Components ===');
    
    // Check for DLQ Stats - try multiple selectors
    console.log('Checking for DLQ Stats component...');
    try {
      // Try various selectors
      const selectors = [
        'text=/Total|Pending|Resolved|Retrying|Failed/i',
        '[data-testid*="dlq"]',
        '.MuiCard-root',
        'div:has-text("Total")',
        'div:has-text("DLQ")'
      ];
      
      let found = false;
      for (const selector of selectors) {
        try {
          const element = page.locator(selector).first();
          if (await element.isVisible({ timeout: 2000 })) {
            console.log(`:check: DLQ Stats component found (selector: ${selector})`);
            const statsText = await element.textContent();
            console.log(`  Stats preview: ${statsText?.substring(0, 150)}...`);
            found = true;
            break;
          }
        } catch (e) {
          // Try next selector
        }
      }
      if (!found) {
        console.log(':cross: DLQ Stats component not found with any selector');
      }
    } catch (e) {
      console.log(`:warning: DLQ Stats check: ${e.message}`);
    }
    
    // Check for Circuit Breaker - try multiple selectors
    console.log('Checking for Circuit Breaker component...');
    try {
      const selectors = [
        'text=/ese_detection|calibration_solve|photometry/i',
        'text=/circuit.*breaker/i',
        '[data-testid*="circuit"]',
        'div:has-text("ese_detection")'
      ];
      
      let found = false;
      for (const selector of selectors) {
        try {
          const element = page.locator(selector).first();
          if (await element.isVisible({ timeout: 2000 })) {
            console.log(`:check: Circuit Breaker component found (selector: ${selector})`);
            found = true;
            break;
          }
        } catch (e) {
          // Try next selector
        }
      }
      if (!found) {
        console.log(':cross: Circuit Breaker component not found');
      }
    } catch (e) {
      console.log(`:warning: Circuit Breaker check: ${e.message}`);
    }
    
    // Check for Navigation - try multiple selectors
    console.log('Checking for Operations navigation link...');
    try {
      const selectors = [
        'text=Operations',
        'a:has-text("Operations")',
        'button:has-text("Operations")',
        '[href="/operations"]'
      ];
      
      let found = false;
      for (const selector of selectors) {
        try {
          const element = page.locator(selector).first();
          if (await element.isVisible({ timeout: 2000 })) {
            console.log(`:check: Operations navigation link found (selector: ${selector})`);
            found = true;
            break;
          }
        } catch (e) {
          // Try next selector
        }
      }
      if (!found) {
        console.log(':cross: Operations navigation link not found');
      }
    } catch (e) {
      console.log(`:warning: Navigation check: ${e.message}`);
    }
    
    // Check for tabs
    console.log('Checking for tabs (DLQ, Circuit Breakers)...');
    try {
      const tabs = page.locator('button[role="tab"]');
      const tabCount = await tabs.count();
      console.log(`:check: Found ${tabCount} tabs`);
      for (let i = 0; i < Math.min(tabCount, 5); i++) {
        const tabText = await tabs.nth(i).textContent();
        console.log(`  Tab ${i + 1}: ${tabText}`);
      }
    } catch (e) {
      console.log(`:warning: Tabs check: ${e.message}`);
    }
    
    console.log('\n=== Checking Console Errors ===');
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.waitForTimeout(2000);
    
    if (errors.length > 0) {
      console.log(`:warning: Found ${errors.length} console errors:`);
      errors.slice(0, 5).forEach(err => console.log(`  - ${err}`));
    } else {
      console.log(':check: No console errors found');
    }
    
    console.log('\n=== Checking Network Requests ===');
    const apiRequests = [];
    page.on('request', request => {
      const url = request.url();
      if (url.includes('/api/operations') || url.includes('/api/health')) {
        apiRequests.push({
          url: url,
          method: request.method(),
          timestamp: Date.now()
        });
      }
    });
    
    // Wait for initial load and auto-refresh
    console.log('Waiting for API requests (12 seconds)...');
    await page.waitForTimeout(12000);
    
    if (apiRequests.length > 0) {
      console.log(`:check: Found ${apiRequests.length} API requests:`);
      const uniqueRequests = [...new Map(apiRequests.map(r => [r.url, r])).values()];
      uniqueRequests.forEach(req => {
        console.log(`  - ${req.method} ${req.url}`);
      });
    } else {
      console.log(':warning: No API requests detected');
    }
    
    // Check response status
    const responses = [];
    page.on('response', response => {
      const url = response.url();
      if (url.includes('/api/operations') || url.includes('/api/health')) {
        responses.push({
          url: url,
          status: response.status(),
          ok: response.ok()
        });
      }
    });
    
    await page.waitForTimeout(2000);
    
    if (responses.length > 0) {
      console.log(`\n:check: Found ${responses.length} API responses:`);
      responses.forEach(resp => {
        const status = resp.ok ? ':check:' : ':cross:';
        console.log(`  ${status} ${resp.status} ${resp.url}`);
      });
    }
    
    console.log('\n=== Test Complete ===');
    console.log('Screenshot saved as: operations_page.png');
    console.log('\nBrowser will stay open for 10 seconds for manual inspection...');
    await page.waitForTimeout(10000);
    
  } catch (error) {
    console.error('Error during testing:', error);
    await page.screenshot({ path: 'operations_page_error.png', fullPage: true });
  } finally {
    await browser.close();
  }
})();

