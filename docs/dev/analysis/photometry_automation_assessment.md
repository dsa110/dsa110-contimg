# Automated Photometry Pipeline Assessment

**Status**: 0% → Needs investigation and implementation

**Date**: 2025-01-15

## Executive Summary

The photometry infrastructure exists (API endpoints, batch jobs, database functions), but **automatic photometry is not triggered** after imaging or mosaic creation in either streaming or orchestrator modes. This assessment identifies what exists and what needs to be implemented.

## Current State Analysis

### What EXISTS (Infrastructure)

#### 1. Photometry Functions
- **Forced Photometry**: `dsa110_contimg.photometry.forced.measure_forced_peak()`
- **Adaptive Photometry**: `dsa110_contimg.photometry.adaptive_photometry.AdaptivePhotometryStage`
- **Normalization**: `dsa110_contimg.photometry.normalize.normalize_measurement()`

#### 2. API Endpoints
- `POST /api/photometry/measure` - Single photometry measurement
- `POST /api/photometry/measure-batch` - Batch photometry measurements
- `POST /api/photometry/normalize` - Photometry normalization
- `POST /api/batch/photometry` - Batch photometry job creation

#### 3. Database Functions
- `dsa110_contimg.database.products.photometry_insert()` - Insert photometry into products DB
- `photometry` table exists in products database

#### 4. Batch Job Infrastructure
- `dsa110_contimg.api.batch_jobs.create_batch_photometry_job()` - Create batch photometry job
- `dsa110_contimg.api.job_adapters.run_batch_photometry_job()` - Execute batch photometry job
- `batch_jobs` and `batch_job_items` tables exist

### What is MISSING (Automation)

#### 1. Automatic Photometry After Imaging
**Location**: `src/dsa110_contimg/conversion/streaming/streaming_converter.py`

**Current State**:
- After `image_ms()` completes, no photometry is triggered
- Individual MS files are imaged but photometry is not performed

**Required**:
- Detect when imaging completes successfully
- Query catalog for sources in field (NVSS or master sources)
- Trigger photometry measurement on the new FITS image
- Store results in products database

#### 2. Automatic Photometry After Mosaic Creation
**Location**: `src/dsa110_contimg/mosaic/orchestrator.py`

**Current State**:
- Mosaics are created via `_process_group_workflow()`
- No photometry is triggered after mosaic completion

**Required**:
- After mosaic FITS file is created, trigger photometry
- Query catalog for sources in mosaic field
- Perform batch photometry on all sources
- Store results in products database
- Link photometry to mosaic data_id in data registry

#### 3. Integration with Data Registry
**Location**: `src/dsa110_contimg/database/data_registry.py`

**Current State**:
- `finalize_data()` and `trigger_auto_publish()` exist
- No photometry-related fields or triggers

**Required**:
- Track photometry status per data product (image/mosaic)
- Link photometry results to data_id
- Include photometry status in QA validation
- Auto-trigger photometry when data is finalized

#### 4. Batch Photometry Processing Automation
**Current State**:
- Batch photometry jobs can be created via API
- No automatic batch job creation after imaging/mosaic

**Required**:
- Automatically create batch photometry jobs for:
  - Newly imaged FITS files
  - Newly created mosaics
- Query master sources catalog for coordinates
- Configure batch job parameters (normalization, method, etc.)
- Monitor batch job completion

## Detailed Gap Analysis

### Gap 1: Streaming Converter Integration

**File**: `src/dsa110_contimg/conversion/streaming/streaming_converter.py`

**Current Workflow**:
```python
# After imaging completes:
if enable_imaging:
    image_ms(...)
    # Update artifacts in products DB
    # NO PHOTOMETRY HERE
```

**Required Workflow**:
```python
# After imaging completes:
if enable_imaging:
    image_ms(...)
    # Update artifacts in products DB
    
    if enable_photometry:
        # Query sources in field
        sources = query_sources_for_image(image_path)
        # Trigger photometry
        trigger_photometry_for_image(image_path, sources)
```

**Missing Functions**:
- `query_sources_for_image(image_path: Path) -> List[Source]`
- `trigger_photometry_for_image(image_path: Path, sources: List[Source]) -> str` (returns job_id)

### Gap 2: Mosaic Orchestrator Integration

**File**: `src/dsa110_contimg/mosaic/orchestrator.py`

**Current Workflow**:
```python
# Phase 10: Create mosaic
mosaic_path = create_mosaic(...)
# Phase 11: Validate and publish
# NO PHOTOMETRY HERE
```

**Required Workflow**:
```python
# Phase 10: Create mosaic
mosaic_path = create_mosaic(...)

# Phase 10.5: Automatic Photometry (NEW)
if enable_photometry:
    sources = query_sources_for_mosaic(mosaic_path)
    photometry_job_id = trigger_photometry_for_mosaic(mosaic_path, sources)
    # Wait for completion or continue asynchronously

# Phase 11: Validate and publish
```

**Missing Functions**:
- `query_sources_for_mosaic(mosaic_path: Path) -> List[Source]`
- `trigger_photometry_for_mosaic(mosaic_path: Path, sources: List[Source]) -> str`

### Gap 3: Data Registry Integration

**File**: `src/dsa110_contimg/database/data_registry.py`

**Current Schema**:
- `data_registry` table tracks: `data_id`, `data_type`, `status`, `qa_status`, `validation_status`
- No photometry-related fields

**Required Schema**:
```sql
ALTER TABLE data_registry ADD COLUMN photometry_status TEXT DEFAULT NULL;
ALTER TABLE data_registry ADD COLUMN photometry_job_id TEXT DEFAULT NULL;
```

**Required Functions**:
- `update_photometry_status(data_id: str, status: str, job_id: Optional[str])`
- `get_photometry_status(data_id: str) -> Optional[str]`
- `link_photometry_to_data(data_id: str, photometry_job_id: str)`

### Gap 4: Source Query Functions

**Missing Module**: `src/dsa110_contimg/photometry/sources.py` (or similar)

**Required Functions**:
- `query_sources_for_image(image_path: Path, catalog: str = "nvss", radius_deg: float = 0.5) -> List[Source]`
- `query_sources_for_mosaic(mosaic_path: Path, catalog: str = "nvss", radius_deg: float = 1.0) -> List[Source]`
- `get_field_center_from_fits(fits_path: Path) -> Tuple[float, float]` (RA, Dec)

**Note**: These may exist in `dsa110_contimg.catalog` or `dsa110_contimg.photometry.source` - needs verification.

## Implementation Plan

### Phase 1: Source Query Functions (Foundation)
1. Create/verify source query functions
2. Add FITS header parsing for field center
3. Integrate with NVSS/master sources catalog
4. Unit tests

### Phase 2: Streaming Converter Integration
1. Add `--enable-photometry` flag to streaming converter
2. Add photometry trigger after imaging
3. Query sources and create batch photometry job
4. Update products DB with photometry job_id
5. Integration tests

### Phase 3: Mosaic Orchestrator Integration
1. Add photometry phase to mosaic workflow
2. Query sources for mosaic field
3. Create batch photometry job for mosaic
4. Link photometry to mosaic data_id
5. Integration tests

### Phase 4: Data Registry Integration
1. Add photometry fields to data_registry schema
2. Add photometry status update functions
3. Integrate photometry status into QA workflow
4. Update `finalize_data()` to check photometry status
5. Migration script for existing data

### Phase 5: End-to-End Testing
1. Test streaming converter → imaging → photometry
2. Test mosaic orchestrator → mosaic → photometry
3. Test data registry tracking
4. Test batch job completion and status updates

## Dependencies

### External
- NVSS catalog access (via `dsa110_contimg.catalog`)
- Master sources catalog (via `dsa110_contimg.database.master_sources`)
- FITS file reading (astropy)

### Internal
- `dsa110_contimg.photometry.forced.measure_forced_peak()`
- `dsa110_contimg.api.batch_jobs.create_batch_photometry_job()`
- `dsa110_contimg.database.products.photometry_insert()`
- `dsa110_contimg.database.data_registry` functions

## Configuration Requirements

### Streaming Converter
```python
--enable-photometry          # Enable automatic photometry after imaging
--photometry-catalog NVSS    # Catalog to use for source queries
--photometry-radius 0.5      # Search radius in degrees
--photometry-normalize       # Enable normalization
```

### Mosaic Orchestrator
```python
config.photometry.enabled = True
config.photometry.catalog = "nvss"
config.photometry.radius_deg = 1.0
config.photometry.normalize = True
```

## Success Criteria

1. **After imaging**: Photometry is automatically triggered for newly imaged FITS files
2. **After mosaic**: Photometry is automatically triggered for newly created mosaics
3. **Data registry**: Photometry status is tracked and linked to data products
4. **Batch processing**: Batch photometry jobs are created and monitored automatically
5. **Database**: Photometry results are stored and queryable via products DB

## Estimated Effort

- **Phase 1** (Source Query): 2-3 hours
- **Phase 2** (Streaming): 3-4 hours
- **Phase 3** (Mosaic): 3-4 hours
- **Phase 4** (Registry): 2-3 hours
- **Phase 5** (Testing): 2-3 hours

**Total**: ~12-17 hours

## Next Steps

1. Verify existing source query functions in catalog module
2. Create source query wrapper functions if needed
3. Implement streaming converter integration
4. Implement mosaic orchestrator integration
5. Add data registry schema and functions
6. Write integration tests
7. Update documentation

