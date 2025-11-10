# Cross-Matching Guide

## Overview

Cross-matching is the process of identifying the same astronomical sources in different catalogs or datasets. The DSA-110 pipeline provides comprehensive cross-matching functionality to match detected sources with reference catalogs (NVSS, FIRST, RACS) for astrometry validation, flux scale calibration, and source identification.

## Quick Start

### Basic Cross-Matching

```python
from dsa110_contimg.catalog.crossmatch import cross_match_dataframes
import pandas as pd

# Your detected sources
detected_sources = pd.DataFrame({
    "ra_deg": [10.0, 20.0, 30.0],
    "dec_deg": [0.0, 5.0, 10.0],
    "flux_jy": [1.0, 2.0, 3.0],
})

# Query reference catalog
from dsa110_contimg.catalog.query import query_sources
catalog_sources = query_sources(
    catalog_type="nvss",
    ra_center=20.0,
    dec_center=5.0,
    radius_deg=1.5,
)

# Perform cross-match
matches = cross_match_dataframes(
    detected_df=detected_sources,
    catalog_df=catalog_sources,
    radius_arcsec=10.0,
    detected_ra_col="ra_deg",
    detected_dec_col="dec_deg",
    catalog_ra_col="ra_deg",
    catalog_dec_col="dec_deg",
    detected_flux_col="flux_jy",
    catalog_flux_col="flux_mjy",
)

print(f"Found {len(matches)} matches")
print(matches[["separation_arcsec", "dra_arcsec", "ddec_arcsec", "flux_ratio"]])
```

### Using Pipeline Stage

```python
from dsa110_contimg.pipeline.config import PipelineConfig
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

# Configure cross-matching
config = PipelineConfig.from_env()
config.crossmatch.enabled = True
config.crossmatch.catalog_types = ["nvss", "first"]
config.crossmatch.radius_arcsec = 10.0
config.crossmatch.method = "basic"

# Run pipeline (cross-matching happens automatically)
workflow = standard_imaging_workflow(config)
# ... execute workflow ...
```

## Cross-Matching Functions

### `cross_match_sources()`

General-purpose cross-matching function for numpy arrays.

```python
from dsa110_contimg.catalog.crossmatch import cross_match_sources
import numpy as np

matches = cross_match_sources(
    detected_ra=np.array([10.0, 20.0]),
    detected_dec=np.array([0.0, 5.0]),
    catalog_ra=np.array([10.1, 20.1]),
    catalog_dec=np.array([0.1, 5.1]),
    radius_arcsec=10.0,
    detected_flux=np.array([1.0, 2.0]),
    catalog_flux=np.array([1.1, 2.1]),
)
```

**Parameters:**
- `detected_ra`, `detected_dec`: Arrays of detected source positions (degrees)
- `catalog_ra`, `catalog_dec`: Arrays of catalog source positions (degrees)
- `radius_arcsec`: Matching radius in arcseconds
- `detected_flux`, `catalog_flux`: Optional flux arrays
- `detected_ids`, `catalog_ids`: Optional ID arrays

**Returns:** DataFrame with matches containing:
- `detected_idx`, `catalog_idx`: Indices of matched sources
- `separation_arcsec`: Separation distance
- `dra_arcsec`, `ddec_arcsec`: RA/Dec offsets
- `detected_flux`, `catalog_flux`: Flux values (if provided)
- `flux_ratio`: Flux ratio (if both fluxes provided)

### `cross_match_dataframes()`

Convenience wrapper for DataFrame inputs.

```python
from dsa110_contimg.catalog.crossmatch import cross_match_dataframes

matches = cross_match_dataframes(
    detected_df=detected_sources,
    catalog_df=catalog_sources,
    radius_arcsec=10.0,
    detected_ra_col="ra_deg",
    detected_dec_col="dec_deg",
    catalog_ra_col="ra_deg",
    catalog_dec_col="dec_deg",
    detected_flux_col="flux_jy",  # Optional
    catalog_flux_col="flux_mjy",  # Optional
)
```

### `calculate_positional_offsets()`

Calculate median positional offsets and MAD.

```python
from dsa110_contimg.catalog.crossmatch import calculate_positional_offsets

dra_median, ddec_median, dra_madfm, ddec_madfm = calculate_positional_offsets(matches)

print(f"RA offset: {dra_median.to(u.arcsec).value:.2f} ± {dra_madfm.to(u.arcsec).value:.2f} arcsec")
print(f"Dec offset: {ddec_median.to(u.arcsec).value:.2f} ± {ddec_madfm.to(u.arcsec).value:.2f} arcsec")
```

### `calculate_flux_scale()`

Calculate flux scale correction factor.

```python
from dsa110_contimg.catalog.crossmatch import calculate_flux_scale

flux_corr, flux_ratio = calculate_flux_scale(matches)

print(f"Flux correction factor: {flux_corr.nominal_value:.3f} ± {flux_corr.std_dev:.3f}")
print(f"Flux ratio: {flux_ratio.nominal_value:.3f} ± {flux_ratio.std_dev:.3f}")
```

### `multi_catalog_match()`

Match against multiple catalogs simultaneously.

```python
from dsa110_contimg.catalog.crossmatch import multi_catalog_match
import numpy as np

catalogs = {
    "nvss": {
        "ra": np.array([10.1, 20.1]),
        "dec": np.array([0.1, 5.1]),
        "flux": np.array([1.0, 2.0]),
    },
    "first": {
        "ra": np.array([10.2, 20.2]),
        "dec": np.array([0.2, 5.2]),
        "flux": np.array([1.1, 2.1]),
    },
}

results = multi_catalog_match(
    detected_ra=np.array([10.0, 20.0]),
    detected_dec=np.array([0.0, 5.0]),
    catalogs=catalogs,
    radius_arcsec=10.0,
)

print(results[["best_catalog", "best_separation_arcsec"]])
```

## Pipeline Integration

### Configuration

Cross-matching is configured via `PipelineConfig`:

```python
from dsa110_contimg.pipeline.config import PipelineConfig, CrossMatchConfig

config = PipelineConfig.from_env()
config.crossmatch = CrossMatchConfig(
    enabled=True,
    catalog_types=["nvss", "first", "rax"],
    radius_arcsec=10.0,
    method="basic",  # or "advanced"
    store_in_database=True,
    min_separation_arcsec=0.1,
    max_separation_arcsec=60.0,
)
```

**Configuration Options:**
- `enabled`: Enable/disable cross-matching stage
- `catalog_types`: List of catalogs to match against (`["nvss"]`, `["first"]`, `["rax"]`, or combinations)
- `radius_arcsec`: Matching radius in arcseconds (default: 10.0)
- `method`: Matching method - `"basic"` (nearest neighbor) or `"advanced"` (all matches)
- `store_in_database`: Store results in database (default: True)
- `min_separation_arcsec`: Minimum separation for valid match (default: 0.1)
- `max_separation_arcsec`: Maximum separation for valid match (default: 60.0)

### Workflow Integration

Cross-matching is automatically included in all standard workflows:

```python
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

config = PipelineConfig.from_env()
config.crossmatch.enabled = True

workflow = standard_imaging_workflow(config)
# Cross-matching runs after validation stage
```

### Accessing Results

Cross-match results are available in the pipeline context:

```python
# After pipeline execution
if "crossmatch_results" in context.outputs:
    results = context.outputs["crossmatch_results"]
    
    print(f"Matched {results['n_catalogs']} catalogs")
    print(f"Catalog types: {results['catalog_types']}")
    
    # Access matches for each catalog
    for catalog_type, matches in results["matches"].items():
        print(f"{catalog_type}: {len(matches)} matches")
    
    # Access offsets
    for catalog_type, offsets in results["offsets"].items():
        print(f"{catalog_type} offsets:")
        print(f"  RA: {offsets['dra_median_arcsec']:.2f} arcsec")
        print(f"  Dec: {offsets['ddec_median_arcsec']:.2f} arcsec")
    
    # Access flux scales
    for catalog_type, flux_scale in results["flux_scales"].items():
        print(f"{catalog_type} flux correction: {flux_scale['flux_correction_factor']:.3f}")
```

## Database Storage

Cross-match results are stored in the `cross_matches` table:

```python
import sqlite3
from dsa110_contimg.pipeline.config import PipelineConfig

config = PipelineConfig.from_env()
products_db = config.paths.products_db

conn = sqlite3.connect(products_db)
cursor = conn.cursor()

# Query cross-matches
cursor.execute("""
    SELECT source_id, catalog_type, separation_arcsec, match_quality
    FROM cross_matches
    WHERE catalog_type = 'nvss'
    ORDER BY separation_arcsec
    LIMIT 10
""")

for row in cursor.fetchall():
    source_id, catalog_type, separation, quality = row
    print(f"{source_id}: {separation:.2f} arcsec ({quality})")

conn.close()
```

**Table Schema:**
- `id`: Primary key
- `source_id`: Source identifier (foreign key to `variability_stats`)
- `catalog_type`: Catalog name (`nvss`, `first`, `rax`)
- `catalog_source_id`: Catalog source identifier
- `separation_arcsec`: Separation distance
- `dra_arcsec`, `ddec_arcsec`: RA/Dec offsets
- `detected_flux_jy`, `catalog_flux_jy`: Flux values
- `flux_ratio`: Flux ratio
- `match_quality`: Quality classification (`excellent`, `good`, `fair`, `poor`)
- `match_method`: Matching method used (`basic` or `advanced`)
- `created_at`: Timestamp

## Match Quality

Matches are automatically classified by separation:

- **Excellent**: < 2 arcsec
- **Good**: 2-5 arcsec
- **Fair**: 5-10 arcsec
- **Poor**: > 10 arcsec

## Matching Methods

### Basic Matching (Default)

- Uses nearest-neighbor matching (`match_coordinates_sky`)
- Fast and simple
- Each detected source matches to closest catalog source
- Good for most use cases

### Advanced Matching

- Finds all matches within radius (`search_around_sky`)
- More flexible but slower
- Useful for complex associations or when multiple matches are expected
- Can handle many-to-many relationships

## Examples

### Example 1: Validate Astrometry

```python
from dsa110_contimg.catalog.crossmatch import cross_match_dataframes, calculate_positional_offsets
from dsa110_contimg.catalog.query import query_sources

# Get detected sources from image
detected_sources = extract_sources_from_image("image.fits", min_snr=5.0)

# Query NVSS catalog
catalog_sources = query_sources(
    catalog_type="nvss",
    ra_center=detected_sources["ra_deg"].median(),
    dec_center=detected_sources["dec_deg"].median(),
    radius_deg=1.5,
)

# Cross-match
matches = cross_match_dataframes(
    detected_df=detected_sources,
    catalog_df=catalog_sources,
    radius_arcsec=10.0,
)

# Calculate offsets
dra_median, ddec_median, dra_madfm, ddec_madfm = calculate_positional_offsets(matches)

print(f"Astrometry offsets:")
print(f"  RA: {dra_median.to(u.arcsec).value:.2f} ± {dra_madfm.to(u.arcsec).value:.2f} arcsec")
print(f"  Dec: {ddec_median.to(u.arcsec).value:.2f} ± {ddec_madfm.to(u.arcsec).value:.2f} arcsec")
```

### Example 2: Flux Scale Calibration

```python
from dsa110_contimg.catalog.crossmatch import cross_match_dataframes, calculate_flux_scale

# Cross-match with flux information
matches = cross_match_dataframes(
    detected_df=detected_sources,
    catalog_df=catalog_sources,
    radius_arcsec=10.0,
    detected_flux_col="flux_jy",
    catalog_flux_col="flux_mjy",
)

# Calculate flux scale
flux_corr, flux_ratio = calculate_flux_scale(matches)

print(f"Flux correction factor: {flux_corr.nominal_value:.3f} ± {flux_corr.std_dev:.3f}")
print(f"Apply correction: corrected_flux = detected_flux * {flux_corr.nominal_value:.3f}")
```

### Example 3: Multi-Catalog Matching

```python
from dsa110_contimg.catalog.crossmatch import multi_catalog_match
from dsa110_contimg.catalog.query import query_sources

# Query multiple catalogs
nvss_sources = query_sources(catalog_type="nvss", ra_center=20.0, dec_center=5.0, radius_deg=1.5)
first_sources = query_sources(catalog_type="first", ra_center=20.0, dec_center=5.0, radius_deg=1.5)

# Prepare catalog dictionaries
catalogs = {
    "nvss": {
        "ra": nvss_sources["ra_deg"].values,
        "dec": nvss_sources["dec_deg"].values,
        "flux": nvss_sources.get("flux_mjy", [0] * len(nvss_sources)).values,
    },
    "first": {
        "ra": first_sources["ra_deg"].values,
        "dec": first_sources["dec_deg"].values,
        "flux": first_sources.get("flux_mjy", [0] * len(first_sources)).values,
    },
}

# Match against all catalogs
results = multi_catalog_match(
    detected_ra=detected_sources["ra_deg"].values,
    detected_dec=detected_sources["dec_deg"].values,
    catalogs=catalogs,
    radius_arcsec=10.0,
)

# Find best match for each source
for idx, row in results.iterrows():
    print(f"Source {idx}: best match in {row['best_catalog']} "
          f"at {row['best_separation_arcsec']:.2f} arcsec")
```

## Best Practices

1. **Choose Appropriate Radius**: Use 2-3× the astrometric uncertainty for matching radius
2. **Filter by Quality**: Use `match_quality` to filter matches (e.g., only `excellent` or `good`)
3. **Check Separation Limits**: Use `min_separation_arcsec` and `max_separation_arcsec` to filter outliers
4. **Multiple Catalogs**: Use `multi_catalog_match()` when matching against multiple catalogs
5. **Flux Scaling**: Account for frequency differences when comparing fluxes (use `scale_flux_to_frequency()`)

## Troubleshooting

### No Matches Found

- Check that catalog databases exist for your declination strip
- Verify matching radius is appropriate (try increasing `radius_arcsec`)
- Check that source positions are in correct coordinate system (ICRS)

### Poor Match Quality

- Verify astrometry is correct
- Check for systematic offsets (use `calculate_positional_offsets()`)
- Consider using larger matching radius for initial matching

### Database Errors

- Ensure products database exists and is writable
- Check that schema evolution has been run
- Verify foreign key relationships (source_id must exist in `variability_stats`)

## Related Documentation

- `docs/reference/CATALOG_CROSS_MATCHING_GUIDE.md` - Cross-matching strategies
- `docs/reference/CATALOG_USAGE_GUIDE.md` - General catalog usage
- `docs/reference/EXISTING_CROSS_MATCHING_TOOLS.md` - Current tools overview
- `docs/dev/CROSS_MATCHING_IMPLEMENTATION.md` - Implementation details

