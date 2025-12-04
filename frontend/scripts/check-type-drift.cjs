#!/usr/bin/env node
/**
 * Pre-commit API Type Drift Check
 *
 * This script checks if the OpenAPI-generated types have drifted from the
 * saved schema. Run this before commits to catch type mismatches early.
 *
 * Usage:
 *   node scripts/check-type-drift.cjs           # Check for drift
 *   node scripts/check-type-drift.cjs --fix     # Check and regenerate if needed
 *
 * Exit codes:
 *   0 - No drift detected (or fixed with --fix)
 *   1 - Drift detected (requires manual sync)
 *   2 - Error during check
 */

const { execSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const GENERATED_FILE = path.join(
  __dirname,
  "..",
  "src",
  "api",
  "generated",
  "api.d.ts"
);
const SCHEMA_FILE = path.join(__dirname, "..", "src", "api", "openapi.json");
const FIX_MODE = process.argv.includes("--fix");
const VERBOSE = process.argv.includes("--verbose");

function log(msg) {
  console.log(`[type-drift] ${msg}`);
}

function error(msg) {
  console.error(`[type-drift] ERROR: ${msg}`);
}

function checkFileExists(filePath, name) {
  if (!fs.existsSync(filePath)) {
    error(`${name} not found: ${filePath}`);
    return false;
  }
  return true;
}

async function main() {
  log("Checking for API type drift...");

  // Check required files exist
  if (!checkFileExists(GENERATED_FILE, "Generated types")) {
    log("Run 'npm run openapi:sync' to generate types first");
    process.exit(2);
  }

  if (!checkFileExists(SCHEMA_FILE, "OpenAPI schema")) {
    log("Run 'npm run openapi:fetch' to fetch schema first");
    process.exit(2);
  }

  // Save current generated file content
  const currentContent = fs.readFileSync(GENERATED_FILE, "utf-8");
  const tempFile = GENERATED_FILE + ".backup";
  fs.writeFileSync(tempFile, currentContent);

  try {
    // Regenerate from schema
    log("Regenerating types from saved schema...");
    execSync("npm run openapi:generate:file", {
      stdio: VERBOSE ? "inherit" : "pipe",
      cwd: path.join(__dirname, ".."),
    });

    // Compare
    const newContent = fs.readFileSync(GENERATED_FILE, "utf-8");

    if (currentContent === newContent) {
      log("✓ No type drift detected - types are up-to-date");
      // Restore original (no changes needed)
      fs.writeFileSync(GENERATED_FILE, currentContent);
      process.exit(0);
    } else {
      // Drift detected
      const diffLines = getDiffSummary(currentContent, newContent);

      if (FIX_MODE) {
        log(
          `⚠ Type drift detected (${diffLines} lines changed) - regenerated types`
        );
        log("Types have been updated. Please review and commit the changes.");
        process.exit(0);
      } else {
        // Restore original content
        fs.writeFileSync(GENERATED_FILE, currentContent);
        error(`Type drift detected (${diffLines} lines changed)`);
        log("Run 'npm run openapi:sync' to update types");
        log("Or run 'npm run precommit:api-fix' to auto-fix");
        process.exit(1);
      }
    }
  } catch (err) {
    // Restore original content on error
    if (fs.existsSync(tempFile)) {
      fs.writeFileSync(GENERATED_FILE, fs.readFileSync(tempFile, "utf-8"));
    }
    error(`Failed to check type drift: ${err.message}`);
    process.exit(2);
  } finally {
    // Cleanup temp file
    if (fs.existsSync(tempFile)) {
      fs.unlinkSync(tempFile);
    }
  }
}

function getDiffSummary(oldContent, newContent) {
  const oldLines = oldContent.split("\n");
  const newLines = newContent.split("\n");

  let changes = 0;
  const maxLen = Math.max(oldLines.length, newLines.length);

  for (let i = 0; i < maxLen; i++) {
    if (oldLines[i] !== newLines[i]) {
      changes++;
    }
  }

  return changes;
}

main().catch((err) => {
  error(`Unexpected error: ${err.message}`);
  process.exit(2);
});
