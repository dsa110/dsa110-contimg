/**
 * Test setup file for Vitest
 */
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';
import { webcrypto } from 'node:crypto';

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Ensure Web Crypto API is available in jsdom environment
if (!(globalThis as any).crypto || !(globalThis as any).crypto.getRandomValues) {
  (globalThis as any).crypto = webcrypto as unknown as Crypto;
}
