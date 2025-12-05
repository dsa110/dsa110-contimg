# casangi Visualization Tools Integration Plan

---

## 📋 Implementation Status Summary

> **Last Updated**: 2025-12-01

### Overall Progress

| Phase        | Status      | Completion |
| ------------ | ----------- | ---------- |
| Phase 1      | ✅ Complete | 100%       |
| Phase 2      | ✅ Complete | 100%       |
| Phase 3      | ✅ Complete | 100%       |
| Native Tools | ✅ Complete | 100%       |

### Phase 1: Quick Wins ✅

| Component                             | File(s)                                                     | Status       |
| ------------------------------------- | ----------------------------------------------------------- | ------------ |
| MS Raster API endpoint                | `backend/src/dsa110_contimg/api/routes/ms.py`               | ✅ Completed |
| MsRasterPlot React component          | `frontend/src/components/ms/MsRasterPlot.tsx`               | ✅ Completed |
| Antenna layout widget (native D3/SVG) | `frontend/src/components/antenna/AntennaLayoutWidget.tsx`   | ✅ Completed |
| Antenna stats API endpoint            | `backend/src/dsa110_contimg/api/routes/ms.py` (`/antennas`) | ✅ Completed |

### Phase 2: Core Features ✅

| Component                     | File(s)                                                                                | Status       |
| ----------------------------- | -------------------------------------------------------------------------------------- | ------------ |
| Bokeh session manager service | `backend/src/dsa110_contimg/api/services/bokeh_sessions.py`                            | ✅ Completed |
| InteractiveClean launcher API | `backend/src/dsa110_contimg/api/routes/imaging.py`                                     | ✅ Completed |
| Interactive imaging page      | `frontend/src/pages/InteractiveImagingPage.tsx`                                        | ✅ Completed |
| Session list/management API   | `backend/src/dsa110_contimg/api/routes/imaging.py` (`/sessions`)                       | ✅ Completed |
| DSA-110 default parameters    | `backend/src/dsa110_contimg/api/services/bokeh_sessions.py` (`DSA110_ICLEAN_DEFAULTS`) | ✅ Completed |

### Phase 3: Deep Integration ✅

| Component                    | File(s)                                                                                                         | Status       |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------ |
| BokehEmbed iframe component  | `frontend/src/components/bokeh/BokehEmbed.tsx`                                                                  | ✅ Completed |
| WebSocket status bridge      | `backend/src/dsa110_contimg/api/routes/imaging.py` (`/sessions/{id}/ws`)                                        | ✅ Completed |
| Progress tracking service    | `backend/src/dsa110_contimg/api/services/bokeh_sessions.py` (`register_websocket`, `broadcast_progress`)        | ✅ Completed |
| Image versioning schema      | `backend/src/dsa110_contimg/api/schemas.py` (`parent_id`, `version`, `imaging_params`)                          | ✅ Completed |
| Image versioning endpoints   | `backend/src/dsa110_contimg/api/routes/images.py` (`/versions`, `/children`, `/reimage`)                        | ✅ Completed |
| Automated session cleanup    | `ops/systemd/contimg-session-cleanup.timer`, `ops/systemd/contimg-session-cleanup.service`                      | ✅ Completed |
| Backend validation utilities | `backend/src/dsa110_contimg/api/validation.py` (`validate_ms_for_visualization`, `validate_imaging_parameters`) | ✅ Completed |
| E2E tests                    | `frontend/e2e/interactive-imaging.spec.ts`                                                                      | ✅ Completed |
| Backend unit tests           | `backend/tests/unit/api/test_phase3_integration.py` (30 tests)                                                  | ✅ Completed |

### Native Tool Implementations (casangi alternatives) ✅

These tools were implemented natively using JS9 and D3/SVG instead of casangi:

| Tool         | Implementation                       | Status       | Rationale                                   |
| ------------ | ------------------------------------ | ------------ | ------------------------------------------- |
| plotants     | `AntennaLayoutWidget.tsx` (D3/SVG)   | ✅ Completed | Native implementation, no Python dependency |
| CreateMask   | `MaskToolbar.tsx` + `/masks` API     | ✅ Completed | Leverages existing JS9 region support       |
| CreateRegion | `RegionToolbar.tsx` + `/regions` API | ✅ Completed | DS9/CRTF/JSON export via JS9                |

#### Native Implementations - File Details

| Component             | Frontend File(s)                                          | Backend File(s)                                                |
| --------------------- | --------------------------------------------------------- | -------------------------------------------------------------- |
| **Antenna Layout**    | `frontend/src/components/antenna/AntennaLayoutWidget.tsx` | (uses existing `/ms/{id}/antennas` endpoint)                   |
| **Mask Creation**     | `frontend/src/components/fits/MaskToolbar.tsx`            | `backend/src/dsa110_contimg/api/routes/images.py` (`/masks`)   |
| **Region Management** | `frontend/src/components/fits/RegionToolbar.tsx`          | `backend/src/dsa110_contimg/api/routes/images.py` (`/regions`) |

### Key Files Created/Modified

#### Backend (Python)

| Path                                                        | Description                                  |
| ----------------------------------------------------------- | -------------------------------------------- |
| `backend/src/dsa110_contimg/api/routes/imaging.py`          | Interactive imaging endpoints + WebSocket    |
| `backend/src/dsa110_contimg/api/routes/images.py`           | Image versioning, mask, and region endpoints |
| `backend/src/dsa110_contimg/api/services/bokeh_sessions.py` | Session lifecycle + WebSocket management     |
| `backend/src/dsa110_contimg/api/schemas.py`                 | Pydantic models with versioning fields       |
| `backend/src/dsa110_contimg/api/validation.py`              | MS visualization validation utilities        |
| `backend/tests/unit/api/test_phase3_integration.py`         | 30 unit tests for Phase 3 features           |

#### Frontend (TypeScript/React)

| Path                                                      | Description                                    |
| --------------------------------------------------------- | ---------------------------------------------- |
| `frontend/src/components/ms/MsRasterPlot.tsx`             | Visibility raster plot component               |
| `frontend/src/components/antenna/AntennaLayoutWidget.tsx` | T-shaped antenna layout visualization (D3/SVG) |
| `frontend/src/components/fits/RegionToolbar.tsx`          | JS9 region creation toolbar (DS9/CRTF export)  |
| `frontend/src/components/fits/MaskToolbar.tsx`            | Clean mask creation with backend save          |
| `frontend/src/components/bokeh/BokehEmbed.tsx`            | Bokeh iframe embedding with progress tracking  |
| `frontend/src/pages/InteractiveImagingPage.tsx`           | Interactive imaging workflow page              |
| `frontend/e2e/interactive-imaging.spec.ts`                | Playwright E2E tests                           |

#### Operations

| Path                                          | Description                      |
| --------------------------------------------- | -------------------------------- |
| `ops/systemd/contimg-session-cleanup.timer`   | Hourly systemd timer for cleanup |
| `ops/systemd/contimg-session-cleanup.service` | Cleanup oneshot service          |

### Decisions Made

| Decision                 | Choice                 | Rationale                                      |
| ------------------------ | ---------------------- | ---------------------------------------------- |
| Antenna visualization    | Native D3/SVG          | Simple, no Python dependency, fast render      |
| Mask creation            | JS9 + MaskToolbar      | Already integrated, full DS9 region support    |
| Region management        | JS9 + RegionToolbar    | DS9/CRTF/JSON export, backend persistence      |
| casagui integration      | Yes (MsRaster, iClean) | No web-based alternatives for MS visualization |
| Bokeh embedding approach | iframe + WebSocket     | Unified UX with real-time progress updates     |

### API Endpoints Added

#### Mask Endpoints (`/images/{id}/masks`)

| Method | Endpoint                       | Description                       |
| ------ | ------------------------------ | --------------------------------- |
| POST   | `/images/{id}/masks`           | Save DS9/CRTF mask for re-imaging |
| GET    | `/images/{id}/masks`           | List all masks for an image       |
| DELETE | `/images/{id}/masks/{mask_id}` | Delete a specific mask            |

#### Region Endpoints (`/images/{id}/regions`)

| Method | Endpoint                           | Description                      |
| ------ | ---------------------------------- | -------------------------------- |
| POST   | `/images/{id}/regions`             | Save regions (DS9/CRTF/JSON)     |
| GET    | `/images/{id}/regions`             | List regions (filter by purpose) |
| GET    | `/images/{id}/regions/{region_id}` | Get region file content          |
| DELETE | `/images/{id}/regions/{region_id}` | Delete a specific region file    |

---

## Overview

This document outlines the integration strategy for incorporating NRAO's
[casangi](https://github.com/casangi) visualization tools into the DSA-110
Continuum Imaging Pipeline frontend. The casangi organization provides
Bokeh-based visualization tools for CASA data processing, offering interactive
capabilities that complement our existing React-based dashboard.

**Target Repositories**:

- [casangi/casagui](https://github.com/casangi/casagui) - CASA GUI Desktop
  (pre-alpha, 4 ⭐, 24 open issues)
- [casangi/cubevis](https://github.com/casangi/cubevis) - CASA Image
  Visualization (beta, 1 ⭐, created Jul 2025)

**Last Updated**: 2025-07-14 (Implementation status added)

---

## Executive Summary

### Why casangi?

The DSA-110 pipeline currently lacks interactive visualization for:

1. **Visibility inspection** - No way to view amplitude/phase vs time/channel
2. **Interactive deconvolution** - tclean runs blindly without mask drawing
3. **Real-time feedback** - Users cannot monitor imaging progress

casangi provides pure-Python, Bokeh-based tools that address these gaps while
maintaining compatibility with our CASA 6.7 environment. The tools are designed
for both standalone use and Jupyter notebook integration.

### Strategic Fit

| DSA-110 Need        | casangi Solution   | Alternative           |
| ------------------- | ------------------ | --------------------- |
| MS visibility plots | `MsRaster`         | plotms (X11 required) |
| Interactive clean   | `InteractiveClean` | viewer (deprecated)   |
| Antenna diagnostics | `plotants`         | Custom D3 (simpler)   |
| Mask creation       | `CreateMask`       | JS9 regions (exists)  |

### Decision Matrix

| Integration | Recommended? | Rationale                               |
| ----------- | ------------ | --------------------------------------- |
| MsRaster    | **Yes**      | No alternative for web-based vis plots  |
| iClean      | **Yes**      | Unique capability, high scientist value |
| plotants    | **No**       | Simple enough to implement natively     |
| CreateMask  | **No**       | JS9 already provides this capability    |

---

## Background: casangi Architecture

### Design Philosophy

From the casagui README:

> "For some time, the GUIs provided by CASA have been based upon Qt. While Qt
> works well, the compiled nature of C++ code made building and distributing
> the GUIs for each architecture a hurdle... These experiences have led CASA
> to begin a multi-year transition from being a large C++ framework attached
> to Python to being a pure-Python framework for processing radio astronomy
> data."

casangi chose **Bokeh** as the visualization framework because:

- Extensibility and community support (NumFocus)
- Limited external dependencies (just JavaScript + modern browser)
- Multiple deployment options (CLI, notebook, standalone server, Electron)

### Technology Stack Details

| Layer    | Technology                 | Version Req |
| -------- | -------------------------- | ----------- |
| Backend  | Python 3.8+                | ≥3.8        |
| CASA     | casatools, casatasks       | CASA 6.x    |
| Plotting | Bokeh, HoloViews, Panel    | Bokeh ≥3.0  |
| Data     | xarray, numpy, pandas      | Standard    |
| Server   | Bokeh server, Panel server | Built-in    |

### Deployment Modes

1. **Python CLI** - Direct function calls from scripts
2. **Jupyter Notebook** - Inline display with `show()`
3. **Bokeh Server** - Standalone web application
4. **Electron** - Desktop application wrapper (planned)

---

## Current DSA-110 Frontend Architecture

### Technology Stack

| Component     | Technology            | Purpose                      |
| ------------- | --------------------- | ---------------------------- |
| Framework     | React 18 + TypeScript | Single-page application      |
| Build         | Vite                  | Fast dev server and bundling |
| Visualization | JS9, Aladin Lite, D3  | FITS/sky/chart visualization |
| UI Components | Tailwind CSS + Radix  | Styling and primitives       |
| State         | Zustand               | Global state management      |
| API           | FastAPI backend       | REST endpoints               |
| Testing       | Vitest + Playwright   | Unit and E2E tests           |

### Existing Visualization Components

| Component          | Location                                      | Capability               |
| ------------------ | --------------------------------------------- | ------------------------ |
| `FitsViewer`       | `src/components/fits/FitsViewer.tsx`          | FITS display via JS9     |
| `AladinLiteViewer` | `src/components/widgets/AladinLiteViewer.tsx` | Sky survey overlays      |
| `LightCurveChart`  | `src/components/widgets/LightCurveChart.tsx`  | Time-series plots        |
| `GifPlayer`        | `src/components/widgets/GifPlayer.tsx`        | Animated image sequences |
| `RatingCard`       | `src/components/rating/RatingCard.tsx`        | QA assessment interface  |

### Current Visualization Gaps

| Gap                       | Impact                                     |
| ------------------------- | ------------------------------------------ |
| No MS visibility plots    | Cannot inspect raw/calibrated visibilities |
| No interactive imaging    | tclean runs blind; no mask drawing         |
| No antenna layout display | Cannot visualize flagged antennas          |
| Static-only FITS viewing  | No real-time deconvolution feedback        |

---

## casangi Tool Inventory

### casagui Applications

| Application        | File                                | Size   | Description                     |
| ------------------ | ----------------------------------- | ------ | ------------------------------- |
| `InteractiveClean` | `casagui/apps/_interactiveclean.py` | 241 KB | Visual tclean with mask drawing |
| `MsRaster`         | `casagui/apps/_ms_raster.py`        | 36 KB  | Visibility raster plots         |
| `PlotAnts`         | `casagui/apps/_plotants.py`         | 10 KB  | Antenna position visualization  |
| `CreateMask`       | `casagui/apps/_createmask.py`       | 23 KB  | Interactive mask creation       |
| `CreateRegion`     | `casagui/apps/_createregion.py`     | 26 KB  | Interactive region definition   |

### cubevis Applications

| Application | Description                            |
| ----------- | -------------------------------------- |
| `iclean`    | Wrapper for interactive clean sessions |

### Technology Stack (casangi)

- **Backend**: Python + CASA (casatools/casatasks)
- **Frontend**: Bokeh + JavaScript
- **Deployment**: Python CLI, Jupyter, Electron, Bokeh server

---

## Detailed Tool Analysis

### MsRaster - Visibility Raster Plotting

**Source**: `casagui/apps/_ms_raster.py` (36 KB)

MsRaster creates 2D raster plots of visibility data from Measurement Sets. It
uses HoloViews and Panel for interactive plotting on top of Bokeh.

#### Supported Plot Axes

From the source code analysis:

| Axis Type  | Options                                         |
| ---------- | ----------------------------------------------- |
| X-axis     | `time`, `baseline`, `frequency`, `antenna_name` |
| Y-axis     | `time`, `baseline`, `frequency`, `polarization` |
| Visibility | `amp`, `phase`, `real`, `imag`                  |
| Color by   | Data values with configurable colormaps         |

#### Key API Methods

```python
from casagui.apps import MsRaster

# Initialize with MS path
msr = MsRaster(ms='observation.ms', log_level='info', show_gui=False)

# View data summary
msr.summary()

# Configure styling
msr.set_style_params(
    unflagged_cmap='Viridis',   # Colormap for unflagged data
    flagged_cmap='Reds',         # Colormap for flagged data
    show_colorbar=True,
    show_flagged_colorbar=True
)

# Create raster plot
msr.plot(
    x_axis='baseline',           # Plot x-axis dimension
    y_axis='time',               # Plot y-axis dimension
    vis_axis='amp',              # Visibility component to plot
    selection={'spw_name': '0'}, # Data selection
    aggregator='mean',           # Reduction method
    agg_axis='frequency',        # Axis to aggregate over
    iter_axis='polarization',    # Create plots per pol
    color_mode='auto',           # 'auto', 'manual', or None
    title='Amplitude vs Time'
)

# Display or save
msr.show()                       # Opens in browser
msr.save('output.png')           # Exports to file (png, svg, html, pdf)
```

#### Selection Options

MsRaster supports rich data selection:

```python
selection = {
    'spw_name': '0',                    # Spectral window
    'data_group': 'base',               # Data group name
    'baseline': 'ANT1 & ANT2',          # Specific baseline
    'polarization': 'XX',               # Polarization
    'query': 'TIME > 5000000000'        # Pandas-style query
}
```

#### Aggregation Support

For reducing dimensions when plotting:

| Aggregator | Description              |
| ---------- | ------------------------ |
| `mean`     | Average across dimension |
| `max`      | Maximum value            |
| `min`      | Minimum value            |
| `std`      | Standard deviation       |
| `sum`      | Sum of values            |
| `var`      | Variance                 |

#### Color Range Calculation

The auto color mode calculates optimal limits for amplitude data:

```python
# From _calc_amp_color_limits()
clip_min = max(data_min, mean - 3.0 * std)
clip_max = min(data_max, mean + 3.0 * std)
```

This prevents outliers from dominating the colormap.

---

### InteractiveClean - Visual Deconvolution Control

**Source**: `casagui/apps/_interactiveclean.py` (241 KB)

InteractiveClean wraps CASA's tclean task with a visual interface for:

- Real-time image display during deconvolution
- Interactive mask drawing (polygon, ellipse, rectangle)
- Iteration control (stop, continue, finish)
- Parameter adjustment between major cycles

#### Supported tclean Parameters

From the docstrings, InteractiveClean supports most tclean parameters:

**Data Selection**:

- `vis` - Input visibility file(s)
- `field` - Field selection
- `spw` - Spectral window selection
- `timerange` - Time range selection
- `uvrange` - UV range selection
- `antenna` - Antenna/baseline selection
- `scan`, `observation`, `intent` - Additional selectors

**Image Definition**:

- `imagename` - Output image name prefix
- `imsize` - Image size in pixels (e.g., `[2048, 2048]`)
- `cell` - Cell size (e.g., `'1arcsec'`)
- `phasecenter` - Phase center coordinate
- `stokes` - Stokes parameters (`'I'`, `'IQUV'`, etc.)
- `projection` - Coordinate projection (`'SIN'`, `'NCP'`)

**Spectral**:

- `specmode` - `'mfs'` (continuum) or `'cube'` (spectral line)
- `nchan`, `start`, `width` - Channel specification
- `outframe` - Spectral reference frame
- `restfreq` - Rest frequency for velocity

**Deconvolution**:

- `deconvolver` - Algorithm (`'hogbom'`, `'multiscale'`, `'mtmfs'`)
- `niter` - Maximum iterations
- `threshold` - Stopping threshold
- `cycleniter` - Iterations per major cycle
- `scales` - Multi-scale sizes

**Weighting**:

- `weighting` - `'natural'`, `'uniform'`, `'briggs'`
- `robust` - Briggs robustness parameter

**Gridding**:

- `gridder` - `'standard'`, `'wproject'`, `'mosaic'`, `'awproject'`

#### Interactive Features

The Bokeh interface provides:

1. **Image Display Panel**

   - Current model/residual/restored image
   - Adjustable color scale and stretch
   - WCS coordinate display on hover

2. **Mask Drawing Tools**

   - Polygon tool for irregular regions
   - Ellipse/circle for symmetric regions
   - Rectangle for box regions
   - Union/intersection of masks

3. **Iteration Control**

   - Stop button - Pause after current iteration
   - Continue - Resume with current mask
   - Finish - Complete and save outputs

4. **Statistics Panel**
   - Peak residual flux
   - RMS noise estimate
   - Iteration count
   - Convergence indicators

#### Usage Example

```python
from casagui.apps import InteractiveClean

ic = InteractiveClean(
    vis='observation.ms',
    imagename='output_image',
    imsize=[2048, 2048],
    cell='1arcsec',
    specmode='mfs',
    deconvolver='hogbom',
    niter=10000,
    threshold='0.1mJy',
    weighting='briggs',
    robust=0.5
)

# Launch interactive session (blocks until user finishes)
ic()

# Retrieve masks created during session
masks = ic.masks()
```

---

### plotants - Antenna Position Visualization

**Source**: `casagui/apps/_plotants.py` (10 KB)

A simple tool to display antenna positions from an MS.

#### Features

- Plots antenna positions in local ENU coordinates
- Labels antennas by name (optionally with ID)
- Supports logarithmic position scaling for VLBA
- Exports to PNG, SVG, or PDF

#### API

```python
from casagui.apps import plotants

plotants(
    vis='observation.ms',       # Input MS
    figfile='antennas.png',     # Output file (optional)
    antindex=True,              # Show antenna IDs
    logpos=False,               # Logarithmic positions (VLBA)
    exclude=[2, 3],             # Exclude specific antennas
    checkbaselines=False,       # Only plot antennas in MAIN table
    title='DSA-110 Array',      # Plot title
    showgui=True                # Display in browser
)
```

#### Coordinate Conversion

From the source code, positions are converted from ITRF to local ENU:

```python
# Convert WGS84 to local coordinates
# X is east, Y is north, Z is up
rade = 6370000.0  # Earth radius in meters
ant_xs = (ant_lons - array_lon) * rade * np.cos(array_lat)
ant_ys = (ant_lats - array_lat) * rade
```

**Note**: This is an approximation that doesn't account for Earth's ellipticity.

---

## Integration Opportunities

### 1. MsRaster → MSDetailPage Enhancement

**Priority**: ⭐⭐⭐ High  
**Effort**: Medium  
**Value**: High (fills major gap in MS inspection)

#### 1.1 Current State

`MSDetailPage.tsx` displays only metadata:

- Path, pointing coordinates, timestamps
- Calibrator matches
- QA grade and summary
- Links to related images

**Missing**: No visualization of the actual visibility data.

#### 1.2 Proposed Enhancement

Add visibility raster plots showing:

- Amplitude vs. time (per baseline)
- Amplitude vs. channel (bandpass shape)
- Phase vs. time
- Flagging summary heatmap

#### 1.3 DSA-110 Specific Considerations

**Data Characteristics**:

| Property        | DSA-110 Value                |
| --------------- | ---------------------------- |
| Antennas        | 110 (63 currently active)    |
| Baselines       | ~2000 (active)               |
| Channels        | 768 (16 subbands × 48)       |
| Polarizations   | 4 (XX, XY, YX, YY)           |
| Time samples    | ~24 per 5-minute observation |
| Typical MS size | 2-4 GB                       |

**Performance Requirements**:

- Initial plot should render in <30 seconds
- Subsequent axis changes should be faster (cached data)
- Handle partial data gracefully (flagged baselines)

**Recommended Plot Types for DSA-110**:

1. **Bandpass Check** - Amplitude vs. frequency, aggregated over time
2. **Time Evolution** - Amplitude vs. time, single baseline or aggregated
3. **UV Coverage** - Baseline length vs. time (diagnostic)
4. **Flagging Summary** - Heatmap of flagged fraction per antenna

#### 1.4 Integration Options

##### Option A: Backend PNG Rendering (Recommended for Phase 1)

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  React Frontend │────▶│  FastAPI Backend │────▶│  casagui/MsRaster│
│  MSDetailPage   │◀────│  /ms/{id}/raster │◀────│  (matplotlib)   │
└─────────────────┘     └──────────────────┘     └─────────────────┘
        │                       │                        │
        │  GET /ms/.../raster   │   render PNG           │
        │  ?xaxis=time          │   to BytesIO           │
        │  &yaxis=amp           │                        │
        └───────────────────────┴────────────────────────┘
```

#### 1.4.1 Step-by-Step Implementation (Option A)

**Step 1: Add API Route** (`backend/src/dsa110_contimg/api/routes/ms.py`)

Add to existing `ms.py` routes file after line 110:

```python
import io
from typing import Optional
from fastapi.responses import StreamingResponse
from urllib.parse import unquote

@router.get("/{encoded_path:path}/raster")
async def get_ms_raster(
    encoded_path: str,
    xaxis: str = "time",
    yaxis: str = "amp",
    colorby: str = "amp",
    spw: Optional[str] = None,
    antenna: Optional[str] = None,
    aggregator: str = "mean",
    width: int = 800,
    height: int = 600,
) -> StreamingResponse:
    """
    Generate visibility raster plot for a Measurement Set.

    Args:
        encoded_path: URL-encoded path to MS
        xaxis: X-axis dimension (time, baseline, frequency)
        yaxis: Y-axis dimension (amp, phase, real, imag)
        colorby: Color dimension (amp, phase)
        spw: Spectral window filter (e.g., "0", "0~3")
        antenna: Antenna filter (e.g., "ANT1 & ANT2")
        aggregator: Aggregation method (mean, max, min, std)
        width: Output image width in pixels
        height: Output image height in pixels

    Returns:
        PNG image as streaming response

    Raises:
        RecordNotFoundError: If MS not found
        HTTPException: If casagui fails to render
    """
    from casagui.apps import MsRaster
    from pathlib import Path

    ms_path = unquote(encoded_path)

    if not Path(ms_path).exists():
        raise RecordNotFoundError("MeasurementSet", ms_path)

    try:
        # Initialize MsRaster with low-level settings
        msr = MsRaster(ms=ms_path, log_level='warning', show_gui=False)

        # Configure selection if filters provided
        selection = {}
        if spw:
            selection['spw_name'] = spw
        if antenna:
            selection['baseline'] = antenna

        # Create the plot
        msr.plot(
            x_axis=xaxis,
            y_axis='time' if yaxis in ('amp', 'phase') else yaxis,
            vis_axis=yaxis if yaxis in ('amp', 'phase', 'real', 'imag') else 'amp',
            selection=selection if selection else None,
            aggregator=aggregator,
            color_mode='auto',
        )

        # Render to PNG buffer
        buf = io.BytesIO()
        msr.save(buf, format='png', width=width, height=height)
        buf.seek(0)

        return StreamingResponse(
            buf,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=300",  # Cache 5 min
                "X-MS-Path": ms_path,
            }
        )

    except Exception as e:
        logger.exception(f"Failed to generate raster for {ms_path}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate raster plot: {str(e)}"
        )
```

**Step 2: Add Pydantic Schema** (`backend/src/dsa110_contimg/api/schemas.py`)

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class RasterPlotParams(BaseModel):
    """Parameters for visibility raster plot."""
    xaxis: Literal["time", "baseline", "frequency"] = "time"
    yaxis: Literal["amp", "phase", "real", "imag"] = "amp"
    colorby: Literal["amp", "phase"] = "amp"
    spw: Optional[str] = Field(None, description="Spectral window filter")
    antenna: Optional[str] = Field(None, description="Antenna/baseline filter")
    aggregator: Literal["mean", "max", "min", "std"] = "mean"
    width: int = Field(800, ge=200, le=2000)
    height: int = Field(600, ge=200, le=2000)
```

**Step 3: Create Frontend Component**

Create new file `frontend/src/components/ms/MsRasterPlot.tsx`:

```tsx
import React, { useState } from 'react';
import { config } from '../../config';

export type RasterAxis = 'time' | 'baseline' | 'frequency';
export type RasterVisAxis = 'amp' | 'phase' | 'real' | 'imag';

interface MsRasterPlotProps {
  /** Full path to the Measurement Set */
  msPath: string;
  /** Initial X-axis selection */
  initialXAxis?: RasterAxis;
  /** Initial Y-axis (visibility component) */
  initialYAxis?: RasterVisAxis;
  /** Optional spectral window filter */
  spw?: string;
  /** Optional antenna filter */
  antenna?: string;
  /** CSS class name */
  className?: string;
}

/**
 * Visibility raster plot component.
 * Renders amplitude/phase vs time/channel from a Measurement Set.
 */
const MsRasterPlot: React.FC<MsRasterPlotProps> = ({
  msPath,
  initialXAxis = 'time',
  initialYAxis = 'amp',
  spw,
  antenna,
  className = '',
}) => {
  const [xaxis, setXAxis] = useState<RasterAxis>(initialXAxis);
  const [yaxis, setYAxis] = useState<RasterVisAxis>(initialYAxis);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Build URL with query params
  const params = new URLSearchParams({
    xaxis,
    yaxis,
    ...(spw && { spw }),
    ...(antenna && { antenna }),
  });

  const url = `${config.api.baseUrl}/ms/${encodeURIComponent(msPath)}/raster?${params}`;

  return (
    <div className={`bg-gray-900 rounded-lg overflow-hidden ${className}`}>
      {/* Controls */}
      <div className="flex items-center gap-4 p-3 bg-gray-800 border-b border-gray-700">
        <label className="flex items-center gap-2 text-sm text-gray-300">
          X-axis:
          <select
            value={xaxis}
            onChange={(e) => setXAxis(e.target.value as RasterAxis)}
            className="bg-gray-700 text-white rounded px-2 py-1 text-sm"
          >
            <option value="time">Time</option>
            <option value="baseline">Baseline</option>
            <option value="frequency">Frequency</option>
          </select>
        </label>

        <label className="flex items-center gap-2 text-sm text-gray-300">
          Plot:
          <select
            value={yaxis}
            onChange={(e) => setYAxis(e.target.value as RasterVisAxis)}
            className="bg-gray-700 text-white rounded px-2 py-1 text-sm"
          >
            <option value="amp">Amplitude</option>
            <option value="phase">Phase</option>
            <option value="real">Real</option>
            <option value="imag">Imaginary</option>
          </select>
        </label>
      </div>

      {/* Image container */}
      <div className="relative aspect-[4/3]">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="animate-pulse text-gray-500">Generating plot...</div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900">
            <div className="text-red-400 text-sm">{error}</div>
          </div>
        )}

        <img
          src={url}
          alt={`${yaxis} vs ${xaxis}`}
          className="w-full h-full object-contain"
          onLoad={() => {
            setIsLoading(false);
            setError(null);
          }}
          onError={() => {
            setIsLoading(false);
            setError('Failed to load raster plot');
          }}
        />
      </div>
    </div>
  );
};

export default MsRasterPlot;
```

**Step 4: Add Query Hook** (`frontend/src/hooks/useQueries.ts`)

Add to the existing query keys:

```typescript
export const queryKeys = {
  // ... existing keys ...

  // MS Raster plots (for prefetching)
  msRaster: (path: string, params: object) => ['ms', path, 'raster', params] as const,
};
```

**Step 5: Integrate into MSDetailPage**

Modify `frontend/src/pages/MSDetailPage.tsx`:

```tsx
// Add import at top
import MsRasterPlot from '../components/ms/MsRasterPlot';

// Add inside the main grid, after the Metadata card:
{
  /* Visibility Raster */
}
<Card title="Visibility Plot">
  <MsRasterPlot
    msPath={ms.path}
    initialXAxis="time"
    initialYAxis="amp"
    className="rounded-lg overflow-hidden"
  />
</Card>;
```

**Step 6: Add Index Export** (`frontend/src/components/ms/index.ts`)

Create the directory and index file:

```typescript
export { default as MsRasterPlot } from './MsRasterPlot';
export type { RasterAxis, RasterVisAxis } from './MsRasterPlot';
```

#### 1.4.2 Testing Checklist

**Backend Tests** (`backend/tests/api/test_ms_raster.py`):

```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

def test_raster_endpoint_returns_png(client: TestClient, mock_ms_path: str):
    """Verify endpoint returns valid PNG."""
    with patch("casagui.apps.MsRaster") as mock_raster:
        # Mock the save method to return valid PNG bytes
        mock_instance = MagicMock()
        mock_raster.return_value = mock_instance

        response = client.get(f"/api/ms/{mock_ms_path}/raster")

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"


def test_raster_endpoint_validates_params(client: TestClient, mock_ms_path: str):
    """Verify invalid params return 422."""
    response = client.get(
        f"/api/ms/{mock_ms_path}/raster",
        params={"xaxis": "invalid"}
    )
    assert response.status_code == 422


def test_raster_endpoint_handles_missing_ms(client: TestClient):
    """Verify 404 for non-existent MS."""
    response = client.get("/api/ms/nonexistent.ms/raster")
    assert response.status_code == 404
```

**Frontend Tests** (`frontend/src/components/ms/MsRasterPlot.test.tsx`):

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import MsRasterPlot from './MsRasterPlot';

describe('MsRasterPlot', () => {
  it('renders with loading state', () => {
    render(<MsRasterPlot msPath="/test/observation.ms" />);
    expect(screen.getByText('Generating plot...')).toBeInTheDocument();
  });

  it('updates URL when axis changes', () => {
    render(<MsRasterPlot msPath="/test/observation.ms" />);
    const select = screen.getByLabelText(/X-axis/);
    fireEvent.change(select, { target: { value: 'frequency' } });
    // Verify img src contains new axis param
  });
});
```

##### Option B: Bokeh Server Embedding (Phase 2)

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  React Frontend │────▶│  Bokeh Server    │────▶│  MsRaster App   │
│  <iframe>       │◀────│  :5006/msraster  │◀────│  (interactive)  │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

- Full interactivity (pan, zoom, hover tooltips)
- Requires Bokeh server process management
- Session state complexity

#### 1.5 Acceptance Criteria

- [ ] API endpoint returns valid PNG for any MS path
- [ ] Frontend displays raster plot on MSDetailPage
- [ ] User can toggle between time/channel/baseline views
- [ ] Error handling for missing/invalid MS files
- [ ] Loading state while plot generates
- [ ] Caching for repeated requests (same MS, same params)

---

### 2. InteractiveClean → Interactive Imaging Page

**Priority**: ⭐⭐⭐ High  
**Effort**: High  
**Value**: Very High (enables interactive science)

#### 2.1 Current State

Pipeline imaging is non-interactive:

- `ImagingStage` runs tclean/WSClean with fixed parameters
- No visual feedback during deconvolution
- No mask drawing capability
- Failed images require CLI re-runs

#### 2.2 Proposed Enhancement

Add interactive imaging workflow:

1. User selects MS from list or QA failure
2. Opens interactive clean session
3. Draws masks, adjusts parameters
4. Monitors deconvolution progress
5. Results automatically registered in products DB

#### 2.3 DSA-110 Specific Configuration

Recommended default parameters for DSA-110 continuum imaging:

```python
ICLEAN_DEFAULTS = {
    'imsize': [5040, 5040],           # Match current pipeline
    'cell': '2.5arcsec',              # DSA-110 resolution
    'specmode': 'mfs',                # Continuum only
    'deconvolver': 'hogbom',          # Fast for point sources
    'weighting': 'briggs',
    'robust': 0.5,
    'gridder': 'standard',            # No w-projection needed
    'niter': 10000,
    'threshold': '0.5mJy',            # Typical noise floor
    'pbcor': True,                    # Always apply PB correction
    'datacolumn': 'corrected',        # Use calibrated data
}
```

#### 2.4 Integration Options

##### Option A: Standalone Bokeh App (Recommended)

```text
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  React Frontend │────▶│  FastAPI Backend │────▶│  InteractiveClean   │
│  "Open iClean"  │     │  launches process│     │  Bokeh Server       │
│  button         │     │  returns URL     │     │  :5007/iclean/{id}  │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
        │                                                  │
        │  window.open(bokeh_url)                          │
        └──────────────────────────────────────────────────┘
```

**Rationale**: DSA-110 MS files are 2-4GB. Launching interactive clean in a
separate browser tab allows the main dashboard to remain responsive while the
resource-intensive imaging session runs.

Implementation:

1. API endpoint to launch iClean session:

   ```python
   @router.post("/imaging/interactive")
   async def start_interactive_clean(
       ms_path: str,
       imagename: str,
       imsize: int = 5040,      # DSA-110 default
       cell: str = "2.5arcsec", # DSA-110 resolution
   ) -> dict:
       """Launch interactive clean session."""
       session_id = str(uuid.uuid4())

       # Start Bokeh server with session
       proc = subprocess.Popen([
           "python", "-m", "casagui.apps",
           "--session-id", session_id,
           "--ms", ms_path,
           "--imagename", imagename,
       ])

       return {
           "session_id": session_id,
           "url": f"http://localhost:5007/iclean/{session_id}",
           "status": "started"
       }
   ```

2. Frontend integration:

   ```tsx
   // src/pages/InteractiveImagingPage.tsx

   const InteractiveImagingPage: React.FC = () => {
     const [session, setSession] = useState<ICleanSession | null>(null);

     const startSession = async (msPath: string) => {
       const response = await api.post('/imaging/interactive', {
         ms_path: msPath,
       });
       setSession(response.data);
       window.open(response.data.url, '_blank');
     };

     return (
       <div>
         <MSSelector onSelect={startSession} />
         {session && <SessionStatus session={session} />}
       </div>
     );
   };
   ```

#### 2.4.1 Step-by-Step Implementation (Interactive Clean)

**Step 1: Create Session Manager Service**

Create `backend/src/dsa110_contimg/api/services/bokeh_sessions.py`:

```python
"""
Bokeh session manager for interactive visualization tools.

Manages lifecycle of Bokeh server processes for InteractiveClean sessions.
"""
from __future__ import annotations

import asyncio
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class BokehSession:
    """Represents a running Bokeh server session."""
    id: str
    port: int
    process: subprocess.Popen
    ms_path: str
    imagename: str
    created_at: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}/iclean/{self.id}"

    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()


class PortPool:
    """Manages a pool of available ports for Bokeh servers."""

    def __init__(self, port_range: range):
        self.available = set(port_range)
        self.in_use: Dict[str, int] = {}  # session_id -> port

    def acquire(self, session_id: str) -> int:
        if not self.available:
            raise RuntimeError("No ports available in pool")
        port = self.available.pop()
        self.in_use[session_id] = port
        return port

    def release(self, session_id: str) -> None:
        if session_id in self.in_use:
            port = self.in_use.pop(session_id)
            self.available.add(port)


class BokehSessionManager:
    """
    Manages Bokeh server sessions for interactive tools.

    Usage:
        manager = BokehSessionManager()
        session = await manager.create_session("iclean", {...params})
        # Later...
        await manager.cleanup_session(session.id)
    """

    def __init__(self, port_range: range = range(5010, 5100)):
        self.sessions: Dict[str, BokehSession] = {}
        self.port_pool = PortPool(port_range)
        self._cleanup_task: Optional[asyncio.Task] = None

    async def create_session(
        self,
        ms_path: str,
        imagename: str,
        params: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> BokehSession:
        """
        Launch new InteractiveClean Bokeh session.

        Args:
            ms_path: Path to Measurement Set
            imagename: Output image name prefix
            params: Optional tclean parameters
            user_id: Optional user identifier for tracking

        Returns:
            BokehSession with connection details
        """
        session_id = str(uuid.uuid4())
        port = self.port_pool.acquire(session_id)

        # DSA-110 default parameters
        default_params = {
            'imsize': [5040, 5040],
            'cell': '2.5arcsec',
            'specmode': 'mfs',
            'deconvolver': 'hogbom',
            'weighting': 'briggs',
            'robust': 0.5,
            'niter': 10000,
            'threshold': '0.5mJy',
        }
        if params:
            default_params.update(params)

        # Build command
        cmd = [
            "python", "-c",
            f'''
from casagui.apps import InteractiveClean
ic = InteractiveClean(
    vis="{ms_path}",
    imagename="{imagename}",
    imsize={default_params['imsize']},
    cell="{default_params['cell']}",
    specmode="{default_params['specmode']}",
    deconvolver="{default_params['deconvolver']}",
    weighting="{default_params['weighting']}",
    robust={default_params['robust']},
    niter={default_params['niter']},
    threshold="{default_params['threshold']}",
)
ic.serve(port={port})
'''
        ]

        logger.info(f"Starting iClean session {session_id} on port {port}")

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env={**os.environ, "BOKEH_ALLOW_WS_ORIGIN": "*"},
        )

        session = BokehSession(
            id=session_id,
            port=port,
            process=proc,
            ms_path=ms_path,
            imagename=imagename,
            user_id=user_id,
        )
        self.sessions[session_id] = session

        # Wait briefly for server to start
        await asyncio.sleep(2.0)

        # Check if process is still running
        if proc.poll() is not None:
            self.port_pool.release(session_id)
            stderr = proc.stderr.read().decode() if proc.stderr else "Unknown error"
            raise RuntimeError(f"Bokeh server failed to start: {stderr}")

        return session

    async def get_session(self, session_id: str) -> Optional[BokehSession]:
        """Get session by ID."""
        return self.sessions.get(session_id)

    async def cleanup_session(self, session_id: str) -> None:
        """Terminate session and free resources."""
        session = self.sessions.pop(session_id, None)
        if session:
            logger.info(f"Cleaning up session {session_id}")
            session.process.terminate()
            try:
                session.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                session.process.kill()
            self.port_pool.release(session_id)

    async def cleanup_stale_sessions(self, max_age_hours: float = 4.0) -> int:
        """Clean up sessions older than max_age_hours. Returns count cleaned."""
        cutoff_seconds = max_age_hours * 3600
        stale = [
            sid for sid, session in self.sessions.items()
            if session.age_seconds > cutoff_seconds
        ]
        for sid in stale:
            await self.cleanup_session(sid)
        return len(stale)

    def list_sessions(self) -> list[dict]:
        """List all active sessions."""
        return [
            {
                "id": s.id,
                "url": s.url,
                "ms_path": s.ms_path,
                "created_at": s.created_at.isoformat(),
                "age_seconds": s.age_seconds,
            }
            for s in self.sessions.values()
        ]


# Singleton instance
_manager: Optional[BokehSessionManager] = None

def get_session_manager() -> BokehSessionManager:
    global _manager
    if _manager is None:
        _manager = BokehSessionManager()
    return _manager
```

**Step 2: Add API Routes**

Create `backend/src/dsa110_contimg/api/routes/imaging.py`:

```python
"""
Interactive imaging routes.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List

from ..services.bokeh_sessions import get_session_manager, BokehSessionManager

router = APIRouter(prefix="/imaging", tags=["imaging"])


class InteractiveCleanRequest(BaseModel):
    """Request to start interactive clean session."""
    ms_path: str = Field(..., description="Path to Measurement Set")
    imagename: str = Field(..., description="Output image name prefix")
    imsize: List[int] = Field([5040, 5040], description="Image size in pixels")
    cell: str = Field("2.5arcsec", description="Cell size")
    niter: int = Field(10000, description="Maximum iterations")
    threshold: str = Field("0.5mJy", description="Stopping threshold")


class InteractiveCleanResponse(BaseModel):
    """Response with session details."""
    session_id: str
    url: str
    status: str


@router.post("/interactive", response_model=InteractiveCleanResponse)
async def start_interactive_clean(
    request: InteractiveCleanRequest,
    manager: BokehSessionManager = Depends(get_session_manager),
) -> InteractiveCleanResponse:
    """
    Launch an interactive clean session.

    Opens a Bokeh server running InteractiveClean for the specified MS.
    Returns a URL that can be opened in a new browser tab.
    """
    from pathlib import Path

    if not Path(request.ms_path).exists():
        raise HTTPException(404, f"MS not found: {request.ms_path}")

    try:
        session = await manager.create_session(
            ms_path=request.ms_path,
            imagename=request.imagename,
            params={
                "imsize": request.imsize,
                "cell": request.cell,
                "niter": request.niter,
                "threshold": request.threshold,
            },
        )
        return InteractiveCleanResponse(
            session_id=session.id,
            url=session.url,
            status="started",
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to start session: {e}")


@router.get("/sessions")
async def list_sessions(
    manager: BokehSessionManager = Depends(get_session_manager),
) -> list[dict]:
    """List all active interactive sessions."""
    return manager.list_sessions()


@router.delete("/sessions/{session_id}")
async def stop_session(
    session_id: str,
    manager: BokehSessionManager = Depends(get_session_manager),
) -> dict:
    """Stop and cleanup an interactive session."""
    session = await manager.get_session(session_id)
    if not session:
        raise HTTPException(404, f"Session not found: {session_id}")

    await manager.cleanup_session(session_id)
    return {"status": "stopped", "session_id": session_id}
```

**Step 3: Register Routes**

In `backend/src/dsa110_contimg/api/app.py`, add:

```python
from .routes import imaging

app.include_router(imaging.router, prefix="/api")
```

**Step 4: Frontend Launch Button**

Add to `frontend/src/pages/MSDetailPage.tsx` in the Actions card:

```tsx
<button
  type="button"
  className="btn btn-primary"
  onClick={async () => {
    try {
      const response = await fetch(`${config.api.baseUrl}/imaging/interactive`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ms_path: ms.path,
          imagename: ms.path.replace('.ms', '.interactive'),
        }),
      });
      if (!response.ok) throw new Error('Failed to start session');
      const data = await response.json();
      window.open(data.url, '_blank', 'noopener,noreferrer');
    } catch (error) {
      console.error('Failed to launch interactive clean:', error);
      // Show error toast
    }
  }}
>
  <PlayIcon className="w-4 h-4 mr-2" />
  Interactive Clean
</button>
```

**Step 5: Add Session Cleanup Background Task**

In `backend/src/dsa110_contimg/api/app.py`:

```python
from contextlib import asynccontextmanager
from .services.bokeh_sessions import get_session_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    manager = get_session_manager()

    # Start background cleanup task
    async def cleanup_loop():
        while True:
            await asyncio.sleep(3600)  # Check hourly
            count = await manager.cleanup_stale_sessions(max_age_hours=4.0)
            if count:
                logger.info(f"Cleaned up {count} stale Bokeh sessions")

    cleanup_task = asyncio.create_task(cleanup_loop())

    yield

    # Shutdown
    cleanup_task.cancel()
    # Cleanup all sessions
    for session_id in list(manager.sessions.keys()):
        await manager.cleanup_session(session_id)

app = FastAPI(lifespan=lifespan)
```

##### Option B: Embedded iframe (Phase 3)

More complex but unified UX:

- Embed Bokeh output directly in React page
- WebSocket bridge for bidirectional communication
- Session management and cleanup

#### Data Flow

```text
User Action                    System Response
───────────────────────────────────────────────────────────
1. Select MS                   Validate MS, show metadata
2. Set imaging params          Pre-populate from defaults
3. Click "Start Interactive"   Launch Bokeh process
4. Draw masks in Bokeh UI      Masks saved to session
5. Click "Run" in Bokeh        tclean executes
6. View residuals              Updates in real-time
7. Stop/Continue               Iteration control
8. Click "Finish"              Products registered in DB
9. Return to React             Show new image in detail page
```

#### Acceptance Criteria

- [ ] User can launch iClean from MSDetailPage or ImageDetailPage
- [ ] Bokeh session opens in new tab with MS loaded
- [ ] Masks drawn in session are persisted
- [ ] Completed images appear in products DB
- [ ] Session cleanup on browser close
- [ ] Error handling for CASA failures

---

### 3. PlotAnts → Antenna Diagnostics Widget

**Priority**: ⭐⭐ Medium  
**Effort**: Low  
**Value**: Medium (useful for QA diagnostics)

#### 3.1 Current State

No antenna visualization in frontend. Flagging status only visible via:

- CLI flagdata summaries
- Log files
- No spatial correlation of bad antennas

#### 3.2 DSA-110 Antenna Considerations

DSA-110 has unique antenna configuration:

| Property               | Value                            |
| ---------------------- | -------------------------------- |
| Total antennas         | 110                              |
| Array configuration    | T-shaped                         |
| East-West arm length   | ~1.2 km                          |
| North-South arm length | ~0.3 km                          |
| Typical baselines      | ~2000                            |
| Coordinate source      | `DSA110_Station_Coordinates.csv` |

#### 3.3 Proposed Enhancement

Add antenna layout widget showing:

- Physical antenna positions (ENU projection from ITRF)
- Color-coded by flagging percentage
- Hover for antenna details (name, flagged %, baseline count)
- Click to see baseline statistics
- T-shaped layout properly rendered

#### 3.4 Implementation Recommendation: Native D3/SVG

**casagui's plotants is NOT needed**. Implement natively in React:

**Rationale**:

- DSA-110 has known, fixed antenna positions
- Static visualization (no interactive features needed beyond tooltips)
- Avoids Python dependency for a simple 2D plot
- Faster render (no server round-trip)

```tsx
// src/components/antenna/AntennaLayoutWidget.tsx

interface Antenna {
  id: number;
  name: string;
  x: number; // East offset in meters (ENU)
  y: number; // North offset in meters (ENU)
  flagged_pct: number;
  baseline_count: number;
}

const AntennaLayoutWidget: React.FC<{ msPath: string }> = ({ msPath }) => {
  const { data: antennas } = useAntennaPositions(msPath);

  // DSA-110 T-shape layout extents
  const viewBox = '-800 -200 1600 600'; // Wider EW, narrower NS

  return (
    <svg viewBox={viewBox} className="w-full h-48">
      {/* Grid lines for scale */}
      <line x1="-600" y1="0" x2="600" y2="0" stroke="#333" strokeDasharray="4" />
      <line x1="0" y1="-150" x2="0" y2="300" stroke="#333" strokeDasharray="4" />

      {/* Antenna markers */}
      {antennas?.map((ant) => (
        <g key={ant.id}>
          <circle
            cx={ant.x / 2} // Scale for SVG
            cy={-ant.y / 2} // Flip Y for screen coords
            r={8}
            fill={getFlagColor(ant.flagged_pct)}
            className="cursor-pointer hover:stroke-white hover:stroke-2"
          />
          <title>{`${ant.name}: ${ant.flagged_pct.toFixed(1)}% flagged`}</title>
        </g>
      ))}

      {/* Scale bar */}
      <g transform="translate(-600, 250)">
        <line x1="0" y1="0" x2="100" y2="0" stroke="white" strokeWidth="2" />
        <text x="50" y="20" fill="white" textAnchor="middle" fontSize="12">
          200m
        </text>
      </g>
    </svg>
  );
};

function getFlagColor(pct: number): string {
  if (pct > 50) return '#EF4444'; // red - severe flagging
  if (pct > 20) return '#F59E0B'; // amber - moderate flagging
  return '#22C55E'; // green - good
}
```

#### 3.5 Step-by-Step Implementation (Antenna Widget)

**Step 1: Create Backend Endpoint**

Add to `backend/src/dsa110_contimg/api/routes/ms.py`:

```python
import numpy as np
from typing import List

@router.get("/{encoded_path:path}/antennas")
async def get_antenna_info(encoded_path: str) -> List[dict]:
    """
    Get antenna positions and flagging statistics for a Measurement Set.

    Returns antenna positions in ENU coordinates (meters) relative to
    array center, along with flagging statistics calculated from the
    FLAG column.
    """
    from casacore.tables import table
    from dsa110_contimg.utils.antpos_local import get_itrf
    from pathlib import Path

    ms_path = unquote(encoded_path)

    if not Path(ms_path).exists():
        raise RecordNotFoundError("MeasurementSet", ms_path)

    # Get authoritative DSA-110 antenna positions
    itrf_df = get_itrf()

    # Convert ITRF to local ENU coordinates
    # Array center (approximate)
    center_lat = np.deg2rad(37.2339)  # DSA-110 latitude
    center_lon = np.deg2rad(-118.2817)  # DSA-110 longitude

    # ITRF to ENU rotation
    def itrf_to_enu(itrf_xyz: np.ndarray) -> np.ndarray:
        """Convert ITRF XYZ to local ENU."""
        # Simplified conversion for display purposes
        # Center on array mean position
        center = itrf_xyz.mean(axis=0)
        offset = itrf_xyz - center

        # Rotation matrix (approximate for DSA-110 location)
        sin_lat, cos_lat = np.sin(center_lat), np.cos(center_lat)
        sin_lon, cos_lon = np.sin(center_lon), np.cos(center_lon)

        R = np.array([
            [-sin_lon, cos_lon, 0],
            [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
            [cos_lat * cos_lon, cos_lat * sin_lon, sin_lat],
        ])
        return (R @ offset.T).T

    itrf_xyz = itrf_df[['x_m', 'y_m', 'z_m']].values
    enu_coords = itrf_to_enu(itrf_xyz)

    # Calculate per-antenna flagging percentage
    flag_pcts = {}
    try:
        with table(ms_path, readonly=True) as ms:
            flags = ms.getcol("FLAG")  # (nrow, nchan, npol)
            ant1 = ms.getcol("ANTENNA1")
            ant2 = ms.getcol("ANTENNA2")

            # Flatten to per-row flag fraction
            row_flagged = np.mean(flags, axis=(1, 2))  # (nrow,)

            # Accumulate per antenna
            for ant_id in range(len(itrf_df)):
                mask = (ant1 == ant_id) | (ant2 == ant_id)
                if mask.sum() > 0:
                    flag_pcts[ant_id] = float(row_flagged[mask].mean() * 100)
                else:
                    flag_pcts[ant_id] = 0.0

    except Exception as e:
        logger.warning(f"Could not compute flagging stats: {e}")
        # Return zeros if flagging can't be computed
        for i in range(len(itrf_df)):
            flag_pcts[i] = 0.0

    return [
        {
            "id": i,
            "name": row.name if hasattr(row, 'name') else f"ANT{i}",
            "x": float(enu_coords[i, 0]),  # East (meters)
            "y": float(enu_coords[i, 1]),  # North (meters)
            "flagged_pct": flag_pcts.get(i, 0.0),
        }
        for i, row in enumerate(itrf_df.itertuples())
    ]
```

**Step 2: Create Frontend Hook**

Add to `frontend/src/hooks/useQueries.ts`:

```typescript
// Add to queryKeys
export const queryKeys = {
  // ... existing keys ...
  msAntennas: (path: string) => ['ms', path, 'antennas'] as const,
};

// Add hook
export interface AntennaInfo {
  id: number;
  name: string;
  x: number;
  y: number;
  flagged_pct: number;
}

export function useAntennaPositions(msPath: string | undefined) {
  return useQuery({
    queryKey: queryKeys.msAntennas(msPath ?? ''),
    queryFn: async () => {
      const response = await apiClient.get<AntennaInfo[]>(
        `/ms/${encodeURIComponent(msPath ?? '')}/antennas`
      );
      return response.data;
    },
    enabled: !!msPath,
    staleTime: 5 * 60 * 1000, // Cache 5 minutes (positions don't change)
  });
}
```

**Step 3: Create Component**

Create `frontend/src/components/antenna/AntennaLayoutWidget.tsx`:

```tsx
import React, { useMemo } from 'react';
import { useAntennaPositions, AntennaInfo } from '../../hooks/useQueries';

interface AntennaLayoutWidgetProps {
  /** Path to the Measurement Set */
  msPath: string;
  /** Widget height in pixels */
  height?: number;
  /** Whether to show legend */
  showLegend?: boolean;
  /** CSS class name */
  className?: string;
}

/**
 * Antenna layout visualization showing DSA-110 T-shaped array.
 * Antennas are color-coded by flagging percentage.
 */
const AntennaLayoutWidget: React.FC<AntennaLayoutWidgetProps> = ({
  msPath,
  height = 200,
  showLegend = true,
  className = '',
}) => {
  const { data: antennas, isLoading, error } = useAntennaPositions(msPath);

  // Calculate SVG viewBox based on antenna positions
  const viewBox = useMemo(() => {
    if (!antennas?.length) return '-800 -300 1600 600';

    const xs = antennas.map((a) => a.x);
    const ys = antennas.map((a) => a.y);
    const minX = Math.min(...xs) - 100;
    const maxX = Math.max(...xs) + 100;
    const minY = Math.min(...ys) - 100;
    const maxY = Math.max(...ys) + 100;

    // Scale to fit, maintaining aspect ratio
    const width = maxX - minX;
    const height = maxY - minY;

    return `${minX} ${-maxY} ${width} ${height}`;
  }, [antennas]);

  if (isLoading) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-900 rounded-lg ${className}`}
        style={{ height }}
      >
        <div className="animate-pulse text-gray-500">Loading antennas...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className={`flex items-center justify-center bg-gray-900 rounded-lg ${className}`}
        style={{ height }}
      >
        <div className="text-red-400 text-sm">Failed to load antenna data</div>
      </div>
    );
  }

  return (
    <div className={`bg-gray-900 rounded-lg overflow-hidden ${className}`}>
      <svg viewBox={viewBox} style={{ height }} className="w-full">
        {/* Background grid */}
        <defs>
          <pattern id="grid" width="100" height="100" patternUnits="userSpaceOnUse">
            <path d="M 100 0 L 0 0 0 100" fill="none" stroke="#333" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#grid)" />

        {/* Axis lines */}
        <line
          x1="-1000"
          y1="0"
          x2="1000"
          y2="0"
          stroke="#555"
          strokeWidth="1"
          strokeDasharray="10,5"
        />
        <line
          x1="0"
          y1="-500"
          x2="0"
          y2="500"
          stroke="#555"
          strokeWidth="1"
          strokeDasharray="10,5"
        />

        {/* Antenna markers */}
        {antennas?.map((ant) => (
          <g key={ant.id} className="antenna-marker">
            <circle
              cx={ant.x}
              cy={-ant.y} // Flip Y for screen coordinates
              r={12}
              fill={getFlagColor(ant.flagged_pct)}
              stroke="#000"
              strokeWidth="1"
              className="cursor-pointer transition-all hover:r-[16] hover:stroke-white hover:stroke-2"
            />
            {/* Tooltip via title element */}
            <title>
              {ant.name}
              {'\n'}Flagged: {ant.flagged_pct.toFixed(1)}%{'\n'}
              Position: ({ant.x.toFixed(0)}m E, {ant.y.toFixed(0)}m N)
            </title>
          </g>
        ))}

        {/* Scale bar */}
        <g transform="translate(-700, 200)">
          <line x1="0" y1="0" x2="200" y2="0" stroke="white" strokeWidth="2" />
          <line x1="0" y1="-5" x2="0" y2="5" stroke="white" strokeWidth="2" />
          <line x1="200" y1="-5" x2="200" y2="5" stroke="white" strokeWidth="2" />
          <text
            x="100"
            y="20"
            fill="white"
            textAnchor="middle"
            fontSize="14"
            fontFamily="sans-serif"
          >
            200 m
          </text>
        </g>

        {/* Direction labels */}
        <text x="750" y="0" fill="#888" textAnchor="start" fontSize="14" dominantBaseline="middle">
          E
        </text>
        <text
          x="0"
          y="-280"
          fill="#888"
          textAnchor="middle"
          fontSize="14"
          dominantBaseline="middle"
        >
          N
        </text>
      </svg>

      {/* Legend */}
      {showLegend && (
        <div className="flex items-center justify-center gap-4 py-2 bg-gray-800 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-gray-400">&lt;20% flagged</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-amber-500" />
            <span className="text-gray-400">20-50%</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <span className="text-gray-400">&gt;50%</span>
          </div>
        </div>
      )}
    </div>
  );
};

/**
 * Get color for antenna based on flagging percentage.
 */
function getFlagColor(flaggedPct: number): string {
  if (flaggedPct > 50) return '#EF4444'; // red-500
  if (flaggedPct > 20) return '#F59E0B'; // amber-500
  return '#22C55E'; // green-500
}

export default AntennaLayoutWidget;
```

**Step 4: Create Index Export**

Create `frontend/src/components/antenna/index.ts`:

```typescript
export { default as AntennaLayoutWidget } from './AntennaLayoutWidget';
```

**Step 5: Integrate into MSDetailPage**

Add to `frontend/src/pages/MSDetailPage.tsx`:

```tsx
// Add import
import { AntennaLayoutWidget } from '../components/antenna';

// Add in the grid after existing cards:
<Card title="Antenna Layout">
  <AntennaLayoutWidget msPath={ms.path} height={200} showLegend />
</Card>;
```

#### 3.6 Acceptance Criteria

- [ ] Widget displays antenna positions in T-shaped layout
- [ ] Color indicates flagging status (green/amber/red)
- [ ] Tooltip shows antenna name and flagging stats
- [ ] Works for any MS in the system
- [ ] Responsive sizing in dashboard panel
- [ ] Legend shows color meanings

---

### 4. CreateMask/CreateRegion → Image QA Workflow

**Priority**: ⭐⭐ Medium  
**Effort**: Low  
**Value**: Medium (JS9 already supports this)

#### 4.1 Current State

`FitsViewer.tsx` uses JS9 which already supports:

- Region creation (circle, box, polygon, ellipse)
- Region import/export (DS9 format)
- WCS coordinate display
- Multi-extension FITS support

#### 4.2 Assessment: JS9 is Sufficient

**casangi's CreateMask and CreateRegion are NOT needed.**

| Feature              | JS9 (current) | casangi              |
| -------------------- | ------------- | -------------------- |
| Draw regions         | ✅ Yes        | ✅ Yes               |
| Export DS9 format    | ✅ Yes        | ✅ Yes               |
| WCS support          | ✅ Yes        | ✅ Yes               |
| No Python dependency | ✅ Yes        | ❌ Requires Bokeh    |
| Already integrated   | ✅ Yes        | ❌ Would need iframe |

#### 4.3 Proposed Enhancement

Leverage existing JS9 capabilities:

1. Add "Create Mask" button to ImageDetailPage
2. Enable JS9 region tools
3. Export regions as DS9 region file
4. Save to DB for pipeline use (e.g., clean masks)

#### 4.4 Implementation

```tsx
// Extend existing FitsViewer.tsx

interface MaskToolbarProps {
  imageId: string;
  onMaskSaved: () => void;
}

const MaskToolbar: React.FC<MaskToolbarProps> = ({ imageId, onMaskSaved }) => {
  const [maskMode, setMaskMode] = useState(false);

  const handleCreateMask = () => {
    if (window.JS9) {
      // Enable region creation mode
      window.JS9.SetRegions('circle', { color: 'green' });
      setMaskMode(true);
    }
  };

  const handleSaveMask = async () => {
    if (window.JS9) {
      const regions = window.JS9.GetRegions('all', { format: 'ds9' });
      await api.post(`/images/${imageId}/masks`, {
        format: 'ds9',
        regions,
      });
      setMaskMode(false);
      onMaskSaved();
    }
  };

  const handleClearRegions = () => {
    if (window.JS9) {
      window.JS9.RemoveRegions('all');
    }
  };

  return (
    <div className="flex gap-2">
      {!maskMode ? (
        <Button onClick={handleCreateMask}>
          <PencilIcon className="w-4 h-4" />
          Create Mask
        </Button>
      ) : (
        <>
          <Button variant="secondary" onClick={handleClearRegions}>
            Clear
          </Button>
          <Button onClick={handleSaveMask}>Save Mask</Button>
        </>
      )}
    </div>
  );
};
```

Backend endpoint:

```python
@router.post("/images/{image_id}/masks")
async def save_mask(image_id: str, mask: MaskCreate) -> MaskResponse:
    """Save DS9 region mask for an image."""
    from dsa110_contimg.database import ProductsDB

    db = ProductsDB()
    image = db.get_image(image_id)

    # Save mask file alongside image
    mask_path = Path(image.path).with_suffix('.mask.reg')
    mask_path.write_text(mask.regions)

    # Register in database
    mask_id = db.register_mask(
        image_id=image_id,
        path=str(mask_path),
        format=mask.format,
    )

    return MaskResponse(id=mask_id, path=str(mask_path))
```

#### 4.5 Acceptance Criteria

- [ ] User can draw regions on FITS image
- [ ] Regions exportable in DS9 format
- [ ] Masks saved to backend for re-imaging
- [ ] Masks visible when image reopened
- [ ] Mask listed in image provenance

---

### 5. cubevis iclean → Pipeline Re-imaging Interface

**Priority**: ⭐⭐⭐ High  
**Effort**: Medium-High  
**Value**: High (closes QA feedback loop)

#### 5.1 Current State

When imaging fails QA:

1. User sees bad image in dashboard
2. Must SSH to server
3. Manually re-run CLI with different parameters
4. Wait for completion
5. Manually check results
6. Update database manually

**Pain points**: Disconnected workflow, no traceability, error-prone.

#### 5.2 Proposed Enhancement

Add "Re-image" workflow directly from ImageDetailPage:

```text
┌─────────────────────────────────────────────────────────────────┐
│  ImageDetailPage                                                │
│  ┌───────────────┐  ┌──────────────────────────────────────┐   │
│  │  Bad Image    │  │  Re-image Panel                      │   │
│  │  QA: FAIL     │  │  ┌────────────────────────────────┐  │   │
│  │               │  │  │ imsize: [5040] x [5040]        │  │   │
│  │  [Re-image]───┼──│  │ cell: [2.5arcsec]              │  │   │
│  │               │  │  │ niter: [10000]                 │  │   │
│  │               │  │  │ threshold: [0.5mJy]            │  │   │
│  │               │  │  │ ☑ Use existing mask            │  │   │
│  │               │  │  │ ☐ Interactive mode             │  │   │
│  │               │  │  │                                │  │   │
│  │               │  │  │ [Cancel] [Start Re-imaging]    │  │   │
│  │               │  │  └────────────────────────────────┘  │   │
│  └───────────────┘  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

#### 5.3 Implementation

1. New API endpoint:

   ```python
   @router.post("/images/{image_id}/reimage")
   async def reimage(
       image_id: str,
       params: ReimageParams,
       background_tasks: BackgroundTasks,
   ) -> dict:
       """Queue re-imaging job with provenance tracking."""
       from dsa110_contimg.database import ProductsDB
       from dsa110_contimg.pipeline.stages_impl import ImagingStage

       db = ProductsDB()
       image = db.get_image(image_id)

       # Validate MS still exists
       if not Path(image.ms_path).exists():
           raise HTTPException(404, f"MS not found: {image.ms_path}")

       # Queue imaging job
       job_id = str(uuid.uuid4())
       background_tasks.add_task(
           run_imaging_job,
           job_id=job_id,
           ms_path=image.ms_path,
           params=params,
           parent_image_id=image_id,  # For provenance
       )

       return {"job_id": job_id, "status": "queued"}
   ```

2. Frontend modal:

   ```tsx
   // src/components/imaging/ReimageModal.tsx

   const ReimageModal: React.FC<{
     image: ImageDetail;
     onClose: () => void;
   }> = ({ image, onClose }) => {
     const navigate = useNavigate();
     const [params, setParams] = useState<ReimageParams>(getDsa110Defaults(image));
     const [isInteractive, setIsInteractive] = useState(false);
     const [useExistingMask, setUseExistingMask] = useState(!!image.mask_path);

     const handleSubmit = async () => {
       if (isInteractive) {
         // Launch interactive session
         const session = await api.post('/imaging/interactive', {
           ms_path: image.ms_path,
           mask: useExistingMask ? image.mask_path : undefined,
           ...params,
         });
         window.open(session.url, '_blank');
       } else {
         // Queue background job
         const job = await api.post(`/images/${image.id}/reimage`, {
           ...params,
           mask: useExistingMask ? image.mask_path : undefined,
         });
         navigate(`/jobs/${job.job_id}`);
       }
       onClose();
     };

     return (
       <Modal title="Re-image" onClose={onClose}>
         <ImagingParamsForm params={params} onChange={setParams} />

         {image.mask_path && (
           <Checkbox
             label="Use existing mask"
             checked={useExistingMask}
             onChange={setUseExistingMask}
           />
         )}

         <Checkbox
           label="Interactive mode (opens iClean)"
           checked={isInteractive}
           onChange={setIsInteractive}
         />

         <div className="flex gap-2 justify-end mt-4">
           <Button variant="secondary" onClick={onClose}>
             Cancel
           </Button>
           <Button onClick={handleSubmit}>Start Re-imaging</Button>
         </div>
       </Modal>
     );
   };

   function getDsa110Defaults(image: ImageDetail): ReimageParams {
     return {
       imsize: [5040, 5040],
       cell: '2.5arcsec',
       niter: 10000,
       threshold: '0.5mJy',
       weighting: 'briggs',
       robust: 0.5,
       // Preserve any custom params from original image
       ...image.imaging_params,
     };
   }
   ```

#### 5.4 Provenance Tracking

Re-imaged products should link to their source:

```python
# backend/src/dsa110_contimg/database/products.py

def register_reimaged_product(
    new_path: str,
    parent_image_id: str,
    params: dict,
) -> str:
    """Register re-imaged product with provenance."""
    conn = get_connection()
    cursor = conn.cursor()

    # Insert new product
    cursor.execute("""
        INSERT INTO images (path, ms_path, created_at, params_json, parent_id)
        SELECT ?, ms_path, ?, ?, id
        FROM images WHERE id = ?
    """, (new_path, datetime.now().isoformat(), json.dumps(params), parent_image_id))

    new_id = cursor.lastrowid
    conn.commit()
    return str(new_id)
```

#### 5.5 Acceptance Criteria

- [ ] Re-image button visible on failed QA images
- [ ] Modal shows DSA-110 default params with ability to modify
- [ ] Option to use existing mask
- [ ] Background job queued and trackable in Jobs page
- [ ] Interactive option launches iClean session
- [ ] New image linked to parent via `parent_id`
- [ ] Provenance chain visible in UI

---

## Technical Architecture

### Integration Patterns

#### Pattern A: Backend Rendering (Stateless)

```text
┌─────────────┐    HTTP GET     ┌─────────────┐    Python    ┌─────────────┐
│   React     │ ──────────────▶ │   FastAPI   │ ──────────▶  │  casagui    │
│  <img src>  │ ◀────PNG─────── │   endpoint  │ ◀───bytes─── │  renderer   │
└─────────────┘                 └─────────────┘              └─────────────┘
```

**Pros**: Simple, stateless, cacheable  
**Cons**: No interactivity, latency per request  
**Use for**: MsRaster (static), PlotAnts

#### Pattern B: Bokeh Server Embedding

```text
┌─────────────┐   HTTP POST    ┌─────────────┐   subprocess  ┌─────────────┐
│   React     │ ─────────────▶ │   FastAPI   │ ────────────▶ │  Bokeh      │
│  launcher   │ ◀──session_id── │   manager   │               │  Server     │
└─────────────┘                └─────────────┘              └──────┬──────┘
       │                                                           │
       │  window.open(bokeh_url)                                   │
       └───────────────────────────────────────────────────────────┘
```

**Pros**: Full interactivity  
**Cons**: Session management, port allocation, cleanup  
**Use for**: InteractiveClean

#### Pattern C: Hybrid (Future)

```text
┌─────────────────────────────────────────────────────────────────┐
│  React Application                                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  <BokehEmbed sessionId={id} />                             │ │
│  │  ┌────────────────────────────────────────────────────────┐│ │
│  │  │  <iframe src={bokeh_url} />                            ││ │
│  │  └────────────────────────────────────────────────────────┘│ │
│  └────────────────────────────────────────────────────────────┘ │
│        │                                                        │
│        │  WebSocket (status updates)                            │
│        ▼                                                        │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  <SessionStatus progress={50} stage="deconvolving" />     │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**Pros**: Unified UX, progress visibility  
**Cons**: Complex WebSocket bridge  
**Use for**: Deep integration (Phase 3)

### Session Management

For Bokeh-based tools, implement session lifecycle:

```python
# backend/src/dsa110_contimg/api/services/bokeh_sessions.py

class BokehSessionManager:
    """Manage Bokeh server sessions."""

    def __init__(self):
        self.sessions: Dict[str, BokehSession] = {}
        self.port_pool = PortPool(range(5010, 5100))

    async def create_session(
        self,
        app_name: str,
        params: dict,
    ) -> BokehSession:
        """Launch new Bokeh session."""
        session_id = str(uuid.uuid4())
        port = self.port_pool.acquire()

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "bokeh", "serve",
            f"casagui.apps.{app_name}",
            "--port", str(port),
            "--session-id", session_id,
            "--args", json.dumps(params),
        )

        session = BokehSession(
            id=session_id,
            port=port,
            process=proc,
            created_at=datetime.now(),
            params=params,
        )
        self.sessions[session_id] = session

        return session

    async def cleanup_session(self, session_id: str) -> None:
        """Terminate session and free resources."""
        session = self.sessions.pop(session_id, None)
        if session:
            session.process.terminate()
            await session.process.wait()
            self.port_pool.release(session.port)

    async def cleanup_stale_sessions(self, max_age_hours: int = 4) -> None:
        """Clean up abandoned sessions."""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        stale = [
            sid for sid, s in self.sessions.items()
            if s.created_at < cutoff
        ]
        for sid in stale:
            await self.cleanup_session(sid)
```

### Dependency Management

Add casangi packages to backend environment:

```yaml
# ops/docker/environment.yml additions

dependencies:
  - pip:
      - casagui>=0.1.0 # When available on PyPI
      - cubevis>=0.1.0 # When available on PyPI
      - bokeh>=3.0.0
```

Or install from GitHub:

```bash
pip install git+https://github.com/casangi/casagui.git
pip install git+https://github.com/casangi/cubevis.git
```

---

## Implementation Roadmap

### Phase 1: Quick Wins (2-3 weeks)

| Task                   | Component | Effort | Dependencies      |
| ---------------------- | --------- | ------ | ----------------- |
| MS raster API endpoint | Backend   | 3 days | casagui installed |
| MsRasterPlot component | Frontend  | 2 days | API endpoint      |
| Antenna layout widget  | Frontend  | 2 days | D3.js (existing)  |
| Antenna stats endpoint | Backend   | 1 day  | casacore          |

**Deliverables**:

- MSDetailPage shows visibility raster plots
- Antenna diagnostics visible in MS/Image pages

### Phase 2: Core Features (4-6 weeks)

| Task                      | Component | Effort | Dependencies       |
| ------------------------- | --------- | ------ | ------------------ |
| Bokeh session manager     | Backend   | 1 week | Bokeh, casagui     |
| InteractiveClean launcher | Backend   | 3 days | Session manager    |
| iClean link from frontend | Frontend  | 2 days | Launcher API       |
| Re-image modal            | Frontend  | 3 days | Imaging API        |
| Re-image job queue        | Backend   | 3 days | Existing job infra |
| JS9 mask export           | Frontend  | 2 days | JS9 (existing)     |
| Mask storage API          | Backend   | 2 days | SQLite/filesystem  |

**Deliverables**:

- Users can launch InteractiveClean from UI
- Re-imaging workflow functional
- Masks creatable and saveable

### Phase 3: Deep Integration (6-8 weeks)

| Task                      | Component | Effort | Dependencies    |
| ------------------------- | --------- | ------ | --------------- |
| Bokeh iframe embedding    | Frontend  | 1 week | Session manager |
| WebSocket status bridge   | Both      | 1 week | WebSocket infra |
| Progress tracking         | Both      | 1 week | Status bridge   |
| Image versioning          | Backend   | 1 week | Products DB     |
| Automated session cleanup | Backend   | 3 days | Systemd/cron    |
| E2E testing               | Testing   | 1 week | All above       |

**Deliverables**:

- Unified UX with embedded Bokeh
- Real-time progress updates
- Production-ready deployment

---

## Risk Assessment

| Risk                    | Probability | Impact | Mitigation                            |
| ----------------------- | ----------- | ------ | ------------------------------------- |
| casagui API instability | Medium      | High   | Pin versions, maintain fork if needed |
| Bokeh session leaks     | Medium      | Medium | Aggressive cleanup, monitoring        |
| Port exhaustion         | Low         | High   | Port pool with limits, alerts         |
| CASA/casagui conflicts  | Medium      | High   | Isolated conda environments           |
| Performance (large MS)  | High        | Medium | Chunked rendering, async              |
| Browser compatibility   | Low         | Low    | Test Chrome/Firefox only              |

---

## Success Metrics

| Metric                     | Target               | Measurement            |
| -------------------------- | -------------------- | ---------------------- |
| MS inspection time         | <30s to view raster  | API latency monitoring |
| Interactive session launch | <10s to usable UI    | User timing            |
| Re-imaging turnaround      | 50% reduction vs CLI | Job completion times   |
| Mask creation rate         | 5+ masks/session     | Usage analytics        |
| Session abandonment        | <20%                 | Cleanup logs           |

---

## Edge Case Analysis

This section documents anticipated edge cases that should be addressed before
and during implementation. These patterns are derived from existing DSA-110
codebase handling of similar scenarios.

### Data Edge Cases (MS/HDF5 Files)

| Edge Case                         | Impact                     | Mitigation Pattern                                                  |
| --------------------------------- | -------------------------- | ------------------------------------------------------------------- |
| **Empty MS file**                 | API returns 500 or hangs   | Check `nrow > 0` before processing (see `ms_helpers.py` validation) |
| **Fully flagged data (100%)**     | Raster shows blank/crashes | Use `validate_ms_unflagged_fraction()` sampling, return 422         |
| **Missing CORRECTED_DATA column** | MsRaster fails to render   | Check column existence first (pattern in `ms_helpers.py:202`)       |
| **Corrupt/partial MS tables**     | casacore table errors      | Wrap in try/catch, return 500 with descriptive message              |
| **MS file locked by other proc**  | "Cannot open for reading"  | Retry with exponential backoff (see `direct_subband.py:275-320`)    |
| **Very large MS (>10GB)**         | Timeout, memory exhaustion | Add `--timeout` parameter, implement chunked reading                |
| **Unusual spectral windows**      | Unexpected array shapes    | Validate `nspw`, squeeze dimensions if needed                       |
| **Path with special characters**  | 404 or encoding errors     | Use `unquote()` for path decoding (pattern in `ms.py` routes)       |

### Memory & Performance Edge Cases

| Edge Case                           | Impact                    | Mitigation                                                      |
| ----------------------------------- | ------------------------- | --------------------------------------------------------------- |
| **Memory exhaustion during raster** | Process killed, 500 error | `try/except MemoryError` (pattern in `parallel.py`), downsample |
| **Raster timeout (>30s)**           | Frontend shows "failed"   | Return partial results, add progress WebSocket                  |
| **Concurrent raster requests**      | OOM, server thrashing     | Implement semaphore limiting (max 2-3 concurrent)               |
| **16K channels × 2000 baselines**   | 32M points to render      | Default downsampling to 1000 time bins, 1000 freq channels      |
| **HDD source path (vs NVMe)**       | 10× slower I/O            | Detect `/data/` prefix, warn user or stage to `/scratch/`       |

### Bokeh Session Edge Cases (InteractiveClean)

| Edge Case                          | Impact                       | Mitigation                                                |
| ---------------------------------- | ---------------------------- | --------------------------------------------------------- |
| **Port exhaustion (5006-5020)**    | New sessions fail            | Implement port pool with `find_free_port()` pattern       |
| **Orphaned Bokeh processes**       | Port stays busy, memory leak | Background cleanup task every 15min                       |
| **Browser closes without cleanup** | Session stays "active"       | Heartbeat WebSocket, mark stale after 5min                |
| **Multiple tabs same session**     | State conflicts              | Session ID in URL, reject duplicate connections           |
| **Long-running clean (>1hr)**      | Timeout, session expiry      | Extend session TTL on activity, checkpoint state          |
| **Bokeh server crash**             | 502 proxy error              | Supervisor auto-restart, session recovery from checkpoint |

### Frontend Component Edge Cases

| Edge Case                          | Impact                          | Mitigation Pattern                                          |
| ---------------------------------- | ------------------------------- | ----------------------------------------------------------- |
| **Image load timeout (>10s)**      | Stuck spinner                   | Use `VIEWER_TIMEOUTS.JS9_LOAD_MS` pattern with fallback     |
| **Component unmount during fetch** | Memory leak, state update error | `AbortController` cleanup (pattern in `FitsViewer.tsx:102`) |
| **Invalid URL encoding**           | 404 from API                    | Client-side `encodeURIComponent()` before fetch             |
| **Missing colormap selection**     | Default renders poorly          | Sensible defaults (`viridis`), persist user preference      |
| **iframe blocked by CSP**          | Blank embed                     | Configure `X-Frame-Options` for Bokeh server                |
| **Touch device pan/zoom**          | Desktop-only gestures           | Add mobile-friendly controls for Bokeh embeds               |

### casagui Dependency Edge Cases

| Edge Case                     | Impact                   | Mitigation                                                  |
| ----------------------------- | ------------------------ | ----------------------------------------------------------- |
| **casagui not installed**     | `ImportError` at startup | Optional import with feature flag, graceful disable         |
| **casagui API changes**       | Breaking changes         | Pin version in `environment.yml`, maintain adapter layer    |
| **CASA version mismatch**     | Runtime errors           | Version check at import time, log warning                   |
| **Missing Bokeh dependency**  | Panel fails to serve     | List in `pyproject.toml` extras: `casagui = [bokeh, panel]` |
| **HoloViews rendering fails** | Blank or error output    | Fallback to matplotlib static render                        |

### Concurrency & Race Condition Edge Cases

| Edge Case                         | Impact               | Mitigation Pattern                                                   |
| --------------------------------- | -------------------- | -------------------------------------------------------------------- |
| **Two users open same MS**        | File lock conflict   | Read-only mode for visualization (casacore handles)                  |
| **Session cleanup during use**    | 404 mid-interaction  | Session lock during active requests                                  |
| **Parallel API requests same MS** | Table lock errors    | Serialize with file-based lock (see `photometry/cli.py:760`)         |
| **SQLite queue race**             | Duplicate processing | WAL mode + 30s timeout (pattern in `streaming_converter.py:185-191`) |

### Network & Infrastructure Edge Cases

| Edge Case                     | Impact               | Mitigation                                         |
| ----------------------------- | -------------------- | -------------------------------------------------- |
| **API server restart**        | Active sessions lost | Persist sessions to SQLite, recover on startup     |
| **Proxy timeout (nginx 60s)** | Long renders fail    | Increase proxy timeout for `/api/imaging/*` routes |
| **DNS resolution failure**    | Bokeh embed 502      | Use `localhost` not hostname for Bokeh server      |
| **CORS issues**               | Frontend can't embed | Configure CORS headers for Bokeh server origin     |

### User Input Validation Edge Cases

| Edge Case                         | Impact                 | Mitigation                                   |
| --------------------------------- | ---------------------- | -------------------------------------------- |
| **Invalid axis selection**        | KeyError in casagui    | Validate against allowed enum before calling |
| **Negative/zero iteration count** | Infinite loop or error | Pydantic model with `ge=0` constraint        |
| **Path traversal attack**         | Security vulnerability | Validate path is under allowed directories   |
| **Extremely large image size**    | OOM                    | Cap at `imsize <= [8192, 8192]`              |
| **Invalid colormap name**         | matplotlib error       | Validate against `matplotlib.colormaps`      |

### Pre-Implementation Validation Utilities

These utility functions should be implemented before integration work begins:

**Backend Validation Helper** (`backend/src/dsa110_contimg/api/utils/validation.py`):

```python
from pathlib import Path
from fastapi import HTTPException
from casacore.tables import table

from dsa110_contimg.utils.ms_helpers import validate_ms_unflagged_fraction


def validate_ms_for_visualization(ms_path: Path) -> None:
    """Validate MS is suitable for casagui visualization.

    Raises:
        HTTPException: 404 if not found, 422 if invalid for visualization
    """
    if not ms_path.exists():
        raise HTTPException(404, f"MS not found: {ms_path}")

    try:
        with table(str(ms_path), readonly=True) as t:
            if t.nrows() == 0:
                raise HTTPException(422, "MS is empty (0 rows)")

            colnames = t.colnames()
            if "CORRECTED_DATA" not in colnames and "DATA" not in colnames:
                raise HTTPException(
                    422,
                    "MS has no DATA or CORRECTED_DATA column"
                )
    except RuntimeError as e:
        if "cannot be opened" in str(e).lower():
            raise HTTPException(423, f"MS is locked by another process: {e}")
        raise HTTPException(500, f"Failed to open MS: {e}")

    # Check flagging fraction (sample-based, memory efficient)
    try:
        unflagged = validate_ms_unflagged_fraction(str(ms_path))
        if unflagged < 0.01:  # Less than 1% unflagged
            raise HTTPException(
                422,
                f"MS is >99% flagged ({unflagged:.1%} unflagged)"
            )
    except Exception as e:
        # Non-fatal: proceed with visualization but log warning
        import logging
        logging.warning(f"Could not validate flags for {ms_path}: {e}")


def validate_imaging_parameters(imsize: list[int], niter: int) -> None:
    """Validate imaging parameters are within safe bounds.

    Raises:
        HTTPException: 422 if parameters invalid
    """
    MAX_IMSIZE = 8192
    MAX_NITER = 1_000_000

    if len(imsize) != 2:
        raise HTTPException(422, "imsize must be [width, height]")

    if any(s <= 0 or s > MAX_IMSIZE for s in imsize):
        raise HTTPException(422, f"imsize must be 1-{MAX_IMSIZE} per dimension")

    if niter < 0 or niter > MAX_NITER:
        raise HTTPException(422, f"niter must be 0-{MAX_NITER}")
```

**Frontend Safe API Call Helper** (`frontend/src/utils/safeApiCall.ts`):

```typescript
export class ApiError extends Error {
  constructor(public readonly status: number, public readonly detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = 'ApiError';
  }
}

/**
 * Wrapper for fetch with timeout and error handling.
 *
 * @param url - API endpoint URL
 * @param options - Standard fetch options
 * @param timeoutMs - Timeout in milliseconds (default: 30000)
 * @returns Parsed JSON response
 * @throws ApiError on non-2xx responses
 */
export async function safeApiCall<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = 30000
): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });

    if (!response.ok) {
      const detail = await response.text().catch(() => 'Unknown error');
      throw new ApiError(response.status, detail);
    }

    return response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError(408, `Request timeout after ${timeoutMs}ms`);
    }
    throw new ApiError(500, String(error));
  } finally {
    clearTimeout(timeout);
  }
}

/**
 * Fetch binary data (images) with timeout.
 */
export async function safeBinaryFetch(url: string, timeoutMs: number = 60000): Promise<Blob> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { signal: controller.signal });

    if (!response.ok) {
      throw new ApiError(response.status, `Failed to fetch: ${url}`);
    }

    return response.blob();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiError(408, `Image load timeout after ${timeoutMs}ms`);
    }
    throw new ApiError(500, String(error));
  } finally {
    clearTimeout(timeout);
  }
}
```

**Feature Flag for Optional casagui** (`backend/src/dsa110_contimg/api/config.py`):

```python
import os
from functools import lru_cache


@lru_cache
def is_casagui_available() -> bool:
    """Check if casagui is installed and usable."""
    try:
        import casagui  # noqa: F401
        return True
    except ImportError:
        return False


@lru_cache
def get_casagui_config() -> dict:
    """Get casagui configuration from environment."""
    return {
        "enabled": os.getenv("CASAGUI_ENABLED", "true").lower() == "true",
        "bokeh_port_start": int(os.getenv("BOKEH_PORT_START", "5006")),
        "bokeh_port_end": int(os.getenv("BOKEH_PORT_END", "5020")),
        "session_timeout_hours": float(os.getenv("BOKEH_SESSION_TIMEOUT", "4.0")),
        "max_concurrent_sessions": int(os.getenv("BOKEH_MAX_SESSIONS", "5")),
    }


def require_casagui():
    """Dependency that raises 501 if casagui not available."""
    from fastapi import HTTPException

    config = get_casagui_config()
    if not config["enabled"]:
        raise HTTPException(501, "casagui integration is disabled")

    if not is_casagui_available():
        raise HTTPException(
            501,
            "casagui is not installed. Install with: "
            "pip install git+https://github.com/casangi/casagui.git"
        )
```

---

## Quick Reference: Files to Create/Modify

### Backend Files

| File                                                        | Action | Purpose                         |
| ----------------------------------------------------------- | ------ | ------------------------------- |
| `backend/src/dsa110_contimg/api/routes/ms.py`               | Modify | Add `/raster` and `/antennas`   |
| `backend/src/dsa110_contimg/api/routes/imaging.py`          | Create | Interactive clean session mgmt  |
| `backend/src/dsa110_contimg/api/services/bokeh_sessions.py` | Create | Bokeh session lifecycle manager |
| `backend/src/dsa110_contimg/api/schemas.py`                 | Modify | Add Pydantic models             |
| `backend/src/dsa110_contimg/api/app.py`                     | Modify | Register routes, add lifespan   |
| `backend/tests/api/test_ms_raster.py`                       | Create | Raster endpoint tests           |
| `backend/tests/api/test_imaging.py`                         | Create | Interactive imaging tests       |

### Frontend Files

| File                                                      | Action | Purpose                     |
| --------------------------------------------------------- | ------ | --------------------------- |
| `frontend/src/components/ms/MsRasterPlot.tsx`             | Create | Visibility raster component |
| `frontend/src/components/ms/MsRasterPlot.test.tsx`        | Create | Component tests             |
| `frontend/src/components/ms/index.ts`                     | Create | Directory exports           |
| `frontend/src/components/antenna/AntennaLayoutWidget.tsx` | Create | Antenna layout SVG          |
| `frontend/src/components/antenna/index.ts`                | Create | Directory exports           |
| `frontend/src/pages/MSDetailPage.tsx`                     | Modify | Add raster + antenna cards  |
| `frontend/src/pages/ImageDetailPage.tsx`                  | Modify | Add re-image button/modal   |
| `frontend/src/hooks/useQueries.ts`                        | Modify | Add query keys + hooks      |

### Configuration Files

| File                                | Action | Purpose                  |
| ----------------------------------- | ------ | ------------------------ |
| `ops/docker/environment.yml`        | Modify | Add casagui dependencies |
| `ops/systemd/contimg-bokeh.service` | Create | Bokeh server service     |

---

## Quick Reference: Commands

### Install casagui

```bash
conda activate casa6
pip install git+https://github.com/casangi/casagui.git
pip install git+https://github.com/casangi/cubevis.git
```

### Run Backend Tests

```bash
cd /data/dsa110-contimg/backend
conda activate casa6
python -m pytest tests/api/test_ms_raster.py -v
python -m pytest tests/api/test_imaging.py -v
```

### Run Frontend Tests

```bash
cd /data/dsa110-contimg/frontend
npm test -- --run src/components/ms/MsRasterPlot.test.tsx
npm test -- --run src/components/antenna/AntennaLayoutWidget.test.tsx
```

### Manual Testing

```bash
# Test raster endpoint
curl "http://localhost:8000/api/ms/$(echo '/stage/dsa110-contimg/ms/test.ms' | jq -sRr @uri)/raster?xaxis=time&yaxis=amp" --output test.png

# Test antenna endpoint
curl "http://localhost:8000/api/ms/$(echo '/stage/dsa110-contimg/ms/test.ms' | jq -sRr @uri)/antennas" | jq

# Start interactive session
curl -X POST "http://localhost:8000/api/imaging/interactive" \
  -H "Content-Type: application/json" \
  -d '{"ms_path": "/stage/dsa110-contimg/ms/test.ms", "imagename": "test_interactive"}'

# List active sessions
curl "http://localhost:8000/api/imaging/sessions" | jq
```

---

## Quick Reference: DSA-110 Defaults

```python
# Standard imaging parameters for DSA-110
DSA110_IMAGING_DEFAULTS = {
    'imsize': [5040, 5040],
    'cell': '2.5arcsec',
    'specmode': 'mfs',
    'deconvolver': 'hogbom',
    'weighting': 'briggs',
    'robust': 0.5,
    'gridder': 'standard',
    'niter': 10000,
    'threshold': '0.5mJy',
    'pbcor': True,
    'datacolumn': 'corrected',
}

# Telescope location
DSA110_LAT = 37.2339   # degrees
DSA110_LON = -118.2817 # degrees

# Array characteristics
DSA110_NANTS = 110     # Total antennas
DSA110_NBASELINES = 2000  # Typical active baselines
DSA110_NCHANNELS = 768    # 16 subbands × 48 channels
```

---

## References

- [casangi/casagui](https://github.com/casangi/casagui) - Source repository
- [casangi/cubevis](https://github.com/casangi/cubevis) - Image visualization
- [Bokeh Documentation](https://docs.bokeh.org/) - Embedding and server
- [JS9 Documentation](https://js9.si.edu/) - Existing FITS viewer
- [DSA-110 Frontend README](/data/dsa110-contimg/frontend/README.md)
- [Pipeline Stage Architecture](/data/dsa110-contimg/docs/concepts/pipeline_stage_architecture.md)
