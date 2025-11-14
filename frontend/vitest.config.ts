import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { webcrypto } from "node:crypto";
import { execSync } from "child_process";
import { existsSync } from "fs";

// CRITICAL: Enforce casa6 Node.js v22.6.0 requirement
// This check runs before Vitest loads, preventing crypto errors
// NOTE: In CI/CD (GitHub Actions), this check is skipped as CI uses Node 22 directly
const CASA6_NODE = "/opt/miniforge/envs/casa6/bin/node";
const REQUIRED_VERSION = "22.0.0";
const IS_CI = process.env.CI === "true" || process.env.GITHUB_ACTIONS === "true";

function checkCasa6Node(): void {
  // Skip check in CI - CI uses Node 22 directly
  if (IS_CI) {
    const currentVersion = execSync("node --version", { encoding: "utf-8" })
      .trim()
      .replace("v", "");
    const versionParts = currentVersion.split(".").map(Number);
    const requiredParts = REQUIRED_VERSION.split(".").map(Number);

    if (
      versionParts[0] < requiredParts[0] ||
      (versionParts[0] === requiredParts[0] && versionParts[1] < requiredParts[1])
    ) {
      console.error("\n❌ ERROR: Node.js version too old in CI");
      console.error(`   Current: v${currentVersion}`);
      console.error(`   Required: v${REQUIRED_VERSION}+`);
      process.exit(1);
    }
    return; // CI check passed
  }

  // Local development check - require casa6 Node.js
  try {
    const currentNode = execSync("which node", { encoding: "utf-8" }).trim();
    const currentVersion = execSync("node --version", { encoding: "utf-8" })
      .trim()
      .replace("v", "");

    if (currentNode !== CASA6_NODE) {
      console.error("\n❌ ERROR: Frontend tests require casa6 Node.js v22.6.0");
      console.error(`   Current: ${currentNode} (v${currentVersion})`);
      console.error(`   Required: ${CASA6_NODE} (v22.6.0)`);
      console.error(
        "\n   Fix: source /opt/miniforge/etc/profile.d/conda.sh && conda activate casa6\n"
      );
      process.exit(1);
    }

    // Check version meets minimum
    const versionParts = currentVersion.split(".").map(Number);
    const requiredParts = REQUIRED_VERSION.split(".").map(Number);

    if (
      versionParts[0] < requiredParts[0] ||
      (versionParts[0] === requiredParts[0] && versionParts[1] < requiredParts[1])
    ) {
      console.error("\n❌ ERROR: Node.js version too old");
      console.error(`   Current: v${currentVersion}`);
      console.error(`   Required: v${REQUIRED_VERSION}+`);
      console.error("\n   Fix: Use casa6 Node.js v22.6.0\n");
      process.exit(1);
    }
  } catch (error) {
    console.error("\n❌ ERROR: Failed to check Node.js version");
    console.error("   Fix: Ensure casa6 is activated\n");
    process.exit(1);
  }
}

// Run check before Vitest loads (cannot be bypassed)
checkCasa6Node();

// Ensure Web Crypto API exists early for Vite/Vitest startup
// Node 16+ requires explicit setup for crypto.getRandomValues
if (typeof globalThis.crypto === "undefined") {
  (globalThis as any).crypto = webcrypto as any;
}

// Ensure getRandomValues is available (required by Vite/Vitest)
if (globalThis.crypto && !globalThis.crypto.getRandomValues) {
  (globalThis.crypto as any).getRandomValues = webcrypto.getRandomValues.bind(webcrypto);
}

// https://vite.dev/config/
const API_PROXY_TARGET = process.env.API_PROXY_TARGET || "http://localhost:8010";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    // Use node environment for backend API/client smoke tests to avoid jsdom/webcrypto issues
    environmentMatchGlobs: [["src/api/**", "node"]],
    setupFiles: "./src/test/setup.ts",
  },
});
