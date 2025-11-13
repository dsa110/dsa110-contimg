// Playwright test script for Operations page
const { chromium } = require('playwright');

(async () => {
  console.log('Starting Playwright browser...');
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    console.log('Navigating to Operations page...');
    await page.goto('http://localhost:5173/operations', { waitUntil: 'networkidle' });
    
    console.log('Page loaded. Taking screenshot...');
    await page.screenshot({ path: 'operations_page.png', fullPage: true });
    
    console.log('Checking page title...');
    const title = await page.title();
    console.log(`Page title: ${title}`);
    
    console.log('Checking for DLQ Stats component...');
    const dlqStats = await page.locator('text=Total').first();
    if (await dlqStats.isVisible()) {
      console.log('✓ DLQ Stats component found');
      const statsText = await dlqStats.textContent();
      console.log(`  Stats text: ${statsText}`);
    } else {
      console.log('✗ DLQ Stats component not found');
    }
    
    console.log('Checking for Circuit Breaker component...');
    const circuitBreaker = await page.locator('text=ese_detection').first();
    if (await circuitBreaker.isVisible()) {
      console.log('✓ Circuit Breaker component found');
    } else {
      console.log('✗ Circuit Breaker component not found');
    }
    
    console.log('Checking for navigation link...');
    const navLink = await page.locator('text=Operations').first();
    if (await navLink.isVisible()) {
      console.log('✓ Operations navigation link found');
    } else {
      console.log('✗ Operations navigation link not found');
    }
    
    console.log('Checking console for errors...');
    const errors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    // Wait a bit for any errors to appear
    await page.waitForTimeout(2000);
    
    if (errors.length > 0) {
      console.log(`⚠ Found ${errors.length} console errors:`);
      errors.forEach(err => console.log(`  - ${err}`));
    } else {
      console.log('✓ No console errors found');
    }
    
    console.log('Checking network requests...');
    const requests = [];
    page.on('request', request => {
      if (request.url().includes('/api/operations') || request.url().includes('/api/health')) {
        requests.push({
          url: request.url(),
          method: request.method()
        });
      }
    });
    
    // Wait for auto-refresh to trigger
    await page.waitForTimeout(12000);
    
    console.log(`✓ Found ${requests.length} API requests:`);
    requests.forEach(req => {
      console.log(`  - ${req.method} ${req.url}`);
    });
    
    console.log('\n✓ Operations page test complete!');
    console.log('Screenshot saved as: operations_page.png');
    
  } catch (error) {
    console.error('Error during testing:', error);
  } finally {
    await browser.close();
  }
})();

