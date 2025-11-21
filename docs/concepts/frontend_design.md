# DSA-110 Continuum Imaging Pipeline: Front-End Design Strategy

## Executive Summary

This document outlines the strategic design for a comprehensive web-based user
interface for the DSA-110 continuum imaging pipeline. The pipeline is a fully
automated, streaming survey system designed to be the most sensitive and
comprehensive search for extreme scattering events (ESE) ever conducted,
monitoring 10³-10⁴ sources per day.

**Core Design Principles:**

- **Information density over volume**: One excellent, information-rich figure
  beats 100 individual diagnostics
- **Ease of use**: Radio astronomers should quickly find what they need
- **Real-time monitoring**: Pipeline health and data quality at a glance
- **Science-first**: Direct access to the "good stuff" - images and variability
  detection
- **Professional aesthetic**: Clean, modern, data-dense interfaces for working
  scientists

---

## 1. Current State Analysis

### 1.1 Existing Infrastructure

**Backend API** (`/data/dsa110-contimg/src/dsa110_contimg/api/`)

- FastAPI application with comprehensive REST endpoints
- Real-time system metrics (CPU, memory, disk, load)
- Queue management and status tracking
- Calibration registry monitoring
- Products database with MS index, images, photometry
- QA artifact serving

**Data Sources**

- `/state/ingest.sqlite3` - Ingest queue, subband files, performance metrics
- `/state/cal_registry.sqlite3` - Calibration tables and validity windows
- `/state/products.sqlite3` - MS index, images, photometry, pointing history
- `/state/catalogs/master_sources.sqlite3` - NVSS/VLASS/FIRST crossmatch catalog
- `/state/qa/` - Quality assurance plots (per-group subdirectories)

**Existing Documentation**

- MkDocs static site for technical documentation
- Some basic HTML endpoints (calibrator matches view)
- Empty dashboard scaffolding at `/var/www/contimg_dashboard/`

### 1.2 Key API Endpoints Available

```
GET  /api/status                     # Queue stats, recent groups, cal sets
GET  /api/products?limit=50          # Recent image products
GET  /api/calibrator_matches         # Calibrator detection history
GET  /api/pointing_history           # Telescope pointing over time
GET  /api/qa?limit=100               # QA artifacts list
GET  /api/qa/file/{group}/{name}    # Serve QA image/plot
GET  /api/qa/thumbs                  # Latest QA artifact per group
GET  /api/groups/{group_id}          # Detailed group information
GET  /api/ms_index                   # MS processing stage tracking
POST /api/reprocess/{group_id}       # Trigger reprocessing
GET  /api/metrics/system             # Current system metrics
GET  /api/metrics/system/history     # Historical system metrics
```

### 1.3 Data Model Highlights

**Pipeline States**: `collecting` → `pending` → `in_progress` →
`processing_fresh` → `completed`

**MS Processing Stages**: `converted` → `calibrated` → `imaged` →
`photometry_complete`

**Photometry Schema**:

- Per-image, per-source measurements
- NVSS reference flux, measured peak (Jy/beam), error estimate
- RA/Dec coordinates for each source

**Pointing History**: Timestamp-indexed RA/Dec telescope pointings

---

## 2. Strategic Vision: Information Architecture

### 2.1 Core User Personas

1. **Operations Monitor** - Needs to know: "Is the pipeline healthy?"
2. **Data Quality Scientist** - Needs to know: "Is the data good?"
3. **Science User** - Needs to know: "Did we detect any interesting
   variability?"

### 2.2 Primary Navigation Structure

```
┌─────────────────────────────────────────────────────┐
│  DSA-110 Continuum Imaging Pipeline                 │
├─────────────────────────────────────────────────────┤
│                                                      │
│  [Dashboard] [Sky] [Sources] [Observing] [Health]  │
│                                                      │
└─────────────────────────────────────────────────────┘

Dashboard  - Executive summary (pipeline status, latest images, alerts)
Sky        - Image gallery, mosaics, sky coverage visualization
Sources    - Source monitoring, flux timeseries, variability detection
Observing  - Telescope status, pointing history, calibrator tracking
Health     - System metrics, queue monitoring, diagnostic plots
```

### 2.3 Design Philosophy: High-Density Information Display

**Inspiration**: Trading dashboards, mission control centers, astronomical
observatories

**Key Techniques**:

- **Small multiples**: Show many sources/images in compact, comparable grids
- **Sparklines**: Inline flux trends without taking full-figure space
- **Color coding**: Quick visual status (green=healthy, yellow=warning,
  red=critical)
- **Drill-down**: Summary → Detail → Deep Dive on demand
- **Live updates**: WebSocket or polling for real-time status changes

---

## 3. Detailed Page Specifications

### 3.1 Dashboard (Home Page)

**Purpose**: At-a-glance pipeline health and recent activity

**Key Requirements**:

- Real-time alert panel showing ESE candidates (5σ threshold)
- Auto-refresh every 10 seconds
- Direct links to flagged sources

**Layout** (4 major sections):

```
┌──────────────────────────────────────────────────────────────────┐
│  Pipeline Status          System Health                          │
│  ● Running (72h uptime)  CPU: ███████░░░ 75%  Disk: █████░░░░░ 45%│
│  Queue: 3 pending        Mem: ████████░ 82%  Load: 2.3/4.1/3.8  │
│  Latest: 2025-10-24T...  Cal: 12 active sets                     │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Recent Observations (last 24h)                                  │
│  [Time] [Field] [Dec] [Cal?] [Sources] [Quality] [Quicklook]   │
│  13:28  J1234  +42.3   ✓     1,247     0.92 Jy   [Image]        │
│  12:56  J1142  +38.7   ✓     1,103     0.88 Jy   [Image]        │
│  ...                                                             │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  Recent Images (thumbnails + metadata)                           │
│  [Thumb] [Thumb] [Thumb] [Thumb] [Thumb] [Thumb]                │
│  Click for full resolution and analysis                          │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│  ESE CANDIDATES & ACTIVE ALERTS                    [Live Update] │
│  ───────────────────────────────────                             │
│                                                                  │
│  🔴 HIGH PRIORITY (3) - Auto-flagged >5σ variability             │
│                                                                  │
│  • NVSS J123456.7+420312  |  6.2σ  |  +36% flux  |  3h ago      │
│    [View Source] [Dismiss] [Slack: Sent ✓]                      │
│                                                                  │
│  • NVSS J092334.5+315609  |  8.9σ  |  -60% flux  |  5h ago      │
│    [View Source] [Dismiss] [Slack: Sent ✓]                      │
│                                                                  │
│  • NVSS J145623.2+442156  |  5.4σ  |  Rapid var  |  8h ago      │
│    [View Source] [Dismiss] [Slack: Sent ✓]                      │
│                                                                  │
│  🟡 MEDIUM PRIORITY (1) - System warnings                        │
│                                                                  │
│  • Calibrator 3C286 not detected in last 2h                     │
│    Possible pointing drift or weather issue                      │
│    [Check Telescope Status]                                      │
│                                                                  │
│  🟢 NO CRITICAL ISSUES                                           │
│  • All systems operational                                       │
│  • No failed observations in 24h                                 │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

**Key Metrics Display**:

- Total sources monitored (cumulative)
- Detection rate (sources with good SNR measurements)
- Calibration success rate (% of observations with valid caltables)
- System uptime
- Data throughput (TB/day, images/hour)

### 3.2 Sky Page

**Purpose**: Visual exploration of sky coverage and images

**Primary View**: Interactive sky map showing:

- Observed fields (color-coded by observation time)
- Source density heatmap
- Calibrator positions
- Current/upcoming telescope pointing

**Secondary Views**:

**Mosaic Builder** (High Priority):

```
┌────────────────────────────────────────────────────────────┐
│  Time Range Mosaic Generator                               │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Time Range (UTC):                                          │
│  Start: [2025-10-24 13:00:00 ▾]                            │
│  End:   [2025-10-24 14:00:00 ▾]   (~1 hour)                │
│                                                             │
│  Or specify in MJD:                                         │
│  Start MJD: [60238.541667]  End MJD: [60238.583333]        │
│                                                             │
│  [Generate Mosaic]                                          │
│                                                             │
│  Status: Generating mosaic from 12 individual images...    │
│  Progress: ████████████░░░░░░░░ 60%                        │
│                                                             │
│  Existing Mosaics:                                          │
│  [List of previously generated mosaics with thumbnails]    │
│  - 2025-10-24 13:00-14:00 (142 sources, 0.85 mJy noise)    │
│  - 2025-10-24 12:00-13:00 (138 sources, 0.91 mJy noise)    │
│  [View] [Download FITS] [Download PNG]                     │
└────────────────────────────────────────────────────────────┘
```

**Image Gallery**:

```
┌────────────────────────────────────────────────────────────┐
│  Filters: [Date Range] [Declination] [Quality] [Search]   │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  [Grid of thumbnails, 4-6 per row]                         │
│  Each with: timestamp, field ID, noise level, # sources    │
│  Click → full-res image + metadata + NVSS overlay          │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

**Mosaic Builder**:

- Time-range query (start/end UTC or MJD)
- Declination range filter (+40° to +45° for current pointing)
- Preview coverage map before generation
- Generate stitched mosaic (async job)
- Download FITS/PNG when complete
- Status polling for long-running jobs

**VO Cone Search** (future):

- Simple Cone Search protocol endpoint
- VOTable output format
- Integration with Aladin, TOPCAT
- Enables external tool queries

**Image Detail View**:

```
┌─────────────────────────────────────────────────────────────┐
│  Image: 2025-10-24T13:28:03 | Field J1234+42              │
├─────────────────────────────────────────────────────────────┤
│  [Large image display with zoom/pan]                        │
│  Overlays: NVSS sources, measured sources, noise contours   │
│                                                              │
│  Metadata Panel:                                             │
│    Noise: 0.92 mJy/beam | Beam: 12.3" x 11.8" PA 45°      │
│    Freq: 1.405 GHz | Integration: 300s | MJD 60240.56      │
│    Sources detected: 1,247 (1,203 NVSS matches)            │
│    Calibrator: 3C286 (sep 0.45°, flux 15.2 Jy)            │
│                                                              │
│  Actions:                                                    │
│    [Download FITS] [Download PNG] [View Source List]       │
│    [Reprocess with different params]                        │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Sources Page

**Purpose**: Monitor source flux variability and identify ESE candidates

**Top Section**: Source Search & Filters

```
┌──────────────────────────────────────────────────────────────┐
│  Search: [Source name or RA/Dec]                             │
│  Filters: [Variability > 3σ] [Dec range] [Flux > X mJy]     │
│           [NVSS match quality] [Observation count > N]        │
└──────────────────────────────────────────────────────────────┘
```

**Main View**: Source Table (sortable, paginated)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Source ID          │ RA/Dec    │ NVSS  │ Latest │ Variability │ Trend      │
│  (NVSS catalog)     │           │ (mJy) │ (mJy)  │ σ / χ²     │            │
├─────────────────────┼───────────┼───────┼────────┼─────────────┼────────────┤
│ NVSS J123456+420312 │ 12:34:56  │ 145   │ 198    │ 6.2σ / 8.3 │ ╱━━━━ [↗]  │
│                     │ +42:03:12 │       │        │            │            │
│ NVSS J114233+384709 │ 11:42:33  │ 89    │ 87     │ 0.8σ / 1.1 │ ━━━━━ [─] │
│                     │ +38:47:09 │       │        │            │            │
│ ...                 │           │       │        │            │            │
└─────────────────────┴───────────┴───────┴────────┴─────────────┴────────────┘

Column descriptions:
- Variability σ: Deviation from mean / σ units
- Variability χ²: Reduced chi-square (χ²_ν) for constant model
- Trend: Sparkline of last 20 observations
```

**Source Detail View** (click on any source):

```
┌─────────────────────────────────────────────────────────────┐
│  Source: J1234+4203 | NVSS J123456.7+420312                │
├─────────────────────────────────────────────────────────────┤
│  [Large flux vs. time plot]                                 │
│  X-axis: MJD or UTC time | Y-axis: Flux density (mJy)      │
│  Error bars, color-coded by image noise                     │
│                                                              │
│  Statistics Panel:                                           │
│    Observations: 142                                         │
│    Mean flux: 153 ± 12 mJy                                  │
│    NVSS flux: 145 mJy (α = -0.7 ± 0.2 from VLASS)         │
│    Variability: χ²_ν = 8.3 (6.2σ from constant)            │
│    Max deviation: +45 mJy on MJD 60235.3                    │
│                                                              │
│  Catalog Info:                                               │
│    RA: 12:34:56.7, Dec: +42:03:12 (J2000)                  │
│    NVSS: 145 mJy, VLASS: 98 mJy (α=-0.7), FIRST: resolved  │
│    Confusion flag: No                                        │
│                                                              │
│  Recent Measurements (table):                                │
│    [MJD] [Image] [Flux] [Error] [Separation from phase ctr]│
│    ...                                                       │
│                                                              │
│  Actions:                                                    │
│    [Export data (CSV/JSON)] [Flag as candidate]             │
│    [View all images containing this source]                 │
│    [Literature search (SIMBAD/NED links)]                   │
└─────────────────────────────────────────────────────────────┘
```

**ESE Candidate Dashboard** (high priority):

- Automatically flagged sources with strong variability
- "Extreme" defined as: >5σ deviation OR flux change >50% on <1 day timescale
- Sort by significance, recency, or deviation magnitude
- Quick-approve or dismiss interface

### 3.4 Observing Page

**Purpose**: Real-time telescope status and observing plan

**Current Status Panel**:

```
┌──────────────────────────────────────────────────────────────┐
│  Telescope Pointing                                          │
│  Current: RA 12:45:32, Dec +42:15:00                        │
│  LST: 13:12:45 | Alt 67.2° | Az 145.3°                      │
│  Next transit: 3C286 in 42 minutes                           │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Antenna Status (simplified)                                 │
│  Online: 110/110 | Flagged: 2 (high RFI) | Offline: 0      │
│  [Antenna map with color-coded status markers]              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Calibrator Tracking                                         │
│  Active calibrators (last 6h):                               │
│    3C286: 8 detections, avg flux 15.3 Jy (expected 15.5)   │
│    3C48:  3 detections, avg flux 16.8 Jy (expected 16.4)   │
│  [Plot: calibrator flux vs. elevation over time]            │
└──────────────────────────────────────────────────────────────┘
```

**Pointing History Visualization**:

- Sky map showing pointing centers over last 24h/7d/30d
- Color-coded by time
- Declination strip coverage overlay
- Interactive: click pointing → show observation details

**Calibrator Plan**:

- Upcoming calibrator transits (next 6h)
- Expected elevation, parallactic angle coverage
- Visibility windows for standard calibrators

### 3.5 Health Page

**Purpose**: Deep diagnostics for pipeline and data quality monitoring

**System Monitoring**:

```
┌──────────────────────────────────────────────────────────────┐
│  Resource Usage (last 6h)                                    │
│  [Time-series plots for CPU, Memory, Disk I/O, Load]        │
│  Thresholds marked, color-coded zones                        │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Processing Queue Status                                     │
│  Total groups: 245 | Pending: 3 | In Progress: 1           │
│  Failed: 2 (retry available) | Completed (24h): 142         │
│                                                              │
│  Recent Groups (detailed table):                             │
│  [Group ID] [State] [Subbands] [Calibrator] [Time] [Action]│
│  2025-10-24T13:28 | completed | 16/16 | 3C286 | 3.2m | View│
│  2025-10-24T13:23 | pending   | 16/16 | -     | -    | ...  │
│  ...                                                         │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  Calibration Registry                                        │
│  Active calibration sets: 12                                 │
│  [Set Name] [Tables] [Valid MJD Range] [Last Used]          │
│  bp_3c286_60240 | K,BP,G | 60240.2-60240.8 | 3 min ago     │
│  ...                                                         │
└──────────────────────────────────────────────────────────────┘
```

**Data Quality Metrics**:

```
┌──────────────────────────────────────────────────────────────┐
│  Image Quality Trends (last 7 days)                         │
│  [Plot: Image noise vs. time]                               │
│  Expected thermal noise marked                               │
│  Ratio: observed/thermal (should be ~1.0-1.2)               │
│                                                              │
│  [Plot: Source detection rate vs. time]                     │
│  Expected from NVSS catalog density                          │
│                                                              │
│  [Plot: Calibration solution success rate]                  │
│  % of observations with valid K, BP, G tables                │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  QA Diagnostic Gallery                                       │
│  Recent QA plots (amplitude, phase, UVW coverage)            │
│  [Thumbnail grid, click to expand]                           │
│  Filter by: [All] [Calibrators only] [Failed groups]        │
└──────────────────────────────────────────────────────────────┘
```

**Performance Metrics**:

- Conversion time (UVH5 → MS): mean, p50, p95
- Calibration time (K+BP+G): mean, p50, p95
- Imaging time (tclean): mean, p50, p95
- End-to-end latency (data arrival → final image)
- Throughput: images/hour, sources measured/hour

---

## 4. Technology Stack Recommendations

### 4.1 Core Framework: Modern Web Stack

**Frontend Framework**: **React** (or Vue.js)

- Component-based architecture
- Large ecosystem for scientific visualization
- Well-supported, mature, excellent performance

**State Management**: **Redux Toolkit** (or Zustand for simplicity)

- Centralized state for pipeline status, filters, user preferences
- Time-travel debugging for complex interactions

**Visualization Libraries**:

- **Plotly.js** - Interactive scientific plots (flux vs. time, system metrics)
- **D3.js** - Custom visualizations (sky maps, antenna arrays)
- **React-Grid-Layout** - Responsive dashboard grid system
- **Leaflet** or **Aladin Lite** - Sky coordinate projections

**Data Tables**: **AG Grid** or **TanStack Table**

- High-performance virtual scrolling for 10k+ source tables
- Sorting, filtering, pagination out-of-box
- Export to CSV

**UI Component Library**: **Material-UI (MUI)** or **Ant Design**

- Professional, consistent look
- Accessibility baked in
- Dark mode support

### 4.2 Backend Integration

**API Communication**: **Axios** or **Fetch API**

- REST API calls to FastAPI backend
- Request caching with React Query

**Real-Time Updates**: **WebSockets** or **Server-Sent Events (SSE)**

- Live pipeline status updates
- System metrics streaming
- Alert notifications

**FITS Image Display**: **JS9** or **Aladin Lite**

- In-browser FITS rendering
- Zoom, pan, colormap adjustments
- Overlay support (catalog sources, regions)

### 4.3 Development & Deployment

**Build Tool**: **Vite** (fast, modern)

**Styling**: **Tailwind CSS** + CSS Modules

- Utility-first for rapid prototyping
- Scoped styles for components

**Testing**: **Vitest** + **React Testing Library**

**Deployment**:

- Static build served via Nginx or Apache
- Docker container for full-stack deployment
- Optional: serve via FastAPI StaticFiles mount (already partially implemented)

**CI/CD**: GitHub Actions for build + deploy

**Environment Variables**:

```bash
# Frontend (.env)
VITE_API_BASE_URL=https://dsa110-pipeline.caltech.edu/api
VITE_WS_URL=wss://dsa110-pipeline.caltech.edu/ws
VITE_ESE_THRESHOLD_SIGMA=5.0
VITE_REFRESH_INTERVAL_MS=10000

# Backend (already in contimg.env)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_ALERT_CHANNEL=#dsa110-alerts
ALERT_RATE_LIMIT_SECONDS=3600
ESE_THRESHOLD_SIGMA=5.0
```

### 4.4 Alternative: Streamlit for Rapid Prototyping

If speed-to-deployment is critical, consider **Streamlit** (Python-native):

- Python backend directly (no separate React app)
- Rapid iteration, less boilerplate
- Good for internal/scientist users
- Limitations: less customizable, heavier server load

**Hybrid Approach**:

- Use Streamlit for internal "power user" diagnostics
- Build React app for polished, public-facing interface

---

## 5. Data Visualization Design Patterns

### 5.1 High-Information-Density Techniques

**1. Small Multiples for Source Monitoring**

```
Grid of 20-50 sources per page, each showing:
- Thumbnail flux timeseries (sparkline)
- Color-coded variability indicator
- Latest flux value
- NVSS comparison
```

**2. Heatmaps for Sky Coverage**

```
RA-Dec grid colored by:
- Observation count
- Average image noise
- Number of variable sources detected
- Time since last observation
```

**3. Horizon Plots for Dense Time-Series**

```
Compact representation of system metrics over days/weeks
- Layers of color bands for different value ranges
- Fits many metrics in small vertical space
```

**4. Parallel Coordinates for Multi-Parameter Source Selection**

```
Filter sources simultaneously by:
- NVSS flux
- Variability
- Observation count
- Spectral index
Interactive brushing to select candidates
```

### 5.2 Interactive Features Priority List

**Must-Have** (Phase 1):

- Click-to-drill-down (table row → detail view)
- Hover tooltips on all plots
- Time range selection for mosaics (MJD or UTC)
- Real-time status updates (polling every 10s)
- Live ESE candidate panel (auto-refreshing list of >5σ sources)

**Should-Have** (Phase 2):

- Zoom/pan on sky maps and images
- Cross-filtering (select sources in plot → highlight in table)
- Export data/plots (CSV, PNG, PDF)
- Mosaic generation by time range
- Slack webhook integration for alerts

**Nice-to-Have** (Phase 3):

- User-configurable alert thresholds (per-user database table)
- Comparison mode (show two images/mosaics side-by-side)
- Integration with external catalogs (SIMBAD, NED queries)
- VO cone search protocol support (IVOA compliance)

---

## 6. Implementation Roadmap

### Phase 1: Core Infrastructure (Weeks 1-3)

**Goals**: Functional monitoring dashboard, basic image gallery, source table

**Deliverables**:

1. Project setup (React + Vite + MUI)
2. API client layer (Axios + React Query)
3. Dashboard page (pipeline status, system metrics, recent obs)
4. **ESE Alert Panel** (real-time, 5σ auto-flagging)
5. Sky page - image gallery with thumbnails
6. Health page - queue status, system metrics plots
7. Basic navigation and routing

**Technical Focus**:

- Establish design system (colors, typography, spacing)
- Set up mock data for development
- Implement responsive layout grid
- **Configure polling for real-time alerts (10s interval)**

### Phase 2: Science Features (Weeks 4-6)

**Goals**: Source monitoring, flux timeseries, variability detection

**Deliverables**:

1. Sources page - searchable/sortable table (NVSS ID naming)
2. Source detail view - flux vs. time plots
3. Photometry data API integration
4. Variability statistics display (χ²_ν, σ-deviation)
5. ESE candidate filtering and export
6. Image detail view with metadata
7. **Slack notification integration** (webhook-based)
8. **Mosaic query by time range** (start/end UTC)

**Technical Focus**:

- Plotly.js integration for scientific plots
- Efficient data loading (pagination, virtual scrolling)
- NVSS catalog crossmatch queries
- **Backend: Add Slack webhook endpoint**
- **Backend: Add mosaic query API**

### Phase 3: Advanced Features (Weeks 7-9)

**Goals**: Real-time updates, sky visualization, advanced filtering

**Deliverables**:

1. WebSocket integration for live status
2. Sky map with pointing history (D3.js or Leaflet)
3. Observing page - telescope status, calibrator tracking
4. Advanced source filtering (multi-parameter)
5. FITS image viewer (JS9 or Aladin Lite)
6. QA diagnostic plot gallery
7. **User-configurable alert thresholds** (admin panel)
8. **VO Cone Search endpoint** (Simple Cone Search protocol)

**Technical Focus**:

- Real-time data streaming
- Sky coordinate projections (RA/Dec → pixel)
- FITS file handling in browser
- **VOTable generation for VO compliance**

### Phase 4: Polish & Optimization (Weeks 10-12)

**Goals**: Performance tuning, user feedback integration, documentation

**Deliverables**:

1. Performance optimization (code splitting, lazy loading)
2. Accessibility improvements (WCAG 2.1 AA compliance)
3. User documentation (inline help, tooltips)
4. Export features (CSV, PNG, PDF downloads)
5. Responsive design refinement (mobile-friendly)
6. Automated testing suite

**Technical Focus**:

- Bundle size optimization
- Lighthouse performance audits
- User acceptance testing (UAT)

### Phase 5: Future Enhancements (Ongoing)

- Mosaic builder and stitcher
- Machine learning variability classifier
- Multi-user collaboration features
- Integration with external archives (VizieR, SIMBAD, NED)
- Custom alerting and email notifications
- API rate limiting and caching strategies

---

## 7. Key Design Decisions & Rationale

### 7.1 Why React over alternatives?

**Pros**:

- Massive ecosystem for scientific viz (Plotly, D3 wrappers)
- Component reusability
- Strong TypeScript support
- Easy integration with FastAPI (REST + WS)

**Cons**:

- Steeper learning curve than Streamlit
- More boilerplate than Vue

**Decision**: React for production UI, consider Streamlit prototype for internal
tools

### 7.2 Separation of Concerns: Documentation vs. Dashboard

**MkDocs** (technical documentation):

- Installation guides
- API reference
- Troubleshooting
- Scientific background

**React Dashboard** (operational monitoring):

- Real-time status
- Data visualization
- Interactive exploration
- Science products

These serve different audiences and should remain separate.

### 7.3 Data Refresh Strategy

**Dashboard/Health**: Poll every 5-10s or WebSocket **Sources page**: Lazy load
on demand, cache aggressively **Image gallery**: Paginated, load thumbnails
first **Detail views**: Fetch on-demand, cache in React Query

### 7.4 Mobile Responsiveness

**Priority**: Desktop-first (working scientists use large monitors) **But**:
Ensure responsive breakpoints for tablet/mobile (on-call monitoring)

### 7.5 Dark Mode

**Importance**: High (astronomers work at night, screen glare)
**Implementation**: Use MUI's built-in dark mode, store preference in
localStorage

---

## 8. Metrics for Success

### 8.1 User Experience

- Time to find a specific source: <30 seconds
- Time to assess pipeline health: <10 seconds (at-a-glance dashboard)
- Ease of identifying variable sources: "I know within 5 seconds if something
  interesting happened today"

### 8.2 Performance

- Initial page load: <2 seconds
- Data refresh latency: <1 second
- Source table with 10k entries: <1 second filter/sort
- Image thumbnail load: <500ms per image

### 8.3 Operational

- Uptime: 99.9% (matches API uptime)
- No data loss on refresh (state persistence)
- Cross-browser compatibility (Chrome, Firefox, Safari)

---

## 9. Design Decisions & Specifications

### 9.1 Source Naming Convention

**Decision**: Use NVSS IDs (e.g., "NVSS J123456.7+420312")

- Primary survey for current declination pointings
- Future: Add support for VLASS, FIRST, and other surveys as telescope repoints
- Database schema should include survey_id field for future extensibility

### 9.2 ESE Candidate Auto-Flagging

**Decision**: 5σ variability threshold for auto-flagging

- χ²_ν > 5 OR flux deviation > 5σ from mean triggers ESE candidate flag
- User-configurable thresholds planned for future phase (store in user
  preferences)
- UI should clearly indicate auto-flagged vs. user-flagged sources

### 9.3 Alert System Architecture

**In-App Alerts** (Phase 1 - Immediate):

- Real-time visual alert panel on Dashboard
- Color-coded severity: Red (>5σ), Yellow (3-5σ), Green (normal)
- Continuously updating list of flagged sources
- Click alert → navigate to source detail page

**Slack Integration** (Phase 2):

```python
# Backend implementation (simplified)
webhook_url = os.getenv('SLACK_WEBHOOK_URL')
alert_payload = {
    "text": "ESE Candidate Detected!",
    "attachments": [{
        "color": "danger",
        "fields": [
            {"title": "Source", "value": "NVSS J123456.7+420312", "short": True},
            {"title": "Significance", "value": "6.2σ", "short": True},
            {"title": "Flux Change", "value": "+36% (145→198 mJy)", "short": True},
            {"title": "Last Obs", "value": "2025-10-24 13:28 UTC", "short": True}
        ],
        "actions": [{
            "type": "button",
            "text": "View Source",
            "url": f"https://dsa110-pipeline.caltech.edu/sources/{source_id}"
        }]
    }]
}
```

**Configuration**:

- Environment variable: `SLACK_WEBHOOK_URL`
- Admin panel to set notification thresholds per channel
- Rate limiting: Max 1 alert per source per hour (avoid spam)

### 9.4 Mosaic Query System

**Primary Feature**: Time-range mosaic query

```
User Interface:
┌─────────────────────────────────────────────┐
│  Mosaic Builder                             │
│  ───────────────                            │
│                                             │
│  Start Time: [2025-10-24 00:00 UTC ▾]      │
│  End Time:   [2025-10-24 01:00 UTC ▾]      │
│  Dec Range:  [+40° ▾] to [+45° ▾]          │
│                                             │
│  [Preview Coverage] [Generate Mosaic]       │
└─────────────────────────────────────────────┘
```

**API Endpoint**:

```python
GET /api/mosaic/query
  ?start_mjd=60238.0
  &end_mjd=60238.042  # ~1 hour
  &dec_min=40
  &dec_max=45

Response:
{
  "images": [...],
  "coverage": {"ra_range": [180, 195], "dec_range": [40, 45]},
  "mosaic_url": "/api/mosaic/generate",  # async job
  "job_id": "mosaic_20251024_001"
}
```

**VO Cone Search** (Future - Phase 3):

- Implement Simple Cone Search (SCS) protocol
- Endpoint: `/api/vo/conesearch?RA=188.5&DEC=42.0&SR=0.5`
- Return VOTable format for external tool compatibility
- Enable queries from Aladin, TOPCAT, etc.

### 9.5 Data Retention Policy

**Decision**: Persistent storage, no expiration for now

- All photometry measurements retained indefinitely
- Future: Implement archival strategy (move old data to cold storage after N
  months)
- Database should support efficient time-range queries

### 9.6 Multi-User Features

**Phase 1**: Single-user focus

- User authentication not required for initial deployment
- Flags and notes stored per-session (localStorage)

**Future**: Collaborative features

- Shared candidate lists
- User comments and classifications
- Role-based access (admin, observer, viewer)

---

## 10. Next Steps

1. **Review this document** with the team and prioritize features
2. **Create UI mockups/wireframes** for top 3 pages (Dashboard, Sky, Sources)
3. **Set up development environment** (React + Vite + MUI)
4. **Implement Phase 1 deliverables** (core infrastructure)
5. **User testing** with domain scientists after each phase
6. **Iterate based on feedback**

---

## Appendix A: Technology Alternatives Considered

| Component   | Primary Choice | Alternative         | Reason for Primary                             |
| ----------- | -------------- | ------------------- | ---------------------------------------------- |
| Framework   | React          | Vue.js              | Larger ecosystem, better TypeScript support    |
| Viz Library | Plotly.js      | Matplotlib (static) | Interactivity, browser-native                  |
| Table       | AG Grid        | TanStack Table      | Performance at scale, enterprise features      |
| UI Library  | Material-UI    | Ant Design          | Maturity, community size, astronomy precedents |
| Sky Map     | Aladin Lite    | D3.js custom        | Built for astronomy, FITS-aware                |
| State Mgmt  | Redux Toolkit  | Zustand             | Team familiarity, debugging tools              |
| Build Tool  | Vite           | Webpack             | Speed, modern defaults                         |

## Appendix B: Existing Projects for Inspiration

- **LOFAR Quality & Pipeline Dashboard**: Real-time observing system monitoring
- **Gaia Archive Interface**: High-density source catalog exploration
- **NRAO VLA/ALMA Observing Tools**: Telescope status and proposal planning
- **ZTF Fritz**: Transient classification and real-time alerts (similar
  variability use case)
- **Bloomberg Terminal**: Information-dense, professional trading interfaces

## Appendix C: Accessibility Considerations

- **WCAG 2.1 AA** compliance minimum
- Keyboard navigation for all interactive elements
- Screen reader compatibility (ARIA labels)
- Color-blind friendly palettes (use ColorBrewer schemes)
- Sufficient contrast ratios (4.5:1 for text)
- Zoom support up to 200% without breaking layout

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-24  
**Authors**: AI Assistant (Strategic Design), DSA-110 Team (Domain Expertise)  
**Status**: Draft for Review
