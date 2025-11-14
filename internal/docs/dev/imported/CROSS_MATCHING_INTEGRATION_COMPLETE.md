# Cross-Matching Integration Complete

## Summary

Cross-matching functionality has been fully integrated into both **manual** and **streaming** modes of the DSA-110 continuum imaging pipeline.

## Integration Status

### Manual Mode ✓

Cross-matching is integrated into all standard pipeline workflows:
- `standard_imaging_workflow()` - Full pipeline with calibration
- `quicklook_workflow()` - Quick imaging without calibration
- `reprocessing_workflow()` - Reprocessing existing MS files

**Integration Point**: `CrossMatchStage` is added after `ValidationStage` in all workflows (if `config.crossmatch.enabled=True`).

**Location**: `src/dsa110_contimg/pipeline/workflows.py`

### Streaming Mode ✓

Cross-matching is integrated into the streaming mosaic workflow:
- Runs automatically after each mosaic is created
- Handles errors gracefully (warnings, doesn't halt processing)
- Uses same `CrossMatchStage` as manual mode for consistency

**Integration Points**:
1. `StreamingMosaicManager.__init__()` - Added optional `config` parameter
2. `StreamingMosaicManager.run_crossmatch_for_mosaic()` - New method to execute cross-matching
3. `StreamingMosaicManager.process_next_group()` - Both variants call cross-matching after mosaic creation

**Location**: `src/dsa110_contimg/mosaic/streaming_mosaic.py`

## Key Features

### Unified Configuration

Both modes use the same `PipelineConfig.crossmatch` configuration:
- `enabled`: Enable/disable cross-matching (default: `True`)
- `catalog_types`: List of catalogs to match (`["nvss"]`, `["nvss", "first", "rax"]`)
- `radius_arcsec`: Matching radius (default: `10.0`)
- `method`: Matching method (`"basic"` or `"advanced"`)
- `min_separation_arcsec`: Minimum valid separation (default: `0.1`)
- `max_separation_arcsec`: Maximum valid separation (default: `60.0`)

### Source Detection

Cross-matching automatically detects sources from:
1. `detected_sources` in context outputs (from photometry/validation stages)
2. `photometry_results` in context outputs
3. `validation_results` in context outputs
4. Direct extraction from image using `extract_sources_from_image()` (fallback)

### Multi-Catalog Matching

- Matches against multiple catalogs simultaneously
- Selects best match across all catalogs
- Handles duplicate sources across catalogs via `master_catalog_id`
- Stores matches in `cross_matches` table with `UNIQUE(source_id, catalog_type)` constraint

### Error Handling

- **Manual Mode**: Cross-matching failures are handled by pipeline retry policies
- **Streaming Mode**: Cross-matching failures log warnings but don't halt processing
- Validation failures (e.g., no sources) skip cross-matching gracefully

## Database Schema

Cross-match results are stored in `cross_matches` table:

```sql
CREATE TABLE cross_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    catalog_type TEXT NOT NULL,
    catalog_source_id TEXT,
    separation_arcsec REAL NOT NULL,
    dra_arcsec REAL,
    ddec_arcsec REAL,
    detected_flux_jy REAL,
    catalog_flux_jy REAL,
    flux_ratio REAL,
    match_quality TEXT,
    match_method TEXT DEFAULT 'basic',
    master_catalog_id TEXT,
    created_at REAL NOT NULL,
    FOREIGN KEY (source_id) REFERENCES variability_stats(source_id),
    UNIQUE(source_id, catalog_type)
)
```

## Usage Examples

### Manual Mode

```python
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

config = PipelineConfig()
config.crossmatch.enabled = True
config.crossmatch.catalog_types = ["nvss", "first"]

orchestrator = standard_imaging_workflow(config)
# Cross-matching runs automatically after validation stage
```

### Streaming Mode

```python
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig()
config.crossmatch.enabled = True

manager = StreamingMosaicManager(
    products_db_path=Path("products.sqlite3"),
    registry_db_path=Path("registry.sqlite3"),
    ms_output_dir=Path("ms/"),
    images_dir=Path("images/"),
    mosaic_output_dir=Path("mosaics/"),
    config=config,
)

# Cross-matching runs automatically after each mosaic
manager.process_next_group()
```

## Testing

### Unit Tests
- `tests/unit/test_crossmatch.py` - Core cross-matching functions
- `tests/integration/test_crossmatch_stage.py` - Stage integration tests

### Manual Testing

1. **Manual Mode**: Run standard pipeline workflow with cross-matching enabled
2. **Streaming Mode**: Process a group and verify cross-matching runs after mosaic creation

## Documentation

- **User Guide**: `docs/how-to/cross-matching-guide.md`
- **Streaming Integration**: `docs/dev/CROSS_MATCHING_STREAMING_INTEGRATION.md`
- **Implementation Details**: `docs/dev/CROSS_MATCHING_IMPLEMENTATION.md`
- **Duplicate Handling**: `docs/dev/CROSS_MATCHING_DUPLICATE_HANDLING.md`

## Next Steps

1. **Performance Optimization**: Consider parallel cross-matching for large mosaics
2. **Quality Metrics**: Add cross-match quality metrics to mosaic metadata
3. **Forced Photometry**: Integrate forced photometry at catalog positions
4. **Visualization**: Add cross-match overlays to postage stamps

## Files Modified

### Core Implementation
- `src/dsa110_contimg/catalog/crossmatch.py` - Core cross-matching functions
- `src/dsa110_contimg/pipeline/stages_impl.py` - `CrossMatchStage` implementation
- `src/dsa110_contimg/pipeline/config.py` - `CrossMatchConfig` class
- `src/dsa110_contimg/database/schema_evolution.py` - `cross_matches` table schema

### Integration
- `src/dsa110_contimg/pipeline/workflows.py` - Manual mode integration
- `src/dsa110_contimg/mosaic/streaming_mosaic.py` - Streaming mode integration

### Tests
- `tests/unit/test_crossmatch.py` - Unit tests
- `tests/integration/test_crossmatch_stage.py` - Integration tests

### Documentation
- `docs/how-to/cross-matching-guide.md` - User guide
- `docs/dev/CROSS_MATCHING_*.md` - Developer documentation

## Status: ✅ Complete

Both manual and streaming modes are fully integrated and tested. Cross-matching runs automatically when enabled and handles errors gracefully.

