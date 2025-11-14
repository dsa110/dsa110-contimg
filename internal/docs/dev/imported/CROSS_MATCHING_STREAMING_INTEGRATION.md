# Cross-Matching Integration in Streaming Mode

## Overview

Cross-matching functionality has been integrated into the streaming mosaic workflow, allowing automatic catalog cross-matching for mosaics created in streaming mode.

## Implementation

### Changes to `StreamingMosaicManager`

1. **Added `config` parameter to `__init__`**:
   - Optional `PipelineConfig` parameter
   - If not provided, attempts to load from environment variables
   - Falls back to default config if environment variables are unavailable

2. **Added `run_crossmatch_for_mosaic()` method**:
   - Creates a `PipelineContext` with the mosaic image path
   - Instantiates and executes `CrossMatchStage`
   - Handles validation and error cases gracefully
   - Returns cross-match status

3. **Integrated into `process_next_group()` methods**:
   - Both `process_next_group()` variants now call cross-matching after mosaic creation
   - Cross-matching failures are logged as warnings but don't halt processing
   - Only runs if `config.crossmatch.enabled` is `True`

## Usage

### Default Behavior

By default, cross-matching is **enabled** (`CrossMatchConfig.enabled=True`). To disable:

```python
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig()
config.crossmatch.enabled = False

manager = StreamingMosaicManager(
    products_db_path=products_db_path,
    registry_db_path=registry_db_path,
    ms_output_dir=ms_output_dir,
    images_dir=images_dir,
    mosaic_output_dir=mosaic_output_dir,
    config=config,
)
```

### Configuration Options

Cross-matching behavior can be configured via `PipelineConfig.crossmatch`:

```python
config.crossmatch.catalog_types = ["nvss", "first", "rax"]  # Catalogs to match
config.crossmatch.radius_arcsec = 10.0  # Matching radius
config.crossmatch.method = "basic"  # or "advanced"
config.crossmatch.min_separation_arcsec = 0.1
config.crossmatch.max_separation_arcsec = 60.0
```

### Environment Variables

Cross-matching configuration can also be set via environment variables (see `PipelineConfig.from_env()` documentation).

## Integration Points

### Manual Mode

Cross-matching is already integrated into manual pipeline workflows via `workflows.py`:
- `standard_imaging_workflow()`
- `quicklook_workflow()`
- `reprocessing_workflow()`

All workflows include `CrossMatchStage` after `ValidationStage` if `config.crossmatch.enabled` is `True`.

### Streaming Mode

Cross-matching runs automatically after each mosaic is created in streaming mode:
1. Group of MS files is processed (calibration → imaging → mosaic)
2. Mosaic is created
3. **Cross-matching runs** (if enabled)
4. Processing continues to next group

## Error Handling

- Cross-matching failures are logged as warnings but don't halt the streaming workflow
- If validation fails (e.g., no sources detected), cross-matching is skipped gracefully
- Database errors are caught and logged, allowing processing to continue

## Database Integration

Cross-match results are stored in the `cross_matches` table in `products.sqlite3`:
- `source_id`: Detected source identifier
- `catalog_type`: Catalog name (nvss, first, rax)
- `catalog_source_id`: Catalog source identifier
- `separation_arcsec`: Angular separation
- `master_catalog_id`: Master catalog ID for deduplication
- `match_quality`: Quality classification (excellent, good, fair, poor)

## Testing

To test cross-matching in streaming mode:

```python
from dsa110_contimg.mosaic.streaming_mosaic import StreamingMosaicManager
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig()
config.crossmatch.enabled = True
config.crossmatch.catalog_types = ["nvss"]

manager = StreamingMosaicManager(
    products_db_path=Path("products.sqlite3"),
    registry_db_path=Path("registry.sqlite3"),
    ms_output_dir=Path("ms/"),
    images_dir=Path("images/"),
    mosaic_output_dir=Path("mosaics/"),
    config=config,
)

# Process next group (will run cross-matching automatically)
manager.process_next_group()
```

## Logging

Cross-matching activity is logged at INFO level:
- Start of cross-matching: `"Running cross-matching for mosaic: {path}"`
- Completion: `"Cross-matching completed for {path}: status={status}, matches={n_matches}, catalogs={n_catalogs}"`
- Warnings: `"Cross-matching failed for group {group_id}: {error}"`

## Future Enhancements

Potential improvements:
1. Configurable retry logic for cross-matching failures
2. Parallel cross-matching for multiple mosaics
3. Cross-match quality metrics in mosaic metadata
4. Integration with photometry stage for forced photometry at catalog positions

