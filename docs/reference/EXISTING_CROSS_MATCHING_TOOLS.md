# Existing Cross-Matching Tools in DSA-110 Pipeline

## Date: 2025-11-10

## Overview

This document catalogs the existing cross-matching functionality in the DSA-110 pipeline. Cross-matching tools exist but are embedded within specific validation and catalog-building functions rather than as standalone utilities.

## Existing Cross-Matching Functionality

### 1. Catalog Validation Module (`qa/catalog_validation.py`)

**Location:** `src/dsa110_contimg/qa/catalog_validation.py`

**Functions with Cross-Matching:**

#### `validate_astrometry()`
- **Purpose:** Validate image astrometry by matching detected sources to reference catalog
- **Matching Method:** Uses `astropy.coordinates.match_coordinates_sky()`
- **Matching Radius:** Configurable (default: 10 arcsec)
- **Returns:** `CatalogValidationResult` with astrometry metrics

**Code:**
```python
from astropy.coordinates import SkyCoord, match_coordinates_sky

# Create coordinate objects
detected_coords = SkyCoord(detected_sources["ra_deg"], detected_sources["dec_deg"], unit='deg')
catalog_coords = SkyCoord(catalog_sources["ra_deg"], catalog_sources["dec_deg"], unit='deg')

# Match sources
idx, sep2d, _ = match_coordinates_sky(detected_coords, catalog_coords)

# Filter matches within search radius
sep_arcsec = sep2d.to(u.arcsec).value
match_mask = sep_arcsec < search_radius_arcsec
```

**Usage:**
```python
from dsa110_contimg.qa.catalog_validation import validate_astrometry

result = validate_astrometry(
    image_path="image.fits",
    catalog="nvss",
    search_radius_arcsec=10.0,
    min_snr=5.0,
    max_offset_arcsec=5.0
)
```

#### `validate_flux_scale()`
- **Purpose:** Validate flux scale by matching detected sources to catalog and comparing fluxes
- **Matching Method:** Uses `astropy.coordinates.match_coordinates_sky()`
- **Matching Radius:** Configurable (default: 10 arcsec)
- **Additional:** Performs forced photometry at catalog positions
- **Returns:** `CatalogValidationResult` with flux scale metrics

**Usage:**
```python
from dsa110_contimg.qa.catalog_validation import validate_flux_scale

result = validate_flux_scale(
    image_path="image.fits",
    catalog="nvss",
    search_radius_arcsec=10.0,
    min_snr=5.0,
    flux_range_jy=(0.01, 10.0),
    max_flux_ratio_error=0.2
)
```

#### `validate_source_counts()`
- **Purpose:** Validate source counts completeness by matching detected sources to catalog
- **Matching Method:** Uses `astropy.coordinates.match_coordinates_sky()`
- **Matching Radius:** Configurable (default: 10 arcsec)
- **Returns:** `CatalogValidationResult` with completeness metrics

**Usage:**
```python
from dsa110_contimg.qa.catalog_validation import validate_source_counts

result = validate_source_counts(
    image_path="image.fits",
    catalog="nvss",
    min_snr=5.0,
    completeness_threshold=0.95,
    search_radius_arcsec=10.0
)
```

### 2. Master Catalog Builder (`catalog/build_master.py`)

**Location:** `src/dsa110_contimg/catalog/build_master.py`

**Function:** `_crossmatch()`

- **Purpose:** Cross-match NVSS with VLASS and FIRST to build master reference catalog
- **Matching Method:** Uses `astropy.coordinates.SkyCoord.search_around_sky()`
- **Matching Radius:** Configurable (default: 7.5 arcsec)
- **Output:** Master catalog SQLite database with cross-matched sources

**Code:**
```python
from astropy.coordinates import SkyCoord

# Build SkyCoord objects
nvss_sc = SkyCoord(nvss_ra, nvss_dec, unit='deg')
vlass_sc = SkyCoord(vlass_ra, vlass_dec, unit='deg')
first_sc = SkyCoord(first_ra, first_dec, unit='deg')

# Match using search_around_sky
radius = match_radius_arcsec * u.arcsec
idx_nv, idx_v, sep2d, _ = nvss_sc.search_around_sky(vlass_sc, radius)
idx_nv, idx_f, sep2d, _ = nvss_sc.search_around_sky(first_sc, radius)
```

**Usage:**
```python
# Called internally by build_master CLI
python -m dsa110_contimg.catalog.build_master \
    --nvss nvss.csv \
    --vlass vlass.csv \
    --first first.csv \
    --match-radius-arcsec 7.5
```

### 3. Mosaic Validation (`mosaic/validation.py`)

**Location:** `src/dsa110_contimg/mosaic/validation.py`

**Function:** Tile validation with catalog matching

- **Purpose:** Validate mosaic tiles by matching catalog sources with image peaks
- **Matching Method:** Uses `astropy.coordinates` for matching
- **Usage:** Internal to mosaic validation workflow

## Current Limitations

### No Standalone Cross-Matching Utility

**Issue:** Cross-matching functionality is embedded within specific functions:
- Validation functions (`validate_astrometry`, `validate_flux_scale`, `validate_source_counts`)
- Master catalog builder (`_crossmatch`)
- Mosaic validation

**Impact:**
- Cannot easily reuse cross-matching logic for other purposes
- Each function implements its own matching logic
- No consistent API for cross-matching operations

### Missing Features

1. **General-Purpose Cross-Matching:**
   - No standalone function to match arbitrary source lists
   - No utility for matching DSA-110 sources with external catalogs
   - No multi-catalog matching utility

2. **Advanced Matching:**
   - No handling of multiple matches (nearest neighbor selection)
   - No quality assessment/scoring
   - No extended source handling (adaptive radii)

3. **Spectral Index Handling:**
   - No automatic spectral index correction for RACS comparisons
   - Flux comparisons assume same frequency

## Recommendations

### Create Standalone Cross-Matching Utility

**Proposed:** Create `src/dsa110_contimg/catalog/crossmatch.py` with:

```python
def cross_match_sources(
    detected_ra, detected_dec,
    catalog_ra, catalog_dec,
    match_radius_arcsec=2.0,
    catalog_flux=None,
    detected_flux=None
) -> CrossMatchResult:
    """General-purpose cross-matching utility.
    
    Returns:
        CrossMatchResult with matches, separations, quality flags
    """
    # Implementation using astropy.coordinates.match_coordinates_sky
    pass

def multi_catalog_match(
    detected_ra, detected_dec,
    catalogs_dict  # {'nvss': (ra, dec, flux), 'first': (ra, dec, flux), ...}
) -> MultiCatalogMatchResult:
    """Match sources against multiple catalogs simultaneously.
    
    Returns:
        Best match for each source across all catalogs
    """
    pass
```

### Enhance Existing Functions

1. **Add Spectral Index Correction:**
   - Update `validate_flux_scale()` to handle RACS frequency differences
   - Apply spectral index corrections automatically

2. **Add Quality Assessment:**
   - Assess match quality (excellent/good/fair/poor)
   - Flag matches with quality issues

3. **Add Extended Source Handling:**
   - Adaptive matching radius based on source size
   - Handle extended sources appropriately

## Current Usage in Pipeline

### Validation Stage

```python
# In ValidationStage.run()
from dsa110_contimg.qa.catalog_validation import validate_astrometry, validate_flux_scale

astrometry_result = validate_astrometry(
    image_path=fits_image,
    catalog=catalog,
    search_radius_arcsec=10.0
)

flux_scale_result = validate_flux_scale(
    image_path=fits_image,
    catalog=catalog,
    search_radius_arcsec=10.0
)
```

### Imaging Stage

```python
# In ImagingStage._run_catalog_validation()
from dsa110_contimg.qa.catalog_validation import validate_flux_scale

result = validate_flux_scale(
    image_path=fits_image,
    catalog=catalog,
    min_snr=5.0,
    flux_range_jy=(0.01, 10.0),
    max_flux_ratio_error=0.2
)
```

## Summary

**Existing Cross-Matching:**
- ✅ Embedded in validation functions (`catalog_validation.py`)
- ✅ Embedded in master catalog builder (`build_master.py`)
- ✅ Uses `astropy.coordinates.match_coordinates_sky()` and `search_around_sky()`

**Missing:**
- ❌ Standalone general-purpose cross-matching utility
- ❌ Multi-catalog matching utility
- ❌ Quality assessment/scoring
- ❌ Spectral index correction for RACS
- ❌ Extended source handling

**Recommendation:** Create a standalone `catalog/crossmatch.py` module with general-purpose cross-matching utilities that can be reused across the pipeline.

## Related Documentation

- `docs/reference/CATALOG_CROSS_MATCHING_GUIDE.md` - Cross-matching strategies and algorithms
- `docs/reference/CATALOG_USAGE_GUIDE.md` - General catalog usage guide
- `src/dsa110_contimg/qa/catalog_validation.py` - Validation functions with matching
- `src/dsa110_contimg/catalog/build_master.py` - Master catalog builder with cross-matching

