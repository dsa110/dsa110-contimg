# External Cross-Matching Tools Survey

## Date: 2025-11-10

## Overview

This document catalogs catalog cross-matching tools found in external codebases, reference repositories, and software suites that may be relevant to the DSA-110 pipeline. These tools were discovered through a thorough search of `/data/dsa110-contimg/archive/references/` and `~/proj/`.

## Summary

**Total Cross-Matching Implementations Found:** 5 major implementations

1. **VAST Post-Processing** (`vast-post-processing/crossmatch.py`) - Dedicated cross-matching module
2. **VAST Tools** (`vast-tools`) - Cross-matching via `match_to_catalog_sky` in examples
3. **ASKAP Continuum Validation** (`ASKAP-continuum-validation/catalogue.py`) - Catalog class with `cross_match()` method
4. **VAST Fast Detection** (`vast-fastdetection`) - Cross-matching for candidate prioritization
5. **VAST Pipeline** (`vast-pipeline`) - Association and cross-matching utilities

---

## 1. VAST Post-Processing: `crossmatch.py`

**Location:** `/data/dsa110-contimg/archive/references/VAST/vast-post-processing/vast_post_processing/crossmatch.py`

**Type:** Dedicated cross-matching module

### Key Functions

#### `join_match_coordinates_sky(coords1, coords2, seplimit)`
- **Purpose:** Helper function for cross-matching using `astropy.coordinates.match_coordinates_sky()`
- **Input:** Two `SkyCoord` objects and separation limit
- **Output:** Indices, matched indices, separations, 3D distances
- **Features:**
  - Filters matches within separation limit
  - Returns mask of valid matches

#### `crossmatch_qtables(catalog, catalog_reference, image_path, radius)`
- **Purpose:** Main cross-matching function for QTable catalogs
- **Input:** Two `Catalog` objects (QTable-based), image path, matching radius
- **Output:** QTable with cross-matched sources
- **Features:**
  - Uses `astropy.table.join()` with `join_skycoord()` function
  - Computes separations (`dra`, `ddec`)
  - Calculates distance to field center
  - Computes flux ratio (`flux_peak_ratio`)
  - Handles coordinate frame transformations (FK5)
  - Removes trailing underscores from column names
  - Logs statistics (number of matches, unique reference sources)

**Code Pattern:**
```python
from astropy.coordinates import SkyCoord, Angle, match_coordinates_sky
from astropy.table import QTable, join, join_skycoord

xmatch = join(
    catalog.table,
    catalog_reference.table,
    keys="coord",
    table_names=["", "reference"],
    join_funcs={
        "coord": join_skycoord(radius, distance_func=join_match_coordinates_sky)
    }
)
xmatch["separation"] = xmatch["coord"].separation(xmatch["coord_reference"])
xmatch["dra"], xmatch["ddec"] = xmatch["coord"].spherical_offsets_to(
    xmatch["coord_reference"]
)
```

#### `calculate_positional_offsets(xmatch_qt)`
- **Purpose:** Calculate median positional offsets and MAD
- **Input:** Cross-matched QTable
- **Output:** Median RA/Dec offsets, MAD of RA/Dec offsets
- **Features:**
  - Uses `np.median()` and `mad_std()` from `astropy.stats`

#### `calculate_flux_offsets_Huber(xmatch_qt)`
- **Purpose:** Fit flux relationship using HuberRegressor (robust to outliers)
- **Input:** Cross-matched QTable with flux columns
- **Output:** Flux correction factor (gradient), gradient error
- **Features:**
  - Uses `statsmodels.api.RLM` with `HuberT` norm
  - Robust against outliers and heteroscedasticity
  - Fixed intercept at zero

### Integration Points

- Used in `corrections.py` for astrometry and flux scale corrections
- Works with `Catalog` class from `catalogs.py`
- Supports QTable-based catalogs with `SkyCoord` columns

### Strengths

- ✅ Dedicated, reusable cross-matching module
- ✅ Handles coordinate frame transformations
- ✅ Computes comprehensive metrics (separations, offsets, flux ratios)
- ✅ Robust flux fitting with HuberRegressor
- ✅ Well-documented with type hints

### Potential Adoption

**High Priority** - This is the most complete standalone cross-matching implementation found. Could serve as a template for DSA-110's cross-matching utility.

---

## 2. VAST Tools: Cross-Matching Examples

**Location:** `/data/dsa110-contimg/archive/references/VAST/vast-tools/`

**Type:** Cross-matching via `match_to_catalog_sky` in examples and source class

### Key Files

#### `notebook-examples-py/catalogue-crossmatching-example.py`
- **Purpose:** Example notebook demonstrating cross-matching workflow
- **Features:**
  - Cross-matches external catalogs (e.g., ATNF Pulsar Catalog) with VAST Pipeline sources
  - Uses `SkyCoord.match_to_catalog_sky()` for matching
  - Demonstrates filtering and merging results
  - Shows integration with VAST Pipeline `Pipeline` class

**Code Pattern:**
```python
from astropy.coordinates import SkyCoord
from astropy import units as u

# Create SkyCoord objects
psrcat_skycoord = SkyCoord(ra, dec, unit=u.deg)
vast_sources_skycoord = pipe_run.sources_skycoord

# Perform cross-match
idx, d2d, d3d = psrcat_skycoord.match_to_catalog_sky(vast_sources_skycoord)
radius_limit = 15 * u.arcsec
matches = d2d <= radius_limit

# Merge results
psrcat_crossmatch_result = psrcat_vast_sources_pd.loc[matches].copy()
psrcat_crossmatch_result['vast_xmatch_id'] = pipe_run.sources.iloc[idx[matches]].index.values
psrcat_crossmatch_result['vast_xmatch_d2d_asec'] = d2d[matches].arcsec
```

#### `vasttools/source.py`
- **Purpose:** Source class with `crossmatch_radius` attribute
- **Features:**
  - Stores cross-match radius used to find measurements
  - Used internally for source creation

#### `vasttools/query.py`
- **Purpose:** Query class with `crossmatch_radius` parameter
- **Features:**
  - Configurable cross-match radius (default: 5.0 arcsec)
  - Used for finding sources around coordinates

### Strengths

- ✅ Clear examples and documentation
- ✅ Integration with VAST Pipeline
- ✅ Demonstrates filtering and merging workflows

### Potential Adoption

**Medium Priority** - Good reference for cross-matching workflows, but less complete than `vast-post-processing/crossmatch.py`.

---

## 3. ASKAP Continuum Validation: Catalog Class

**Location:** `/data/dsa110-contimg/archive/references/ASKAP-continuum-validation/catalogue.py`

**Type:** Object-oriented catalog class with `cross_match()` method

### Key Function

#### `cross_match(cat, radius='largest', join_type='1', redo=False, write=True)`
- **Purpose:** Perform nearest-neighbor cross-match between two catalog objects
- **Input:** Another catalog object, matching radius, join type
- **Output:** Updates catalog object with matched sources
- **Features:**
  - Supports configurable radius (can use 'largest' to use larger of two default radii)
  - Join types: '1' (keep all rows from this instance) or '1and2' (keep only matched rows)
  - Caching: Skips re-matching if cross-matched file exists (unless `redo=True`)
  - File I/O: Writes cross-matched catalog to CSV file
  - Prevents duplicate cross-matching (checks `cat_list`)
  - Handles empty catalogs gracefully

**Code Pattern:**
```python
class Catalogue:
    def cross_match(self, cat, radius='largest', join_type='1', redo=False, write=True):
        # Check if already cross-matched
        if cat.name in self.cat_list:
            warnings.warn("Already cross-matched")
            return
        
        # Check for existing file
        filename = '{0}_{1}.csv'.format(self.basename, cat.name)
        if redo or not os.path.exists(filename):
            # Perform cross-match
            # Uses SkyCoord for matching
            # Updates self.df with matched sources
            # Writes to file if write=True
```

### Integration Points

- Part of ASKAP continuum validation workflow
- Used with `report.py` for generating cross-match tables in HTML reports
- Works with `radio_image.py` for image validation

### Strengths

- ✅ Object-oriented design
- ✅ Caching mechanism (avoids re-matching)
- ✅ File I/O integration
- ✅ Flexible join types

### Limitations

- ❌ Less detailed than VAST Post-Processing implementation
- ❌ No flux comparison or offset calculations
- ❌ Limited documentation

### Potential Adoption

**Low-Medium Priority** - Good reference for object-oriented design and caching, but less feature-complete than VAST Post-Processing.

---

## 4. VAST Fast Detection: Candidate Cross-Matching

**Location:** `/data/dsa110-contimg/archive/references/VAST/vast-fastdetection/src/vaster/summarise_candidates.py`

**Type:** Cross-matching for transient candidate prioritization

### Key Function

#### `crossmatch_onebeam(args, cands, beamid, catname, catsrc, base_url, dyspec_url)`
- **Purpose:** Cross-match transient candidates with known sources (e.g., pulsars) for prioritization
- **Input:** Candidate sources, catalog sources, cross-match radius
- **Output:** Updated candidates table with cross-match information
- **Features:**
  - Uses `SkyCoord.separation()` for matching
  - Adds columns: `KNOWN_name`, `KNOWN_sep` (separation in arcsec)
  - Used for candidate prioritization (high/mid/low priority)
  - Integrates with email reporting and visualization

**Code Pattern:**
```python
from astropy.coordinates import SkyCoord
from astropy import units as u

# Create SkyCoord for candidate
candsrc = SkyCoord(cand['ra'], cand['dec'], unit=u.degree)

# Match against catalog sources
ind = candsrc.separation(sel_catsrc) < args.crossmatch_radius * u.arcsec

if sum(ind) == 0:
    match = ''
    sep = ''
else:
    match = sel_catname[ind][0]
    sep = candsrc.separation(sel_catsrc)[ind].arcsec[0]
```

### Integration Points

- Used in transient detection pipeline
- Integrates with candidate prioritization
- Generates email reports with cross-match information

### Strengths

- ✅ Simple, focused implementation
- ✅ Good for candidate filtering/prioritization
- ✅ Handles multiple matches (takes first)

### Limitations

- ❌ Very specific use case (transient candidates)
- ❌ Limited to single match per candidate
- ❌ No flux comparison

### Potential Adoption

**Low Priority** - Too specific to transient detection workflow, but good reference for simple separation-based matching.

---

## 5. VAST Pipeline: Association Utilities

**Location:** `/data/dsa110-contimg/archive/references/VAST/vast-pipeline/vast_pipeline/pipeline/`

**Type:** Association and cross-matching utilities for pipeline

### Key Files

#### `association.py`
- **Purpose:** Source association across epochs (likely uses cross-matching)
- **Note:** File not fully examined, but likely contains association logic

#### `utils.py`
- **Purpose:** Pipeline utilities (may contain cross-matching helpers)
- **Note:** File not fully examined

### Potential Adoption

**Low Priority** - Likely too integrated with VAST Pipeline architecture to be directly adoptable.

---

## Comparison Matrix

| Implementation | Standalone | Reusable | Features | Documentation | Adoption Priority |
|----------------|------------|----------|----------|--------------|-------------------|
| VAST Post-Processing `crossmatch.py` | ✅ Yes | ✅ Yes | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | **HIGH** |
| VAST Tools Examples | ⚠️ Partial | ⚠️ Partial | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | **MEDIUM** |
| ASKAP Catalog Class | ✅ Yes | ✅ Yes | ⭐⭐⭐ | ⭐⭐ | **LOW-MEDIUM** |
| VAST Fast Detection | ❌ No | ❌ No | ⭐⭐ | ⭐⭐ | **LOW** |
| VAST Pipeline Utils | ❌ No | ❌ No | ⭐⭐ | ⭐⭐ | **LOW** |

**Legend:**
- ⭐⭐⭐⭐⭐ = Excellent
- ⭐⭐⭐⭐ = Very Good
- ⭐⭐⭐ = Good
- ⭐⭐ = Fair
- ⭐ = Poor

---

## Recommendations for DSA-110

### Primary Recommendation: Adopt VAST Post-Processing Pattern

**File:** `vast-post-processing/vast_post_processing/crossmatch.py`

**Rationale:**
1. **Most Complete:** Dedicated module with comprehensive functionality
2. **Reusable:** Standalone functions that can be adapted
3. **Well-Designed:** Uses QTable and SkyCoord effectively
4. **Feature-Rich:** Includes positional offsets, flux comparisons, robust fitting
5. **Documented:** Good docstrings and type hints

### Implementation Strategy

1. **Create:** `src/dsa110_contimg/catalog/crossmatch.py`
2. **Adapt Functions:**
   - `cross_match_sources()` - General-purpose cross-matching (based on `crossmatch_qtables`)
   - `calculate_positional_offsets()` - Offset calculations (directly adoptable)
   - `calculate_flux_scale()` - Flux comparison (adapt `calculate_flux_offsets_Huber`)
3. **Integration:**
   - Replace embedded matching in `catalog_validation.py`
   - Use in `build_master.py` for multi-catalog matching
   - Add to API endpoints for cross-matching queries

### Secondary Reference: VAST Tools Examples

**File:** `vast-tools/notebook-examples-py/catalogue-crossmatching-example.py`

**Use For:**
- Workflow examples
- Integration patterns with pipeline data
- Filtering and merging strategies

### Additional Considerations

1. **ASKAP Catalog Class:** Reference for object-oriented design and caching
2. **VAST Fast Detection:** Reference for simple separation-based matching

---

## Code Patterns to Adopt

### Pattern 1: QTable-Based Cross-Matching (VAST Post-Processing)

```python
from astropy.table import QTable, join, join_skycoord
from astropy.coordinates import SkyCoord, Angle

def cross_match_sources(
    catalog1: QTable,
    catalog2: QTable,
    radius: Angle = Angle("10 arcsec")
) -> QTable:
    """Cross-match two catalogs using QTable join."""
    xmatch = join(
        catalog1,
        catalog2,
        keys="coord",
        table_names=["", "reference"],
        join_funcs={
            "coord": join_skycoord(radius, distance_func=join_match_coordinates_sky)
        }
    )
    xmatch["separation"] = xmatch["coord"].separation(xmatch["coord_reference"])
    xmatch["dra"], xmatch["ddec"] = xmatch["coord"].spherical_offsets_to(
        xmatch["coord_reference"]
    )
    return xmatch
```

### Pattern 2: Simple SkyCoord Matching (VAST Tools)

```python
from astropy.coordinates import SkyCoord
from astropy import units as u

def simple_cross_match(ra1, dec1, ra2, dec2, radius_arcsec=10.0):
    """Simple cross-match using match_to_catalog_sky."""
    coords1 = SkyCoord(ra1, dec1, unit=u.deg)
    coords2 = SkyCoord(ra2, dec2, unit=u.deg)
    
    idx, d2d, d3d = coords1.match_to_catalog_sky(coords2)
    matches = d2d <= radius_arcsec * u.arcsec
    
    return idx[matches], d2d[matches], matches
```

### Pattern 3: Separation-Based Matching (VAST Fast Detection)

```python
from astropy.coordinates import SkyCoord
from astropy import units as u

def separation_match(cand_coords, catalog_coords, radius_arcsec=10.0):
    """Match using separation calculation."""
    separations = cand_coords.separation(catalog_coords)
    matches = separations < radius_arcsec * u.arcsec
    return matches, separations[matches]
```

---

## Next Steps

1. **Examine VAST Post-Processing `crossmatch.py` in detail**
2. **Create DSA-110 cross-matching utility module**
3. **Adapt functions from VAST Post-Processing**
4. **Integrate with existing validation and catalog-building code**
5. **Add unit tests based on VAST examples**

---

## Related Documentation

- `docs/reference/EXISTING_CROSS_MATCHING_TOOLS.md` - Current DSA-110 cross-matching tools
- `docs/reference/CATALOG_CROSS_MATCHING_GUIDE.md` - Cross-matching strategies and algorithms
- `docs/reference/CATALOG_USAGE_GUIDE.md` - General catalog usage guide

