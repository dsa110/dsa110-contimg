# Calibration Module

Radio interferometer calibration routines for DSA-110 data.

## Overview

Calibration corrects for instrumental and atmospheric effects in the visibility
data. This module handles:

1. **Bandpass calibration** - Frequency-dependent gain corrections
2. **Calibrator field detection** - Identifying calibrator transits in data
3. **Calibration table management** - Storing and retrieving calibration solutions

## Key Files

| File                     | Purpose                                 |
| ------------------------ | --------------------------------------- |
| `bandpass.py`            | Bandpass calibration routines           |
| `field_naming.py`        | Calibrator field detection and renaming |
| `calibrator_registry.py` | Database of known calibrators           |
| `calibrator_matching.py` | Match fields to calibrator catalog      |

## Calibrator Detection

The pipeline auto-detects which field contains a calibrator transit:

```python
from dsa110_contimg.calibration.field_naming import rename_calibrator_fields_from_catalog

# Scans all 24 fields, finds calibrator, renames field
rename_calibrator_fields_from_catalog("observation.ms")
# Result: Field 17 renamed from "meridian_icrs_t17" to "3C286_t17"
```

## Known Calibrators

The calibrator registry contains VLA calibrators visible to DSA-110:

```python
from dsa110_contimg.calibration.calibrator_registry import get_calibrator_info

info = get_calibrator_info("3C286")
print(info.ra_deg, info.dec_deg, info.flux_density)
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

Calibration tables are tracked in:

- `/data/dsa110-contimg/state/cal_registry.sqlite3`
- `/data/dsa110-contimg/state/calibrator_registry.sqlite3`
