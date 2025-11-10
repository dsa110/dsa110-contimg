# Declination Change Detection

## Date: 2025-11-10

## Overview

Added declination change detection to the `CatalogSetupStage` to flag when the telescope's pointing (declination) changes significantly. This is critical for DSA-110 since it only slews in elevation and declination changes rarely, but when they do, catalogs need immediate update.

## Implementation

### Detection Logic

**Location:** `src/dsa110_contimg/pipeline/stages_impl.py::CatalogSetupStage`

**Process:**
1. Extract current declination from HDF5 observation file
2. Query `pointing_history` table for most recent declination
3. Compare current vs. previous declination
4. Flag change if difference exceeds threshold (default: 0.1°)
5. Log pointing to `pointing_history` for future comparisons

**Code:**
```python
# Get most recent declination from pointing_history
cursor.execute(
    "SELECT dec_deg FROM pointing_history ORDER BY timestamp DESC LIMIT 1"
)
result = cursor.fetchone()
if result:
    previous_dec = float(result[0])
    dec_change = abs(dec_center - previous_dec)
    
    if dec_change > dec_change_threshold:
        dec_change_detected = True
        logger.warning(
            f"⚠️  DECLINATION CHANGE DETECTED: "
            f"{previous_dec:.6f}° → {dec_center:.6f}° "
            f"(Δ = {dec_change:.6f}° > {dec_change_threshold:.6f}° threshold)"
        )
```

### Configuration

**Default Threshold:** 0.1 degrees (configurable via `config.catalog_setup_dec_change_threshold`)

**Rationale:**
- DSA-110 declination changes are rare but significant
- 0.1° threshold catches meaningful changes while ignoring small variations
- Catalogs are built for ±6° strips, so 0.1° change is significant

### Logging

**When Change Detected:**
```
⚠️  DECLINATION CHANGE DETECTED: 54.700000° → 55.200000° (Δ = 0.500000° > 0.100000° threshold)
⚠️  Telescope pointing has changed significantly. Catalogs will be rebuilt for new declination strip.
```

**When Stable:**
```
Declination stable: 54.700000° (previous: 54.700000°, Δ = 0.000000°)
```

### Pointing History

**Table:** `pointing_history` in `products.sqlite3`

**Schema:**
```sql
CREATE TABLE pointing_history (
    timestamp REAL PRIMARY KEY,
    ra_deg REAL,
    dec_deg REAL
)
```

**Usage:**
- Stores pointing for each observation
- Used to detect declination changes
- Populated by `CatalogSetupStage` and `PointingMonitor`

## Integration

### Catalog Setup Stage

The `CatalogSetupStage` now:
1. Detects declination changes
2. Flags significant changes (> threshold)
3. Logs pointing to `pointing_history`
4. Builds catalogs for new declination (if needed)

### Pointing Monitor

The existing `PointingMonitor` (`src/dsa110_contimg/pointing/monitor.py`) also logs pointing, but doesn't detect changes. The `CatalogSetupStage` complements it by:
- Detecting changes during pipeline execution
- Flagging changes immediately
- Ensuring catalogs are rebuilt when needed

## Benefits

1. **Automatic Detection:** Flags declination changes automatically
2. **Immediate Action:** Catalogs rebuilt when declination changes
3. **Observatory-Specific:** Adapts to DSA-110's drift scan pattern
4. **Non-Blocking:** Detection doesn't fail pipeline if pointing history unavailable

## Usage

### Automatic (Default)

Declination change detection runs automatically in `CatalogSetupStage`:

```python
from dsa110_contimg.pipeline.workflows import standard_imaging_workflow

workflow = standard_imaging_workflow(config)
context = workflow.execute(initial_context)

# Check if declination change was detected
catalog_status = context.outputs.get("catalog_setup_status", {})
if catalog_status.get("dec_change_detected"):
    print("⚠️  Declination change detected!")
```

### Configuration

```python
# Set custom threshold (degrees)
config.catalog_setup_dec_change_threshold = 0.5  # 0.5° threshold
```

## Future Enhancements

### Potential Additions:

1. **Alert System:** Send alerts/notifications when declination changes
2. **Dashboard Integration:** Display declination changes in monitoring dashboard
3. **Historical Tracking:** Track declination change frequency and patterns
4. **Automatic Actions:** Trigger additional actions when declination changes (e.g., recalibration)

### Example Alert Integration:

```python
if dec_change_detected:
    # Send alert
    send_alert(
        level="warning",
        message=f"Telescope declination changed: {previous_dec:.6f}° → {dec_center:.6f}°",
        action="Catalogs rebuilt automatically"
    )
```

## Related Files

- `src/dsa110_contimg/pipeline/stages_impl.py` - CatalogSetupStage with change detection
- `src/dsa110_contimg/pointing/monitor.py` - PointingMonitor (logs pointing)
- `src/dsa110_contimg/database/products.py` - pointing_history table schema
- `docs/dev/AUTOMATIC_CATALOG_SETUP_IMPLEMENTATION.md` - Catalog setup documentation

## Status

✅ **COMPLETE** - Declination change detection implemented in CatalogSetupStage.

The pipeline now automatically detects and flags when telescope pointing (declination) changes, ensuring catalogs are rebuilt when needed.

