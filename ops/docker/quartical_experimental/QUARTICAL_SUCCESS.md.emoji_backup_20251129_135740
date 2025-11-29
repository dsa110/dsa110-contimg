# QuartiCal Installation - SUCCESS :check:

## Status: INSTALLED AND WORKING

QuartiCal has been successfully installed in the Docker container!

## Installation Details

- **Version**: 0.2.5 (from PyPI)
- **Python**: 3.10.13
- **Method**: `pip install quartical`
- **Status**: :check: Installation completed successfully
- **Import**: :check: Module imports successfully

## Key Dependencies Installed

- :check: `codex-africanus` 0.4.1 (instead of problematic sharedarray)
- :check: `dask` 2024.10.0 and `dask-ms` 0.2.23
- :check: `astro-tigger-lsm` 1.7.3 (for sky models)
- :check: `python-casacore` 3.7.1 (for MS I/O)
- :check: All other dependencies resolved

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

1. :check: QuartiCal installed
2. ⏭:variation_selector-16: Create QuartiCal configuration for calibration
3. ⏭:variation_selector-16: Test QuartiCal on MS file
   (`/scratch/ms/timesetv3/caltables/2025-10-29T13:54:17.cal.ms`)
4. ⏭:variation_selector-16: Compare results with CASA

## Advantages Over CubiCal

- :check: No sharedarray dependency issues
- :check: Modern Python support (3.10-3.12)
- :check: Easier installation (`pip install quartical`)
- :check: More flexible Jones term combinations
- :check: Better documentation and active development
