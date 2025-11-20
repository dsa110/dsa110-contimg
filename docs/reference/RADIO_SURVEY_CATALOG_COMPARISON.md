# Radio Survey Catalog Comparison: NVSS, FIRST, and RACS

## Date: 2025-11-10

## Overview

This document compares the three primary radio survey catalogs used in the
DSA-110 pipeline: **NVSS**, **FIRST**, and **RACS** (Rapid ASKAP Continuum
Survey). Understanding their specifications, strengths, and weaknesses enables
optimal catalog selection for different science cases.

## Survey Specifications Comparison

| Parameter               | NVSS                                                     | FIRST                                                                                                                                          | RACS                                                                                                  |
| ----------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Full Name**           | NRAO VLA Sky Survey                                      | Faint Images of the Radio Sky at Twenty-centimeters                                                                                            | Rapid ASKAP Continuum Survey                                                                          |
| **Frequency**           | 1.4 GHz (1400 MHz)                                       | 1.4 GHz (1400 MHz)                                                                                                                             | ~0.888 GHz (887.5 MHz) primary<br>Also: 943.5 MHz, 1367.5 MHz, 1655.5 MHz                             |
| **Wavelength**          | 21 cm                                                    | 21 cm                                                                                                                                          | ~34 cm (primary)                                                                                      |
| **Angular Resolution**  | ~45 arcsec                                               | ~5 arcsec                                                                                                                                      | ~15-25 arcsec (15" for high-res)                                                                      |
| **Sensitivity (rms)**   | ~0.45 mJy/beam                                           | ~0.15 mJy/beam                                                                                                                                 | ~0.45 mJy/beam (Stokes I)                                                                             |
| **Detection Threshold** | ~2.5 mJy (5σ)                                            | ~1 mJy (5σ)                                                                                                                                    | ~3-5 mJy (95% completeness)                                                                           |
| **Sky Coverage**        | North of -40° declination<br>(~82% of sky, ~33,000 deg²) | ~10,575 deg²<br>North Galactic Cap: +28° to +42° (~8,444 deg²)<br>South Equatorial Strip: −1° to +1° (~2,131 deg²)<br>Total range: −1° to +42° | South of +41° to +47° declination<br>(~36,200 deg², entire southern sky)<br>Most releases: up to +41° |
| **Source Density**      | ~60 sources/sq. deg                                      | ~90 sources/sq. deg                                                                                                                            | Variable (millions total)                                                                             |
| **Total Sources**       | ~1.8 million                                             | ~950,000                                                                                                                                       | ~2.5 million (first release)                                                                          |
| **Telescope**           | VLA (D-configuration)                                    | VLA (B-configuration)                                                                                                                          | ASKAP (36 dishes)                                                                                     |
| **Pixel Scale**         | ~1.5 arcsec                                              | ~1.8 arcsec                                                                                                                                    | Variable                                                                                              |
| **Survey Era**          | 1993-1996                                                | 1993-2011 (20+ years)                                                                                                                          | 2019-present (ongoing)                                                                                |

## Detailed Specifications

### NVSS (NRAO VLA Sky Survey)

**Strengths:**

- **Wide Sky Coverage:** Largest uniform coverage (~82% of sky)
- **Extended Sources:** Low resolution (45") preserves extended/diffuse emission
- **Surface Brightness:** Excellent sensitivity to low surface brightness
  structures
- **Completeness:** Best for wide-area completeness studies
- **Mature Catalog:** Well-established, extensively used

**Weaknesses:**

- **Low Resolution:** Cannot resolve compact sources or separate blends
- **Moderate Sensitivity:** Higher rms noise (~0.45 mJy) than FIRST
- **Northern Sky Only:** Limited to declination > -40°
- **Aging Data:** Observations from 1993-1996

**Best For:**

- Wide-area source counts and completeness studies
- Extended radio galaxies and diffuse emission
- Low surface brightness structures
- Large-scale structure studies
- Cross-matching when precise positions not critical

### FIRST (Faint Images of the Radio Sky at Twenty-centimeters)

**Strengths:**

- **High Resolution:** 5" resolution (~9× better than NVSS)
- **High Sensitivity:** ~3× more sensitive than NVSS (0.15 mJy rms)
- **Precise Positions:** Essential for accurate cross-matching with optical/IR
- **Source Separation:** Can resolve blends and identify compact sources
- **Deep Coverage:** Detects fainter sources (~1 mJy threshold)

**Weaknesses:**

- **Limited Sky Coverage:** Only ~10,575 deg² (much smaller than NVSS)
- **Limited Declination Range:** Covers −1° to +42° declination (patchy
  coverage)
  - North Galactic Cap: +28° to +42° (~8,444 deg²)
  - South Equatorial Strip: −1° to +1° (~2,131 deg²)
- **Resolves Out Extended Emission:** Misses diffuse/low surface brightness
  sources
- **Patchy Coverage:** Not uniform all-sky coverage
- **Surface Brightness:** Limited sensitivity to extended structures

**Best For:**

- Precise source identification and cross-matching
- Compact source studies
- Optical/IR cross-identification (SDSS overlap)
- High-resolution structural studies
- Source blending resolution

### RACS (Rapid ASKAP Continuum Survey)

**Strengths:**

- **Southern Sky Coverage:** Entire southern sky (complements NVSS)
- **Modern Instrumentation:** ASKAP's Phased-Array Feed (PAF) technology
- **Rapid Survey:** Fast completion due to large field of view (~31 deg²)
- **Intermediate Resolution:** 15-25" (balance between NVSS and FIRST)
- **Multiple Frequencies:** Observations at multiple bands (0.888, 0.944, 1.368,
  1.655 GHz)
- **Recent Data:** Ongoing survey with modern data quality

**Weaknesses:**

- **Southern Sky Only:** Limited to declination < +41° to +47° (varies by
  release; most cover up to +41°)
- **Moderate Resolution:** Not as high as FIRST (15" vs 5")
- **Moderate Sensitivity:** Similar to NVSS (~0.45 mJy)
- **Newer Catalog:** Less mature than NVSS/FIRST

**Best For:**

- Southern sky studies (complements NVSS)
- Wide-area surveys with good resolution
- Modern calibration and validation
- Multi-frequency spectral studies
- Extended sources (better than FIRST, not as good as NVSS)

## Science Case Recommendations

### For DSA-110 Continuum Imaging Pipeline

#### 1. **Source Validation & Cross-Matching**

**Recommended:** FIRST (if available) > NVSS > RACS

**Rationale:**

- FIRST provides highest resolution and most precise positions
- Essential for accurate cross-matching with optical/IR catalogs
- Better source separation reduces confusion

**When to Use:**

- Validating detected sources
- Cross-matching with optical catalogs
- Precise astrometry verification

#### 2. **Flux Scale Validation**

**Recommended:** NVSS > RACS > FIRST

**Rationale:**

- NVSS has widest sky coverage and uniform sensitivity
- Better for statistical flux comparisons
- More sources available for validation

**When to Use:**

- Calibrating flux scales
- Validating pipeline flux measurements
- Statistical completeness studies

#### 3. **Extended Source Studies**

**Recommended:** NVSS > RACS > FIRST

**Rationale:**

- NVSS's low resolution preserves extended emission
- Better surface brightness sensitivity
- RACS provides intermediate resolution for southern sky

**When to Use:**

- Studying extended radio galaxies
- Detecting diffuse emission
- Low surface brightness structures

#### 4. **Compact Source Studies**

**Recommended:** FIRST > RACS > NVSS

**Rationale:**

- FIRST's high resolution essential for compact sources
- Better source separation and identification
- RACS provides good resolution for southern sky

**When to Use:**

- Compact source identification
- Resolving source blends
- High-resolution structural studies

#### 5. **Southern Sky Studies**

**Recommended:** RACS > NVSS (limited)

**Rationale:**

- RACS covers entire southern sky
- NVSS limited to declination > -40°
- RACS provides modern, high-quality data

**When to Use:**

- Observations at southern declinations
- Southern sky completeness studies
- Modern calibration references

#### 6. **Northern Sky Studies**

**Recommended:** NVSS > FIRST > RACS (not applicable)

**Rationale:**

- NVSS provides widest northern sky coverage
- FIRST available for specific regions
- RACS not applicable (southern sky only)

**When to Use:**

- Northern declination observations
- Wide-area northern sky studies
- Large-scale structure studies

## Catalog Selection Strategy

### Decision Tree

```
1. What declination?
   ├─ Southern (< -40°): Use RACS
   ├─ Northern (> -40°): Continue to step 2
   └─ Overlap region (-40° to +41°): Use NVSS or RACS (RACS covers up to +41° to +47° depending on release)

2. What resolution needed?
   ├─ High resolution (5"): Use FIRST (if available)
   ├─ Medium resolution (15-25"): Use RACS or NVSS
   └─ Low resolution (45"): Use NVSS

3. What sensitivity needed?
   ├─ High sensitivity (< 1 mJy): Use FIRST
   ├─ Medium sensitivity (1-3 mJy): Use NVSS or RACS
   └─ Low sensitivity (> 3 mJy): Use NVSS

4. What source type?
   ├─ Extended/diffuse: Use NVSS
   ├─ Compact: Use FIRST
   └─ Mixed: Use RACS or NVSS
```

### Multi-Catalog Approach

**Best Practice:** Use multiple catalogs when possible:

1. **Primary:** NVSS for wide-area validation
2. **High-Resolution:** FIRST for precise cross-matching (when available)
3. **Southern Sky:** RACS for declination < -40°
4. **Cross-Validation:** Compare results across catalogs

## Implementation in DSA-110 Pipeline

### Current Usage

The pipeline supports all three catalogs:

- **NVSS:** Primary catalog for validation and cross-matching
- **FIRST:** Available for high-resolution studies
- **RACS:** Available for southern sky observations

### Catalog Query System

The `dsa110_contimg.catalog.query` module supports:

- Automatic catalog selection based on declination
- Multi-catalog queries
- Catalog-specific filtering

### Recommendations

1. **Default:** Use NVSS for general validation (widest coverage)
2. **High-Resolution:** Use FIRST when precise positions needed
3. **Southern Sky:** Use RACS for declination < -40°
4. **Cross-Validation:** Compare results across catalogs when available

## Summary

| Catalog   | Best Use Case                           | Key Strength                    | Key Limitation    |
| --------- | --------------------------------------- | ------------------------------- | ----------------- |
| **NVSS**  | Wide-area validation, extended sources  | Sky coverage, extended emission | Low resolution    |
| **FIRST** | Precise cross-matching, compact sources | High resolution, sensitivity    | Limited coverage  |
| **RACS**  | Southern sky, modern calibration        | Southern coverage, modern data  | Southern sky only |

**For DSA-110:**

- **Primary:** NVSS for general validation (best coverage)
- **High-Resolution:** FIRST for precise cross-matching (when available)
- **Southern Sky:** RACS for declination < -40° (complements NVSS)

## References

- NVSS: Condon et al. (1998), AJ, 115, 1693
- FIRST: Becker et al. (1995), ApJ, 450, 559; Helfand et al. (2015), ApJ, 801,
  26
- RACS: McConnell et al. (2020), PASA, 37, e048; Hale et al. (2021), PASA, 38,
  e058

## Notes

### RAX vs RACS Naming

**Important:** The codebase uses "RAX" as the catalog identifier, but this
likely refers to **RACS (Rapid ASKAP Continuum Survey)**.

- **RAX** (Radio Aurora eXplorer) is actually a CubeSat mission for ionospheric
  research, not a radio survey catalog.
- **RACS** (Rapid ASKAP Continuum Survey) is the actual radio survey that
  produces astronomical catalogs.
- The codebase's "RAX" identifier is likely a shorthand or historical naming
  convention for RACS.

**Recommendation:** Consider updating codebase references from "RAX" to "RACS"
for clarity, or document that "RAX" refers to RACS.

### Other Notes

- **Catalog Availability:** FIRST coverage is patchy; check availability for
  specific declination strips.
- **Frequency Mismatch:** RACS at ~0.888 GHz vs NVSS/FIRST at 1.4 GHz - spectral
  index corrections may be needed for flux comparisons.
- **RACS Multi-Frequency:** RACS has multiple frequency bands (low/mid/high) -
  use appropriate band for science case.
