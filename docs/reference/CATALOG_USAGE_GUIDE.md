# Radio Catalog Usage Guide for DSA-110 Pipeline

## Date: 2025-11-10

## Overview

This guide provides practical information for using NVSS, FIRST, and RACS
catalogs in the DSA-110 continuum imaging pipeline, including astrometric
accuracy, flux scale considerations, cross-matching strategies, and best
practices.

## Astrometric Accuracy & Positional Uncertainties

### Positional Uncertainties

| Catalog   | Positional Uncertainty | Notes                                                                    |
| --------- | ---------------------- | ------------------------------------------------------------------------ |
| **NVSS**  | ~1-2 arcsec            | Suitable for general cross-matching                                      |
| **FIRST** | ~1 arcsec              | Best astrometric reference; often used as reference for other catalogs   |
| **RACS**  | ~2 arcsec              | Declination-dependent systematic offsets; polynomial corrections applied |

### Cross-Matching Radii

**Recommended matching radii:**

- **FIRST:** 1-2 arcsec (high precision)
- **NVSS:** 1-2 arcsec (moderate precision)
- **RACS:** 2-3 arcsec (after declination correction)

**Best Practice:** Use isolated, unresolved sources for astrometric calibration
to minimize positional errors from extended emission or source confusion.

### RACS Declination Corrections

RACS has systematic positional offsets that vary with declination. The catalog
applies polynomial corrections (4th order for RACS-high) to improve astrometric
accuracy for cross-matching with FIRST and ICRF3.

**For DSA-110:** When cross-matching RACS sources, consider
declination-dependent corrections if high astrometric precision is required.

## Flux Scale & Spectral Index Considerations

### Frequency Differences

| Catalog       | Frequency            | Wavelength |
| ------------- | -------------------- | ---------- |
| **NVSS**      | 1.4 GHz              | 21 cm      |
| **FIRST**     | 1.4 GHz              | 21 cm      |
| **RACS**      | ~0.888 GHz (primary) | ~34 cm     |
| **RACS-mid**  | 1.3675 GHz           | ~22 cm     |
| **RACS-high** | 1.6555 GHz           | ~18 cm     |

### Spectral Index Corrections

**Critical:** RACS operates at different frequencies than NVSS/FIRST, requiring
spectral index corrections for flux comparisons.

**Assumed Spectral Index:** RACS uses α = -0.8 ± 0.1 (where S ∝ ν^α)

**Flux Scale Accuracy:**

- **NVSS/FIRST:** Same frequency (1.4 GHz) - direct flux comparison possible
- **RACS vs NVSS:** ~5% flux offset expected due to frequency separation (0.888
  vs 1.4 GHz)
- **RACS vs SUMSS:** ~0.5% flux offset (similar frequencies)

**For DSA-110 Pipeline:**

- When comparing RACS fluxes with NVSS/FIRST, apply spectral index correction
- Use RACS-mid (1.3675 GHz) for closer frequency match to NVSS/FIRST (1.4 GHz)
- Consider spectral index uncertainty (±0.1) in flux comparisons

### Flux Scale Validation

**Current Pipeline Usage:**

- `validate_flux_scale()` compares DSA-110 fluxes with catalog fluxes
- For RACS, spectral index corrections should be applied before comparison
- Typical flux scale errors: < 20% acceptable for validation

## Catalog Access & Formats

### Download Methods

| Catalog   | Access Method              | Formats                    | Notes                                            |
| --------- | -------------------------- | -------------------------- | ------------------------------------------------ |
| **NVSS**  | FTP download, online forms | TXT (~150 MB), FITS images | Large file download recommended for bulk queries |
| **FIRST** | VO tools, FTP              | FITS, CSV                  | Similar to NVSS access methods                   |
| **RACS**  | CASDA VO API, FTP          | CSV, FITS                  | VO cone search via TOPCAT/Astroquery             |

### DSA-110 Implementation

**Current System:**

- Catalogs converted to SQLite databases (`state/catalogs/`)
- Per-declination strip databases (e.g., `nvss_dec+54.7.sqlite3`)
- Automatic catalog building in `CatalogSetupStage`
- Query interface: `dsa110_contimg.catalog.query.query_sources()`

**Catalog Resolution:**

1. Check SQLite database (per-declination strip)
2. Check environment variable (`NVSS_CATALOG`, `FIRST_CATALOG`, `RAX_CATALOG`)
3. Fall back to CSV (NVSS only - auto-downloads if needed)

### Catalog Formats

**SQLite Database Schema:**

```sql
CREATE TABLE sources (
    source_id INTEGER PRIMARY KEY,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    flux_mjy REAL,
    -- Catalog-specific columns (e.g., maj_arcsec, min_arcsec for FIRST)
    UNIQUE(ra_deg, dec_deg)
);
CREATE INDEX idx_radec ON sources(ra_deg, dec_deg);
```

## Cross-Matching Strategies

### Best Practices

1. **Use Appropriate Matching Radius:**
   - FIRST: 1-2 arcsec
   - NVSS: 1-2 arcsec
   - RACS: 2-3 arcsec (after declination correction)

2. **Prefer Isolated Sources:**
   - Use point sources or isolated extended sources
   - Avoid confused/blended sources for astrometric calibration

3. **Consider Source Type:**
   - Extended sources: Larger matching radius may be needed
   - Compact sources: Smaller matching radius appropriate

4. **Multi-Catalog Cross-Match:**
   - Match against multiple catalogs when available
   - Use FIRST for precise positions, NVSS for completeness
   - Cross-validate matches across catalogs

### Matching Algorithm

**Recommended Approach:**

```python
# 1. Query catalog for sources in field
catalog_sources = query_sources(
    catalog_type="nvss",
    ra_center=ra_deg,
    dec_center=dec_deg,
    radius_deg=0.5
)

# 2. Calculate angular separations
from astropy.coordinates import SkyCoord
catalog_coords = SkyCoord(catalog_sources['ra_deg'], catalog_sources['dec_deg'], unit='deg')
detected_coords = SkyCoord(detected_ra, detected_dec, unit='deg')
separations = detected_coords.separation(catalog_coords)

# 3. Match within radius
match_radius = 2.0 * u.arcsec  # Adjust based on catalog
matches = separations < match_radius
```

## Completeness Limits

### Detection Thresholds

| Catalog   | 5σ Detection | Completeness Limit | Notes                                    |
| --------- | ------------ | ------------------ | ---------------------------------------- |
| **NVSS**  | ~2.5 mJy     | ~3-5 mJy           | 95% complete above ~5 mJy                |
| **FIRST** | ~1 mJy       | ~1-2 mJy           | High completeness at 1 mJy               |
| **RACS**  | ~3-5 mJy     | ~5 mJy             | 95% complete for point sources at ~5 mJy |

**For DSA-110:**

- Use completeness limits when comparing source counts
- Account for completeness when validating detection rates
- Consider flux-dependent completeness for statistical studies

## Multi-Frequency Considerations (RACS)

### RACS Frequency Bands

RACS provides multiple frequency bands:

| Band          | Frequency  | Resolution         | Use Case                         |
| ------------- | ---------- | ------------------ | -------------------------------- |
| **RACS-low**  | 887.5 MHz  | ~25 arcsec         | Wide-area, low-frequency studies |
| **RACS-mid**  | 1.3675 GHz | 8-47 arcsec        | Closest to NVSS/FIRST (1.4 GHz)  |
| **RACS-high** | 1.6555 GHz | ~11.8 × 8.1 arcsec | High-resolution southern sky     |

**Recommendation:** Use **RACS-mid** (1.3675 GHz) for flux comparisons with
NVSS/FIRST due to similar frequency.

## Known Issues & Caveats

### NVSS

- **Low Resolution:** May blend nearby sources
- **Extended Sources:** Better sensitivity than FIRST for extended emission
- **Aging Data:** Observations from 1993-1996

### FIRST

- **Resolves Out Extended Emission:** May miss diffuse/low surface brightness
  sources
- **Patchy Coverage:** Not uniform all-sky (check availability for declination)
- **Source Confusion:** High resolution can separate blends but may miss
  extended structures

### RACS

- **Declination-Dependent Offsets:** Systematic positional offsets require
  correction
- **Frequency Mismatch:** Different frequency than NVSS/FIRST requires spectral
  index correction
- **Newer Catalog:** Less mature than NVSS/FIRST, may have fewer
  cross-identifications

## Performance Considerations

### Query Performance

**SQLite Databases:**

- Fast queries (~milliseconds) with spatial indexing
- Per-declination strip databases reduce query size
- Indexed on (ra_deg, dec_deg) for fast spatial queries

**CSV Fallback:**

- Slower queries (~seconds to minutes for large catalogs)
- Requires loading full catalog into memory
- Use SQLite databases when possible

### Database Size

**Typical Database Sizes (per declination strip, ±6°):**

- **NVSS:** ~50-200 MB (depends on declination)
- **FIRST:** ~20-100 MB (patchy coverage)
- **RACS:** ~50-200 MB (southern sky)

## Integration Best Practices

### Pipeline Usage

1. **Catalog Selection:**
   - Use NVSS as default (widest coverage)
   - Use FIRST for high-resolution needs (when available)
   - Use RACS for southern sky (< -40° declination)

2. **Flux Scale Validation:**
   - Apply spectral index corrections for RACS comparisons
   - Use RACS-mid for NVSS/FIRST comparisons
   - Account for frequency differences in error estimates

3. **Astrometric Validation:**
   - Use FIRST as reference when available (best accuracy)
   - Apply RACS declination corrections if needed
   - Consider source type (extended vs. compact) in matching

4. **Cross-Matching:**
   - Use appropriate matching radius for each catalog
   - Prefer isolated sources for calibration
   - Cross-validate matches across multiple catalogs

### Code Examples

**Query Catalog:**

```python
from dsa110_contimg.catalog.query import query_sources

# Query NVSS sources
nvss_sources = query_sources(
    catalog_type="nvss",
    ra_center=122.0,
    dec_center=54.7,
    radius_deg=0.5,
    min_flux_mjy=5.0  # Above completeness limit
)
```

**Cross-Match with Detections:**

```python
from astropy.coordinates import SkyCoord
import astropy.units as u

# Match detected sources with catalog
catalog_coords = SkyCoord(nvss_sources['ra_deg'], nvss_sources['dec_deg'], unit='deg')
detected_coords = SkyCoord(detected_ra, detected_dec, unit='deg')
separations = detected_coords.separation(catalog_coords)

# Find matches within 2 arcsec
match_radius = 2.0 * u.arcsec
matches = separations < match_radius
matched_catalog = nvss_sources[matches]
```

**Apply Spectral Index Correction (RACS):**

```python
import numpy as np

# RACS flux at 0.888 GHz, convert to 1.4 GHz (NVSS/FIRST)
racs_flux_888 = 10.0  # mJy at 888 MHz
spectral_index = -0.8  # Typical value
flux_1400 = racs_flux_888 * (1400.0 / 888.0) ** spectral_index
# flux_1400 ≈ 7.4 mJy at 1.4 GHz
```

## Recommendations for DSA-110

### Default Strategy

1. **Primary Catalog:** NVSS (widest coverage, good for validation)
2. **High-Resolution:** FIRST (when available, for precise cross-matching)
3. **Southern Sky:** RACS (for declination < -40°)

### Flux Scale Validation

- Use NVSS for flux scale validation (same frequency as DSA-110 ~1.4 GHz)
- For RACS comparisons, use RACS-mid (1.3675 GHz) and apply spectral index
  correction
- Account for completeness limits in validation

### Astrometric Validation

- Use FIRST as reference when available (best positional accuracy)
- Apply appropriate matching radii for each catalog
- Consider source type (extended vs. compact) in matching

### Multi-Catalog Approach

- Query multiple catalogs when available
- Cross-validate matches across catalogs
- Use catalog-specific strengths (FIRST for positions, NVSS for completeness)

## Related Documentation

- `docs/reference/RADIO_SURVEY_CATALOG_COMPARISON.md` - Survey specifications
  comparison
- `docs/reference/FIRST_DECLINATION_COVERAGE.md` - FIRST coverage details
- `src/dsa110_contimg/catalog/query.py` - Catalog query interface
- `src/dsa110_contimg/qa/catalog_validation.py` - Catalog validation functions

## References

- NVSS: Condon et al. (1998), AJ, 115, 1693
- FIRST: Becker et al. (1995), ApJ, 450, 559; Helfand et al. (2015), ApJ, 801,
  26
- RACS: McConnell et al. (2020), PASA, 37, e048; Hale et al. (2021), PASA, 38,
  e058
