# Pointing Visualization Background Image

## Overview

The PointingVisualization component now supports displaying an all-sky radio map
as a background image in the Aitoff-projected sky map view.

## Background Image Requirements

To use a background image, you need:

1. **Aitoff-projected image**: The image must already be in Aitoff projection
   format
2. **Coordinate system**: The image should cover RA 0-360° (or -180 to +180°
   centered) and Dec -90° to +90°
3. **Image format**: Any web-accessible image format (PNG, JPG, etc.)

## Usage

Pass the `skyMapBackgroundImage` prop with a URL to the image:

```tsx
<PointingVisualization
  height={500}
  showHistory={true}
  skyMapBackgroundImage="https://example.com/aitoff-radio-sky-map.png"
/>
```

## Recommended Sources

### Radio Sky Maps

1. **Haslam 408 MHz Map**:
   - Original FITS file available from various astronomical data repositories
   - Needs to be converted to Aitoff projection and exported as PNG/JPG
   - Can be processed using Python tools like:
     - `astropy` + `matplotlib` with Aitoff projection
     - `skyproj` package
     - `ligo.skymap` package

2. **Other Radio Surveys**:
   - Various all-sky radio surveys at different frequencies
   - Can be processed similarly

### Processing Tools (Python)

To create an Aitoff-projected background image from a FITS file:

```python
from astropy.io import fits
from astropy.wcs import WCS
import matplotlib.pyplot as plt
import numpy as np

# Load FITS file
hdul = fits.open('haslam_408mhz.fits')
data = hdul[0].data
wcs = WCS(hdul[0].header)

# Create Aitoff projection plot
fig = plt.figure(figsize=(12, 6))
ax = fig.add_subplot(111, projection='aitoff')
ax.imshow(data, origin='lower', cmap='gray', alpha=0.5)
ax.grid(True)

# Save as PNG
plt.savefig('aitoff-radio-sky.png', dpi=150, bbox_inches='tight')
```

## Implementation Details

The background image is added to the Plotly layout using the `images` array:

- **Position**: Covers the full Aitoff projection range (-180 to +180 in x, -90
  to +90 in y)
- **Opacity**: Set to 0.3 (30%) so pointing data remains visible
- **Layer**: Placed below the data traces (`layer: "below"`)

## Future Enhancements

- Automatic fetching of radio sky map data
- Support for different radio frequencies
- Interactive opacity control
- Support for HEALPix format maps
