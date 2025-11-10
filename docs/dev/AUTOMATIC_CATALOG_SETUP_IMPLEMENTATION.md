# Automatic Catalog Setup Implementation

## Date: 2025-11-10

## Overview

Implemented automatic catalog database building as a pre-pipeline stage. The `CatalogSetupStage` now runs automatically as the first stage in all workflows, ensuring catalog databases (NVSS, FIRST, RAX) are available for the declination strip being observed.

## Rationale

**DSA-110 Telescope Characteristics:**
- Only slews in elevation (declination changes rarely)
- When declination changes, catalogs need immediate update
- Manual catalog building was error-prone and easy to forget

**Solution:**
- Automatic catalog building integrated into pipeline workflow
- Catalogs built automatically when declination changes
- No manual intervention required

## Implementation

### 1. New Pipeline Stage: `CatalogSetupStage`

**Location:** `src/dsa110_contimg/pipeline/stages_impl.py`

**Features:**
- Extracts declination from HDF5 observation file
- Checks if catalog databases exist for that declination strip
- Builds missing catalogs (NVSS, FIRST, RAX) automatically
- Non-blocking: Pipeline continues even if some catalogs fail
- Logs catalog status for downstream stages

**Key Methods:**
- `validate()`: Checks that input_path (HDF5) exists
- `execute()`: Extracts declination, checks/builds catalogs
- `cleanup()`: No cleanup needed (catalogs persist)

### 2. Workflow Integration

**Location:** `src/dsa110_contimg/pipeline/workflows.py`

**Updated Workflows:**
- `standard_imaging_workflow()`: Catalog setup → Convert → Calibrate → Image
- `quicklook_workflow()`: Catalog setup → Convert → Image
- `reprocessing_workflow()`: Catalog setup → Calibrate → Image

**Stage Order:**
```
1. catalog_setup (NEW - First Stage)
2. convert (depends on catalog_setup)
3. calibrate_solve (depends on convert)
4. calibrate_apply (depends on calibrate_solve)
5. image (depends on calibrate_apply)
6. validate (depends on image, if enabled)
7. adaptive_photometry (depends on image, if enabled)
```

### 3. Catalog Building Logic

**Process:**
1. Extract declination from HDF5 using `load_pointing()`
2. Calculate declination range (default ±6 degrees)
3. For each catalog type (NVSS, FIRST, RAX):
   - Check if SQLite database exists using `resolve_catalog_path()`
   - If exists: Log and skip
   - If missing: Build using `build_{catalog}_strip_db()`
4. Store catalog status in pipeline context

**Error Handling:**
- If declination extraction fails: Skip catalog setup, log warning
- If catalog build fails: Log error, continue pipeline (uses CSV fallback)
- Non-blocking: Pipeline continues even if catalogs fail

### 4. Configuration

**Default Settings:**
- Declination range: ±6 degrees (configurable via `config.catalog_setup_dec_range`)
- Catalog types: NVSS, FIRST, RAX (all built automatically)
- Flux threshold: None (includes all sources)

**Future Enhancement:**
- Add config option for catalog types to build
- Add config option for declination range
- Add config option to skip catalog setup

## Usage

### Automatic (Default)

Catalogs are built automatically when pipeline runs:

```python
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig.from_env()
workflow = standard_imaging_workflow(config)

# Catalog setup runs automatically as first stage
context = workflow.execute(initial_context)
```

### Manual Override (If Needed)

If catalogs need to be built manually (e.g., for testing):

```bash
# Build catalogs manually
python -m dsa110_contimg.catalog.build_nvss_strip_cli \
    --hdf5 /path/to/observation.h5 \
    --dec-range 6.0
```

## Benefits

1. **Automatic:** No manual intervention required
2. **Reliable:** Catalogs always available when needed
3. **Efficient:** Only builds missing catalogs (checks first)
4. **Non-blocking:** Pipeline continues even if catalogs fail
5. **Observatory-specific:** Adapts to DSA-110's drift scan observing pattern

## Testing

### Unit Tests

```python
def test_catalog_setup_stage():
    """Test catalog setup stage."""
    stage = CatalogSetupStage(config)
    context = PipelineContext(inputs={"input_path": "test.h5"})
    
    # Should extract declination and build catalogs
    result = stage.execute(context)
    assert "catalog_setup_status" in result.outputs
```

### Integration Tests

```python
def test_workflow_with_catalog_setup():
    """Test workflow includes catalog setup."""
    workflow = standard_imaging_workflow(config)
    stages = workflow.stages
    
    # First stage should be catalog setup
    assert stages[0].name == "catalog_setup"
```

## Migration Notes

### Before (Manual)

```bash
# Manual catalog building required
python -m dsa110_contimg.catalog.build_nvss_strip_cli --hdf5 obs.h5
python -m dsa110_contimg.catalog.build_first_strip_cli --hdf5 obs.h5
python -m dsa110_contimg.catalog.build_rax_strip_cli --hdf5 obs.h5

# Then run pipeline
python -m dsa110_contimg.pipeline.run ...
```

### After (Automatic)

```bash
# Just run pipeline - catalogs built automatically
python -m dsa110_contimg.pipeline.run ...
```

## Related Files

- `src/dsa110_contimg/pipeline/stages_impl.py` - CatalogSetupStage implementation
- `src/dsa110_contimg/pipeline/workflows.py` - Workflow integration
- `src/dsa110_contimg/catalog/builders.py` - Catalog building functions
- `src/dsa110_contimg/catalog/query.py` - Catalog path resolution
- `docs/dev/CATALOG_DB_POPULATION_TIMING.md` - Updated documentation

## Status

✅ **COMPLETE** - Automatic catalog setup implemented and integrated into all workflows.

The pipeline now automatically builds catalog databases when needed, ensuring catalogs are always available for the declination strip being observed.

