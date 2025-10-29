# Priority Features Implementation Plan

## Status: In Progress

This document outlines the implementation of the three highest-priority features requested:

1. **Bulk Operations** - Batch processing of multiple MS files
2. **Quality Assessment** - Automatic QA metrics for calibration and imaging
3. **Data Organization** - Enhanced MS listing with search, filter, and sort

---

## Feature 1: Bulk Operations ✓ Models Added

### Backend Components

#### Database Schema ✓ COMPLETE
- `batch_jobs` table: tracks batch job status
- `batch_job_items` table: individual MS within a batch
- Indices for efficient queries

#### Models ✓ COMPLETE
- `BatchJob`: overall batch status
- `BatchJobStatus`: individual item status
- `BatchCalibrateParams`, `BatchApplyParams`, `BatchImageParams`
- `BatchJobCreateRequest`

#### API Endpoints (TODO)
```
POST /api/batch/calibrate   - Create batch calibration job
POST /api/batch/apply       - Create batch apply job
POST /api/batch/image       - Create batch imaging job
GET  /api/batch/{id}        - Get batch job status
GET  /api/batch             - List batch jobs
POST /api/batch/{id}/cancel - Cancel running batch
```

#### Batch Processing Logic (`batch_jobs.py`) ✓ COMPLETE
- `create_batch_job()`: Initialize batch in DB
- `update_batch_item()`: Update item status
- Background worker to process items sequentially

### Frontend Components (TODO)
- Multi-select checkboxes in MS table
- "Batch Actions" dropdown: Calibrate, Apply, Image
- Batch progress modal with per-item status
- Cancel batch button

---

## Feature 2: Quality Assessment ✓ Partial

### Backend Components

#### Database Schema ✓ COMPLETE
- `calibration_qa` table: K/BP/G metrics, flag fractions
- `image_qa` table: RMS, peak flux, dynamic range, beam, thumbnail path

#### Models ✓ COMPLETE
- `CalibrationQA`: per-cal-table metrics
- `ImageQA`: image statistics and quality
- `QAMetrics`: combined view

#### QA Extraction (`batch_jobs.py`) ✓ COMPLETE
- `extract_calibration_qa()`: Analyze cal tables
  - Flag fractions per table
  - SNR statistics
  - Overall quality: excellent/good/marginal/poor
- `extract_image_qa()`: Analyze images
  - RMS noise, peak flux, dynamic range
  - Beam parameters
  - Quality classification
- `generate_image_thumbnail()`: Create PNG preview

####API Endpoints (TODO)
```
GET /api/qa/calibration/{ms_path}  - Get cal QA for MS
GET /api/qa/image/{ms_path}        - Get image QA for MS
GET /api/thumbnails/{ms_path}.png  - Serve image thumbnail
```

### Frontend Components (TODO)
- QA badges in MS table (color-coded quality)
- QA panel in MS metadata display
- Image thumbnail preview
- Expandable QA details (flag fractions, DR, etc.)

---

## Feature 3: Data Organization ✓ Partial

### Backend Components

#### Enhanced MSListEntry Model ✓ COMPLETE
```python
class MSListEntry(BaseModel):
    path: str
    # Status fields
    has_calibrator: bool
    calibrator_name: Optional[str]
    calibrator_quality: Optional[str]
    is_calibrated: bool
    is_imaged: bool
    calibration_quality: Optional[str]
    image_quality: Optional[str]
    size_gb: Optional[float]
    start_time: Optional[str]
```

#### Filtering Model ✓ COMPLETE
```python
class MSListFilters(BaseModel):
    search: Optional[str]  # Search path or calibrator
    has_calibrator: Optional[bool]
    is_calibrated: Optional[bool]
    is_imaged: Optional[bool]
    calibrator_quality: Optional[str]
    start_date / end_date: Optional[str]
    sort_by: str  # time_asc, time_desc, name, size
    limit / offset: int  # Pagination
```

#### Enhanced `/api/ms` Endpoint (TODO)
Current implementation is simple. Need to:
1. Query MS index with enhanced fields
2. Join with calibrator_matches, calibration_qa, image_qa
3. Apply filters and sorting
4. Return paginated results with total/filtered counts

### Frontend Components (TODO)
- Replace dropdown with **DataGrid table**
- Search box (filters path + calibrator name)
- Filter chips: "Has Calibrator", "Calibrated", "Imaged"
- Quality filter dropdown
- Sort column headers (clickable)
- Status badges/icons:
  - ✓ Has calibrator (green)
  - ⚠ No calibrator (yellow)
  - ✓ Calibrated (blue)
  - ✓ Imaged (purple)
- Pagination controls
- Multi-select checkboxes (for bulk ops)

---

## Implementation Priority

### Phase 1: Data Organization (Start Here)
This is foundational for the other features.

1. ✓ Update MSListEntry model
2. ✓ Add MSListFilters model
3. **Enhance `/api/ms` endpoint** with filtering/sorting
4. **Frontend: Replace dropdown with DataGrid table**
5. **Frontend: Add search, filters, sort**
6. **Frontend: Add status badges**

### Phase 2: Quality Assessment
Once we can see MS status, add QA.

1. ✓ Database schema for QA tables
2. ✓ QA extraction functions
3. **Integrate QA into job_runner** (call after cal/image)
4. **API endpoints for QA retrieval**
5. **Frontend: Display QA in table and metadata panel**
6. **Frontend: Image thumbnails**

### Phase 3: Bulk Operations
With table + QA in place, add bulk ops.

1. ✓ Database schema for batch jobs
2. ✓ Batch job models
3. **API endpoints for batch operations**
4. **Background worker for batch processing**
5. **Frontend: Multi-select in table**
6. **Frontend: Batch actions dropdown**
7. **Frontend: Batch progress modal**

---

## Next Steps

**Immediate Action**: Implement Phase 1, Step 3
- Rewrite `/api/ms` endpoint to:
  - Fetch MS with enhanced status fields
  - Apply filters from query parameters
  - Sort results
  - Return pagination info

**File to Edit**: `src/dsa110_contimg/src/dsa110_contimg/api/routes.py`
- Replace `list_ms()` function (line ~527)
- Add helper to join MS with calibrator/QA data
- Add query parameter handling

---

## Testing Plan

### Phase 1 Testing
- [ ] API returns MS with all status fields populated
- [ ] Search filters by path and calibrator name
- [ ] Filters work correctly (has_calibrator, is_calibrated, etc.)
- [ ] Sorting works (time, name, size)
- [ ] Pagination works
- [ ] Frontend table displays correctly
- [ ] Clicking column headers sorts
- [ ] Search box filters in real-time

### Phase 2 Testing
- [ ] QA extraction runs after calibration
- [ ] QA extraction runs after imaging
- [ ] Quality assessment is accurate
- [ ] Thumbnails generate correctly
- [ ] Frontend displays QA badges
- [ ] Clicking MS shows QA details

### Phase 3 Testing
- [ ] Multi-select works in table
- [ ] Batch calibration processes all selected MS
- [ ] Batch progress updates in real-time
- [ ] Failed items don't block batch
- [ ] Cancel batch works
- [ ] Frontend shows per-item status

---

## Files Created/Modified

### Backend
- ✓ `src/dsa110_contimg/api/models.py` - Added batch + QA models
- ✓ `src/dsa110_contimg/api/batch_jobs.py` - New file, batch processing + QA
- ✓ `src/dsa110_contimg/database/products.py` - Added batch + QA tables
- TODO: `src/dsa110_contimg/api/routes.py` - New endpoints
- TODO: `src/dsa110_contimg/api/job_runner.py` - Integrate QA extraction

### Frontend
- TODO: `frontend/src/api/types.ts` - Add batch + QA types
- TODO: `frontend/src/api/queries.ts` - Add batch + QA hooks
- TODO: `frontend/src/pages/ControlPage.tsx` - Replace dropdown with table
- TODO: `frontend/src/components/MSTable.tsx` - New component
- TODO: `frontend/src/components/BatchProgress.tsx` - New component

---

## Estimated Effort

- Phase 1 (Data Organization): ~2-3 hours
- Phase 2 (Quality Assessment): ~3-4 hours  
- Phase 3 (Bulk Operations): ~4-5 hours

**Total**: ~10-12 hours of development + testing

---

## Current Status

**Completed**:
- ✓ Backend models for all three features
- ✓ Database schema for all three features
- ✓ QA extraction functions
- ✓ Batch job management functions

**In Progress**:
- API endpoint enhancements

**Not Started**:
- Frontend components
- Integration testing

