import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { webcrypto } from 'node:crypto';

// Ensure Web Crypto API exists early for Vite/Vitest startup
// Some Node builds may not expose globalThis.crypto by default
// Only set if not already present and writable
if (!globalThis.crypto) {
  try {
    (globalThis as any).crypto = webcrypto as any;
  } catch (e) {
    // Ignore if crypto is read-only (Node 22+ handles this automatically)
  }
}

// https://vite.dev/config/
const API_PROXY_TARGET = process.env.API_PROXY_TARGET || 'http://localhost:8010';

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    // Use node environment for backend API/client smoke tests to avoid jsdom/webcrypto issues
    environmentMatchGlobs: [["src/api/**", "node"]],
    setupFiles: './src/test/setup.ts',
  },
});
