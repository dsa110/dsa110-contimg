# Sky Model Image Expectations

## What the Image Should Look Like

### For a Single Point Source (Current Test Case)

The image at `/tmp/skymodel_demo.png` should show:

1. **Single Bright Spot**
   - One bright region (the NVSS source)
   - Gaussian shape from 45 arcsec beam convolution
   - Beam width: ~9 pixels (45 arcsec / 5 arcsec per pixel)

2. **Image Characteristics**
   - **Size**: 1024 x 1024 pixels
   - **Field of view**: ~1.4° x 1.4° (5120 arcsec)
   - **Pixel scale**: 5 arcsec/pixel
   - **Center**: RA=165.029091°, Dec=55.559350°
   - **Source position**: Off-center (at pixel ~596, 412)

3. **Visualization Features**
   - **Color scale**: Logarithmic (darker = lower flux, brighter = higher flux)
   - **Grid**: RA/Dec coordinate grid overlay
   - **Colorbar**: Shows flux scale in Jy/pixel
   - **Title**: "Sky Model"

4. **Data Characteristics**
   - Peak flux: ~0.000451 Jy/pixel
   - Non-zero pixels: ~961 (beam convolution spreads the source)
   - Most of image is black/empty (only one source)

### For Multiple Sources

If you generate an image with multiple sources, you should see:

- Multiple bright spots (one per source)
- Each convolved with the specified beam
- Sources distributed across the field of view
- Colorbar showing relative flux levels

### For NVSS Regions

With many NVSS sources:

- Dense field of point sources
- Sources clustered or distributed depending on region
- Each source convolved with beam
- May appear as extended emission if sources are close together

## Interpreting the Image

- **Bright spots** = Radio sources (point sources convolved with beam)
- **Dark areas** = Empty sky (no sources)
- **Beam shape** = Shows the resolution (Gaussian blur)
- **Color scale** = Flux density (brighter = higher flux)

## Expected Appearance for Test Case

Given the test parameters:

- **1 source** found in 0.2° radius
- **45 arcsec beam** (moderate resolution)
- **5 arcsec/pixel** (good sampling)

You should see:

- A single, moderately-sized bright spot
- Off-center in the image (source not at exact center)
- Smooth Gaussian falloff around the source
- Most of the image is dark/empty
- Grid lines showing RA/Dec coordinates
