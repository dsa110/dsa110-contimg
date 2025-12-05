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
print(df.columns)  # ['name', 'ra_deg', 'dec_deg', 'flux_1400', ...]
```

## Bandpass Field Selection

Select optimal fields for bandpass calibration using primary-beam-weighted flux:

```python
from dsa110_contimg.calibration.selection import select_bandpass_from_catalog

field_sel, indices, wflux, cal_info, peak_idx = select_bandpass_from_catalog("observation.ms")
print(f"Best field: {peak_idx}, calibrator: {cal_info}")
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
