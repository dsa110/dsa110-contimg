# Plotly.js CommonJS Fix

**Date:** 2025-11-17  
**Type:** Troubleshooting Guide  
**Status:** ✅ Fixed

---

## Problem

When lazy-loading Plotly.js in the dashboard, the browser console showed:

```
ReferenceError: require is not defined
```

This error occurred in the `PlotlyLazy` component when trying to dynamically
import `plotly.js`.

---

## Root Cause

**Vite's Module Transformation:**

- Vite uses esbuild to pre-transform CommonJS dependencies into ES modules
  during development
- This transformation happens in the `optimizeDeps` step
- However, dependencies listed in `optimizeDeps.exclude` are **not transformed**

**The Issue:**

- `plotly.js` contains CommonJS code (using `require()`, `module.exports`, etc.)
- When `plotly.js` was in `optimizeDeps.exclude`, Vite skipped transformation
- The browser received raw CommonJS code with `require()` calls
- Browsers don't understand `require()` (it's a Node.js API), causing the error

---

## Solution

### Step 1: Include plotly.js in optimizeDeps

Modified `vite.config.ts` to include `plotly.js` in `optimizeDeps.include`:

```typescript
optimizeDeps: {
  // CRITICAL: Include all dependencies that need CommonJS -> ESM transformation
  // plotly.js must be pre-transformed because it contains CommonJS code
  // This happens once at startup, then the transformed version is cached
  include: ["date-fns", "react", "react-dom", "react-plotly.js", "plotly.js"],
  // Exclude only dependencies that are already ESM and don't need transformation
  exclude: [
    "golden-layout",
    // Exclude other large dependencies that are already ESM-compatible
  ],
}
```

### Step 2: Clear Vite Cache

```bash
cd /data/dsa110-contimg/frontend
rm -rf node_modules/.vite
```

### Step 3: Restart Dev Server

The dev server automatically detected the config change and re-optimized
dependencies.

---

## Technical Details

### What `optimizeDeps` Does

1. **Include:** Forces Vite to pre-bundle and transform these dependencies
   - CommonJS → ES modules conversion
   - Dependency flattening
   - Caching for faster subsequent loads

2. **Exclude:** Skips pre-bundling for these dependencies
   - Useful for dependencies that are already ES modules
   - Useful for dependencies that don't work well with esbuild
   - **Warning:** Excluded dependencies must be valid ES modules!

### Why plotly.js Needs Pre-transformation

- `plotly.js` is a large library (~3MB) with CommonJS modules
- It uses `require()` internally for module loading
- Browsers don't support `require()` - only `import`/`export`
- Vite's esbuild pre-bundling converts `require()` → `import`

### Performance Impact

**Startup Time:**

- First load: +2-3 seconds (one-time pre-bundling of plotly.js)
- Subsequent loads: Fast (uses cached transformed version)

**Runtime Performance:**

- No impact - the transformed module is cached in `node_modules/.vite/`
- Lazy loading still works - the module is only loaded when needed

**Build Time:**

- No impact on production build time
- This only affects development mode

---

## Related Errors

This fix also resolved:

1. **"exports is not defined"** - Same root cause (CommonJS not transformed)
2. **"module is not defined"** - Same root cause

---

## Files Changed

1. **`vite.config.ts`**
   - Added `plotly.js` to `optimizeDeps.include`
   - Removed `plotly.js` from `optimizeDeps.exclude`

---

## Verification

After applying this fix:

1. ✅ No more "require is not defined" errors
2. ✅ PlotlyLazy component loads successfully
3. ✅ Pointing visualization renders correctly
4. ✅ Dev server startup is fast (after first pre-bundle)

---

## Prevention

### When to Include in optimizeDeps

**Include dependencies that:**

- Use CommonJS (`require()`, `module.exports`)
- Have many internal modules that need flattening
- Are frequently imported (for faster dev server startup)

**Exclude dependencies that:**

- Are already pure ES modules
- Don't work well with esbuild transformation
- Are very large and rarely used (to speed up startup)

### Testing

When adding a new lazy-loaded dependency:

1. Check if it uses CommonJS or ESM
2. If CommonJS, add to `optimizeDeps.include`
3. Test lazy loading in the browser
4. Check console for `require`/`exports`/`module` errors

---

## Related Issues

- **Plotly.purge error:** Fixed in `PLOTLY_FIX.md`
- **Build hangs:** Fixed in `BUILD_SOLUTION.md` (using `/scratch/`)
- **CSP violations:** Fixed in `PREVIEW_FIX.md`

---

## References

- [Vite Dependency Pre-Bundling](https://vitejs.dev/guide/dep-pre-bundling.html)
- [Vite optimizeDeps Documentation](https://vitejs.dev/config/dep-optimization-options.html)
- [CommonJS vs ES Modules](https://nodejs.org/api/esm.html#modules-commonjs-namespace)

---

**Last Updated:** 2025-11-17  
**Status:** ✅ Fixed and Documented
