# Pipeline Data Flow and Directory Structure Redesign

## Executive Summary

This document proposes a redesign of the DSA-110 continuum imaging pipeline's
data flow and directory structure to:

1. **Align with scientific workflow** - Structure mirrors the 9-stage pipeline
   process
2. **Clarify data provenance** - Clear separation between raw, processed, and
   published data
3. **Optimize performance** - Better use of SSD staging vs HDD archival
4. **Improve maintainability** - Intuitive organization that matches scientific
   protocols
5. **Enable better debugging** - Clear data lineage and intermediate products

---

## Current Issues Identified

### 1. **Confusing Naming and Organization**

- `calib_ms/` directory exists but is unused - calibrated MS files stay in
  `ms/science/` or `ms/calibrators/`
- Mixing of "calibrator MS" (contains calibrator source) vs "calibrated MS" (has
  calibration applied)
- `tmp/`, `logs/`, `state/` in `/stage/` - these don't belong with data products

### 2. **Unclear Data Provenance**

- Hard to trace: raw MS → calibrated MS → imaged MS
- No clear indication of processing stage in directory structure
- Calibration tables stored separately from the MS files they calibrate

### 3. **Inefficient Staging**

- All data types mixed in flat structure
- No clear separation of "in-progress" vs "ready for publishing"
- Temporary files mixed with permanent products

### 4. **Misalignment with Scientific Workflow**

- Directory structure doesn't reflect the 9-stage pipeline
- No clear representation of data transformation stages
- Grouping information (10 MS per group) not visible in structure

---

## Proposed Redesign

### Core Principles

1. **Stage-Based Organization**: Directory structure mirrors pipeline stages
2. **Provenance Tracking**: Each transformation creates a new, clearly-labeled
   product
3. **Temporal Organization**: Date-based subdirectories for time-series data
4. **Separation of Concerns**:
   - Raw data (HDF5) → Input area
   - Processing workspace → Staging area
   - Final products → Published area
   - Metadata/logs → Separate from data

### New Directory Structure

```
/stage/dsa110-contimg/
├── raw/                          # Stage 1-2: Raw converted data
│   ├── ms/
│   │   ├── science/              # Science MS files (uncalibrated)
│   │   │   └── YYYY-MM-DD/
│   │   │       └── <timestamp>.ms/
│   │   └── calibrators/           # Calibrator MS files (uncalibrated)
│   │       └── YYYY-MM-DD/
│   │           └── <timestamp>.ms/
│   └── groups/                    # Stage 3: Group metadata
│       └── YYYY-MM-DD/
│           └── group_<id>.json   # Group definition (10 MS files)
│
├── calibrated/                   # Stage 4-5: Calibration products
│   ├── ms/                       # Calibrated MS files
│   │   ├── science/              # Calibrated science MS
│   │   │   └── YYYY-MM-DD/
│   │   │       └── <timestamp>_cal.ms/
│   │   └── calibrators/          # Calibrated calibrator MS
│   │       └── YYYY-MM-DD/
│   │           └── <timestamp>_cal.ms/
│   └── tables/                   # Calibration tables
│       └── YYYY-MM-DD/
│           ├── <group_id>_bpcal/ # Bandpass calibration
│           ├── <group_id>_gpcal/ # Gain calibration
│           └── <group_id>_2gcal/ # Secondary gain calibration
│
├── images/                       # Stage 6: Individual tile images
│   └── YYYY-MM-DD/
│       └── <ms_timestamp>_<params>.image/
│
├── mosaics/                      # Stage 7: Combined mosaics
│   └── YYYY-MM-DD/
│       └── mosaic_<group_id>_<method>.fits
│
├── products/                     # Stage 8-9: Final products (ready for publish)
│   ├── mosaics/                  # Validated mosaics
│   ├── catalogs/                 # Source catalogs (if cross-matched)
│   └── metadata/                 # Product metadata
│
└── workspace/                    # Temporary processing space
    ├── active/                   # Currently processing
    │   ├── conversion/           # Active conversions
    │   ├── calibration/          # Active calibration solving
    │   ├── imaging/              # Active imaging jobs
    │   └── mosaicking/           # Active mosaic creation
    └── failed/                    # Failed processing attempts
        └── YYYY-MM-DD/
            └── <job_id>_error.log

/data/dsa110-contimg/
├── incoming/                     # Raw HDF5 input (read-only staging)
│   └── YYYY-MM-DD/
│       └── <group_id>.uvh5
│
├── products/                     # Published final products (HDD archive)
│   ├── mosaics/
│   │   └── YYYY-MM-DD/
│   │       └── mosaic_<id>.fits
│   ├── catalogs/
│   ├── images/                   # Archived individual images (optional)
│   └── metadata/
│
└── state/                        # Pipeline state (databases, configs)
    ├── products.sqlite3
    ├── cal_registry.sqlite3
    ├── data_registry.sqlite3
    └── ingest.sqlite3
```

---

## Data Flow Redesign

### Stage-by-Stage Data Movement

#### **Stage 1: File Ingestion**

- **Input**: `/data/incoming/YYYY-MM-DD/<group_id>.uvh5`
- **Action**: Register in `ingest.sqlite3`
- **Output**: Metadata entry, file remains in place

#### **Stage 2: MS Conversion**

- **Input**: HDF5 files from `/data/incoming/`
- **Workspace**: `/stage/dsa110-contimg/workspace/active/conversion/`
- **Output**:
  - Science MS →
    `/stage/dsa110-contimg/raw/ms/science/YYYY-MM-DD/<timestamp>.ms/`
  - Calibrator MS →
    `/stage/dsa110-contimg/raw/ms/calibrators/YYYY-MM-DD/<timestamp>.ms/`
- **Registration**: `products.sqlite3` (ms_index table)

#### **Stage 3: Group Formation**

- **Input**: MS files from `raw/ms/`
- **Action**: Create group definition (10 MS files, 2 overlap)
- **Output**: `/stage/dsa110-contimg/raw/groups/YYYY-MM-DD/group_<id>.json`
- **Metadata**: Links to MS files, time range, calibrator info

#### **Stage 4: Calibration Solving**

- **Input**:
  - Calibrator MS from `raw/ms/calibrators/`
  - Group definition from `raw/groups/`
- **Workspace**: `/stage/dsa110-contimg/workspace/active/calibration/`
- **Output**:
  - Calibration tables →
    `/stage/dsa110-contimg/calibrated/tables/YYYY-MM-DD/<group_id>_bpcal/`
  - Calibration metadata → Registered in `cal_registry.sqlite3`

#### **Stage 5: Calibration Application**

- **Input**:
  - Raw MS from `raw/ms/science/` or `raw/ms/calibrators/`
  - Calibration tables from `calibrated/tables/`
- **Workspace**: `/stage/dsa110-contimg/workspace/active/calibration/`
- **Output**:
  - Calibrated MS →
    `/stage/dsa110-contimg/calibrated/ms/science/YYYY-MM-DD/<timestamp>_cal.ms/`
  - Calibrated calibrator MS →
    `/stage/dsa110-contimg/calibrated/ms/calibrators/YYYY-MM-DD/<timestamp>_cal.ms/`
- **Registration**: `data_registry.sqlite3` with `data_type="calibrated_ms"`

#### **Stage 6: Imaging**

- **Input**: Calibrated MS from `calibrated/ms/science/`
- **Workspace**: `/stage/dsa110-contimg/workspace/active/imaging/`
- **Output**:
  `/stage/dsa110-contimg/images/YYYY-MM-DD/<ms_timestamp>_<params>.image/`
- **Registration**: `data_registry.sqlite3` with `data_type="image"`

#### **Stage 7: Mosaic Creation**

- **Input**: Images from `images/YYYY-MM-DD/` (for a group)
- **Workspace**: `/stage/dsa110-contimg/workspace/active/mosaicking/`
- **Output**:
  `/stage/dsa110-contimg/mosaics/YYYY-MM-DD/mosaic_<group_id>_<method>.fits`
- **Registration**: `data_registry.sqlite3` with `data_type="mosaic"`

#### **Stage 8: Cross-Matching** (Optional)

- **Input**: Mosaic from `mosaics/`
- **Output**: Catalog →
  `/stage/dsa110-contimg/products/catalogs/YYYY-MM-DD/catalog_<mosaic_id>.fits`

#### **Stage 9: Publishing**

- **Input**: Products from `/stage/dsa110-contimg/products/`
- **Action**: Move to `/data/dsa110-contimg/products/`
- **Output**: Published products in HDD archive
- **Registration**: Update `data_registry.sqlite3` status to "published"

---

## Key Improvements

### 1. **Clear Data Provenance**

```
Raw MS (uncalibrated)
  ↓ [Stage 4-5: Calibration]
Calibrated MS
  ↓ [Stage 6: Imaging]
Image
  ↓ [Stage 7: Mosaicking]
Mosaic
  ↓ [Stage 9: Publishing]
Published Product
```

Each transformation creates a new, clearly-labeled product in a distinct
directory.

### 2. **Better Organization**

- **Raw data** clearly separated from **processed data**
- **Calibration products** (tables + calibrated MS) grouped together
- **Workspace** for active processing, separate from final products
- **Products** directory for validated, ready-to-publish items

### 3. **Scientific Workflow Alignment**

- Directory structure mirrors the 9-stage pipeline
- Each stage has a clear input/output location
- Group information preserved in `raw/groups/`
- Calibration tables stored with date/group organization

### 4. **Performance Optimization**

- **SSD (`/stage/`)**: Active processing, recent data, temporary workspace
- **HDD (`/data/`)**: Long-term archive, published products
- Clear separation allows efficient cleanup of staging area
- Workspace directory can be on fastest storage (tmpfs option)

### 5. **Improved Debugging**

- Failed processing attempts in `workspace/failed/` with error logs
- Active processing visible in `workspace/active/`
- Clear lineage: can trace any product back to raw MS
- Group definitions preserved for reprocessing

---

## Migration Strategy

### Phase 1: Add New Structure (Non-Breaking)

1. Create new directory structure alongside existing
2. Update code to write to both old and new locations
3. Add symlinks for backward compatibility

### Phase 2: Update Pipeline Code

1. Modify each stage to use new paths
2. Update database registration to use new paths
3. Add migration scripts for existing data

### Phase 3: Data Migration

1. Move existing data to new structure
2. Update database references
3. Verify all paths resolve correctly

### Phase 4: Cleanup

1. Remove old directory structure
2. Remove symlinks
3. Update documentation

---

## Configuration Changes

### New Environment Variables

```python
# Base directories
CONTIMG_STAGE_BASE = "/stage/dsa110-contimg"
CONTIMG_DATA_BASE = "/data/dsa110-contimg"

# Stage-specific directories
CONTIMG_RAW_MS_DIR = f"{CONTIMG_STAGE_BASE}/raw/ms"
CONTIMG_CALIBRATED_MS_DIR = f"{CONTIMG_STAGE_BASE}/calibrated/ms"
CONTIMG_CALIBRATION_TABLES_DIR = f"{CONTIMG_STAGE_BASE}/calibrated/tables"
CONTIMG_IMAGES_DIR = f"{CONTIMG_STAGE_BASE}/images"
CONTIMG_MOSAICS_DIR = f"{CONTIMG_STAGE_BASE}/mosaics"
CONTIMG_PRODUCTS_DIR = f"{CONTIMG_STAGE_BASE}/products"
CONTIMG_WORKSPACE_DIR = f"{CONTIMG_STAGE_BASE}/workspace"

# Published products
CONTIMG_PUBLISHED_PRODUCTS_DIR = f"{CONTIMG_DATA_BASE}/products"
```

### Updated Data Type Configuration

```python
DATA_TYPES = {
    "raw_ms": {
        "staging_dir": STAGE_BASE / "raw/ms",
        "published_dir": None,  # Raw MS not published
    },
    "calibrated_ms": {
        "staging_dir": STAGE_BASE / "calibrated/ms",
        "published_dir": PRODUCTS_BASE / "ms",  # Optional: publish calibrated MS
    },
    "calibration_table": {
        "staging_dir": STAGE_BASE / "calibrated/tables",
        "published_dir": PRODUCTS_BASE / "caltables",
    },
    "image": {
        "staging_dir": STAGE_BASE / "images",
        "published_dir": PRODUCTS_BASE / "images",  # Optional
    },
    "mosaic": {
        "staging_dir": STAGE_BASE / "mosaics",
        "published_dir": PRODUCTS_BASE / "mosaics",
    },
}
```

---

## Benefits Summary

### For Scientists

- **Intuitive structure**: Matches scientific workflow
- **Clear provenance**: Easy to trace data lineage
- **Easy reprocessing**: Group definitions preserved
- **Better debugging**: Failed jobs clearly visible

### For Operators

- **Easier monitoring**: Active processing visible in workspace
- **Clear cleanup**: Know what's temporary vs permanent
- **Better organization**: Logical grouping by stage
- **Efficient storage**: SSD for active, HDD for archive

### For Developers

- **Clearer code**: Paths reflect processing stages
- **Better testing**: Can test each stage independently
- **Easier debugging**: Structure matches code flow
- **Maintainable**: Intuitive organization

---

## Implementation Considerations

### Backward Compatibility

- Maintain old paths during transition
- Use symlinks where possible
- Gradual migration of existing data

### Performance

- Workspace on fastest storage (tmpfs option)
- Batch moves for publishing (not individual files)
- Efficient cleanup of workspace after completion

### Error Handling

- Failed jobs moved to `workspace/failed/` with logs
- Preserve intermediate products for debugging
- Clear retry mechanisms

### Monitoring

- Track data in each stage directory
- Monitor workspace for stuck jobs
- Alert on failed directory growth

---

## Next Steps

1. **Review and refine** this proposal with team
2. **Create detailed migration plan** with timeline
3. **Implement Phase 1** (add new structure, dual-write)
4. **Update pipeline code** to use new paths
5. **Migrate existing data** to new structure
6. **Update documentation** and training materials
