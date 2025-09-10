# Antenna Position Swapping Guide

This guide explains how to swap antenna positions from HDF5 file headers with positions from CSV files when using Pyuvdata.

## Overview

When working with DSA110 continuum imaging data, you may need to replace antenna positions stored in HDF5 file headers with more accurate survey-grade positions from CSV files. This guide provides multiple approaches for different scenarios.

## Key Concepts

### Coordinate Systems
- **HDF5 positions**: Typically stored in ITRF coordinates (meters)
- **CSV positions**: Usually in lat/lon/alt format that needs conversion to ITRF
- **Conversion**: Use `astropy.coordinates.EarthLocation` for coordinate transformation

### Pyuvdata Integration
- **UVData objects**: Store antenna positions in `antenna_positions` attribute
- **Antenna metadata**: Includes `antenna_names` and `antenna_numbers`
- **UVW coordinates**: May need recalculation after position changes

## Approaches

### 1. Working with UVData Objects (Recommended)

This is the recommended approach when using Pyuvdata:

```python
from pyuvdata import UVData
from astropy.coordinates import EarthLocation
import astropy.units as u

# Read HDF5 file with Pyuvdata
uv_data = UVData()
uv_data.read(hdf5_file, file_type='uvh5')

# Load new positions from CSV
new_positions, new_names, new_numbers = load_csv_antenna_positions(csv_file)

# Update UVData object
uv_data.antenna_positions = new_positions
uv_data.antenna_names = new_names
uv_data.antenna_numbers = new_numbers

# Write to new format
uv_data.write_ms(output_ms_file)
```

### 2. Direct HDF5 File Modification

For cases where you need to preserve exact HDF5 structure:

```python
import h5py

# Read original HDF5 file
with h5py.File(hdf5_path, 'r') as f_in:
    with h5py.File(output_path, 'w') as f_out:
        # Copy all groups and datasets
        copy_group(f_in, f_out)
        
        # Update antenna positions
        f_out['Header/antenna_positions'] = new_positions
        f_out['Header/antenna_names'] = [name.encode('utf-8') for name in new_names]
        f_out['Header/antenna_numbers'] = new_numbers
```

### 3. Integration with Existing Pipeline

Use the provided utility classes for seamless integration:

```python
from tools.utilities.practical_antenna_swap_example import AntennaPositionSwapper

# Initialize swapper
swapper = AntennaPositionSwapper()

# Swap positions in UVData object
uv_data = swapper.swap_uvdata_positions(uv_data, use_survey_grade=True)
```

## Utility Scripts

### 1. `antenna_position_swapper.py`
Comprehensive utility with multiple approaches and demonstration code.

### 2. `hdf5_antenna_swapper.py`
Focused utility with specific methods for different scenarios.

### 3. `practical_antenna_swap_example.py`
Integration examples for your existing DSA110 pipeline.

## Key Functions

### Reading HDF5 Antenna Information
```python
def read_hdf5_antenna_info(hdf5_path: str) -> Tuple[Optional[np.ndarray], Optional[List[str]], Optional[np.ndarray]]:
    """Read antenna information directly from HDF5 file."""
    with h5py.File(hdf5_path, 'r') as f:
        if 'Header/antenna_positions' in f and 'Header/antenna_names' in f:
            antenna_positions = f['Header/antenna_positions'][:]
            antenna_names = [name.decode('utf-8') for name in f['Header/antenna_names'][:]]
            antenna_numbers = f['Header/antenna_numbers'][:] if 'Header/antenna_numbers' in f else np.arange(len(antenna_names))
            return antenna_positions, antenna_names, antenna_numbers
    return None, None, None
```

### Loading CSV Positions
```python
def load_csv_antenna_positions(csv_path: str) -> Tuple[np.ndarray, List[str], np.ndarray]:
    """Load antenna positions from CSV file and convert to ITRF coordinates."""
    df = pd.read_csv(csv_path, skiprows=5)  # Adjust as needed
    df = df.dropna(subset=['Latitude', 'Longitude', 'Elevation (meters)'])
    
    # Convert to ITRF coordinates
    telescope_location = EarthLocation(
        lat=df['Latitude'].values * u.deg,
        lon=df['Longitude'].values * u.deg,
        height=df['Elevation (meters)'].values * u.m
    )
    
    antenna_positions_itrf = telescope_location.to_geocentric()
    antenna_names = [f"pad{station_num}" for station_num in df.index]
    antenna_numbers = np.arange(len(antenna_names))
    
    return antenna_positions_itrf, antenna_names, antenna_numbers
```

### Swapping in UVData Objects
```python
def swap_uvdata_antenna_positions(uv_data: UVData, csv_path: str) -> UVData:
    """Swap antenna positions in a UVData object with positions from CSV file."""
    new_positions, new_names, new_numbers = load_csv_antenna_positions(csv_path)
    
    uv_data.antenna_positions = new_positions
    uv_data.antenna_names = new_names
    uv_data.antenna_numbers = new_numbers
    
    return uv_data
```

## Important Considerations

### 1. Coordinate Systems
- Ensure consistent coordinate systems between sources
- Use proper conversion from lat/lon/alt to ITRF
- Verify units are correct (degrees vs radians, meters vs kilometers)

### 2. Antenna Numbering
- Check for 0-based vs 1-based indexing
- Ensure antenna numbers match between sources
- Verify antenna names are consistent

### 3. UVW Recalculation
- After changing antenna positions, UVW coordinates may need recalculation
- Use `pyuvdata.utils.phasing.calc_uvw()` for recalculation
- Consider phase center adjustments

### 4. Data Validation
- Always validate antenna counts match
- Check baseline lengths are reasonable
- Verify coordinate system consistency
- Compare positions before and after swapping

## Integration Examples

### Batch Processing
```python
def process_hdf5_files_with_swapping(hdf5_files: List[str], output_dir: str):
    """Process multiple HDF5 files with antenna position swapping."""
    swapper = AntennaPositionSwapper()
    
    for hdf5_file in hdf5_files:
        uv_data = UVData()
        uv_data.read(hdf5_file, file_type='uvh5')
        uv_data = swapper.swap_uvdata_positions(uv_data, use_survey_grade=True)
        
        output_file = os.path.join(output_dir, f"{Path(hdf5_file).stem}.ms")
        uv_data.write_ms(output_file, clobber=True)
```

### Validation
```python
def validate_antenna_positions(hdf5_file: str) -> bool:
    """Validate antenna positions and log differences."""
    uv_data = UVData()
    uv_data.read(hdf5_file, file_type='uvh5')
    
    swapper = AntennaPositionSwapper()
    comparison = swapper.compare_positions(uv_data)
    
    if comparison['position_differences']:
        diff = comparison['position_differences']
        logger.info(f"Position differences - Max: {diff['max_diff']:.3f}m, "
                   f"Mean: {diff['mean_diff']:.3f}m, RMS: {diff['rms_diff']:.3f}m")
    
    return True
```

## Troubleshooting

### Common Issues
1. **Coordinate system mismatch**: Ensure proper conversion between lat/lon/alt and ITRF
2. **Antenna count mismatch**: Verify both sources have the same number of antennas
3. **Indexing issues**: Check for 0-based vs 1-based antenna numbering
4. **UVW inconsistencies**: Recalculate UVW coordinates after position changes

### Debugging Tips
1. Always compare positions before and after swapping
2. Log antenna position statistics
3. Validate baseline lengths are reasonable
4. Check coordinate system consistency

## Conclusion

The provided utilities offer flexible approaches for swapping antenna positions between HDF5 files and CSV files. Choose the approach that best fits your specific use case:

- **UVData objects**: Recommended for most Pyuvdata workflows
- **Direct HDF5 modification**: When preserving exact file structure is important
- **Pipeline integration**: For seamless integration with existing DSA110 pipeline

Always validate your results and ensure coordinate system consistency throughout the process.
