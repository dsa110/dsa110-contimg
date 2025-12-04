#!/usr/bin/env node
/**
 * Headless Pipeline Status test using Puppeteer
 * Runs against the local dev server at http://127.0.0.1:3000
 */
import puppeteer from "puppeteer";

const BASE_URL = process.env.BASE_URL || "http://127.0.0.1:3000";

async function testPipelineStatus() {
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
    if (
      text.includes("[AUTH_STORE]") ||
      text.includes("[LOGIN_PAGE]") ||
      text.includes("Pipeline")
    ) {
      console.log(`📄 PAGE: ${text}`);
    }
  });

  try {
    // --- LOGIN STEP ---
    console.log(`🌐 Navigating to ${BASE_URL}/login`);
    await page.goto(`${BASE_URL}/login`, {
      waitUntil: "networkidle2",
      timeout: 30000,
    });

    console.log("⌨️  Filling in credentials (admin/admin)...");
    await page.type("#username", "admin");
    await page.type("#password", "admin");

    console.log("🖱️  Clicking Sign In button...");
    await Promise.all([
      page.click('button[type="submit"]'),
      page
        .waitForNavigation({ waitUntil: "networkidle2", timeout: 10000 })
        .catch(() => {}),
    ]);

    await new Promise((r) => setTimeout(r, 2000));
    const url = page.url();
    console.log(`📍 Current URL: ${url}`);

    if (url.includes("/login")) {
      throw new Error("Login failed, still on login page");
    }

    // --- PIPELINE STATUS CHECK ---
    console.log("🔍 Looking for Pipeline Status Panel...");

    // Wait for the panel header
    await page.waitForSelector("h3", { timeout: 5000 });

    // Evaluate page content to find status
    const statusInfo = await page.evaluate(() => {
      const headers = Array.from(document.querySelectorAll("h3"));
      const panelHeader = headers.find((h) =>
        h.textContent.includes("Pipeline Status")
      );

      if (!panelHeader) return { found: false };

      // Navigate up to the card container
      const card = panelHeader.closest(".card");
      if (!card) return { found: true, cardFound: false };

      const textContent = card.textContent;
      const isHealthy = textContent.includes("Healthy");
      const isDegraded = textContent.includes("Degraded");
      const workerMatch = textContent.match(/(\d+) workers?/);

      return {
        found: true,
        cardFound: true,
        textContent: textContent.substring(0, 200) + "...", // Log start of content
        isHealthy,
        isDegraded,
        workerCount: workerMatch ? parseInt(workerMatch[1]) : null,
      };
    });

    console.log("📊 Status Panel Info:", JSON.stringify(statusInfo, null, 2));

    if (!statusInfo.found) {
      console.error("❌ FAIL: Pipeline Status header not found");
    } else if (!statusInfo.cardFound) {
      console.error("❌ FAIL: Pipeline Status card container not found");
    } else {
      if (statusInfo.isHealthy) {
        console.log('✅ SUCCESS: Pipeline Status is "Healthy"');
      } else if (statusInfo.isDegraded) {
        console.log('⚠️  WARNING: Pipeline Status is "Degraded"');
      } else {
        console.log(
          "❌ FAIL: Pipeline Status is neither Healthy nor Degraded (or loading failed)"
        );
      }

      if (statusInfo.workerCount !== null) {
        console.log(`✅ Worker Count: ${statusInfo.workerCount}`);
      } else {
        console.log("⚠️  Worker count not found in text");
      }
    }
  } catch (err) {
    console.error("❌ Error during test:", err);
    // Take a screenshot on error
    try {
      await page.screenshot({ path: "error-screenshot.png" });
      console.log("📸 Screenshot saved to error-screenshot.png");
    } catch (e) {}
  } finally {
    await browser.close();
    console.log("🏁 Test complete.");
  }
}

testPipelineStatus();
