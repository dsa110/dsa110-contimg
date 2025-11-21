# Image Filters Backend Implementation

**Date:** 2025-11-12  
**Endpoint:** `GET /api/images`  
**File:** `src/dsa110_contimg/api/routers/images.py`

## Summary

Extended the `/api/images` endpoint to support advanced filtering parameters
including date range, declination range, quality threshold, and calibrator
detection status.

## New Query Parameters

### Date Range Filters

- `start_date` (str, optional): Start date filter in ISO 8601 format
- `end_date` (str, optional): End date filter in ISO 8601 format
- **Implementation:** Filters by `created_at` timestamp column
- **Example:** `?start_date=2025-01-01T00:00:00Z&end_date=2025-01-31T23:59:59Z`

### Declination Range Filters

- `dec_min` (float, optional): Minimum declination in degrees
- `dec_max` (float, optional): Maximum declination in degrees
- **Implementation:** Post-filtering by extracting RA/Dec from FITS file headers
- **Limitation:** Requires opening FITS files, which is slower than database
  queries
- **Example:** `?dec_min=-30&dec_max=30`

### Quality Threshold Filter

- `noise_max` (float, optional): Maximum noise level in Jy
- **Implementation:** Database filter on `noise_jy` column
- **Example:** `?noise_max=0.001` (1 mJy)

### Calibrator Detection Filter

- `has_calibrator` (bool, optional): Filter by calibrator detection status
- **Implementation:** Heuristic check on MS path patterns (looks for 'cal',
  'calibrator', '3c', 'j1331')
- **Limitation:** Uses path pattern matching, not actual calibrator detection
  results
- **Example:** `?has_calibrator=true`

## Implementation Details

### Database-Level Filters (Efficient)

These filters are applied at the SQL query level:

- `ms_path` - LIKE search
- `image_type` - Exact match
- `pbcor` - Boolean match
- `start_date` / `end_date` - Timestamp comparison
- `noise_max` - Numeric comparison

### Post-Processing Filters (Less Efficient)

These filters require additional processing after database query:

- `dec_min` / `dec_max` - Extract RA/Dec from FITS headers
- `has_calibrator` - Pattern matching on MS path

**Performance Note:** When declination or calibrator filters are used, the
endpoint fetches more rows (limit + offset + 1000) to account for
post-filtering, then applies offset/limit after filtering.

### RA/Dec Extraction

The endpoint now extracts `center_ra_deg` and `center_dec_deg` from FITS file
headers when available, populating these fields in the `ImageInfo` response.
This enables:

- Declination filtering (post-processing)
- Sky map visualization (frontend)
- Coordinate-based searches (future)

## Response Changes

The endpoint now populates `center_ra_deg` and `center_dec_deg` in `ImageInfo`
objects when FITS files are available and contain WCS information.

## Limitations

1. **Declination Filtering Performance:**
   - Requires opening FITS files for each image
   - Slower than database-level filtering
   - **Recommendation:** Store `center_ra_deg` and `center_dec_deg` in database
     for better performance

2. **Calibrator Detection:**
   - Uses heuristic pattern matching on MS path
   - May not accurately reflect actual calibrator detection
   - **Recommendation:** Store calibrator detection status in database or join
     with calibrator table

3. **Total Count Accuracy:**
   - When post-filtering is applied, total count may be inaccurate if fetch
     limit is reached
   - **Recommendation:** Implement proper counting with post-filters or store
     coordinates in DB

## Future Improvements

1. **Database Schema Enhancement:**
   - Add `center_ra_deg` and `center_dec_deg` columns to `images` table
   - Add `has_calibrator` boolean column
   - Populate during image ingestion/processing

2. **Performance Optimization:**
   - Move declination filtering to SQL WHERE clause once coordinates are in DB
   - Add database indexes on `center_dec_deg` for faster filtering

3. **Calibrator Detection:**
   - Join with calibrator detection table if available
   - Store detection results during processing

## Testing

Test the endpoint with various filter combinations:

```bash
# Date range filter
curl "http://localhost:8000/api/images?start_date=2025-01-01T00:00:00Z&end_date=2025-01-31T23:59:59Z"

# Declination range filter
curl "http://localhost:8000/api/images?dec_min=-30&dec_max=30"

# Quality threshold filter
curl "http://localhost:8000/api/images?noise_max=0.001"

# Calibrator filter
curl "http://localhost:8000/api/images?has_calibrator=true"

# Combined filters
curl "http://localhost:8000/api/images?start_date=2025-01-01T00:00:00Z&dec_min=-30&dec_max=30&noise_max=0.001&has_calibrator=true"
```

---

**Status:** ✅ Implementation Complete  
**Frontend Integration:** ✅ Already implemented in `ImageBrowser.tsx`
