# Imaging Guide

Create FITS images from calibrated Measurement Sets using WSClean or CASA tclean.

## Basic Imaging

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img
```

## Imaging with NVSS Mask (Faster)

Using an NVSS-based clean mask speeds up imaging by 2-4x:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img \
    --mask-radius-arcsec 60.0
```

## Disable Masking

For blind imaging without a priori source positions:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img \
    --no-nvss-mask
```

## Environment Configuration

Imaging settings can be configured via environment variables:

| Variable                      | Description                 | Default    |
| ----------------------------- | --------------------------- | ---------- |
| `PIPELINE_GRIDDER`            | Gridding algorithm          | `wproject` |
| `PIPELINE_USE_NVSS_MASK`      | Use NVSS mask (2-4x faster) | `true`     |
| `PIPELINE_MASK_RADIUS_ARCSEC` | Mask radius                 | `60.0`     |

## Output Products

Images are stored in `/stage/dsa110-contimg/images/` with FITS format:

| File Pattern          | Description           |
| --------------------- | --------------------- |
| `*.img-image.fits`    | Stokes I image        |
| `*.img-model.fits`    | Clean model           |
| `*.img-residual.fits` | Residual image        |
| `*.img-psf.fits`      | Point spread function |

## CLI Reference

```bash
# Full help
python -m dsa110_contimg.imaging.cli --help

# Image subcommand help
python -m dsa110_contimg.imaging.cli image --help
```

## Source Extraction (Photometry)

After imaging, extract source measurements:

```bash
# Peak photometry
python -m dsa110_contimg.photometry.cli peak \
    --image /path/to/image.fits \
    --output /path/to/photometry.csv

# Adaptive binning
python -m dsa110_contimg.photometry.cli adaptive \
    --image /path/to/image.fits \
    --output /path/to/photometry.csv
```

## Related Documentation

- [Calibration Guide](calibration.md) - Calibrate before imaging
- [Mosaicking Guide](mosaicking.md) - Combine multiple images
- [Visualization Guide](visualization.md) - View images with CARTA
- [Storage & File Organization](storage-and-file-organization.md) - Output paths
