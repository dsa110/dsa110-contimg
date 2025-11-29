# QuartiCal Installation - SUCCESS

## Status: :check: INSTALLED

QuartiCal has been successfully installed in the Docker container!

## Installation Details

- **Version**: 0.2.5
- **Python**: 3.10.13
- **Method**: `pip install quartical` from PyPI
- **Status**: Installation completed successfully

## Note on Dependencies

There is a version conflict warning:

- `cupy` requires `numpy<1.25`
- QuartiCal installed `numpy 2.0.2`

This may affect GPU operations with CuPy, but CPU operations should work fine.
If GPU support is needed, we may need to pin numpy to <1.25.

## Verification

```bash
# Test import
docker run --rm dsa110-cubical:experimental \
  bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate cubical && python -c 'import quartical; print(quartical.__version__)'"

# Test CLI
docker run --rm dsa110-cubical:experimental \
  bash -c "source /opt/conda/etc/profile.d/conda.sh && conda activate cubical && goquartical --help"
```

## Next Steps

1. :check: QuartiCal installed
2. ⏭:variation_selector-16: Create QuartiCal configuration for calibration
3. ⏭:variation_selector-16: Test QuartiCal on MS file
4. ⏭:variation_selector-16: Compare results with CASA

## Advantages Over CubiCal

- :check: No sharedarray dependency issues
- :check: Modern Python support (3.10-3.12)
- :check: Easier installation
- :check: More flexible Jones term combinations
- :check: Better documentation
