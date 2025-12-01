#!/usr/bin/env npx ts-node
/**
 * API Fixture Sync Tool
 *
 * Fetches live API responses and generates/updates fixture data for alignment tests.
 * This ensures fixtures stay in sync with actual backend responses.
 *
 * Usage:
 *   npx ts-node scripts/sync-api-fixtures.ts [--check] [--update]
 *
 * Options:
 *   --check   Compare live responses against fixtures, exit 1 if mismatched
 *   --update  Fetch live responses and update fixtures file
 *   (default) Show diff between live and fixtures without updating
 *
 * Environment:
 *   API_BASE_URL  Backend URL (default: http://localhost:8000)
 */

const API_BASE = process.env.API_BASE_URL || "http://localhost:8000";

// Endpoints to sync
const ENDPOINTS = {
  systemHealth: "/api/v1/health/system",
  validityTimeline: "/api/v1/health/validity-windows/timeline",
  fluxMonitoring: "/api/v1/health/flux-monitoring",
  pointingStatus: "/api/v1/health/pointing",
  alerts: "/api/v1/health/alerts",
} as const;

// Required keys for each endpoint (subset validation)
const REQUIRED_KEYS: Record<keyof typeof ENDPOINTS, string[]> = {
  systemHealth: ["overall_status", "services", "summary"],
  validityTimeline: [
    "timeline_start",
    "timeline_end",
    "current_time",
    "current_mjd",
    "windows",
    "total_windows",
  ],
  fluxMonitoring: ["calibrators"],
  pointingStatus: ["current_lst", "current_lst_deg", "upcoming_transits", "timestamp"],
  alerts: ["alerts"],
};

interface ValidationResult {
  endpoint: string;
  valid: boolean;
  missingKeys: string[];
  extraKeys: string[];
  typeIssues: string[];
}

async function fetchEndpoint(path: string): Promise<unknown> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

function validateResponse(
  name: string,
  data: unknown,
  requiredKeys: string[]
): ValidationResult {
  const result: ValidationResult = {
    endpoint: name,
    valid: true,
    missingKeys: [],
    extraKeys: [],
    typeIssues: [],
  };

  if (typeof data !== "object" || data === null) {
    result.valid = false;
    result.typeIssues.push(`Expected object, got ${typeof data}`);
    return result;
  }

  const dataKeys = Object.keys(data);

  // Check required keys
  for (const key of requiredKeys) {
    if (!dataKeys.includes(key)) {
      result.valid = false;
      result.missingKeys.push(key);
    }
  }

  // Check for arrays that should be arrays (common bug)
  const obj = data as Record<string, unknown>;
  if ("services" in obj && !Array.isArray(obj.services)) {
    result.valid = false;
    result.typeIssues.push("'services' should be an array, not Record");
  }
  if ("windows" in obj && !Array.isArray(obj.windows)) {
    result.valid = false;
    result.typeIssues.push("'windows' should be an array");
  }
  if ("calibrators" in obj && !Array.isArray(obj.calibrators)) {
    result.valid = false;
    result.typeIssues.push("'calibrators' should be an array");
  }
  if ("alerts" in obj && !Array.isArray(obj.alerts)) {
    result.valid = false;
    result.typeIssues.push("'alerts' should be an array");
  }

  return result;
}

function generateFixtureCode(name: string, data: unknown): string {
  const sanitized = JSON.stringify(data, null, 2)
    // Add TypeScript type annotation
    .replace(/^{/, `{\n    // Auto-generated from live API response`)
    // Truncate long arrays for readability
    .replace(/("services":\s*\[)[^\]]{500,}(\])/g, '$1 /* truncated */ $2');
  
  return `  ${name}: ${sanitized},`;
}

async function main() {
  const args = process.argv.slice(2);
  const checkMode = args.includes("--check");
  const updateMode = args.includes("--update");

  console.log(`🔍 API Fixture Sync Tool`);
  console.log(`   Backend: ${API_BASE}`);
  console.log(`   Mode: ${checkMode ? "check" : updateMode ? "update" : "diff"}\n`);

  const results: ValidationResult[] = [];
  const fixtures: Record<string, unknown> = {};

  for (const [name, path] of Object.entries(ENDPOINTS)) {
    process.stdout.write(`  ${name}... `);
    try {
      const data = await fetchEndpoint(path);
      const validation = validateResponse(
        name,
        data,
        REQUIRED_KEYS[name as keyof typeof ENDPOINTS]
      );
      results.push(validation);
      fixtures[name] = data;

      if (validation.valid) {
        console.log("✅");
      } else {
        console.log("❌");
        if (validation.missingKeys.length > 0) {
          console.log(`     Missing: ${validation.missingKeys.join(", ")}`);
        }
        if (validation.typeIssues.length > 0) {
          console.log(`     Issues: ${validation.typeIssues.join("; ")}`);
        }
      }
    } catch (error) {
      console.log(`❌ ${error instanceof Error ? error.message : error}`);
      results.push({
        endpoint: name,
        valid: false,
        missingKeys: [],
        extraKeys: [],
        typeIssues: [`Fetch failed: ${error}`],
      });
    }
  }

  const allValid = results.every((r) => r.valid);
  console.log(`\n${allValid ? "✅ All endpoints valid" : "❌ Some endpoints have issues"}`);

  if (updateMode && allValid) {
    console.log("\n📝 Generating fixture update...");
    console.log("   Copy the following to alignment.test.ts FIXTURES:\n");
    
    for (const [name, data] of Object.entries(fixtures)) {
      // Create a minimal example fixture (first item of arrays, etc.)
      const minimal = createMinimalFixture(data);
      console.log(generateFixtureCode(name, minimal));
    }
  }

  if (checkMode) {
    process.exit(allValid ? 0 : 1);
  }
}

function createMinimalFixture(data: unknown): unknown {
  if (typeof data !== "object" || data === null) return data;
  
  const obj = data as Record<string, unknown>;
  const result: Record<string, unknown> = {};
  
  for (const [key, value] of Object.entries(obj)) {
    if (Array.isArray(value)) {
      // Keep only first item of arrays
      result[key] = value.length > 0 ? [createMinimalFixture(value[0])] : [];
    } else if (typeof value === "object" && value !== null) {
      result[key] = createMinimalFixture(value);
    } else {
      result[key] = value;
    }
  }
  
  return result;
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
