# FIRST Survey Declination Coverage

## Date: 2025-11-10

## Overview

The FIRST (Faint Images of the Radio Sky at Twenty Centimeters) radio survey has **patchy sky coverage** focused on specific regions rather than uniform all-sky coverage.

## Declination Range

### Total Coverage

**Declination Range:** Approximately **−1° to +42°**

**Total Sky Area:** ~10,575 square degrees

### Regional Breakdown

| Region | Declination Range | Sky Area | Notes |
|--------|------------------|----------|-------|
| **North Galactic Cap** | +28° to +42° | ~8,444 deg² | Main coverage area, overlaps with SDSS |
| **South Equatorial Strip** | −1° to +1° | ~2,131 deg² | Narrow strip along celestial equator |
| **Total** | −1° to +42° | ~10,575 deg² | Combined coverage |

## Coverage Details

### North Galactic Cap (Primary Coverage)

- **Declination:** +28° to +42°
- **Area:** ~8,444 square degrees
- **Purpose:** Designed to overlap with Sloan Digital Sky Survey (SDSS) footprint
- **Coverage:** Most of FIRST's sources are in this region

### South Equatorial Strip (Secondary Coverage)

- **Declination:** −1° to +1°
- **Area:** ~2,131 square degrees
- **Coverage:** Narrow strip along celestial equator
- **Purpose:** Provides equatorial coverage for cross-matching studies

## Gaps in Coverage

**FIRST does NOT cover:**
- Declinations < −1° (except the narrow equatorial strip)
- Declinations > +42°
- Most of the sky between −1° and +28° (gap between equatorial strip and north cap)

## Comparison with Other Surveys

| Survey | Declination Range | Sky Coverage |
|--------|------------------|--------------|
| **NVSS** | −40° to +90° | ~82% of sky (~33,000 deg²) |
| **FIRST** | −1° to +42° (patchy) | ~10,575 deg² |
| **RACS** | −90° to +41° to +47° | ~90% of sky (~36,200 deg²) |

## Implications for DSA-110

### When FIRST is Available

FIRST coverage is available for:
- **Declination +28° to +42°:** Primary coverage region (best availability)
- **Declination −1° to +1°:** Equatorial strip (limited coverage)

### When FIRST is NOT Available

FIRST is **not available** for:
- Declinations < −1° (use NVSS or RACS)
- Declinations > +42° (use NVSS)
- Declinations between +1° and +28° (use NVSS or RACS)

### Recommendation

**For DSA-110 Pipeline:**
1. **Check FIRST availability** for specific declination strips
2. **Use NVSS as fallback** for declinations outside FIRST coverage
3. **Use RACS** for southern declinations (< −1°)

## Usage in Pipeline

The catalog query system should:
1. Check if declination falls within FIRST coverage (−1° to +42°)
2. Verify specific region (north cap vs. equatorial strip)
3. Fall back to NVSS or RACS if FIRST unavailable

## References

- FIRST Survey: Becker et al. (1995), ApJ, 450, 559
- FIRST Final Catalog: Helfand et al. (2015), ApJ, 801, 26
- FIRST Survey Parameters: http://sundog.stsci.edu/first/catalog_paper/node2.html

