# HDF5 to Measurement Set Conversion Module

This module provides infrastructure for converting DSA-110 uvh5/HDF5 visibility files to CASA Measurement Sets (MS) for continuum imaging.

## Overview

The conversion infrastructure is built on top of `pyuvdata` and `dsa110-calib` utilities, providing a clean, unified interface for:

- Converting single HDF5 files to MS format
- Concatenating multiple sub-band files and converting to MS
- Batch processing multiple files
- Extracting metadata from HDF5 files
- Verifying MS output
- Writing the final MS via a UVFITS intermediate (CASA-compatible) layer

## Components

### `unified_converter.py` ⭐ **RECOMMENDED**
Main module containing the `UnifiedHDF5Converter` class with a clean, consistent API for all conversion tasks. The default `convert_subbands` path now:

1. Reads each UVH5 sub-band into a `UVData` object.
2. Validates metadata and concatenates along the frequency axis using `pyuvdata.fast_concat`.
3. Writes a temporary UVFITS file and imports it with CASA’s `importuvfits`, patching the ANTENNA table.
4. (Optionally) Seeds the MS `MODEL_DATA` column with unity visibilities when `populate_model=True`.

### `converter.py` (Legacy)
Original `HDF5toMSConverter` class - still available for backward compatibility.

### `concatenate_and_convert.py` (Legacy)
Original `SubbandConcatenator` class - still available for backward compatibility.

### `uvh5_to_ms.py`
Core conversion utilities adapted from `dsa110-calib`. These are used by the single-file path; the sub-band workflow layers additional UVFITS helpers defined in `pipeline.utils.ms_io` (`write_uvdata_to_ms_via_uvfits`, `compute_absolute_antenna_positions`, `populate_unity_model`).

## Usage

### Python API (Recommended)

```python
from pipeline.core.conversion import UnifiedHDF5Converter

# Create converter instance
converter = UnifiedHDF5Converter(
    input_dir='/data/incoming_data',
    output_dir='/data/dsa110-contimg/processed/ms'
)

# List available files
files = converter.list_files(pattern='*_sb*.hdf5')

# Get file metadata
info = converter.get_file_info('2025-09-05T03:23:14_sb00.hdf5')

# Convert single file
ms_path = converter.convert_single('2025-09-05T03:23:14_sb00.hdf5')

# Convert multiple sub-bands
result = converter.convert_subbands(
    file_paths=['sb01.hdf5', 'sb02.hdf5', 'sb03.hdf5'],
    output_name='combined_observation'
)

# Batch convert
ms_files = converter.convert_batch(pattern='*_sb00.hdf5', max_files=5)

# Verify MS
is_valid = converter.verify_ms(ms_path)

# Convert all 16 sub-bands and have the MS MODEL column pre-populated
default_result = converter.convert_subbands(
    file_paths=[f'sb{i:02d}.hdf5' for i in range(16)],
    output_name='full_band_observation',
    populate_model=True,            # optional, defaults to False
    model_value=1.0 + 0.0j          # optional complex value written into MODEL_DATA
)
```

### Convenience Functions

```python
from pipeline.core.conversion import convert_single_file, convert_subband_group

# Quick single file conversion
ms_path = convert_single_file('file.hdf5', output_dir='/custom/output')

# Quick subband group conversion
result = convert_subband_group(['sb01.hdf5', 'sb02.hdf5'], 'combined')
```

### Command-Line Interface

A convenience script is provided in `/data/dsa110-contimg/tmp/convert_hdf5_to_ms.py` and wraps `UnifiedHDF5Converter`. It currently exposes the legacy `concat-uvdata` and `single-ms-streaming` strategies. For advanced options such as `populate_model` or keeping the intermediate UVFITS file, prefer the Python API shown above.

## File Structure

```
/data/incoming_data/              # Input HDF5 files
/data/dsa110-contimg/
  └─ processed/
      └─ ms/                      # Output MS files
  └─ pipeline/
      └─ pipeline/
          └─ core/
              └─ conversion/
                  ├── __init__.py
                  ├── README.md
                  ├── converter.py      # Main converter class
                  └── uvh5_to_ms.py     # Core conversion utilities
  └─ tmp/
      └─ convert_hdf5_to_ms.py    # CLI script
```

## Data Format

### Input: HDF5/uvh5 Files
- Format: DSA-110 "fast" visibility files
- Structure: UVH5 specification (pyuvdata compatible)
- Frequency: 16 sub-bands spanning 1311.25-1498.75 MHz
- Time sampling: ~12.5 seconds per integration

### Output: CASA Measurement Sets
- Format: CASA MS v2
- Columns: DATA, MODEL_DATA, CORRECTED_DATA, FLAG, WEIGHT
- Additional: Imaging columns added automatically
- Creation: `write_uvdata_to_ms_via_uvfits` writes a temporary UVFITS before running `importuvfits` (requires several GB of scratch space depending on dataset size); the FITS file is deleted unless `keep_uvfits=True`.

## Dependencies

- `pyuvdata`: UVH5 file I/O and format handling
- `casatools`: MS creation via UVFITS intermediate
- `casatasks`: importuvfits task
- `casacore.tables`: Direct table manipulation
- `astropy`: Unit handling and coordinate transformations
- `numpy`: Array operations
- `antpos`: DSA-110 antenna positions

## Notes

1. **Fringestopping**: By default, data is fringestopped to the meridian. Use `fringestop=False` to disable.

2. **Phasing**: Data can be phased to specific RA/Dec coordinates by providing `ra` and `dec` parameters.

3. **Time Selection**: Extract specific time ranges using the `dt` parameter.

4. **Antenna Selection**: Filter specific antennas using the `antenna_list` parameter.

5. **Reference MJD**: Automatically extracted from the HDF5 file header.

6. **Intermediate Files**: Conversion uses a UVFITS intermediate (`*.fits`) that is automatically cleaned up. Pass `keep_uvfits=True` to retain it for debugging.

7. **MODEL Column**: Enable `populate_model=True` (optionally set `model_value`) when calling `convert_subbands` to fill the MS `MODEL_DATA` column with a constant complex value.

## Reference

This conversion infrastructure is adapted from:
- `dsa110-calib/dsacalib/uvh5_to_ms.py`
- `dsa110-meridian-fs/dsamfs/io.py`

Original implementations located in `/data/dsa110-contimg/references/`.

