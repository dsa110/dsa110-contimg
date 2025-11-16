# JS9 Performance - Next Steps Checklist

## Immediate Actions Required

### 1. Integrate Performance Monitoring ✓ (Code Ready)

**File:** `frontend/src/components/Sky/SkyViewer.tsx`

Add the performance monitoring hook:

```typescript
import { useJS9PerformanceMonitoring } from './hooks/useJS9PerformanceMonitoring';

export function SkyViewer({ ... }) {
  // Add this hook
  useJS9PerformanceMonitoring({
    enabled: process.env.NODE_ENV === 'development',
    slowThresholdMs: 50,
    autoLog: true
  });

  // ... existing code
}
```

**Status:** Code ready, needs integration

### 2. Test Performance Profiler

**Steps:**

1. Start the development server
2. Navigate to a page with JS9 (SkyViewer)
3. Open browser console
4. Load a FITS image
5. Check for `[JS9 Performance]` warnings
6. Verify profiler is tracking operations

**Expected Output:**

```
[JS9 Performance] Slow operation detected: setTimeout handler took 874.23ms
```

### 3. Profile Specific Operations

**Goal:** Identify which JS9 operations trigger the 874ms delay

**Steps:**

1. Enable profiler (already done if hook is added)
2. Perform these operations one at a time:
   - Load a small FITS image
   - Load a large FITS image
   - Zoom in/out
   - Pan the image
   - Switch between images
   - Add overlays (if applicable)
3. Note which operations trigger slow warnings
4. Document findings

**Documentation Template:**

```markdown
## Profiling Results

| Operation        | Duration | Frequency | Notes      |
| ---------------- | -------- | --------- | ---------- |
| Load small image | 120ms    | Always    | Acceptable |
| Load large image | 874ms    | Always    | **ISSUE**  |
| Zoom             | 45ms     | Always    | Acceptable |
```

## Short-term Optimizations

### 4. Add Monitoring to Image Loader

**File:** `frontend/src/components/Sky/hooks/useJS9ImageLoader.ts`

Wrap JS9.Load calls with monitoring:

```typescript
import { monitorPromiseChain } from "../../../utils/js9/promiseChunker";

// Around line 250, wrap the loadImage call:
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

monitorPromiseChain(loadPromise, `JS9.Load: ${displayId}`, 100);
```

### 5. Optimize Based on Profiling Results

**If image loading is slow:**

- Consider using `processArrayInChunks` if loading multiple images
- Add delays between operations
- Defer non-critical callbacks

**If promise chains are long:**

- Break into smaller promises
- Use `chunkedPromise` wrapper
- Consider using `requestIdleCallback` for non-critical work

## Medium-term Improvements

### 6. Add Performance Metrics Dashboard (Optional)

Create a debug panel to show:

- Current slow operations
- Performance summary
- Export performance data

**File:** `frontend/src/components/Sky/JS9PerformancePanel.tsx` (new)

### 7. Set Performance Budgets

Define acceptable thresholds:

- Image load: < 200ms
- Zoom/pan: < 50ms
- Overlay operations: < 100ms

Enforce in tests or CI/CD.

### 8. Production Monitoring (Optional)

If needed, add opt-in production monitoring:

- Feature flag: `VITE_ENABLE_JS9_PERF_MONITORING`
- Send metrics to analytics
- Track performance trends

## Long-term Considerations

### 9. Evaluate JS9/jQuery Updates

- Check for newer JS9 versions
- Check for jQuery updates that might improve promise handling
- Consider migration path if updates available

### 10. Consider Alternative Approaches

If performance issues persist:

- Implement custom promise resolution with chunking
- Migrate to native Promises where possible
- Consider alternative FITS viewers if JS9 cannot be optimized

## Testing Checklist

- [ ] Performance monitoring hook integrated
- [ ] Profiler starts automatically in development
- [ ] Console warnings appear for slow operations
- [ ] Profiling data can be exported
- [ ] Specific operations identified as slow
- [ ] Optimizations applied based on findings
- [ ] Performance improvements verified
- [ ] No regressions in functionality

## Success Criteria

1. **Monitoring:** Profiler successfully identifies slow operations
2. **Documentation:** Slow operations are documented with durations
3. **Optimization:** At least one slow operation is optimized
4. **Verification:** Performance violations reduced or eliminated
5. **User Experience:** UI remains responsive during JS9 operations

## Files to Modify

1. `frontend/src/components/Sky/SkyViewer.tsx` - Add monitoring hook
2. `frontend/src/components/Sky/hooks/useJS9ImageLoader.ts` - Add promise
   monitoring
3. (Optional) Create performance dashboard component

## Files Already Created

1. `frontend/src/utils/js9/performanceProfiler.ts` ✓
2. `frontend/src/utils/js9/promiseChunker.ts` ✓
3. `frontend/src/components/Sky/hooks/useJS9PerformanceMonitoring.ts` ✓
4. `frontend/src/utils/js9/index.ts` - Updated with exports ✓
5. `docs/JS9_SETTIMEOUT_PERFORMANCE_ISSUE.md` ✓
6. `docs/JS9_PERFORMANCE_MONITORING_GUIDE.md` ✓
7. `docs/JS9_PERFORMANCE_IMPLEMENTATION_SUMMARY.md` ✓
8. `docs/JS9_PERFORMANCE_NEXT_STEPS.md` - This file ✓

## Questions to Answer

1. Which specific JS9 operations trigger the 874ms delay?
2. Is it consistent across different image sizes?
3. Does it occur with specific image types or formats?
4. Can we optimize the slow operations without breaking functionality?
5. Are there workarounds (e.g., loading indicators, progressive loading)?

## Notes

- All code is ready for integration
- Profiler is disabled by default in production
- Can be enabled via environment variable or feature flag
- Performance data can be exported for analysis
- No breaking changes to existing functionality
