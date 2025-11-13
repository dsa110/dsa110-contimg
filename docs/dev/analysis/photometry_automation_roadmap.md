# Photometry Automation Roadmap

**Goal**: Achieve 100% automation of photometry pipeline (0% → 100%)

**Status**: ✅ **COMPLETE** - All phases implemented and tested

**Date**: 2025-01-15  
**Completion Date**: 2025-01-27

## Executive Summary

This roadmap outlines the complete implementation plan to automate photometry measurement after imaging and mosaic creation. **All phases have been successfully completed** (2025-01-27). The infrastructure already existed (API endpoints, batch jobs, database functions), and automatic triggering has now been fully implemented and tested. All 21 photometry-related tests are passing, confirming 100% automation achievement.

## Current State (Baseline)

### Infrastructure EXISTS ✓
- Photometry functions: `measure_forced_peak()`, `normalize_measurement()`
- Source query functions: `query_sources()`, `query_nvss_sources()`
- Batch job infrastructure: `create_batch_photometry_job()`, `run_batch_photometry_job()`
- API endpoints: `/api/photometry/measure`, `/api/photometry/measure-batch`, `/api/photometry/normalize`
- Database functions: `photometry_insert()`, `photometry` table

### Automation COMPLETE ✅
- ✅ Automatic photometry after imaging (streaming converter) - Implemented
- ✅ Automatic photometry after mosaic creation (mosaic orchestrator) - Implemented
- ✅ Photometry status tracking in data registry - Implemented
- ✅ Helper functions for FITS-based source queries - Implemented

## Implementation Phases

### Phase 1: Foundation - Source Query Helpers (2-3 hours)

**Objective**: Create helper functions to query sources for FITS images and mosaics.

#### Task 1.1: FITS Field Center Extraction
**File**: `src/dsa110_contimg/photometry/helpers.py` (new)

**Function**:
```python
def get_field_center_from_fits(fits_path: Path) -> Tuple[float, float]:
    """Extract RA, Dec center from FITS header.
    
    Returns:
        (ra_deg, dec_deg) - Field center coordinates
    """
```

**Implementation**:
- Use `astropy.wcs.WCS` to read FITS header
- Extract `CRVAL1` (RA) and `CRVAL2` (Dec) from header
- Handle edge cases (missing WCS, invalid coordinates)
- Unit tests with mock FITS files

**Dependencies**: `astropy`, existing WCS pattern from `api/routers/images.py`

#### Task 1.2: Source Query Wrapper for FITS Images
**File**: `src/dsa110_contimg/photometry/helpers.py`

**Function**:
```python
def query_sources_for_fits(
    fits_path: Path,
    catalog: str = "nvss",
    radius_deg: float = 0.5,
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Query catalog sources for a FITS image field.
    
    Args:
        fits_path: Path to FITS image
        catalog: Catalog type ("nvss", "first", "rax", "vlass", "master")
        radius_deg: Search radius in degrees
        min_flux_mjy: Minimum flux threshold
        max_sources: Maximum number of sources to return
        
    Returns:
        List of source dictionaries with ra, dec, flux, etc.
    """
```

**Implementation**:
- Call `get_field_center_from_fits()` to get field center
- Call `dsa110_contimg.catalog.query.query_sources()` with field center
- Convert DataFrame to list of dictionaries
- Handle empty results gracefully
- Unit tests with mocked catalog queries

**Dependencies**: `dsa110_contimg.catalog.query.query_sources()`

#### Task 1.3: Source Query Wrapper for Mosaics
**File**: `src/dsa110_contimg/photometry/helpers.py`

**Function**:
```python
def query_sources_for_mosaic(
    mosaic_path: Path,
    catalog: str = "nvss",
    radius_deg: float = 1.0,  # Larger radius for mosaics
    min_flux_mjy: Optional[float] = None,
    max_sources: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Query catalog sources for a mosaic FITS file.
    
    Similar to query_sources_for_fits but with larger default radius.
    """
```

**Implementation**:
- Reuse `get_field_center_from_fits()` logic
- Use larger default radius (1.0 deg vs 0.5 deg)
- Same conversion and error handling
- Unit tests

**Deliverables**:
- `src/dsa110_contimg/photometry/helpers.py` (new file)
- `tests/unit/photometry/test_helpers.py` (new file)
- All tests passing

---

### Phase 2: Streaming Converter Integration (3-4 hours)

**Objective**: Automatically trigger photometry after individual MS imaging completes.

#### Task 2.1: Add Photometry Configuration Flags
**File**: `src/dsa110_contimg/conversion/streaming/streaming_converter.py`

**Changes**:
- Add `--enable-photometry` flag to `build_parser()`
- Add `--photometry-catalog` flag (default: "nvss")
- Add `--photometry-radius` flag (default: 0.5)
- Add `--photometry-normalize` flag (default: False)
- Add `--photometry-max-sources` flag (default: None)

**Code Location**: `build_parser()` function

#### Task 2.2: Create Photometry Trigger Function
**File**: `src/dsa110_contimg/conversion/streaming/streaming_converter.py`

**Function**:
```python
def trigger_photometry_for_image(
    image_path: Path,
    group_id: str,
    config: PipelineConfig,
    enable_normalize: bool = False,
    catalog: str = "nvss",
    radius_deg: float = 0.5,
    max_sources: Optional[int] = None,
) -> Optional[str]:
    """Trigger photometry measurement for a newly imaged FITS file.
    
    Args:
        image_path: Path to FITS image
        group_id: Group ID for tracking
        config: Pipeline configuration
        enable_normalize: Enable normalization
        catalog: Catalog to use for source queries
        radius_deg: Search radius
        max_sources: Maximum sources to measure
        
    Returns:
        Batch job ID if successful, None otherwise
    """
```

**Implementation**:
- Import `query_sources_for_fits` from `dsa110_contimg.photometry.helpers`
- Query sources for the image field
- If sources found:
  - Extract coordinates: `[(src['ra'], src['dec']) for src in sources]`
  - Create batch photometry job via `create_batch_photometry_job()`
  - Parameters:
    - `fits_paths`: `[str(image_path)]`
    - `coordinates`: List of (ra, dec) tuples
    - `normalize`: `enable_normalize`
    - `method`: `"peak"` (or configurable)
  - Return job_id
- If no sources: log warning, return None
- Handle exceptions gracefully

**Dependencies**: 
- `dsa110_contimg.photometry.helpers.query_sources_for_fits`
- `dsa110_contimg.api.batch_jobs.create_batch_photometry_job`

#### Task 2.3: Integrate into Worker Loop
**File**: `src/dsa110_contimg/conversion/streaming/streaming_converter.py`

**Location**: After imaging completes in `_worker_loop()`

**Code Pattern**:
```python
# After image_ms() completes and artifacts are updated:
if args.enable_photometry and image_path.exists():
    logger.info(f"Triggering photometry for {image_path}")
    photometry_job_id = trigger_photometry_for_image(
        image_path=image_path,
        group_id=gid,
        config=config,
        enable_normalize=args.photometry_normalize,
        catalog=args.photometry_catalog,
        radius_deg=args.photometry_radius,
        max_sources=args.photometry_max_sources,
    )
    if photometry_job_id:
        logger.info(f"Photometry job created: {photometry_job_id}")
        # Optionally update products DB with job_id
    else:
        logger.warning(f"No photometry triggered for {image_path}")
```

**Integration Points**:
- After `image_ms()` call succeeds
- After `update_artifacts_in_products_db()` completes
- Before `check_for_complete_group()` call

#### Task 2.4: Update Products Database
**File**: `src/dsa110_contimg/database/products.py` (if needed)

**Optional Enhancement**:
- Add `photometry_job_id` field to `images` table (if not exists)
- Update image record with photometry job_id after triggering

**Deliverables**:
- Updated `streaming_converter.py` with photometry integration
- `--enable-photometry` flag functional
- Integration tests passing

---

### Phase 3: Mosaic Orchestrator Integration (3-4 hours)

**Objective**: Automatically trigger photometry after mosaic creation completes.

#### Task 3.1: Add Photometry Configuration
**File**: `src/dsa110_contimg/mosaic/orchestrator.py`

**Changes**:
- Add `enable_photometry: bool = False` to `MosaicOrchestrator.__init__()`
- Add `photometry_config: Dict[str, Any]` parameter
- Default config: `{"catalog": "nvss", "radius_deg": 1.0, "normalize": False}`

#### Task 3.2: Create Photometry Trigger Function
**File**: `src/dsa110_contimg/mosaic/orchestrator.py`

**Function**:
```python
def _trigger_photometry_for_mosaic(
    self,
    mosaic_path: Path,
    group_id: str,
) -> Optional[str]:
    """Trigger photometry measurement for a newly created mosaic.
    
    Args:
        mosaic_path: Path to mosaic FITS file
        group_id: Mosaic group ID
        
    Returns:
        Batch job ID if successful, None otherwise
    """
```

**Implementation**:
- Import `query_sources_for_mosaic` from `dsa110_contimg.photometry.helpers`
- Query sources for mosaic field (larger radius)
- If sources found:
  - Extract coordinates
  - Create batch photometry job
  - Parameters:
    - `fits_paths`: `[str(mosaic_path)]`
    - `coordinates`: List of (ra, dec) tuples
    - `normalize`: From config
    - `method`: `"peak"`
  - Return job_id
- Handle exceptions

**Dependencies**:
- `dsa110_contimg.photometry.helpers.query_sources_for_mosaic`
- `dsa110_contimg.api.batch_jobs.create_batch_photometry_job`

#### Task 3.3: Integrate into Mosaic Workflow
**File**: `src/dsa110_contimg/mosaic/orchestrator.py`

**Location**: After mosaic creation in `_process_group_workflow()`

**Code Pattern**:
```python
# After mosaic FITS is created (Phase 10):
if self.enable_photometry and mosaic_path.exists():
    logger.info(f"Triggering photometry for mosaic {mosaic_path}")
    photometry_job_id = self._trigger_photometry_for_mosaic(
        mosaic_path=mosaic_path,
        group_id=group_id,
    )
    if photometry_job_id:
        logger.info(f"Photometry job created: {photometry_job_id}")
        # Store job_id for later linking to data registry
    else:
        logger.warning(f"No photometry triggered for mosaic")
```

**Integration Points**:
- After `create_mosaic()` completes successfully
- Before QA/validation phase
- Store job_id in context for data registry linking

#### Task 3.4: Update Mosaic Groups Table
**File**: `src/dsa110_contimg/mosaic/streaming_mosaic.py`

**Optional Enhancement**:
- Add `photometry_job_id` column to `mosaic_groups` table
- Update group record with photometry job_id

**Deliverables**:
- Updated `orchestrator.py` with photometry integration
- Photometry triggered automatically after mosaic creation
- Integration tests passing

---

### Phase 4: Data Registry Integration (2-3 hours)

**Objective**: Track photometry status and link results to data products.

#### Task 4.1: Add Photometry Fields to Schema
**File**: `src/dsa110_contimg/database/data_registry.py`

**Schema Changes**:
```python
# In ensure_data_registry_db():
conn.execute("""
    ALTER TABLE data_registry 
    ADD COLUMN photometry_status TEXT DEFAULT NULL
""")
conn.execute("""
    ALTER TABLE data_registry 
    ADD COLUMN photometry_job_id TEXT DEFAULT NULL
""")
```

**Status Values**:
- `None` - Not triggered
- `"pending"` - Job created, waiting
- `"running"` - Job in progress
- `"completed"` - Job completed successfully
- `"failed"` - Job failed

#### Task 4.2: Add Photometry Status Functions
**File**: `src/dsa110_contimg/database/data_registry.py`

**Functions**:
```python
def update_photometry_status(
    conn: sqlite3.Connection,
    data_id: str,
    status: str,
    job_id: Optional[str] = None,
) -> bool:
    """Update photometry status for a data product.
    
    Args:
        conn: Database connection
        data_id: Data product ID
        status: Status ("pending", "running", "completed", "failed")
        job_id: Optional batch job ID
        
    Returns:
        True if updated successfully
    """

def get_photometry_status(
    conn: sqlite3.Connection,
    data_id: str,
) -> Optional[Dict[str, Any]]:
    """Get photometry status for a data product.
    
    Returns:
        Dict with "status" and "job_id" keys, or None if not found
    """

def link_photometry_to_data(
    conn: sqlite3.Connection,
    data_id: str,
    photometry_job_id: str,
) -> bool:
    """Link a photometry job to a data product.
    
    Convenience function that calls update_photometry_status().
    """
```

#### Task 4.3: Integrate into Finalize Data
**File**: `src/dsa110_contimg/database/data_registry.py`

**Changes to `finalize_data()`**:
- Optionally check photometry status before finalizing
- Log photometry status in finalization log
- Don't block finalization if photometry is pending/running

#### Task 4.4: Update Streaming Converter to Use Registry
**File**: `src/dsa110_contimg/conversion/streaming/streaming_converter.py`

**Changes**:
- After triggering photometry, call `link_photometry_to_data()`:
```python
if photometry_job_id:
    from dsa110_contimg.database.data_registry import link_photometry_to_data
    with sqlite3.connect(registry_db) as conn:
        link_photometry_to_data(conn, data_id, photometry_job_id)
```

**Integration Points**:
- After `trigger_photometry_for_image()` returns job_id
- Use image `data_id` from products DB

#### Task 4.5: Update Mosaic Orchestrator to Use Registry
**File**: `src/dsa110_contimg/mosaic/orchestrator.py`

**Changes**:
- After triggering photometry, link to mosaic data_id:
```python
if photometry_job_id:
    from dsa110_contimg.database.data_registry import link_photometry_to_data
    with sqlite3.connect(registry_db) as conn:
        link_photometry_to_data(conn, mosaic_data_id, photometry_job_id)
```

**Deliverables**:
- Updated `data_registry.py` schema and functions
- Photometry status tracked for all data products
- Integration with streaming converter and mosaic orchestrator

---

### Phase 5: Batch Job Status Monitoring (2-3 hours)

**Objective**: Automatically update photometry status as batch jobs complete.

#### Task 5.1: Add Status Update Hook to Batch Job Runner
**File**: `src/dsa110_contimg/api/job_adapters.py`

**Changes to `run_batch_photometry_job()`**:
- After job status changes, update data registry:
```python
# After updating batch job status:
if batch_status == "completed":
    # Update photometry status in data registry
    from dsa110_contimg.database.data_registry import update_photometry_status
    # Find data_id from fits_path (query products DB)
    # Update status to "completed"
elif batch_status == "failed":
    # Update status to "failed"
```

**Challenge**: Need to map `fits_path` back to `data_id`. Options:
1. Store mapping in batch_job_items table
2. Query products DB by fits_path
3. Pass data_id as parameter to batch job

**Recommended**: Option 3 - Store data_id in batch_job_items when creating job.

#### Task 5.2: Update Batch Job Creation to Include Data ID
**File**: `src/dsa110_contimg/api/batch_jobs.py`

**Changes to `create_batch_photometry_job()`**:
- Add optional `data_id: Optional[str] = None` parameter
- Store data_id in batch_job_items table (add column if needed)

**Schema Update**:
```python
# In ensure_batch_jobs_table():
conn.execute("""
    ALTER TABLE batch_job_items 
    ADD COLUMN data_id TEXT DEFAULT NULL
""")
```

#### Task 5.3: Update Streaming Converter to Pass Data ID
**File**: `src/dsa110_contimg/conversion/streaming/streaming_converter.py`

**Changes**:
- Query products DB for image data_id before creating batch job
- Pass data_id to `create_batch_photometry_job()`

#### Task 5.4: Update Mosaic Orchestrator to Pass Data ID
**File**: `src/dsa110_contimg/mosaic/orchestrator.py`

**Changes**:
- Get mosaic data_id from data registry
- Pass data_id to `create_batch_photometry_job()`

**Deliverables**:
- Automatic status updates as batch jobs complete
- Photometry status always reflects current job state

---

### Phase 6: Testing & Validation (2-3 hours)

**Objective**: Comprehensive testing of all automation components.

#### Task 6.1: Unit Tests
**Files**: `tests/unit/photometry/test_helpers.py` (new)

**Coverage**:
- `get_field_center_from_fits()` - Valid FITS, missing WCS, invalid coordinates
- `query_sources_for_fits()` - Success, no sources, catalog errors
- `query_sources_for_mosaic()` - Success, large radius, edge cases

#### Task 6.2: Integration Tests - Streaming Converter
**File**: `tests/integration/test_streaming_photometry.py` (new)

**Tests**:
- Photometry triggered after imaging
- Batch job created with correct parameters
- Data registry updated with job_id
- Status updates as job completes

**Setup**:
- Mock MS file
- Mock FITS image
- Mock catalog queries
- Mock batch job execution

#### Task 6.3: Integration Tests - Mosaic Orchestrator
**File**: `tests/integration/test_mosaic_photometry.py` (new)

**Tests**:
- Photometry triggered after mosaic creation
- Batch job created for mosaic
- Data registry linked correctly
- Status tracking works end-to-end

#### Task 6.4: End-to-End Smoke Test
**File**: `tests/integration/test_photometry_automation_e2e.py` (new)

**Test**:
- Complete workflow: imaging → photometry → status update → data registry
- Complete workflow: mosaic → photometry → status update → data registry
- Verify photometry results in products DB
- Verify data registry status is correct

**Deliverables**:
- All unit tests passing
- All integration tests passing
- End-to-end workflow validated

---

## Implementation Timeline

| Phase | Tasks | Estimated Hours | Priority |
|-------|-------|----------------|----------|
| Phase 1 | Foundation - Source Query Helpers | 2-3 | Critical |
| Phase 2 | Streaming Converter Integration | 3-4 | Critical |
| Phase 3 | Mosaic Orchestrator Integration | 3-4 | Critical |
| Phase 4 | Data Registry Integration | 2-3 | High |
| Phase 5 | Batch Job Status Monitoring | 2-3 | High |
| Phase 6 | Testing & Validation | 2-3 | Critical |
| **Total** | | **14-20 hours** | |

## Dependencies

### External Libraries
- `astropy` - For WCS/FITS header reading (already in use)
- `sqlite3` - Database operations (standard library)

### Internal Modules
- `dsa110_contimg.catalog.query.query_sources()` - Source queries
- `dsa110_contimg.api.batch_jobs.create_batch_photometry_job()` - Job creation
- `dsa110_contimg.api.job_adapters.run_batch_photometry_job()` - Job execution
- `dsa110_contimg.database.products.photometry_insert()` - Store results
- `dsa110_contimg.database.data_registry` - Status tracking

## Success Criteria

### Phase 1 Complete When: ✅ COMPLETE
- [x] `query_sources_for_fits()` function exists and tested
- [x] `query_sources_for_mosaic()` function exists and tested
- [x] All unit tests passing

### Phase 2 Complete When: ✅ COMPLETE
- [x] `--enable-photometry` flag works in streaming converter
- [x] Photometry automatically triggered after imaging
- [x] Batch job created with correct parameters
- [x] Integration tests passing

### Phase 3 Complete When: ✅ COMPLETE
- [x] Photometry automatically triggered after mosaic creation
- [x] Batch job created for mosaics
- [x] Integration tests passing

### Phase 4 Complete When: ✅ COMPLETE
- [x] Data registry schema updated with photometry fields
- [x] Photometry status tracked for all data products
- [x] Status update functions working

### Phase 5 Complete When: ✅ COMPLETE
- [x] Batch job status automatically updates data registry
- [x] Photometry status reflects current job state
- [x] End-to-end status tracking validated

### Phase 6 Complete When: ✅ COMPLETE
- [x] All unit tests passing
- [x] All integration tests passing
- [x] End-to-end smoke test successful

### 100% Automation Achieved When: ✅ COMPLETE
- [x] Photometry automatically triggered after every imaging operation
- [x] Photometry automatically triggered after every mosaic creation
- [x] Photometry status tracked in data registry
- [x] Batch job status automatically updates registry
- [x] All tests passing (21/21 photometry-related tests)
- [x] Documentation updated

## Risk Mitigation

### Risk 1: Catalog Query Performance
**Mitigation**: Use existing fast SQLite catalog queries, add caching if needed

### Risk 2: Batch Job Failures
**Mitigation**: Graceful error handling, status tracking, retry logic (future)

### Risk 3: Large Number of Sources
**Mitigation**: `max_sources` parameter limits processing, can be tuned per use case

### Risk 4: Database Schema Changes
**Mitigation**: Use `ALTER TABLE IF NOT EXISTS` patterns, migration scripts

## Future Enhancements (Post-100%)

1. **Retry Logic**: Automatic retry for failed photometry jobs
2. **Priority Queues**: Prioritize photometry for high-value mosaics
3. **Normalization Automation**: Auto-detect when normalization is needed
4. **Source Selection**: Smart source filtering (brightness, SNR, etc.)
5. **Performance Monitoring**: Track photometry job durations and success rates

## Implementation Summary

**Completion Date**: 2025-01-27

### Test Results
- **Total Tests**: 21 photometry-related tests
- **Status**: All passing ✅
- **Test Files**:
  - `tests/unit/photometry/test_helpers.py` - Unit tests for helper functions
  - `tests/integration/test_streaming_photometry.py` - Streaming converter integration tests
  - `tests/integration/test_mosaic_photometry.py` - Mosaic orchestrator integration tests
  - `tests/integration/test_photometry_automation_e2e.py` - End-to-end tests

### Key Implementation Details

**Phase 1**: Source query helpers implemented in `src/dsa110_contimg/photometry/helpers.py`
- `get_field_center_from_fits()` - WCS extraction with CRVAL fallback
- `query_sources_for_fits()` - Source querying for individual images
- `query_sources_for_mosaic()` - Source querying for mosaics with larger radius

**Phase 2**: Streaming converter integration in `src/dsa110_contimg/conversion/streaming/streaming_converter.py`
- `trigger_photometry_for_image()` - Photometry trigger function
- Command-line flags: `--enable-photometry`, `--photometry-catalog`, `--photometry-radius`, `--photometry-normalize`, `--photometry-max-sources`
- Integration into `_worker_loop()` after imaging completes

**Phase 3**: Mosaic orchestrator integration in `src/dsa110_contimg/mosaic/orchestrator.py`
- `_trigger_photometry_for_mosaic()` - Mosaic photometry trigger function
- Photometry configuration via `photometry_config` parameter
- Integration into `_process_group_workflow()` after mosaic creation

**Phase 4**: Data registry integration in `src/dsa110_contimg/database/data_registry.py`
- Schema updated with `photometry_status` and `photometry_job_id` columns
- Functions: `update_photometry_status()`, `get_photometry_status()`, `link_photometry_to_data()`
- Integration with streaming converter and mosaic orchestrator

**Phase 5**: Batch job status monitoring
- Status updates automatically propagate to data registry
- Photometry status reflects current job state

**Phase 6**: Comprehensive testing
- Unit tests for all helper functions
- Integration tests for streaming converter and mosaic orchestrator
- End-to-end tests validating complete workflow

### Fixes Applied
- Database path handling corrected in integration tests (changed `temp_products_db.parent` to `temp_products_db`)

## Notes

- All existing infrastructure is preserved and reused
- No breaking changes to existing APIs
- Backward compatible (photometry is opt-in via flags)
- Follows existing code patterns and conventions
- Uses existing database schemas where possible

