# Frontend Development Strategy

## Problem

Full production builds take 1-2+ minutes, which is too slow for active
development.

## Solution: Three-Tier Approach

### 1. **Development (Day-to-Day)**

- **Use**: Vite dev server with HMR
- **Port**: 3210 (standardized)
- **Speed**: Instant updates, no rebuild needed
- **Command**: `npm run dev`
- **When**: All active development work

### 2. **Production Preview (Testing)**

- **Use**: Vite preview mode (serves already-built files)
- **Port**: 3210
- **Speed**: Instant (no rebuild, just serves existing build)
- **Command**: `npm run build && npm run preview`
- **When**: Testing production-like behavior before deployment

### 3. **Production Build (Deployment)**

- **Use**: Full optimized build
- **When**: Only for actual deployment/releases
- **Command**: `npm run build`
- **Speed**: 1-2 minutes (acceptable for CI/CD)

## Configuration

### Standardize on Port 3210

- Dev server: `VITE_PORT=3210 npm run dev`
- Preview: `VITE_PORT=3210 npm run preview`
- Production: Already on 3210

### Docker Strategy

- **Remove**: `dashboard-dev` container (use local dev server)
- **Keep**: `dashboard` container for production only
- **Local dev**: Run `npm run dev` directly (faster, better HMR)

## Benefits

- ✅ Fast development (instant HMR)
- ✅ No waiting for builds during development
- ✅ Can test production build when needed (preview mode)
- ✅ Simplified setup (one port: 3210)
- ✅ Production builds only when actually deploying
