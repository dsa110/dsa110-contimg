# PyUVData Phase Center Bug Analysis

## Problem Description

PyUVData's UVH5 reader fails to properly read phase center coordinates from DSA-110 HDF5 files, instead falling back to default zenith phase center values that get transformed to incorrect apparent coordinates.

## Root Cause Analysis

### What PyUVData Does Wrong

1. **Ignores HDF5 Phase Center Data**: PyUVData's UVH5 reader does not properly extract `phase_center_app_dec` and `phase_center_app_ra` from DSA-110 HDF5 files.

2. **Falls Back to Default Catalog**: Instead, it uses its default phase center catalog entry:
   ```python
   phase_center_catalog: {
       0: {
           'cat_name': 'search',
           'cat_type': 'unprojected', 
           'cat_lon': 0.0,                    # 0° longitude
           'cat_lat': 1.5707963267948966,     # 90° declination (zenith)
           'cat_frame': 'altaz',
           'info_source': 'user'
       }
   }
   ```

3. **Applies Incorrect Coordinate Transformation**: The zenith declination (90°) gets transformed to an apparent declination of ~37.23°, which is completely wrong for the actual telescope pointing.

### Evidence

**Raw HDF5 Values (Correct)**:
- `phase_center_app_dec`: `1.2502388000415088` radians = `71.63°` degrees
- `phase_center_app_ra`: `4.83499762368182` radians = `277.02°` degrees

**PyUVData's Incorrect Values**:
- `phase_center_app_dec`: `0.64984551` radians = `37.23°` degrees ❌
- `phase_center_app_ra`: `5.86786234` radians = `336.20°` degrees ❌
- `phase_center_catalog[0]['cat_lat']`: `1.5707963267948966` radians = `90.00°` degrees (zenith)

## Impact

This bug causes:
1. **Incorrect MS Field Centers**: Measurement Sets have wrong phase center coordinates
2. **Failed Calibrations**: Calibrator selection fails due to wrong field coordinates
3. **Poor Image Quality**: Images are centered on wrong sky positions
4. **36° Declination Error**: The most critical error is the declination discrepancy

## Solution Implemented

### 1. Phase Center Override
```python
# Read correct values directly from HDF5
with h5py.File(hdf5_path, 'r') as f:
    correct_dec_rad = f['Header']['phase_center_app_dec'][()]
    correct_ra_rad = f['Header']['phase_center_app_ra'][()]

# Override PyUVData's incorrect values
uv_data.phase_center_app_dec = np.full(n_times, correct_dec_rad)
uv_data.phase_center_app_dec_degrees = np.full(n_times, np.degrees(correct_dec_rad))
uv_data.phase_center_app_ra = np.full(n_times, correct_ra_rad)
uv_data.phase_center_app_ra_degrees = np.full(n_times, np.degrees(correct_ra_rad))
```

### 2. Phase Center Catalog Update
```python
# Update the phase center catalog with correct coordinates
pc_id = list(uv_data.phase_center_catalog.keys())[0]
uv_data.phase_center_catalog[pc_id]['cat_lon'] = correct_ra_rad
uv_data.phase_center_catalog[pc_id]['cat_lat'] = correct_dec_rad
```

### 3. Direct MS FIELD Table Update
```python
# Directly update the MS FIELD table after creation
with casatools.table() as field_table:
    field_table.open(output_ms_path + "/FIELD")
    ref_dir = field_table.getcol("REFERENCE_DIR")
    ref_dir[0, 0, 0] = correct_ra_rad  # RA
    ref_dir[1, 0, 0] = correct_dec_rad  # Dec
    field_table.putcol("REFERENCE_DIR", ref_dir)
```

## Files Modified

- `core/data_ingestion/unified_ms_creation.py`: Main fix implementation
- `core/data_ingestion/working_hdf5_to_ms_converter.py`: Applied same fix
- `core/data_ingestion/complete_hdf5_to_ms_converter.py`: Applied same fix
- `core/data_ingestion/hdf5_to_ms_converter.py`: Applied same fix

## Verification

The fix has been verified to:
1. ✅ Read correct phase center values from HDF5 files
2. ✅ Override PyUVData's incorrect default values
3. ✅ Update the phase center catalog correctly
4. ✅ Write correct coordinates to the MS FIELD table
5. ✅ Produce Measurement Sets with accurate field centers

## Prevention

This issue highlights the importance of:
1. **Always validating PyUVData output** against source data
2. **Implementing comprehensive logging** to trace coordinate transformations
3. **Testing with real data** rather than assuming library behavior
4. **Understanding library defaults** and fallback behaviors

## Related Issues

- PyUVData UVH5 reader may have similar issues with other telescope data formats
- Coordinate transformation logic in PyUVData may need review
- Default phase center catalog behavior should be better documented

## Date

Discovered and fixed: September 9, 2025
