# VAST Tools Visualization Features - Implementation Summary

## Date: 2025-11-10

## Overview

This document summarizes the implementation of VAST Tools visualization features in DSA-110 postage stamp visualization.

## Implemented Features

### High Priority ✓

#### 1. Shared Normalization (`disable_autoscaling=False`)

**Status:** ✓ **IMPLEMENTED**

**Implementation:**
- Added `disable_autoscaling` parameter to `show_all_cutouts()` (default: `False`)
- When `False`: Uses shared normalization from first cutout across all epochs
- When `True`: Each cutout uses its own normalization
- Critical for visual variability comparison

**Code Location:**
- `src/dsa110_contimg/qa/postage_stamps.py::show_all_cutouts()`

**Usage:**
```python
# Shared normalization (default - recommended for variability)
source.show_all_cutouts(disable_autoscaling=False)

# Individual normalization per cutout
source.show_all_cutouts(disable_autoscaling=True)
```

### Medium Priority ✓

#### 2. Colormap: `gray_r` for Cutouts

**Status:** ✓ **IMPLEMENTED**

**Implementation:**
- Changed default colormap from `viridis` to `gray_r` for cutouts
- Matches VAST Tools standard
- Better contrast for radio astronomy images
- Configurable via `cmap` parameter

**Code Location:**
- `src/dsa110_contimg/qa/postage_stamps.py::plot_cutout()` (default: `cmap='gray_r'`)
- `src/dsa110_contimg/qa/postage_stamps.py::show_all_cutouts()` (default: `cmap='gray_r'`)

#### 3. Contrast: 0.1 for Grid Views

**Status:** ✓ **IMPLEMENTED**

**Implementation:**
- Changed default contrast from `0.2` to `0.1` for grid views
- Matches VAST Tools `show_all_png_cutouts()` default
- Better for multiple images in grid layout
- Configurable via `contrast` parameter

**Code Location:**
- `src/dsa110_contimg/qa/postage_stamps.py::show_all_cutouts()` (default: `contrast=0.1`)

#### 4. Data Scaling: mJy Conversion

**Status:** ✓ **IMPLEMENTED**

**Implementation:**
- Added `mjy_conversion` parameter (default: `True`)
- Multiplies data by `1.e3` (Jy → mJy) for display
- Better numerical precision
- Updates colorbar label automatically

**Code Location:**
- `src/dsa110_contimg/qa/postage_stamps.py::show_all_cutouts()` (default: `mjy_conversion=True`)

**Usage:**
```python
# Display in mJy (default)
source.show_all_cutouts(mjy_conversion=True)

# Display in Jy
source.show_all_cutouts(mjy_conversion=False)
```

### Low Priority ✓

#### 5. Overlay Features

**Status:** ✓ **IMPLEMENTED** (Basic framework)

**Implementation:**
- Added `overlay_catalog` parameter to `plot_cutout()` and `show_all_cutouts()`
- Supports catalog overlays: `'nvss'`, `'first'`, `'rax'`, `'master'`
- Uses existing `dsa110_contimg.catalog.query.query_sources()` function
- Overlays catalog sources as green 'x' markers
- Also supports custom source overlays via `overlay_sources` parameter

**Code Location:**
- `src/dsa110_contimg/qa/postage_stamps.py::plot_cutout()`
- `src/dsa110_contimg/qa/postage_stamps.py::show_all_cutouts()`

**Usage:**
```python
# Overlay NVSS catalog sources
source.show_all_cutouts(overlay_catalog='nvss')

# Overlay FIRST catalog sources
source.show_all_cutouts(overlay_catalog='first')

# Custom source overlay
custom_sources = [
    {'ra': 122.0, 'dec': 54.5, 'label': 'Source A'},
    {'ra': 122.1, 'dec': 54.6, 'label': 'Source B'}
]
plot_cutout(data, wcs, overlay_sources=custom_sources)
```

**Available Catalogs:**
- `'nvss'`: NVSS catalog (1.4 GHz)
- `'first'`: FIRST catalog (1.4 GHz)
- `'rax'`: RAX catalog
- `'master'`: Master catalog (combined)

**Note:** Selavy overlay (source detection components) not yet implemented - requires additional utilities.

#### 6. Offset Axes

**Status:** ✓ **IMPLEMENTED**

**Implementation:**
- Added `offset_axes` parameter (default: `True`)
- Offsets coordinate axes labels to avoid overlap with image
- Uses WCS axes `minpad` and tick label positioning
- Visual polish feature

**Code Location:**
- `src/dsa110_contimg/qa/postage_stamps.py::plot_cutout()` (default: `offset_axes=True`)

**Usage:**
```python
# Offset axes (default)
plot_cutout(data, wcs, offset_axes=True)

# No offset
plot_cutout(data, wcs, offset_axes=False)
```

#### 7. Percentile Standardization

**Status:** ✓ **IMPLEMENTED**

**Implementation:**
- Standardized percentile to `99.9` everywhere (matches VAST Tools)
- Updated `normalize_cutout()` default: `percentile=99.9`
- Updated `show_all_cutouts()` default: `percentile=99.9`
- Updated `imaging/export.py` fallback: `percentile=99.9`

**Code Locations:**
- `src/dsa110_contimg/qa/postage_stamps.py::normalize_cutout()` (default: `percentile=99.9`)
- `src/dsa110_contimg/qa/postage_stamps.py::show_all_cutouts()` (default: `percentile=99.9`)
- `src/dsa110_contimg/imaging/export.py::save_png_from_fits()` (fallback: `percentile=99.9`)

## Feature Comparison

| Feature | VAST Tools | DSA-110 (Before) | DSA-110 (After) |
|---------|------------|-----------------|-----------------|
| **Shared Normalization** | ✓ (`disable_autoscaling=False`) | ✗ | ✓ |
| **Colormap** | `gray_r` | `viridis`/`inferno` | `gray_r` ✓ |
| **Contrast (grid)** | `0.1` | `0.2` | `0.1` ✓ |
| **mJy Conversion** | ✓ (`* 1.e3`) | ✗ | ✓ |
| **Overlays** | ✓ (selavy, crossmatch) | ✗ | ✓ (catalog) |
| **Offset Axes** | ✓ | ✗ | ✓ |
| **Percentile** | `99.9` | `99.5`/`99.9` | `99.9` ✓ |

## API Changes

### `show_all_cutouts()` New Parameters

```python
source.show_all_cutouts(
    # Existing parameters...
    disable_autoscaling: bool = False,      # NEW: Shared normalization control
    cmap: str = 'gray_r',                   # NEW: Changed default from 'viridis'
    contrast: float = 0.1,                  # NEW: Changed default from 0.2
    mjy_conversion: bool = True,            # NEW: mJy conversion
    percentile: float = 99.9,               # NEW: Standardized to 99.9
    overlay_catalog: Optional[str] = None,  # NEW: Catalog overlay
    offset_axes: bool = True                # NEW: Offset axes
)
```

### `plot_cutout()` New Parameters

```python
plot_cutout(
    # Existing parameters...
    cmap: str = 'gray_r',                   # NEW: Changed default from 'viridis'
    unit_label: str = 'Flux (Jy/beam)',     # NEW: Configurable unit label
    offset_axes: bool = True,               # NEW: Offset axes
    overlay_sources: Optional[List[Dict]] = None,  # NEW: Custom source overlay
    overlay_catalog: Optional[str] = None   # NEW: Catalog overlay
)
```

## Testing

### Test Shared Normalization

```python
from dsa110_contimg.photometry.source import Source

source = Source(source_id="test_123", products_db="products.sqlite3")

# Shared normalization (default - recommended)
fig1 = source.show_all_cutouts(disable_autoscaling=False)

# Individual normalization
fig2 = source.show_all_cutouts(disable_autoscaling=True)
```

### Test Catalog Overlay

```python
# Overlay NVSS sources
fig = source.show_all_cutouts(overlay_catalog='nvss')

# Overlay FIRST sources
fig = source.show_all_cutouts(overlay_catalog='first')
```

## Remaining Work

### Not Yet Implemented

1. **Selavy Overlay**: Source detection component overlay
   - Requires: `read_selavy()` utility function
   - Requires: Selavy catalog format support
   - **Status:** Framework ready, needs selavy utilities

2. **Crossmatch Overlay**: External catalog crossmatch overlay
   - Requires: Crossmatch database/utilities
   - **Status:** Basic catalog overlay implemented, crossmatch overlay needs crossmatch data

## Related Documentation

- `docs/dev/VAST_VISUALIZATION_FEATURES_MISSING.md` - Original analysis
- `docs/dev/VISUALIZATION_METHODS_COMPARISON.md` - Comparison with VAST Tools
- `src/dsa110_contimg/qa/postage_stamps.py` - Implementation
- `src/dsa110_contimg/catalog/query.py` - Catalog query utilities

## Summary

**All high and medium priority features implemented!**

- ✓ Shared normalization (critical for variability analysis)
- ✓ Colormap `gray_r` (matches VAST Tools)
- ✓ Contrast `0.1` for grids (matches VAST Tools)
- ✓ mJy conversion (better precision)
- ✓ Catalog overlays (NVSS, FIRST, RAX, master)
- ✓ Offset axes (visual polish)
- ✓ Percentile standardization (99.9 everywhere)

**Low priority features:**
- ✓ Basic overlay framework implemented
- ⏭ Selavy overlay (needs utilities)
- ⏭ Crossmatch overlay (needs crossmatch data)

DSA-110 visualization now matches or exceeds VAST Tools standards for postage stamp visualization!

