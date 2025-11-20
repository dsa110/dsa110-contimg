# Data Registry Implementation Summary

## Overview

The data registry system has been fully implemented, providing automatic and
manual publishing of pipeline data products from SSD (`/stage/`) to HDD
(`/data/dsa110-contimg/products/`).

## Completed Components

### 1. Database Schema ✓

- `data_registry` table: Central registry of all data instances
- `data_relationships` table: Tracks relationships between data instances
- `data_tags` table: Tags for organization/search
- Migrations integrated into existing migration system
- Table renames: `ms_index` → `ms_all`, `images` → `images_all`, `mosaics` →
  `mosaics_all`

### 2. Directory Structure ✓

- `/stage/dsa110-contimg/` (SSD): Fast access for active work
  - Subdirectories: `ms/`, `calib_ms/`, `caltables/`, `images/`, `mosaics/`,
    `catalogs/`, `qa/`, `metadata/`
- `/data/dsa110-contimg/products/` (HDD): Long-term storage
  - Same subdirectory structure as staging

### 3. Data Management Functions ✓

- `register_data()`: Register new data instances
- `finalize_data()`: Mark data as finalized, triggers auto-publish
- `trigger_auto_publish()`: Automatically moves data from SSD to HDD
- `publish_data_manual()`: Manual publishing
- `enable_auto_publish()` / `disable_auto_publish()`: Per-instance control
- `check_auto_publish_criteria()`: Check if criteria are met
- `get_data_lineage()`: Track relationships

### 4. API Endpoints ✓

- `GET /api/data` - List data instances (with filters)
- `GET /api/data/{data_id}` - Get specific data instance
- `POST /api/data/{data_id}/finalize` - Finalize data (triggers auto-publish)
- `POST /api/data/{data_id}/publish` - Manual publish
- `POST /api/data/{data_id}/auto-publish/enable` - Enable auto-publish
- `POST /api/data/{data_id}/auto-publish/disable` - Disable auto-publish
- `GET /api/data/{data_id}/auto-publish/status` - Check auto-publish status
- `GET /api/data/{data_id}/lineage` - Get data lineage

### 5. Dashboard Integration ✓

- **DataBrowserPage**: Main data browser with staging/published tabs
- **DataDetailPage**: Detailed view with metadata, lineage, and controls
- **DataLineageGraph**: Visual lineage graph component
- Navigation updated with "Data" menu item
- Routes: `/data` and `/data/:type/:id`

### 6. Pipeline Integration ✓

- Updated API routes to use `/stage/` instead of `/scratch/`
- Created `data_registration.py` helper module
- Ready for integration into pipeline workflows

## Auto-Publish Behavior

### Criteria (per data type)

- **Science data** (images, mosaics, calib_ms, caltables): Requires QA passed +
  validation
- **Diagnostic data** (qa reports, metadata): Auto-publishes with parent data or
  immediately
- **Raw data** (ms): Requires validation only
- **Catalogs**: Requires validation only

### Workflow

1. Pipeline creates data in `/stage/` (SSD)
2. Data registered with `status='staging'`
3. QA/validation runs
4. When finalized, if criteria met → automatically moves to `/data/` (HDD)
5. Database updated: `status='published'`, `publish_mode='auto'`

## Testing

### Test Scripts

- `scripts/test_data_registry.py`: Unit tests for data registry functions
- `scripts/test_end_to_end.sh`: End-to-end integration tests

### Test Results

✓ Database migration working ✓ Data registration working ✓ Data linking working
✓ Lineage tracking working ✓ API endpoints working ✓ Directory structure created

## Next Steps for Pipeline Integration

To fully integrate into the pipeline, update these locations to register data:

1. **Conversion pipeline**: Register MS files when created
2. **Calibration pipeline**: Register calibrated MS and caltables
3. **Imaging pipeline**: Register images and link to source MS
4. **Mosaic pipeline**: Register mosaics and link to source images

Example usage:

```python
from dsa110_contimg.database.data_registration import register_pipeline_data, link_pipeline_data

# Register an MS file
register_pipeline_data(
    data_type='ms',
    data_id='2025-11-07T12:00:00',
    file_path=Path('/stage/dsa110-contimg/ms/2025-11-07T12:00:00.ms'),
    metadata={'frequency': 1.4, 'bandwidth': 0.1},
)

# Link an image to its source MS
link_pipeline_data(
    parent_id='2025-11-07T12:00:00',
    child_id='image_001',
    relationship_type='derived_from',
)
```

## Configuration

Default paths can be overridden with environment variables:

- `CONTIMG_OUTPUT_DIR`: Defaults to `/stage/dsa110-contimg/ms`
- `CONTIMG_CAL_DIR`: Defaults to `/stage/dsa110-contimg/caltables`
- `CONTIMG_SCRATCH_DIR`: Defaults to `/stage/dsa110-contimg`
