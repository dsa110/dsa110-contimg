import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { nodePolyfills } from "vite-plugin-node-polyfills";
import { webcrypto } from "node:crypto";

// Ensure Web Crypto API exists early for Vite startup
if (typeof globalThis.crypto === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).crypto = webcrypto as any;
}

if (globalThis.crypto && !globalThis.crypto.getRandomValues) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis.crypto as any).getRandomValues = webcrypto.getRandomValues.bind(webcrypto);
}

function getApiProxyTarget(): string {
  const envTarget = process.env.API_PROXY_TARGET;
  if (envTarget) {
    try {
      new URL(envTarget);
      return envTarget;
    } catch {
      throw new Error(`Invalid API_PROXY_TARGET format: ${envTarget}. Must be a valid URL.`);
    }
  }
  return "http://127.0.0.1:8000";
}

const API_PROXY_TARGET = getApiProxyTarget();

// MINIMAL CONFIG - for debugging build hangs
export default defineConfig({
  plugins: [
    react(),
    nodePolyfills({
      globals: {
        Buffer: true,
        global: true,
        process: true,
      },
      include: ["crypto", "stream", "util"],
    }),
  ],
  base: process.env.NODE_ENV === "production" ? "/ui/" : "/",
  server: {
    host: "0.0.0.0",
    port: parseInt(process.env.VITE_PORT || process.env.PORT || "3210", 10),
    proxy: {
      "/api": {
        target: API_PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        ws: true,
        timeout: 10000,
        proxyTimeout: 10000,
      },
    },
  },
  build: {
    // Absolute minimal build config
    target: "esnext",
    minify: false, // Disable minification to speed up
    sourcemap: false, // Disable sourcemaps to speed up
    chunkSizeWarningLimit: 5000,
    // No rollup options - let Vite handle everything automatically
  },
  resolve: {
    dedupe: ["react", "react-dom"],
  },
});
