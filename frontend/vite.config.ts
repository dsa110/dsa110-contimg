import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { nodePolyfills } from "vite-plugin-node-polyfills";

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
      // Enable buffer polyfill
      globals: {
        Buffer: true,
        global: true,
        process: true,
      },
    }),
  ],
  // Use /ui/ base path for production builds (when served from FastAPI at /ui)
  // In dev mode, Vite serves from root, so base is '/'
  base: process.env.NODE_ENV === "production" ? "/ui/" : "/",
  server: {
    host: "0.0.0.0", // Allow external connections in Docker
    port: 5173,
    hmr: {
      host: "localhost",
      port: 5173,
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
        // Manual chunk splitting for better caching and code splitting
        // Using function form to handle dynamic imports and node_modules better
        manualChunks(id) {
          // Plotly is lazy-loaded, so it will be in its own chunk automatically
          // But we explicitly ensure it's separated
          if (id.includes("plotly.js") || id.includes("react-plotly.js")) {
            return "plotly-vendor";
          }

          // Node modules vendor chunks
          if (id.includes("node_modules")) {
            // React ecosystem
            if (id.includes("react") || id.includes("react-dom") || id.includes("react-router")) {
              return "react-vendor";
            }
            // Material-UI
            if (id.includes("@mui") || id.includes("@emotion")) {
              return "mui-vendor";
            }
            // TanStack Query
            if (id.includes("@tanstack/react-query")) {
              return "query-vendor";
            }
            // CARTA dependencies
            if (id.includes("carta") || id.includes("protobuf")) {
              return "carta-vendor";
            }
            // JS9 dependencies
            if (id.includes("js9")) {
              return "js9-vendor";
            }
            // Other large vendor libraries
            if (id.includes("dayjs") || id.includes("date-fns")) {
              return "date-vendor";
            }
            // Default vendor chunk for other node_modules
            return "vendor";
          }

          // Application code chunks (for better caching)
          if (
            id.includes("/src/pages/CARTAPage") ||
            id.includes("/src/pages/QACartaPage") ||
            id.includes("/src/components/CARTA")
          ) {
            return "carta-app";
          }
          if (id.includes("/src/contexts/JS9Context")) {
            return "js9-app";
          }
        },
      },
    },
    // Optimize build output
    target: "esnext",
    minify: "esbuild",
    sourcemap: process.env.NODE_ENV === "development",
    // Chunk size warning threshold (1MB)
    // Large chunks like plotly-vendor are lazy-loaded, so warnings are expected
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
