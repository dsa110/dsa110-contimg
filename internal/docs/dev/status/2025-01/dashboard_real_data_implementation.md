# Dashboard Real Data Implementation

## Summary

Successfully replaced all mock data endpoints with real database-backed implementations for:
- ✅ Dashboard Page (ESE Candidates, Alert History)
- ✅ Mosaic Gallery Page (Mosaic Query)
- ✅ Source Monitoring Page (Source Timeseries)

## Changes Made

### 1. Backend Models (`src/dsa110_contimg/api/models.py`)

Added new Pydantic models:
- `ESECandidate` - ESE candidate source with variability stats
- `ESECandidatesResponse` - Response wrapper for ESE candidates
- `Mosaic` - Mosaic image metadata
- `MosaicQueryResponse` - Response wrapper for mosaic queries
- `SourceFluxPoint` - Single flux measurement point
- `SourceTimeseries` - Source flux timeseries with statistics
- `SourceSearchResponse` - Response wrapper for source search
- `AlertHistory` - Alert history entry

### 2. Data Access Functions (`src/dsa110_contimg/api/data_access.py`)

Added new database query functions:
- `fetch_ese_candidates()` - Queries `ese_candidates` and `variability_stats` tables
- `fetch_mosaics()` - Queries `mosaics` table with time range filtering
- `fetch_source_timeseries()` - Queries `photometry` table and calculates statistics
- `fetch_alert_history()` - Queries `alert_history` table

All functions:
- Check for table existence before querying
- Handle missing databases gracefully
- Return empty lists/None when no data is available
- Use parameterized queries for security

### 3. API Endpoints (`src/dsa110_contimg/api/routes.py`)

Updated endpoints to use real data:

#### `/api/ese/candidates` (GET)
- **Before**: Returned `generate_mock_ese_candidates(5)`
- **After**: Queries `ese_candidates` table joined with `variability_stats`
- **Parameters**: `limit` (default: 50), `min_sigma` (default: 5.0)
- **Returns**: `ESECandidatesResponse` with real ESE candidates

#### `/api/mosaics/query` (POST)
- **Before**: Returned `generate_mock_mosaics(start_time, end_time)`
- **After**: Queries `mosaics` table filtered by time range (MJD)
- **Parameters**: `start_time`, `end_time` (ISO format datetime strings)
- **Returns**: `MosaicQueryResponse` with real mosaics from database

#### `/api/mosaics/create` (POST)
- **Before**: Returned mock response with `status: 'pending'`
- **After**: Returns `status: 'not_implemented'` with message
- **Note**: Mosaic creation via API is not yet implemented. Users should use CLI tools.
- **Future**: Can be integrated with mosaic generation pipeline

#### `/api/sources/search` (POST)
- **Before**: Returned `generate_mock_source_timeseries(source_id)`
- **After**: Queries `photometry` table for source measurements
- **Parameters**: `source_id` (e.g., "NVSS J123456+420312")
- **Returns**: `SourceSearchResponse` with:
  - Flux timeseries from photometry measurements
  - Calculated statistics (mean, std, chi-square)
  - Variability detection (chi_sq_nu > 3.0)

#### `/api/alerts/history` (GET)
- **Before**: Returned `generate_mock_alert_history(limit)`
- **After**: Queries `alert_history` table
- **Parameters**: `limit` (default: 50)
- **Returns**: List of `AlertHistory` objects

## Database Tables Used

### ESE Candidates
- `ese_candidates` - Flagged ESE candidates
- `variability_stats` - Pre-computed variability statistics
- `photometry` - Flux measurements (for first/last detection times)

### Mosaics
- `mosaics` - Mosaic image metadata with time ranges

### Source Timeseries
- `photometry` - Flux measurements with `source_id`, `mjd`, `peak_jyb`

### Alert History
- `alert_history` - Log of alerts sent

## Graceful Degradation

All endpoints handle missing data gracefully:
- If database doesn't exist → Returns empty results
- If tables don't exist → Returns empty results
- If no matching data → Returns empty results
- Frontend displays appropriate "No data" messages

## Testing Notes

### ESE Candidates
- Requires `ese_candidates` and `variability_stats` tables
- Will return empty list if tables don't exist
- Filters by `min_sigma` threshold (default: 5.0)
- Only returns `status = 'active'` candidates

### Mosaics
- Requires `mosaics` table
- Time range filtering uses MJD conversion
- Returns mosaics that overlap with requested time range

### Source Search
- Requires `photometry` table with `source_id` column
- Matches by exact `source_id` or pattern match
- Calculates statistics on-the-fly from flux measurements
- Returns None if no measurements found

### Alert History
- Requires `alert_history` table
- Returns most recent alerts first
- Limited by `limit` parameter

## Frontend Compatibility

All endpoints maintain the same response format as the mock data, so:
- ✅ No frontend changes required
- ✅ Existing React Query hooks work unchanged
- ✅ TypeScript types match exactly

## Remaining Work

### Mosaic Creation
The `/api/mosaics/create` endpoint currently returns "not_implemented". To fully implement:
1. Integrate with mosaic CLI tools (`dsa110_contimg.mosaic.cli`)
2. Queue mosaic generation as background job
3. Track job status in database
4. Return job ID for status tracking

This is a future enhancement and doesn't block the dashboard functionality.

## Files Modified

1. `src/dsa110_contimg/api/models.py` - Added 7 new models
2. `src/dsa110_contimg/api/data_access.py` - Added 4 new query functions
3. `src/dsa110_contimg/api/routes.py` - Updated 4 endpoints to use real data

## Files No Longer Needed

The mock data functions in `src/dsa110_contimg/api/mock_data.py` are no longer used by the API endpoints, but the file is kept for:
- Testing purposes
- Reference implementation
- Future mock data needs

