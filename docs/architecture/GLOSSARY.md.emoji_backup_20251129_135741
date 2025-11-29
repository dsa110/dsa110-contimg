# Definition: Tile

## Overview

A **tile** is a single astronomical image created from a short-duration
observation (typically 5 minutes) in the DSA-110 continuum imaging pipeline.
Multiple tiles are combined to create a larger, seamless **mosaic** covering a
wider field of view.

## Detailed Definition

### What is a Tile?

A **tile** is:

1. **A radio astronomy image** created from calibrated interferometric data
2. **Time-bounded**: Each tile represents data from a specific time window
   (typically ~5 minutes of observation)
3. **Spatially localized**: Each tile covers a portion of the sky determined by
   the telescope's pointing direction and primary beam field of view
4. **Calibrated and imaged**: Tiles have been:
   - Calibrated using calibration tables (bandpass, gain calibration)
   - Imaged using deconvolution (e.g., `tclean` in CASA)
   - Primary beam corrected (`.pbcor` images)

### Tile Characteristics

**File Format:**

- **CASA format**: Directory structure (e.g., `{timestamp}.image`,
  `{timestamp}.pb`, `{timestamp}.pbcor`)
- **FITS format**: FITS files (e.g., `{base}-MFS-image-pb.fits`)

**Components:**

- **Main image**: The astronomical image (flux density map)
- **Primary beam image** (`.pb`): Model of the telescope's sensitivity pattern
- **PB-corrected image** (`.pbcor`): Image corrected for primary beam
  attenuation

**Metadata:**

- Stored in `products.sqlite3` database
- Contains: path, creation timestamp, PB correction status
- Linked to source measurement set (MS) file

### How Tiles are Created

**Production Pipeline:**

```
Measurement Set (MS)
  :arrow_right: Calibration (apply calibration tables)
  :arrow_right: Imaging (tclean with deconvolution)
  :arrow_right: Primary Beam Correction
  :arrow_right: Tile Image (.pbcor)
```

**Typical Workflow:**

1. Raw observation data stored as Measurement Set (`.ms`)
2. Calibration tables applied to correct for instrumental effects
3. Imaging performed using `tclean` or similar, creating:
   - `.image` - Deconvolved image
   - `.pb` - Primary beam model
   - `.pbcor` - Primary beam corrected image
4. Tile registered in products database

### Relationship to Mosaics

**Mosaic Assembly:**

- Multiple tiles covering adjacent or overlapping sky regions
- Tiles combined using weighted averaging:
  - **PB-weighted**: `weight = pb_response² / noise_variance`
  - **Noise-weighted**: `weight = 1 / noise_variance²`
- Final mosaic provides:
  - Larger field of view than individual tiles
  - Uniform sensitivity across the field
  - Better signal-to-noise ratio in overlap regions

**Example:**

```
Tile 1 (5 min, pointing A) ──┐
Tile 2 (5 min, pointing B) ──┤
Tile 3 (5 min, pointing C) ──┼──:arrow_right: Mosaic (15 min total, wider FoV)
Tile 4 (5 min, pointing D) ──┘
```

### Tile Properties in the Codebase

**In `products.sqlite3` database:**

- `path`: File system path to tile image
- `created_at`: Timestamp when tile was created
- `pbcor`: Boolean flag indicating if PB correction applied
- `ms_path`: Source measurement set

**In `mosaic/cli.py`:**

- Tiles are paths (strings) to image files/directories
- Fetched from database based on time window (`--since`, `--until`)
- Validated for consistency before mosaicking
- Combined using primary beam weighting

**Tile Quality Metrics:**

- RMS noise level
- Dynamic range
- Primary beam response range
- Calibration status
- Astrometric accuracy

### Key Terminology

**Related Terms:**

- **Measurement Set (MS)**: Raw interferometric observation data
- **Mosaic**: Combined image from multiple tiles
- **Primary Beam (PB)**: Telescope sensitivity pattern
- **PB Correction**: Normalization by primary beam response
- **Pointing**: Telescope pointing direction for a tile

**Common Patterns:**

- **5-minute tiles**: Standard tile duration in DSA-110 pipeline
- **PB-corrected tiles**: Tiles with flux density corrected for primary beam
  attenuation
- **Tile overlap**: Overlapping sky coverage between adjacent tiles

### Usage in Code

**Fetching tiles:**

```python
tiles = _fetch_tiles(products_db, since=timestamp, until=timestamp2)
```

**Validating tiles:**

```python
is_valid, issues, metrics = validate_tiles_consistency(tiles)
```

**Building mosaic from tiles:**

```python
_build_weighted_mosaic(tiles, metrics_dict, output_path)
```

### Summary

A **tile** is a **single calibrated, imaged, and primary-beam-corrected radio
astronomy image** covering a portion of the sky from a short observation window.
Multiple tiles are combined to create mosaics that cover larger areas with
uniform sensitivity.

**Key Points:**

- Time-bounded: ~5 minutes of observation data
- Spatially localized: Covers portion of sky
- Fully processed: Calibrated, imaged, PB-corrected
- Mosaic building block: Combined to create larger images
