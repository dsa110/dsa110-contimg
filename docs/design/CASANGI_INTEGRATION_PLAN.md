# casangi Visualization Tools Integration Plan

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

**Last Updated**: 2025-11-30

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
| Channels        | 16,384 (16 subbands × 1024)  |
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

Implementation steps:

1. Create new API endpoint: `GET /api/ms/{ms_path}/raster`

   - Query params: `xaxis`, `yaxis`, `colorby`, `spw`, `antenna`
   - Returns: PNG image

2. Backend implementation:

   ```python
   # backend/src/dsa110_contimg/api/routes/ms.py

   @router.get("/ms/{ms_path:path}/raster")
   async def get_ms_raster(
       ms_path: str,
       xaxis: str = "time",
       yaxis: str = "amp",
       spw: Optional[str] = None,
       antenna: Optional[str] = None,
   ) -> StreamingResponse:
       """Generate visibility raster plot."""
       from casagui.apps import MsRaster

       msr = MsRaster(ms=ms_path)
       msr.plot(xaxis=xaxis, yaxis=yaxis)

       # Render to PNG
       buf = io.BytesIO()
       msr.save(buf, format='png')
       buf.seek(0)

       return StreamingResponse(buf, media_type="image/png")
   ```

3. Frontend component:

   ```tsx
   // src/components/ms/MsRasterPlot.tsx

   interface MsRasterPlotProps {
     msPath: string;
     xaxis?: "time" | "channel" | "baseline";
     yaxis?: "amp" | "phase" | "real" | "imag";
   }

   const MsRasterPlot: React.FC<MsRasterPlotProps> = ({
     msPath,
     xaxis,
     yaxis,
   }) => {
     const url = `${config.api.baseUrl}/ms/${encodeURIComponent(
       msPath
     )}/raster?xaxis=${xaxis}&yaxis=${yaxis}`;
     return <img src={url} alt={`${yaxis} vs ${xaxis}`} className="w-full" />;
   };
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
       const response = await api.post("/imaging/interactive", {
         ms_path: msPath,
       });
       setSession(response.data);
       window.open(response.data.url, "_blank");
     };

     return (
       <div>
         <MSSelector onSelect={startSession} />
         {session && <SessionStatus session={session} />}
       </div>
     );
   };
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
  const viewBox = "-800 -200 1600 600"; // Wider EW, narrower NS

  return (
    <svg viewBox={viewBox} className="w-full h-48">
      {/* Grid lines for scale */}
      <line
        x1="-600"
        y1="0"
        x2="600"
        y2="0"
        stroke="#333"
        strokeDasharray="4"
      />
      <line
        x1="0"
        y1="-150"
        x2="0"
        y2="300"
        stroke="#333"
        strokeDasharray="4"
      />

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
  if (pct > 50) return "#EF4444"; // red - severe flagging
  if (pct > 20) return "#F59E0B"; // amber - moderate flagging
  return "#22C55E"; // green - good
}
```

#### 3.5 Backend Endpoint

```python
@router.get("/ms/{ms_path:path}/antennas")
async def get_antenna_info(ms_path: str) -> list[dict]:
    """Get antenna positions and flagging statistics."""
    from casacore.tables import table
    from dsa110_contimg.utils.antpos_local import get_itrf
    from dsa110_contimg.conversion.helpers_coordinates import itrf_to_enu

    # Get antenna positions from our authoritative source
    itrf_df = get_itrf()

    # Convert to ENU for display
    enu_coords = itrf_to_enu(itrf_df[['x_m', 'y_m', 'z_m']].values)

    # Get per-antenna flagging from MS
    with table(ms_path) as ms:
        flags = ms.getcol("FLAG")
        ant1 = ms.getcol("ANTENNA1")
        ant2 = ms.getcol("ANTENNA2")

    # Calculate per-antenna flagging percentage
    flag_pcts = calculate_antenna_flagging(flags, ant1, ant2)

    return [
        {
            "id": int(row.Index),
            "name": row.name,
            "x": float(enu_coords[row.Index, 0]),  # East
            "y": float(enu_coords[row.Index, 1]),  # North
            "flagged_pct": float(flag_pcts.get(row.Index, 0)),
        }
        for row in itrf_df.itertuples()
    ]
```

#### 3.6 Acceptance Criteria

- [ ] Widget displays antenna positions in T-shaped layout
- [ ] Color indicates flagging status (green/amber/red)
- [ ] Tooltip shows antenna name and flagging stats
- [ ] Works for any MS in the system
- [ ] Responsive sizing in dashboard panel

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
      window.JS9.SetRegions("circle", { color: "green" });
      setMaskMode(true);
    }
  };

  const handleSaveMask = async () => {
    if (window.JS9) {
      const regions = window.JS9.GetRegions("all", { format: "ds9" });
      await api.post(`/images/${imageId}/masks`, {
        format: "ds9",
        regions,
      });
      setMaskMode(false);
      onMaskSaved();
    }
  };

  const handleClearRegions = () => {
    if (window.JS9) {
      window.JS9.RemoveRegions("all");
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
     const [params, setParams] = useState<ReimageParams>(
       getDsa110Defaults(image)
     );
     const [isInteractive, setIsInteractive] = useState(false);
     const [useExistingMask, setUseExistingMask] = useState(!!image.mask_path);

     const handleSubmit = async () => {
       if (isInteractive) {
         // Launch interactive session
         const session = await api.post("/imaging/interactive", {
           ms_path: image.ms_path,
           mask: useExistingMask ? image.mask_path : undefined,
           ...params,
         });
         window.open(session.url, "_blank");
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
       cell: "2.5arcsec",
       niter: 10000,
       threshold: "0.5mJy",
       weighting: "briggs",
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

## References

- [casangi/casagui](https://github.com/casangi/casagui) - Source repository
- [casangi/cubevis](https://github.com/casangi/cubevis) - Image visualization
- [Bokeh Documentation](https://docs.bokeh.org/) - Embedding and server
- [JS9 Documentation](https://js9.si.edu/) - Existing FITS viewer
- [DSA-110 Frontend README](/data/dsa110-contimg/frontend/README.md)
- [Pipeline Stage Architecture](/data/dsa110-contimg/docs/concepts/pipeline_stage_architecture.md)
