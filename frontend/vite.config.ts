import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// In Docker, use service name 'api' or container name 'contimg-api'; locally, use localhost
// Try container name first (more reliable), then service name, then localhost
const API_PROXY_TARGET = process.env.API_PROXY_TARGET || 
  (process.env.NODE_ENV === 'production' ? 'http://contimg-api:8010' : 'http://localhost:8010')

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow external connections in Docker
    port: 5173,
    proxy: {
      '/api': {
        target: API_PROXY_TARGET,
        changeOrigin: true,
        rewrite: (path) => path, // Keep /api prefix
      }
    }
  }
})
