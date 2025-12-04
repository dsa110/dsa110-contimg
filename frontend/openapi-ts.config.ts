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
 *   npm run openapi:sync           # Fetch + generate in one step
 *
 * Configuration options:
 *   https://openapi-ts.dev/introduction
 */

import { defineConfig } from "openapi-typescript";

export default defineConfig({
  // Default input path - overridden by CLI arguments
  // Using relative path for file-based generation
  input: "./src/api/openapi.json",

  // Output path - also typically overridden by CLI
  output: "./src/api/generated/api.d.ts",

  // Type generation options
  exportType: true, // Generate 'export type' instead of 'export interface'
  pathParamsAsTypes: true, // Use types for path params instead of inline
  alphabetize: false, // Don't alphabetize - keep API order for readability

  // Enable better formatting
  formatter: "prettier",

  // Additional TypeScript enhancements
  additionalProperties: false, // Strict mode - no extra props by default

  // Post-transform hook for custom type modifications
  // Uncomment to add custom transformations
  // transform: (schemaObject, metadata) => {
  //   // Example: Convert all Date strings to Date type
  //   if (schemaObject.format === 'date-time') {
  //     return { ...schemaObject, tsType: 'Date' };
  //   }
  //   return schemaObject;
  // },
});
