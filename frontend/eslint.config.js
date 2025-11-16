import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import unusedImports from "eslint-plugin-unused-imports";
import tseslint from "typescript-eslint";
import { defineConfig, globalIgnores } from "eslint/config";

export default defineConfig([
  globalIgnores(["dist"]),
  {
    files: ["**/*.{ts,tsx}"],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs["recommended-latest"],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "unused-imports": unusedImports,
    },
    rules: {
      // Prevent console.log usage - use logger instead
      "no-console": [
        "warn",
        {
          allow: ["warn", "error"], // Allow console.warn/error in ErrorBoundary and test setup
        },
      ],
      // Auto-remove unused imports
      "unused-imports/no-unused-imports": "error",
      // Turn off base rule to avoid conflicts
      "@typescript-eslint/no-unused-vars": "off",
      "no-unused-vars": "off",
    },
  },
  // Note: ESLint import plugin doesn't fully support flat config (ESLint 9) yet
  // Default export enforcement for lazy-loaded components is handled by:
  // 1. TypeScript type checking (catches missing default exports)
  // 2. Custom verification script: scripts/verify-page-exports.js
  // 3. Route rendering integration test (catches runtime errors)
  // See: frontend/docs/analysis/lazy-loading-export-issues.md
]);
