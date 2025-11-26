# API Mosaic Listing and ESE Candidates Implementation

**Date:** 2025-11-25

## Summary

Implemented real database queries for the mosaic listing and ESE candidate
detection API endpoints, replacing placeholder/mock implementations.

## Changes

### Mosaic Listing (`GET /api/mosaics`)

- **New function:** `fetch_mosaics_recent()` in `api/data_access.py`
  - Queries the `mosaics` table ordered by creation time
  - Returns tuple of (mosaics_list, total_count)
  - Handles null/zero MJD values gracefully
  - Includes status, method, image_count, noise_jy, source_count fields

- **Updated endpoint:** `GET /api/mosaics` in both `routers/mosaics.py` and
  `routes.py`
  - Now returns real mosaic data from the products database
  - Supports `limit` query parameter (default: 10, max: 100)

### ESE Candidate Detection (`GET /api/ese/candidates`)

- **Existing implementation:** Already functional in `fetch_ese_candidates()`
- **Bug fix:** Corrected `PIPELINE_PRODUCTS_DB` environment variable in
  `ops/systemd/contimg.env` to point to `products.sqlite3` instead of
  `hdf5.sqlite3`

## API Response Examples

### GET /api/mosaics

```json
{
  "mosaics": [
    {
      "id": 1,
      "name": "mosaic_group_1762566273_...",
      "path": "/stage/dsa110-contimg/mosaics/mosaic_group_1762566273_....fits",
      "status": "completed",
      "start_time": "2025-10-28T13:30:07",
      "end_time": "2025-10-28T14:16:30",
      "created_at": "2025-11-07T17:59:24.697973",
      "image_count": 10,
      "noise_jy": 0.001,
      "source_count": 0
    }
  ],
  "total": 2,
  "limit": 10
}
```

### GET /api/ese/candidates

```json
{
  "candidates": [
    {
      "id": 3,
      "source_id": "NVSS J345678+234567",
      "ra_deg": 64.33,
      "dec_deg": 23.76,
      "max_sigma_dev": 9.5,
      "current_flux_jy": 6.1e-5,
      "baseline_flux_jy": 0.0521,
      "status": "active",
      "notes": "Detected at 9.5σ deviation"
    }
  ],
  "total": 5
}
```

## Tests Added

- `TestFetchMosaicsRecent` in `tests/unit/api/test_data_access.py`
  - `test_fetch_mosaics_recent_success`
  - `test_fetch_mosaics_recent_limit`
  - `test_fetch_mosaics_recent_empty_db`
  - `test_fetch_mosaics_recent_nonexistent_db`

- `TestMosaicListEndpoint` in `tests/unit/api/test_mosaic_endpoints.py`
  - `test_list_mosaics_success`
  - `test_list_mosaics_empty`
  - `test_list_mosaics_with_limit`

## Files Modified

- `backend/src/dsa110_contimg/api/data_access.py` - Added
  `fetch_mosaics_recent()`
- `backend/src/dsa110_contimg/api/routers/mosaics.py` - Added GET /api/mosaics
  endpoint
- `backend/src/dsa110_contimg/api/routes.py` - Updated duplicate endpoint to use
  real data
- `ops/systemd/contimg.env` - Fixed PIPELINE_PRODUCTS_DB path
- `docs/reference/api-endpoints.md` - Documented new endpoint
- `backend/tests/unit/api/test_data_access.py` - Added tests, updated mock
  schema
- `backend/tests/unit/api/test_mosaic_endpoints.py` - Added list endpoint tests
