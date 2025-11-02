# Creating Hour-Long Mosaic for Most Recent 0834 Transit

## Analysis Date: 2025-01-XX

## 1. Pipeline Workflow Identification

### Available Components

The pipeline has the following components that can be used to create an hour-long mosaic:

#### A. Transit Finding
- **Script**: `scripts/find_latest_transit_group.py`
  - Finds the most recent transit for a calibrator by name
  - Searches up to `max_days_back` days (default: 14)
  - Returns transit ISO time, group ID, and file list
  - Usage: `python scripts/find_latest_transit_group.py --name 0834+555`

#### B. Mosaic Building
- **Script**: `ops/pipeline/build_transit_mosaic.py`
  - Builds 1-hour mosaic around a transit time
  - Creates 12 groups at 5-minute cadence (±30 minutes)
  - Converts UVH5 → MS → Images → Mosaic
  - **Limitation**: Requires manual specification of transit time or curated subdirectory

#### C. Mosaic CLI
- **Module**: `src/dsa110_contimg/mosaic/cli.py`
  - `plan`: Creates mosaic plan from products DB tiles
  - `build`: Builds mosaic using CASA immath (mean combination)

### Workflow Steps

To create an hour-long mosaic of the most recent 0834 transit, the workflow would be:

1. **Find Transit Time**
   ```bash
   python scripts/find_latest_transit_group.py \
     --name 0834+555 \
     --input-dir /data/incoming \
     --max-days-back 14
   ```
   This returns JSON with `transit_iso` (e.g., "2025-01-15T14:23:45.123")

2. **Build Mosaic** (Option A: Using existing script)
   ```bash
   python ops/pipeline/build_transit_mosaic.py \
     --center 2025-01-15T14:23:45 \
     --incoming-dir /data/incoming \
     --output-dir state/mosaics/0834_555 \
     --products-db state/products.sqlite3
   ```

3. **Alternative: Manual Process** (Option B: Step-by-step)
   - Convert groups: Use `hdf5_orchestrator` or `direct_subband` writer
   - Calibrate: Apply calibration tables
   - Image: Use `imaging.cli.image_ms()` for each MS
   - Plan mosaic: `python -m dsa110_contimg.mosaic.cli plan --since <epoch> --until <epoch>`
   - Build mosaic: `python -m dsa110_contimg.mosaic.cli build --name <name>`

## 2. Missing Code Analysis

### Gap Identified: **Automated Transit Mosaic Builder**

**Problem**: The existing `build_transit_mosaic.py` script requires manual specification of:
- Transit time (`--center` argument), OR
- Curated subdirectory (`--transit-subdir`)

**What's Missing**: A script that:
1. Automatically finds the most recent transit for a calibrator
2. Extracts the transit time
3. Calls `build_transit_mosaic.py` (or equivalent workflow) with that time

### Proposed Solution

Create a new wrapper script that combines transit finding with mosaic building:

**File**: `ops/pipeline/build_latest_transit_mosaic.py`

**Features**:
- Takes calibrator name (e.g., "0834+555" or "0834")
- Calls `find_latest_transit_group()` to get transit time
- Extracts transit ISO time from result
- Calls `build_transit_mosaic.py` with `--center` argument
- Handles errors gracefully (no transit found, missing data, etc.)

**Alternative**: Enhance `build_transit_mosaic.py` to:
- Accept `--calibrator-name` argument
- If `--center` not provided, automatically find latest transit
- Fall back to curated subdirectory if transit not found

### Additional Considerations

#### Calibrator Name Format
- The catalog uses "0834+555" format (with "+" separator)
- Code handles case-insensitive matching and stripping
- Should verify name format in catalog

#### Data Availability
- Need to verify data exists for the 1-hour window (±30 minutes)
- Current scripts check for file existence but don't handle partial groups gracefully
- May need to handle cases where <12 groups are available

#### Calibration Application
- `build_transit_mosaic.py` images groups but doesn't explicitly apply calibration
- **Note**: `image_ms()` function automatically detects and uses `CORRECTED_DATA` if present (via `_detect_datacolumn()`)
- If MS files don't have `CORRECTED_DATA`, imaging will use raw `DATA` column
- **Recommendation**: Explicitly apply calibration before imaging OR verify MS files have `CORRECTED_DATA` populated
- Alternative: Use `imaging.worker.process_once()` which applies calibration via `apply_to_target()` before imaging

#### Time Window Logic
- Current `build_transit_mosaic.py` uses hardcoded ±30 minutes (12 groups)
- Should verify transit time precision matches 5-minute cadence
- May need to align transit time to nearest 5-minute boundary

## 3. Recommended Implementation

### Option 1: Enhanced Existing Script (Recommended)

Modify `ops/pipeline/build_transit_mosaic.py` to:
- Add `--calibrator-name` argument
- If `--center` not provided, call `find_latest_transit_group()` internally
- Use transit ISO time from result
- Improve error handling for missing data

**Pros**:
- Minimal code changes
- Backward compatible (existing `--center` still works)
- Reuses existing transit finding logic

### Option 2: New Wrapper Script

Create `ops/pipeline/build_latest_transit_mosaic.py` that:
- Imports and calls `find_latest_transit_group()` and `build_transit_mosaic.main()`
- Provides clean CLI interface
- Handles transit finding → mosaic building pipeline

**Pros**:
- Clear separation of concerns
- Doesn't modify existing working script
- Easy to test transit finding separately

## 4. Code Verification Checklist

Before implementation, verify:

- [ ] Calibrator name format: Test with "0834+555" and "0834"
- [ ] Transit finding: Verify `find_latest_transit_group()` returns correct format
- [ ] Time window: Confirm ±30 minutes matches 12 groups at 5-minute cadence
- [ ] File existence: Check that groups exist for the hour window
- [ ] Calibration: Verify calibration tables are applied before imaging
- [ ] Mosaic consistency: Ensure tiles have consistent grids/cell sizes
- [ ] Error handling: Test with missing data, no transit found scenarios

## 5. Current Workflow (Manual)

For immediate use, manual steps:

```bash
# Step 1: Find latest transit
TRANSIT_INFO=$(python scripts/find_latest_transit_group.py \
  --name 0834+555 \
  --input-dir /data/incoming \
  --max-days-back 14)

# Step 2: Extract transit time (requires jq or manual parsing)
TRANSIT_TIME=$(echo $TRANSIT_INFO | jq -r '.transit_iso' | cut -d'T' -f1,2 | sed 's/T/ /')

# Step 3: Build mosaic
python ops/pipeline/build_transit_mosaic.py \
  --center "$TRANSIT_TIME" \
  --incoming-dir /data/incoming \
  --output-dir state/mosaics/0834_555 \
  --products-db state/products.sqlite3 \
  --name 0834+555
```

## 6. Summary

**What Works Now**:
- Transit finding: ✓ Available (`find_latest_transit_group.py`)
- Mosaic building: ✓ Available (`build_transit_mosaic.py`)
- Mosaic CLI: ✓ Available (`mosaic.cli`)

**What's Missing**:
- ✗ Automated integration: No script that combines transit finding + mosaic building
- ✗ Error handling: Limited handling for missing data or partial groups
- ✗ Calibration verification: No explicit check that calibration is applied

**Recommendation**: Enhance `build_transit_mosaic.py` with `--calibrator-name` option that automatically finds the latest transit if `--center` is not provided.
