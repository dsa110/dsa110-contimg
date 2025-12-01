/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  css: {
    postcss: "./config/build/postcss.config.js",
  },
  // Base path for GitHub Pages deployment (repo name + dashboard subdirectory)
  // Use "/" for local dev and E2E tests (VITE_E2E_TEST=true), "/dsa110-contimg/dashboard/" for production
  base:
    process.env.GITHUB_ACTIONS && !process.env.VITE_E2E_TEST
      ? "/dsa110-contimg/dashboard/"
      : "/",
  server: {
    port: 3000,
    strictPort: true, // Fail if port 3000 is occupied
    open: false, // Disabled to prevent SSH disconnection issues
    host: "127.0.0.1", // Bind only to localhost
    allowedHosts: [
      "localhost",
      ".trycloudflare.com",
      ".ngrok-free.app",
      ".ngrok-free.dev",
    ],
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 3210,
    strictPort: true,
    host: "127.0.0.1",
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    // Generate sourcemaps for debugging
    sourcemap: true,
    // Report compressed chunk sizes for bundle analysis
    reportCompressedSize: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // D3 visualization libraries (~300KB)
          d3: ["d3", "d3-geo-projection", "d3-celestial"],
          // ECharts charting library (~900KB)
          echarts: ["echarts"],
          // Note: aladin-lite is vendored and loaded separately
        },
      },
    },
    // Allow larger vendor chunks for optional heavy viewers
    // Rationale: These are loaded on-demand only when users access specific features
    chunkSizeWarningLimit: 2500,
  },
  resolve: {
    alias: {
      "@": "/src",
    },
    dedupe: ["react", "react-dom"],
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/testing/setup.ts"],
    exclude: ["**/node_modules/**", "**/dist/**", "**/e2e/**"],
    typecheck: {
      tsconfig: "./tsconfig.test.json",
    },
  },
});
