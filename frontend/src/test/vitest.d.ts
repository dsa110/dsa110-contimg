/// <reference types="vitest" />
/// <reference types="@testing-library/jest-dom" />

/**
 * Type augmentation for Vitest to include @testing-library/jest-dom matchers.
 *
 * This file extends Vitest's Assertion interface with the custom matchers
 * provided by @testing-library/jest-dom, such as:
 * - toBeInTheDocument()
 * - toHaveAttribute()
 * - toHaveClass()
 * - toBeVisible()
 * - etc.
 *
 * This is imported via the test setup file.
 */

import type { TestingLibraryMatchers } from "@testing-library/jest-dom/matchers";

declare module "vitest" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  interface Assertion<T = any> extends TestingLibraryMatchers<T, void> {}
  interface AsymmetricMatchersContaining extends TestingLibraryMatchers<unknown, void> {}
}
