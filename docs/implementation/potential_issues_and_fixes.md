# Potential Issues and Fixes for High-Priority Implementations

## Critical Issues (High Probability of Failure)

### 1. API Path Handling for Image IDs ⚠️

**Issue:** The catalog validation and overlay endpoints use `{image_id}` parameter but treat it as a direct file path. This may fail if:
- Image IDs are database IDs, not paths
- Paths need URL decoding
- Images are accessed through a different mechanism

**Current Code:**
```python
image_path = f"/{image_id}" if not image_id.startswith('/') else image_id
```

**Fix Needed:**
- Check how other image endpoints handle image IDs (see `/api/images/{image_id}/fits`)
- May need to query database for image path instead of using ID directly
- Or use `{image_path:path}` like other endpoints

**Location:** `api/routes.py` lines ~2089, ~2127

---

### 2. Frontend SVG Overlay Integration ⚠️

**Issue:** The `CatalogOverlay` component renders an SVG overlay, but it assumes:
- The parent component provides a container with specific dimensions
- The image viewer uses pixel coordinates matching the image dimensions
- The SVG can be absolutely positioned over the image

**Current Code:**
```tsx
<svg style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%' }}>
```

**Potential Failures:**
- If image viewer uses canvas instead of img tag
- If image is scaled/zoomed, pixel coordinates won't match
- If image viewer has different coordinate system

**Fix Needed:**
- Check existing image viewer implementation
- May need to integrate with specific image viewer library (e.g., OpenLayers, Leaflet, or custom)
- May need to handle image transformations/zoom

**Location:** `frontend/src/components/Sky/CatalogOverlay.tsx`

---

### 3. Source Extraction Without scipy ⚠️

**Issue:** The fallback source extraction when scipy is unavailable is very basic:
- Creates one source per pixel above threshold (no clustering)
- No proper peak finding
- Will create many false sources

**Current Code:**
```python
except ImportError:
    # Fallback: simple threshold-based extraction without scipy
    n_features = len(x_coords)
    labeled = np.zeros_like(data, dtype=int)
    for i, (x, y) in enumerate(zip(x_coords, y_coords)):
        labeled[y, x] = i + 1
```

**Impact:**
- Validation will have many false matches
- Flux measurements will be inaccurate
- Astrometry offsets may be wrong due to poor source positions

**Fix Needed:**
- Install scipy as a dependency, OR
- Implement better clustering algorithm without scipy (e.g., DBSCAN from sklearn or custom)

**Location:** `qa/catalog_validation.py` lines ~146-160

---

## Moderate Issues (Medium Probability)

### 4. Catalog Column Name Mismatch ⚠️

**Issue:** The code assumes catalog DataFrames have specific column names:
- `ra_deg`, `dec_deg` (required)
- `flux_mjy` or `flux_jy` (for flux)

**Current Code:**
```python
if "flux_mjy" in catalog_sources.columns:
    catalog_sources["flux_jy"] = catalog_sources["flux_mjy"] / 1000.0
elif "flux_jy" not in catalog_sources.columns:
    catalog_sources["flux_jy"] = 0.0
```

**Potential Failure:**
- If catalog returns different column names
- If catalog structure changes

**Fix:** Already handled with fallback, but may produce incorrect results

**Location:** Multiple locations in `qa/catalog_validation.py`

---

### 5. WCS Parsing for Non-Standard Images ⚠️

**Issue:** WCS parsing assumes standard FITS headers:
- `CRVAL1`, `CRVAL2`, `CDELT1`, `CDELT2`, `CRPIX1`, `CRPIX2`
- `CTYPE1`, `CTYPE2` for coordinate types

**Potential Failures:**
- Non-standard WCS keywords
- Different projection types
- Missing WCS keywords

**Current Handling:**
- Uses `astropy.wcs.WCS` which is robust, but may fail silently
- Falls back to defaults if keywords missing

**Fix:** Add validation and better error messages

**Location:** `qa/catalog_validation.py` - multiple functions

---

### 6. Frequency Detection from FITS Headers ⚠️

**Issue:** Frequency detection tries multiple keywords but may fail:
- `RESTFRQ`, `FREQ`, `CRVAL3` with `CTYPE3='FREQ'`

**Current Code:**
```python
if "RESTFRQ" in header:
    return header["RESTFRQ"] * 1e6
elif "FREQ" in header:
    return header["FREQ"] * 1e6
elif "CRVAL3" in header and header.get("CTYPE3", "").startswith("FREQ"):
    return header["CRVAL3"] * 1e6
```

**Impact:**
- Flux scale validation will fail if frequency unknown
- Can't scale catalog fluxes to image frequency

**Fix:** Add fallback to use catalog frequency directly, or require frequency parameter

**Location:** `qa/catalog_validation.py` - `get_image_frequency()`

---

### 7. SPW Count Detection Failure ⚠️

**Issue:** SPW count detection may fail if:
- MS structure is non-standard
- SPECTRAL_WINDOW table doesn't exist
- casacore.tables import fails

**Current Code:**
```python
try:
    from casacore.tables import table
    spw_table_path = str(ms_path) + "/SPECTRAL_WINDOW"
    with table(spw_table_path, ack=False) as spw_table:
        return len(spw_table)
except Exception as e:
    logger.warning(f"Could not determine SPW count from MS {ms_path}: {e}")
    return 1  # Default to 1 SPW
```

**Impact:**
- May create wrong number of expected BP tables
- Validation may miss tables or expect non-existent tables

**Fix:** Already has fallback, but may produce incorrect expectations

**Location:** `calibration/caltable_paths.py` - `_get_n_spws_from_ms()`

---

## Low-Probability Issues (Edge Cases)

### 8. Catalog Query Failures

**Issue:** Catalog queries may fail if:
- Catalog database not accessible
- Catalog files missing
- Network issues (if remote catalog)

**Current Handling:**
- Functions will raise exceptions
- API endpoints will return 500 errors

**Fix:** Add better error handling and user-friendly messages

---

### 9. Large Catalog Queries

**Issue:** Querying large fields may:
- Return thousands of sources
- Slow down validation
- Cause memory issues

**Current Handling:**
- No limits on query size
- No pagination

**Fix:** Add `max_sources` parameter to queries

---

### 10. Frontend Type Mismatches

**Issue:** TypeScript types may not match actual API responses:
- Optional fields may be required
- Array types may differ
- Nested structures may be different

**Fix:** Test API responses match TypeScript types

---

## Recommended Immediate Fixes

### Priority 1 (Critical)

1. **Fix API path handling** - Check how images are accessed and update endpoints accordingly
2. **Fix frontend overlay integration** - Verify image viewer structure and adjust overlay component
3. **Improve source extraction** - Either require scipy or implement better fallback

### Priority 2 (Important)

4. **Add frequency parameter** - Allow manual frequency specification if header parsing fails
5. **Add better error messages** - Improve user-facing error messages for all failure modes
6. **Add validation** - Validate WCS and image format before processing

### Priority 3 (Nice to Have)

7. **Add query limits** - Limit catalog query results
8. **Add caching** - Cache catalog queries and validation results
9. **Add progress indicators** - Show progress for long-running validations

---

## Testing Recommendations

1. **Integration Tests:**
   - Test with real MS files and images
   - Test with various image formats
   - Test with missing dependencies (scipy)
   - Test with non-standard WCS

2. **API Tests:**
   - Test path encoding/decoding
   - Test with invalid image IDs
   - Test error handling

3. **Frontend Tests:**
   - Test overlay rendering with different image viewers
   - Test validation panel with various result states
   - Test error states

4. **Edge Case Tests:**
   - Empty catalogs
   - No sources detected
   - Very large fields
   - Missing WCS keywords

