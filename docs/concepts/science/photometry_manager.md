# PhotometryManager Architecture

**Purpose:** Centralized photometry workflow coordination  
**Last Updated:** 2025-01-XX  
**Status:** Production

---

## Overview

The `PhotometryManager` class consolidates scattered photometry functionality
into a unified interface, similar to `StreamingMosaicManager` for mosaic
workflows. It eliminates code duplication and provides a consistent API for
photometry operations across the pipeline.

---

## Architecture

### Class Structure

```python
class PhotometryManager:
    """Manages photometry workflow for images and mosaics."""

    def __init__(
        self,
        products_db_path: Path,
        data_registry_db_path: Optional[Path] = None,
        default_config: Optional[PhotometryConfig] = None,
    )
```

### Key Components

1. **PhotometryConfig**: Configuration class for photometry parameters
   - Catalog selection (nvss, first, rax, vlass, master)
   - Search radius (0.5° for images, 1.0° for mosaics)
   - Source filtering (min flux, max sources)
   - Measurement method (peak, adaptive, aegean)
   - Normalization and ESE detection flags

2. **PhotometryResult**: Result container
   - Sources queried count
   - Measurements successful/total
   - Batch job ID (if async)
   - Measurement results (if sync)

3. **PhotometryManager**: Main workflow coordinator
   - `measure_for_fits()`: Complete workflow for single FITS image
   - `measure_for_mosaic()`: Complete workflow for mosaic FITS
   - `_create_batch_job()`: Create async batch jobs
   - `_link_to_data_registry()`: Link results to data registry

---

## Workflow

### Complete Photometry Workflow

1. **Query Catalog Sources**
   - Extract field center from FITS
   - Query catalog (NVSS, FIRST, etc.) within radius
   - Filter by flux threshold and max sources

2. **Measure Photometry**
   - Forced photometry (peak fitting)
   - Adaptive binning (optional)
   - Aegean fitting (optional)

3. **Normalize** (optional)
   - Use reference sources for flux calibration
   - Ensemble correction

4. **Detect ESE Candidates** (optional)
   - Variability analysis
   - Significance scoring

5. **Store Results**
   - Insert into products database
   - Link to data registry

6. **Link to Data Registry**
   - Associate photometry job with data product
   - Update status tracking

---

## Usage Examples

### Basic Usage

```python
from dsa110_contimg.photometry import PhotometryManager, PhotometryConfig
from pathlib import Path

# Initialize manager
manager = PhotometryManager(
    products_db_path=Path("state/products.sqlite3"),
    data_registry_db_path=Path("state/data_registry.sqlite3"),
    default_config=PhotometryConfig(
        catalog="nvss",
        radius_deg=0.5,
        method="peak",
    ),
)

# Measure photometry for a FITS image
result = manager.measure_for_fits(
    fits_path=Path("image.fits"),
    create_batch_job=True,  # Async execution
    data_id="image_20250101",
)

if result:
    print(f"Created batch job {result.batch_job_id}")
    print(f"Found {result.sources_queried} sources")
```

### Mosaic Photometry

```python
# Measure photometry for a mosaic (larger search radius)
result = manager.measure_for_mosaic(
    mosaic_path=Path("mosaic.fits"),
    create_batch_job=True,
    data_id="mosaic_20250101",
)
```

### Synchronous Execution

```python
# Execute synchronously (returns results immediately)
result = manager.measure_for_fits(
    fits_path=Path("image.fits"),
    create_batch_job=False,  # Sync execution
)

if result and result.results:
    for r in result.results:
        if r.success:
            print(f"Source: {r.ra_deg:.6f}, {r.dec_deg:.6f}, Flux: {r.peak_jyb:.3f} Jy/beam")
```

---

## Integration Points

### MosaicOrchestrator

The `MosaicOrchestrator` uses `PhotometryManager` to trigger photometry after
mosaic creation:

```python
# In MosaicOrchestrator.__init__
if self.enable_photometry:
    pm_config = PhotometryConfig.from_dict(photometry_config_dict)
    self.photometry_manager = PhotometryManager(
        products_db_path=self.products_db_path,
        data_registry_db_path=self.data_registry_db_path,
        default_config=pm_config,
    )

# In _trigger_photometry_for_mosaic()
result = self.photometry_manager.measure_for_mosaic(
    mosaic_path=mosaic_path,
    create_batch_job=True,
    data_id=mosaic_data_id,
)
```

### Streaming Converter

The streaming converter uses `PhotometryManager` for per-image photometry:

```python
# In trigger_photometry_for_image()
config = PhotometryConfig(
    catalog=getattr(args, "photometry_catalog", "nvss"),
    radius_deg=getattr(args, "photometry_radius", 0.5),
    method="peak",
    normalize=getattr(args, "photometry_normalize", False),
)

manager = PhotometryManager(
    products_db_path=products_db_path,
    data_registry_db_path=data_registry_db_path,
    default_config=config,
)

result = manager.measure_for_fits(
    fits_path=image_path,
    create_batch_job=True,
    data_id=image_data_id,
)
```

---

## Benefits

### Code Consolidation

- **Eliminates duplication**: Replaces `_trigger_photometry_for_mosaic()` and
  `trigger_photometry_for_image()` with unified interface
- **Consistent API**: Same interface for images and mosaics
- **Centralized configuration**: Single source of truth for photometry settings

### Maintainability

- **Single point of change**: Updates to workflow logic happen in one place
- **Easier testing**: Mockable interface for unit tests
- **Clear separation**: Workflow coordination separate from measurement logic

### Extensibility

- **Future enhancements**: Easy to add normalization, ESE detection, etc.
- **Configuration flexibility**: Supports per-call overrides
- **Async/sync support**: Handles both batch jobs and direct execution

---

## Related Documentation

- [Variability Metrics](science/variability_metrics.md) - Definitions of
  variability statistics
- [Photometry Module](../reference/photometry.md) - Detailed photometry API
- [Mosaic Orchestrator](mosaic_orchestrator.md) - Mosaic workflow coordination
- [Streaming Converter](../how-to/streaming_converter.md) - Streaming pipeline

---

## Migration Notes

### Replaced Functions

- `MosaicOrchestrator._trigger_photometry_for_mosaic()` →
  `PhotometryManager.measure_for_mosaic()`
- `trigger_photometry_for_image()` → `PhotometryManager.measure_for_fits()`

### Backward Compatibility

- `MosaicOrchestrator.photometry_config` dict is still available for backward
  compatibility
- Old function signatures maintained (wrappers around PhotometryManager)

---

**See Also:**

- `src/dsa110_contimg/photometry/manager.py` - Implementation
- `src/dsa110_contimg/photometry/__init__.py` - Public API exports
