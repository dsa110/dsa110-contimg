# Sky Model Image Generation

## Overview

Generate FITS and PNG images from sky models for visualization and quality
checking.

## Quick Start

```python
from pyradiosky import SkyModel
from dsa110_contimg.calibration.skymodel_image import write_skymodel_images

# Create or load sky model
sky = SkyModel.from_votable_catalog('nvss.vot')

# Generate images
fits_path, png_path = write_skymodel_images(
    sky,
    'skymodel_output',
    image_size=(1024, 1024),
    pixel_scale_arcsec=5.0,
    center_ra_deg=165.0,
    center_dec_deg=55.5,
    beam_fwhm_arcsec=45.0,  # Optional: convolve with beam
)
```

## Functions

### `write_skymodel_images()`

Generate both FITS and PNG images from a sky model.

**Parameters:**

- `sky`: pyradiosky SkyModel object
- `base_path`: Base path (will add .fits and .png extensions)
- `image_size`: (width, height) in pixels (default: (512, 512))
- `pixel_scale_arcsec`: Pixel scale in arcseconds (default: 10.0)
- `center_ra_deg`: Center RA in degrees (default: mean of sources)
- `center_dec_deg`: Center Dec in degrees (default: mean of sources)
- `beam_fwhm_arcsec`: Optional beam FWHM for convolution (default: None)

**Returns:**

- `(fits_path, png_path)` tuple

### `write_skymodel_fits()`

Generate only FITS image.

### `write_skymodel_png()`

Generate only PNG image with visualization.

## Example: NVSS Sky Model

```python
from pyradiosky import SkyModel
from dsa110_contimg.calibration.skymodel_image import write_skymodel_images

# Read NVSS catalog
sky = SkyModel.from_votable_catalog('nvss.vot')

# Generate images
fits_path, png_path = write_skymodel_images(
    sky,
    'nvss_skymodel',
    image_size=(2048, 2048),
    pixel_scale_arcsec=2.0,  # 2 arcsec/pixel
    center_ra_deg=165.0,
    center_dec_deg=55.5,
    beam_fwhm_arcsec=45.0,  # 45 arcsec beam
)
```

## Output

- **FITS file**: Standard astronomical image format with WCS header
- **PNG file**: Visualization with colorbar, grid, and labels

## Use Cases

1. **Quality checking**: Visualize sky model before use
2. **Documentation**: Include in reports/presentations
3. **Debugging**: Verify source positions and fluxes
4. **Comparison**: Compare different sky models

## Implementation Complexity

**Low complexity** - The implementation is straightforward:

- Uses astropy for WCS and FITS I/O
- Uses matplotlib for PNG visualization
- Simple point source placement
- Optional beam convolution

**Time to implement**: Already done! (~200 lines of code)
