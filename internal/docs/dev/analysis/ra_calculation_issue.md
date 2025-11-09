# Issue: Incorrect RA Assignment to Fields in MS Files

## Problem Summary

When generating MS files from HDF5 files, the Right Ascension (RA) values assigned to fields in the MS FIELD table are incorrect. The code creates time-dependent phase centers with RA = LST(time) for each unique time, but then assigns a **single midpoint RA** to all fields instead of the time-dependent RA values.

## Root Cause Analysis

### 1. Time-Dependent Phase Centers Are Created Correctly

In `conversion/helpers_coordinates.py`, the `phase_to_meridian()` function correctly creates time-dependent phase centers:

```90:103:conversion/helpers_coordinates.py
    for i, time_jd in enumerate(unique_times):
        time_mjd = Time(time_jd, format="jd").mjd
        phase_ra, phase_dec = get_meridian_coords(pt_dec, time_mjd)

        # Create phase center with unique name per time
        pc_id = uvdata._add_phase_center(
            cat_name=f'meridian_icrs_t{i}',
            cat_type='sidereal',
            cat_lon=float(phase_ra.to_value(u.rad)),
            cat_lat=float(phase_dec.to_value(u.rad)),
            cat_frame='icrs',
            cat_epoch=2000.0,
        )
        phase_center_ids[time_jd] = pc_id
```

Each phase center has RA = LST(time) for that specific time, which is correct.

### 2. Midpoint RA Overwrites Time-Dependent Values

However, immediately after creating time-dependent phase centers, the code sets the UVData object's `phase_center_ra` attribute to the **midpoint RA**:

```117:125:conversion/helpers_coordinates.py
    # Update metadata to reflect the new phasing
    # Use midpoint values for backward compatibility with legacy code
    phase_time = Time(float(np.mean(uvdata.time_array)), format="jd")
    phase_ra_mid, phase_dec_mid = get_meridian_coords(pt_dec, phase_time.mjd)
    uvdata.phase_type = 'phased'
    uvdata.phase_center_ra = phase_ra_mid.to_value(u.rad)
    uvdata.phase_center_dec = phase_dec_mid.to_value(u.rad)
    uvdata.phase_center_frame = 'icrs'
    uvdata.phase_center_epoch = 2000.0
```

**This is the bug**: `uvdata.phase_center_ra` is set to the midpoint RA, not the time-dependent RA.

### 3. pyuvdata.write_ms() Uses the Wrong RA

When `pyuvdata.write_ms()` writes the MS file, it likely uses `uvdata.phase_center_ra` (the midpoint value) to populate the FIELD table's PHASE_DIR column, rather than correctly mapping each field to its corresponding time-dependent phase center from `phase_center_catalog`.

### 4. Impact

- **Fields get incorrect RA values**: All fields receive the midpoint RA instead of their time-dependent RA = LST(time)
- **Phase center mismatch**: The FIELD table PHASE_DIR does not match the actual phase centers used in the data
- **Imaging artifacts**: This can cause phase errors and imaging artifacts, especially for long observations where LST changes significantly
- **Calibration issues**: Calibration tasks that rely on field phase centers may use incorrect coordinates

## Evidence

### In `_peek_uvh5_phase_and_midtime()`:

When phase_center_ra is missing, the code calculates RA from HA and LST:

```108:130:conversion/strategies/hdf5_orchestrator.py
            # If phase_center_ra is missing, calculate from HA and LST
            # RA = LST - HA (when HA=0, RA=LST, i.e., meridian transit)
            val_ha = _read_extra("ha_phase_center")
            if val_ha is not None and np.isfinite(val_ha) and mid_jd > 0:
                try:
                    from astropy.coordinates import EarthLocation
                    from astropy.time import Time
                    # Get longitude from Header (default to DSA-110 location)
                    lon_deg = -118.2817  # DSA-110 default
                    if "Header" in f and "longitude" in f["Header"]:
                        lon_val = np.asarray(f["Header"]["longitude"])
                        if lon_val.size == 1:
                            lon_deg = float(lon_val)
                    
                    # Calculate LST at mid_time
                    location = EarthLocation(lat=37.2314 * u.deg, lon=lon_deg * u.deg, height=1222.0 * u.m)
                    tref = Time(mid_jd, format='jd')
                    lst = tref.sidereal_time('apparent', longitude=location.lon)
                    
                    # Calculate RA: RA = LST - HA
                    ha_rad = float(val_ha)  # HA is in radians
                    ra_rad = (lst.to(u.rad).value - ha_rad) % (2 * np.pi)
                    pt_ra_val = ra_rad
```

This correctly calculates RA at the midpoint time, but this is only used for peeking/estimation, not for field assignment.

### In `hdf5_orchestrator.py` when NOT using phase_to_meridian:

```809:830:conversion/strategies/hdf5_orchestrator.py
        else:
            _, pt_dec, mid_mjd = _peek_uvh5_phase_and_midtime(file_list[0])
            if not np.isfinite(mid_mjd) or mid_mjd == 0.0:
                temp_uv = UVData()
                temp_uv.read(
                    file_list[0],
                    file_type='uvh5',
                    read_data=False,
                    run_check=False,
                    check_extra=False,
                    run_check_acceptability=False,
                    strict_uvw_antpos_check=False,
                )
                pt_dec = temp_uv.extra_keywords.get(
                    "phase_center_dec", 0.0) * u.rad
                mid_mjd = Time(
                    float(
                        np.mean(
                            temp_uv.time_array)),
                    format="jd").mjd
                del temp_uv
            phase_ra, phase_dec = get_meridian_coords(pt_dec, mid_mjd)
```

This also uses the midpoint RA, which is incorrect for time-dependent fields.

## Correct Behavior

For time-dependent phase centers, each field in the MS should have:
- **RA = LST(time)** for that field's specific time
- **Dec = pointing_dec** (constant)

The FIELD table's PHASE_DIR should reflect the actual phase center used for each time sample, not a single midpoint value.

## Recommended Fix

1. **Ensure pyuvdata correctly maps phase centers to fields**: Verify that `write_ms()` uses `phase_center_catalog` to assign the correct RA to each field based on `phase_center_id_array`.

2. **If pyuvdata doesn't handle this correctly**: Post-process the MS FIELD table after writing to update PHASE_DIR with the correct time-dependent RA values from `phase_center_catalog`.

3. **Remove or fix the midpoint RA assignment**: The assignment at lines 119-123 in `helpers_coordinates.py` should not overwrite the time-dependent phase center information that will be used for field assignment.

## Implementation

A fix has been implemented in `conversion/ms_utils.py`:

### `_fix_field_phase_centers_from_times()` Function

This function post-processes the MS FIELD table after `pyuvdata.write_ms()` to correct RA values:

1. **Reads FIELD_ID and TIME mapping**: Determines which times correspond to which fields from the main MS table
2. **Calculates correct RA for each field**: For each field, computes RA = LST(time) at that field's mean time using `get_meridian_coords()`
3. **Updates FIELD table**: Updates both PHASE_DIR and REFERENCE_DIR columns with the correct time-dependent RA values

The function is automatically called by `configure_ms_for_imaging()`, which runs after all MS files are written, ensuring all MS files have correct field RA values.

### Integration

The fix is integrated into the MS configuration pipeline:
- Called automatically in `configure_ms_for_imaging()` after MS files are written
- Non-fatal: if the fix fails, it logs a warning but doesn't crash the conversion
- Only updates fields if RA differs by more than 1 arcsecond (avoids unnecessary writes)

### Verification

The existing validation in `validate_phase_center_coherence()` already checks for time-dependent phasing patterns and will correctly identify properly fixed MS files with time-dependent phase centers tracking LST.

