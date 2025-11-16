# JS9 Performance Monitoring and Optimization Guide

## Overview

This guide explains how to use the performance monitoring and optimization tools
created to address the `setTimeout` handler performance violation in JS9
operations.

## Problem

JS9 uses jQuery's Deferred/promise system internally. When images are loaded or
operations are performed, promise chains execute synchronously within
`setTimeout` callbacks, causing:

- UI freezes for extended periods (e.g., 874ms)
- Browser performance violations
- Poor user experience

## Solution Components

### 1. Performance Profiler (`performanceProfiler.ts`)

Monitors JS9 operations and `setTimeout` handlers to identify slow operations.

**Features:**

- Automatically patches `setTimeout` to measure handler execution time
- Monitors `JS9.Load` calls
- Tracks operations exceeding configurable thresholds
- Provides summary statistics and export functionality

**Usage:**

```typescript
import { js9PerformanceProfiler } from "../utils/js9/performanceProfiler";

// Start monitoring
js9PerformanceProfiler.startMonitoring();

// Get slow operations
const slowOps = js9PerformanceProfiler.getSlowOperations(100); // >100ms

// Get summary
const summary = js9PerformanceProfiler.getSummary();
console.log(summary);

// Export data
const json = js9PerformanceProfiler.export();

// Stop monitoring
js9PerformanceProfiler.stopMonitoring();
```

### 2. Promise Chunker (`promiseChunker.ts`)

Utilities to break up long-running operations into smaller chunks.

**Features:**

- `chunkedExecution`: Execute work in time-sliced chunks
- `processArrayInChunks`: Process arrays without blocking
- `chunkedPromise`: Wrap promises to execute in chunks
- `monitorPromiseChain`: Monitor and warn about slow promises

**Usage:**

```typescript
import {
  chunkedExecution,
  processArrayInChunks,
  monitorPromiseChain,
} from "../utils/js9/promiseChunker";

// Monitor a promise chain
const promise = js9Service.loadImage(imagePath, options);
const monitoredPromise = monitorPromiseChain(
  promise,
  "JS9.Load",
  50 // threshold in ms
);

// Process an array in chunks
const results = await processArrayInChunks(
  imagePaths,
  (path) => js9Service.loadImage(path),
  10, // chunk size
  5 // delay between chunks (ms)
);
```

### 3. React Hook (`useJS9PerformanceMonitoring`)

Easy integration for React components.

**Usage:**

```typescript
import { useJS9PerformanceMonitoring } from "./hooks/useJS9PerformanceMonitoring";

function SkyViewer() {
  const {
    getSummary,
    getSlowOperations,
    export: exportData,
  } = useJS9PerformanceMonitoring({
    enabled: true,
    slowThresholdMs: 50,
    onSlowOperation: (entry) => {
      console.warn("Slow operation:", entry);
    },
    autoLog: true,
  });

  // Component code...
}
```

## Integration Steps

### Step 1: Add Performance Monitoring to SkyViewer

Update `SkyViewer.tsx` to include performance monitoring:

```typescript
import { useJS9PerformanceMonitoring } from './hooks/useJS9PerformanceMonitoring';

export function SkyViewer({ ... }) {
  // Add performance monitoring (only in development)
  useJS9PerformanceMonitoring({
    enabled: process.env.NODE_ENV === 'development',
    slowThresholdMs: 50,
    autoLog: true
  });

  // ... rest of component
}
```

### Step 2: Monitor JS9.Load Operations

Update `useJS9ImageLoader.ts` to monitor image loading:

```typescript
import { monitorPromiseChain } from "../../../utils/js9/promiseChunker";

// In the loadImage call:
const loadPromise = new Promise<void>((resolve, reject) => {
  js9Service.loadImage(imageUrlWithCacheBuster, {
    divID: displayId,
    onload: (im) => {
      resolve();
      // ... existing onload code
    },
    onerror: (err) => {
      reject(err);
      // ... existing onerror code
    },
  });
});

// Monitor the promise
monitorPromiseChain(loadPromise, `JS9.Load: ${displayId}`, 100);
```

### Step 3: Profile Specific Operations

To identify which operations are slow:

1. **Enable profiler in development:**

   ```typescript
   // In App.tsx or main entry point
   if (process.env.NODE_ENV === "development") {
     import("./utils/js9/performanceProfiler").then(
       ({ js9PerformanceProfiler }) => {
         js9PerformanceProfiler.startMonitoring();

         // Log summary every 10 seconds
         setInterval(() => {
           const summary = js9PerformanceProfiler.getSummary();
           if (summary.slowOperations > 0) {
             console.log("JS9 Performance Summary:", summary);
           }
         }, 10000);
       }
     );
   }
   ```

2. **Export performance data:**
   ```typescript
   // In browser console or debug panel
   const profiler = window.js9PerformanceProfiler; // if exposed globally
   const data = profiler.export();
   console.log(data);
   // Copy and analyze the JSON
   ```

### Step 4: Optimize Based on Findings

Once you identify slow operations:

1. **For large image loads:**
   - Break up image processing into chunks
   - Use `requestIdleCallback` for non-critical operations
   - Defer non-essential callbacks

2. **For multiple operations:**
   - Use `processArrayInChunks` to process images sequentially
   - Add delays between operations
   - Batch DOM updates

3. **For promise chains:**
   - Wrap with `monitorPromiseChain` to identify bottlenecks
   - Consider breaking chains into smaller promises
   - Use `chunkedPromise` for long-running operations

## Browser DevTools Integration

### Chrome DevTools Performance Tab

1. Open DevTools → Performance tab
2. Click Record
3. Perform JS9 operations (load images, zoom, etc.)
4. Stop recording
5. Look for:
   - Long tasks (red blocks)
   - `setTimeout` handlers taking >50ms
   - Promise resolution chains

### Console Monitoring

The profiler automatically logs warnings for slow operations:

```
[JS9 Performance] Slow operation detected: setTimeout handler took 874.23ms
```

## Recommended Thresholds

- **Warning threshold**: 50ms (operations taking longer are logged)
- **Critical threshold**: 100ms (operations taking longer should be optimized)
- **Violation threshold**: 200ms+ (causes browser performance violations)

## Production Considerations

1. **Disable in production** (or use minimal monitoring):

   ```typescript
   const enabled =
     process.env.NODE_ENV === "development" ||
     localStorage.getItem("js9-perf-monitoring") === "true";
   ```

2. **Use feature flags:**

   ```typescript
   const ENABLE_PERFORMANCE_MONITORING =
     import.meta.env.VITE_ENABLE_JS9_PERF_MONITORING === "true";
   ```

3. **Remote monitoring** (optional):
   - Send performance data to analytics
   - Track slow operations in production
   - Alert on performance degradation

## Next Steps

1. **Immediate**: Add `useJS9PerformanceMonitoring` to `SkyViewer.tsx`
2. **Short-term**: Profile during typical usage to identify slow operations
3. **Medium-term**: Optimize identified bottlenecks using chunking utilities
4. **Long-term**: Consider updating JS9/jQuery or implementing custom promise
   resolution

## Related Files

- `/frontend/src/utils/js9/performanceProfiler.ts` - Performance monitoring
- `/frontend/src/utils/js9/promiseChunker.ts` - Chunking utilities
- `/frontend/src/components/Sky/hooks/useJS9PerformanceMonitoring.ts` - React
  hook
- `/docs/JS9_SETTIMEOUT_PERFORMANCE_ISSUE.md` - Original issue analysis
