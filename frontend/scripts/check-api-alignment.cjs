#!/usr/bin/env node
/**
 * API Alignment Checker
 *
 * Validates that live API responses match expected type structures.
 * Used in CI to detect frontend/backend type drift.
 *
 * Usage:
 *   node scripts/check-api-alignment.cjs [--verbose]
 *
 * Exit codes:
 *   0 - All endpoints valid
 *   1 - One or more endpoints have structural issues
 *
 * Environment:
 *   API_BASE_URL - Backend URL (default: http://localhost:8000)
 */

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";
const VERBOSE = process.argv.includes("--verbose");

// Endpoint definitions with expected structure
const ENDPOINTS = [
  {
    name: "systemHealth",
    path: "/api/v1/health/system",
    requiredKeys: ["overall_status", "services", "summary"],
    arrayFields: ["services"],
    nestedArrayFields: {},
  },
  {
    name: "validityTimeline",
    path: "/api/v1/health/validity-windows/timeline",
    requiredKeys: [
      "timeline_start",
      "timeline_end",
      "current_time",
      "current_mjd",
      "windows",
      "total_windows",
    ],
    arrayFields: ["windows"],
    nestedArrayFields: {},
  },
  {
    name: "fluxMonitoring",
    path: "/api/v1/health/flux-monitoring",
    requiredKeys: ["calibrators"],
    arrayFields: ["calibrators"],
    nestedArrayFields: {},
  },
  {
    name: "pointingStatus",
    path: "/api/v1/health/pointing",
    requiredKeys: [
      "current_lst",
      "current_lst_deg",
      "upcoming_transits",
      "timestamp",
    ],
    arrayFields: ["upcoming_transits"],
    nestedArrayFields: {},
  },
  {
    name: "alerts",
    path: "/api/v1/health/alerts",
    requiredKeys: ["alerts"],
    arrayFields: ["alerts"],
    nestedArrayFields: {},
  },
];

async function fetchEndpoint(path) {
  const url = `${API_BASE}${path}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

function validateEndpoint(data, endpoint) {
  const issues = [];

  if (typeof data !== "object" || data === null) {
    issues.push(`Expected object, got ${typeof data}`);
    return issues;
  }

  // Check required keys
  for (const key of endpoint.requiredKeys) {
    if (!(key in data)) {
      issues.push(`Missing required key: "${key}"`);
    }
  }

  // Check array fields are actually arrays
  for (const field of endpoint.arrayFields) {
    if (field in data && !Array.isArray(data[field])) {
      issues.push(`"${field}" should be array, got ${typeof data[field]}`);
    }
  }

  // Type checks for common patterns
  if ("overall_status" in data && typeof data.overall_status !== "string") {
    issues.push(`"overall_status" should be string`);
  }
  if ("current_mjd" in data && typeof data.current_mjd !== "number") {
    issues.push(`"current_mjd" should be number`);
  }
  if ("total_windows" in data && typeof data.total_windows !== "number") {
    issues.push(`"total_windows" should be number`);
  }

  return issues;
}

async function main() {
  console.log("🔍 API Alignment Check");
  console.log(`   Backend: ${API_BASE}\n`);

  let allPassed = true;
  const results = [];

  for (const endpoint of ENDPOINTS) {
    process.stdout.write(`  ${endpoint.name}... `);

    try {
      const data = await fetchEndpoint(endpoint.path);
      const issues = validateEndpoint(data, endpoint);

      if (issues.length === 0) {
        console.log("✅");
        results.push({ name: endpoint.name, status: "pass" });
      } else {
        console.log("❌");
        allPassed = false;
        results.push({ name: endpoint.name, status: "fail", issues });
        if (VERBOSE) {
          issues.forEach((issue) => console.log(`     - ${issue}`));
        }
      }
    } catch (error) {
      console.log(`❌ ${error.message}`);
      allPassed = false;
      results.push({
        name: endpoint.name,
        status: "error",
        issues: [error.message],
      });
    }
  }

  console.log(
    `\n${allPassed ? "✅ All endpoints aligned" : "❌ Alignment issues detected"}`
  );

  if (!allPassed && !VERBOSE) {
    console.log("   Run with --verbose for details");
  }

  // Output JSON summary for CI parsing
  if (process.env.CI) {
    console.log("\n--- JSON Summary ---");
    console.log(JSON.stringify({ passed: allPassed, results }, null, 2));
  }

  process.exit(allPassed ? 0 : 1);
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
