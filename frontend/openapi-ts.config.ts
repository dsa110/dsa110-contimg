/**
 * OpenAPI TypeScript Configuration
 *
 * This configuration file controls the generation of TypeScript types
 * from the FastAPI backend's OpenAPI schema.
 *
 * Usage:
 *   npm run openapi:generate       # Generate types from live API
 *   npm run openapi:generate:file  # Generate types from saved schema
 *   npm run openapi:fetch          # Just fetch and save the schema
 */

import { defineConfig } from "openapi-typescript";

export default defineConfig({
  // Path to the backend's OpenAPI schema
  // Can be a URL (for live API) or file path (for saved schema)
  // Default uses the local FastAPI server
  // Override with OPENAPI_URL environment variable
});
