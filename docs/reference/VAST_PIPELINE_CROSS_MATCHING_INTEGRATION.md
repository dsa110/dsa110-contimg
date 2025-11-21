# VAST Pipeline Cross-Matching Integration Guide

## Date: 2025-11-10

## Overview

This document details how the VAST pipeline integrates cross-matching
functionality into its workflow, providing guidance for pipeline-specific
implementation in DSA-110. The VAST pipeline demonstrates several key
integration patterns:

1. **Source Association** - Cross-matching for associating measurements across
   epochs
2. **Corrections Workflow** - Cross-matching for astrometry and flux scale
   corrections
3. **Database Models** - Storing cross-match results in database
4. **Duplicate Detection** - Using cross-matching to identify duplicate sources

---

## 1. Source Association Integration

**Location:** `vast-pipeline/vast_pipeline/pipeline/association.py`

### Purpose

Cross-matching is used to associate source detections across multiple
epochs/images into unique sources. This is the core of VAST's variability
analysis.

### Key Functions

#### `basic_association()`

- **Purpose:** Basic source association using nearest-neighbor matching
- **Method:** `SkyCoord.match_to_catalog_sky()`
- **Features:**
  - Matches new sources (`skyc2`) to existing sources (`skyc1`)
  - Uses configurable association radius (`limit`)
  - Handles one-to-many associations (multiple detections → one source)
  - Assigns source IDs to matched detections
  - Creates new source IDs for unmatched detections

**Code Pattern:**

```python
from astropy.coordinates import SkyCoord, Angle
from astropy import units as u

def basic_association(
    sources_df: pd.DataFrame,
    skyc1_srcs: pd.DataFrame,  # Existing sources
    skyc1: SkyCoord,            # Existing source coordinates
    skyc2_srcs: pd.DataFrame,   # New detections
    skyc2: SkyCoord,            # New detection coordinates
    limit: Angle,               # Association radius
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Match new sources to existing sources
    idx, d2d, d3d = skyc2.match_to_catalog_sky(skyc1)

    # Filter matches within association radius
    sel = d2d <= limit

    # Assign source IDs to matched detections
    skyc2_srcs.loc[sel, 'source'] = skyc1_srcs.loc[idx[sel], 'source'].values
    skyc2_srcs.loc[sel, 'd2d'] = d2d[sel].arcsec

    # Handle one-to-many associations
    skyc2_srcs, sources_df = one_to_many_basic(skyc2_srcs, sources_df)

    # Create new source IDs for unmatched detections
    nan_sel = (skyc2_srcs['source'] == -1).values
    skyc2_srcs.loc[nan_sel, 'source'] = np.arange(
        sources_df['source'].values.max() + 1,
        sources_df['source'].values.max() + 1 + nan_sel.sum()
    )

    return sources_df, skyc1_srcs
```

#### `advanced_association()`

- **Purpose:** Advanced association using de Ruiter radius
- **Method:** `SkyCoord.search_around_sky()` (finds all matches, not just
  nearest)
- **Features:**
  - Uses beamwidth limit for initial filtering
  - Calculates de Ruiter radius (statistical association metric)
  - Handles many-to-many associations
  - More sophisticated than basic association

**Code Pattern:**

```python
def advanced_association(
    method: str,
    sources_df: pd.DataFrame,
    skyc1_srcs: pd.DataFrame,
    skyc1: SkyCoord,
    skyc2_srcs: pd.DataFrame,
    skyc2: SkyCoord,
    dr_limit: float,      # de Ruiter radius limit
    bw_max: float,        # Beamwidth limit
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    # Find all matches within beamwidth limit
    idx_skyc1, idx_skyc2, d2d, d3d = skyc2.search_around_sky(skyc1, bw_max)

    # Merge candidate matches
    temp_srcs = merge_candidates(idx_skyc1, idx_skyc2, skyc1_srcs, skyc2_srcs)

    # Apply beamwidth limit
    temp_srcs = temp_srcs[d2d <= bw_max].copy()

    # Calculate and apply de Ruiter radius cut
    if method == 'deruiter':
        temp_srcs['dr'] = calc_de_ruiter(temp_srcs)
        temp_srcs = temp_srcs[temp_srcs['dr'] <= dr_limit]

    # Handle many-to-many associations
    temp_srcs = many_to_many_advanced(temp_srcs, method)

    return sources_df, skyc1_srcs
```

### Integration Points

- **Pipeline Config:** Association parameters in `PipelineConfig`:

  ```python
  "source_association": {
      "method": "basic" | "advanced" | "deruiter",
      "radius": float,              # Association radius (arcsec)
      "deruiter_radius": float,     # de Ruiter radius limit
      "deruiter_beamwidth_limit": float,
      "parallel": bool,
      "epoch_duplicate_radius": float,
  }
  ```

- **Pipeline Main:** Called from `pipeline/main.py`:

  ```python
  from vast_pipeline.pipeline.association import association

  # After loading measurements
  sources_df = association(
      images_df=images_df,
      limit=config.source_association.radius,
      method=config.source_association.method,
      ...
  )
  ```

### Key Design Patterns

1. **Incremental Association:** Sources are associated incrementally as new
   images are processed
2. **Source ID Management:** Unmatched detections get new source IDs
3. **Relationship Tracking:** One-to-many and many-to-many relationships are
   tracked
4. **Distance Metrics:** Both angular separation (`d2d`) and de Ruiter radius
   (`dr`) are stored

---

## 2. Corrections Workflow Integration

**Location:** `vast-post-processing/vast_post_processing/corrections.py`

### Purpose

Cross-matching is used to compare detected sources with reference catalogs to
calculate astrometry and flux scale corrections.

### Key Function

#### `vast_xmatch_qc()`

- **Purpose:** Cross-match detected sources with reference catalog for quality
  control
- **Integration:** Uses `crossmatch_qtables()` from `crossmatch.py`
- **Workflow:**
  1. Create `Catalog` objects for detected and reference catalogs
  2. Perform cross-match using `crossmatch_qtables()`
  3. Filter matches (flux errors, crop size, sigma clipping)
  4. Calculate positional offsets
  5. Calculate flux scale corrections
  6. Write outputs (CSV, cross-match table)

**Code Pattern:**

```python
from vast_post_processing.catalogs import Catalog
from vast_post_processing.crossmatch import (
    crossmatch_qtables,
    calculate_positional_offsets,
    calculate_flux_offsets_Huber
)

def vast_xmatch_qc(
    image_path: Path,
    reference_catalog_path: str,
    catalog_path: str,
    radius: Angle = Angle("10arcsec"),
    flux_limit: float = 0,
    snr_limit: float = 20,
    crop_size: float = 6.67,
    crossmatch_output: Optional[str] = None,
) -> Tuple[float, float, AffineScalarFunc, AffineScalarFunc]:
    # Create Catalog objects
    reference_catalog = Catalog(
        reference_catalog_path,
        input_format="selavy",
        flux_limit=flux_limit,
        snr_limit=snr_limit,
        ...
    )
    catalog = Catalog(
        catalog_path,
        input_format="selavy",
        flux_limit=flux_limit,
        snr_limit=snr_limit,
        ...
    )

    # Perform cross-match
    xmatch_qt = crossmatch_qtables(
        catalog,
        reference_catalog,
        image_path,
        radius=radius
    )

    # Filter matches
    mask = xmatch_qt["flux_peak_err"] > 0
    mask &= xmatch_qt["flux_peak_err_reference"] > 0
    mask &= abs(xmatch_qt["fc_ddec"].to(u.deg)) < (crop_size/2)
    mask &= abs(xmatch_qt["fc_dra"].to(u.deg)) < (crop_size/2)

    # Sigma clipping for outliers
    sigma_clip_mask = sigma_clip(
        data=np.asarray(xmatch_qt["flux_peak_ratio"]),
        sigma=flux_ratio_sigma_clip,
        maxiters=None,
    ).mask
    mask &= ~(sigma_clip_mask)

    data = xmatch_qt[mask]

    # Calculate offsets
    dra_median, ddec_median, dra_madfm, ddec_madfm = calculate_positional_offsets(data)
    gradient, offset, gradient_err, offset_err = calculate_flux_offsets_Huber(data)

    # Write outputs
    if crossmatch_output is not None:
        data.write(crossmatch_output, overwrite=True)

    return dra_median, ddec_median, flux_corr_mult, flux_corr_add
```

### Integration Points

- **CLI Integration:** Called from `cli/run_corrections.py`:

  ```python
  # For each epoch
  dra_median, ddec_median, flux_corr_mult, flux_corr_add = vast_xmatch_qc(
      image_path=image_path,
      reference_catalog_path=reference_catalog,
      catalog_path=detected_catalog,
      radius=Angle(f"{args.radius}arcsec"),
      crossmatch_output=crossmatch_file,
      ...
  )
  ```

- **Epoch Processing:** Applied per epoch/field:

  ```python
  # Process each epoch
  for epoch_dir in epoch_dirs:
      epoch_corr_dir = epoch_dir / "corrections"
      crossmatch_file = epoch_corr_dir / f"{field}_crossmatch.csv"

      corrections = vast_xmatch_qc(
          image_path=image_path,
          reference_catalog_path=reference_catalog,
          catalog_path=detected_catalog,
          crossmatch_output=crossmatch_file,
          ...
      )
  ```

### Key Design Patterns

1. **Catalog Abstraction:** Uses `Catalog` class to handle different input
   formats
2. **Filtering Pipeline:** Multiple filtering steps (flux errors, crop size,
   sigma clipping)
3. **Robust Statistics:** Uses MAD and Huber regression for robust offset
   calculations
4. **Output Management:** Writes cross-match tables and correction CSV files

---

## 3. Database Model Integration

**Location:** `vast-pipeline/vast_pipeline/models.py` and
`migrations/0001_initial.py`

### Purpose

Cross-match results are stored in the database for tracking and querying.

### Database Schema

#### `CrossMatch` Model

```python
class CrossMatch(models.Model):
    """Cross-match between Source and SurveySource."""
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    survey_source = models.ForeignKey(SurveySource, on_delete=models.CASCADE)
    manual = models.BooleanField()          # Manual vs automatic match
    distance = models.FloatField()          # Separation (arcsec)
    probability = models.FloatField()       # Match probability
    comment = models.TextField(blank=True, default='', max_length=1000)
```

#### `Source` Model Relationship

```python
class Source(models.Model):
    # ...
    cross_match_sources = models.ManyToManyField(
        through='CrossMatch',
        to='SurveySource'
    )
```

### Integration Points

- **Migration:** Database schema defined in migrations
- **Loading:** Cross-matches loaded via `loading.py`:

  ```python
  from vast_pipeline.pipeline.loading import make_upload_crossmatches

  # After association
  crossmatch_models = make_upload_crossmatches(
      crossmatch_df=crossmatch_df,
      pipeline_run=pipeline_run
  )
  ```

### Key Design Patterns

1. **Many-to-Many Relationship:** Sources can match multiple survey sources
2. **Through Model:** `CrossMatch` model stores match metadata
3. **Manual Override:** Supports manual cross-match editing
4. **Probability Scoring:** Stores match confidence/probability

---

## 4. Duplicate Detection Integration

**Location:** `vast-pipeline/vast_pipeline/pipeline/utils.py`

### Purpose

Cross-matching is used to identify and remove duplicate source detections within
the same epoch/image.

### Key Function

#### `remove_duplicate_measurements()`

- **Purpose:** Remove duplicate sources within an epoch
- **Method:** `SkyCoord.search_around_sky()` for self-matching
- **Features:**
  - Finds sources within duplicate radius
  - Keeps source closest to image center
  - Removes duplicates from different images (not same image)

**Code Pattern:**

```python
def remove_duplicate_measurements(
    sources_df: pd.DataFrame,
    dup_lim: Optional[Angle] = None,
) -> pd.DataFrame:
    if dup_lim is None:
        dup_lim = Angle(2.5 * u.arcsec)  # Default: ASKAP pixel size

    # Sort by distance from image center (keep closest)
    sources_df = sources_df.sort_values(by='dist_from_centre')

    sources_sc = SkyCoord(
        sources_df['ra'],
        sources_df['dec'],
        unit=(u.deg, u.deg)
    )

    # Self-match to find duplicates
    idxc, idxcatalog, *_ = sources_sc.search_around_sky(sources_sc, dup_lim)

    # Create results dataframe
    results = pd.DataFrame({
        'source_id': idxc,
        'match_id': idxcatalog,
        'source_image': sources_df.iloc[idxc]['image'].tolist(),
        'match_image': sources_df.iloc[idxcatalog]['image'].tolist()
    })

    # Drop matches from same image (not duplicates)
    matching_image_mask = (results['source_image'] != results['match_image'])
    results = results.loc[matching_image_mask]

    # Drop duplicate pairs (keep first, drop second)
    to_drop = results.loc[
        results['source_id'] != results['match_id'],
        'match_id'
    ]

    # Remove duplicates
    sources_df = sources_df.drop(sources_df.index[to_drop])

    return sources_df
```

### Integration Points

- **Epoch Processing:** Called during epoch-based association:

  ```python
  # In prep_skysrc_df()
  if epoch_based:
      sources_df = remove_duplicate_measurements(
          sources_df,
          duplicate_limit=duplicate_limit
      )
  ```

- **Config:** Duplicate radius configurable:
  ```python
  "source_association": {
      "epoch_duplicate_radius": float,  # arcsec
  }
  ```

### Key Design Patterns

1. **Self-Matching:** Uses `search_around_sky()` on same catalog
2. **Image-Aware:** Only removes duplicates from different images
3. **Center-Priority:** Keeps source closest to image center
4. **Configurable Radius:** Default based on pixel size

---

## 5. Pipeline Workflow Integration

### Overall Pipeline Flow

```
1. Load Images & Measurements
   ↓
2. Remove Duplicates (within epoch)
   ↓
3. Association (across epochs)
   - basic_association() or advanced_association()
   - Uses cross-matching to group detections into sources
   ↓
4. Calculate Metrics
   - Variability metrics (V, η, Vs, m)
   - Pair-wise metrics
   ↓
5. Finalize & Upload
   - Upload sources, associations, cross-matches to database
   ↓
6. Corrections (Post-Processing)
   - vast_xmatch_qc() for astrometry/flux corrections
   - Cross-match with reference catalogs
```

### Key Integration Points

1. **Config-Driven:** All cross-matching parameters in pipeline config
2. **Modular Design:** Cross-matching functions are reusable modules
3. **Database Integration:** Results stored for querying and analysis
4. **Error Handling:** Robust filtering and outlier rejection
5. **Performance:** Supports parallel processing for large datasets

---

## Recommendations for DSA-110 Pipeline Integration

### 1. Create Cross-Matching Stage

**Proposed:** Add `CrossMatchStage` to pipeline workflow

```python
class CrossMatchStage(PipelineStage):
    """Cross-match detected sources with reference catalogs."""

    def execute(self, context: PipelineContext) -> PipelineContext:
        # Get detected sources from previous stage
        detected_sources = context.outputs.get("detected_sources")

        # Query reference catalog
        catalog_sources = query_sources(
            catalog_type="nvss",
            ra_center=context.observation.ra_deg,
            dec_center=context.observation.dec_deg,
            radius_deg=1.5
        )

        # Perform cross-match
        from dsa110_contimg.catalog.crossmatch import cross_match_sources
        matches = cross_match_sources(
            detected_sources,
            catalog_sources,
            radius=Angle("10arcsec")
        )

        # Calculate offsets
        offsets = calculate_positional_offsets(matches)

        # Store in context
        return context.with_output("cross_matches", matches) \
                      .with_output("astrometry_offsets", offsets)
```

### 2. Integrate with Validation Stage

**Current:** Validation uses embedded cross-matching

**Proposed:** Use standalone cross-matching utility

```python
# In ValidationStage
from dsa110_contimg.catalog.crossmatch import cross_match_sources

# Replace embedded matching with utility call
matches = cross_match_sources(
    detected_sources_df,
    catalog_sources_df,
    radius=Angle(f"{search_radius_arcsec}arcsec")
)
```

### 3. Add to Database Schema

**Proposed:** Add cross-match table to `products.sqlite3`

```sql
CREATE TABLE IF NOT EXISTS cross_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    catalog_type TEXT NOT NULL,
    catalog_source_id TEXT,
    separation_arcsec REAL,
    dra_arcsec REAL,
    ddec_arcsec REAL,
    flux_ratio REAL,
    match_quality TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_id) REFERENCES sources(id)
);
```

### 4. Integration with Source Association

**Proposed:** Use cross-matching for source association (if needed)

```python
# In SourceAssociationStage (if implemented)
from dsa110_contimg.catalog.crossmatch import cross_match_sources

# Associate measurements across epochs
associated_sources = associate_measurements(
    measurements_list,
    association_radius=Angle("5arcsec"),
    method="basic"  # or "advanced"
)
```

---

## Summary

### VAST Pipeline Cross-Matching Integration Patterns

1. **Source Association:** Cross-matching to group detections into sources
2. **Corrections:** Cross-matching for astrometry/flux corrections
3. **Database Storage:** Cross-match results stored in database
4. **Duplicate Detection:** Self-matching to find duplicates
5. **Config-Driven:** All parameters in pipeline configuration
6. **Modular Design:** Reusable cross-matching functions
7. **Robust Filtering:** Multiple filtering steps and outlier rejection

### Key Takeaways for DSA-110

- ✅ Create standalone cross-matching utility module
- ✅ Integrate into pipeline stages (validation, corrections)
- ✅ Store cross-match results in database
- ✅ Use config-driven parameters
- ✅ Support multiple matching methods (basic, advanced)
- ✅ Implement robust filtering and outlier rejection
- ✅ Track match quality and metadata

---

## Related Documentation

- `docs/reference/EXISTING_CROSS_MATCHING_TOOLS.md` - Current DSA-110
  cross-matching tools
- `docs/reference/EXTERNAL_CROSS_MATCHING_TOOLS_SURVEY.md` - External tool
  survey
- `docs/reference/CATALOG_CROSS_MATCHING_GUIDE.md` - Cross-matching strategies
- `docs/reference/CATALOG_USAGE_GUIDE.md` - General catalog usage guide
