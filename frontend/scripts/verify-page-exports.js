#!/usr/bin/env node
/**
 * Verify that all page components have default exports
 * This prevents "Cannot convert object to primitive value" errors with React.lazy()
 *
 * Usage: node scripts/verify-page-exports.js
 */

import { readdir, readFile } from "fs/promises";
import { join, extname } from "path";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const pagesDir = join(__dirname, "../src/pages");

async function checkPageExports() {
  const errors = [];
  const files = await readdir(pagesDir, { recursive: true });
  const pageFiles = files.filter(
    (file) =>
      (extname(file) === ".tsx" || extname(file) === ".ts") &&
      !file.includes(".test.") &&
      !file.includes(".spec.") &&
      !file.endsWith(".test.tsx") &&
      !file.endsWith(".test.ts") &&
      !file.endsWith(".spec.tsx") &&
      !file.endsWith(".spec.ts")
  );

  for (const file of pageFiles) {
    const filePath = join(pagesDir, file);
    const content = await readFile(filePath, "utf-8");

    // Check if file has default export
    const hasDefaultExport =
      /export\s+default\s+(function|const|class|)/.test(content) ||
      /export\s+{\s*default\s*}/.test(content);

    if (!hasDefaultExport) {
      // Check if it's a page component (not a utility file)
      const isPageComponent = /^[A-Z]/.test(file.replace(/\.(tsx|ts)$/, ""));

      if (isPageComponent) {
        errors.push({
          file,
          message: `Missing default export. Page components must use default exports for React.lazy()`,
        });
      }
    }
  }

  if (errors.length > 0) {
    console.error("❌ Page export verification failed:\n");
    errors.forEach(({ file, message }) => {
      console.error(`  ${file}: ${message}`);
    });
    console.error(
      "\n💡 Fix: Change 'export function ComponentName()' to 'export default function ComponentName()'"
    );
    process.exit(1);
  }

  console.log(`✅ All ${pageFiles.length} page components have default exports`);
}

checkPageExports().catch((error) => {
  console.error("Error checking page exports:", error);
  process.exit(1);
});
