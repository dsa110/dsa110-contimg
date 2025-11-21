# Source Search Button Investigation

## Summary

Investigation into why the Search button on the Source Monitoring page appears
disabled when it should be enabled.

## Findings

### 1. Button Disabled Logic

**Location**: `frontend/src/pages/SourceMonitoringPage.tsx` line 201

```typescript
disabled={!sourceId.trim() && !showAdvancedFilters}
```

**Analysis**: This logic is **correct**. The button should be enabled when:

- `sourceId.trim()` is truthy (has text), OR
- `showAdvancedFilters` is true

The button is disabled only when both conditions are false (no source ID AND
advanced filters not shown).

### 2. State Management

**Location**: `frontend/src/pages/SourceMonitoringPage.tsx` lines 42, 217

```typescript
const [sourceId, setSourceId] = useState("");
// ...
<TextField
  value={sourceId}
  onChange={(e) => setSourceId(e.target.value)}
  // ...
/>
```

**Analysis**: The state management appears correct. The TextField is properly
bound to `sourceId` state with `onChange` handler.

### 3. API Endpoint

**Location**: `src/dsa110_contimg/api/routers/photometry.py` line 42

**Endpoint**: `POST /api/sources/search`

**Expected Request Body**:

```json
{
  "source_id": "NVSS J123456.7+420312"
}
```

**Response**: `SourceSearchResponse` with `sources` array and `total` count.

### 4. Source ID Format

**Expected Format**: `NVSS J123456.7+420312` (with decimal point) or
`NVSS J123456+420312` (without decimal point)

**Database Query**: The API uses both exact match and LIKE pattern matching:

```python
WHERE source_id = ? OR source_id LIKE ?
```

### 5. Potential Bug in `handleSearch`

**Location**: `frontend/src/pages/SourceMonitoringPage.tsx` lines 54-68

```typescript
const handleSearch = () => {
  const request: SourceSearchRequest = {};

  if (sourceId.trim()) {
    request.source_id = sourceId.trim();
  }

  if (showAdvancedFilters) {
    request.limit = 1000;
  } else {
    request.limit = 100;
  }

  setSearchRequest(Object.keys(request).length > 0 ? request : null);
};
```

**Issue**: The `request` object will always have at least the `limit` key, so
`Object.keys(request).length > 0` will always be true, even when `source_id` is
not set. This means:

- The search query will be triggered even without a source ID
- The API will return an empty result (since it requires `source_id`)
- This is inefficient but not a critical bug

**Recommended Fix**:

```typescript
const handleSearch = () => {
  const request: SourceSearchRequest = {};

  if (sourceId.trim()) {
    request.source_id = sourceId.trim();
  } else if (!showAdvancedFilters) {
    // No source ID and no advanced filters - don't search
    setSearchRequest(null);
    return;
  }

  if (showAdvancedFilters) {
    request.limit = 1000;
  } else {
    request.limit = 100;
  }

  setSearchRequest(request);
};
```

### 6. API Query Hook

**Location**: `frontend/src/api/queries.ts` lines 240-252

```typescript
export function useSourceSearch(
  request: SourceSearchRequest | null
): UseQueryResult<SourceSearchResponse> {
  return useQuery({
    queryKey: ["sources", request],
    queryFn: async () => {
      if (!request) {
        return { sources: [], total: 0 };
      }
      const response = await apiClient.post<SourceSearchResponse>(
        "/sources/search",
        request
      );
      return response.data;
    },
    enabled: !!request,
  });
}
```

**Analysis**: The query hook is correctly configured. It only runs when
`request` is truthy.

## Root Cause Analysis

The button disabled logic appears correct. Possible reasons for the button
appearing disabled:

1. **React State Not Updating**: The `sourceId` state might not be updating when
   text is entered
2. **Visual Styling Issue**: The button might be enabled but appear disabled due
   to CSS
3. **Browser Console Errors**: JavaScript errors might be preventing state
   updates
4. **Component Re-rendering Issue**: The component might not be re-rendering
   when state changes

## Testing Recommendations

1. **Verify State Updates**: Add console logging to verify `sourceId` state
   updates:

   ```typescript
   useEffect(() => {
     console.log("sourceId:", sourceId, "trimmed:", sourceId.trim());
   }, [sourceId]);
   ```

2. **Check Browser Console**: Look for JavaScript errors that might prevent
   state updates

3. **Test with Valid Source ID**: Use a known valid source ID from the database:
   - `NVSS J123456.7+420312` (from test data)
   - Or query the database for actual source IDs

4. **Test Advanced Filters**: Enable advanced filters and verify the button
   becomes enabled

## API Endpoint Verification

**Endpoint**: `POST /api/sources/search`

**Backend Implementation**: `src/dsa110_contimg/api/routers/photometry.py:42`

**Database Function**: `src/dsa110_contimg/api/data_access.py:595` -
`fetch_source_timeseries()`

**Expected Behavior**:

- Returns `SourceSearchResponse` with sources array
- Returns empty array if source not found
- Uses SQL LIKE pattern matching for partial matches

## Recommended Actions

1. **Fix `handleSearch` function** to properly handle empty source ID case
2. **Add debugging** to verify state updates
3. **Test with actual source IDs** from the database
4. **Verify API endpoint** is accessible and working
5. **Check browser console** for any JavaScript errors

## Source ID Format Validation

The code does not appear to validate the source ID format. The API accepts any
string and attempts to match it in the database. Consider adding format
validation if needed:

```typescript
const isValidSourceId = (id: string): boolean => {
  // NVSS format: NVSS J123456.7+420312 or NVSS J123456+420312
  return /^NVSS J\d{6}(\.\d)?[+-]\d{5,6}$/.test(id.trim());
};
```
