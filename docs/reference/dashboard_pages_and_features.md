# DSA-110 Dashboard: Pages & Features Reference

**Date:** 2025-01-XX  
**Status:** Consolidated feature documentation  
**Audience:** Users, frontend developers, product managers

---

## Implementation Status Legend

- ✅ **Implemented** - Feature is fully implemented and working
- 🔄 **Partially Implemented** - Feature exists but may be incomplete or in progress
- 📋 **Planned** - Feature is planned but not yet implemented
- 💡 **Future** - Feature is in backlog or future consideration

---

## Table of Contents

1. [Dashboard Page (`/dashboard`)](#dashboard-page-dashboard) - ✅ Implemented
2. [Sky View Page (`/sky`)](#sky-view-page-sky) - ✅ Implemented
3. [Sources Page (`/sources`)](#sources-page-sources) - ✅ Implemented
4. [Observing Page (`/observing`)](#observing-page-observing) - ✅ Implemented
5. [Health Page (`/health`)](#health-page-health) - ✅ Implemented
6. [Control Page (`/control`)](#control-page-control) - ✅ Implemented
7. [Streaming Page (`/streaming`)](#streaming-page-streaming) - ✅ Implemented
8. [QA Visualization Page (`/qa`)](#qa-visualization-page-qa) - ✅ Implemented
9. [Data Browser Page (`/data`)](#data-browser-page-data) - ✅ Implemented

---

## Dashboard Page (`/dashboard`)

**URL:** `/dashboard`  
**Status:** ✅ **Implemented**  
**Purpose:** At-a-glance pipeline health and recent activity  
**Refresh Rate:** 10 seconds (auto-refresh)

### Features

#### Pipeline Status Panel

**Status:** ✅ **Implemented**

**Queue Statistics:**
- Total groups in queue
- Pending groups (ready for processing)
- In-progress groups (currently processing)
- Completed groups (successfully processed)
- Failed groups (errors occurred)
- Collecting groups (waiting for all subbands)

**Calibration Sets:**
- Active calibration sets count
- Calibration set details (set name, tables, valid MJD range)
- Last update timestamp
- Number of targets per set

**Recent Observations Table:**
- Last 20 observation groups
- Group ID (normalized timestamp)
- Processing state
- Subband counts (present/expected)
- Calibrator detection status
- Timestamps (received, last update)

#### System Health Panel

**Status:** ✅ **Implemented**

**Resource Metrics:**
- CPU usage percentage (with threshold indicators)
- Memory usage percentage
- Disk usage percentage
- System load averages (1, 5, 15 minutes)

**Real-Time Updates:**
- Last update timestamp
- Current metrics display (no historical chart - see Health page for trends)
- Basic status indicators

#### ESE Candidates Panel

**Status:** ✅ **Implemented**

**Real-Time Variability Alerts:**
- Auto-flagged sources with >5σ variability
- Source ID (NVSS naming convention)
- Maximum σ deviation
- Current flux vs. baseline flux
- Status indicators (active, resolved, false_positive)
- Last detection timestamp
- Auto-refresh every 10 seconds

**Alert Display:**
- Auto-flagged sources with >5σ variability
- Click to navigate to source detail page

#### Pointing Visualization

**Status:** ✅ **Implemented**

**Interactive Sky Map:**
- Current telescope pointing position (RA/Dec)
- Historical pointing trail (configurable days, default 7)
- Color-coded by time
- Click to view observation details

**Display Options:**
- Show/hide historical trail
- Adjust trail duration (1 day, 7 days, 30 days)
- Zoom and pan controls

### API Endpoints Used

- `GET /api/status` - Pipeline queue statistics
- `GET /api/metrics/system` - System health metrics
- `GET /api/ese/candidates` - ESE detection alerts
- `GET /api/pointing_history` - Telescope pointing history

### User Workflows

**Normal Operation:**
1. User opens dashboard
2. Sees pipeline status at a glance
3. Monitors ESE candidates panel for alerts
4. Checks system health metrics

**Alert Investigation:**
1. ESE candidate appears in panel
2. User clicks "View Source"
3. Navigates to Sources page for detailed investigation

---

## Sky View Page (`/sky`)

**URL:** `/sky`  
**Status:** ✅ **Implemented**  
**Purpose:** Visual exploration of sky coverage and images  
**Refresh Rate:** On-demand (user-triggered)

### Features

#### Interactive Sky Map

**Status:** ✅ **Implemented**

**Coverage Visualization:**
- Observed fields (color-coded by observation time)
- Source density heatmap
- Calibrator positions
- Current/upcoming telescope pointing

**Interactive Features:**
- Click field → show observation details
- Zoom and pan controls
- Time range filtering
- Declination range filtering

#### Image Gallery

**Status:** ✅ **Implemented**

**Grid View:**
- Thumbnail grid (4-6 images per row, responsive)
- Each thumbnail shows:
  - Observation timestamp
  - Field ID
  - Noise level
  - Source count
  - Calibrator status

**Filters:**
- Date range (start/end UTC)
- Declination range
- Quality threshold (noise level)
- Primary-beam corrected flag
- Calibrator detected flag
- Search by field ID or coordinates

**Pagination:**
- Configurable items per page
- Page navigation controls
- Total count display

#### Image Detail View

**Status:** ✅ **Implemented**

**Full-Resolution Display:**
- Large image viewer (JS9 integration)
- Zoom and pan controls
- Colormap selection
- Scaling options (linear, log, sqrt)
- Grid overlay toggle
- Catalog overlay toggle

**Metadata Panel:**
- Observation details (date, MJD, integration time)
- Pointing center (RA/Dec)
- Field size
- Image quality metrics:
  - Noise level (mJy/beam)
  - Synthesized beam (major, minor, PA)
  - Noise/thermal ratio
  - Dynamic range
- Frequency information (center, bandwidth)
- Source statistics:
  - Detected sources count
  - NVSS matches count
  - Variable sources count
- Calibration information:
  - Calibrator name
  - Separation from pointing center
  - Measured vs. expected flux
  - Calibration tables used

**Actions:**
- Download FITS file
- View source list
- Catalog overlay toggle
- Region tools (create/edit regions)
- Profile tool
- Image fitting tool
- Photometry plugin

**Note:** Mosaic Builder functionality is available on the separate Mosaic Gallery page (`/mosaics`), not on Sky View page.

### API Endpoints Used

- `GET /api/images` - List images with filters (via ImageBrowser component)
- `GET /api/images/{image_id}/fits` - Download FITS file (for JS9 viewer)
- `GET /api/pointing_history` - Pointing history (for SkyMap component)

### User Workflows

**Image Exploration:**
1. User navigates to Sky View
2. Filters images by date range or quality
3. Clicks thumbnail to view full image
4. Examines image with JS9 viewer
5. Downloads FITS file for analysis

**Image Analysis:**
1. User selects image from browser
2. Views image in JS9 viewer
3. Uses region tools, profile tool, or fitting tool
4. Toggles catalog overlay if needed
5. Examines image metadata

---

## Sources Page (`/sources`)

**URL:** `/sources`  
**Status:** ✅ **Implemented**  
**Purpose:** Monitor source flux variability and identify ESE candidates  
**Refresh Rate:** On-demand (user-triggered)

### Features

#### Source Search & Filters

**Status:** ✅ **Implemented**

**Quick Search:**
- Search by NVSS ID (e.g., `NVSS J123456.7+420312`)
- Enter key to search

**Advanced Filters (Collapsible):**
- Variability threshold slider (0-10σ)
- Declination range slider (-90° to +90°)
- ESE candidates only checkbox

**Filter Management:**
- Active filter count chip
- Clear all filters button
- Show/hide advanced filters toggle

#### Source Table (AG Grid)

**Status:** ✅ **Implemented**

**High-Performance Table:**
- Handles 10,000+ rows efficiently
- Virtual scrolling
- Sortable columns
- Filterable columns
- Pagination (configurable page size)

**Columns:**
- Source ID (NVSS naming, monospace font)
- RA/Dec coordinates (J2000)
- NVSS flux (mJy)
- Latest flux (mJy)
- Variability metrics:
  - σ deviation (highlight if >5)
  - χ²/ν (reduced chi-squared)
- Observation count
- Trend sparkline (last 20 observations)
- Variability indicator (✓/⚠/✗)

**Table Features:**
- Clickable source IDs (navigate to detail page)
- Sortable columns
- Filterable columns
- Pagination (20 items per page)

#### Source Detail View

**Status:** ✅ **Implemented** (Basic detail view with metadata and detections table)

**Source Details Panel:**
- Source name/ID
- RA/Dec coordinates (formatted HH:MM:SS and decimal)
- Flux statistics (mean, std, max SNR if available)
- Variability metrics (v, η if available)
- ESE probability chip (if >0)
- New source chip (if applicable)
- Measurement counts (total, forced)
- External links (SIMBAD, NED)

**Sky Visualization:**
- Aladin Lite placeholder (not yet implemented)

**Comments & Annotations:**
- Placeholder section (not yet implemented)

**Light Curve:**
- Collapsible section (placeholder, not yet implemented)

**Detections Table:**
- GenericTable component
- Columns: Name, RA, Dec, Peak Flux, Integrated Flux, SNR, Forced flag, Date
- Clickable rows (navigate to image detail page)
- Searchable and exportable

**Note:** Light curve visualization, Aladin Lite sky view, and comments system are placeholders and not yet fully implemented.

### API Endpoints Used

- `POST /api/sources/search` - Search sources
- `GET /api/sources/{sourceId}` - Get source details
- `GET /api/sources/{sourceId}/detections` - Get source detections (for detail page table)

### User Workflows

**Source Investigation:**
1. User searches for source by NVSS ID (or uses advanced filters)
2. Views source in table
3. Clicks source ID to navigate to detail page
4. Examines source metadata and detections table
5. Clicks detection row to view associated image

**ESE Candidate Review:**
1. User views ESE candidates on Dashboard
2. Clicks candidate to navigate to source detail page
3. Reviews source metadata and detections
4. Examines variability statistics in table

---

## Observing Page (`/observing`)

**URL:** `/observing`  
**Status:** ✅ **Implemented**  
**Purpose:** Real-time telescope status and observing plan  
**Refresh Rate:** 10 seconds (auto-refresh)

### Features

#### Current Status Panel

**Telescope Pointing:**
- Current RA/Dec coordinates (from most recent pointing history entry)
- Last update timestamp
- Pipeline status chips (pending, in-progress, completed counts)

**Note:** LST, Alt/Az, Parallactic angle, Antenna status, and Observing mode features are not yet implemented.

#### Pointing History Visualization

**Sky Map Display:**
- Pointing centers over last 7 days (fixed)
- Color-coded by time
- Uses PointingVisualization component
- Historical trail display

**Note:** Time range selection, declination strip overlay, and click-to-view details are not yet implemented.

#### Calibrator Tracking

**Active Calibrators (Recent):**
- Calibrator name
- RA/Dec coordinates
- Flux (mJy)
- Separation from pointing center (°)
- Last seen timestamp
- Table display (top 10 matches)

**Calibrator Flux vs Time:**
- Time-series plot (Plotly.js)
- Multiple calibrators overlaid
- Shows flux measurements over time
- Conditional display (only shown if multiple measurements exist)

**Note:** Elevation-dependent effects, expected flux markers, and Calibrator Plan (upcoming transits) are not yet implemented.

### API Endpoints Used

- `GET /api/pointing_history` - Pointing history (used to derive current pointing)
- `GET /api/calibrator_matches` - Calibrator detection history
- `GET /api/status` - Pipeline status

### User Workflows

**Monitoring Telescope Status:**
1. User opens Observing page
2. Checks current pointing (RA/Dec from most recent history)
3. Reviews pipeline status chips
4. Views calibrator tracking table
5. Examines calibrator flux vs time plot (if data available)

**Pointing History Analysis:**
1. User views pointing history visualization (7-day trail)
2. Examines pointing patterns on sky map
3. Reviews calibrator matches in table

---

## Health Page (`/health`)

**URL:** `/health`  
**Status:** ✅ **Implemented**  
**Purpose:** Deep diagnostics for pipeline and data quality monitoring  
**Refresh Rate:** 10 seconds (auto-refresh)

### Features

#### System Monitoring

**Current Metrics (Metric Cards):**
- CPU usage percentage (with progress bar and thresholds)
- Memory usage percentage (with progress bar and thresholds)
- Disk usage percentage (with progress bar and thresholds)
- Load average (1m) display

**Resource Usage Plot:**
- Basic plot showing current CPU and Memory % (single data point, not historical)
- Plotly.js visualization

**Detailed Metrics:**
- Memory details (total, used in GB)
- Disk details (total, used, available in GB)
- Load averages (1m, 5m, 15m)

**Note:** Historical metrics plots (last 6 hours), average/peak values, and color-coded zones are not yet implemented.

#### Processing Queue Status

**Queue Statistics:**
- Total groups
- Pending groups
- In-progress groups
- Failed groups
- Completed groups (last 24 hours)

**State Distribution:**
- Visual bar chart
- Percentage breakdown
- Color-coded by state

**Recent Groups Table:**
- Group ID
- Processing state (with color-coded chips)
- Subband counts (present/expected)
- Top 10 recent groups displayed

#### QA Diagnostics Tab

**ESE Candidates Table:**
- Source ID
- Max σ deviation
- Status (active/resolved/false_positive)
- Last detection timestamp
- Top 10 candidates displayed

**Link to QA Visualization:**
- Alert with link to `/qa` page for full QA diagnostics

**Note:** Calibration Registry, Data Quality Metrics, Performance Metrics, and QA Diagnostic Gallery features are not yet implemented on this page. See QA Visualization page for QA features.

### API Endpoints Used

- `GET /api/metrics/system` - System metrics
- `GET /api/status` - Queue statistics
- `GET /api/ese/candidates` - ESE candidates

### User Workflows

**System Health Monitoring:**
1. User opens Health page
2. Reviews resource usage trends
3. Checks queue statistics
4. Examines data quality metrics
5. Identifies potential issues

**Diagnostic Investigation:**
1. User notices elevated metrics
2. Reviews QA diagnostic gallery
3. Examines failed groups
4. Checks calibration registry
5. Takes corrective action

---

## Control Page (`/control`)

**URL:** `/control`  
**Status:** ✅ **Implemented**  
**Purpose:** Manual job execution for selected Measurement Sets  
**Refresh Rate:** 5 seconds (for job status)

### Features

#### Job Submission Forms

**Convert Job:**
- Select UVH5 files or group ID
- Output directory
- Configuration options

**Calibrate Job:**
- Select Measurement Set
- Reference antenna (default: "103")
- Solve bandpass (yes/no)
- Solve gains (yes/no)
- Gain solution interval
- Gain calibration mode (ap, apcal)
- Auto-detect fields
- Minimum primary beam threshold

**Apply Job:**
- Select Measurement Set
- Select calibration tables (K, BP, G)
- Apply options

**Image Job:**
- Select Measurement Set
- Imaging parameters:
  - Gridder (wgridder, standard)
  - Cell size
  - Image size
  - Weighting (natural, uniform, robust)
  - Deconvolution algorithm
  - Iteration limits

**Workflow Job:**
- End-to-end pipeline execution
- Convert → Calibrate → Apply → Image
- Configuration for each stage

#### MS Browser

**Measurement Set List:**
- Available Measurement Sets
- Filter by path, date, state
- Sortable columns
- Select MS for job submission

**MS Details:**
- Path
- Processing stage
- Timestamps (created, updated)
- Calibration status
- Image status

#### Job Management

**Job List:**
- Recent jobs (with status filter)
- Job type, status, MS path
- Created, started, finished timestamps
- Actions (View Details, View Logs, Cancel)

**Job Details:**
- Job parameters
- Status history
- Logs (live streaming via SSE)
- Artifacts (output files)
- Error messages (if failed)

**Live Log Streaming:**
- Server-Sent Events (SSE) for real-time logs
- Auto-scroll to latest
- Filter log levels
- Export logs

#### Calibration QA Display

**Calibration Quality Metrics:**
- K-table SNR
- Bandpass RMS
- Gain solution quality
- Bandpass plots
- Gain solution plots

**QA Visualization:**
- Interactive plots
- Quality indicators
- Comparison with expected values

### API Endpoints Used

- `GET /api/ms` - List Measurement Sets
- `GET /api/ms/{ms_path}` - Get MS details
- `POST /api/jobs/calibrate` - Create calibration job
- `POST /api/jobs/apply` - Create apply job
- `POST /api/jobs/image` - Create imaging job
- `POST /api/jobs/workflow` - Create workflow job
- `GET /api/jobs` - List jobs
- `GET /api/jobs/{job_id}` - Get job details
- `GET /api/jobs/{job_id}/logs` - Stream job logs
- `GET /api/calibration/qa` - Get calibration QA

### User Workflows

**Manual Calibration:**
1. User selects Measurement Set
2. Configures calibration parameters
3. Submits calibration job
4. Monitors job progress
5. Reviews calibration QA
6. Applies calibration if quality is good

**Reprocessing:**
1. User identifies failed observation
2. Selects Measurement Set
3. Submits workflow job
4. Monitors end-to-end processing
5. Reviews results

---

## Streaming Page (`/streaming`)

**URL:** `/streaming`  
**Status:** ✅ **Implemented**  
**Purpose:** Control and monitor the streaming converter service  
**Refresh Rate:** 5 seconds (auto-refresh)

### Features

#### Service Control

**Service Status:**
- Running/Stopped/Error state
- Process ID (PID)
- Started timestamp
- Uptime (formatted)
- Error message (if any)

**Control Buttons:**
- Start service
- Stop service
- Restart service
- Update configuration

#### Real-Time Status

**Service Status:**
- Running/Stopped state (with chip indicator)
- Health status chip (if healthy)
- Process ID (PID)
- Started timestamp
- Uptime (formatted: hours, minutes, seconds)

**Resource Usage:**
- CPU percentage (with progress bar and color coding)
- Memory usage (MB, with progress bar)
- Real-time updates (5s refresh)

#### Queue Statistics

**Queue Metrics:**
- Total groups processed
- Groups processed in last hour
- Average processing time per group
- Current queue depth (if available from status)

**Note:** Detailed processing rate metrics and throughput breakdown are not yet fully implemented.

#### Configuration Management

**Current Configuration:**
- Input directory
- Output directory
- Max workers
- Expected subbands
- Other settings

**Configuration Editor:**
- Dialog-based configuration editor
- Edit configuration values
- Save configuration (updates via API)
- Configuration displayed in dialog form

### API Endpoints Used

- `GET /api/streaming/status` - Service status
- `GET /api/streaming/health` - Health check
- `GET /api/streaming/config` - Get configuration
- `PUT /api/streaming/config` - Update configuration
- `POST /api/streaming/start` - Start service
- `POST /api/streaming/stop` - Stop service
- `POST /api/streaming/restart` - Restart service
- `GET /api/streaming/metrics` - Processing metrics

### User Workflows

**Starting Streaming Service:**
1. User navigates to Streaming page
2. Reviews current configuration
3. Clicks "Start" button
4. Monitors service status
5. Reviews queue statistics

**Updating Configuration:**
1. User clicks "Edit Configuration"
2. Modifies configuration values
3. Validates changes
4. Saves configuration
5. Restarts service if needed

---

## QA Visualization Page (`/qa`)

**URL:** `/qa`  
**Status:** ✅ **Implemented**  
**Purpose:** Quality assurance data visualization and exploration  
**Refresh Rate:** On-demand (user-triggered)

### Features

#### Directory Browser

**File Tree Navigation:**
- Browse QA artifact directories
- Expand/collapse folders
- Filter by file type (FITS, images, logs, tables)
- Search functionality
- File metadata (size, modified time)

**File Actions:**
- View FITS file
- View CASA table
- Download file
- Generate notebook

#### FITS Viewer

**JS9 Integration:**
- Load FITS files
- Scale controls (linear, log, sqrt)
- Colormap selection
- Zoom and pan
- Coordinate display (RA/Dec, pixel)
- Image statistics

**Note:** Dual Window Mode (side-by-side comparison) is not yet implemented.

#### CASA Table Viewer

**Table Browser:**
- Browse Measurement Set tables
- Column selection
- Filtering and sorting
- Subtable navigation
- Data export (CSV)

**Table Types:**
- MAIN table (visibilities)
- ANTENNA table
- FIELD table
- SPECTRAL_WINDOW table
- POLARIZATION table
- Other subtables

#### QA Notebook Generator

**Automated Report Generation:**
- Generate Jupyter notebooks for QA analysis
- Customizable templates
- Include relevant plots and data
- Export notebook file

**Notebook Templates:**
- Calibration QA
- Image QA
- Source detection QA
- Custom analysis

### API Endpoints Used

- `GET /api/visualization/browse` - Browse QA directory
- `GET /api/visualization/fits/view` - View FITS file
- `GET /api/visualization/casa/table` - Browse CASA table
- `POST /api/visualization/qa/run` - Run QA analysis
- `GET /api/visualization/qa/notebook` - Generate QA notebook

### User Workflows

**QA Review:**
1. User navigates to QA page
2. Browses QA directory
3. Views FITS files with JS9
4. Examines CASA tables
5. Generates QA notebook for detailed analysis

**Diagnostic Investigation:**
1. User identifies quality issue
2. Navigates to QA page
3. Locates relevant QA artifacts
4. Examines plots and tables
5. Generates diagnostic report

---

## Data Browser Page (`/data`)

**URL:** `/data`  
**Status:** ✅ **Implemented**  
**Purpose:** Browse data products and visualize data lineage  
**Refresh Rate:** On-demand (user-triggered)

### Features

#### Data Product Browser

**Product Types:**
- Images (FITS files)
- Mosaics (combined images)
- Catalogs (source lists)
- Measurement Sets

**Filters:**
- Date range
- Product type
- Quality threshold
- Search functionality

**Product Details:**
- Metadata display
- File paths
- Processing history
- Related products

**Note:** Data Lineage Graph visualization is not yet implemented. Data detail pages (`/data/:type/:id`) may provide lineage information.

### API Endpoints Used

- `GET /api/data` - List data instances (with type and status filters)
- `GET /api/data/{type}/{id}` - Get data instance details (via detail page)

### User Workflows

**Product Exploration:**
1. User navigates to Data Browser
2. Filters products by type or date
3. Views product details
4. Examines data lineage
5. Downloads products

---

## Common Features Across Pages

### Navigation

**Top Navigation Bar:**
- Logo and title
- Page links (Dashboard, Sky, Sources, etc.)
- Settings menu (future)
- User menu (future)

**Breadcrumbs:**
- Page hierarchy
- Quick navigation
- Current page indicator

### Real-Time Updates

**Update Mechanisms:**
- WebSocket (primary)
- HTTP polling (fallback)
- Server-Sent Events (for logs)

**Update Intervals:**
- Critical data: 10 seconds
- Job status: 5 seconds
- On-demand: User-triggered

### Error Handling

**Error Display:**
- User-friendly error messages
- Retry buttons
- Error details (in development mode)
- Error boundaries for component errors

### Loading States

**Loading Indicators:**
- Circular progress for data loading
- Skeleton loaders for better UX
- Progress bars for long operations
- Status messages

### Export Functionality

**Export Options:**
- CSV export for tables
- JSON export for data
- PNG export for images
- FITS download for images
- PDF export for reports (future)

---

## Related Documentation

- **[Dashboard Quick Start](../how-to/dashboard-quickstart.md)** - Getting started guide
- **[API Reference](./dashboard_api.md)** - API endpoint documentation
- **[Dashboard Architecture](../concepts/dashboard_architecture.md)** - System architecture
- **[Dashboard Vision & Design](../concepts/dashboard_vision_and_design.md)** - Design principles

---

**Last Updated:** 2025-01-XX  
**Status:** Consolidated Feature Reference

