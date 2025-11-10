# CASA linearmosaic Parameters

## Overview

The `linearmosaic` tool in CASA combines multiple images (typically from a mosaic of pointings) into a single mosaic image with proper weighting.

## Method Signature

```python
from casatools import linearmosaic
lm = linearmosaic()
lm.makemosaic(
    images=[],           # List of image paths
    weightimages=[],      # List of weight image paths
    imageweighttype=1,   # Type of input images (PB-corrected or not)
    weighttype=1         # Type of weight images
)
```

## Parameters

### 1. `images` (list of strings)

**Description:** List of CASA image paths to combine into mosaic.

**Requirements:**
- Must be regridded to a common coordinate system before calling `makemosaic()`
- Can be CASA image directories (`.image`) or FITS files (converted internally)
- All images must have compatible coordinate systems
- Images should cover overlapping regions of the sky

**Example:**
```python
images = [
    "/path/to/tile1.image",
    "/path/to/tile2.image",
    "/path/to/tile3.image"
]
```

### 2. `weightimages` (list of strings)

**Description:** List of weight images corresponding to each input image.

**Requirements:**
- Must match the order of the `images` list (one weight image per input image)
- Must be regridded to the same coordinate system as the input images
- Typically primary beam (PB) images, but can be noise weights or uniform weights

**Example:**
```python
weightimages = [
    "/path/to/tile1.pb.image",   # PB image for tile1
    "/path/to/tile2.pb.image",   # PB image for tile2
    "/path/to/tile3.pb.image"    # PB image for tile3
]
```

### 3. `imageweighttype` (int, default=1)

**Description:** Controls whether input images are PB-corrected or not.

**Values:**
- **`0`**: Images are **NOT PB-corrected**
  - `linearmosaic` will apply PB correction internally
  - Use with uncorrected images
  - Recommended when input images are raw (not divided by PB)
  
- **`1`**: Images **ARE PB-corrected** (default)
  - `linearmosaic` assumes images are already divided by PB
  - Use with PB-corrected images
  - **WARNING:** If images are not actually PB-corrected, this will cause artifacts
  
- **`2`**: Other weighting scheme (less common, rarely used)

**Example:**
```python
# For uncorrected images:
imageweighttype=0  # Let linearmosaic handle PB correction

# For PB-corrected images:
imageweighttype=1  # Images already corrected
```

### 4. `weighttype` (int, default=1)

**Description:** Controls the type of weight images provided.

**Values:**
- **`0`**: Uniform weights
  - All pixels weighted equally
  - Rarely used for mosaics
  
- **`1`**: Primary beam (PB) weights (default)
  - Weight images contain PB response values
  - Higher weight at center, lower at edges
  - Most common for radio astronomy mosaics
  
- **`2`**: Noise weights (inverse variance)
  - Weight images contain inverse variance values
  - Used when noise varies across images

**Example:**
```python
# For PB weight images:
weighttype=1  # Weight images are PB response values

# For noise weight images:
weighttype=2  # Weight images are inverse variance
```

## Recommended Usage

### For Uncorrected Images (Our Case)

```python
lm.makemosaic(
    images=regridded_tiles,      # Uncorrected images
    weightimages=regridded_pbs,  # PB weight images
    imageweighttype=0,           # Images are NOT PB-corrected
    weighttype=1                 # Weight images are PB values
)
```

**What this does:**
- Tells `linearmosaic` that input images are uncorrected
- Provides PB weight images
- `linearmosaic` applies PB correction internally using optimal weighting

### For PB-Corrected Images

```python
lm.makemosaic(
    images=regridded_tiles,      # PB-corrected images
    weightimages=regridded_pbs,  # PB weight images
    imageweighttype=1,           # Images ARE PB-corrected
    weighttype=1                 # Weight images are PB values
)
```

**What this does:**
- Tells `linearmosaic` that input images are already PB-corrected
- Provides PB weight images for weighting
- `linearmosaic` combines without additional PB correction

## Important Notes

1. **Images must be regridded first:** All input images and weight images must be regridded to a common coordinate system before calling `makemosaic()`. Use `imregrid` for this.

2. **Coordinate system:** The output coordinate system is defined by `defineoutputimage()` before calling `makemosaic()`.

3. **Order matters:** The `weightimages` list must match the order of the `images` list.

4. **PB Correction:** If you're unsure whether images are PB-corrected, use `imageweighttype=0` to let `linearmosaic` handle it. Incorrectly setting `imageweighttype=1` with uncorrected images will cause artifacts.

## Common Issues

### Issue: Semi-circular patterns at tile edges

**Cause:** Using `imageweighttype=1` with images that are not actually PB-corrected.

**Solution:** Use `imageweighttype=0` with uncorrected images and let `linearmosaic` handle PB correction.

### Issue: Sources not visible in mosaic

**Cause:** Incorrect PB correction or wrong `imageweighttype` setting.

**Solution:** Verify images are actually PB-corrected if using `imageweighttype=1`, or use `imageweighttype=0` with uncorrected images.

## References

- [CASA linearmosaic documentation](https://casadocs.readthedocs.io/en/stable/api/tt/casatools.linearmosaic.html)
- CASA source code: `LinearMosaic.h` (for detailed implementation)

