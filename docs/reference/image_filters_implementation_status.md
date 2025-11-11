# Image Filters Implementation Status

**Date:** 2025-01-XX  
**Endpoint:** `GET /api/images`  
**Component:** `ImageBrowser.tsx`

## Implementation Summary

### ✅ Fully Working Filters

These filters are implemented at the SQL level and work efficiently:

1. **Date Range** (`start_date`, `end_date`)
   - **Status:** ✅ Fully implemented
   - **Performance:** Fast (SQL WHERE clause)
   - **Accuracy:** Accurate pagination
   - **Implementation:** Filters by `created_at` timestamp column

2. **Quality Threshold** (`noise_max`)
   - **Status:** ✅ Fully implemented
   - **Performance:** Fast (SQL WHERE clause)
   - **Accuracy:** Accurate pagination
   - **Implementation:** Filters by `noise_jy` column
   - **Unit:** Jy (converted from mJy in frontend)

3. **Basic Filters** (`ms_path`, `image_type`, `pbcor`)
   - **Status:** ✅ Fully implemented
   - **Performance:** Fast (SQL WHERE clause)
   - **Accuracy:** Accurate pagination

### ⚠️ Experimental Filters (Limited Functionality)

These filters are implemented but have performance and accuracy limitations:

1. **Declination Range** (`dec_min`, `dec_max`)
   - **Status:** ⚠️ Experimental (post-processing)
   - **Performance:** Slow (requires opening FITS files)
   - **Accuracy:** Pagination may be inaccurate
   - **Implementation:** Extracts RA/Dec from FITS headers after database query
   - **Limitation:** Not stored in database, requires file I/O
   - **Recommendation:** Add `center_ra_deg` and `center_dec_deg` columns to `images` table

2. **Calibrator Detection** (`has_calibrator`)
   - **Status:** ⚠️ Experimental (heuristic)
   - **Performance:** Moderate (pattern matching)
   - **Accuracy:** May have false positives/negatives
   - **Implementation:** Pattern matching on MS path (looks for 'cal', 'calibrator', '3c', 'j1331')
   - **Limitation:** Not based on actual calibrator detection results
   - **Recommendation:** Store calibrator detection status in database or join with calibrator registry

## Frontend Implementation

### ✅ Completed Features

- Material-UI form components (TextField, Slider, Checkbox, DateTimePicker)
- URL query parameter synchronization (shareable filtered views)
- Collapsible advanced filters section
- Unit conversion (mJy display ↔ Jy API)
- Clear filters button
- Proper TypeScript typing
- useCallback optimization for event handlers

### UI Components

- **Date Range:** DateTimePicker with UTC timezone
- **Declination Range:** Slider (-90° to +90°)
- **Quality Threshold:** TextField with mJy input
- **Calibrator Flag:** Checkbox control
- **Clear Filters:** Button to reset all filters

## Backend Implementation

### SQL-Level Filters (Efficient)

```python
# Date range
if start_date:
    where_clauses.append("created_at >= ?")
    params.append(start_timestamp)

# Noise threshold
if noise_max is not None:
    where_clauses.append("noise_jy <= ?")
    params.append(noise_max)
```

### Post-Processing Filters (Less Efficient)

```python
# Declination filter (requires FITS file access)
for row in rows:
    fits_path = get_fits_path(row["path"])
    # Extract dec from FITS header
    # Apply filter
    
# Calibrator filter (heuristic pattern matching)
if has_calibrator:
    # Check MS path patterns
    has_cal = any(pattern in ms_path.lower() for pattern in patterns)
```

## Known Limitations

1. **Declination Filtering Performance**
   - Requires opening FITS files for each image
   - Slower than database queries
   - May break pagination accuracy
   - **Workaround:** Store coordinates in database

2. **Calibrator Detection Accuracy**
   - Uses path pattern matching, not actual detection
   - May have false positives/negatives
   - **Workaround:** Store detection status in database

3. **Total Count Accuracy**
   - Post-filtering may cause inaccurate total counts
   - **Workaround:** Store coordinates in database for SQL-level filtering

## Recommendations

### Short-Term (Current Implementation)

- ✅ Use working filters (date, noise) for production
- ⚠️ Use experimental filters (dec, calibrator) with caution
- 📝 Document limitations clearly in API docs

### Long-Term (Recommended Improvements)

1. **Database Schema Enhancement**
   ```sql
   ALTER TABLE images ADD COLUMN center_ra_deg REAL;
   ALTER TABLE images ADD COLUMN center_dec_deg REAL;
   ALTER TABLE images ADD COLUMN has_calibrator INTEGER DEFAULT 0;
   ```

2. **Data Backfill**
   - Extract coordinates from existing FITS files
   - Populate `center_ra_deg` and `center_dec_deg` columns
   - Flag calibrator detections from processing logs

3. **Update Insertion Code**
   - Extract coordinates during image ingestion
   - Store in database immediately
   - Flag calibrator detections during processing

4. **Performance Optimization**
   - Move declination filtering to SQL WHERE clause
   - Add database indexes on `center_dec_deg`
   - Implement proper calibrator detection flagging

## Testing

### Working Filters

```bash
# Date range
curl "http://localhost:8000/api/images?start_date=2025-01-01T00:00:00Z&end_date=2025-01-31T23:59:59Z"

# Noise threshold
curl "http://localhost:8000/api/images?noise_max=0.001"

# Combined
curl "http://localhost:8000/api/images?start_date=2025-01-01T00:00:00Z&noise_max=0.001&limit=10"
```

### Experimental Filters

```bash
# Declination range (slow, may have pagination issues)
curl "http://localhost:8000/api/images?dec_min=-30&dec_max=30&limit=10"

# Calibrator detection (heuristic, may have false positives)
curl "http://localhost:8000/api/images?has_calibrator=true&limit=10"
```

## Frontend Usage

The frontend automatically handles:
- Unit conversion (mJy ↔ Jy)
- URL parameter synchronization
- Filter state management
- Clear filters functionality

Users can:
- Share filtered views via URL
- Use browser back/forward buttons
- Clear all filters with one click
- Collapse/expand advanced filters

---

**Status:** ✅ Working filters ready for production  
**Status:** ⚠️ Experimental filters available but limited  
**Next Steps:** Database schema enhancement for full functionality

