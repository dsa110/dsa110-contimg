# Build Solution: Using /scratch/ for Faster Builds

## Problem Solved

The build was hanging for 30+ minutes on `/data/` filesystem. **Root cause: slow
filesystem I/O** (likely network-mounted storage).

## Solution

Build in `/scratch/` (fast local storage), then copy results back to `/data/`.

**Results:**

- ✅ Build completes in **~1-2 minutes** (vs 30+ minutes/hanging)
- ✅ All files properly built and chunked
- ✅ Plotly.js (12MB) successfully bundled
- ✅ No hangs or timeouts

## Usage

### Quick Build (Recommended)

```bash
# From /data/dsa110-contimg/frontend/
npm run build:scratch
```

### Fast Build (Development Mode)

```bash
npm run build:scratch:fast
```

### Manual Build

```bash
# Build in /scratch/ and copy back
bash scripts/build-in-scratch.sh build:no-check

# Or with type checking
bash scripts/build-in-scratch.sh build
```

## How It Works

1. **Copies source** to `/scratch/dsa110-contimg-build/frontend/` (excludes
   node_modules, dist, .git)
2. **Installs dependencies** in scratch if needed
3. **Builds** in scratch (fast I/O)
4. **Copies dist/** back to `/data/dsa110-contimg/frontend/dist/`

## Why This Works

- `/scratch/` is **local NVMe storage** (fast I/O)
- `/data/` is likely **network-mounted** (slow I/O)
- Vite build does **massive I/O** (reading 13,167 modules, writing chunks)
- Fast I/O = fast builds ✅

## Build Output

The build produces:

- `dist/index.html` - Entry point
- `dist/assets/*.js` - Code-split chunks
  - `plotly-vendor-*.js` - 12MB (lazy-loaded)
  - `react-vendor-*.js` - 829KB
  - `mui-vendor-*.js` - 1.3MB
  - `vendor-*.js` - 2.7MB
  - Various page chunks (lazy-loaded)
- `dist/assets/*.css` - Stylesheets

## Performance

| Location    | Build Time      | Status |
| ----------- | --------------- | ------ |
| `/data/`    | 30+ min / hangs | ❌     |
| `/scratch/` | ~1-2 min        | ✅     |

## For CI/CD

If building in CI/CD, ensure:

1. Build directory is on fast local storage
2. Or use Docker with volume mounts on fast storage
3. Or use the scratch approach if available

## Alternative: Move Entire Project

If you want to work entirely from `/scratch/`:

```bash
# Move project
mv /data/dsa110-contimg /scratch/dsa110-contimg

# Update any absolute paths in configs
# Then build normally:
cd /scratch/dsa110-contimg/frontend
npm run build:no-check
```

## Technical Details

The build process:

1. Transforms 13,167 modules
2. Creates optimized chunks with code splitting
3. Handles large libraries (plotly.js 12MB) via lazy loading
4. Generates sourcemaps (in development mode)
5. Computes gzip sizes

All of this requires **fast I/O** - which `/scratch/` provides.
