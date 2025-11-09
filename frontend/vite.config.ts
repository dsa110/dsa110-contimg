import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

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
  return 'http://127.0.0.1:8000';
}

const API_PROXY_TARGET = getApiProxyTarget();

export default defineConfig({
  plugins: [react()],
  // Use /ui/ base path for production builds (when served from FastAPI at /ui)
  // In dev mode, Vite serves from root, so base is '/'
  base: process.env.NODE_ENV === 'production' ? '/ui/' : '/',
  server: {
    host: '0.0.0.0', // Allow external connections in Docker
    port: 5173,
    proxy: {
      '/api': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
        secure: false,
        ws: true,
        timeout: 10000,
        proxyTimeout: 10000,
      }
    }
  }
})
