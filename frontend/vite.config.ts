/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const CSP_DIRECTIVES = [
  "default-src 'self'",
  // Allow images from Aladin HiPS servers, JS9, and data URIs
  "img-src 'self' data: blob: https://js9.si.edu https://*.unistra.fr https://*.cds.unistra.fr https://*.u-strasbg.fr https://alaskybis.cds.unistra.fr https://alaskybis.u-strasbg.fr https://alasky.cds.unistra.fr https://alasky.u-strasbg.fr",
  "style-src 'self' 'unsafe-inline' https://js9.si.edu",
  // Allow scripts from JS9 and CDNs, plus WASM for Aladin
  "script-src 'self' 'unsafe-eval' 'wasm-unsafe-eval' https://js9.si.edu https://cdnjs.cloudflare.com https://aladin.cds.unistra.fr",
  // Allow connections to local servers and Aladin HiPS tile servers
  "connect-src 'self' http://127.0.0.1:* http://localhost:* ws://localhost:* ws://127.0.0.1:* https://*.unistra.fr https://*.cds.unistra.fr https://*.u-strasbg.fr https://alaskybis.cds.unistra.fr https://alaskybis.u-strasbg.fr https://alasky.cds.unistra.fr https://alasky.u-strasbg.fr https://cdsweb.u-strasbg.fr",
  "worker-src 'self' blob:",
  "object-src 'none'",
  "frame-ancestors 'self'",
];

const CSP_HEADER = `${CSP_DIRECTIVES.join("; ")};`;

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
    headers: {
      "Content-Security-Policy": CSP_HEADER,
    },
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
      "/absurd": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 3210,
    strictPort: true,
    host: "127.0.0.1",
    headers: {
      "Content-Security-Policy": CSP_HEADER,
    },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/absurd": {
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
    setupFiles: ["./src/testing/msw-setup.ts", "./src/testing/setup.ts"],
    exclude: ["**/node_modules/**", "**/dist/**", "**/e2e/**"],
    typecheck: {
      tsconfig: "./tsconfig.test.json",
    },
  },
});
