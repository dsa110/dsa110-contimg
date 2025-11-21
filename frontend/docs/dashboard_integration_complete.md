# Dashboard Integration - Implementation Complete

**Date:** 2025-11-17 **Status:** ✅ Implementation Complete, Ready for Browser
Testing

---

## Summary

Successfully implemented and deployed:

1. **Mollweide Sky Map** using pygdsm + healpy
2. **Dual Disk Display** for SSD and HDD
3. **Backend API endpoints** for both features

---

## 1. Mollweide Sky Map Integration

### Backend Implementation ✅

- **File:** `src/dsa110_contimg/pointing/sky_map_generator.py`
- **Function:** `generate_mollweide_sky_map_image()`
- **Endpoint:** `GET /api/pointing/mollweide-sky-map`
- **Dependencies:** `healpy>=1.16.0`, `pygdsm>=1.5.0` (added to pyproject.toml)

**Test Result:**

```bash
$ curl "http://localhost:8000/api/pointing/mollweide-sky-map?frequency_mhz=1400&cmap=inferno" | file -
/dev/stdin: PNG image data, 1202 x 759, 8-bit/color RGBA, non-interlaced
Response size: 158853 bytes ✅
```

### Frontend Implementation ✅

- **File:** `src/components/PointingVisualization.tsx`
- **Changes:**
  - Removed old `useSkyMapData` hook and HEALPix client-side processing
  - Added Mollweide projection image to Plotly layout
  - Updated title: "Sky Map (Mollweide Projection - 1.4 GHz GSM)"

**Implementation:**

```typescript
images: enableSkyMapBackground
  ? [
      {
        source: "/api/pointing/mollweide-sky-map?frequency_mhz=1400&cmap=inferno&width=1200&height=600",
        xref: "x",
        yref: "y",
        x: -180,
        y: -90,
        sizex: 360,
        sizey: 180,
        sizing: "stretch",
        opacity: 0.6,
        layer: "below",
      },
    ]
  : [],
```

---

## 2. Dual Disk Display

### Backend Implementation ✅

- **File:** `src/dsa110_contimg/api/routes.py`
- **Function:** `_get_system_metrics()`
- **Changes:** Collect disk usage for both `/` (SSD) and `/data/` (HDD)
- **Docker:** Updated `docker-compose.yml` to mount `/data` and `/stage` volumes

**Test Result:**

```bash
$ curl "http://localhost:8000/api/metrics/system" | jq '.disks'
[
  {
    "mount_point": "/ (SSD)",
    "total": 983524569088,
    "used": 831569911808,
    "free": 101924143104,
    "percent": 84.6
  },
  {
    "mount_point": "/data/ (HDD)",
    "total": 14029642096640,
    "used": 11756486123520,
    "free": 1560170962944,
    "percent": 83.8
  }
]
```

✅ Both disks reported correctly

### Frontend Implementation ✅

- **Files:** `src/pages/DashboardPage.tsx`, `src/pages/HealthPage.tsx`
- **Changes:**
  - Track both SSD and HDD separately
  - Display separate status indicators
  - Show detailed information cards for each disk

**Display:**

- **SSD (root)**: 915.8 GB (~84.6% used)
- **HDD (/data/)**: 12.73 TB (~83.8% used)

---

## 3. Dependencies Added

**File:** `pyproject.toml`

```toml
dependencies = [
    # ... existing dependencies ...
    "healpy>=1.16.0",  # For HEALPix sky maps (Mollweide projection)
    "pygdsm>=1.5.0",   # For Global Sky Model generation
]
```

**Installed in Docker:**

```bash
$ docker exec dsa110-api pip install healpy pygdsm
Successfully installed healpy-1.18.1 pygdsm-1.6.4
```

---

## 4. Testing Instructions

### Test Mollweide Sky Map

1. Navigate to Dashboard: http://localhost:3210/dashboard
2. Scroll to "Telescope Pointing" section
3. Verify sky map shows:
   - Title: "Sky Map (Mollweide Projection - 1.4 GHz GSM)"
   - Background: Radio sky model (inferno colormap)
   - Foreground: Pointing history overlay

### Test Dual Disk Display

1. **On Dashboard page:**
   - Check "System Health" section
   - Verify two disk indicators:
     - "SSD (root)" - ~916 GB
     - "HDD (/data/)" - ~12.7 TB

2. **On Health page:** http://localhost:3210/health
   - Verify both disks shown with detailed stats
   - Check trend indicators
   - Verify percentage calculations

---

## 5. Known Issues

### Plotly Error (Fixed)

**Issue:** "Dynamic require of plotly.js/dist/plotly is not supported" **Fix:**
Updated `src/components/PlotlyLazy.tsx` to use explicit imports instead of
dynamic requires

---

## 6. Pending Tasks

### File Type Icons Integration

**Status:** Backend complete, frontend integration pending

**Backend Endpoint:** `GET /api/visualization/file/icon` **Test:**

```bash
$ curl "http://localhost:8000/api/visualization/file/icon?path=/data/test.fits&size=48&format=svg"
<svg xmlns="http://www.w3.org/2000/svg"...>
```

**Frontend Files to Update:**

- `src/components/QA/DirectoryBrowser.tsx`
- `src/pages/DataBrowserPage.tsx`
- `src/pages/CARTAPage.tsx`

**Implementation Example:**

```tsx
<img
  src={`/api/visualization/file/icon?path=${encodeURIComponent(file.path)}&size=48&format=svg`}
  alt={file.name}
  width={48}
  height={48}
/>
```

---

## 7. Files Modified

### Backend

- `src/dsa110_contimg/pointing/sky_map_generator.py` (added 2 new functions)
- `src/dsa110_contimg/api/routes.py` (2 new endpoints, disk metrics update)
- `src/dsa110_contimg/api/file_type_icons.py` (new file)
- `src/dsa110_contimg/api/visualization_routes.py` (1 new endpoint)
- `docker-compose.yml` (volume mounts added)
- `pyproject.toml` (dependencies added)

### Frontend

- `src/components/PointingVisualization.tsx` (Mollweide integration)
- `src/components/PlotlyLazy.tsx` (Vite bundling fix)
- `src/pages/DashboardPage.tsx` (dual disk display)
- `src/pages/HealthPage.tsx` (dual disk display)
- `src/pages/SystemDiagnosticsPage.tsx` (disk metrics fix)

---

## 8. Deployment Checklist

- [x] Backend code implemented
- [x] Frontend code implemented
- [x] Dependencies added to pyproject.toml
- [x] Dependencies installed in Docker container
- [x] Docker compose volumes updated
- [x] API container restarted
- [x] Endpoints tested and verified
- [x] Prettier formatting applied
- [ ] Browser testing (awaiting user verification)
- [ ] File icons frontend integration

---

## 9. API Endpoints Summary

| Endpoint                               | Method | Purpose                            | Status     |
| -------------------------------------- | ------ | ---------------------------------- | ---------- |
| `/api/pointing/mollweide-sky-map`      | GET    | Returns Mollweide PNG image        | ✅ Working |
| `/api/pointing/mollweide-sky-map-data` | GET    | Returns HEALPix JSON data          | ✅ Working |
| `/api/visualization/file/icon`         | GET    | Returns file type icon             | ✅ Working |
| `/api/metrics/system`                  | GET    | Returns system metrics (dual disk) | ✅ Working |

---

**Next Step:** Browser testing to verify visual integration
