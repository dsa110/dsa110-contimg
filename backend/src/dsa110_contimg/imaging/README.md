# Imaging Module

Radio imaging wrappers for WSClean and CASA tclean.

## Overview

This module produces FITS images from calibrated Measurement Sets using:

- **WSClean** - Fast widefield imager (preferred for production)
- **CASA tclean** - CASA's imaging task

## Key Files

| File             | Purpose                                  |
| ---------------- | ---------------------------------------- |
| `wsclean.py`     | WSClean wrapper and parameter management |
| `tclean.py`      | CASA tclean wrapper                      |
| `image_utils.py` | FITS image utilities                     |
| `beam.py`        | Primary beam calculations                |

## Quick Usage

```python
from dsa110_contimg.imaging.wsclean import run_wsclean

# Basic imaging
run_wsclean(
    ms_path="/path/to/observation.ms",
    output_prefix="/path/to/output",
    size=4096,
    scale="1asec",
)
```

## WSClean Parameters

Common parameters for DSA-110:

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
