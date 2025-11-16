# JS9 Performance Profiling - Ready for Use

## Status: ✅ Integration Complete

All performance monitoring tools have been successfully integrated. The system
is now ready to profile JS9 operations and identify the source of the 874ms
setTimeout handler violation.

## What Was Done

### 1. Performance Monitoring Infrastructure ✓

Created comprehensive monitoring tools:

- **Performance Profiler** - Tracks setTimeout handlers and JS9 operations
- **Promise Chunker** - Utilities for breaking up long-running operations
- **React Hook** - Easy integration for components

### 2. Integration into Components ✓

**SkyViewer.tsx:**

- Added `useJS9PerformanceMonitoring` hook
- Configured for development-only monitoring
- Logs slow operations (>100ms) to console

**useJS9ImageLoader.ts:**

- Wrapped JS9.Load calls in Promises
- Added `monitorPromiseChain` for both primary and fallback paths
- Tracks image loading performance

### 3. Documentation ✓

Created comprehensive guides:

- Issue analysis
- Usage guide
- Implementation summary
- Integration checklist
- This profiling guide

## How to Use

### Step 1: Start Development Server

```bash
cd /data/dsa110-contimg/frontend
npm run dev
```

### Step 2: Open Browser DevTools

1. Open the application in your browser
2. Open DevTools (F12 or Right-click → Inspect)
3. Go to Console tab
4. Look for: `JS9 Performance Profiler started`

### Step 3: Perform JS9 Operations

Navigate to a page with JS9 (SkyViewer) and:

1. **Load a FITS image**
   - Select an image from the browser
   - Watch console for performance warnings
   - Note the duration reported

2. **Try different operations:**
   - Load small images
   - Load large images
   - Zoom in/out
   - Pan the image
   - Switch between images

### Step 4: Analyze Console Output

You should see warnings like:

```
[JS9 Performance] Slow operation detected: setTimeout handler took 874.23ms
[SkyViewer] Slow JS9 operation: setTimeout handler took 874.23ms
[Promise Monitor] JS9.Load: js9Display took 874.23ms (threshold: 100ms)
```

**Key Information to Note:**

- Which operation triggered the delay
- Duration of the operation
- Image size/type (if applicable)
- Frequency (does it happen every time?)

### Step 5: Document Findings

Create a profiling log:

| Operation  | Duration | Image Size | Frequency | Notes      |
| ---------- | -------- | ---------- | --------- | ---------- |
| Load image | 874ms    | Large FITS | Always    | **ISSUE**  |
| Load image | 120ms    | Small FITS | Always    | Acceptable |
| Zoom       | 45ms     | Any        | Always    | Acceptable |

## Expected Findings

Based on the original error (`setTimeout handler took 874ms`), you should see:

1. **Image Loading Operations:**
   - JS9.Load calls taking >100ms
   - Promise resolution chains blocking the event loop
   - Large FITS files taking longer

2. **setTimeout Handlers:**
   - jQuery Deferred promise resolution
   - Multiple promise handlers executing synchronously
   - DOM manipulation in promise callbacks

## Next Steps After Profiling

### If Image Loading is Slow

**Option 1: Chunked Processing**

```typescript
import { processArrayInChunks } from "../../../utils/js9/promiseChunker";

// If loading multiple images
const results = await processArrayInChunks(
  imagePaths,
  (path) => js9Service.loadImage(path),
  5, // chunk size
  10 // delay between chunks (ms)
);
```

**Option 2: Defer Non-Critical Operations**

```typescript
// Move non-critical callbacks to requestIdleCallback
if (window.requestIdleCallback) {
  window.requestIdleCallback(() => {
    // Non-critical operations here
  });
}
```

### If Promise Chains are Long

**Option 1: Break into Smaller Promises**

```typescript
// Instead of one long chain, break into steps
const step1 = await loadImage();
const step2 = await processImage();
const step3 = await displayImage();
```

**Option 2: Use Chunked Promise**

```typescript
import { chunkedPromise } from "../../../utils/js9/promiseChunker";

const optimizedLoad = chunkedPromise(js9Service.loadImage, {
  chunkTimeMs: 5,
  maxChunks: 100,
});
```

## Profiling Checklist

- [ ] Development server running
- [ ] Browser DevTools open
- [ ] Console shows profiler started
- [ ] Loaded a FITS image
- [ ] Observed performance warnings
- [ ] Documented slow operations
- [ ] Identified patterns (size, type, frequency)
- [ ] Ready to apply optimizations

## Troubleshooting

### No Warnings Appearing

1. **Check NODE_ENV:**

   ```javascript
   console.log(process.env.NODE_ENV); // Should be "development"
   ```

2. **Verify Profiler Started:**
   - Look for: `JS9 Performance Profiler started` in console
   - If missing, check hook is being called

3. **Check Operations:**
   - Ensure JS9 operations are actually being performed
   - Try loading an image explicitly

4. **Check Thresholds:**
   - Default threshold is 50ms for setTimeout
   - Default threshold is 100ms for promises
   - Operations below threshold won't trigger warnings

### Too Many Warnings

1. **Increase Threshold:**

   ```typescript
   useJS9PerformanceMonitoring({
     slowThresholdMs: 200, // Only warn for >200ms
   });
   ```

2. **Filter Operations:**
   ```typescript
   onSlowOperation: (entry) => {
     // Only log specific operations
     if (entry.operation.includes("JS9.Load")) {
       console.warn(entry);
     }
   };
   ```

## Performance Budget

Based on browser recommendations:

- **Acceptable:** < 50ms
- **Warning:** 50-100ms
- **Critical:** > 100ms (causes violations)
- **Target:** < 200ms for image loads (user-perceptible delay)

## Files to Monitor

When profiling, pay attention to:

1. **Console Output:**
   - `[JS9 Performance]` - Profiler warnings
   - `[SkyViewer]` - Component-level warnings
   - `[Promise Monitor]` - Promise chain warnings

2. **Browser Performance Tab:**
   - Long tasks (red blocks)
   - setTimeout handlers
   - Promise resolution

3. **Network Tab:**
   - Image load times
   - File sizes
   - Transfer times

## Success Criteria

Profiling is successful when:

1. ✅ Slow operations are identified
2. ✅ Patterns are documented (size, type, frequency)
3. ✅ Root cause is understood (promise chains, DOM manipulation, etc.)
4. ✅ Optimization strategy is defined
5. ✅ Ready to apply chunking/optimization utilities

## Related Files

- `frontend/src/components/Sky/SkyViewer.tsx` - Main component with monitoring
- `frontend/src/components/Sky/hooks/useJS9ImageLoader.ts` - Image loader with
  promise monitoring
- `frontend/src/utils/js9/performanceProfiler.ts` - Profiler implementation
- `frontend/src/utils/js9/promiseChunker.ts` - Optimization utilities

## Support

If you encounter issues:

1. Check console for error messages
2. Verify all imports are correct
3. Check that JS9 is properly initialized
4. Review the monitoring guide: `JS9_PERFORMANCE_MONITORING_GUIDE.md`

---

**Ready to Profile!** Start the dev server and begin loading images to see
performance data in the console.
