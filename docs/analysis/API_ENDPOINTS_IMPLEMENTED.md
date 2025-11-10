# API Endpoints Implementation Summary

## Overview

New API endpoints have been implemented to support the Phase 1 detail pages (SourceDetailPage and ImageDetailPage).

## New Endpoints

### Source Endpoints

#### `GET /api/sources/{source_id}`
**Description:** Get detailed information for a source.

**Response Model:** `SourceDetail`
```python
{
    "id": str,
    "name": Optional[str],
    "ra_deg": float,
    "dec_deg": float,
    "catalog": str,
    "n_meas": int,
    "n_meas_forced": int,
    "mean_flux_jy": Optional[float],
    "std_flux_jy": Optional[float],
    "max_snr": Optional[float],
    "is_variable": bool,
    "ese_probability": Optional[float],
    "new_source": bool,
    "variability_metrics": Optional[VariabilityMetrics]
}
```

**Implementation:**
- Uses `Source` class from `dsa110_contimg.photometry.source`
- Calculates variability metrics if available
- Counts forced vs detected measurements
- Computes flux statistics

#### `GET /api/sources/{source_id}/detections`
**Description:** Get paginated detections/measurements for a source.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 25, max: 100): Items per page

**Response Model:** `DetectionList`
```python
{
    "items": List[Detection],
    "total": int,
    "page": int,
    "page_size": int
}
```

**Detection Model:**
```python
{
    "id": Optional[int],
    "name": Optional[str],
    "image_id": Optional[int],
    "image_path": Optional[str],
    "ra": float,
    "dec": float,
    "flux_peak": float,  # mJy/beam
    "flux_peak_err": Optional[float],  # mJy/beam
    "flux_int": Optional[float],  # mJy
    "flux_int_err": Optional[float],  # mJy
    "snr": Optional[float],
    "forced": bool,
    "frequency": Optional[float],  # MHz
    "mjd": Optional[float],
    "measured_at": Optional[datetime]
}
```

**Implementation:**
- Loads measurements from `Source` class
- Maps image paths to image IDs from database
- Handles flux unit conversion (Jy ↔ mJy)
- Paginates results client-side (from DataFrame)

### Image Endpoints

#### `GET /api/images/{image_id}`
**Description:** Get detailed information for an image.

**Response Model:** `ImageDetail`
```python
{
    "id": int,
    "name": Optional[str],
    "path": str,
    "ms_path": Optional[str],
    "ra": Optional[float],
    "dec": Optional[float],
    "ra_hms": Optional[str],
    "dec_dms": Optional[str],
    "l": Optional[float],  # Galactic longitude
    "b": Optional[float],  # Galactic latitude
    "beam_bmaj": Optional[float],  # degrees
    "beam_bmin": Optional[float],  # degrees
    "beam_bpa": Optional[float],  # degrees
    "rms_median": Optional[float],  # mJy
    "rms_min": Optional[float],  # mJy
    "rms_max": Optional[float],  # mJy
    "frequency": Optional[float],  # MHz
    "bandwidth": Optional[float],  # MHz
    "datetime": Optional[datetime],
    "created_at": Optional[datetime],
    "n_meas": int,
    "n_runs": int,
    "type": str,
    "pbcor": bool
}
```

**Implementation:**
- Queries `images` table in products database
- Extracts WCS and metadata from FITS headers using Astropy
- Counts measurements from `photometry` table
- Converts coordinates to HMS/DMS format
- Converts beam parameters from arcsec to degrees
- Converts RMS from Jy to mJy

#### `GET /api/images/{image_id}/measurements`
**Description:** Get paginated measurements/detections for an image.

**Query Parameters:**
- `page` (int, default: 1): Page number
- `page_size` (int, default: 25, max: 100): Items per page

**Response Model:** `MeasurementList`
```python
{
    "items": List[Measurement],
    "total": int,
    "page": int,
    "page_size": int
}
```

**Measurement Model:**
```python
{
    "id": Optional[int],
    "name": Optional[str],
    "source_id": Optional[str],
    "ra": float,
    "dec": float,
    "flux_peak": float,  # mJy/beam
    "flux_peak_err": Optional[float],  # mJy/beam
    "flux_int": Optional[float],  # mJy
    "flux_int_err": Optional[float],  # mJy
    "snr": Optional[float],
    "forced": bool,
    "frequency": Optional[float],  # MHz
    "compactness": Optional[float],
    "has_siblings": bool
}
```

**Implementation:**
- Queries `photometry` table filtered by `image_path`
- Maps image ID to image path
- Handles flux unit conversion
- Paginates results server-side

## Models Added

All models added to `src/dsa110_contimg/api/models.py`:

1. `Detection` - Single detection/measurement for a source
2. `DetectionList` - Paginated list of detections
3. `SourceDetail` - Detailed source information
4. `Measurement` - Single measurement/detection in an image
5. `MeasurementList` - Paginated list of measurements
6. `ImageDetail` - Detailed image information

## Frontend Hooks Added

Added to `frontend/src/api/queries.ts`:

1. `useSourceDetail(sourceId)` - Fetch source details
2. `useSourceDetections(sourceId, page, pageSize)` - Fetch paginated detections
3. `useImageDetail(imageId)` - Fetch image details
4. `useImageMeasurements(imageId, page, pageSize)` - Fetch paginated measurements

## Database Dependencies

### Required Tables

1. **`images` table** (products.sqlite3)
   - Columns used: `id`, `path`, `ms_path`, `created_at`, `type`, `beam_major_arcsec`, `beam_minor_arcsec`, `beam_pa_deg`, `noise_jy`, `pbcor`

2. **`photometry` table** (products.sqlite3)
   - Columns used: `source_id`, `image_path`, `ra_deg`, `dec_deg`, `peak_jyb`, `peak_err_jyb`, `flux_int_jy`, `flux_int_err_jy`, `snr`, `forced`, `is_forced`, `mjd`, `measured_at`

### Optional Tables

- `photometry_timeseries` - Preferred table for source measurements (if exists)
- FITS files - For extracting WCS and metadata

## Error Handling

All endpoints:
- Return 404 if resource not found
- Handle missing tables gracefully
- Handle missing columns gracefully
- Log errors for debugging
- Return appropriate HTTP status codes

## Unit Conversion

The endpoints handle unit conversions:
- **Flux:** Jy ↔ mJy (converts if value < 1.0, assumes Jy)
- **Beam:** arcsec ↔ degrees (converts arcsec to degrees)
- **RMS:** Jy ↔ mJy (converts Jy to mJy)
- **Frequency:** Hz ↔ MHz (converts Hz to MHz)

## TODOs / Future Enhancements

1. **ESE Probability Calculation**
   - Currently returns `None`
   - Need to implement ESE detection algorithm

2. **New Source Detection**
   - Currently returns `False`
   - Need to implement catalog matching logic

3. **Image Frequency Extraction**
   - Currently extracts from FITS headers
   - Could also extract from MS metadata

4. **Measurement Frequency**
   - Currently returns `None`
   - Could extract from image metadata

5. **Run Count for Images**
   - Currently returns 0
   - Images aren't directly linked to runs in current schema

6. **Related Sources**
   - Not yet implemented
   - Would need spatial matching logic

7. **Navigation IDs (prev/next)**
   - Not yet implemented
   - Would need to query source/image lists

## Testing

To test the endpoints:

```bash
# Test source detail
curl http://localhost:8000/api/sources/NVSS%20J123456+420312

# Test source detections
curl http://localhost:8000/api/sources/NVSS%20J123456+420312/detections?page=1&page_size=25

# Test image detail
curl http://localhost:8000/api/images/1

# Test image measurements
curl http://localhost:8000/api/images/1/measurements?page=1&page_size=25
```

## Notes

- All endpoints use the existing `Source` class for consistency
- Pagination is implemented server-side for measurements, client-side for detections
- Unit conversions are handled automatically
- Missing data is handled gracefully (returns `None` or empty lists)
- FITS header extraction is optional (falls back gracefully if FITS not available)

