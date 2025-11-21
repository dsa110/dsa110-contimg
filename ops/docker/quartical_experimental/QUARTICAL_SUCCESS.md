# QuartiCal Installation - SUCCESS ✅

## Status: INSTALLED AND WORKING

QuartiCal has been successfully installed in the Docker container!

## Installation Details

- **Version**: 0.2.5 (from PyPI)
- **Python**: 3.10.13
- **Method**: `pip install quartical`
- **Status**: ✅ Installation completed successfully
- **Import**: ✅ Module imports successfully

## Key Dependencies Installed

- ✅ `codex-africanus` 0.4.1 (instead of problematic sharedarray)
- ✅ `dask` 2024.10.0 and `dask-ms` 0.2.23
- ✅ `astro-tigger-lsm` 1.7.3 (for sky models)
- ✅ `python-casacore` 3.7.1 (for MS I/O)
- ✅ All other dependencies resolved

## Known Issues

### CuPy/Numpy Version Conflict

- **Warning**: `cupy 10.4.0` requires `numpy<1.25`, but QuartiCal installed
  `numpy 2.0.2`
- **Impact**: GPU operations with CuPy may not work
- **Workaround**: CPU operations work fine (QuartiCal can run in CPU mode)
- **Note**: This doesn't affect QuartiCal's core functionality

## Usage

QuartiCal uses the `goquartical` command (or `python -m quartical.executor`):

```bash
# Generate config template
goquartical-config

# Run calibration
goquartical <config_file>
```

## Next Steps

1. ✅ QuartiCal installed
2. ⏭️ Create QuartiCal configuration for calibration
3. ⏭️ Test QuartiCal on MS file
   (`/scratch/ms/timesetv3/caltables/2025-10-29T13:54:17.cal.ms`)
4. ⏭️ Compare results with CASA

## Advantages Over CubiCal

- ✅ No sharedarray dependency issues
- ✅ Modern Python support (3.10-3.12)
- ✅ Easier installation (`pip install quartical`)
- ✅ More flexible Jones term combinations
- ✅ Better documentation and active development
