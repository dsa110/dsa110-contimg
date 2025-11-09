# CubiCal Experimental Module

## Purpose

This module provides a **standalone** CubiCal-based calibration implementation
for testing and evaluation. It does NOT modify or depend on the existing
CASA-based calibration pipeline.

## Installation Requirements

```bash
# Install CubiCal (in casa6 environment or separate environment)
conda install -c conda-forge cupy cudatoolkit=11.1
pip install "cubical[lsm-support]@git+https://github.com/ratt-ru/CubiCal.git@1.4.0"
```

## Usage

### Standalone CLI

```bash
# Run CubiCal calibration (completely independent)
python -m dsa110_contimg.calibration.cubical_experimental.cubical_cli \
    --ms /stage/dsa110-contimg/ms/timesetv3/caltables/2025-10-29T13:54:17.cal.ms \
    --auto-fields \
    --output-dir /stage/dsa110-contimg/calibration_test/cubical
```

### Compare with CASA Results

```bash
# Run CASA calibration (existing pipeline)
python -m dsa110_contimg.calibration.cli calibrate \
    --ms /stage/dsa110-contimg/ms/timesetv3/caltables/2025-10-29T13:54:17.cal.ms \
    --auto-fields \
    --preset standard

# Compare results
python scripts/compare_calibration_results.py \
    --casa-dir /stage/dsa110-contimg/calibration_test/casa \
    --cubical-dir /stage/dsa110-contimg/calibration_test/cubical
```

## Module Structure

- `cubical_calibrate.py`: Core CubiCal calibration functions
- `cubical_cli.py`: Standalone CLI interface
- `format_converter.py`: Convert CubiCal results to CASA format for comparison
- `comparison_tools.py`: Utilities to compare CASA vs CubiCal results

## Status

**Experimental** - This is a proof-of-concept implementation.
The existing CASA-based pipeline remains the production system.

## Benefits

- Zero risk to existing pipeline
- Can test GPU performance
- Side-by-side comparison with CASA
- Easy to abandon if not beneficial
