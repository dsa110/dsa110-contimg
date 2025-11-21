# Transit Search Process - Step-by-Step Explanation

## Overview

The transit search process finds when a calibrator source (e.g., "0834+555")
transits the meridian and matches it to available observation data. This is used
to create mosaics centered on calibrator transits.

## High-Level Flow

```
1. User requests mosaic for calibrator (e.g., "0834+555")
2. Calculate theoretical transit times
3. Search for observation groups near transit times
4. Validate transit matches (time + declination + primary beam)
5. Select best matching group
6. Create time window centered on transit
7. Find MS files in that window
```

---

## Step-by-Step Details

### Step 1: Calculate Theoretical Transit Times

**Location**: `dsa110_contimg/calibration/schedule.py`

**Function**: `previous_transits(ra_deg, start_time, n)`

**Process**:

1. **Input**: Calibrator RA (right ascension) in degrees
2. **Calculate next transit**: Uses `next_transit_time()` which:
   - Converts RA to hours
   - Gets Local Sidereal Time (LST) at start time
   - Calculates when LST = RA (meridian transit)
   - Iteratively refines to find exact transit time
3. **Step backward**: Steps back in 1 sidereal-day increments to get previous
   transits
4. **Output**: List of `Time` objects representing transit times

**Key Formula**:

```
Transit occurs when: LST = RA (modulo 24 hours)
Sidereal day = 1.0 / SIDEREAL_RATE ≈ 0.99727 solar days
```

**Example**:

- Calibrator "0834+555" has RA ≈ 8.58 hours
- Transit occurs when LST = 8.58 hours
- Previous transits are 1 sidereal day apart

---

### Step 2: List Available Transits with Data

**Location**: `dsa110_contimg/conversion/calibrator_ms_service.py`

**Function**: `list_available_transits(calibrator_name, max_days_back)`

**Process**:

1. **Load calibrator coordinates**:
   - RA and Dec from catalog (e.g., VLA catalog)
   - Example: "0834+555" → RA=8.58°, Dec=55.57°

2. **Calculate search window**:
   - Start: `Time.now() - max_days_back days`
   - End: `Time.now()`
   - Cutoff: Filter out groups older than cutoff

3. **Query database for complete groups**:
   - Query `products_db` for 16-subband groups in time range
   - Groups must be complete (all 16 subbands present)
   - Uses `query_subband_groups()` function

4. **Get theoretical transits**:
   - Calls `previous_transits(ra_deg, start_time=Time.now(), n=max_days_back)`
   - Gets list of transit times going back `max_days_back` days

5. **Match transits to groups**:
   - For each transit, find groups whose observation window contains the transit
   - Calls `_process_transits_for_available_data()`

**Output**: List of transit info dicts, sorted by most recent first:

```python
{
    'transit_iso': '2025-11-07T13:19:23.000',
    'transit_mjd': 60345.555,
    'group_id': '2025-11-07T13:19:23',
    'group_mid_iso': '2025-11-07T13:19:25.000',
    'delta_minutes': 0.033,  # Time difference between group mid and transit
    'subband_count': 16,
    'files': [...],  # List of 16 HDF5 file paths
    'days_ago': 9,
    'has_ms': False
}
```

---

### Step 3: Find Transit-Centered Window

**Location**: `dsa110_contimg/mosaic/orchestrator.py`

**Function**: `find_transit_centered_window(calibrator_name, timespan_minutes)`

**Process**:

1. **Get available transits**:
   - Calls
     `calibrator_service.list_available_transits(calibrator_name, max_days_back=60)`
   - Gets list of transits with available data

2. **Select earliest transit**:
   - List is sorted most recent first
   - Takes last element (earliest transit): `earliest_transit = transits[-1]`
   - Extracts transit time: `transit_time = Time(transit_iso)`

3. **Calculate time window**:
   - Window centered on transit time
   - Half-span:
     `half_span = TimeDelta(timespan_minutes / 2.0 * 60, format="sec")`
   - Start: `start_time = transit_time - half_span`
   - End: `end_time = transit_time + half_span`

4. **Get calibrator declination**:
   - Loads Dec from catalog:
     `_, dec_deg = calibrator_service._load_radec(calibrator_name)`

5. **Count available MS files**:
   - Queries `ms_index` table for MS files in window:
     ```sql
     SELECT COUNT(*) FROM ms_index
     WHERE mid_mjd >= ? AND mid_mjd <= ?
     AND status IN ('converted', 'calibrated', 'imaged', 'done')
     ```

**Output**: Window info dict:

```python
{
    'transit_time': Time('2025-11-07T13:19:23'),
    'start_time': Time('2025-11-07T13:13:23'),  # 6 min before transit
    'end_time': Time('2025-11-07T13:25:23'),     # 6 min after transit
    'dec_deg': 55.57,
    'bp_calibrator': '0834+555',
    'ms_count': 3  # Number of MS files in window
}
```

---

### Step 4: Process Single Transit (Validation)

**Location**: `dsa110_contimg/conversion/calibrator_ms_service.py`

**Function**:
`_process_single_transit(t, calibrator_name, ra_deg, dec_deg, window_minutes, ...)`

**Process**:

1. **Calculate search window**:
   - `t0, t1 = _calculate_transit_window(t, window_minutes)`
   - Window: `transit ± (window_minutes / 2)`

2. **Query for groups in window**:
   - `groups = query_subband_groups(products_db, t0, t1, tolerance_s=1.0)`
   - Finds all 16-subband groups whose observation time overlaps the window

3. **Find best candidate group**:
   - Calls `_find_best_candidate_group(groups, t)`
   - Selects group whose mid-time is closest to transit time
   - Returns: `(delta_minutes, best_group, group_mid_time)`

4. **Validate complete subband group**:
   - Checks if group has all 16 subbands:
     `_is_complete_subband_group(best_group)`
   - If incomplete, rejects transit

5. **Validate primary beam response**:
   - Calls
     `_validate_primary_beam(group_file, ra_deg, dec_deg, min_pb_response, freq_ghz)`
   - Calculates primary beam response at calibrator position
   - Requires `pb_response >= min_pb_response` (default: 0.3 = 30%)
   - If below threshold, rejects transit

6. **Build result dict**:
   - If all validations pass, returns transit info dict

**Validation Criteria**:

- ✅ Group exists in time window
- ✅ Group has all 16 subbands
- ✅ Primary beam response ≥ 30% at calibrator position
- ✅ Group mid-time closest to transit

---

### Step 5: Match Transit to Group (Detailed)

**Location**: `dsa110_contimg/conversion/calibrator_ms_service.py`

**Function**:
`_match_transit_to_group(transit, group_files, group_id, dec_deg, ...)`

**Process**:

1. **Parse group start time**:
   - Group ID is timestamp: `group_start = Time(group_id)`
   - Example: `group_id = "2025-11-07T13:19:23"`

2. **Extract group metadata**:
   - Reads HDF5 file to get actual mid-time and declination
   - `group_mid, pt_dec_deg = _extract_group_time_and_dec(group_files, group_id)`
   - Opens first HDF5 file and reads metadata

3. **Validate transit in window**:
   - Checks if transit falls within group's observation window
   - Window: `[group_start, group_start + filelength]` (typically 5 minutes)
   - Transit must be within this window

4. **Check declination match**:
   - Compares group declination to expected calibrator declination
   - **Warning only** (doesn't filter): Logs if difference > tolerance
   - This is why you see warnings like:
     ```
     WARNING - Group 2025-11-07T13:19:23 transit time matches but declination mismatch:
     file dec=50.18°, expected 55.57° (diff=5.39°). Trusting transit time match.
     ```

5. **Validate complete subband group**:
   - Ensures all 16 subbands are present
   - Files must be sorted by subband number

6. **Calculate time difference**:
   - `dt_min = abs((group_mid - transit).to(u.min).value)`
   - Time difference between group mid-time and transit time

**Output**: Transit match dict or None:

```python
{
    'group_id': '2025-11-07T13:19:23',
    'group_mid': Time('2025-11-07T13:19:25'),
    'group_files_sorted': [...],  # 16 files sorted by subband
    'delta_minutes': 0.033  # How close group mid is to transit
}
```

---

### Step 6: Validate Transit in Window

**Location**: `dsa110_contimg/conversion/calibrator_ms_service.py`

**Function**: `_validate_transit_in_window(group_id, transit, filelength)`

**Process**:

1. **Parse group start time**: `group_start = Time(group_id)`
2. **Calculate group end time**: `group_end = group_start + filelength`
3. **Check overlap**:
   - Transit must fall within `[group_start, group_end]`
   - Uses overlap logic: `(group_start <= transit) and (transit <= group_end)`

**Purpose**: Ensures the transit actually occurred during the observation
window.

---

### Step 7: Primary Beam Validation

**Location**: `dsa110_contimg/conversion/calibrator_ms_service.py`

**Function**:
`_validate_primary_beam(group_file, ra_deg, dec_deg, min_pb_response, freq_ghz)`

**Process**:

1. **Read pointing from HDF5 file**:
   - Extracts telescope pointing (RA, Dec) from file metadata
   - Gets frequency information

2. **Calculate angular separation**:
   - Distance between calibrator position and pointing center
   - `separation = angular_distance(calibrator_ra, calibrator_dec, pointing_ra, pointing_dec)`

3. **Calculate primary beam response**:
   - Uses primary beam model (typically Gaussian or Airy pattern)
   - Response depends on:
     - Angular separation from pointing center
     - Frequency (affects beam size)
   - Formula: `pb_response = f(separation, freq_ghz)`

4. **Check threshold**:
   - Requires `pb_response >= min_pb_response` (default: 0.3 = 30%)
   - If below threshold, calibrator is too far from pointing center

**Purpose**: Ensures calibrator is actually in the primary beam (not just near
transit time).

---

### Step 8: Find Best Candidate Group

**Location**: `dsa110_contimg/conversion/calibrator_ms_service.py`

**Function**: `_find_best_candidate_group(groups, transit)`

**Process**:

1. **For each group**:
   - Extract group mid-time
   - Calculate time difference:
     `dt_min = abs((group_mid - transit).to(u.min).value)`

2. **Select best**:
   - Group with smallest `dt_min` (closest to transit)
   - Returns: `(dt_min, best_group, group_mid)`

**Purpose**: If multiple groups exist in the window, pick the one whose
observation time is closest to the transit time.

---

## Complete Flow Example

**Input**:
`create_mosaic_centered_on_calibrator("0834+555", timespan_minutes=12)`

1. **Orchestrator calls** `find_transit_centered_window("0834+555", 12)`

2. **Service calls** `list_available_transits("0834+555", max_days_back=60)`

3. **Calculate transits**:
   - RA = 8.58 hours
   - Previous transits: [2025-11-07T13:19:23, 2025-11-06T13:22:18, ...]

4. **For each transit, match to groups**:
   - Transit: 2025-11-07T13:19:23
   - Query groups in window: ±30 minutes
   - Find group: 2025-11-07T13:19:23
   - Validate: ✅ Complete (16 subbands), ✅ PB response > 30%
   - Match: delta_minutes = 0.033

5. **Select earliest transit**: 2025-11-07T13:19:23

6. **Calculate window**:
   - Transit: 2025-11-07T13:19:23
   - Window: 2025-11-07T13:13:23 to 2025-11-07T13:25:23 (12 minutes)

7. **Find MS files in window**:
   - Query `ms_index` for MS files with `mid_mjd` in window
   - Count: 3 MS files

8. **Return window info**:

   ```python
   {
       'transit_time': Time('2025-11-07T13:19:23'),
       'start_time': Time('2025-11-07T13:13:23'),
       'end_time': Time('2025-11-07T13:25:23'),
       'ms_count': 3
   }
   ```

9. **Create mosaic** using MS files in this window

---

## Key Points

1. **Transit time is theoretical**: Calculated from RA and LST, not from actual
   observations
2. **Time matching is primary**: Transit time must fall within group's
   observation window
3. **Declination mismatch is warning only**: System trusts transit time match
   even if declination differs
4. **Primary beam validation is critical**: Ensures calibrator is actually
   observable
5. **Complete groups required**: All 16 subbands must be present
6. **Earliest transit selected**: For mosaic creation, uses the oldest available
   transit

---

## Common Warnings Explained

**Warning**:
`"Group 2025-11-07T13:19:23 transit time matches but declination mismatch: file dec=50.18°, expected 55.57°"`

**Meaning**:

- Transit time matches (transit occurred during observation)
- But pointing declination (50.18°) differs from calibrator declination (55.57°)
- System trusts the transit time match and proceeds
- This can happen if:
  - Telescope was pointing at a different declination
  - Calibrator is still in primary beam (5.39° separation is acceptable)
  - Observation was for a different source but transit time matches

**Action**: System continues with the match, trusting transit time over
declination.
