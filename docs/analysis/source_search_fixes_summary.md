# Source Search Button Investigation - Summary & Fixes

## Investigation Summary

### Issues Found

1. **Bug in `handleSearch` function**: The function would always create a search
   request (even without `source_id`) because `limit` was always set, making
   `Object.keys(request).length > 0` always true.

2. **Missing advanced filters in search request**: The advanced filters
   (variability threshold, declination range, ESE only) were not being included
   in the search request, even though the UI allowed users to set them.

3. **Backend API limitation**: The backend API endpoint (`/api/sources/search`)
   only supports `source_id` parameter and ignores advanced filter parameters.
   This is a backend limitation that needs to be addressed separately.

### Fixes Applied

1. **Fixed `handleSearch` function**
   (`frontend/src/pages/SourceMonitoringPage.tsx`):
   - Added early return when no source ID and no advanced filters are set
   - Now properly includes advanced filters in the search request when
     `showAdvancedFilters` is true
   - Prevents unnecessary API calls when no search criteria are provided

2. **Button disabled logic**: Verified as correct - button is enabled when:
   - `sourceId.trim()` is truthy, OR
   - `showAdvancedFilters` is true

### Source ID Format

**Expected Format**: `NVSS J123456.7+420312` (with decimal point) or
`NVSS J123456+420312` (without decimal point)

**Database Query**: The API uses both exact match and LIKE pattern matching:

```sql
WHERE source_id = ? OR source_id LIKE ?
```

### API Endpoint

**Endpoint**: `POST /api/sources/search`

**Request Body**:

```json
{
  "source_id": "NVSS J123456.7+420312",
  "limit": 100,
  "variability_threshold": 5,
  "ese_only": false,
  "dec_min": -90,
  "dec_max": 90
}
```

**Response**: `SourceSearchResponse` with `sources` array and `total` count.

**Note**: Currently, the backend only uses `source_id` and ignores other
parameters. Advanced filter support needs to be implemented in the backend.

### Testing Recommendations

1. **Test with valid source ID**: Use `NVSS J123456.7+420312` (from test data)
   or query the database for actual source IDs

2. **Test button enabled state**:
   - Enter text in source ID field → button should be enabled
   - Show advanced filters → button should be enabled
   - Clear source ID and hide advanced filters → button should be disabled

3. **Test search functionality**:
   - Search with valid source ID → should return results
   - Search with invalid source ID → should return empty results
   - Search with advanced filters → filters are sent but currently ignored by
     backend

4. **Verify API endpoint**: Check that `/api/sources/search` is accessible and
   returns expected format

### Known Limitations

1. **Backend doesn't support advanced filters**: The API endpoint only processes
   `source_id` and ignores other filter parameters. This needs backend
   implementation.

2. **No source ID format validation**: The frontend doesn't validate the source
   ID format before sending the request.

### Next Steps

1. **Backend implementation**: Add support for advanced filter parameters in the
   `/api/sources/search` endpoint
2. **Frontend validation**: Add source ID format validation (optional, since API
   uses LIKE matching)
3. **Testing**: Test with actual source IDs from the database
4. **Documentation**: Update API documentation to reflect advanced filter
   support (once implemented)
