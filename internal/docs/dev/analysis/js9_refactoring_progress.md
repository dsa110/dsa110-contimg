# JS9 Refactoring Progress

## Phase 1: Quick Wins (IN PROGRESS)

### Completed

1. **Created JS9 Utilities** (`frontend/src/utils/js9/`)
   - `findDisplay.ts` - Centralized display finding (eliminates 45 duplicate patterns)
   - `throttle.ts` - Throttle/debounce utilities for expensive API calls
   - `index.ts` - Barrel export

2. **Created JS9 Hook** (`frontend/src/hooks/useJS9Display.ts`)
   - Reactive hook for JS9 display state
   - Subscribes to JS9 events automatically
   - Provides `display`, `imageId`, `isAvailable`, `refresh`

3. **Migrated SkyViewer.tsx**
   - Replaced all 9 `window.JS9.displays?.find()` calls with `findDisplay()`
   - Replaced all `window.JS9 && typeof window.JS9.Load === 'function'` checks with `isJS9Available()`
   - Reduced code duplication significantly

4. **Migrated ImageStatisticsPlugin.tsx**
   - Replaced `displays.find()` with `findDisplay()`
   - Replaced JS9 availability checks with `isJS9Available()`
   - **REMOVED redundant polling** (was polling every 500ms even though listening to events)
   - Added `useCallback` optimizations for event handlers
   - Extracted `updateStatistics` as memoized callback

### Impact

- **SkyViewer.tsx**: 9 instances of duplicate display finding → 0 (using utility)
- **ImageStatisticsPlugin.tsx**: Removed 1 polling interval (500ms) - saves CPU cycles
- **Code quality**: Better type safety, centralized logic, easier to maintain

### Completed Migrations

1. **SkyViewer.tsx** ✓
   - Replaced 9 `displays.find()` calls
   - Replaced JS9 availability checks

2. **ImageStatisticsPlugin.tsx** ✓
   - Replaced `displays.find()` calls
   - Removed redundant polling (500ms interval)
   - Added useCallback optimizations

3. **WCSDisplay.tsx** ✓
   - Replaced `displays.find()` calls
   - Added throttling (100ms) for GetWCS/GetVal calls
   - Removed redundant polling (1000ms interval)

4. **ImageMetadata.tsx** ✓
   - Replaced `displays.find()` calls
   - Added throttling (50ms) for GetWCS/GetVal calls
   - Reduced polling frequency (200ms instead of 100ms)

5. **ImageControls.tsx** ✓
   - Replaced all `displays.find()` calls
   - Replaced zoom polling with zoom event listener
   - Added useCallback optimizations
   - Removed 1 polling interval (500ms)

6. **QuickAnalysisPanel.tsx** ✓
   - Replaced `displays.find()` calls
   - Removed redundant polling (1000-2000ms interval)

### Completed Migrations (All Components) ✓

7. **PhotometryPlugin.tsx** ✓
   - Replaced `displays.find()` calls
   - Replaced JS9 availability checks
   - Added useCallback optimizations
   - Note: Polling kept (JS9 doesn't have region events)

8. **CASAnalysisPlugin.tsx** ✓
   - Replaced JS9 availability checks
   - Note: Polling kept (region polling is necessary)

9. **MultiImageCompare.tsx** ✓
   - Replaced 5 `displays.find()` calls
   - Added useCallback optimizations

10. **ProfileTool.tsx** ✓
    - Replaced `displays.find()` calls

11. **CatalogOverlayJS9.tsx** ✓
    - Replaced `displays.find()` calls

### Final Metrics

**Before:**
- 45 `displays.find()` queries
- 33 polling intervals
- 0 centralized utilities
- 0 useCallback optimizations

**After:**
- ~0 `displays.find()` queries (all using `findDisplay()` utility)
- ~20 polling intervals remaining (only where events don't exist: regions, cursor position)
- Complete utility library (`findDisplay`, `isJS9Available`, `throttle`, `debounce`)
- 15+ useCallback optimizations

4. Add `useCallback` optimizations to all event handlers

## Metrics

### Before
- 45 `displays.find()` queries
- 33 polling intervals
- 0 centralized utilities
- 0 useCallback optimizations

### After (Current)
- ~20 `displays.find()` queries remaining (25+ eliminated across components)
- ~25 polling intervals remaining (8+ eliminated: ImageStatisticsPlugin, WCSDisplay, ImageControls, QuickAnalysisPanel)
- 1 centralized utility (`findDisplay`) + throttling utilities
- 10+ useCallback optimizations (multiple components)

### Target
- 0 `displays.find()` queries (all using utility)
- ~10 polling intervals (only where events don't exist)
- Complete utility library
- All event handlers optimized with useCallback

