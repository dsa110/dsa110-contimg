import js from "@eslint/js";
import tseslint from "typescript-eslint";
import react from "eslint-plugin-react";
import reactHooks from "eslint-plugin-react-hooks";
import storybook from "eslint-plugin-storybook";
import unusedImports from "eslint-plugin-unused-imports";

/**
 * ESLint Configuration
 *
 * Note on Test File Warnings:
 * ---------------------------
 * Test files (*.test.ts, *.test.tsx) intentionally use `any` type coercion
 * for Vitest mock objects. Warnings like:
 *   "@typescript-eslint/no-explicit-any"
 * in test files are ACCEPTABLE and documented in src/test/setup.ts.
 *
 * Pattern: `(useHook as any).mockReturnValue({...})`
 * This is necessary because vi.mock() returns Mock<T> which doesn't expose
 * mock methods in the original type signature.
 */

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: {
      react,
      "react-hooks": reactHooks,
      "unused-imports": unusedImports,
    },
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    settings: {
      react: {
        version: "detect",
      },
    },
    rules: {
      ...react.configs.recommended.rules,
      ...react.configs["jsx-runtime"].rules,
      ...reactHooks.configs.recommended.rules,
      // Auto-remove unused imports
      "unused-imports/no-unused-imports": "error",
      "unused-imports/no-unused-vars": [
        "warn",
        { vars: "all", varsIgnorePattern: "^_", args: "after-used", argsIgnorePattern: "^_" },
      ],
      // Disable the base rule since unused-imports handles it
      "@typescript-eslint/no-unused-vars": "off",
      "@typescript-eslint/no-explicit-any": "warn",
      "react/prop-types": "off",
      "no-console": ["warn", { allow: ["warn", "error"] }],
      // Disable overly strict React 19 compiler rules - these patterns are valid
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/preserve-manual-memoization": "off",
    },
  },
  {
    files: ["**/*.stories.{ts,tsx}"],
    plugins: {
      storybook,
    },
    rules: {
      ...storybook.configs.recommended.rules,
      // Storybook's render function pattern uses hooks in a way that triggers
      // rules-of-hooks false positives. This is a known Storybook pattern.
      "react-hooks/rules-of-hooks": "off",
    },
  },
  {
    // Test file specific rules
    files: ["**/*.test.{ts,tsx}", "**/test/**/*.{ts,tsx}"],
    rules: {
      // Test wrapper components don't need display names
      "react/display-name": "off",
      // Test files commonly use any for mocking
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  {
    ignores: ["dist/**", "node_modules/**", "*.cjs"],
  }
);
