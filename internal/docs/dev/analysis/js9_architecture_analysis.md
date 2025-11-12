# JS9 Integration Architecture Analysis
**Date:** 2025-01-12  
**Purpose:** Deep technical analysis of JS9 integration patterns, problems, and improvement opportunities

## Executive Summary

**Core Problem:** JS9 is treated as global singleton with no abstraction layer, causing:
- 194 direct API calls across Sky components
- 45+ redundant `displays.find()` queries (same pattern repeated)
- 33 polling intervals (anti-pattern: should use events)
- 19 components prop-drilling `displayId`
- No centralized state management for display/image lifecycle

**Critical Finding:** Components use BOTH events AND polling simultaneously (ImageStatisticsPlugin listens to `displayimage` event BUT ALSO polls every 500ms). This is redundant and wasteful.

## JS9 API Usage Patterns

### Most Used APIs (by frequency)
1. **`displays.find()`** - 45 instances
   - Pattern: `window.JS9.displays?.find((d: any) => { const divId = d.id || d.display || d.divID; return divId === displayId; })`
   - Problem: Same 4-line pattern repeated 45 times, inconsistent property access (`id` vs `display` vs `divID`)

2. **`Load()`** - 16 instances
   - Used for: Loading FITS images into displays
   - Pattern: `window.JS9.Load(imagePath, { divID: displayId })`
   - Problem: No error handling wrapper, no retry logic, no loading state coordination

3. **`AddEventListener/RemoveEventListener`** - 14 add, 12 remove
   - Events used: `displayimage`, `imageLoad`, `imageDisplay`, `zoom`, `pan`, `colormap`
   - Problem: Inconsistent cleanup (some components don't remove listeners), no centralized event bus

4. **`GetImageData()`** - 6 instances
   - Used by: ImageStatisticsPlugin, PhotometryPlugin, QuickAnalysisPanel
   - Problem: No caching, called repeatedly for same image

5. **`GetWCS()`** - 8 instances
   - Used by: WCSDisplay, ImageStatisticsPlugin
   - Problem: No memoization, recalculated on every cursor move

6. **`GetVal()`** - 8 instances
   - Used by: WCSDisplay, ImageMetadata (cursor position)
   - Problem: Called on every mouse move, no throttling

### Display Management APIs
- `AddDivs()` - 2 instances (initialization only)
- `SetDisplay()` - 6 instances (switching images between displays)
- `CloseImage()` - 2 instances (cleanup)
- `ResizeDisplay()` - 4 instances (manual resize triggers)

### Image Analysis APIs
- `GetRegions()` - 8 instances (photometry, region tools)
- `GetFITSheader()` - 2 instances (metadata)
- `PixToWCS()` - 2 instances (coordinate conversion)

### Display Control APIs
- `SetZoom()` - 4 instances
- `GetZoom()` - 4 instances
- `SetColormap()` - 2 instances
- `GetColormap()` - 1 instance
- `SetScale()` - 1 instance
- `GetScale()` - 1 instance
- `SetPan()` - 1 instance

### Advanced Features
- `SyncImages()` - 2 instances (MultiImageCompare)
- `BlendImage()` - 2 instances (MultiImageCompare)
- `AddOverlay()` - 13 instances (catalog overlays, contours)
- `RegisterPlugin()` - 2 instances (custom plugins)

## Component Architecture

### Display ID Propagation
**19 components** receive `displayId` prop:
- SkyViewPage → SkyViewer (`displayId="skyViewDisplay"`)
- SkyViewPage → 8 plugins/controls (all get `displayId="skyViewDisplay"`)
- MultiImageCompare → 2 SkyViewers (`displayId={displayAId}`, `displayId={displayBId}`)

**Pattern:** Hardcoded string `"skyViewDisplay"` repeated 9 times in SkyViewPage.tsx

**Problem:** No single source of truth. If displayId changes, must update 9 places.

### State Management Patterns

#### SkyViewer.tsx (965 lines - TOO LARGE)
**State variables:**
- `initialized` (boolean) - JS9 ready?
- `loading` (boolean) - Image loading?
- `error` (string | null) - Error state
- `imageLoadedRef` (ref) - Image loaded flag (why ref vs state?)

**Problem:** `imageLoadedRef` used instead of state - breaks React reactivity. Other components can't subscribe to image load status.

**Effects:** 8 useEffect/useLayoutEffect hooks
- Initialization (waits for JS9)
- Image loading (watches imagePath changes)
- Display restoration (prevents React from clearing JS9 DOM)
- Resize handling (window resize)
- Cleanup (removes listeners)

**Problem:** Complex interdependencies between effects. Hard to reason about execution order.

#### ImageStatisticsPlugin.tsx
**State:**
- `stats` (ImageStatistics | null)
- `loading` (boolean)
- `error` (string | null)
- `lastImageIdRef` (ref) - tracks image ID changes

**Pattern:** Uses BOTH events AND polling
```typescript
// Event listener
window.JS9.AddEventListener('displayimage', handleImageDisplay);
window.JS9.AddEventListener('zoom', handlePanZoom);
window.JS9.AddEventListener('pan', handlePanZoom);

// BUT ALSO polls every 500ms
const pollInterval = setInterval(() => {
  const display = window.JS9.displays?.find(...);
  if (display?.im) {
    const imageId = display.im.id;
    if (lastImageIdRef.current !== imageId) {
      // Update stats
    }
  }
}, 500);
```

**Problem:** Redundant. Events should be sufficient. Polling wastes CPU and creates race conditions.

#### Other Plugins
- **PhotometryPlugin:** Polls every 500ms for region changes
- **CASAnalysisPlugin:** Polls for JS9 availability (100ms interval)
- **QuickAnalysisPanel:** Polls for image changes (1000ms interval)
- **ImageControls:** Polls for zoom level (500ms interval)
- **ImageMetadata:** Polls for cursor info (100ms interval)

**Pattern:** Every plugin independently polls JS9 state.

## Initialization Flow

### JS9 Loading (index.html)
1. Load `js9support.js` (sets up `window.JS9` object)
2. Load `js9.min.js` as text
3. Patch hardcoded paths in source (`PREFSFILE`, `WORKERFILE`)
4. Execute patched source
5. Configure paths via `JS9.SetOptions()` or `JS9.opts`

**Problem:** Complex, fragile. If patching fails, fallback loads unpatched version (will break).

### Component Initialization
**Pattern:** Every component checks `if (!window.JS9)` then polls:
```typescript
const checkJS9 = setInterval(() => {
  if (window.JS9 && typeof window.JS9.Load === 'function') {
    clearInterval(checkJS9);
    // Initialize
  }
}, 100);
```

**Problem:** 9 components all polling simultaneously. Race condition: which one initializes first?

**SkyViewer initialization:**
1. Check if JS9 loaded (`typeof window.JS9.Load === 'function'`)
2. Check if display exists (`displays.find()`)
3. If exists, set `initialized = true`
4. If not, wait for JS9, then call `JS9.AddDivs(displayId)`
5. Configure options (`SetOptions`, `opts`)
6. Set up resize handlers

**Problem:** No coordination with other components. Each component independently queries `displays.find()`.

## Event Handling Patterns

### Events Used
- `displayimage` - Image displayed in a display
- `imageLoad` - Image loaded (before display)
- `imageDisplay` - Image displayed (after load)
- `zoom` - Zoom level changed
- `pan` - Pan position changed
- `colormap` - Colormap changed

### Event Listener Management
**Pattern:** Components add listeners in `useEffect`, remove in cleanup
```typescript
useEffect(() => {
  if (typeof window.JS9.AddEventListener === 'function') {
    window.JS9.AddEventListener('displayimage', handler);
  }
  return () => {
    if (typeof window.JS9?.RemoveEventListener === 'function') {
      window.JS9.RemoveEventListener('displayimage', handler);
    }
  };
}, [deps]);
```

**Problems:**
1. Type checking every time (`typeof window.JS9.AddEventListener === 'function'`)
2. No guarantee listeners are removed (if component unmounts during JS9 init)
3. No centralized event bus - each component manages own listeners
4. Event handlers often recreated on every render (missing `useCallback`)

### Event vs Polling Redundancy
**ImageStatisticsPlugin:**
- Listens to `displayimage` event (should trigger on image change)
- BUT ALSO polls every 500ms to check `display.im.id` (redundant!)

**Why?** Likely because events don't fire reliably, or developer didn't trust events.

## State Synchronization Issues

### Display Finding Pattern
**45 instances** of this pattern:
```typescript
const display = window.JS9.displays?.find((d: any) => {
  const divId = d.id || d.display || d.divID;
  return divId === displayId;
});
```

**Problems:**
1. JS9 uses inconsistent property names (`id` vs `display` vs `divID`)
2. No type safety (`d: any`)
3. No caching - same query repeated multiple times per render
4. No centralized lookup function

### Image Load State
**SkyViewer** uses `imageLoadedRef` (ref, not state):
```typescript
const imageLoadedRef = useRef(false);
// ...
imageLoadedRef.current = true;
```

**Problem:** Other components can't react to image load. They must poll or listen to events.

**Components that need image load state:**
- ImageStatisticsPlugin (waits for image to calculate stats)
- PhotometryPlugin (needs image for photometry)
- WCSDisplay (needs image for WCS)
- ImageMetadata (needs image for metadata)
- QuickAnalysisPanel (needs image for analysis)

**Current solution:** Each component independently checks `display?.im` via polling.

## Performance Issues

### Polling Overhead
**33 polling intervals** running simultaneously:
- ImageStatisticsPlugin: 500ms
- PhotometryPlugin: 500ms
- CASAnalysisPlugin: 100ms (JS9 check) + 500ms (plugin init)
- QuickAnalysisPanel: 1000ms
- ImageControls: 500ms (zoom) + 500ms (menubar hide)
- ImageMetadata: 100ms (cursor)
- WCSDisplay: 1000ms (image check) + 100ms (WCS update)

**Impact:** Even when idle, 7+ intervals running. Wastes CPU, drains battery on mobile.

### Redundant API Calls
- `GetImageData()` called multiple times for same image (no caching)
- `GetWCS()` called on every mouse move (no throttling)
- `GetVal()` called on every mouse move (no throttling)
- `displays.find()` called 45+ times (no memoization)

### Memory Leaks Risk
**Potential leaks:**
1. Intervals not cleared if component unmounts during JS9 init
2. Event listeners not removed if JS9 unavailable during cleanup
3. Timeout refs not cleared in all code paths

## Testing Gaps

**Only 5 test files** in Sky components:
- ImageStatisticsPlugin.test.tsx
- PhotometryPlugin.test.tsx
- CASAnalysisPlugin.test.tsx
- ContourOverlay.test.tsx
- (Missing tests for SkyViewer, ImageControls, WCSDisplay, etc.)

**Problem:** Hard to test because:
1. `window.JS9` is global - can't easily mock
2. Components tightly coupled to JS9 API
3. No abstraction layer to inject test doubles

## Critical Design Flaws

### 1. No Abstraction Layer
**Problem:** Direct `window.JS9` access everywhere. Can't:
- Mock for testing
- Swap implementations
- Add cross-cutting concerns (logging, metrics, error recovery)
- Type-check API calls

**Impact:** High. Every JS9 API change requires updating 19+ files.

### 2. No Centralized State
**Problem:** Each component independently tracks:
- JS9 availability
- Display existence
- Image load status
- Current image ID

**Impact:** Components can get out of sync. Race conditions.

### 3. Prop Drilling
**Problem:** `displayId` passed through 19 components. No context.

**Impact:** Medium. Easy to pass wrong ID, hard to add new plugins.

### 4. Polling Anti-Pattern
**Problem:** 33 intervals polling JS9 state instead of using events.

**Impact:** High. Wastes CPU, creates race conditions, drains battery.

### 5. Redundant Event + Polling
**Problem:** Components use BOTH events AND polling (ImageStatisticsPlugin).

**Impact:** Medium. Wastes resources, suggests events don't work reliably.

### 6. Inconsistent Property Access
**Problem:** JS9 uses `id`, `display`, `divID` inconsistently. Code checks all three.

**Impact:** Low. Works but ugly. Suggests JS9 API is inconsistent.

### 7. No Error Recovery
**Problem:** If JS9.Load fails, no retry. If display not found, no fallback.

**Impact:** Medium. Users see errors with no recovery path.

### 8. SkyViewer Too Large
**Problem:** 965 lines, 8 effects, multiple responsibilities.

**Impact:** High. Hard to understand, modify, test.

## Improvement Opportunities

### High-Value, Low-Risk
1. **Extract `displays.find()` to utility function**
   - Single source of truth for display lookup
   - Type-safe wrapper
   - Memoization possible

2. **Create JS9 Context Provider**
   - Centralize JS9 availability state
   - Provide `displayId` via context (eliminate prop drilling)
   - Single initialization point

3. **Replace polling with events**
   - ImageStatisticsPlugin: Remove 500ms poll, rely on `displayimage` event
   - ImageControls: Listen to `zoom` event instead of polling
   - ImageMetadata: Throttle cursor updates, use events if available

4. **Throttle/debounce expensive calls**
   - `GetWCS()`: Throttle to 100ms
   - `GetVal()`: Throttle to 50ms
   - `GetImageData()`: Cache results

### Medium-Value, Medium-Risk
5. **Create JS9 Service Abstraction**
   - Wrap JS9 API in typed interface
   - Add error handling, retry logic
   - Enable mocking for tests

6. **Split SkyViewer into smaller components**
   - JS9Initializer (handles init)
   - JS9ImageLoader (handles loading)
   - JS9DisplayContainer (handles rendering)
   - JS9ResizeHandler (handles resize)

7. **Centralize image load state**
   - Use Zustand store or Context for image load status
   - Components subscribe instead of polling

### High-Value, High-Risk
8. **Full refactor to event-driven architecture**
   - Remove all polling
   - Centralize event bus
   - State management via Zustand/Context
   - Complete abstraction layer

## Migration Strategy

### Phase 1: Low-Risk Utilities (1-2 days)
- Extract `findDisplay()` utility
- Create JS9 Context (backward compatible)
- Add throttling utilities

### Phase 2: Replace Polling (3-5 days)
- Remove polling from ImageStatisticsPlugin
- Remove polling from ImageControls
- Add event listeners where missing
- Test thoroughly

### Phase 3: Abstraction Layer (1 week)
- Create JS9Service interface
- Wrap common APIs
- Migrate components incrementally
- Keep `window.JS9` access as fallback

### Phase 4: State Management (1 week)
- Create Zustand store for display state
- Migrate components to use store
- Remove redundant state tracking

### Phase 5: Component Split (1 week)
- Split SkyViewer into smaller components
- Refactor initialization flow
- Improve test coverage

## Key Metrics

- **194** direct JS9 API calls
- **45** `displays.find()` queries
- **33** polling intervals
- **19** components prop-drilling `displayId`
- **8** useEffect hooks in SkyViewer
- **965** lines in SkyViewer.tsx
- **5** test files (incomplete coverage)
- **9** hardcoded `"skyViewDisplay"` strings

## Critical Code Patterns

### Redundant Event + Polling (ImageStatisticsPlugin)
**Pattern:**
```typescript
// Event listener (should be sufficient)
window.JS9.AddEventListener('displayimage', handleImageDisplay);
window.JS9.AddEventListener('zoom', handlePanZoom);
window.JS9.AddEventListener('pan', handlePanZoom);

// BUT ALSO polls every 500ms (redundant!)
const pollInterval = setInterval(() => {
  const display = window.JS9.displays?.find(...);
  if (display?.im) {
    const imageId = display.im.id;
    if (lastImageIdRef.current !== imageId) {
      // Update stats
    }
  }
}, 500);
```

**Why?** Likely defensive programming - developer didn't trust events. But this wastes CPU.

**Fix:** Remove polling, rely on events. If events don't fire, that's a JS9 bug we should fix, not work around.

### Display Finding Pattern (45 instances)
**Pattern:**
```typescript
const display = window.JS9.displays?.find((d: any) => {
  const divId = d.id || d.display || d.divID;
  return divId === displayId;
});
```

**Problems:**
- JS9 API inconsistency (`id` vs `display` vs `divID`)
- No type safety (`d: any`)
- No memoization (called multiple times per render)
- Same 4-line pattern repeated 45 times

**Fix:** Extract to `findDisplay(displayId: string): JS9Display | null` utility with memoization.

### Initialization Race Conditions
**Pattern:** 9 components all check `if (!window.JS9)` then poll:
```typescript
const checkJS9 = setInterval(() => {
  if (window.JS9 && typeof window.JS9.Load === 'function') {
    clearInterval(checkJS9);
    initialize();
  }
}, 100);
```

**Problem:** All 9 components polling simultaneously. Which one initializes first? Race condition.

**Fix:** Single initialization point (JS9 Context Provider). Other components subscribe to initialization state.

### Image Load State (Ref vs State)
**SkyViewer** uses `imageLoadedRef` (ref):
```typescript
const imageLoadedRef = useRef(false);
imageLoadedRef.current = true; // Not reactive!
```

**Problem:** Other components can't react to image load. They must poll or listen to events.

**Why ref?** Possibly performance (avoiding re-renders), but breaks React reactivity.

**Fix:** Use state or Zustand store. Components subscribe instead of polling.

### Resize Handling Complexity
**SkyViewer** has multiple resize mechanisms:
1. `window.JS9.opts.autoResize = true` (global option)
2. `window.JS9.opts.resizeDisplay = true` (global option)
3. `window.JS9.ResizeDisplay(displayId)` (manual calls)
4. `MutationObserver` watching for React clearing DOM
5. `requestAnimationFrame` for timing

**Problem:** Over-engineered. Multiple mechanisms fighting each other.

**Fix:** Single resize handler. Use ResizeObserver API (modern, efficient).

## Performance Hotspots

### Expensive Calls (No Throttling)
- `GetWCS()`: Called on every mouse move (no throttling)
- `GetVal()`: Called on every mouse move (no throttling)
- `GetImageData()`: Called multiple times for same image (no caching)

### Polling Overhead
**7+ intervals running simultaneously:**
- ImageStatisticsPlugin: 500ms
- PhotometryPlugin: 500ms
- CASAnalysisPlugin: 100ms + 500ms
- QuickAnalysisPanel: 1000ms
- ImageControls: 500ms + 500ms
- ImageMetadata: 100ms
- WCSDisplay: 1000ms + 100ms

**Impact:** Even when idle, 7+ intervals = ~14 checks/second. Wastes CPU.

### Memory Leaks Risk
**Potential leaks:**
1. Intervals not cleared if component unmounts during JS9 init
2. Event listeners not removed if JS9 unavailable during cleanup
3. Timeout refs not cleared in all code paths
4. MutationObserver not disconnected in error cases

## React Performance Issues

### Missing Optimizations
**Only 11 useCallback/useMemo** in Sky components (grep found 11, but many handlers not wrapped).

**Problem:** Event handlers recreated on every render. Causes unnecessary re-renders and repeated `AddEventListener` calls.

**Example:** ImageStatisticsPlugin recreates `handleImageDisplay` on every render (not wrapped in useCallback), causing `AddEventListener` to be called repeatedly.

**Fix:** Wrap all event handlers in `useCallback` with proper deps. Only 11 instances found suggests many handlers are not optimized.

### Effect Dependencies
**SkyViewer** has 8 effects with complex dependencies. Hard to reason about execution order.

**Example:** Effect depends on `[displayId, initialized, loading, imagePath]` but also checks `imageLoadedRef.current` (not in deps). This breaks React's dependency tracking.

## Questions to Resolve

1. **Why polling + events?** Do JS9 events not fire reliably? Need to test.
2. **Why `imageLoadedRef` instead of state?** Performance? Need to measure.
3. **What's the actual user impact?** Are there real bugs from these issues?
4. **What's the JS9 version?** Are there API changes we should use?
5. **Can we upgrade JS9?** Would newer version fix some issues?
6. **Why no useCallback/useMemo?** Performance not a concern, or oversight?

## Next Steps (Prioritized)

### Phase 1: Quick Wins (1-2 days)
1. Extract `findDisplay()` utility function (eliminates 45 duplicate patterns)
2. Add `useCallback` to event handlers (fixes React performance)
3. Throttle `GetWCS()` and `GetVal()` calls (reduces CPU usage)

### Phase 2: State Management (3-5 days)
4. Create JS9 Context Provider (eliminates prop drilling, centralizes init)
5. Remove redundant polling from ImageStatisticsPlugin (relies on events)
6. Replace `imageLoadedRef` with Zustand store (enables reactivity)

### Phase 3: Abstraction (1 week)
7. Create JS9Service interface (enables testing, type safety)
8. Migrate components incrementally (backward compatible)
9. Add comprehensive error handling

### Phase 4: Architecture (1-2 weeks)
10. Split SkyViewer into smaller components
11. Centralize event bus
12. Remove all polling (event-driven only)

