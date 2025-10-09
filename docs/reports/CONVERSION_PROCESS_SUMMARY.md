# DSA-110 UVH5 to CASA Measurement Set Conversion Process

## Overview

This document provides a comprehensive guide for converting UVH5 (HDF5) visibility files from the DSA-110 radio telescope into CASA Measurement Sets (MS) for further analysis and calibration.

## Step-by-Step Process

### 1. File Discovery and Time Filtering

**Purpose**: Identify UVH5 files within the specified time range

**Process**:
- Scan the input directory for files with `.uvh5` extension
- Parse timestamps from filenames using common DSA-110 naming conventions:
  - `YYYY-MM-DDTHH:MM:SS.uvh5`
  - `YYYY-MM-DD HH:MM:SS.uvh5`
- Filter files based on the requested time range
- Return list of matching files

**Key Functions**:
- `find_uvh5_files_in_time_range()` - Main discovery function
- Timestamp parsing with multiple format support
- Time range validation

### 2. UVH5 File Loading

**Purpose**: Load visibility data from UVH5 files using pyuvdata

**Process**:
- Initialize UVData object from pyuvdata
- Read UVH5 file with appropriate parameters:
  - `file_type='uvh5'`
  - `run_check_acceptability=False` (for DSA-110 compatibility)
  - `strict_uvw_antpos_check=False`
- Handle antenna selection if specified
- Apply time filtering if duration is specified

**Key Functions**:
- `load_uvh5_file()` - Core loading function
- `extract_times()` - Time-based data extraction

### 3. Data Processing and Phasing

**Purpose**: Apply necessary corrections and phasing for DSA-110 data

**Process**:
- Set antenna positions using DSA-110 configuration
- Apply fringestopping to phase the data to a specific direction
- Handle coordinate system transformations
- Apply frequency and time axis corrections

**Key Functions**:
- `set_antenna_positions()` - Set ITRF antenna coordinates
- `phase_visibilities()` - Apply fringestopping
- `calc_uvw_interpolate()` - Calculate UVW coordinates

### 4. Measurement Set Creation

**Purpose**: Convert processed data to CASA Measurement Set format

**Process**:
- Write UVData to UVFITS intermediate format
- Use CASA's `importuvfits` task to create the MS
- Update antenna positions in the MS
- Add imaging columns for CASA compatibility
- Clean up intermediate files

**Key Functions**:
- `write_UV_to_ms()` - Main conversion function
- `importuvfits()` - CASA task for UVFITS to MS conversion
- `addImagingColumns()` - Add CASA imaging columns

### 5. Model Column Setup

**Purpose**: Initialize model data in the Measurement Set

**Process**:
- Create MODEL_DATA column with appropriate dimensions
- Copy DATA to CORRECTED_DATA column
- Set up primary beam model if flux information is available
- Ensure proper data types and shapes

**Key Functions**:
- `set_ms_model_column()` - Model column initialization
- `amplitude_sky_model()` - Primary beam modeling

## Available Scripts

### 1. `dsa110_uvh5_to_ms.py` (Recommended)

**Features**:
- Uses specialized dsacalib functions
- Full DSA-110 data processing pipeline
- Handles fringestopping and antenna positioning
- Comprehensive error handling

**Usage**:
```bash
python dsa110_uvh5_to_ms.py <input_dir> <output_dir> <start_time> <end_time>
```

**Dependencies**:
- dsacalib library
- pyuvdata >= 3.2.4
- CASA >= 6.7
- astropy, numpy, scipy

### 2. `simple_uvh5_to_ms.py` (Standalone)

**Features**:
- Minimal dependencies
- Simplified conversion process
- Good for basic conversions
- No dsacalib dependency

**Usage**:
```bash
python simple_uvh5_to_ms.py <input_dir> <output_dir> <start_time> <end_time>
```

**Dependencies**:
- pyuvdata >= 3.2.4
- CASA >= 6.7
- astropy, numpy

### 3. `uvh5_to_ms_converter.py` (Comprehensive)

**Features**:
- Full-featured standalone converter
- Advanced time filtering
- Antenna selection support
- Duration limiting
- Comprehensive error handling

**Usage**:
```bash
python uvh5_to_ms_converter.py <input_dir> <output_dir> <start_time> <end_time> [options]
```

## Technical Details

### Data Flow

```
UVH5 Files → pyuvdata.UVData → UVFITS → CASA importuvfits → Measurement Set
```

### Key Parameters

- **refmjd**: Reference MJD for fringestopping (default: 59215.0)
- **fringestop**: Apply fringestopping (default: True)
- **antenna_list**: Specific antennas to include (default: None = all)
- **dt**: Duration to extract from each file (default: None = entire file)

### File Naming Conventions

The scripts expect UVH5 files to follow DSA-110 naming conventions:

- Primary: `YYYY-MM-DDTHH:MM:SS.uvh5`
- Alternative: `YYYY-MM-DD HH:MM:SS.uvh5`
- Legacy: `YYYYMMDD_HHMMSS.uvh5`

### Output Structure

Each UVH5 file produces a Measurement Set directory containing:

- **ANTENNA/**: Antenna position and configuration data
- **DATA_DESCRIPTION/**: Spectral window and polarization information
- **FIELD/**: Source and pointing information
- **HISTORY/**: Processing history
- **OBSERVATION/**: Observation metadata
- **POINTING/**: Pointing model data
- **POLARIZATION/**: Polarization configuration
- **PROCESSOR/**: Processing information
- **SOURCE/**: Source catalog information
- **SPECTRAL_WINDOW/**: Frequency channel information
- **STATE/**: Observation state information
- **SYSPOWER/**: System power information
- **WEATHER/**: Weather data
- **MAIN/**: Main data table with visibilities

## Error Handling

### Common Issues and Solutions

1. **ImportError for dsacalib**
   - Solution: Use `simple_uvh5_to_ms.py` or install dsacalib
   - Alternative: Use the comprehensive converter

2. **CASA not found**
   - Solution: Install CASA and ensure it's in PATH
   - Check: `which importuvfits`

3. **No files found**
   - Check: Input directory path and file naming convention
   - Verify: Time range covers file timestamps

4. **Memory issues**
   - Solution: Process files individually
   - Use: Duration parameter to limit data size

5. **Conversion failures**
   - Check: File integrity and format compatibility
   - Verify: CASA installation and pyuvdata version

### Debugging Tips

1. **Enable verbose output**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Check file contents**:
   ```python
   from pyuvdata import UVData
   uv = UVData()
   uv.read('your_file.uvh5')
   print(uv)
   ```

3. **Validate Measurement Set**:
   ```python
   from casacore.tables import table
   with table('your_file.ms') as tb:
       print(tb.info())
   ```

## Performance Considerations

### File Size Impact

- **Small files** (< 1 GB): ~1-2 minutes conversion time
- **Medium files** (1-10 GB): ~5-15 minutes conversion time
- **Large files** (> 10 GB): ~30+ minutes conversion time

### Memory Requirements

- **Minimum**: 2x file size in RAM
- **Recommended**: 4x file size in RAM
- **Large files**: Consider processing in chunks

### Disk Space

- **Measurement Sets**: Typically 1.5-2x larger than UVH5 files
- **Temporary files**: Additional space for UVFITS intermediate files
- **Cleanup**: Automatic cleanup of intermediate files

## Integration with CASA

After conversion, use standard CASA tasks:

```python
# Example CASA calibration script
import casatools as cc

# Open measurement set
ms = cc.ms()
ms.open('your_file.ms')

# Perform calibration
cb = cc.calibrater()
cb.open('your_file.ms')
cb.selectvis()
cb.setsolve(type='K', table='delay_cal')
cb.solve()
cb.close()

# Imaging
im = cc.imager()
im.open('your_file.ms')
im.selectvis()
im.defineimage(nx=512, ny=512, cellx='1arcsec', celly='1arcsec')
im.clean(algorithm='hogbom', niter=1000)
im.close()
```

## Best Practices

1. **Use appropriate script**: Choose based on your needs and available dependencies
2. **Validate input**: Check file naming and time ranges before processing
3. **Monitor resources**: Watch memory and disk usage during conversion
4. **Test with small files**: Verify process with small test files first
5. **Keep backups**: Maintain original UVH5 files
6. **Document processing**: Keep logs of conversion parameters and results

## Support and Troubleshooting

For issues related to:

- **DSA-110 specific processing**: Contact DSA-110 team
- **dsacalib functions**: Refer to dsacalib documentation
- **CASA usage**: Consult CASA documentation
- **pyuvdata**: Check pyuvdata documentation and GitHub issues
- **General conversion issues**: Review error messages and check file formats
