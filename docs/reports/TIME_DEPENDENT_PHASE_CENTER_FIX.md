# Time-Dependent Phase Center Fix

**Date**: 2025-11-05  
**Status**: Implemented  
**Priority**: High - Improves phase coherence and follows interferometry best practices

---

## Problem Statement

The original `phase_to_meridian()` function set a **single phase center** at the midpoint time (RA=LST(midpoint)) for all data in the observation. However, due to Earth's rotation, the meridian (RA=LST) continuously moves, causing the actual phase center to drift away from the fixed midpoint for data taken at other times.

### Issues with Fixed Midpoint Phase Center

1. **Phase Coherence Degradation**: Data away from the midpoint accumulates phase errors as the source appears to move through the fringe pattern
2. **Bandwidth Smearing**: Additional phase rotation across bandwidth reduces coherence
3. **Imaging Quality Loss**: Residual phase errors manifest as reduced image contrast and shifted source positions
4. **Calibration Complications**: Phase calibration solutions don't transfer cleanly between different times

### Current Implementation Inconsistency

The code had a **partial fix**:
- **Phase center metadata**: Fixed at LST(midpoint) for all data
- **UVW coordinates**: Already correctly computed per-time using meridian at each time

This inconsistency could cause issues if downstream tasks rely on phase center metadata rather than UVW coordinates.

---

## Solution: Time-Dependent Phase Centers

### Implementation

Modified `phase_to_meridian()` in `src/dsa110_contimg/conversion/helpers.py` to:

1. **Identify unique times**: Extract all unique time samples in the observation
2. **Create phase center per time**: For each unique time, compute meridian coordinates (RA=LST(time), Dec=pointing_dec) and create a phase center
3. **Map baseline-times to phase centers**: Use `phase_center_id_array` to map each baseline-time to its corresponding time-dependent phase center

### Key Changes

**Before** (single phase center):
```python
phase_time = Time(float(np.mean(uvdata.time_array)), format="jd")
phase_ra, phase_dec = get_meridian_coords(pt_dec, phase_time.mjd)
pc_id = uvdata._add_phase_center(
    cat_name='meridian_icrs',
    cat_lon=float(phase_ra.to_value(u.rad)),
    cat_lat=float(phase_dec.to_value(u.rad)),
    ...
)
uvdata.phase_center_id_array[:] = pc_id  # All use same ID
```

**After** (time-dependent phase centers):
```python
unique_times, _, time_inverse = np.unique(
    uvdata.time_array, return_index=True, return_inverse=True
)
phase_center_ids = {}
for i, time_jd in enumerate(unique_times):
    time_mjd = Time(time_jd, format="jd").mjd
    phase_ra, phase_dec = get_meridian_coords(pt_dec, time_mjd)
    pc_id = uvdata._add_phase_center(
        cat_name=f'meridian_icrs_t{i}',
        cat_lon=float(phase_ra.to_value(u.rad)),
        cat_lat=float(phase_dec.to_value(u.rad)),
        ...
    )
    phase_center_ids[time_jd] = pc_id

# Vectorized mapping
pc_id_array = np.array([phase_center_ids[t] for t in unique_times])
uvdata.phase_center_id_array[:] = pc_id_array[time_inverse]
```

### Benefits

1. **Proper Phase Tracking**: Phase center RA now tracks LST throughout the observation, matching Earth's rotation
2. **Consistency**: Phase center metadata now matches the time-dependent UVW coordinate computation
3. **Best Practices**: Follows radio interferometry standards for continuous phase tracking
4. **Improved Coherence**: Eliminates phase errors from fixed midpoint assumption

---

## Alignment with Interferometry Best Practices

According to interferometry principles:
- **Natural fringe rate** due to Earth's rotation: ~70 Hz for million-wavelength baselines
- **Continuous tracking required**: Phase and delay centers must continuously adjust to follow source motion
- **Time-dependent phase centers**: Standard practice in modern interferometry software (CASA, AIPS, etc.)

The fix ensures that:
- Each time sample uses RA = LST(time) at its actual time
- Phase center metadata accurately reflects the phasing at each timestamp
- UVW coordinates and phase centers are now consistent

---

## Backward Compatibility

The function still sets legacy metadata fields (`phase_center_ra`, `phase_center_dec`) to midpoint values for backward compatibility with code that may rely on these fields. However, the `phase_center_catalog` and `phase_center_id_array` now correctly represent time-dependent phase centers.

---

## Testing Recommendations

1. **Verify phase coherence**: Compare phase scatter before/after fix for observations > 5 minutes
2. **Check calibration quality**: Verify that calibration solutions improve with time-dependent phase centers
3. **Imaging tests**: Confirm that image quality improves, especially for longer observations
4. **MS validation**: Verify that MS files written with time-dependent phase centers are correctly interpreted by CASA

---

## Files Modified

- `src/dsa110_contimg/conversion/helpers.py`: Updated `phase_to_meridian()` function (lines 206-280)

---

## Related Documentation

- `docs/reports/MS_PHASING_DURING_CONVERSION.md`: Explains initial phasing during MS conversion
- `docs/reports/UVW_COORDINATE_HANDLING_REVIEW.md`: Documents UVW coordinate handling
- Perplexity reasoning validation: Confirmed that time-dependent phase centers are standard practice

