# QuartiCal Setup

## Overview

QuartiCal is the successor to CubiCal - a fast and flexible calibration suite
for radio interferometer data.

## Advantages over CubiCal

1. **Better dependency management**: Uses `codex-africanus` instead of
   `sharedarray`
2. **Modern Python**: Supports Python 3.10-3.12
3. **Easier installation**: Simple `pip install quartical`
4. **More flexible**: Allows any available Jones terms to be combined
5. **Cluster deployment**: Can be deployed on clusters

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install quartical
```

### Option 2: Install from local repository

```bash
cd /home/ubuntu/proj/QuartiCal
pip install -e .
```

## Python Requirements

- Python >= 3.10, < 3.13
- Our Docker image uses Python 3.10.13 (perfect match!)

## Key Dependencies

- `codex-africanus` (instead of sharedarray)
- `dask` and `dask-ms` (for distributed processing)
- `astro-tigger-lsm` (for sky models)
- `python-casacore` (for MS I/O)

## Usage

QuartiCal provides a CLI command: `goquartical`

```bash
goquartical <config_file>
```

## Next Steps

1. Rebuild Docker image (already done with Python 3.10)
2. Install QuartiCal in Docker container
3. Test QuartiCal calibration on MS file
4. Compare with CASA results
