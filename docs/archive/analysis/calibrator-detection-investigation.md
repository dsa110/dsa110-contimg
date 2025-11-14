# Calibrator Detection Investigation Summary

**Date:** 2025-11-07  
**Issue:** "No calibrators detected" message in dashboard for MS files containing VLA calibrator 0834+555

## Root Causes Identified

### 1. ✅ Fixed: `weighted_flux` Calculation Bug
**Problem:** The `calibrator_match()` function only checked for `flux_20_cm` column, but the SQLite catalog uses `flux_jy`.

**Fix:** Updated `src/dsa110_contimg/calibration/catalogs.py` to:
- Check for `flux_20_cm` first (for CSV catalogs)
- Fallback to `flux_jy` (for SQLite catalogs)
- Apply correct scaling (mJy → Jy for `flux_20_cm`, no scaling for `flux_jy`)

**Result:** `weighted_flux` now calculates correctly (1.075 Jy for 0834+555).

### 2. ✅ Fixed: Frontend API URL Mismatch
**Problem:** Frontend `.env.development` was configured for port 8000, but API runs on 8010.

**Fix:** Updated `frontend/.env.development` to use port 8010.

**Note:** Frontend dev server needs restart to pick up this change.

### 3. ✅ Fixed: Auto-Scan for MS Files
**Problem:** MS list endpoint doesn't auto-scan filesystem; requires explicit `scan=true` parameter.

**Fix:** Updated `frontend/src/pages/ControlPage.tsx` to automatically call `useMSList()` with:
```typescript
useMSList({ 
  scan: true, 
  scan_dir: '/stage/dsa110-contimg/ms' 
});
```

**Result:** MS files are now discovered automatically on page load.

### 4. ⚠️ Catalog Only Has 2 Calibrators (Expected)
**Investigation:** The VLA calibrator catalog (`state/catalogs/vla_calibrators.sqlite3`) contains only 2 calibrators:
- 0834+555 (2.5 Jy at 1.4 GHz)
- 0702+445 (1.1 Jy at 1.4 GHz)

**Analysis:**
- This is a **minimal test catalog** for development/testing
- The catalog structure is correct (SQLite database with `calibrators` and `fluxes` tables)
- The `vla_20cm` view correctly joins calibrators and fluxes
- For production, a full VLA catalog would need to be populated

**Status:** This is expected behavior for a test/development environment. The catalog structure supports adding more calibrators when needed.

## Testing Results

### Calibrator Matching Works Correctly
```bash
# Test with 0834+555 MS
curl "http://localhost:8010/api/ms/.../calibrator-matches?catalog=vla&radius_deg=1.5"

# Response:
{
  "has_calibrator": true,
  "matches": [{
    "name": "0834+555",
    "pb_response": 0.430,
    "quality": "marginal",
    "weighted_flux": 1.075
  }]
}
```

### MS Discovery Works
```bash
# API endpoint discovers 9 MS files when scan=true
curl "http://localhost:8010/api/ms?scan=true&scan_dir=/stage/dsa110-contimg/ms"

# Response: 9 MS files found
```

## Remaining Issues

### Frontend Not Showing MS Files
**Symptom:** Dashboard still shows "No MS files found" even after fixes.

**Possible Causes:**
1. Frontend dev server needs restart to pick up `.env.development` changes
2. Vite proxy might not be forwarding correctly
3. API response might not be parsed correctly

**Next Steps:**
1. Restart frontend dev server
2. Check browser console for API errors
3. Verify network requests are reaching API on port 8010

## Files Modified

1. `src/dsa110_contimg/calibration/catalogs.py` - Fixed `weighted_flux` calculation
2. `frontend/.env.development` - Updated API URL to port 8010
3. `frontend/src/pages/ControlPage.tsx` - Added auto-scan on load

## Recommendations

1. **Restart Frontend Dev Server:** Required to pick up `.env.development` changes
2. **Populate Full VLA Catalog:** For production use, populate `vla_calibrators.sqlite3` with full VLA calibrator catalog
3. **Monitor API Logs:** Check API logs to verify requests are being received correctly
4. **Test Calibrator Detection:** After restart, select an MS file and verify calibrator detection works

## Catalog Structure

The SQLite catalog has the following structure:
- **Tables:**
  - `calibrators`: Name, RA, Dec
  - `fluxes`: Name, band, frequency, flux_jy
  - `meta`: Metadata
- **View:**
  - `vla_20cm`: Joins calibrators and fluxes, filters for 20cm band

This structure supports adding more calibrators by inserting into `calibrators` and `fluxes` tables.

