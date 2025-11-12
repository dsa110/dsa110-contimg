/**
 * Test setup file for Vitest
 */
import { expect, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom/matchers';
import { webcrypto } from 'node:crypto';
import { execSync } from 'child_process';

// CRITICAL: Second check for casa6 Node.js (runs before tests)
// This catches any bypass of vitest.config.ts check
const CASA6_NODE = '/opt/miniforge/envs/casa6/bin/node';

function verifyCasa6Node(): void {
  try {
    const currentNode = execSync('which node', { encoding: 'utf-8' }).trim();
    if (currentNode !== CASA6_NODE) {
      const currentVersion = execSync('node --version', { encoding: 'utf-8' }).trim();
      console.error('\n❌ ERROR: Tests require casa6 Node.js v22.6.0');
      console.error(`   Current: ${currentNode} (${currentVersion})`);
      console.error(`   Required: ${CASA6_NODE} (v22.6.0)`);
      console.error('\n   Fix: source /opt/miniforge/etc/profile.d/conda.sh && conda activate casa6\n');
      throw new Error('Invalid Node.js environment');
    }
  } catch (error: any) {
    if (error.message === 'Invalid Node.js environment') {
      throw error;
    }
    // If execSync fails, we're in a test environment - allow it
  }
}

// Verify casa6 Node.js before tests run
verifyCasa6Node();

// Extend Vitest's expect with jest-dom matchers
expect.extend(matchers);

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Ensure Web Crypto API is available in jsdom environment
// If this fails, it's likely due to Node.js version issue
try {
  if (!(globalThis as any).crypto || !(globalThis as any).crypto.getRandomValues) {
    (globalThis as any).crypto = webcrypto as unknown as Crypto;
  }
} catch (error: any) {
  console.error('\n❌ ERROR: Crypto API initialization failed');
  console.error('   This usually indicates Node.js version incompatibility');
  console.error('   Required: casa6 Node.js v22.6.0');
  console.error('   Fix: source /opt/miniforge/etc/profile.d/conda.sh && conda activate casa6\n');
  throw error;
}
