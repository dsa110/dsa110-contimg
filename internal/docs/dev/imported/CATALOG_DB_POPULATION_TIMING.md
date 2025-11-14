# Catalog Database Population Timing in Pipeline Workflow

## Date: 2025-11-10

## Overview

This document explains when catalog SQLite databases (NVSS, FIRST, RAX) are populated in the DSA-110 pipeline workflow.

## Current Status: Automatic Pre-Pipeline Setup ✓

**Catalog databases are now automatically built during pipeline execution.**

A new `CatalogSetupStage` runs as the first stage in all workflows, automatically:
1. Extracting declination from the observation (HDF5 file)
2. Checking if catalog databases exist for that declination strip
3. Building missing catalogs (NVSS, FIRST, RAX) automatically
4. Logging catalog status for downstream stages

**Manual building is no longer required** - catalogs are built automatically when needed.

## When Catalogs Are Used

### 1. Imaging Stage (`ImagingStage`)

**Location:** `src/dsa110_contimg/pipeline/stages_impl.py::ImagingStage`

**Usage:**
- **NVSS Mask**: If `use_nvss_mask=True` (default), queries NVSS catalog to create source mask
- **Catalog Validation**: If `run_catalog_validation=True`, validates flux scale against catalog

**When:** During imaging stage execution

**Code:**
```python
# In ImagingStage.run()
if context.config.imaging.use_nvss_mask:
    # Queries NVSS catalog for sources in field
    # Uses query_sources() which auto-resolves to SQLite if available

if context.config.imaging.run_catalog_validation:
    self._run_catalog_validation(
        primary_image, 
        context.config.imaging.catalog_validation_catalog
    )
```

### 2. Validation Stage (`ValidationStage`)

**Location:** `src/dsa110_contimg/pipeline/stages_impl.py::ValidationStage`

**Usage:**
- **Catalog Validation**: Validates astrometry, flux scale, and source counts against catalog
- **HTML Reports**: Generates validation reports with catalog comparisons

**When:** During validation stage execution (if enabled)

**Code:**
```python
# In ValidationStage.run()
from dsa110_contimg.qa.catalog_validation import run_full_validation

astrometry_result, flux_scale_result, source_counts_result = (
    run_full_validation(
        image_path=fits_image,
        catalog=catalog,  # 'nvss' or 'vlass'
        validation_types=validation_types,
        ...
    )
)
```

### 3. Adaptive Photometry Stage (`AdaptivePhotometryStage`)

**Location:** `src/dsa110_contimg/pipeline/stages_impl.py::AdaptivePhotometryStage`

**Usage:**
- **Source Selection**: Queries NVSS catalog for sources in field if no explicit coordinates provided
- **Forced Photometry**: Performs forced photometry at catalog source positions

**When:** During adaptive photometry stage execution (if enabled)

**Code:**
```python
# In AdaptivePhotometryStage.run()
# Query NVSS catalog for sources in the field
from dsa110_contimg.catalog.query import query_sources

catalog_sources = query_sources(
    catalog_type="nvss",
    ra_center=ra_deg,
    dec_center=dec_deg,
    radius_deg=radius_deg,
    min_flux_mjy=config.photometry.min_nvss_flux_mjy
)
```

### 4. Mosaic Streaming (`StreamingMosaicManager`)

**Location:** `src/dsa110_contimg/mosaic/streaming_mosaic.py`

**Usage:**
- **Catalog Overlay**: Uses catalog sources for overlay visualization
- **Validation**: May use catalogs for mosaic validation

**When:** During streaming mosaic generation

## Catalog Resolution Logic

The catalog query system (`dsa110_contimg.catalog.query`) uses this precedence:

1. **Explicit path** (if provided)
2. **Environment variable** (`NVSS_CATALOG`, `FIRST_CATALOG`, `RAX_CATALOG`)
3. **Per-declination SQLite database** (`state/catalogs/{catalog}_dec{dec}.sqlite3`)
4. **Master catalog** (`state/catalogs/master_sources.sqlite3`)
5. **CSV fallback** (NVSS only - auto-downloads if needed)

**Key Point:** If SQLite databases don't exist, the system falls back to CSV files (slower) or raises `FileNotFoundError`.

## When to Build Catalog Databases

### Recommended: Pre-Pipeline Setup

Build catalog databases **before running the pipeline** for the declination strips you'll be observing:

```bash
# Build NVSS catalog for declination strip
python -m dsa110_contimg.catalog.build_nvss_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0

# Build FIRST catalog for same declination strip
python -m dsa110_contimg.catalog.build_first_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0

# Build RAX catalog for same declination strip
python -m dsa110_contimg.catalog.build_rax_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0
```

### When to Build

1. **Before first pipeline run** for a new declination strip
2. **Periodically** if catalog data is updated
3. **As needed** when catalog validation fails due to missing database

## Current Workflow

```
1. Pipeline Execution (Automatic):
   ├─ Catalog Setup Stage (NEW - First Stage)
   │   ├─ Extract declination from HDF5 observation
   │   ├─ Check if NVSS/FIRST/RAX databases exist
   │   └─ Build missing catalogs automatically
   ├─ Conversion Stage
   ├─ Calibration Stage
   ├─ Imaging Stage
   │   ├─ Uses NVSS catalog (SQLite now guaranteed)
   │   └─ Validates against catalog (if enabled)
   ├─ Validation Stage
   │   └─ Validates against catalog (if enabled)
   └─ Photometry Stage
       └─ Queries NVSS catalog (SQLite now guaranteed)
```

## Implementation: Automatic Catalog Setup Stage ✓

**Status:** ✅ **IMPLEMENTED** - Automatic catalog building is now part of the pipeline.

**Implementation:**
- `CatalogSetupStage` runs as the first stage in all workflows
- Automatically extracts declination from HDF5 observation file
- Checks for existing catalog databases (NVSS, FIRST, RAX)
- Builds missing catalogs automatically
- Non-blocking: Pipeline continues even if some catalogs fail (uses CSV fallback)

**Code Location:**
- `src/dsa110_contimg/pipeline/stages_impl.py::CatalogSetupStage`
- Integrated into all workflows in `src/dsa110_contimg/pipeline/workflows.py`

**Rationale:**
- DSA-110 only slews in elevation (declination changes rarely)
- When declination changes, catalogs need immediate update
- Automatic building ensures catalogs are always available for the observed declination strip

## Impact of Missing Catalogs

### If SQLite Database Missing:

1. **NVSS Mask**: Falls back to CSV (slower, but works)
2. **Catalog Validation**: May fail with `FileNotFoundError` if CSV not available
3. **Adaptive Photometry**: Falls back to CSV (slower, but works)
4. **Catalog Overlay**: May fail if catalog not found

### Performance Impact:

- **SQLite**: Fast queries (~milliseconds)
- **CSV**: Slower queries (~seconds to minutes for large catalogs)

## Recommendations

1. **Build catalog databases during setup** for all declination strips you'll observe
2. **Store databases in** `state/catalogs/` (standard location)
3. **Use consistent naming**: `{catalog}_dec{dec:+.1f}.sqlite3`
4. **Consider automation**: Add catalog building to deployment/setup scripts

## Related Documentation

- `docs/how-to/build-nvss-catalog.md` - NVSS catalog building
- `docs/how-to/build-first-rax-catalogs.md` - FIRST/RAX catalog building
- `src/dsa110_contimg/catalog/query.py` - Catalog query system
- `src/dsa110_contimg/pipeline/stages_impl.py` - Pipeline stages

