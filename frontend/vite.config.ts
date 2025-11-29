/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // Base path for GitHub Pages deployment (repo name + dashboard subdirectory)
  // Use "/" for local dev and E2E tests (VITE_E2E_TEST=true), "/dsa110-contimg/dashboard/" for production
  base:
    process.env.GITHUB_ACTIONS && !process.env.VITE_E2E_TEST ? "/dsa110-contimg/dashboard/" : "/",
  server: {
    port: 3000,
    strictPort: true, // Fail if port 3000 is occupied (don't auto-switch)
    open: true,
    allowedHosts: ["localhost", ".trycloudflare.com", ".ngrok-free.app", ".ngrok-free.dev"],
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
    rollupOptions: {
      output: {
        manualChunks: {
          d3: ["d3", "d3-geo-projection"],
          echarts: ["echarts"],
        },
      },
    },
    // Allow larger vendor chunks for optional heavy viewers (echarts, aladin-lite)
    chunkSizeWarningLimit: 2500,
  },
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    exclude: ["**/node_modules/**", "**/dist/**", "**/e2e/**"],
  },
});
