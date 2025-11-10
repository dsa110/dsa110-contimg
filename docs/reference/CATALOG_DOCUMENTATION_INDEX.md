# Radio Catalog Documentation Index

## Date: 2025-11-10

## Overview

This index provides a guide to all catalog-related documentation for the DSA-110 continuum imaging pipeline. Use this to quickly find information about catalog specifications, usage, and best practices.

## Documentation Files

### 1. Survey Specifications & Comparison

**`RADIO_SURVEY_CATALOG_COMPARISON.md`**
- Comprehensive comparison of NVSS, FIRST, and RACS
- Survey specifications table (resolution, sensitivity, coverage)
- Strengths and weaknesses analysis
- Science case recommendations
- Decision tree for catalog selection

**Key Information:**
- Declination ranges for all surveys
- Resolution and sensitivity comparisons
- Sky coverage details
- Best use cases for each catalog

### 2. FIRST Coverage Details

**`FIRST_DECLINATION_COVERAGE.md`**
- Detailed FIRST declination coverage breakdown
- Regional coverage (North Galactic Cap vs. Equatorial Strip)
- Coverage gaps identified
- Implications for DSA-110 pipeline

**Key Information:**
- FIRST covers −1° to +42° (patchy)
- North Cap: +28° to +42° (~8,444 deg²)
- Equatorial Strip: −1° to +1° (~2,131 deg²)

### 3. Catalog Usage Guide

**`CATALOG_USAGE_GUIDE.md`**
- Astrometric accuracy and positional uncertainties
- Flux scale and spectral index considerations
- Catalog access methods and formats
- Completeness limits
- Multi-frequency considerations (RACS)
- Known issues and caveats
- Performance considerations
- Integration best practices

**Key Information:**
- Positional uncertainties: FIRST ~1", NVSS ~1-2", RACS ~2"
- Spectral index corrections needed for RACS comparisons
- Matching radii recommendations
- Completeness limits for each catalog

### 4. Cross-Matching Guide

**`CATALOG_CROSS_MATCHING_GUIDE.md`**
- Matching radius selection strategies
- Cross-matching algorithms (basic and advanced)
- Handling extended sources
- Flux comparison methods
- Spectral index correction code examples
- Handling multiple matches
- Quality flags and filtering
- Best practices

**Key Information:**
- Code examples for cross-matching
- Spectral index correction formulas
- Quality assessment methods
- Multi-catalog matching strategies

### 5. Naming Clarification

**`RAX_RACS_NAMING_CLARIFICATION.md`** (in `docs/dev/`)
- Clarifies RAX vs. RACS naming issue
- Notes that codebase "RAX" likely refers to RACS
- Recommendations for naming updates

## Quick Reference

### Declination Coverage

| Survey | Declination Range | Notes |
|-------|------------------|-------|
| **NVSS** | North of -40° | ~82% of sky, uniform |
| **FIRST** | −1° to +42° | Patchy: +28° to +42° main, −1° to +1° strip |
| **RACS** | South of +41° to +47° | Most releases: up to +41° |

### Positional Accuracy

| Catalog | Positional Uncertainty | Matching Radius |
|---------|----------------------|------------------|
| **FIRST** | ~1 arcsec | 1-2 arcsec |
| **NVSS** | ~1-2 arcsec | 1-2 arcsec |
| **RACS** | ~2 arcsec | 2-3 arcsec |

### Flux Scale

| Catalog | Frequency | Spectral Index Needed? |
|---------|-----------|----------------------|
| **NVSS** | 1.4 GHz | No (same as DSA-110) |
| **FIRST** | 1.4 GHz | No (same as DSA-110) |
| **RACS** | 0.888 GHz (primary) | Yes (α = -0.8 ± 0.1) |
| **RACS-mid** | 1.3675 GHz | Minimal (close to 1.4 GHz) |

### Completeness Limits

| Catalog | 5σ Detection | Completeness |
|---------|-------------|--------------|
| **NVSS** | ~2.5 mJy | ~3-5 mJy |
| **FIRST** | ~1 mJy | ~1-2 mJy |
| **RACS** | ~3-5 mJy | ~5 mJy |

## Use Cases by Science Goal

### Source Validation & Cross-Matching
- **Recommended:** FIRST > NVSS > RACS
- **Rationale:** FIRST provides highest resolution and most precise positions

### Flux Scale Validation
- **Recommended:** NVSS > RACS > FIRST
- **Rationale:** NVSS has widest sky coverage and uniform sensitivity

### Extended Source Studies
- **Recommended:** NVSS > RACS > FIRST
- **Rationale:** NVSS's low resolution preserves extended emission

### Compact Source Studies
- **Recommended:** FIRST > RACS > NVSS
- **Rationale:** FIRST's high resolution essential for compact sources

### Southern Sky Studies
- **Recommended:** RACS > NVSS (limited)
- **Rationale:** RACS covers entire southern sky

### Northern Sky Studies
- **Recommended:** NVSS > FIRST > RACS (not applicable)
- **Rationale:** NVSS provides widest northern sky coverage

## Code Integration

### Querying Catalogs

```python
from dsa110_contimg.catalog.query import query_sources

# Query NVSS sources
nvss_sources = query_sources(
    catalog_type="nvss",
    ra_center=122.0,
    dec_center=54.7,
    radius_deg=0.5,
    min_flux_mjy=5.0
)
```

### Cross-Matching

See `CATALOG_CROSS_MATCHING_GUIDE.md` for detailed algorithms and code examples.

### Flux Comparison

See `CATALOG_USAGE_GUIDE.md` for spectral index correction code examples.

## Related Code

- `src/dsa110_contimg/catalog/query.py` - Catalog query interface
- `src/dsa110_contimg/catalog/builders.py` - Catalog database builders
- `src/dsa110_contimg/qa/catalog_validation.py` - Catalog validation functions
- `src/dsa110_contimg/pipeline/stages_impl.py` - Catalog setup stage

## Summary

All catalog-related information is now comprehensively documented:

1. ✅ Survey specifications and comparison
2. ✅ Declination coverage details (FIRST, RACS)
3. ✅ Astrometric accuracy and positional uncertainties
4. ✅ Flux scale and spectral index considerations
5. ✅ Cross-matching strategies and algorithms
6. ✅ Catalog access methods and formats
7. ✅ Completeness limits
8. ✅ Multi-frequency considerations (RACS)
9. ✅ Known issues and caveats
10. ✅ Best practices and recommendations

Use this index to quickly navigate to the relevant documentation for your specific needs.

