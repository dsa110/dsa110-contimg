import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { nodePolyfills } from "vite-plugin-node-polyfills";
import { webcrypto } from "node:crypto";

// Ensure Web Crypto API exists early for Vite startup
// Node 16+ requires explicit setup for crypto.getRandomValues
// This is required because Vite 6 needs crypto.getRandomValues which isn't available in Node 16
if (typeof globalThis.crypto === "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).crypto = webcrypto as any;
}

// Ensure getRandomValues is available (required by Vite)
if (globalThis.crypto && !globalThis.crypto.getRandomValues) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis.crypto as any).getRandomValues = webcrypto.getRandomValues.bind(webcrypto);
}

// Plugin to suppress CSS URL warnings for public assets that resolve at runtime
// These warnings are harmless - the assets exist in public/ and work correctly at runtime
function suppressPublicAssetWarnings(): Plugin {
  const originalWarn = console.warn;

  return {
    name: "suppress-public-asset-warnings",
    enforce: "pre",
    buildStart() {
      // Intercept console.warn during build to filter out public asset warnings
      console.warn = (...args: unknown[]) => {
        const message = String(args[0] || "");
        // Suppress warnings about golden-layout images that don't resolve at build time
        // These are in public/ and work correctly at runtime
        if (message.includes("didn't resolve at build time") && message.includes("golden-layout")) {
          return; // Suppress this warning
        }
        // Pass through all other warnings
        originalWarn.apply(console, args);
      };
    },
    buildEnd() {
      // Restore original console.warn
      console.warn = originalWarn;
    },
  };
}

// https://vite.dev/config/
// In Docker, use service name 'api' or container name 'contimg-api'; locally, use localhost
// Try container name first (more reliable), then service name, then localhost
// If API is running on host, use host gateway IP (detected from container's default gateway)

function getApiProxyTarget(): string {
  const envTarget = process.env.API_PROXY_TARGET;
  if (envTarget) {
    // Validate URL format
    try {
      new URL(envTarget);
      return envTarget;
    } catch {
      throw new Error(`Invalid API_PROXY_TARGET format: ${envTarget}. Must be a valid URL.`);
    }
  }

  // Default based on environment - use 127.0.0.1 for better compatibility
  // Backend runs on host, not in container for dev mode
  return "http://127.0.0.1:8000";
}

const API_PROXY_TARGET = getApiProxyTarget();

export default defineConfig({
  plugins: [
    react(),
    nodePolyfills({
      // Enable buffer and crypto polyfills
      globals: {
        Buffer: true,
        global: true,
        process: true,
      },
      // Enable crypto polyfill for browser environment
      include: ["crypto", "stream", "util"],
    }),
    suppressPublicAssetWarnings(),
  ],
  // Use /ui/ base path for production builds (when served from FastAPI at /ui)
  // In dev mode, Vite serves from root, so base is '/'
  base: process.env.NODE_ENV === "production" ? "/ui/" : "/",
  server: {
    host: "0.0.0.0", // Allow external connections in Docker
    port: parseInt(process.env.VITE_PORT || process.env.PORT || "3210", 10),
    hmr: {
      // Let Vite auto-detect the client hostname and port for HMR WebSocket connections
      // This works for both local and remote connections and matches the server port
      // Port will automatically match server.port when not specified
    },
    watch: {
      usePolling: false, // Use native file system events (faster)
      interval: 100, // Polling interval if usePolling is true
    },
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
    target: "esnext",
    minify: "esbuild",
    // sourcemap is defined below in rollupOptions
    chunkSizeWarningLimit: 5000, // Increased to accommodate plotly-vendor (4.8MB) which is expected
    // CRITICAL FIX: Increase build timeout and disable problematic optimizations
    // Using plotly.js-dist-min (pre-built browser bundle) instead of plotly.js source
    // By using the pre-built version and lazy-loading, we keep build times manageable
    rollupOptions: {
      output: {
        // Separate only the heaviest libraries to keep build times manageable
        manualChunks(id) {
          if (id.includes("plotly.js-dist-min") || id.includes("react-plotly.js")) {
            return "plotly-vendor";
          }
          if (id.includes("golden-layout")) {
            return "golden-layout-vendor";
          }
        },
      },
      // CRITICAL: Use onwarn to suppress warnings and prevent build from hanging on warnings
      onwarn(warning, warn) {
        // Suppress warnings for large chunks (plotly.js will be large)
        if (warning.code === "CHUNK_SIZE_WARNING") {
          return;
        }
        warn(warning);
      },
    },
    // CRITICAL: Disable sourcemap for large libraries to speed up build
    // Sourcemaps for plotly.js-dist-min are huge and slow down the build significantly
    sourcemap: process.env.NODE_ENV === "development" ? "inline" : false,
    // Suppress warnings for asset paths that resolve at runtime
    assetsInlineLimit: 4096,
  },
  preview: {
    port: parseInt(process.env.VITE_PORT || process.env.PORT || "3210", 10),
    host: "0.0.0.0",
    // Always use /ui/ base path for preview to match production build
    // The build uses /ui/ base, so preview must match for assets to load correctly
    base: "/ui/",
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
  resolve: {
    // Ensure proper module resolution and prevent multiple React copies
    dedupe: ["react", "react-dom", "date-fns"],
  },
  optimizeDeps: {
    // CRITICAL: Include all dependencies that need CommonJS -> ESM transformation
    // plotly.js must be pre-transformed because it contains CommonJS code
    // This happens once at startup, then the transformed version is cached
    include: ["date-fns", "react", "react-dom", "react-plotly.js", "plotly.js"],
    // Exclude only dependencies that are already ESM and don't need transformation
    exclude: [
      "golden-layout",
      // Exclude other large dependencies that are already ESM-compatible
    ],
    esbuildOptions: {
      // Ensure date-fns is treated as ESM
      mainFields: ["module", "main"],
    },
  },
});
