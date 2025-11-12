# DSA-110 UVH5 → CASA Measurement Set (Current Process)

This document reflects the current supported conversion flow used by the pipeline.

## Overview

- Input: DSA-110 UVH5 subband files (`*_sb??.hdf5`) grouped in 5‑minute windows
- Converter: Strategy orchestrator (`dsa110_contimg.conversion.strategies.hdf5_orchestrator`)
- Writers: `parallel-subband` (production, 16 subbands) or `pyuvdata` (testing only, ≤2 subbands)
- Outputs: CASA Measurement Sets prepared for imaging

## Step-by-Step Process

### 1. Group Discovery (Time Window)

- Identify complete 16‑subband groups between `start_time` and `end_time`
- Parse timestamps from filenames (e.g., `YYYY-MM-DDTHH:MM:SS_sbNN.hdf5`)
- Function: `find_subband_groups(input_dir, start_time, end_time)`

### 2. Write Strategy Selection

- **Production**: `parallel-subband` writer (default) for 16 subbands
- **Testing**: `pyuvdata` writer available for ≤2 subbands only
- `--writer auto` selects `parallel-subband` for production (16 subbands) or `pyuvdata` for testing (≤2 subbands)
- `parallel-subband`: per‑subband MS parts written in parallel, then concatenated
- Optional staging: tmpfs (`/dev/shm`) or SSD scratch for speed

### 3. Phasing and UVW

- Set telescope identity (`PIPELINE_TELESCOPE_NAME`, default `DSA_110`)
- Phase to meridian at group midpoint; compute/update UVW
- Functions: `set_telescope_identity`, `phase_to_meridian`, `compute_and_set_uvw`

### 4. Measurement Set Creation

- Write a full‑band MS (concat for `direct-subband`, monolithic for `pyuvdata`)
- Ensure and populate imaging columns: `MODEL_DATA`, `CORRECTED_DATA`, `WEIGHT_SPECTRUM`
- Function: `configure_ms_for_imaging(ms_path)`

### 5. Optional Model Setup

- Initialize `MODEL_DATA` with simple sky model if flux is provided
- Copy DATA → CORRECTED_DATA if appropriate
- Function: `set_model_column(...)`

## CLI Usage

- Strategy orchestrator:
```bash
python -m dsa110_contimg.conversion.strategies.hdf5_orchestrator \
  /data/incoming_dir /data/ms_out \
  "2025-10-13 13:25:00" "2025-10-13 13:30:00" \
  --writer auto --scratch-dir /scratch --stage-to-tmpfs --tmpfs-path /dev/shm
```

- Standalone single‑file converter:
```bash
python -m dsa110_contimg.conversion.uvh5_to_ms /path/to/input.uvh5 /path/to/output.ms \
  --add-imaging-columns --enable-phasing
```

## Troubleshooting (Current)
- Ensure `HDF5_USE_FILE_LOCKING=FALSE`, limit BLAS threads (`OMP/MKL/OPENBLAS/NUMEXPR` set to 1) for stability
- If concat fails, verify imaging columns exist and are populated
- Use SSD or tmpfs for scratch to reduce I/O latency
- Confirm `PIPELINE_TELESCOPE_NAME` is set (defaults to `DSA_110`)

## Historical Note
⚠️ **This document has been updated to reflect current conversion tools only.**

The following scripts mentioned in older versions of this document are **no longer available**:
- `dsa110_uvh5_to_ms.py` (deprecated)
- `simple_uvh5_to_ms.py` (deprecated)

**Current conversion path:** Use the orchestrator CLI (see "CLI Usage" section above) or the conversion CLI:
```bash
python -m dsa110_contimg.conversion.cli groups \
  --input-dir /data/incoming \
  --output-dir /data/ms_out \
  --start-time "2025-10-13 13:25:00" \
  --end-time "2025-10-13 13:30:00" \
  --writer auto
```

## Technical Details

### Data Flow (Current)

```
UVH5 Files → Strategy Orchestrator → Writer (parallel-subband or pyuvdata) → Measurement Set
```

**Note:** The previous UVFITS intermediate format is no longer used. Direct conversion to MS is now standard.

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
- **Large files**: Consider processing in chunks or using tmpfs staging (`/dev/shm`)

### Disk Space

- **Measurement Sets**: Typically 1.5-2x larger than UVH5 files
- **Temporary files**: Staging area (tmpfs or SSD scratch) for parallel-subband writer
- **Cleanup**: Automatic cleanup of intermediate files after concatenation

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
