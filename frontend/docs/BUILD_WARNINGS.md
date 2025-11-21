# Build Warnings Explained

This document explains the warnings that appear during the build process and
whether they need to be addressed.

## Expected Warnings (No Action Required)

### 1. Node.js Version Warning

```
npm warn EBADENGINE Unsupported engine {
  package: '@vitejs/plugin-react@5.1.1',
  required: { node: '^20.19.0 || >=22.12.0' },
  current: { node: 'v22.6.0', npm: '10.8.2' }
}
```

**Status:** ⚠️ Warning only - build still works  
**Explanation:** The casa6 Node.js environment uses v22.6.0, which is slightly
older than the recommended version (>=22.12.0) for `@vitejs/plugin-react@5.1.1`.
However, the build completes successfully and the plugin functions correctly.

**Action:** None required. This is a version recommendation, not a hard
requirement.

### 2. Golden-Layout Image Path Warnings

```
/ui/golden-layout/img/lm_close_white.png referenced in ... didn't resolve at build time,
it will remain unchanged to be resolved at runtime
```

**Status:** ✅ Suppressed by plugin - paths work correctly at runtime  
**Explanation:** These CSS background-image URLs use the `/ui/` prefix which
matches the production `base` configuration. Vite can't verify these paths exist
at build time because they reference assets in the `public/` folder, but they
resolve correctly at runtime.

**Action:** None required. A Vite plugin (`suppressPublicAssetWarnings`) now
suppresses these warnings automatically. The images are in
`public/golden-layout/img/` and work correctly at runtime.

### 3. Eval Usage Warning

```
Use of eval in "node_modules/@protobufjs/inquire/index.js" is strongly discouraged
```

**Status:** ⚠️ Dependency issue - cannot be fixed directly  
**Explanation:** This warning comes from the `@protobufjs/inquire` dependency,
which is used by protobuf libraries. This is a known issue in the dependency and
doesn't affect functionality.

**Action:** None required. This is a security warning from a third-party
dependency.

### 4. Large Chunk Warning

```
(!) Some chunks are larger than 2000 kB after minification.
```

**Status:** ✅ Expected - plotly-vendor is intentionally large  
**Explanation:** The `plotly-vendor` chunk is ~4.8MB (gzipped: 1.4MB) because
Plotly.js is a large visualization library. This is expected and acceptable
because:

- Plotly.js is lazy-loaded (only loaded when needed)
- The chunk is properly code-split
- Gzip compression reduces it to 1.4MB

**Action:** None required. The `chunkSizeWarningLimit` has been increased to
5000 kB to accommodate this.

## Fixed Issues

### ✅ Duplicate Sourcemap Key

**Status:** Fixed  
**Issue:** `sourcemap` was defined twice in `vite.config.ts` (lines 89 and
138).  
**Fix:** Removed the duplicate definition on line 89, kept the more specific one
on line 138.

## Summary

All warnings are either:

- Expected behavior (golden-layout paths, large chunks)
- Dependency issues that can't be fixed directly (eval warning)
- Version recommendations that don't affect functionality (Node.js version)

The build completes successfully with all warnings, and the application
functions correctly.
