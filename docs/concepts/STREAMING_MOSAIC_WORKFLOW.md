# Streaming Mosaic Generation Workflow

## Overview

This document describes the streaming mosaic generation workflow for DSA-110
continuum imaging. The workflow processes groups of 10 MS files in a sliding
window pattern with 2 MS overlap between consecutive mosaics.

**Key Principle**: The **calibration registry** (`cal_registry.sqlite3`) is the
**authoritative source** for determining which calibration solutions to apply.
All calibration decisions are made by querying the registry based on observation
time and validity windows.

## Workflow Steps

### 1. HDF5 Group Detection and Staging

- **Input**: Groups of 16 subband HDF5 files detected in `/data/incoming`
- **Action**:
  - Register group as a 5-minute observation
  - Move HDF5 files to staging area (`/stage/dsa110-contimg/hdf5/`)
  - Register in products database with `stage="staging"`

### 2. HDF5 to MS Conversion

- **Input**: Staged HDF5 group (16 subband files)
- **Action**:
  - Convert to MS file
  - Register MS in products database with `stage="converted"`,
    `status="converted"`
  - Remove HDF5 files from staging area (but **NEVER** remove from
    `/data/incoming`)

### 3. Group Formation (10 MS Groups)

- **Trigger**: When 10 MS files are registered as `stage="converted"` and
  `status="converted"`
- **Action**: Form a group of 10 MS files, ordered by observation time
  (`mid_mjd`)

### 4. Calibration Solving

- **Calibration MS Selection**: Use the **5th MS** (middle by time) in the group
  of 10
- **Registry Check First**: Before solving, check registry for existing valid
  solutions:
  - Query registry for 5th MS observation time to see if valid tables already
    exist
  - If valid tables found in registry, skip solving and use registry tables
  - Registry is authoritative - only solve if no valid tables exist in registry
- **Gain Calibration** (solve if not in registry):
  - Solve `.gpcal` (phase-only, `solint="inf"`)
  - Solve `.2gcal` (short-timescale phase, `solint="60s"`)
  - **Validity Window**: 1 hour centered on the 5th MS observation time
    - Start: 30 minutes before 5th MS `mid_mjd`
    - End: 30 minutes after 5th MS `mid_mjd`
  - **Register in Registry**: After solving, register tables with validity
    windows
- **Bandpass Calibration** (conditional, solve if not in registry):
  - Check if any MS in the group contains the VLA calibrator defined for the
    current pointing
  - **Check Registry First**: Query registry for valid BP table covering
    observation time
  - **Validity Window**: 24 hours centered on calibrator transit
    - Start: 12 hours BEFORE calibrator transit
    - End: 12 hours AFTER calibrator transit
  - **Special Case - New Calibrator**: When pointing Dec changes and a new
    calibrator is chosen:
    - First transit starts a "1st day" period
    - "1st day" ends 12 hours AFTER that first transit (may not be exactly 24
      hours)
    - After "1st day", regular 24-hour intervals resume (centered on subsequent
      transits)
  - If calibrator present and no valid BP in registry: Solve `.bpcal` using the
    calibrator MS
  - **Register in Registry**: After solving, register BP table with
    transit-centered validity window

### 5. Calibration Application

- **Input**: All 10 MS files in the group
- **Action**:
  - **Registry-Based Solution Selection**: For each MS, query the calibration
    registry to find valid solutions:
    - Query by MS observation time (`mid_mjd`) to find calibration tables whose
      validity windows (`valid_start_mjd`, `valid_end_mjd`) include the MS
      observation time
    - Use `get_active_applylist(registry_db, ms_mid_mjd)` to retrieve ordered
      list of applicable tables
    - Registry is the **authoritative source** for which solutions to apply
  - Apply calibration tables from registry to all 10 MS files:
    - Apply `.bpcal` if valid BP table found in registry for MS observation time
    - Apply `.gpcal` and `.2gcal` if valid G tables found in registry for MS
      observation time
  - Update products database: `stage="calibrated"`, `cal_applied=1`

### 6. Individual Imaging

- **Input**: All 10 calibrated MS files
- **Action**:
  - Image each MS individually
  - Primary beam correction applied
  - Update products database: `stage="imaged"`, `status="done"`,
    `imagename=<path>`

### 7. Mosaic Generation

- **Input**: 10 individual images (tiles)
- **Action**:
  - Create weighted mosaic from 10 tiles
  - Register mosaic in products database
  - Mark MS files as `stage="mosaicked"`

### 8. Sliding Window for Next Mosaic

- **Trigger**: When 8 additional MS files are registered (total 18 MS)
- **Action**:
  - **Last 2 MS** from previous group become **first 2 MS** of next group
  - Clear calibration tables from these 2 MS (remove `.bpcal`, `.gpcal`,
    `.2gcal` if present)
  - Form new group of 10 MS: [last 2 from previous] + [8 new MS]
  - Use **5th MS** (middle by time) of new group for calibration solving
  - Repeat steps 4-7

## Key Design Principles

### Overarching Strategy

**Solutions should be generated and applied such that they fall roughly in the
middle of their application windows:**

- **Bandpass**: Generated at calibrator transit, applied over 24-hour window
  (±12 hours)
- **Gain**: Generated from middle MS (5th of 10), applied over 1-hour window
  (±30 minutes)

This ensures optimal calibration quality by centering solutions within their
validity periods.

### Overlap Strategy

- Each mosaic shares **2 tiles** with the previous mosaic

---

## Directory Organization

The pipeline automatically organizes files into a hierarchical structure for
efficient management and recovery.

### MS File Organization

MS files are organized by type and date:

```
/stage/dsa110-contimg/ms/
├── calibrators/                    # Calibrator observations
│   └── YYYY-MM-DD/                 # Organized by date
│       ├── <timestamp>.ms/         # Calibrator MS file (CASA directory)
│       ├── <timestamp>_bpcal/      # Bandpass calibration table (CASA directory)
│       ├── <timestamp>_gpcal/       # Gain phase calibration table (CASA directory)
│       └── <timestamp>_2gcal/      # Short-timescale gain table (CASA directory)
│
├── science/                        # Science observations
│   └── YYYY-MM-DD/                 # Organized by date
│       └── <timestamp>.ms/         # Science MS with CORRECTED_DATA (CASA directory)
│
└── failed/                         # Failed conversions (quarantine)
    └── YYYY-MM-DD/                 # Organized by date
        └── <timestamp>.ms/         # Partial/corrupted MS (CASA directory)
```

**Organization Rules:**

- Calibrator MS files are moved to `calibrators/YYYY-MM-DD/` after successful
  calibration solving
- Science MS files are moved to `science/YYYY-MM-DD/` after successful
  calibration application
- Failed MS files are moved to `failed/YYYY-MM-DD/` for manual review
- Calibration tables are stored alongside their corresponding calibrator MS
  files

### Image Organization

Images are stored in a dedicated directory:

```
/stage/dsa110-contimg/images/
└── <timestamp>.img-*/              # Image files (WSClean/CASA format)
    ├── <timestamp>.img-image-pb.fits # Primary beam corrected image (WSClean)
    ├── <timestamp>.img.pbcor        # Primary beam corrected image (CASA)
    └── <timestamp>.img.image        # Image (CASA)
```

### Mosaic Organization

Mosaics are stored in a dedicated directory:

```
/stage/dsa110-contimg/mosaics/
└── <mosaic_name>.fits              # Combined mosaic images
```

### Storage Location Registration

The pipeline maintains a two-level registry system for tracking file locations:

#### 1. Base Directory Registration (`storage_locations` table in `products.sqlite3`)

Tracks where different file types are stored:

- `ms_files` → `/stage/dsa110-contimg/ms/`
- `calibration_tables` → `/stage/dsa110-contimg/ms/calibrators/`
- `science_ms` → `/stage/dsa110-contimg/ms/science/`
- `failed_ms` → `/stage/dsa110-contimg/ms/failed/`
- `images` → `/stage/dsa110-contimg/images/`
- `mosaics` → `/stage/dsa110-contimg/mosaics/`

Registered automatically when `StreamingMosaicManager` initializes.

#### 2. Individual File Path Tracking

**MS Files** (`ms_index` table in `products.sqlite3`):

- Tracks full path of each MS file
- Path updated when files are moved via `_organize_ms_file()`
- Example: `/stage/dsa110-contimg/ms/science/2025-10-29/2025-10-29T13:54:17.ms`

**Calibration Tables** (`cal_registry.sqlite3`):

- Tracks individual calibration table paths
- Uses `register_set_from_prefix()` which finds tables matching prefix pattern
- Stores full organized path:
  `/stage/dsa110-contimg/ms/calibrators/2025-10-29/2025-10-29T13:54:17_0~23_bpcal`

**Recovery:**

- Query `storage_locations` to find base directories
- Query `ms_index` for individual MS file paths
- Query `cal_registry` for calibration table paths
- All paths reflect the organized directory structure
- This ensures continuity and smooth transitions between mosaics
- The overlap tiles are re-calibrated using the new group's calibration solution

### Calibration Validity Windows

#### Bandpass Calibration

- **Window**: 24 hours centered on calibrator transit
  - Start: 12 hours BEFORE transit
  - End: 12 hours AFTER transit
- **Rationale**: Solution generated at transit time falls in the middle of the
  24-hour application window
- **New Calibrator Transition**:
  - When pointing Dec changes and new calibrator is chosen
  - First transit starts "1st day" period ending 12 hours after that transit
  - After "1st day", regular 24-hour intervals resume (centered on subsequent
    transits)

#### Gain Calibration

- **Window**: 1 hour centered on 5th MS observation time
  - Start: 30 minutes BEFORE 5th MS `mid_mjd`
  - End: 30 minutes AFTER 5th MS `mid_mjd`
- **Rationale**: Solution generated from middle MS falls in the middle of the
  1-hour application window

#### Registry Integration

- **Registry as Authoritative Source**: The calibration registry is the **single
  source of truth** for determining which calibration solutions to apply
- **Validity Window Queries**: For each MS, query registry by observation time
  (`mid_mjd`) to find tables whose validity windows include the MS time:
  ```python
  applylist = get_active_applylist(registry_db, ms_mid_mjd)
  ```
- **Validity Window Storage**: Registry tracks `valid_start_mjd` and
  `valid_end_mjd` for each calibration table:
  - Bandpass: ±12 hours around calibrator transit (or first transit special
    case)
  - Gain: ±30 minutes around 5th MS observation time
- **Solution Selection Logic**:
  - Query registry for each MS's observation time
  - Registry returns ordered list of valid calibration tables
  - Apply tables in order: BP → GP → 2G (if present and valid)
  - If no valid tables found in registry, skip calibration or flag for manual
    review

### State Tracking

- Products database tracks MS state: `staging` → `converted` → `calibrated` →
  `imaged` → `mosaicked`
- Registry tracks calibration table validity windows
- Groups are tracked to ensure proper sequencing

## Database Schema Requirements

### Products Database (`ms_index` table)

- `stage`: Current pipeline stage (`staging`, `converted`, `calibrated`,
  `imaged`, `mosaicked`)
- `status`: Processing status (`converted`, `done`, `failed`)
- `cal_applied`: Flag indicating if calibration was applied
- `imagename`: Path to image created from MS
- `mid_mjd`: Observation midpoint time (for ordering)

### New Table: `mosaic_groups`

```sql
CREATE TABLE IF NOT EXISTS mosaic_groups (
    group_id TEXT PRIMARY KEY,
    mosaic_id TEXT,
    ms_paths TEXT,  -- JSON array of MS paths
    calibration_ms_path TEXT,  -- Path to MS used for calibration solving
    bpcal_solved INTEGER DEFAULT 0,
    created_at REAL NOT NULL,
    calibrated_at REAL,
    imaged_at REAL,
    mosaicked_at REAL,
    status TEXT DEFAULT 'pending'  -- pending, calibrated, imaged, mosaicked, completed
)
```

## Implementation Notes

### Registry-First Approach

- **Always query registry first** before solving calibration
- Registry determines which solutions to apply based on validity windows
- Only solve new calibration if registry has no valid solutions for the
  observation time
- Registry registration must include accurate validity windows for proper
  solution selection

### Calibration MS Selection

- Sort MS files by `mid_mjd` (observation time)
- Select MS at index 4 (0-indexed, so 5th MS)
- This ensures calibration represents the middle of the observation window
- When querying registry, use this 5th MS `mid_mjd` to check for existing valid
  solutions

### Calibrator Detection and Transit Calculation

- Query VLA catalog for calibrators valid for the current pointing (Dec)
- Check if any MS in the group contains a calibrator field
- Use field selection logic to identify calibrator presence
- **Transit Time Calculation**:
  - Calculate calibrator transit time for the observation date
  - Transit occurs when calibrator RA matches local sidereal time
  - Use `astropy` or similar to compute transit MJD

### Validity Window Calculation

#### Bandpass Validity Window

```python
transit_mjd = calculate_calibrator_transit(calibrator_ra, observation_date)
valid_start_mjd = transit_mjd - 0.5  # 12 hours before transit
valid_end_mjd = transit_mjd + 0.5    # 12 hours after transit
```

#### Gain Validity Window

```python
calibration_ms_mid_mjd = extract_ms_time_range(calibration_ms_path)[2]  # 5th MS
valid_start_mjd = calibration_ms_mid_mjd - (30 / 1440.0)  # 30 minutes before
valid_end_mjd = calibration_ms_mid_mjd + (30 / 1440.0)    # 30 minutes after
```

#### New Calibrator Transition Handling

- Detect when pointing Dec changes (new calibrator selected)
- For first transit of new calibrator:
  - `valid_start_mjd = transit_mjd` (starts at transit, not 12h before)
  - `valid_end_mjd = transit_mjd + 0.5` (ends 12h after transit)
- For subsequent transits:
  - Use standard ±12 hour window centered on transit

### Calibration Table Clearing

- When reusing MS files for next mosaic:
  - **Registry-Based Approach**: The registry automatically handles validity -
    old tables outside validity windows won't be selected
  - **Physical Table Cleanup** (optional): Remove calibration tables: `*_bpcal`,
    `*_gpcal`, `*_2gcal` from overlap MS files
  - **Registry Status Update**: Mark old tables as `status="retired"` in
    registry (or let validity windows expire naturally)
  - Clear `cal_applied` flag in products database
  - **New Calibration**: When overlap MS files are processed in new group,
    registry will return new valid solutions based on new observation times
  - This ensures overlap tiles are re-calibrated with the new group's solutions
    via registry queries

### Error Handling

- If calibration solving fails: mark group as `status="calibration_failed"`
- If imaging fails for individual MS: mark that MS as `status="failed"`,
  continue with others
- If mosaic generation fails: mark group as `status="mosaic_failed"`
- If registry query fails: log error, fall back to solving new calibration
  (don't skip calibration entirely)

## Registry Query Workflow Summary

### For Each MS File:

1. **Extract observation time**: Get `mid_mjd` from MS metadata
2. **Query registry**: `applylist = get_active_applylist(registry_db, mid_mjd)`
3. **Check results**:
   - If `applylist` is empty → solve new calibration
   - If `applylist` contains tables → use those tables (skip solving)
4. **Apply calibration**: Use tables from registry (or newly solved tables)
5. **Register new tables**: If new calibration solved, register with proper
   validity windows

### For Calibration Solving (5th MS):

1. **Query registry first**: Check if valid solutions exist for 5th MS `mid_mjd`
2. **If valid solutions found**: Skip solving, use registry tables
3. **If no valid solutions**: Solve new calibration
4. **Register new solutions**: Store with transit-centered validity windows (BP)
   or time-centered windows (G)

## API/CLI Integration

### New Commands Needed

- `streaming-mosaic process`: Main processing loop
- `streaming-mosaic check-groups`: Check if groups are ready for processing
- `streaming-mosaic clear-calibration`: Clear calibration from MS files (for
  overlap)

### Monitoring

- Track number of MS files in staging
- Track group formation progress
- Monitor calibration solving success rates
- Track mosaic generation completion

## Future Enhancements

- Parallel processing of multiple groups
- Automatic retry for failed calibrations
- Quality checks before mosaic generation
- Mosaic validation and metrics
