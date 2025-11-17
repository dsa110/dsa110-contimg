# Automatic Calibrator Registration Algorithm

## Overview

This algorithm automatically registers bandpass calibrators and pre-calculates
transit times when the telescope declination changes. It is integrated into the
watchdog service that monitors `/data/incoming/` for new HDF5 files.

## Algorithm Flow

```
1. New HDF5 file detected in /data/incoming/
   ↓
2. Extract pointing (RA, Dec) from file
   ↓
3. Check if declination has changed significantly (> threshold)
   ↓
4. If Dec change detected:
   ├─→ Check if BP calibrator is registered for new Dec
   │   ├─→ If YES: Calculate transit times for time range spanned by data on disk
   │   └─→ If NO: Continue to step 5
   │
   └─→ Find and register calibrator:
       ├─→ Try VLA calibrator catalog (brightest within ±2.5° tolerance)
       │   └─→ If found: Register and calculate transit times
       │
       └─→ If no VLA calibrator: Try NVSS catalog (brightest within ±2.5° tolerance)
           ├─→ Check for FIRST and RACS databases (warn if missing but should exist)
           └─→ If found: Register and calculate transit times
```

## Implementation

### Main Module

**File**: `dsa110_contimg/pointing/auto_calibrator.py`

**Key Functions**:

1. **`on_new_hdf5_file()`** - Entry point called by watchdog service
   - Extracts pointing from HDF5 file
   - Detects declination change
   - Triggers calibrator registration if needed

2. **`handle_declination_change()`** - Main algorithm logic
   - Checks for existing BP calibrator
   - Finds and registers new calibrator if needed
   - Pre-calculates transit times

3. **`check_bp_calibrator_registered()`** - Checks if calibrator exists
   - Queries `bandpass_calibrators` table
   - Returns calibrator info if found within tolerance

4. **`find_brightest_vla_calibrator()`** - Finds VLA calibrator
   - Loads VLA catalog
   - Filters by declination tolerance (±2.5°)
   - Returns brightest (highest flux) calibrator

5. **`find_brightest_nvss_source()`** - Finds NVSS source
   - Checks for missing FIRST and RACS databases (warns if missing but should
     exist)
   - Queries NVSS catalog
   - Filters by declination tolerance (±2.5°)
   - Returns brightest source

6. **`register_and_precalculate_transits()`** - Registers calibrator
   - Registers in `bandpass_calibrators` table
   - Calculates transit times for data time range
   - Stores in `calibrator_transits` table

7. **`get_data_time_range()`** - Gets time range of data on disk
   - Queries database for HDF5 files on disk
   - Returns earliest and latest observation times

### Integration

The algorithm is integrated into `dsa110_contimg/pointing/monitor.py`:

- When a new HDF5 file is processed, `on_new_hdf5_file()` is called
- This happens automatically in the `log_pointing_from_file()` method

## Configuration

### Declination Tolerance

- **Default**: ±2.5 degrees
- **Constant**: `DEC_TOLERANCE_DEG = 2.5` in `auto_calibrator.py`
- Used for:
  - Matching existing calibrators
  - Finding new VLA calibrators
  - Finding new NVSS sources

### Declination Change Threshold

- **Default**: 0.1 degrees
- **Parameter**: `dec_change_threshold` in `on_new_hdf5_file()`
- Minimum change required to trigger the algorithm

## Database Tables Used

1. **`pointing_history`** (in ingest DB)
   - Tracks telescope pointing over time
   - Used to detect declination changes

2. **`bandpass_calibrators`** (in products DB)
   - Stores registered BP calibrators
   - Columns: `calibrator_name`, `ra_deg`, `dec_deg`, `dec_range_min`,
     `dec_range_max`, `status`

3. **`calibrator_transits`** (in products DB)
   - Stores pre-calculated transit times
   - Created by `precalculate_transits_for_calibrator()`

4. **Subband groups** (in products DB)
   - Tracks HDF5 files and their on-disk status
   - Used to determine data time range

## Calibrator Selection Priority

1. **Existing BP Calibrator** (if registered)
   - Reuse existing calibrator
   - Recalculate transit times for new data time range

2. **VLA Calibrator** (if available)
   - Standard VLA calibrator catalog
   - Brightest source within tolerance
   - Preferred for calibration quality

3. **NVSS Source** (fallback)
   - NVSS radio source catalog
   - Brightest source within tolerance
   - Used when no VLA calibrator available
   - **Cross-matching**: When NVSS is used, automatically checks for FIRST and
     RACS databases
     - Warns if databases are missing but should exist (within coverage limits)
     - Helps debug pipeline issues during development

## Transit Time Calculation

When a calibrator is registered or found:

1. **Determine data time range**:
   - Query database for all HDF5 files on disk
   - Find earliest and latest observation times

2. **Calculate transit times**:
   - Use `precalculate_transits_for_calibrator()`
   - Search back from current time to earliest data
   - Assess data availability for each transit
   - Store in `calibrator_transits` table

3. **Validation**:
   - Declination match within ±2.5° tolerance
   - Primary beam response > 30%
   - Complete subband groups (16 files)

## Usage

The algorithm runs automatically when:

1. Watchdog service monitors `/data/incoming/`
2. New HDF5 file is detected
3. Declination change is detected

**Manual trigger** (for testing):

```python
from dsa110_contimg.pointing.auto_calibrator import handle_declination_change
from pathlib import Path

products_db = Path("/data/dsa110-contimg/state/products.sqlite3")
handle_declination_change(
    new_dec_deg=54.6,
    products_db_path=products_db,
    dec_change_threshold=0.1,
)
```

## Logging

The algorithm logs at INFO level:

- Declination changes detected
- Calibrator registration
- Transit time pre-calculation results
- Warnings when no calibrator found

The algorithm logs at WARNING level:

- Catalog coverage limit violations (declination outside coverage)
- Empty catalog database results
- Missing catalog databases (when they should exist)

## Catalog Coverage Checks and Warnings

### Coverage Limits

The system checks catalog coverage limits and warns when observations fall
outside:

| Catalog   | Declination Coverage | Notes                                       |
| --------- | -------------------- | ------------------------------------------- |
| **NVSS**  | Declination > -40°   | Northern sky only                           |
| **FIRST** | Declination > -40°   | Northern sky only (similar to NVSS)         |
| **RACS**  | Declination < +49.9° | Southern sky (varies by band: +41° to +49°) |

### Coverage Warnings

When catalog databases are built, the system:

1. **Checks coverage limits**:
   - Warns if declination is outside catalog's coverage range
   - Example:
     `⚠️  Declination -45.0° is outside NVSS coverage (southern limit: -40.0°)`

2. **Warns on empty results**:
   - Flags when filtered result has 0 sources
   - Indicates potential coverage issue

3. **Stores coverage status**:
   - `within_coverage` flag in database metadata
   - `"true"` if within limits, `"false"` if outside

### Missing Database Checks

When NVSS catalog is queried:

1. **Automatic cross-matching check**:
   - Checks for FIRST and RACS databases
   - Only checks catalogs within coverage limits for the declination

2. **Warnings for missing databases**:
   - Warns if database should exist but doesn't
   - Example:
     `⚠️  FIRST catalog database is missing for declination 54.6°, but should exist (within coverage limits: -40.0° to 90.0°). Database should be built by CatalogSetupStage.`

3. **Integration points**:
   - `query_nvss_sources()` - Checks when NVSS is queried
   - `find_brightest_nvss_source()` - Checks during automatic calibrator
     selection
   - `build_*_strip_db()` - Checks during database creation

### Helper Functions

**`check_catalog_database_exists()`** (in `dsa110_contimg/catalog/builders.py`):

- Checks if a catalog database exists for a given declination
- Returns `(exists: bool, db_path: Optional[Path])`

**`check_missing_catalog_databases()`** (in
`dsa110_contimg/catalog/builders.py`):

- Checks which catalog databases are missing when they should exist
- Only checks catalogs within coverage limits
- Generates warnings for missing databases
- Returns dictionary mapping `catalog_type -> exists (bool)`

## Error Handling

- Failures in calibrator finding are logged but don't stop the monitor
- Database errors trigger reconnection attempts
- Missing catalogs are logged as warnings
- **Coverage warnings**: Generated when declination is outside catalog limits
- **Missing database warnings**: Generated when databases should exist but don't
  (within coverage)

## Future Enhancements

- Configurable declination tolerance per calibrator type
- Support for additional catalog sources
- Automatic calibrator quality assessment
- Integration with calibration solving stage
- Auto-build missing catalog databases when detected (if within coverage)
- Coverage status in pipeline status reports
- Coverage visualization tools
