#!/usr/bin/env node
/**
 * Headless login test using Puppeteer
 * Runs against the local dev server at http://127.0.0.1:3000
 */
import puppeteer from "puppeteer";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:3000";

async function testLogin() {
  console.log("🔧 Launching browser...");
  const browser = await puppeteer.launch({
    headless: "new",
    executablePath: "/usr/bin/google-chrome",
    args: [
      "--no-sandbox",
      "--disable-setuid-sandbox",
      "--disable-dev-shm-usage",
    ],
  });

  const page = await browser.newPage();

  // Capture console logs from the page
  page.on("console", (msg) => {
    const text = msg.text();
    if (text.includes("[AUTH_STORE]") || text.includes("[LOGIN_PAGE]")) {
      console.log(`📄 PAGE: ${text}`);
    }
  });

  try {
    console.log(`🌐 Navigating to ${BASE_URL}/login`);
    await page.goto(`${BASE_URL}/login`, {
      waitUntil: "networkidle2",
      timeout: 30000,
    });

    const url1 = page.url();
    console.log(`📍 Current URL: ${url1}`);

    // Fill in the login form
    console.log("⌨️  Filling in credentials (admin/admin)...");
    await page.type("#username", "admin");
    await page.type("#password", "admin");

    // Submit the form
    console.log("🖱️  Clicking Sign In button...");
    await Promise.all([
      page.click('button[type="submit"]'),
      // Wait for either navigation or some reasonable time
      page
        .waitForNavigation({ waitUntil: "networkidle2", timeout: 10000 })
        .catch(() => {}),
    ]);

    // Give a moment for any async state updates
    await new Promise((r) => setTimeout(r, 2000));

    const url2 = page.url();
    console.log(`📍 Final URL: ${url2}`);

    // Check localStorage for auth state
    const authState = await page.evaluate(() => {
      const stored = localStorage.getItem("dsa110-auth");
      if (!stored) return null;
      try {
        return JSON.parse(stored);
      } catch {
        return stored;
      }
    });

    console.log(
      "🔐 Auth state in localStorage:",
      JSON.stringify(authState, null, 2)
    );

    // Determine success
    if (url2 !== `${BASE_URL}/login` && url2 !== `${BASE_URL}/login/`) {
      console.log("✅ SUCCESS: Redirected away from login page!");
    } else if (authState?.state?.isAuthenticated) {
      console.log("⚠️  Auth state shows authenticated but URL is still /login");
      console.log("   This may indicate a routing or useEffect issue.");
    } else {
      console.log("❌ FAIL: Still on login page and not authenticated");
    }
  } catch (err) {
    console.error("❌ Error during test:", err);
  } finally {
    await browser.close();
    console.log("🏁 Test complete.");
  }
}

testLogin();
