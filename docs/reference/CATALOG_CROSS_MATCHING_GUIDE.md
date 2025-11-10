# Catalog Cross-Matching Guide for DSA-110

## Date: 2025-11-10

## Overview

This guide provides detailed strategies and best practices for cross-matching DSA-110 detected sources with NVSS, FIRST, and RACS catalogs, including matching algorithms, radius selection, and handling of extended sources.

## Matching Radius Selection

### Recommended Matching Radii

| Catalog | Matching Radius | Rationale |
|---------|----------------|-----------|
| **FIRST** | 1-2 arcsec | High positional accuracy (~1 arcsec) |
| **NVSS** | 1-2 arcsec | Moderate positional accuracy (~1-2 arcsec) |
| **RACS** | 2-3 arcsec | Lower accuracy (~2 arcsec), declination-dependent offsets |

### Source-Type Dependent Radii

**Point Sources:**
- Use standard matching radii (1-2 arcsec)
- Smaller radius acceptable for high-SNR sources

**Extended Sources:**
- Increase radius to 3-5 arcsec
- Consider source size (major axis) in matching
- May need position offset from centroid

**Blended/Confused Sources:**
- Use larger radius (5-10 arcsec)
- Consider multiple matches
- Manual inspection recommended

## Cross-Matching Algorithm

### Basic Matching

```python
from astropy.coordinates import SkyCoord
import astropy.units as u
import numpy as np

def cross_match_sources(
    detected_ra, detected_dec,
    catalog_ra, catalog_dec,
    match_radius_arcsec=2.0
):
    """Cross-match detected sources with catalog sources.
    
    Args:
        detected_ra, detected_dec: Arrays of detected source positions (deg)
        catalog_ra, catalog_dec: Arrays of catalog source positions (deg)
        match_radius_arcsec: Matching radius in arcseconds
    
    Returns:
        matches: Boolean array indicating matches
        separations: Angular separations in arcseconds
    """
    # Create coordinate objects
    detected_coords = SkyCoord(detected_ra, detected_dec, unit='deg')
    catalog_coords = SkyCoord(catalog_ra, catalog_dec, unit='deg')
    
    # Find nearest neighbors
    idx, sep2d, _ = detected_coords.match_to_catalog_sky(catalog_coords)
    
    # Convert separation to arcseconds
    separations = sep2d.to(u.arcsec).value
    
    # Find matches within radius
    matches = separations < match_radius_arcsec
    
    return matches, separations, idx
```

### Advanced Matching (Multiple Catalogs)

```python
def multi_catalog_match(
    detected_ra, detected_dec,
    catalogs_dict  # {'nvss': (ra, dec), 'first': (ra, dec), ...}
):
    """Match sources against multiple catalogs.
    
    Returns:
        matches: Dict of matches for each catalog
        best_match: Best matching catalog for each source
    """
    matches = {}
    best_separations = np.full(len(detected_ra), np.inf)
    best_catalog = np.full(len(detected_ra), '', dtype=object)
    
    for catalog_name, (cat_ra, cat_dec) in catalogs_dict.items():
        cat_matches, separations, _ = cross_match_sources(
            detected_ra, detected_dec, cat_ra, cat_dec
        )
        matches[catalog_name] = cat_matches
        
        # Track best match
        better = separations < best_separations
        best_separations[better] = separations[better]
        best_catalog[better] = catalog_name
    
    return matches, best_catalog, best_separations
```

## Handling Extended Sources

### Positional Offsets

Extended sources may have positional offsets between surveys due to:
- Different resolutions (NVSS 45" vs FIRST 5")
- Different source extraction methods
- Extended emission structure

**Strategy:**
1. Use source centroid for matching
2. Consider source size (major axis) in matching radius
3. For very extended sources, use larger matching radius or manual inspection

### Source Size Considerations

```python
def match_with_size(
    detected_ra, detected_dec, detected_maj_arcsec,
    catalog_ra, catalog_dec, catalog_maj_arcsec,
    base_radius=2.0
):
    """Match sources accounting for source size.
    
    Matching radius increases with source size.
    """
    # Calculate adaptive matching radius
    max_size = np.maximum(detected_maj_arcsec, catalog_maj_arcsec)
    adaptive_radius = base_radius + 0.5 * max_size  # Add half source size
    
    # Match with adaptive radius
    matches, separations, _ = cross_match_sources(
        detected_ra, detected_dec,
        catalog_ra, catalog_dec,
        match_radius_arcsec=adaptive_radius
    )
    
    return matches, separations
```

## Flux Comparison & Spectral Index

### Same Frequency (NVSS/FIRST)

NVSS and FIRST both operate at 1.4 GHz, allowing direct flux comparison:

```python
def compare_fluxes_same_freq(
    detected_flux_mjy, catalog_flux_mjy,
    flux_err_mjy=None, catalog_flux_err_mjy=None
):
    """Compare fluxes at same frequency (no spectral index needed)."""
    flux_ratio = detected_flux_mjy / catalog_flux_mjy
    
    # Calculate uncertainty if errors available
    if flux_err_mjy is not None and catalog_flux_err_mjy is not None:
        rel_err = np.sqrt(
            (flux_err_mjy / detected_flux_mjy)**2 +
            (catalog_flux_err_mjy / catalog_flux_mjy)**2
        )
        flux_ratio_err = flux_ratio * rel_err
    else:
        flux_ratio_err = None
    
    return flux_ratio, flux_ratio_err
```

### Different Frequencies (RACS vs NVSS/FIRST)

RACS requires spectral index correction:

```python
def apply_spectral_index_correction(
    flux_low_mjy, freq_low_ghz, freq_high_ghz,
    spectral_index=-0.8, spectral_index_err=0.1
):
    """Convert flux from low to high frequency using spectral index.
    
    Args:
        flux_low_mjy: Flux at low frequency (mJy)
        freq_low_ghz: Low frequency (GHz)
        freq_high_ghz: High frequency (GHz)
        spectral_index: Spectral index (S ∝ ν^α)
        spectral_index_err: Uncertainty in spectral index
    
    Returns:
        flux_high_mjy: Flux at high frequency (mJy)
        flux_high_err_mjy: Uncertainty in converted flux
    """
    # Convert flux
    flux_ratio = (freq_high_ghz / freq_low_ghz) ** spectral_index
    flux_high_mjy = flux_low_mjy * flux_ratio
    
    # Calculate uncertainty
    # d(flux)/flux = ln(freq_ratio) * d(alpha)
    rel_err = np.abs(np.log(freq_high_ghz / freq_low_ghz)) * spectral_index_err
    flux_high_err_mjy = flux_high_mjy * rel_err
    
    return flux_high_mjy, flux_high_err_mjy

# Example: Convert RACS flux (888 MHz) to NVSS frequency (1.4 GHz)
racs_flux_888 = 10.0  # mJy at 888 MHz
flux_1400, flux_1400_err = apply_spectral_index_correction(
    racs_flux_888, 0.888, 1.4, spectral_index=-0.8, spectral_index_err=0.1
)
# flux_1400 ≈ 7.4 mJy at 1.4 GHz
```

## Handling Multiple Matches

### Nearest Neighbor Matching

When multiple catalog sources match a detected source:

```python
def find_best_match(
    detected_coord, catalog_coords, catalog_fluxes=None
):
    """Find best matching catalog source.
    
    Prefers:
    1. Closest match
    2. Brightest source (if multiple at similar distance)
    """
    # Find all matches within reasonable radius
    separations = detected_coord.separation(catalog_coords)
    candidates = separations < 5.0 * u.arcsec
    
    if not np.any(candidates):
        return None, None
    
    # Among candidates, prefer closest
    candidate_seps = separations[candidates]
    closest_idx = np.argmin(candidate_seps)
    
    # If multiple at similar distance, prefer brightest
    if len(candidate_seps) > 1:
        if catalog_fluxes is not None:
            candidate_fluxes = catalog_fluxes[candidates]
            # Check if brightest is significantly brighter
            flux_ratio = candidate_fluxes[closest_idx] / np.max(candidate_fluxes)
            if flux_ratio < 0.5:  # Closest is not brightest
                brightest_idx = np.argmax(candidate_fluxes)
                if candidate_seps[brightest_idx] < 2.0 * u.arcsec:
                    closest_idx = brightest_idx
    
    match_idx = np.where(candidates)[0][closest_idx]
    return match_idx, separations[match_idx]
```

## Quality Flags & Filtering

### Source Quality Flags

```python
def assess_match_quality(
    separation_arcsec, flux_ratio, flux_ratio_err=None,
    source_type='point'
):
    """Assess quality of catalog match.
    
    Returns:
        quality: 'excellent', 'good', 'fair', 'poor'
        flags: List of quality flags
    """
    flags = []
    quality_score = 0
    
    # Positional quality
    if separation_arcsec < 1.0:
        quality_score += 2
        flags.append('excellent_position')
    elif separation_arcsec < 2.0:
        quality_score += 1
        flags.append('good_position')
    else:
        flags.append('poor_position')
    
    # Flux quality
    if flux_ratio_err is not None:
        flux_consistency = abs(flux_ratio - 1.0) / flux_ratio_err
        if flux_consistency < 2.0:  # Within 2σ
            quality_score += 2
            flags.append('consistent_flux')
        elif flux_consistency < 3.0:
            quality_score += 1
            flags.append('marginal_flux')
        else:
            flags.append('inconsistent_flux')
    
    # Source type
    if source_type == 'extended' and separation_arcsec > 2.0:
        flags.append('extended_source_offset')
    
    # Overall quality
    if quality_score >= 4:
        quality = 'excellent'
    elif quality_score >= 2:
        quality = 'good'
    elif quality_score >= 1:
        quality = 'fair'
    else:
        quality = 'poor'
    
    return quality, flags
```

## Best Practices

### 1. Use Appropriate Matching Radius

- **Point sources:** 1-2 arcsec
- **Extended sources:** 3-5 arcsec (or adaptive based on size)
- **Confused regions:** Larger radius, manual inspection

### 2. Prefer Isolated Sources

- Use isolated sources for astrometric calibration
- Avoid confused/blended regions for validation
- Filter by source density if needed

### 3. Apply Spectral Index Corrections

- Always correct RACS fluxes when comparing with NVSS/FIRST
- Use RACS-mid (1.3675 GHz) for closest frequency match
- Account for spectral index uncertainty (±0.1)

### 4. Cross-Validate Across Catalogs

- Match against multiple catalogs when available
- Use FIRST for precise positions, NVSS for completeness
- Flag sources matched in multiple catalogs

### 5. Handle Edge Cases

- **Multiple matches:** Use nearest neighbor or brightest source
- **No matches:** Check completeness limits, consider false positives
- **Extended sources:** Use adaptive matching radius

## Integration with DSA-110 Pipeline

### Current Implementation

The pipeline uses catalog validation in:
- `ImagingStage`: Flux scale validation
- `ValidationStage`: Astrometry and flux scale validation
- `AdaptivePhotometryStage`: Source selection from catalogs

### Recommended Enhancements

1. **Multi-Catalog Matching:** Match against all available catalogs
2. **Quality Flags:** Assess and flag match quality
3. **Spectral Index Handling:** Automatic correction for RACS comparisons
4. **Extended Source Handling:** Adaptive matching radius based on source size

## Related Documentation

- `docs/reference/CATALOG_USAGE_GUIDE.md` - General catalog usage guide
- `docs/reference/RADIO_SURVEY_CATALOG_COMPARISON.md` - Survey specifications
- `src/dsa110_contimg/catalog/query.py` - Catalog query interface
- `src/dsa110_contimg/qa/catalog_validation.py` - Validation functions

