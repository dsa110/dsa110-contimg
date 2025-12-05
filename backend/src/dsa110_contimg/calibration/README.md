# Calibration Module

Radio interferometer calibration routines for DSA-110 data.

## Overview

Calibration corrects for instrumental and atmospheric effects in the visibility
data. This module handles:

1. **Bandpass calibration** - Frequency-dependent gain corrections
2. **Calibrator field detection** - Identifying calibrator transits in data
3. **Calibration table management** - Storing and retrieving calibration solutions

## Key Files

| File                  | Purpose                                          |
| --------------------- | ------------------------------------------------ |
| `calibration.py`      | Core calibration routines (gaincal wrapper)      |
| `field_naming.py`     | Calibrator field detection and renaming          |
| `selection.py`        | Bandpass field selection with PB-weighted flux   |
| `catalog_registry.py` | Unified catalog query interface (NVSS/FIRST/etc) |
| `catalogs.py`         | Catalog loading and source queries               |
| `caltables.py`        | Calibration table management                     |
| `selfcal.py`          | Self-calibration routines                        |
| `transit.py`          | Transit time calculations                        |

## Calibrator Detection

The pipeline auto-detects which field contains a calibrator transit:

```python
from dsa110_contimg.calibration.field_naming import rename_calibrator_fields_from_catalog

# Scans all 24 fields, finds calibrator, renames field
rename_calibrator_fields_from_catalog("observation.ms")
# Result: Field 17 renamed from "meridian_icrs_t17" to "3C286_t17"
```

## VLA Calibrator Catalog

The VLA calibrator catalog is stored in SQLite:

```python
from dsa110_contimg.calibration.catalogs import load_vla_catalog

# Load all VLA calibrators as DataFrame
df = load_vla_catalog()
print(df.columns)  # ['ra_deg', 'dec_deg', 'flux_jy']
# Note: Index is the calibrator name
```

**Important**: The catalog includes ALL calibrators from the VLA database, not just
those with 20cm flux measurements. Calibrators without L-band flux data (e.g., those
only measured at Q-band like 1911+161) are assigned a default flux of 1.0 Jy.

## Primary Beam Model

The calibrator selection uses an Airy disk primary beam model:

```python
from dsa110_contimg.calibration.beam_model import primary_beam_response

# Calculate beam response for source offset from field center
resp = primary_beam_response(
    ant_ra=field_center_ra,    # radians
    ant_dec=field_center_dec,  # radians
    src_ra=source_ra,          # radians
    src_dec=source_dec,        # radians
    freq_GHz=1.4,
    dish_dia_m=4.7,            # DSA-110 dish size
)
# Returns: 0.0-1.0 (1.0 = at phase center)
```

The Airy pattern uses scipy's Bessel function: `PB(θ) = (2·J₁(x)/x)²`
where `x = π·D·sin(θ)/λ`.

## Bandpass Field Selection

Select optimal fields for bandpass calibration using primary-beam-weighted flux:

```python
from dsa110_contimg.calibration.selection import select_bandpass_from_catalog

field_sel, indices, wflux, cal_info, peak_idx = select_bandpass_from_catalog(
    "observation.ms",
    search_radius_deg=1.0,  # Default; increase for sparse catalogs
)
name, ra_deg, dec_deg, flux_jy = cal_info
print(f"Best field: {peak_idx}, calibrator: {name}")
```

## Usage in Pipeline

Calibration typically runs after conversion:

```
UVH5 → MS → Calibration → Imaging
              ↓
         Apply bandpass
         solutions to
         target fields
```

## Database

Calibration state is tracked in the unified pipeline database:

- `/data/dsa110-contimg/state/db/pipeline.sqlite3` - Contains `caltables` table
- `/data/dsa110-contimg/state/catalogs/vla_calibrators.sqlite3` - VLA calibrator catalog
