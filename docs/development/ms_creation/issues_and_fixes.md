# Unified MS Creation - Issues and Fixes

## Overview
This document catalogs all issues encountered during the development of the unified MS creation system and their solutions. This serves as a reference for future development and troubleshooting.

## Issue Categories

### 1. PyUVData Attribute Access Issues

#### Issue: `'UVData' object has no attribute 'Nants'`
**Symptoms:**
- Error when trying to access `uv_data.Nants`, `uv_data.Nbls`, etc.
- Occurs after reading HDF5 files with `run_check=False`

**Root Cause:**
- PyUVData doesn't populate derived attributes like `Nants`, `Nbls` until `uv_data.check()` is called
- `uv_data.check()` was failing due to other data issues (UVW array type, antenna position mismatches)

**Solution:**
```python
# Use getattr() with fallbacks instead of direct attribute access
'n_antennas': getattr(uv_data, 'Nants_data', 0),
'n_baselines': getattr(uv_data, 'Nbls', 0),
'n_times': getattr(uv_data, 'Ntimes', 0),
'n_freqs': getattr(uv_data, 'Nfreqs', 0),
'n_pols': getattr(uv_data, 'Npols', 0),
```

**Files Modified:**
- `core/data_ingestion/unified_ms_creation.py`
- `scripts/test_unified_ms_creation.py`

#### Issue: `'UVData' object has no attribute 'antenna_numbers'`
**Symptoms:**
- Error when trying to access `uv_data.antenna_numbers`
- Similar to above, but for different attributes

**Root Cause:**
- `antenna_numbers` is not a standard PyUVData attribute
- Should use `Nants_data` and `Nants_telescope` instead

**Solution:**
```python
# Use correct PyUVData attributes
'n_antennas': getattr(uv_data, 'Nants_data', 0),
```

#### Issue: `'UVData' object has no attribute 'close'`
**Symptoms:**
- Error when trying to call `uv_data.close()`
- Occurs in validation functions

**Root Cause:**
- PyUVData objects don't have a `close()` method
- This is not a file-like object

**Solution:**
```python
# Use del instead of close()
del uv_data
```

### 2. MS File Validation Issues

#### Issue: MS files reported as "too small" (168 bytes)
**Symptoms:**
- MS validation failing with "MS file too small" error
- MS files actually being created successfully

**Root Cause:**
- MS files are directories, not single files
- `os.path.getsize()` on a directory returns the size of the directory entry (typically 4096 bytes or less)
- Need to calculate total size of all files within the directory

**Solution:**
```python
# For MS files (which are directories), check total size
if os.path.isdir(ms_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(ms_path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.exists(filepath):
                total_size += os.path.getsize(filepath)
    file_size = total_size
else:
    file_size = os.path.getsize(ms_path)
```

**Files Modified:**
- `core/data_ingestion/unified_ms_creation.py` (both `_write_to_ms_with_fixes` and `_validate_created_ms`)

### 3. DSA-110 Specific Data Issues

#### Issue: UVW Array Type Mismatch
**Symptoms:**
- `UVParameter _uvw_array is not the appropriate type. Is: <class 'numpy.float32'>. Should be: <class 'numpy.float64'>`
- Prevents `uv_data.check()` from running

**Root Cause:**
- DSA-110 HDF5 files store UVW arrays as `float32`
- PyUVData requires `float64` for MS writing

**Solution:**
```python
# Fix UVW array type in _fix_dsa110_issues()
if uv_data.uvw_array.dtype != np.float64:
    uv_data.uvw_array = uv_data.uvw_array.astype(np.float64)
```

#### Issue: Telescope Name Incorrect
**Symptoms:**
- Telescope name shows as "OVRO_MMA" instead of "DSA-110"
- Causes confusion in CASA processing

**Root Cause:**
- HDF5 files contain incorrect telescope name
- Likely from original data processing pipeline

**Solution:**
```python
# Correct telescope name in _fix_dsa110_issues()
if uv_data.telescope.name == "OVRO_MMA":
    uv_data.telescope.name = "DSA-110"
```

#### Issue: Visibility Units Uncalibrated
**Symptoms:**
- Warning: "Writing in the MS file that the units of the data are uncalib"
- CASA processes may ignore this and assume Jy

**Root Cause:**
- HDF5 files have `vis_units` set to "uncalib"
- Should be "Jy" for proper CASA processing

**Solution:**
```python
# Set proper units in _fix_dsa110_issues()
if not hasattr(uv_data, 'vis_units') or uv_data.vis_units is None or uv_data.vis_units == 'uncalib':
    uv_data.vis_units = 'Jy'
```

#### Issue: Mount Type Warnings
**Symptoms:**
- Multiple warnings: "MSDerivedValues::parAngle unhandled mount type"
- All antennas show mount type as "other"

**Root Cause:**
- DSA-110 uses alt-az mounts
- Mount type not properly set in HDF5 files

**Solution:**
```python
# Set proper mount type in _fix_dsa110_issues()
if hasattr(uv_data.telescope, 'mount_type'):
    uv_data.telescope.mount_type = ['alt-az'] * len(uv_data.telescope.mount_type)
```

### 4. Antenna Position Integration Issues

#### Issue: Antenna Position Parsing Error
**Symptoms:**
- `invalid literal for int() with base 10: 'DSA-001'`
- Failed to load antenna positions from CSV

**Root Cause:**
- CSV file contains station numbers in "DSA-001" format
- Code expected simple integers

**Solution:**
```python
# Handle DSA-001 format in antenna_positions.py
def extract_station_number(station_str):
    if isinstance(station_str, str) and station_str.startswith('DSA-'):
        return int(station_str.split('-')[1])
    return int(station_str)

self._positions_df['Station Number'] = self._positions_df['Station Number'].apply(extract_station_number)
```

#### Issue: UVW Array vs Antenna Position Mismatch
**Symptoms:**
- Warning: "The uvw_array does not match the expected values given the antenna positions. The largest discrepancy is 1253.2069264236213 meters"
- Repeated many times during processing

**Root Cause:**
- UVW arrays calculated from different antenna positions than those in CSV
- Common in radio astronomy, not critical for processing

**Solution:**
- This is a warning, not an error
- PyUVData handles this automatically with `force_phase=True`
- No code changes needed, just documentation

### 5. MS Writing Parameter Issues

#### Issue: Invalid MS Writing Parameters
**Symptoms:**
- `UVData.write_ms() got an unexpected keyword argument 'write_autocorr'`
- MS writing fails

**Root Cause:**
- PyUVData version doesn't support some parameters
- Parameters were copied from documentation without testing

**Solution:**
```python
# Use only supported parameters
uv_data.write_ms(
    output_ms_path, 
    clobber=True, 
    fix_autos=True,  # Fix auto-correlations to be real-only
    force_phase=True,  # Phase data to zenith of first timestamp
    run_check=False  # Skip PyUVData checks during write
)
```

### 6. Code Structure Issues

#### Issue: Relative Import Errors
**Symptoms:**
- `ImportError: attempted relative import beyond top-level package`
- CASA pipeline modules failing to import

**Root Cause:**
- Relative imports don't work when modules are run directly
- Need absolute imports for standalone execution

**Solution:**
```python
# Change from relative to absolute imports
# FROM:
from ...utils.logging import get_logger

# TO:
from core.utils.logging import get_logger
```

#### Issue: CASA Tool vs Task Imports
**Symptoms:**
- `ImportError: cannot import name 'flagdata' from 'casatools'`
- Various CASA functions not found

**Root Cause:**
- Some functions are in `casatools`, others in `casatasks`
- Need to check correct import location

**Solution:**
```python
# Import from correct modules
from casatasks import flagdata, gencal, bandpass, gaincal, applycal, setjy
from casatools import ms, calanalysis, image, imager, linearmosaic
```

## Prevention Strategies

### 1. Attribute Access
- Always use `getattr()` with fallbacks for PyUVData attributes
- Don't assume derived attributes exist without calling `check()`
- Test attribute access before using in production

### 2. File Validation
- Remember that MS files are directories, not single files
- Use `os.walk()` to calculate total directory size
- Check both file existence and reasonable size

### 3. DSA-110 Data Handling
- Always apply DSA-110 specific fixes before processing
- Test with real DSA-110 data, not just synthetic data
- Validate all data types and units

### 4. Error Handling
- Use try-catch blocks around all PyUVData operations
- Log detailed error messages for debugging
- Provide graceful fallbacks where possible

### 5. Testing
- Test with both single files and multi-file combinations
- Test with missing or corrupted data
- Validate MS files after creation

## Debugging Tips

### 1. Check PyUVData Attributes
```python
# List all available attributes
for attr in dir(uv_data):
    if not attr.startswith('_') and not callable(getattr(uv_data, attr)):
        print(f'{attr}: {getattr(uv_data, attr, "ERROR")}')
```

### 2. Validate MS Files
```python
# Check MS file structure
import os
if os.path.isdir(ms_path):
    print(f"MS directory: {ms_path}")
    for root, dirs, files in os.walk(ms_path):
        for file in files:
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            print(f"  {file}: {size} bytes")
```

### 3. Test Data Quality
```python
# Check data consistency
print(f"Time array shape: {uv_data.time_array.shape}")
print(f"Frequency array shape: {uv_data.freq_array.shape}")
print(f"Data array shape: {uv_data.data_array.shape}")
print(f"UVW array type: {uv_data.uvw_array.dtype}")
```

## Conclusion

These issues and fixes represent the accumulated knowledge from developing a robust MS creation system for DSA-110. The key lessons are:

1. **PyUVData is complex** - always use defensive programming
2. **MS files are directories** - not single files
3. **DSA-110 data needs special handling** - don't assume standard formats
4. **Test with real data** - synthetic data doesn't reveal all issues
5. **Document everything** - future developers will thank you

This document should be updated as new issues are discovered and resolved.
