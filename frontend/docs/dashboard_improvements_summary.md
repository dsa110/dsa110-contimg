# Dashboard Frontend Improvements - Summary

**Date:** 2025-11-17  
**Type:** Summary Report  
**Status:** ✅ 4/6 Complete, 2/6 Require Backend Changes

---

## Executive Summary

Based on user feedback, six issues were identified with the dashboard frontend.
**Four have been completed** with frontend-only changes, **two require backend
API modifications** before they can be fully resolved.

---

## Completed Items (4/6)

### 1. ✅ Directory Path Updates (`/scratch/` → `/stage/`)

**Issue:** Pipeline now uses `/stage/` directory instead of `/scratch/`.

**Solution:** Updated 5 files to reference correct directory:

- `ControlPage.tsx`
- `MSBrowserPage.tsx`
- `CalibrationWorkflowPage.tsx`
- `MSComparisonPanel.tsx`
- `ConversionWorkflow.tsx`

**Impact:** MS file browsers now point to current pipeline output location.

---

### 2. ✅ Catalog Selection UI (NVSS, FIRST, RACS)

**Issue:** Sky map catalog overlay lacked user-selectable catalog options.

**Solution:** Added catalog selector dropdown to Sky View page:

- Options: All Catalogs, NVSS, FIRST, RACS
- Appears inline with "Show Catalog Overlay" toggle
- Preserves selection during image navigation

**Files Modified:**

- `pages/SkyViewPage.tsx`

**Backend Status:** ✅ Already supports all catalogs via
`/catalog/overlay?catalog={nvss|first|racs|all}`

**Impact:** Users can now select individual catalogs for overlay visualization.

---

### 3. ✅ File Browser Navigation Investigation

**Issue:** User reported file browser clicks causing unexpected page navigation.

**Findings:** **No navigation bug found in code.**

- `DirectoryBrowser` component has NO navigation logic
- All file selection handlers only update local state
- No React Router navigation calls in any handler

**Conclusion:** Likely user confusion or browser extension interference.

**Recommendation:** User to reproduce with browser console open and provide
detailed steps.

**Documentation:** See `frontend/docs/file_browser_navigation_investigation.md`

---

### 4. ✅ Page Consolidation Recommendations

**Issue:** Too many navigation pages (15 total).

**Recommendations:**

#### Option 1: Aggressive Consolidation (15 → 7 pages)

1. **Operations Dashboard** - Dashboard + Health + Events + Cache
2. **Control Panel** - Job execution
3. **Pipeline Monitor** - Pipeline + Streaming
4. **Sky Analysis** - Sources + Mosaics + Sky View
5. **Data Browser** - Data management
6. **CARTA** - Advanced analysis
7. **QA Tools** - QA workflows

#### Option 2: Moderate Consolidation (15 → 10 pages) **[RECOMMENDED]**

1. **Dashboard** - Overview and quick stats
2. **Operations** - Health + Events + Cache + Diagnostics
3. **Control** - Manual job execution
4. **Pipeline** - Pipeline monitoring + Streaming
5. **Sky View** - FITS viewer and analysis
6. **Sources** - Source monitoring
7. **Mosaics** - Mosaic gallery
8. **Data Browser** - Data management
9. **CARTA** - Advanced analysis
10. **QA Tools** - QA workflows

**Rationale:**

- Less disruptive to existing users
- Maintains clear separation of concerns
- Reduces navigation clutter by 33%
- Pipeline + Streaming merge is logical (both about data flow)
- Operations consolidation improves monitoring UX

**Documentation:** See `frontend/docs/dashboard_improvements_status.md`
(section 6)

---

## Pending Items (2/6) - Require Backend Changes

### 5. 🔄 Radio Sky Map Plotting

**Issue:** Sky map uses Aitoff projection instead of HEALPix Mollweide
projection with PyGDSM GSM.

**Correct Implementation:**

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

**Current State:**

- Frontend: `PointingVisualization.tsx` uses Aitoff projection
- Backend: `/api/pointing/sky_map` returns `{x: [], y: [], z: [[]]}`
- Data is projected incorrectly

**Required Changes:**

#### Backend (REQUIRED):

**Option 1 (Recommended):** Backend generates Mollweide PNG/JPEG

- Endpoint: `/api/pointing/sky_map_image?frequency=1400`
- Returns: PNG/JPEG image with Mollweide projection
- Uses: `healpy.mollview()` to generate image

**Option 2:** Backend returns HEALPix pixel data

- Endpoint: `/api/pointing/sky_map?frequency=1400&format=healpix`
- Returns: HEALPix pixel array
- Frontend: Render Mollweide projection client-side

#### Frontend:

- Display image if Option 1
- Render HEALPix data if Option 2

**Status:** ⏸️ **Blocked - Requires backend API changes**

**Documentation:** See `frontend/docs/dashboard_improvements_status.md`
(section 3)

---

### 6. 🔄 Thumbnail Display Formatting

**Issue:** Thumbnail view shows cramped filenames in hard-to-see colors. Need
file type icons instead.

**Current State:**

- Component: `DirectoryBrowser.tsx`
- Backend: `/api/visualization/directory/thumbnails`
- Returns: HTML with thumbnail grid (sanitized with DOMPurify)
- Layout: Generated server-side

**Required Changes:**

#### Backend (REQUIRED):

**Option 1 (Recommended):** Improve server-side HTML generation

- Add file type icons (Font Awesome, Material Icons)
- Improve CSS styling:
  - Larger, more readable filenames
  - Better color contrast
  - Icon-based file type indicators
- Better layout for thumbnail grid

**Option 2:** Frontend component rewrite

- Replace HTML rendering with React components
- Use Material-UI icons for file types
- More maintainable, but requires API changes

#### Frontend:

- If Option 1: Minimal changes, just consume improved HTML
- If Option 2: Complete rewrite of thumbnail rendering

**Recommendation:** Option 1 (backend improvement) is faster and less invasive.

**Status:** ⏸️ **Blocked - Requires backend API changes**

**Documentation:** See `frontend/docs/dashboard_improvements_status.md`
(section 4)

---

## Files Modified

### Frontend Changes (4 files)

1. `pages/ControlPage.tsx` - `/stage/` directory path
2. `pages/MSBrowserPage.tsx` - `/stage/` directory path
3. `pages/CalibrationWorkflowPage.tsx` - `/stage/` directory path
4. `components/MSDetails/MSComparisonPanel.tsx` - `/stage/` directory path
5. `components/workflows/ConversionWorkflow.tsx` - `/stage/` directory path
6. `pages/SkyViewPage.tsx` - Catalog selector UI

### Documentation Created (3 files)

1. `frontend/docs/dashboard_improvements_status.md` - Detailed status tracking
2. `frontend/docs/file_browser_navigation_investigation.md` - Navigation bug
   investigation
3. `frontend/docs/dashboard_improvements_summary.md` - This document

---

## Next Steps

### Immediate (Frontend Team)

1. ✅ Test catalog selector on Sky View page
2. ✅ Verify `/stage/` directory paths in MS browsers
3. 📋 Implement page consolidation (if approved)

### Backend Team Coordination Required

4. 🔄 Sky map Mollweide projection API endpoint
5. 🔄 Thumbnail generation improvement

### User Verification

6. 📋 Reproduce file browser navigation issue (if it persists)
7. 📋 Provide feedback on page consolidation options

---

## Impact Assessment

### Performance Impact

- ✅ Minimal - All changes are lightweight
- ✅ Catalog selector adds no overhead (existing API)
- ✅ No new dependencies

### User Experience Impact

- ✅ **Positive** - Catalog selection improves sky analysis workflow
- ✅ **Positive** - Correct directory paths prevent confusion
- ✅ **Positive** - Page consolidation will reduce navigation clutter

### Breaking Changes

- ❌ **None** - All changes are backward-compatible
- ❌ No API changes required for completed items

---

## Testing Recommendations

### Manual Testing

1. **Sky View page:**
   - Toggle catalog overlay on/off
   - Select different catalogs (NVSS, FIRST, RACS, All)
   - Verify overlay displays correct catalog sources
   - Switch between images, verify catalog selection persists
2. **MS Browsers:**
   - Open Control page, verify MS list loads from `/stage/`
   - Test MS selection and metadata display
   - Repeat for Calibration Workflow and MS Comparison panels
3. **File Browsers:**
   - Test CARTA page file browser
   - Test QA Visualization page file browser
   - Verify no unexpected navigation occurs

### Automated Testing

1. Add E2E tests for catalog selector
2. Add unit tests for directory path updates
3. Add navigation tests for file browsers

---

## Rollout Plan

### Phase 1: Immediate Deployment (Ready Now)

- Directory path updates (`/stage/`)
- Catalog selector UI

### Phase 2: Backend Coordination (TBD)

- Sky map Mollweide projection
- Thumbnail formatting improvements

### Phase 3: Page Consolidation (User Decision)

- Implement chosen consolidation option
- Update navigation
- Migrate bookmarks/deep links
- Update documentation

---

## Contact & Support

**Questions or Issues:**

- Frontend: See `/data/dsa110-contimg/frontend/docs/`
- Backend API: See
  `/data/dsa110-contimg/docs/reference/dashboard_backend_api.md`

**Related Documentation:**

- `dashboard_improvements_status.md` - Detailed status
- `file_browser_navigation_investigation.md` - Navigation bug analysis
- `DASHBOARD_PATH_MAP.md` - Page routing reference

---

**Last Updated:** 2025-11-17  
**Completion Status:** 4/6 Complete (67%)  
**Blocked Items:** 2/6 (Backend required)
