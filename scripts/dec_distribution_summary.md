# DSA-110 Declination Distribution Analysis

**Date**: December 5, 2025

## Summary

Analysis of 523 HDF5 observations sampled from 83,585 files (16,115 unique timestamps) spanning October 2 - November 18, 2025.

## Key Findings

### Declination Distribution

The DSA-110 telescope observes at **three distinct declination pointings**:

| Declination | Count | Percentage | Description                      |
| ----------- | ----- | ---------- | -------------------------------- |
| **16.3°**   | 166   | 31.7%      | Low declination pointing         |
| **50.5°**   | 15    | 2.9%       | Mid declination pointing (rare)  |
| **54.6°**   | 337   | 64.4%      | **Primary pointing (dominant)**  |
| **65.7°**   | 5     | 1.0%       | High declination pointing (rare) |

**Statistics:**

- Min: 16.27°
- Max: 65.72°
- Mean: 42.40°
- Median: 54.57°
- Std Dev: 17.86°

### Dec ~55° Observations

**Found 337 observations within ±2° of 55° (64.4% of sample)**

The telescope pointing at Dec ~54.6° is the **dominant observing mode** during the sampled period.

## Days with Dec ~55° (54.6° actual)

All observations at this declination have **identical Dec = 54.5734°**, indicating a fixed pointing position.

### October 2025

- **Oct 2**: 25 obs
- **Oct 17-22**: 6 consecutive days (135 obs)
- **Oct 23**: 9 obs (partial day)
- **Oct 24-31**: 8 consecutive days (172 obs)

### Days with Dec = 54.6°

| Date Range               | Days | Total Obs | Notes                   |
| ------------------------ | ---- | --------- | ----------------------- |
| 2025-10-02               | 1    | 25        | Single day              |
| 2025-10-17 to 2025-10-22 | 6    | 135       | Consecutive run         |
| 2025-10-23               | 1    | 9         | Partial day             |
| 2025-10-24 to 2025-10-31 | 8    | 172       | Longest consecutive run |

**Total**: 16 days with Dec ~55° observations in the sampled data.

## Interpretation

1. **Primary Pointing**: The telescope spends most observing time at Dec = 54.6° (64% of observations)

2. **Fixed Pointings**: The exact declination values (16.27°, 54.57°, 65.72°) suggest the telescope uses **discrete pointing positions** rather than continuous scanning

3. **Extended Campaigns**: Multi-day consecutive observing runs at Dec 54.6°:

   - Oct 17-22 (6 days)
   - Oct 24-31 (8 days, longest run)

4. **Observing Strategy**: The telescope appears to follow a coordinated observing strategy with extended periods at the primary Dec ~55° pointing, interspersed with shorter campaigns at other declinations

## Data Coverage

- **Total HDF5 files**: 83,585
- **Unique timestamps**: 16,115 observation groups
- **Time range**: 2025-10-02 to 2025-11-18 (48 days)
- **Sample rate**: 523 files analyzed (3.2% of unique timestamps)

## Technical Notes

- Declination extracted from `Header/extra_keywords/phase_center_dec` in HDF5 files
- All declinations in ICRS frame
- Sample strategy: uniform temporal sampling of subband 0 files
- Precision: All observations at a given pointing have identical Dec to 0.001°

## Recommendations

For pipeline work requiring Dec ~55° data:

1. **Primary targets**: Oct 24-31, 2025 (longest consecutive run, 172+ observations)
2. **Secondary targets**: Oct 17-22, 2025 (6-day run, 135+ observations)
3. **Test data**: Oct 2, 2025 (single day, 25 observations)

The high observation density at Dec 54.6° makes this the ideal declination for:

- Calibration studies
- Imaging pipeline testing
- Long-term monitoring projects
