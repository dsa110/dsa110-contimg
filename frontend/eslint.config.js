import path from "node:path";
import { fileURLToPath } from "node:url";
import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import unusedImports from "eslint-plugin-unused-imports";
import tseslint from "typescript-eslint";
import { defineConfig, globalIgnores } from "eslint/config";
import requireReactForRouterHooks from "./scripts/tools/eslint-rules/require-react-for-router-hooks.js";

const tsconfigRootDir = path.dirname(fileURLToPath(import.meta.url));
const nodeTsFilePatterns = [
  "scripts/**/*.{ts,tsx}",
  "**/*.config.{ts,tsx}",
  "vitest.config.{ts,tsx}",
  "playwright.config.{ts,tsx}",
];
const nodeJsFilePatterns = [
  "scripts/**/*.{js,jsx,mjs,cjs}",
  "**/*.config.{js,jsx,mjs,cjs}",
  "eslint.config.js",
];
const projectServiceParserOptions = {
  projectService: true,
  tsconfigRootDir,
};
const sharedTsRules = {
  "unused-imports/no-unused-imports": "error",
  "@typescript-eslint/no-unused-vars": "off",
  "no-unused-vars": "off",
};
const noConsoleRule = [
  "warn",
  {
    allow: ["warn", "error"],
  },
];

export default defineConfig([
  globalIgnores(["node_modules", "dist", "build", ".local", "playwright-report", "config/playwright", "config/vite"]),
  {
    files: ["**/*.{ts,tsx}"],
    ignores: nodeTsFilePatterns,
    extends: [
      js.configs.recommended,
      ...tseslint.configs.strictTypeChecked,
      ...tseslint.configs.stylisticTypeChecked,
      reactHooks.configs["recommended-latest"],
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      parserOptions: projectServiceParserOptions,
    },
    plugins: {
      "unused-imports": unusedImports,
      "require-react-for-router-hooks": {
        rules: {
          "require-react-for-router-hooks":
            requireReactForRouterHooks.default || requireReactForRouterHooks,
        },
      },
    },
    rules: {
      // Prevent console.log usage - use logger instead
      "no-console": noConsoleRule,
      // Auto-remove unused imports
      ...sharedTsRules,
      // Require React import when using react-router-dom hooks (React 19 requirement)
      "require-react-for-router-hooks/require-react-for-router-hooks": "error",
      // Allow GridLegacy usage - Grid2 not available in this MUI version
      "@typescript-eslint/no-deprecated": "off",
    },
  },
  {
    files: nodeTsFilePatterns,
    extends: [
      js.configs.recommended,
      ...tseslint.configs.strictTypeChecked,
      ...tseslint.configs.stylisticTypeChecked,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.node,
      parserOptions: projectServiceParserOptions,
    },
    plugins: {
      "unused-imports": unusedImports,
    },
    rules: {
      ...sharedTsRules,
      "no-console": noConsoleRule,
    },
  },
  {
    files: ["**/*.{js,jsx,mjs,cjs}", ...nodeJsFilePatterns],
    extends: [js.configs.recommended],
    languageOptions: {
      ecmaVersion: 2022,
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      "unused-imports": unusedImports,
    },
    rules: {
      "no-console": noConsoleRule,
      "unused-imports/no-unused-imports": "error",
    },
  },
  // Note: ESLint import plugin doesn't fully support flat config (ESLint 9) yet
  // Default export enforcement for lazy-loaded components is handled by:
  // 1. TypeScript type checking (catches missing default exports)
  // 2. Custom verification script: scripts/verify-page-exports.js
  // 3. Route rendering integration test (catches runtime errors)
  // See: frontend/docs/analysis/lazy-loading-export-issues.md
]);
