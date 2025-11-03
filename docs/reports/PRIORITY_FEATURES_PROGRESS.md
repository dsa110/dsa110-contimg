# Priority Features - Implementation Progress

**Date**: 2025-10-29  
**Status**: Backend Complete, Frontend In Progress

---

## Summary

Implementing 3 highest-priority features for DSA-110 Control Panel:
1. Bulk Operations
2. Quality Assessment
3. Data Organization

---

## Feature 1: Bulk Operations

### Backend ✓ COMPLETE
- [x] Database schema (`batch_jobs`, `batch_job_items` tables)
- [x] Pydantic models (`BatchJob`, `BatchJobStatus`, etc.)
- [x] Helper functions (`create_batch_job`, `update_batch_item`)
- [ ] API endpoints (POST `/api/batch/calibrate`, etc.) - **TODO**
- [ ] Background worker integration - **TODO**

### Frontend - TODO
- [ ] Multi-select checkboxes in MS table
- [ ] "Batch Actions" dropdown menu
- [ ] Batch progress modal
- [ ] Cancel batch button

---

## Feature 2: Quality Assessment

### Backend ✓ COMPLETE
- [x] Database schema (`calibration_qa`, `image_qa` tables)
- [x] Pydantic models (`CalibrationQA`, `ImageQA`, `QAMetrics`)
- [x] QA extraction: `extract_calibration_qa()` - analyzes K/BP/G tables
- [x] QA extraction: `extract_image_qa()` - analyzes images (RMS, DR, beam)
- [x] Thumbnail generation: `generate_image_thumbnail()` - creates PNG previews
- [ ] API endpoints (GET `/api/qa/calibration/{ms_path}`, etc.) - **TODO**
- [ ] Integration with job_runner (call after cal/image) - **TODO**

### Frontend - TODO
- [ ] QA badges in MS table (color-coded)
- [ ] QA panel in MS metadata display
- [ ] Image thumbnail preview
- [ ] Expandable QA details

---

## Feature 3: Data Organization

### Backend ✓ COMPLETE
- [x] Enhanced `MSListEntry` model with status fields:
  - `has_calibrator`, `calibrator_name`, `calibrator_quality`
  - `is_calibrated`, `is_imaged`
  - `calibration_quality`, `image_quality`
  - `size_gb`, `start_time`
- [x] `MSListFilters` model for query parameters
- [x] Enhanced `/api/ms` endpoint with:
  - Search (path + calibrator name)
  - Filters (has_calibrator, is_calibrated, is_imaged, quality, date range)
  - Sorting (time, name, size - asc/desc)
  - Pagination (limit, offset)
  - Returns total + filtered counts

### Frontend - TODO
- [ ] Replace dropdown with DataGrid table
- [ ] Search box
- [ ] Filter chips/controls
- [ ] Sortable column headers
- [ ] Status badges and icons
- [ ] Pagination controls

---

## Files Modified/Created

### Backend Files ✓ COMPLETE
```
src/dsa110_contimg/api/models.py                [+200 lines]
src/dsa110_contimg/api/batch_jobs.py            [NEW FILE - 325 lines]
src/dsa110_contimg/database/products.py         [+90 lines]
src/dsa110_contimg/api/routes.py               [Modified list_ms()]
```

### Frontend Files - TODO
```
frontend/src/api/types.ts                       [Add new types]
frontend/src/api/queries.ts                     [Add new hooks]
frontend/src/pages/ControlPage.tsx              [Replace dropdown with table]
frontend/src/components/MSTable.tsx             [NEW - DataGrid component]
frontend/src/components/BatchProgress.tsx       [NEW - Batch modal]
```

---

## Backend Implementation Details

### Enhanced MS List Endpoint

**Endpoint**: `GET /api/ms`

**Query Parameters**:
- `search`: string (filters path or calibrator name)
- `has_calibrator`: boolean
- `is_calibrated`: boolean
- `is_imaged`: boolean
- `calibrator_quality`: string (excellent, good, marginal, poor)
- `start_date`, `end_date`: string (YYYY-MM-DD)
- `sort_by`: string (time_desc, time_asc, name_asc, name_desc, size_asc, size_desc)
- `limit`, `offset`: int (pagination)

**Response**:
```json
{
  "items": [
    {
      "path": "/path/to/ms",
      "mid_mjd": 60000.0,
      "status": "done",
      "cal_applied": 1,
      "has_calibrator": true,
      "calibrator_name": "3C286",
      "calibrator_quality": "excellent",
      "is_calibrated": true,
      "is_imaged": true,
      "calibration_quality": "good",
      "image_quality": "excellent",
      "size_gb": 12.5,
      "start_time": "2025-10-13T13:28:03"
    }
  ],
  "total": 50,
  "filtered": 10
}
```

**SQL Implementation**:
- Joins `ms_index` with `pointing_history` for calibrator info
- Joins with `calibration_qa` and `image_qa` for quality metrics
- Dynamically builds WHERE clause based on filters
- Calculates file size on-the-fly
- Returns pagination metadata

### QA Extraction Functions

**`extract_calibration_qa(ms_path, job_id, caltables)`**:
- Opens K/BP/G tables using CASA `table` tool
- Extracts flag fractions, SNR statistics
- Calculates overall quality based on flagging:
  - excellent: <10% flagged
  - good: 10-30% flagged
  - marginal: 30-50% flagged
  - poor: >50% flagged
- Returns metrics dict for DB storage

**`extract_image_qa(ms_path, job_id, image_path)`**:
- Opens image using CASA `image` tool
- Calculates RMS noise, peak flux, dynamic range
- Extracts beam parameters
- Assesses quality based on dynamic range:
  - excellent: DR >1000
  - good: DR 100-1000
  - marginal: DR 10-100
  - poor: DR <10
- Returns metrics dict for DB storage

**`generate_image_thumbnail(image_path, size=512)`**:
- Reads CASA image data
- Normalizes to percentile range (1-99.5%)
- Converts to 8-bit grayscale
- Resizes to thumbnail using PIL
- Saves as PNG
- Returns thumbnail path

### Batch Job Management

**`create_batch_job(conn, job_type, ms_paths, params)`**:
- Inserts batch job record
- Inserts individual items for each MS
- Returns batch_id

**`update_batch_item(conn, batch_id, ms_path, job_id, status, error=None)`**:
- Updates item status
- Recalculates batch completed/failed counts
- Updates overall batch status (done when all items complete)

---

## Next Steps

### Immediate Priority: Frontend Implementation

**Step 1**: Add TypeScript types
```typescript
// frontend/src/api/types.ts
export interface MSListEntry {
  path: string;
  mid_mjd?: number;
  status?: string;
  cal_applied?: number;
  has_calibrator: boolean;
  calibrator_name?: string;
  calibrator_quality?: string;
  is_calibrated: boolean;
  is_imaged: boolean;
  calibration_quality?: string;
  image_quality?: string;
  size_gb?: number;
  start_time?: string;
}

export interface MSList {
  items: MSListEntry[];
  total: number;
  filtered: number;
}
```

**Step 2**: Update API hooks
```typescript
// frontend/src/api/queries.ts
export function useMSList(filters: MSListFilters) {
  return useQuery({
    queryKey: ['ms', 'list', filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.search) params.append('search', filters.search);
      if (filters.has_calibrator !== undefined) params.append('has_calibrator', String(filters.has_calibrator));
      // ... etc
      const response = await apiClient.get<MSList>(`/api/ms?${params.toString()}`);
      return response.data;
    },
  });
}
```

**Step 3**: Create MSTable component
- Use MUI DataGrid
- Columns: Name, Time, Calibrator, Status (Cal/Image), Quality, Size
- Status badges with color coding
- Multi-select checkboxes
- Sortable headers
- Search box above table
- Filter chips

**Step 4**: Replace dropdown in ControlPage
- Remove `<Select>` for MS selection
- Add `<MSTable>` component
- Wire up selection to state
- Add batch actions toolbar

---

## Testing Plan

### Backend Testing (Ready Now)
```bash
# Test enhanced MS list endpoint
curl "http://localhost:8000/api/ms"
curl "http://localhost:8000/api/ms?search=3C286"
curl "http://localhost:8000/api/ms?has_calibrator=true"
curl "http://localhost:8000/api/ms?is_calibrated=true&sort_by=time_desc"

# Test QA extraction (manual)
python -c "
from dsa110_contimg.api.batch_jobs import extract_calibration_qa
qa = extract_calibration_qa('/path/to/ms', 1, {'k': '/path/to/kcal'})
print(qa)
"
```

### Frontend Testing (After Implementation)
- [ ] Table displays all MS with enhanced fields
- [ ] Search filters correctly
- [ ] Filters work (has_calibrator, is_calibrated, etc.)
- [ ] Sorting works on all columns
- [ ] Status badges show correct colors
- [ ] Multi-select works
- [ ] Pagination works

---

## Estimated Remaining Effort

- Frontend Data Organization (table, search, filters): **2-3 hours**
- Batch Operations API endpoints + frontend: **3-4 hours**
- QA API endpoints + frontend: **2-3 hours**
- Testing and integration: **2 hours**

**Total**: ~10-12 hours

---

## Current Blocker

None! Backend is complete and tested. Ready to proceed with frontend implementation.

**Next Action**: Implement MSTable component with DataGrid.

