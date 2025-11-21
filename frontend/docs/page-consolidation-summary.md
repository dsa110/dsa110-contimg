# Page Consolidation Summary

**Date:** 2025-11-17  
**Status:** ✅ Complete

---

## Overview

Successfully consolidated 10+ pages into 4 unified pages, simplifying navigation
and grouping related functionality. All deprecated files removed; backward
compatibility redirects in place.

---

## Consolidated Pages

### 1. `/control` → PipelineControlPage

**Merges:**

- ControlPage (Measurement Sets & Workflows) - Tab 0
- StreamingPage (Streaming Service) - Tab 1
- ObservingPage (Observing) - Tab 2

**Navigation:** Main nav shows "Control"

**Redirects:**

- `/streaming` → `/control?tab=1`
- `/observing` → `/control?tab=2`

---

### 2. `/operations` → PipelineOperationsPage

**Merges:**

- PipelinePage (Pipeline monitoring & executions) - Tab 1
- OperationsPage (DLQ & Circuit Breakers) - Tab 2
- EventsPage (Event Stream) - Tab 3
- Overview dashboard - Tab 0
- Dependency Graph - Tab 4

**Navigation:** Main nav shows "Operations"

---

### 3. `/health` → SystemDiagnosticsPage

**Merges:**

- System Dashboard - Tab 0
- HealthPage (Deep diagnostics) - Tab 1
- QAPage (QA Tools) - Tab 2
- CachePage (Cache statistics) - Tab 3

**Navigation:** Main nav shows "Health"

**Redirects:**

- `/cache` → `/health?tab=3`

---

### 4. `/qa` → QAPage (New Unified Page)

**Merges:**

- QAVisualizationPage (Tab-based UI)
- QACartaPage (Golden Layout dockable panels)

**Features:**

- Toggle between "Tab View" and "CARTA View" modes
- Tab View: 5 tabs (Directory Browser, FITS Viewer, CASA Table Viewer, Notebook
  Generator, Image Comparison)
- CARTA View: Golden Layout dockable panels (drag & drop interface)

**Navigation:** Main nav shows "QA Tools"

**Redirects:**

- `/qa/carta` → `/qa`

---

### 5. Deprecated: MSBrowserPage

**Status:** REMOVED (functionality merged into ControlPage/PipelineControlPage)

**Redirects:**

- `/ms-browser` → `/control`

---

## Files Deleted

1. `src/pages/QAVisualizationPage.tsx` (merged into QAPage)
2. `src/pages/QACartaPage.tsx` (merged into QAPage)
3. `src/pages/MSBrowserPage.tsx` (merged into ControlPage/PipelineControlPage)

---

## Files Modified

1. `src/pages/QAPage.tsx` - **NEW** unified QA page
2. `src/App.tsx` - Updated routing and lazy imports
3. `src/components/Navigation.tsx` - Removed consolidated routes from nav
4. `src/pages/SystemDiagnosticsPage.tsx` - Uses QAPage instead of
   QAVisualizationPage
5. `src/utils/routePrefetch.ts` - Updated route prefetch mappings

---

## Navigation Changes

### Before (15 items)

- Dashboard
- Pipeline
- Operations
- Control
- Calibration
- **Streaming** ← removed
- Data Browser
- Sources
- Mosaics
- Sky View
- CARTA
- QA Tools
- Health
- Events
- **Cache** ← removed

### After (13 items)

- Dashboard
- Pipeline
- Operations _(now consolidated)_
- Control _(now consolidated)_
- Calibration
- Data Browser
- Sources
- Mosaics
- Sky View
- CARTA
- QA Tools _(now consolidated)_
- Health _(now consolidated)_
- Events

---

## Benefits

1. **Reduced cognitive load:** 13 nav items instead of 15
2. **Logical grouping:** Related functionality in tabs
3. **Cleaner navigation:** Less clutter in sidebar
4. **Better UX:** Users find related features together
5. **Preserved URLs:** All old routes redirect to new ones

---

## Technical Details

### Tab Query Parameters

Consolidated pages support `?tab=N` query parameter for deep linking:

- `/control?tab=0` - Control (MS & Workflows)
- `/control?tab=1` - Streaming Service
- `/control?tab=2` - Observing
- `/operations?tab=0` - Overview
- `/operations?tab=1` - Executions
- `/operations?tab=2` - Operations (DLQ)
- `/operations?tab=3` - Events
- `/operations?tab=4` - Dependency Graph
- `/health?tab=0` - Dashboard
- `/health?tab=1` - System Health
- `/health?tab=2` - QA Tools
- `/health?tab=3` - Cache

### QA View Toggle

The QAPage includes a view mode toggle:

- **Tab View** - Traditional tabbed interface
- **CARTA View** - Golden Layout dockable panels

View preference could be saved to localStorage in future enhancement.

---

## Component Pages (Still Used Internally)

These pages are no longer standalone routes but are embedded in consolidated
pages:

- `ControlPage.tsx` - Used in PipelineControlPage
- `StreamingPage.tsx` - Used in PipelineControlPage
- `ObservingPage.tsx` - Used in PipelineControlPage
- `HealthPage.tsx` - Used in SystemDiagnosticsPage
- `CachePage.tsx` - Used in SystemDiagnosticsPage

These can be further refactored/removed in future if needed.

---

## Testing Checklist

- [x] All routes resolve correctly
- [x] Redirects work with tab parameters
- [x] Navigation links work
- [x] Tab persistence in URL
- [x] QA view toggle works
- [x] No broken imports
- [x] No linting errors

---

## Future Enhancements

1. Save QA view preference (Tab vs CARTA) to localStorage
2. Consider removing component pages if not needed elsewhere
3. Add breadcrumbs showing current tab
4. Add keyboard shortcuts for tab navigation (Ctrl+1, Ctrl+2, etc.)
5. Consider consolidating EventsPage into PipelineOperationsPage permanently

---

**Related Documentation:**

- Main navigation: `src/components/Navigation.tsx`
- Routing: `src/App.tsx`
- Route prefetching: `src/utils/routePrefetch.ts`
