# Plotly.js Integration - Complete Fix Summary

**Date:** 2025-11-17  
**Type:** Reference  
**Status:** ✅ All Issues Resolved

---

## Overview

This document summarizes **all Plotly.js integration issues** encountered during
dashboard development and their solutions.

---

## Timeline of Issues & Fixes

### Issue 1: Plotly.purge TypeError ✅ Fixed

**Error:**

```
TypeError: Cannot read properties of undefined (reading 'purge')
TypeError: Plotly.purge is not a function
```

**Root Cause:**

- Incorrect module export access in `PlotlyLazy.tsx`
- The factory function was receiving the module object instead of the Plotly
  object

**Solution:**

- Access `PlotlyModule.default` when passing to `react-plotly.js/factory`
- Changed from `factory.default(Plotly)` to
  `factory.default(PlotlyModule.default)`

**Documentation:** [PLOTLY_FIX.md](./PLOTLY_FIX.md)

---

### Issue 2: "require is not defined" ReferenceError ✅ Fixed

**Error:**

```
ReferenceError: require is not defined
```

**Root Cause:**

- `plotly.js` contains CommonJS code (`require()`, `module.exports`)
- When excluded from Vite's `optimizeDeps`, it wasn't being transformed to ES
  modules
- Browsers don't understand `require()` (Node.js API)

**Solution:**

- Added `plotly.js` to `optimizeDeps.include` in `vite.config.ts`
- Removed `plotly.js` from `optimizeDeps.exclude`
- Cleared Vite cache: `rm -rf node_modules/.vite`

**Documentation:** [PLOTLY_COMMONJS_FIX.md](./PLOTLY_COMMONJS_FIX.md)

---

### Issue 3: "exports is not defined" ReferenceError ✅ Fixed

**Error:**

```
ReferenceError: exports is not defined
```

**Root Cause:**

- Same as Issue 2 - CommonJS transformation was needed
- `react-plotly.js` was excluded from `optimizeDeps`

**Solution:**

- Added `react-plotly.js` to `optimizeDeps.include`
- This ensures both the wrapper and the library are pre-transformed

**Documentation:** [PLOTLY_COMMONJS_FIX.md](./PLOTLY_COMMONJS_FIX.md)

---

## Current Configuration

### vite.config.ts

```typescript
optimizeDeps: {
  // CRITICAL: Include all dependencies that need CommonJS -> ESM transformation
  include: ["date-fns", "react", "react-dom", "react-plotly.js", "plotly.js"],
  exclude: [
    "golden-layout",
    // Only exclude dependencies that are already pure ES modules
  ],
}
```

### PlotlyLazy.tsx

```typescript
const Plot = lazy(() =>
  import("plotly.js").then((PlotlyModule) =>
    import("react-plotly.js/factory").then((factory) => ({
      // CRITICAL: Access the default export, not the module object
      default: factory.default(PlotlyModule.default),
    }))
  )
);
```

---

## Verification ✅

**Confirmed working:**

1. ✅ Plotly charts render correctly
2. ✅ No "require is not defined" errors
3. ✅ No "exports is not defined" errors
4. ✅ No "Plotly.purge is not a function" errors
5. ✅ Lazy loading works as expected
6. ✅ Dev server starts quickly (after first pre-bundle)
7. ✅ Charts are interactive with full Plotly toolbar

**Screenshot:** `plotly_fix_confirmed.png` (shows both charts rendering)

---

## Key Lessons Learned

### 1. CommonJS vs ES Modules in Vite

**Problem:**

- Browsers only understand ES modules (`import`/`export`)
- Many npm packages still use CommonJS (`require`/`module.exports`)

**Solution:**

- Vite's `optimizeDeps` pre-transforms CommonJS to ES modules
- **Always include** dependencies with CommonJS in `optimizeDeps.include`
- Only **exclude** dependencies that are pure ES modules

### 2. Module Export Access

**Problem:**

- Dynamic imports return a module object with exports
- The actual export is in `module.default` for ES modules

**Solution:**

- When dynamically importing, check the export structure
- Access `.default` when needed: `PlotlyModule.default`

### 3. Lazy Loading Large Libraries

**Best Practice:**

```typescript
// ✅ GOOD: Lazy load large libraries
const Plot = lazy(() => import("./PlotlyComponent"));

// Include in optimizeDeps for CommonJS transformation
optimizeDeps: {
  include: ["plotly.js", "react-plotly.js"];
}
```

---

## Related Issues

### Build Performance

**Issue:** Builds hang when processing `plotly.js` (~3MB)

**Solution:** Build in `/scratch/` for faster I/O

- See [BUILD_SOLUTION.md](./BUILD_SOLUTION.md)

### CSP Violations

**Issue:** Content Security Policy blocking external scripts

**Solution:** Updated CSP meta tag in `index.html`

- See [PREVIEW_FIX.md](./PREVIEW_FIX.md)

---

## Preventing Future Issues

### When Adding New Dependencies

**Checklist:**

1. Check if the package uses CommonJS or ES modules
2. If CommonJS, add to `optimizeDeps.include`
3. Test lazy loading in the browser
4. Check console for module-related errors
5. Verify in both dev and production builds

### Testing Module Integration

```bash
# 1. Clear cache
rm -rf node_modules/.vite

# 2. Start dev server
npm run dev

# 3. Check browser console for errors
# Look for: require, exports, module, import errors

# 4. Test lazy-loaded components
# Navigate to pages that use the new dependency
```

---

## Files Changed

1. **`vite.config.ts`**
   - Updated `optimizeDeps.include` and `exclude`

2. **`src/components/PlotlyLazy.tsx`**
   - Fixed module export access

3. **`package.json`**
   - No changes needed (dependencies were already correct)

---

## Performance Impact

### Development Mode

- **First load:** +2-3 seconds (one-time pre-bundling)
- **Subsequent loads:** Fast (cached in `node_modules/.vite/`)
- **HMR:** No impact (Plotly is lazy-loaded)

### Production Build

- **Build time:** No significant impact
- **Bundle size:** ~3MB for Plotly chunk (separate, lazy-loaded)
- **Runtime:** Charts load only when needed

---

## References

- [Vite Dependency Pre-Bundling](https://vitejs.dev/guide/dep-pre-bundling.html)
- [Vite optimizeDeps](https://vitejs.dev/config/dep-optimization-options.html)
- [CommonJS vs ES Modules](https://nodejs.org/api/esm.html)
- [React.lazy()](https://react.dev/reference/react/lazy)
- [Plotly.js Documentation](https://plotly.com/javascript/)
- [react-plotly.js](https://github.com/plotly/react-plotly.js)

---

**Last Updated:** 2025-11-17  
**Status:** ✅ All Plotly Issues Resolved  
**Dashboard:** Fully functional with interactive charts
