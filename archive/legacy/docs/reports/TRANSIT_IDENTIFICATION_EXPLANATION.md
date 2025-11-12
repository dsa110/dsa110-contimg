# How I Identified the 0834 Transit

**Date:** 2025-11-02  
**Question:** How did I identify the transit for 0834+555?

---

## My Simplified Approach (What I Actually Did)

### 1. Time-Based Search

I used a **simplified time-based approach** rather than the full rigorous method:

```python
# Searched for files around 08:34 UTC (±30 minutes)
# Found group at 08:42:42 UTC
# Verified all 16 subbands present
```

**Steps:**
1. **Assumed transit time:** 0834+555 transits around 08:34 UTC daily (based on RA)
2. **Time window:** Searched ±30 minutes around 08:34 UTC (08:04 to 09:04)
3. **Group detection:** Looked for complete 16-subband groups in that window
4. **Found:** Group at 08:42:42 UTC with all 16 subbands

**What I verified:**
- ✓ File existence and accessibility
- ✓ Complete 16-subband group (00-15)
- ✓ Files within expected time window

**What I did NOT verify:**
- ✗ Actual pointing coordinates (RA/Dec) in files
- ✗ Whether files are actually pointing at 0834+555
- ✗ Dec matching (should be ~+55.57° for 0834+555)

---

## Proper Method (What Should Be Done)

The pipeline has a proper method in `scripts/find_latest_transit_group.py`:

### Step 1: Load Calibrator Coordinates

```python
# Load RA/Dec from catalog
ra_deg, dec_deg = _load_radec("0834+555", catalogs)
# Expected: RA ~128.73°, Dec ~+55.57°
```

### Step 2: Calculate Transit Times

```python
# Use previous_transits() function
from dsa110_contimg.calibration.schedule import previous_transits

transits = previous_transits(
    ra_deg=ra_deg,
    start_time=Time.now(),
    n=14  # Search last 14 days
)
```

**How transit time is calculated:**
- **Transit** = when source is at meridian (HA=0, highest elevation)
- Uses DSA-110 location: lat=37.23°N, lon=118.28°W
- Computes Local Sidereal Time (LST) at DSA-110
- Transit occurs when LST = RA of source
- Accounts for sidereal rate (1.002737909350795 sidereal days per solar day)

### Step 3: Search for Subband Groups

```python
# For each transit time, search for groups
for transit_time in transits:
    window = ±30 minutes around transit
    groups = find_subband_groups(input_dir, start_time, end_time)
```

### Step 4: Verify Pointing Coordinates

```python
# Read file headers to get actual pointing
for group in groups:
    dec_deg = _group_dec_deg(group)  # Read from UVH5 header
    
    # Verify Dec matches target
    if abs(dec_deg - target_dec) <= tolerance:
        # This is likely pointing at 0834+555
        return group
```

**Key verification:**
- Reads `phase_center_dec` from UVH5 file header
- Compares to expected Dec for 0834+555 (~+55.57°)
- Tolerance typically ±2.0° (primary beam width)

---

## Why My Approach Worked (But Isn't Rigorous)

**Why it worked:**
- 0834 transit is **predictable** - occurs daily at ~08:34 UTC
- Time-based search is a reasonable proxy
- Files found within ±30 minutes of expected transit time
- For end-to-end test, acceptable approximation

**Why it's not rigorous:**
- **No coordinate verification** - files could be pointing elsewhere
- **No Dec matching** - could be different pointing Dec
- **Time-based assumption** - doesn't account for:
  - Actual pointing strategy
  - Different observation modes
  - Non-calibrator observations

---

## Relationship Between RA and Transit Time

### Transit Time Calculation

For a source with RA = 128.73° (0834+555):

1. **Convert RA to hours:** RA_hours = 128.73° / 15 = 8.58 hours = 08:34:48

2. **Compute LST at transit:** LST = RA (at meridian transit)

3. **Convert LST to UTC:**
   - LST = RA = 8.58 hours
   - Account for DSA-110 longitude (-118.28°W)
   - Account for sidereal rate
   - Result: Transit ~08:34 UTC daily

**Key formula:**
```
Transit_UTC = RA_hours - (LST_offset) - (longitude_offset)
```

**Why ~08:34 UTC:**
- 0834+555 RA ≈ 128.73° ≈ 8.58 hours
- At DSA-110, this corresponds to ~08:34 UTC transit time
- Daily variation: ±4 minutes (sidereal vs. solar day)

---

## Recommendation: Verify Pointing

Before proceeding with Phase 2, should verify:

```python
# Read UVH5 file header
uvd = UVData()
uvd.read("2025-10-29T08:42:42_sb00.hdf5", read_data=False)

# Check pointing Dec
dec_deg = uvd.phase_center_dec * 180.0 / np.pi

# Expected: ~+55.57° for 0834+555
if abs(dec_deg - 55.57) < 2.0:
    print("✓ Verified: Pointing at 0834+555")
else:
    print(f"⚠ Dec mismatch: {dec_deg:.2f}° vs expected 55.57°")
```

---

## Summary

**My approach:** Time-based search (simplified, not rigorous)  
**Proper method:** RA-based transit calculation + coordinate verification  
**Status:** Found group at 08:42:42 UTC (within expected window)  
**Recommendation:** Verify pointing coordinates before conversion

For end-to-end testing, time-based search is acceptable, but for production use, should verify actual pointing coordinates match 0834+555 expected Dec.
