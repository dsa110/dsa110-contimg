# Imaging Module

Radio imaging wrappers for WSClean and CASA tclean.

## Overview

This module produces FITS images from calibrated Measurement Sets using:

- **WSClean** - Fast widefield imager (preferred for production)
- **CASA tclean** - CASA's imaging task

## Key Files

| File               | Purpose                              |
| ------------------ | ------------------------------------ |
| `fast_imaging.py`  | WSClean wrapper for snapshot imaging |
| `spw_imaging.py`   | Spectral window imaging utilities    |
| `gpu_gridding.py`  | GPU-accelerated gridding             |
| `masks.py`         | Clean mask generation                |
| `export.py`        | FITS export utilities                |
| `catalog_tools.py` | Source catalog integration           |
| `worker.py`        | Imaging worker daemon                |
| `cli.py`           | Command-line interface               |

## Quick Usage

```python
from dsa110_contimg.imaging.fast_imaging import run_wsclean_snapshots

# Snapshot imaging with WSClean
images = run_wsclean_snapshots(
    ms_path="/path/to/observation.ms",
    output_dir="/path/to/output",
    n_intervals=24,  # One per 12.88s field
)
```

## WSClean Parameters

Common parameters for DSA-110 (in `fast_imaging.py`):

```python
{
    "size": 4096,           # Image size in pixels
    "scale": "1asec",       # Pixel scale
    "niter": 50000,         # Clean iterations
    "auto-threshold": 3,    # Auto-masking threshold
    "mgain": 0.8,           # Major cycle gain
    "join-channels": True,  # MFS imaging
}
```

## Output Products

Imaging produces:

- `*-image.fits` - Cleaned image
- `*-residual.fits` - Residual image
- `*-psf.fits` - Point spread function
- `*-model.fits` - Model image

## Integration with Pipeline

```
MS → Calibration → Imaging → Source Extraction → Catalog
                      ↓
                 FITS images
                 stored in
                 /stage/products/
```
