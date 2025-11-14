import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

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
  plugins: [react()],
  // Use /ui/ base path for production builds (when served from FastAPI at /ui)
  // In dev mode, Vite serves from root, so base is '/'
  base: process.env.NODE_ENV === "production" ? "/ui/" : "/",
  server: {
    host: "0.0.0.0", // Allow external connections in Docker
    port: 3210,
    hmr: {
      host: "localhost",
      port: 3210,
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
    // Code splitting configuration
    rollupOptions: {
      output: {
        // Manual chunk splitting for better caching
        manualChunks: {
          // Vendor chunks
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          "mui-vendor": [
            "@mui/material",
            "@mui/icons-material",
            "@emotion/react",
            "@emotion/styled",
          ],
          "query-vendor": ["@tanstack/react-query"],
          "plotly-vendor": ["plotly.js", "react-plotly.js"],
          // Heavy components
          "carta-vendor": [
            "./src/components/CARTA",
            "./src/pages/CARTAPage",
            "./src/pages/QACartaPage",
          ],
          "js9-vendor": ["./src/contexts/JS9Context"],
        },
        // Optimize chunk size
        chunkSizeWarningLimit: 1000, // 1MB warning threshold
      },
    },
    // Optimize build output
    target: "esnext",
    minify: "esbuild",
    sourcemap: process.env.NODE_ENV === "development",
    // Increase chunk size limit for large dependencies
    chunkSizeWarningLimit: 1000,
  },
  resolve: {
    // Ensure proper module resolution for date-fns
    dedupe: ["date-fns"],
  },
  optimizeDeps: {
    include: ["date-fns"],
    esbuildOptions: {
      // Ensure date-fns is treated as ESM
      mainFields: ["module", "main"],
    },
  },
});
