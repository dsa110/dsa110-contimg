#!/usr/bin/env node
/**
 * API Alignment Checker
 *
 * Validates that live API responses match expected type structures.
 * Used in CI to detect frontend/backend type drift.
 *
 * Usage:
 *   node scripts/check-api-alignment.cjs [--verbose] [--all]
 *
 * Options:
 *   --verbose  Show detailed error messages
 *   --all      Test all endpoints (not just health)
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
const TEST_ALL = process.argv.includes("--all");

// Core health endpoints (always tested)
const HEALTH_ENDPOINTS = [
  {
    name: "systemHealth",
    path: "/api/v1/health/system",
    requiredKeys: ["overall_status", "services", "summary"],
    arrayFields: ["services"],
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
  },
  {
    name: "fluxMonitoring",
    path: "/api/v1/health/flux-monitoring",
    requiredKeys: ["calibrators"],
    arrayFields: ["calibrators"],
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
  },
  {
    name: "alerts",
    path: "/api/v1/health/alerts",
    requiredKeys: ["alerts"],
    arrayFields: ["alerts"],
  },
];

// Extended endpoints (tested with --all)
const EXTENDED_ENDPOINTS = [
  // ABSURD task queue - registered at /absurd (not /api/v1/absurd)
  {
    name: "absurdHealth",
    path: "/absurd/health",
    requiredKeys: ["status"],
    arrayFields: [],
  },
  {
    name: "absurdQueues",
    path: "/absurd/queues",
    requiredKeys: [], // Returns array
    isArray: true,
  },
  {
    name: "absurdWorkers",
    path: "/absurd/workers",
    requiredKeys: ["workers", "total"],
    arrayFields: ["workers"],
  },
  // Calibrator imaging
  {
    name: "calibrators",
    path: "/api/v1/calibrator-imaging/calibrators",
    requiredKeys: [], // Returns array
    isArray: true,
  },
  {
    name: "calibratorImagingHealth",
    path: "/api/v1/calibrator-imaging/health",
    requiredKeys: ["status"],
    arrayFields: [],
  },
  // Core data endpoints
  {
    name: "images",
    path: "/api/v1/images",
    requiredKeys: [], // Returns array
    isArray: true,
  },
  {
    name: "sources",
    path: "/api/v1/sources",
    requiredKeys: [], // Returns array
    isArray: true,
  },
  {
    name: "jobs",
    path: "/api/v1/jobs",
    requiredKeys: [], // Returns array
    isArray: true,
  },
  // Interactive imaging
  {
    name: "imagingSessions",
    path: "/api/v1/imaging/sessions",
    requiredKeys: ["sessions", "total"],
    arrayFields: ["sessions"],
  },
  {
    name: "imagingDefaults",
    path: "/api/v1/imaging/defaults",
    requiredKeys: ["imsize", "cell", "niter"],
    arrayFields: ["imsize"],
  },
];

const ENDPOINTS = TEST_ALL
  ? [...HEALTH_ENDPOINTS, ...EXTENDED_ENDPOINTS]
  : HEALTH_ENDPOINTS;

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
  const arrayFields = endpoint.arrayFields || [];

  // Handle endpoints that return arrays directly
  if (endpoint.isArray) {
    if (!Array.isArray(data)) {
      issues.push(`Expected array response, got ${typeof data}`);
    }
    return issues;
  }

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
  for (const field of arrayFields) {
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
  if ("total" in data && typeof data.total !== "number") {
    issues.push(`"total" should be number`);
  }
  if ("status" in data && typeof data.status !== "string") {
    issues.push(`"status" should be string`);
  }

  return issues;
}

async function main() {
  console.log("🔍 API Alignment Check");
  console.log(`   Backend: ${API_BASE}`);
  console.log(`   Mode: ${TEST_ALL ? "all endpoints" : "health only"}`);
  console.log(`   Endpoints: ${ENDPOINTS.length}\n`);

  let allPassed = true;
  let passCount = 0;
  let failCount = 0;
  const results = [];

  for (const endpoint of ENDPOINTS) {
    process.stdout.write(`  ${endpoint.name}... `);

    try {
      const data = await fetchEndpoint(endpoint.path);
      const issues = validateEndpoint(data, endpoint);

      if (issues.length === 0) {
        console.log("✅");
        results.push({ name: endpoint.name, status: "pass" });
        passCount++;
      } else {
        console.log("❌");
        allPassed = false;
        failCount++;
        results.push({ name: endpoint.name, status: "fail", issues });
        if (VERBOSE) {
          issues.forEach((issue) => console.log(`     - ${issue}`));
        }
      }
    } catch (error) {
      console.log(`❌ ${error.message}`);
      allPassed = false;
      failCount++;
      results.push({
        name: endpoint.name,
        status: "error",
        issues: [error.message],
      });
    }
  }

  console.log(
    `\n${passCount}/${ENDPOINTS.length} passed${
      failCount > 0 ? `, ${failCount} failed` : ""
    }`
  );
  console.log(
    `${allPassed ? "✅ All endpoints aligned" : "❌ Alignment issues detected"}`
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
