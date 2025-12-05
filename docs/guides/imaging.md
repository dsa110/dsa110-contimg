# Imaging Guide

Create FITS images from calibrated Measurement Sets using WSClean or CASA tclean.

## Basic Imaging

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img
```

## Imaging with Catalog Mask (Faster)

Using the unified catalog (FIRST+RACS+NVSS) mask speeds up imaging by 2-4x:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img \
    --mask-radius-arcsec 60.0
```

Masking is **enabled by default**. The mask radius of 60 arcsec covers ~2-3× the synthesized beam.

## Disable Masking

For blind imaging without a priori source positions:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img \
    --no-unicat-mask
```

## Quality Tiers

Choose imaging quality based on your use case:

| Tier             | Description                               | Use Case             |
| ---------------- | ----------------------------------------- | -------------------- |
| `development`    | ⚠️ Non-science, coarser, fewer iterations | Quick testing        |
| `standard`       | Full quality (default)                    | Science observations |
| `high_precision` | Maximum quality, slower                   | Publication images   |

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img \
    --quality-tier standard
```

## Sky Model Seeding

Seed MODEL_DATA from the unified catalog for improved deconvolution:

```bash
python -m dsa110_contimg.imaging.cli image \
    --ms /path/to/observation.ms \
    --imagename /path/to/output.img \
    --unicat-min-mjy 10.0
```

## Environment Configuration

Imaging settings can be configured via environment variables:

| Variable                      | Description                    | Default    |
| ----------------------------- | ------------------------------ | ---------- |
| `PIPELINE_GRIDDER`            | Gridding algorithm             | `standard` |
| `PIPELINE_USE_UNICAT_MASK`    | Use catalog mask (2-4x faster) | `true`     |
| `PIPELINE_MASK_RADIUS_ARCSEC` | Mask radius in arcseconds      | `60.0`     |

## CLI Options

Key imaging options:

| Option                 | Description                | Default    |
| ---------------------- | -------------------------- | ---------- |
| `--ms`                 | Input Measurement Set      | (required) |
| `--imagename`          | Output image name prefix   | (required) |
| `--imsize`             | Image size in pixels       | `1024`     |
| `--cell-arcsec`        | Cell size in arcseconds    | (auto)     |
| `--weighting`          | Visibility weighting       | `briggs`   |
| `--robust`             | Briggs robust parameter    | `0.0`      |
| `--niter`              | Maximum clean iterations   | `1000`     |
| `--quality-tier`       | Imaging quality tier       | `standard` |
| `--no-unicat-mask`     | Disable catalog masking    | `false`    |
| `--mask-radius-arcsec` | Mask radius around sources | `60.0`     |
| `--gridder`            | tclean gridder             | `standard` |

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

# Subcommands
python -m dsa110_contimg.imaging.cli image --help
python -m dsa110_contimg.imaging.cli export --help
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
