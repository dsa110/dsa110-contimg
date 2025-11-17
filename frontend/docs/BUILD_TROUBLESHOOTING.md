# Build Troubleshooting

## ✅ SOLUTION: Build in /scratch/

**The build hang was caused by slow filesystem I/O on `/data/`.**

**Use the scratch build script:**

```bash
npm run build:scratch
```

This builds in `/scratch/` (fast local storage) and copies results back. Build
time: **~1-2 minutes** (vs 30+ min/hanging).

See [BUILD_SOLUTION.md](./BUILD_SOLUTION.md) for details.

---

## Problem: Build Hangs for 30+ Minutes (RESOLVED)

The build process was hanging during the "transforming" phase and never
completes. **This is now solved by building in `/scratch/`**.

## Root Cause Analysis

The build hangs at the transformation step, which suggests:

1. A problematic dependency (golden-layout, plotly.js, or large libraries)
2. Circular dependencies
3. Memory/resource constraints
4. Vite 6 compatibility issues with certain dependencies

## Workaround: Use Dev Server Only

**Since builds never complete, the recommended approach is:**

### For Development

```bash
# Use dev server (works perfectly, instant updates)
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6
npm run dev  # → http://localhost:3210
```

### For Production Deployment

Since local builds don't work, use one of these alternatives:

1. **CI/CD Build** (Recommended)
   - Build in CI/CD pipeline where environment is controlled
   - Push built artifacts to deployment

2. **Docker Build**

   ```bash
   docker build -f Dockerfile.dev -t frontend-dev .
   # Or use docker-compose which may have different build context
   ```

3. **Skip Local Builds Entirely**
   - Use dev server for all development
   - Only build in CI/CD or production environment
   - This is actually a common pattern for large frontend projects

## Why This Happens

The transformation phase processes all source files and dependencies. With:

- 196 TypeScript files
- Large dependencies (plotly.js, golden-layout, etc.)
- Complex code splitting logic (now simplified)
- Vite 6 + Node.js compatibility issues

The build can hang or take extremely long times.

## Alternative Build Commands (If You Want to Try)

```bash
# Minimal config (may work)
npm run build:debug

# Skip transformations where possible
npm run build:skip-transform

# Development mode (less optimization)
npm run build:fast
```

## Recommended Strategy

**Don't build locally.** Instead:

1. **Development**: Always use `npm run dev` (works perfectly)
2. **Testing**: Use dev server - it's production-like enough
3. **Production**: Build in CI/CD or Docker where environment is controlled

This is actually a best practice - many teams don't build locally, they rely on
CI/CD.

## If You Must Build Locally

Try these in order:

1. Increase Node.js memory:

   ```bash
   NODE_OPTIONS="--max-old-space-size=4096" npm run build:no-check
   ```

2. Use minimal config:

   ```bash
   npm run build:debug
   ```

3. Build in Docker (different environment):

   ```bash
   docker-compose build dashboard-dev
   ```

4. Check for problematic files:
   - Large files (>100KB)
   - Circular dependencies
   - Problematic imports

## Status

- ✅ Dev server: Works perfectly
- ❌ Local builds: Hang indefinitely
- ✅ Solution: Use dev server for development, CI/CD for builds
