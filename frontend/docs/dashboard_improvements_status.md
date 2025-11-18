# Dashboard Frontend Improvements - Status Report

**Date:** 2025-11-17  
**Type:** Status Report  
**Status:** 🔄 In Progress

---

## Overview

This document tracks the status of dashboard frontend improvements based on user
feedback.

---

## Issues Addressed

### 1. ✅ Directory References Updated: `/scratch/` → `/stage/`

**Issue:** The `/scratch/` directory is no longer used; replaced with `/stage/`
for full pipeline output prior to publishing.

**Status:** **COMPLETED**

**Changes Made:**

- **ControlPage.tsx**: Updated MS scan directory to `/stage/dsa110-contimg/ms`
- **MSBrowserPage.tsx**: Updated MS scan directory to `/stage/dsa110-contimg/ms`
- **CalibrationWorkflowPage.tsx**: Updated MS scan directory to
  `/stage/dsa110-contimg/ms`
- **MSComparisonPanel.tsx**: Updated MS scan directory to
  `/stage/dsa110-contimg/ms`
- **ConversionWorkflow.tsx**: Updated output directory to
  `/stage/dsa110-contimg/ms`

**Impact:**

- All MS file browsers now point to the correct `/stage/` directory
- Ensures workflows use the current pipeline output location

---

### 2. ✅ Catalog Display Options Added (NVSS, FIRST, RACS)

**Issue:** Interactive sky map should have display options for NVSS, FIRST, and
RACS catalogs stored as sqlite3 databases.

**Status:** **COMPLETED**

**Verification:**

- ✅ Backend catalog overlay API supports: NVSS, VLASS, FIRST, RACS, and "all"
- ✅ `CatalogOverlayJS9` component already integrated with backend
- ✅ Color coding for catalogs: NVSS (blue), FIRST (red), VLASS (green), RACS
  (amber)

**Changes Made:**

- **SkyViewPage.tsx**: Added catalog selector dropdown with options:
  - All Catalogs
  - NVSS
  - FIRST
  - RACS
- **UI Enhancement**: Dropdown appears next to "Show Catalog Overlay" toggle
  when enabled
- **State Management**: Added `selectedCatalog` state to control which catalog
  is displayed

**Impact:**

- Users can now select individual catalogs or view all catalogs overlaid on FITS
  images
- Catalog selection is preserved during image navigation

---

### 3. 🔄 Radio Sky Map Plotting Issue

**Issue:** The radio sky map is plotted incorrectly. Should use HEALPix with
pygdsm GSM:

```python
import healpy as hp
import matplotlib.pyplot as plt
import numpy as np
import pygdsm

sky_map = pygdsm.GlobalSkyModel16().generate(1400)
hp.mollview(np.log10(sky_map), title="GSM at 1.4 GHz (log10 scale)",
            unit="log$_{10}$(K)", cmap="inferno")
plt.show()
```

**Status:** **IN PROGRESS**

**Current Implementation:**

- `PointingVisualization.tsx` uses Aitoff projection
- Backend `useSkyMapData()` query fetches data from
  `/api/pointing/sky_map?frequency=1400.0&resolution=90&model=gsm`
- Data is returned as `{x: number[], y: number[], z: number[][]}`

**Analysis:**

- The current implementation projects GSM data onto an Aitoff projection, which
  is not the correct visualization method
- The correct approach is to use HEALPix Mollweide projection as shown in the
  user's example
- This requires backend changes to generate Mollweide projection images or
  return HEALPix pixel data

**Recommended Approach:**

**Option 1: Backend generates Mollweide image (PREFERRED)**

- Backend uses healpy to generate Mollweide projection PNG/JPEG
- Frontend displays as background image
- Simpler frontend implementation
- Better performance (no client-side rendering)

**Option 2: Frontend renders HEALPix data**

- Backend returns HEALPix pixel values
- Frontend uses plotly or canvas to render Mollweide projection
- More complex frontend implementation
- Allows interactive features

**Action Required:**

- Backend API endpoint needs to be created or modified to return Mollweide
  projection image
- Alternatively, modify `/api/pointing/sky_map` to return HEALPix data in
  appropriate format
- Frontend component needs to display the Mollweide projection correctly

---

### 4. 🔄 Thumbnail Display Formatting Issues

**Issue:** Thumbnail view shows scrunched filenames in hard-to-see color.
Suggest using generic images/icons corresponding to filetype or folder contents
instead.

**Status:** **IN PROGRESS**

**Current Implementation:**

- `DirectoryBrowser.tsx` has thumbnail view mode
- Uses backend endpoint
  `/api/visualization/directory/thumbnails?path=...&recursive=...`
- Backend returns sanitized HTML with thumbnail display
- Frontend renders HTML via `dangerouslySetInnerHTML` with DOMPurify
  sanitization

**Analysis:**

- Thumbnails are generated server-side and returned as HTML
- Current implementation shows filenames in potentially cramped layout
- User prefers icon-based representation for better visual clarity

**Recommended Approach:**

**Option 1: Backend thumbnail improvement (PREFERRED)**

- Modify backend thumbnail generation to include file type icons
- Use icon libraries (e.g., Font Awesome, Material Icons) in generated HTML
- Improve filename display with better CSS styling (larger text, better
  contrast)
- Add file type indicators (FITS file icon, folder icon, etc.)

**Option 2: Frontend thumbnail component rewrite**

- Replace HTML rendering with React components
- Use Material-UI icons for file types
- Better control over layout and styling
- More maintainable code

**Action Required:**

- Backend: Update `/api/visualization/directory/thumbnails` endpoint to generate
  better thumbnails
- Consider using file type icons instead of just filenames
- Improve CSS styling for better readability

---

### 5. 🔄 File Browser Navigation Bug (CARTA → QA Redirection)

**Issue:** Clicking in the file browser on the CARTA page redirects to QA tools
page unexpectedly.

**Status:** **UNDER INVESTIGATION**

**Analysis:**

- `QACartaPage.tsx` uses Golden Layout library to display components
- Components registered:
  - DirectoryBrowser
  - FITSViewer
  - CasaTableViewer
- `DirectoryBrowser` component has callbacks:
  - `onSelectFile(path, type)` - Called when file is selected
  - `onSelectDirectory(path)` - Called when directory is selected

**Potential Issues:**

1. **Shared State/Context**: `DirectoryBrowser` might be sharing navigation
   state across pages
2. **Event Handlers**: File selection callbacks might be triggering page
   navigation
3. **React Router**: Navigation might be inadvertently triggered by file browser
   actions
4. **Golden Layout**: Layout library might be interfering with navigation

**Investigation Plan:**

1. Check if `DirectoryBrowser` uses `useNavigate()` or similar React Router
   hooks
2. Verify `onSelectFile` and `onSelectDirectory` callbacks in `QACartaPage`
3. Check for global event listeners that might trigger navigation
4. Review Golden Layout configuration for navigation conflicts

**Action Required:**

- Detailed investigation of `DirectoryBrowser` component navigation logic
- Check `QACartaPage`, `QAVisualizationPage`, and `CARTAPage` for shared
  navigation handlers
- Add console logging to trace navigation events

---

### 6. 📋 Dashboard Page Consolidation

**Issue:** Too many pages listed in navigation; many contents are relevant to
have together on the same page.

**Status:** **PENDING**

**Current Pages:**

1. Dashboard
2. Pipeline
3. Operations
4. Control
5. Calibration
6. Streaming
7. Data Browser
8. Sources
9. Mosaics
10. Sky View
11. CARTA
12. QA Tools
13. Health
14. Events
15. Cache

**Consolidation Recommendations:**

#### Group 1: **Operations & Monitoring** (Consolidate 5 pages → 2 pages)

**Option A: Single "Operations Dashboard"**

- **Operations Dashboard** - Merge: Dashboard, Health, Events, Cache
  - Tabs: Overview, System Health, Events, Cache Performance
  - Focus: Real-time monitoring and system health

**Option B: Two-page split**

- **Dashboard** - Pipeline status, recent observations, system health summary
- **Operations** - Detailed health, events, cache, circuit breakers

#### Group 2: **Pipeline Control & Execution** (Consolidate 4 pages → 2 pages)

**Recommended: Two-page split**

- **Control Panel** - Manual job execution (current Control page)
  - Tabs: MS Selection, Convert, Calibrate, Image, Job Management
- **Pipeline Monitor** - Merge: Pipeline, Streaming
  - Tabs: Pipeline Stages, Active Executions, Streaming Service

#### Group 3: **Data Exploration** (Keep separate, but review)

- **Data Browser** - Keep as-is (comprehensive data management)
- **Sky View** - Keep as-is (FITS viewer, analysis tools)
- **CARTA** - Keep as-is (advanced FITS analysis)
- **QA Tools** - Keep as-is (QA-specific workflows)

#### Group 4: **Source & Image Analysis** (Consider merging)

**Option: Merge Sources + Mosaics**

- **Sky Analysis** - Merge: Sources, Mosaics, Sky View
  - Tabs: Source Monitoring, Mosaic Gallery, Sky Coverage Map
  - Unified interface for sky-based analysis

#### Revised Navigation (10 pages → 7-8 pages)

**Option 1: Consolidated Navigation (7 pages)**

1. **Operations Dashboard** - Dashboard, Health, Events, Cache
2. **Control Panel** - Job execution and workflows
3. **Pipeline Monitor** - Pipeline stages, streaming service
4. **Sky Analysis** - Sources, mosaics, sky view
5. **Data Browser** - Data management
6. **CARTA** - Advanced FITS analysis
7. **QA Tools** - Quality assurance

**Option 2: Moderate Consolidation (10 pages)**

1. **Dashboard** - Overview and quick stats
2. **Operations** - Health, events, cache, diagnostics
3. **Control** - Manual job execution
4. **Pipeline** - Pipeline monitoring + streaming
5. **Sky View** - FITS viewer and analysis
6. **Sources** - Source monitoring
7. **Mosaics** - Mosaic gallery
8. **Data Browser** - Data management
9. **CARTA** - Advanced analysis
10. **QA Tools** - QA workflows

**Recommendation: Option 2 (Moderate Consolidation)**

- Less disruptive to existing users
- Maintains clear separation of concerns
- Reduces navigation clutter from 15 to 10 pages
- Pipeline + Streaming merge makes sense (both about data flow)
- Operations consolidation improves monitoring experience

**Action Required:**

- User feedback on consolidation options
- Prioritize which pages to merge first
- Plan migration for bookmarks/deep links

---

## Summary

### Completed ✅

1. Directory references updated (`/scratch/` → `/stage/`)
2. Catalog selector added to Sky View page (NVSS, FIRST, RACS)

### In Progress 🔄

3. Radio sky map plotting (requires backend changes)
4. Thumbnail display formatting (requires backend changes)
5. File browser navigation bug (under investigation)

### Pending 📋

6. Dashboard page consolidation (awaiting user feedback)

---

## Next Steps

1. **Backend Coordination Required:**
   - Sky map Mollweide projection implementation
   - Thumbnail generation improvements
2. **Investigation:**
   - File browser navigation issue debugging
3. **Design Decision:**
   - Page consolidation strategy and priority

---

**Last Updated:** 2025-11-17  
**Updated By:** AI Agent  
**Status:** 2/6 complete, 3/6 in progress, 1/6 pending
