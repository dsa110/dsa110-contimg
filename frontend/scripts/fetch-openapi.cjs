#!/usr/bin/env node
/**
 * OpenAPI Schema Fetcher
 *
 * Fetches the OpenAPI schema from the backend API and saves it locally.
 * This allows for offline type generation and version control of the API schema.
 *
 * Usage:
 *   node scripts/fetch-openapi.cjs
 *   node scripts/fetch-openapi.cjs --url http://localhost:8000/api/openapi.json
 *   node scripts/fetch-openapi.cjs --output src/api/schema.json
 */

const http = require("http");
const fs = require("fs");
const path = require("path");

// Configuration
const DEFAULT_URL =
  process.env.OPENAPI_URL || "http://localhost:8000/api/openapi.json";
const DEFAULT_OUTPUT = path.join(__dirname, "..", "src", "api", "openapi.json");

// Parse command line arguments
const args = process.argv.slice(2);
let url = DEFAULT_URL;
let output = DEFAULT_OUTPUT;

for (let i = 0; i < args.length; i++) {
  if (args[i] === "--url" && args[i + 1]) {
    url = args[++i];
  } else if (args[i] === "--output" && args[i + 1]) {
    output = args[++i];
  } else if (args[i] === "--help") {
    console.log(`
OpenAPI Schema Fetcher

Usage:
  node scripts/fetch-openapi.cjs [options]

Options:
  --url <url>       URL to fetch OpenAPI schema from (default: ${DEFAULT_URL})
  --output <path>   Output file path (default: ${DEFAULT_OUTPUT})
  --help            Show this help message

Environment Variables:
  OPENAPI_URL       Default URL for OpenAPI schema

Examples:
  node scripts/fetch-openapi.cjs
  node scripts/fetch-openapi.cjs --url http://localhost:8000/api/openapi.json
  OPENAPI_URL=http://prod-api/openapi.json node scripts/fetch-openapi.cjs
`);
    process.exit(0);
  }
}

console.log(`📥 Fetching OpenAPI schema from: ${url}`);

// Determine if http or https
const client = url.startsWith("https") ? require("https") : require("http");

const request = client.get(url, (response) => {
  if (response.statusCode !== 200) {
    console.error(`❌ Failed to fetch schema: HTTP ${response.statusCode}`);
    console.error("   Make sure the backend API is running.");
    console.error(`   Try: curl ${url}`);
    process.exit(1);
  }

  let data = "";
  response.on("data", (chunk) => {
    data += chunk;
  });

  response.on("end", () => {
    try {
      // Parse to validate JSON
      const schema = JSON.parse(data);

      // Ensure output directory exists
      const outputDir = path.dirname(output);
      if (!fs.existsSync(outputDir)) {
        fs.mkdirSync(outputDir, { recursive: true });
      }

      // Write formatted JSON
      fs.writeFileSync(output, JSON.stringify(schema, null, 2));

      console.log(`✅ Schema saved to: ${output}`);
      console.log(`   API Title: ${schema.info?.title || "Unknown"}`);
      console.log(`   API Version: ${schema.info?.version || "Unknown"}`);
      console.log(`   Paths: ${Object.keys(schema.paths || {}).length}`);
      console.log(
        `   Schemas: ${Object.keys(schema.components?.schemas || {}).length}`
      );
    } catch (error) {
      console.error("❌ Failed to parse OpenAPI schema:", error.message);
      process.exit(1);
    }
  });
});

request.on("error", (error) => {
  console.error("❌ Failed to connect to API:", error.message);
  console.error("   Make sure the backend API is running at:", url);
  process.exit(1);
});

request.setTimeout(10000, () => {
  console.error("❌ Request timed out");
  request.destroy();
  process.exit(1);
});
