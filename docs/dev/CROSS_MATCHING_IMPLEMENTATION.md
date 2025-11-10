# Cross-Matching Implementation Summary

## Date: 2025-11-10

## Overview

This document summarizes the implementation of cross-matching functionality in the DSA-110 pipeline, following VAST pipeline patterns and recommendations.

## Implementation Status

### ✅ Completed

1. **Standalone Cross-Matching Utility** (`src/dsa110_contimg/catalog/crossmatch.py`)
   - `cross_match_sources()` - General-purpose cross-matching
   - `cross_match_dataframes()` - DataFrame convenience wrapper
   - `calculate_positional_offsets()` - Median offsets and MAD
   - `calculate_flux_scale()` - Flux scale correction factor
   - `search_around_sky()` - Advanced matching (all matches)
   - `multi_catalog_match()` - Match against multiple catalogs

2. **Database Schema** (`src/dsa110_contimg/database/schema_evolution.py`)
   - Added `cross_matches` table with:
     - Source and catalog IDs
     - Separation, offsets, flux ratios
     - Match quality and method
     - Timestamps
   - Indexes for efficient querying

3. **Pipeline Configuration** (`src/dsa110_contimg/pipeline/config.py`)
   - Added `CrossMatchConfig` class with:
     - `enabled` - Enable/disable cross-matching
     - `catalog_types` - List of catalogs to match against
     - `radius_arcsec` - Matching radius
     - `method` - Basic or advanced matching
     - `store_in_database` - Database storage flag
     - `min_separation_arcsec` / `max_separation_arcsec` - Filtering limits

4. **CrossMatchStage** (`src/dsa110_contimg/pipeline/stages_impl.py`)
   - Pipeline stage for cross-matching
   - Supports multiple catalogs (NVSS, FIRST, RACS)
   - Calculates offsets and flux scales
   - Stores results in database
   - Handles errors gracefully

5. **Module Exports** (`src/dsa110_contimg/catalog/__init__.py`)
   - Exported all cross-matching functions for easy import

### 🔄 In Progress

1. **Update Validation Functions**
   - Replace embedded matching in `validate_astrometry()`, `validate_flux_scale()`, `validate_source_counts()`
   - Use `cross_match_dataframes()` instead of direct `match_coordinates_sky()` calls

2. **Add to Workflows**
   - Add `CrossMatchStage` to `standard_imaging_workflow()`
   - Add to `quicklook_workflow()` and `reprocessing_workflow()`
   - Configure dependencies (after validation/photometry)

### 📋 TODO

1. **Update Validation Functions**
   - Refactor `validate_astrometry()` to use `cross_match_dataframes()`
   - Refactor `validate_flux_scale()` to use `cross_match_dataframes()`
   - Refactor `validate_source_counts()` to use `cross_match_dataframes()`

2. **Workflow Integration**
   - Add `CrossMatchStage` to workflows
   - Configure stage dependencies
   - Test end-to-end pipeline execution

3. **Testing**
   - Unit tests for `crossmatch.py` functions
   - Integration tests for `CrossMatchStage`
   - Database schema migration tests

4. **Documentation**
   - User guide for cross-matching
   - API documentation
   - Examples and use cases

## Key Features

### Cross-Matching Methods

1. **Basic Matching** (default)
   - Nearest neighbor matching
   - Uses `match_coordinates_sky()`
   - Fast and simple
   - Good for most use cases

2. **Advanced Matching**
   - Finds all matches within radius
   - Uses `search_around_sky()`
   - More flexible but slower
   - Useful for complex associations

### Match Quality Assessment

Matches are automatically classified by separation:
- **Excellent**: < 2 arcsec
- **Good**: 2-5 arcsec
- **Fair**: 5-10 arcsec
- **Poor**: > 10 arcsec

### Database Storage

Cross-match results are stored in `cross_matches` table with:
- Source and catalog IDs
- Separation and offsets
- Flux information
- Match quality and method
- Timestamps

## Usage Examples

### Standalone Cross-Matching

```python
from dsa110_contimg.catalog.crossmatch import cross_match_dataframes

# Match detected sources with catalog
matches = cross_match_dataframes(
    detected_df=detected_sources,
    catalog_df=catalog_sources,
    radius_arcsec=10.0,
    detected_ra_col="ra_deg",
    detected_dec_col="dec_deg",
    catalog_ra_col="ra_deg",
    catalog_dec_col="dec_deg",
)

# Calculate offsets
from dsa110_contimg.catalog.crossmatch import calculate_positional_offsets
dra_median, ddec_median, dra_madfm, ddec_madfm = calculate_positional_offsets(matches)
```

### Pipeline Integration

```python
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.stages_impl import CrossMatchStage

# Configure cross-matching
config = PipelineConfig.from_env()
config.crossmatch.enabled = True
config.crossmatch.catalog_types = ["nvss", "first"]
config.crossmatch.radius_arcsec = 10.0
config.crossmatch.method = "basic"

# Create and execute stage
stage = CrossMatchStage(config)
context = stage.execute(context)
```

## Configuration

Cross-matching can be configured via `PipelineConfig`:

```python
crossmatch:
  enabled: true
  catalog_types: ["nvss", "first", "rax"]
  radius_arcsec: 10.0
  method: "basic"  # or "advanced"
  store_in_database: true
  min_separation_arcsec: 0.1
  max_separation_arcsec: 60.0
```

## Database Schema

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
    created_at REAL NOT NULL,
    FOREIGN KEY (source_id) REFERENCES variability_stats(source_id)
);
```

## Next Steps

1. Complete validation function refactoring
2. Add CrossMatchStage to workflows
3. Write comprehensive tests
4. Update user documentation
5. Add API endpoints for cross-match queries

## Related Documentation

- `docs/reference/EXISTING_CROSS_MATCHING_TOOLS.md` - Current tools
- `docs/reference/EXTERNAL_CROSS_MATCHING_TOOLS_SURVEY.md` - External tools survey
- `docs/reference/VAST_PIPELINE_CROSS_MATCHING_INTEGRATION.md` - VAST patterns
- `docs/reference/CATALOG_CROSS_MATCHING_GUIDE.md` - Cross-matching strategies

