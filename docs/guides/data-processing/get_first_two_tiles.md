# Getting First Two Tiles from Earliest Calibrator Validity Window

**Purpose**: This guide explains how to automatically find and use the first two
tiles from the first validity window of the calibrator assigned to the
declination of your earliest observations.

**Location**: `docs/how-to/get_first_two_tiles_from_earliest_calibrator.md`

## Overview

This workflow is useful when you want to:

- Process the earliest available data in your system
- Use the calibrator automatically assigned to that data's declination
- Get tiles from the first validity window (first transit) of that calibrator
- Create a 2-tile mosaic from those tiles

## Prerequisites

1. **Earliest observations exist** in `/data/incoming` (HDF5 files)
2. **Calibrator registered** for the declination of your earliest observations
3. **Tiles processed** (converted → calibrated → imaged) in the validity window
4. **Casa6 environment** activated

## Quick Start

### Step 1: Find and Get First Two Tiles

Run the script to automatically find everything:

```bash
cd /data/dsa110-contimg
source scripts/developer-setup.sh  # Ensures casa6 environment

/opt/miniforge/envs/casa6/bin/python scripts/get_first_two_tiles_from_earliest_calibrator_window.py \
    --data-dir /data/incoming \
    --products-db state/products.sqlite3 \
    --max-days-back 60 \
    --output /tmp/first_two_tiles.txt
```

**What this does:**

1. Scans `/data/incoming` for earliest HDF5 observation files
2. Extracts declination from the earliest observation
3. Looks up the calibrator registered for that declination
4. Finds the first transit/validity window for that calibrator
5. Queries the products database for the first 2 tiles in that window
6. Saves tile paths to output file (optional)

### Step 2: Verify Tiles

Check the output:

```bash
cat /tmp/first_two_tiles.txt
```

You should see two tile paths, for example:

```
/stage/dsa110-contimg/images/2025-01-15T13:00:00.image
/stage/dsa110-contimg/images/2025-01-15T13:05:00.image
```

### Step 3: Create 2-Tile Mosaic

Use the tile paths to create a mosaic. You have two options:

#### Option A: Direct Mosaic Build (Python)

```python
#!/usr/bin/env python3
"""Build 2-tile mosaic from first two tiles."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dsa110_contimg.mosaic.cli import _build_weighted_mosaic_linearmosaic
from dsa110_contimg.mosaic.validation import TileQualityMetrics

# Read tile paths from file
with open("/tmp/first_two_tiles.txt") as f:
    tiles = [line.strip() for line in f if line.strip()]

print(f"Building mosaic from {len(tiles)} tiles:")
for i, tile in enumerate(tiles, 1):
    print(f"  {i}. {Path(tile).name}")

# Create metrics dict
metrics_dict = {t: TileQualityMetrics(tile_path=t) for t in tiles}

# Build mosaic
output_path = "/stage/dsa110-contimg/mosaics/first_two_tile_mosaic"

_build_weighted_mosaic_linearmosaic(
    tiles=tiles,
    metrics_dict=metrics_dict,
    output_path=output_path
)

print(f"\n✓ Mosaic built: {output_path}")
```

#### Option B: Using Mosaic CLI (After Planning)

If tiles are already in the products database, you can plan and build:

```bash
# Get the validity window times from script output, then:
SINCE=$(date -u -d '2025-01-15 13:00:00' +%s)  # Adjust to your validity window start
UNTIL=$(date -u -d '2025-01-15 13:10:00' +%s)   # Adjust to your validity window end

# Plan mosaic (will include all tiles in window, but we'll limit to 2)
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.mosaic.cli plan \
    --products-db state/products.sqlite3 \
    --name first_two_tiles_mosaic \
    --since "$SINCE" \
    --until "$UNTIL" \
    --method pbweighted

# Build mosaic
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.mosaic.cli build \
    --products-db state/products.sqlite3 \
    --name first_two_tiles_mosaic \
    --output /stage/dsa110-contimg/mosaics/first_two_tiles_mosaic
```

**Note**: The CLI approach will include all tiles in the window. To limit to
exactly 2 tiles, use Option A or modify the plan query.

## Understanding the Workflow

### 1. Earliest Observations

The script finds the earliest HDF5 files in `/data/incoming` by:

- Scanning the directory for `*_sb*.hdf5` files
- Using `fetch_observation_timeline()` to get the earliest timestamp
- Selecting the first file matching that timestamp

### 2. Declination Extraction

Declination is extracted from the HDF5 file using:

- `load_pointing()` function (handles both MS and UVH5)
- Fallback to direct HDF5 header reading via `_peek_uvh5_phase_and_midtime()`

### 3. Calibrator Lookup

The script uses `StreamingMosaicManager.get_bandpass_calibrator_for_dec()` to:

- Query the `bandpass_calibrators` table in products database
- Find active calibrator registered for the declination range
- Return calibrator name, RA/Dec, and Dec range

**Important**: If no calibrator is found, you need to register one:

```bash
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.mosaic.cli register-bp-calibrator \
    --calibrator "0834+555,129.0,-30.0" \
    --dec-tolerance 5.0
```

### 4. First Validity Window

For the **first transit** of a calibrator, the validity window is:

- **Start**: Transit time
- **End**: Transit time + 12 hours

This differs from subsequent transits, which use ±12 hours (24-hour window
centered on transit).

The script:

- Uses `CalibratorMSGenerator.list_available_transits()` to find all transits
- Selects the earliest transit (last in the list, since sorted most recent
  first)
- Calculates the validity window

### 5. Tile Selection

Tiles are queried from the `images` table in products database:

- Filter by `created_at` within validity window
- Filter by `pbcor = 1` (PB-corrected tiles only)
- Order by `created_at ASC` (chronological)
- Limit to first 2 tiles

## Troubleshooting

### No Calibrator Found

**Error**: `✗ No calibrator registered for Dec = X.XXXXXX°`

**Solution**: Register a calibrator for this declination:

```bash
# Find appropriate calibrator for your Dec range
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.calibration.cli find-calibrators \
    --dec-deg <YOUR_DEC> \
    --radius-deg 2.0

# Register the calibrator
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.mosaic.cli register-bp-calibrator \
    --calibrator "<NAME>,<RA_DEG>,<DEC_DEG>" \
    --dec-tolerance 5.0
```

### No Tiles Found in Validity Window

**Error**: `✗ No tiles found in validity window`

**Possible causes:**

1. Observations haven't been processed yet (convert → calibrate → image)
2. Tiles exist but aren't PB-corrected (`pbcor = 0`)
3. Tiles exist but timestamps are outside validity window

**Solution**: Process observations in the validity window:

```bash
# Convert HDF5 to MS
/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-01-15 13:00:00" \
    "2025-01-16 01:00:00" \
    --writer parallel-subband

# Calibrate and image (see batch_mode_guide.md for details)
```

### Only One Tile Found

**Warning**: `⚠ Only 1 tile(s) found (expected 2)`

**Solution**: The validity window may only contain one observation. You can:

1. Expand the search window (increase `--max-days-back`)
2. Use the single tile for a 1-tile "mosaic" (not recommended)
3. Wait for more observations to be processed

## Example Output

```
======================================================================
Step 1: Finding earliest observations in /data/incoming
======================================================================
✓ Earliest observation time: 2025-01-15T13:00:00.000
  Total files: 1234
  Unique timestamps: 89
✓ Using file: 2025-01-15T13:00:00_sb00.hdf5

======================================================================
Step 2: Extracting declination from earliest observation
======================================================================
✓ Declination extracted: -30.123456°

======================================================================
Step 3: Finding calibrator for Dec = -30.123456°
======================================================================
✓ Found calibrator: 0834+555
  RA: 129.000000°
  Dec: -30.000000°
  Dec range: [-35.00°, -25.00°]

======================================================================
Step 4: Finding first validity window for 0834+555
======================================================================
Searching for available transits (max 60 days back)...
✓ Found 12 transits with data
✓ First transit: 2025-01-15T13:30:00.000
  Group ID: 2025-01-15T13:30:00
  Files: 16 subband files

✓ First validity window:
  Start: 2025-01-15T13:30:00.000
  End: 2025-01-16T01:30:00.000
  Duration: 12 hours

======================================================================
Step 5: Getting first two tiles from validity window
======================================================================
Querying tiles from 2025-01-15T13:30:00.000 to 2025-01-16T01:30:00.000
  1. 2025-01-15T13:30:00.image
     Created: 2025-01-15T13:35:00.000
     PB-corrected: 1
  2. 2025-01-15T13:35:00.image
     Created: 2025-01-15T13:40:00.000
     PB-corrected: 1

✓ Found 2 tile(s) in validity window

======================================================================
Summary
======================================================================
Earliest observation: 2025-01-15T13:00:00.000
Declination: -30.123456°
Calibrator: 0834+555
First validity window: 2025-01-15T13:30:00.000 to 2025-01-16T01:30:00.000
First 2 tile(s):
  1. /stage/dsa110-contimg/images/2025-01-15T13:30:00.image
  2. /stage/dsa110-contimg/images/2025-01-15T13:35:00.image

✓ Tile paths saved to: /tmp/first_two_tiles.txt

✓ Success!
```

## Related Documentation

- [Batch Mode Guide](../workflow/batch_mode_guide.md) - Complete batch processing workflow
- [Mosaic Quickstart](../workflow/mosaic_quickstart.md) - Basic mosaic creation
- [Streaming Mosaic Workflow](../../architecture/pipeline/STREAMING_MOSAIC_WORKFLOW.md) -
  Validity window details
- [Calibration Validity Windows](../../architecture/pipeline/STREAMING_MOSAIC_WORKFLOW.md#calibration-validity-windows) -
  Window calculation rules

## Script Reference

**Script**: `scripts/get_first_two_tiles_from_earliest_calibrator_window.py`

**Arguments**:

- `--data-dir`: Directory with HDF5 files (default: `/data/incoming`)
- `--products-db`: Products database path (default: `state/products.sqlite3`)
- `--max-days-back`: Days to search for transits (default: 60)
- `--output`: Optional file to save tile paths

**Exit codes**:

- `0`: Success
- `1`: Failure (see error messages)
