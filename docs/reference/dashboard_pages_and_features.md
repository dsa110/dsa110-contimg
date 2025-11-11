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
2. [Sky View Page (`/sky`)](#sky-view-page-sky) - 🔄 Partially Implemented
3. [Sources Page (`/sources`)](#sources-page-sources) - 🔄 Partially Implemented
4. [Observing Page (`/observing`)](#observing-page-observing) - 📋 Planned
5. [Health Page (`/health`)](#health-page-health) - 📋 Planned
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
- Live metrics chart (last 6 hours)
- Color-coded status indicators (green/yellow/red)

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

**Alert Prioritization:**
- High priority (>5σ deviation)
- Medium priority (3-5σ deviation)
- Quick actions (View Source, Dismiss, Export)

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
**Status:** 🔄 **Partially Implemented**  
**Purpose:** Visual exploration of sky coverage and images  
**Refresh Rate:** On-demand (user-triggered)

### Features

#### Interactive Sky Map

**Status:** 📋 **Planned** (Not yet implemented)

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

**Status:** 🔄 **Partially Implemented** (Basic gallery exists, advanced features planned)

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

**Status:** 🔄 **Partially Implemented** (JS9 viewer exists, some metadata features planned)

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
- Download PNG image
- View source list
- Reprocess with different parameters
- View QA plots

#### Mosaic Builder

**Status:** ✅ **Implemented** (Query and list implemented, generation UI in progress)

**Time-Range Query:**
- Start/End DateTime pickers (UTC timezone)
- MJD conversion support
- Declination range filter
- Preview coverage map before generation

**Mosaic Generation:**
- Create new mosaic from time range
- Background processing with status updates
- Progress tracking (0-100%)
- Status indicators (pending, in_progress, completed, failed)

**Existing Mosaics:**
- List previously generated mosaics
- Thumbnail previews (when available)
- Metadata display:
  - Time range
  - Source count
  - Noise level
  - Image count
- Download options (FITS, PNG)
- Quick view button

### API Endpoints Used

- `GET /api/images` - List images with filters
- `GET /api/images/{image_id}` - Get image details
- `GET /api/images/{image_id}/fits` - Download FITS file
- `POST /api/mosaics/query` - Query mosaics by time range
- `POST /api/mosaics/create` - Create new mosaic
- `GET /api/mosaics/{mosaic_id}` - Get mosaic details

### User Workflows

**Image Exploration:**
1. User navigates to Sky View
2. Filters images by date range or quality
3. Clicks thumbnail to view full image
4. Examines image with JS9 viewer
5. Downloads FITS file for analysis

**Mosaic Creation:**
1. User selects time range (e.g., 1 hour)
2. Clicks "Generate Mosaic"
3. Monitors progress in mosaic gallery
4. Downloads completed mosaic

---

## Sources Page (`/sources`)

**URL:** `/sources`  
**Status:** 🔄 **Partially Implemented**  
**Purpose:** Monitor source flux variability and identify ESE candidates  
**Refresh Rate:** On-demand (user-triggered)

### Features

#### Source Search & Filters

**Status:** ✅ **Implemented**

**Quick Search:**
- Search by NVSS ID (e.g., `NVSS J123456.7+420312`)
- Search by coordinates (RA/Dec)
- Auto-complete suggestions

**Advanced Filters:**
- Variability threshold (χ² > 5, σ deviation)
- Declination range
- NVSS flux range
- Observation count threshold
- Spectral index range
- ESE candidates only
- User-flagged sources
- New detections (last 7 days)

**Active Filters Display:**
- Shows active filters as chips
- Quick remove buttons
- Save filter presets (future)

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

**Bulk Actions:**
- Select all / Deselect all
- Flag selected sources
- Export selected (CSV, JSON)
- Add to watch list

#### Source Detail View

**Status:** 🔄 **Partially Implemented** (Basic detail view exists, advanced features planned)

**Flux Light Curve:**
- Interactive Plotly.js visualization
- Flux vs. time (MJD or UTC)
- Error bars for each measurement
- Mean flux reference line
- NVSS reference flux line
- Zoom, pan, and export capabilities

**Statistics Panel:**
- Observations count
- Mean flux ± standard deviation
- NVSS flux (with spectral index from VLASS)
- Variability metrics:
  - χ²/ν (reduced chi-squared)
  - σ deviation from constant model
  - Maximum deviation (magnitude and time)
- Variability timescale (shortest variation)

**Catalog Information:**
- RA/Dec coordinates (J2000, Galactic)
- NVSS flux
- VLASS flux (with spectral index)
- FIRST resolution status
- Confusion flag
- External links (SIMBAD, NED, VizieR)

**Recent Measurements Table:**
- MJD timestamp
- Date/Time (UTC)
- Image identifier
- Flux measurement (Jy)
- Flux error (Jy)
- Separation from phase center
- Signal-to-noise ratio

**Images Containing Source:**
- Grid of image thumbnails
- Each shows timestamp and measured flux
- Click to view image in Sky View

**Notes & Classification:**
- User notes and comments
- Classification tags
- Flag status
- Collaborative features (future)

### API Endpoints Used

- `POST /api/sources/search` - Search sources
- `GET /api/sources/{source_id}` - Get source details
- `GET /api/sources/{source_id}/timeseries` - Get flux timeseries
- `GET /api/ese/candidates` - Get ESE candidates

### User Workflows

**Source Investigation:**
1. User searches for source by NVSS ID
2. Views flux light curve
3. Examines variability statistics
4. Compares with catalog values
5. Flags as ESE candidate if significant

**ESE Candidate Review:**
1. User views ESE candidates panel
2. Clicks candidate to view details
3. Reviews light curve and statistics
4. Compares with historical data
5. Approves or dismisses candidate

---

## Observing Page (`/observing`)

**URL:** `/observing`  
**Status:** 📋 **Planned** (Not yet implemented)  
**Purpose:** Real-time telescope status and observing plan  
**Refresh Rate:** 10 seconds (auto-refresh)

### Features

#### Current Status Panel

**Telescope Pointing:**
- Current RA/Dec coordinates
- Local Sidereal Time (LST)
- Altitude and Azimuth
- Parallactic angle
- Next calibrator transit information

**Antenna Status:**
- Total antennas count
- Online antennas count
- Flagged antennas (with reason)
- Offline antennas
- Antenna array map (color-coded status)

**Observing Mode:**
- Current mode (drift scan, etc.)
- Cadence (5 minutes)
- Field size
- Frequency setup

#### Pointing History Visualization

**Sky Map Display:**
- Pointing centers over last 24h/7d/30d
- Color-coded by time
- Declination strip coverage overlay
- Interactive: click pointing → show observation details

**Time Range Selection:**
- Last 24 hours
- Last 7 days
- Last 30 days
- Custom date range

#### Calibrator Tracking

**Active Calibrators (Last 6 Hours):**
- Calibrator name
- RA/Dec coordinates
- Detection count
- Average flux vs. expected flux
- Deviation percentage
- Last seen timestamp

**Calibrator Flux vs. Elevation:**
- Time-series plot
- Multiple calibrators overlaid
- Expected flux marked
- Elevation-dependent effects visible

**Calibrator Plan:**
- Upcoming calibrator transits (next 6 hours)
- Peak elevation
- Parallactic angle coverage
- Visibility windows
- Transit times

### API Endpoints Used

- `GET /api/pointing/current` - Current telescope pointing
- `GET /api/pointing_history` - Pointing history
- `GET /api/calibrator_matches` - Calibrator detection history
- `GET /api/antenna/status` - Antenna status (future)

### User Workflows

**Monitoring Telescope Status:**
1. User opens Observing page
2. Checks current pointing and antenna status
3. Reviews calibrator tracking
4. Plans for upcoming calibrator transits

**Pointing History Analysis:**
1. User selects time range
2. Views pointing trail on sky map
3. Clicks pointing to view observation details
4. Analyzes coverage patterns

---

## Health Page (`/health`)

**URL:** `/health`  
**Status:** 📋 **Planned** (Not yet implemented)  
**Purpose:** Deep diagnostics for pipeline and data quality monitoring  
**Refresh Rate:** 10 seconds (auto-refresh)

### Features

#### System Monitoring

**Resource Usage Plots (Last 6 Hours):**
- CPU usage (with threshold markers)
- Memory usage
- Disk I/O
- System load averages
- Color-coded zones (normal/warning/critical)

**Current Metrics:**
- CPU percentage (current, average, peak)
- Memory percentage (current, average, peak)
- Disk usage (total, used, available)
- Load averages (1, 5, 15 minutes)

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
- Processing state
- Subband counts
- Calibrator detection
- Processing time
- Retry count
- Actions (View QA, Retry, etc.)

#### Calibration Registry

**Active Calibration Sets:**
- Set name
- Table types (K, BP, G)
- Valid MJD range
- Last used timestamp
- Usage count
- Status (active, expired, retired)

**Calibration Set Details:**
- Table paths
- Calibrator source
- Reference antenna
- Creation timestamp
- Notes

#### Data Quality Metrics

**Image Quality Trends (Last 7 Days):**
- Image noise vs. time
- Expected thermal noise marked
- Noise/thermal ratio (should be ~1.0-1.2)
- Source detection rate vs. time
- Expected from NVSS catalog density
- Calibration solution success rate

**Performance Metrics:**
- Conversion time (UVH5 → MS): mean, p50, p95
- Calibration time (K+BP+G): mean, p50, p95
- Imaging time (tclean): mean, p50, p95
- End-to-end latency (data arrival → final image)
- Throughput: images/hour, sources measured/hour

#### QA Diagnostic Gallery

**Recent QA Plots:**
- Thumbnail grid
- Filter by: All, Calibrators only, Failed groups
- Click to expand full-size view
- Types: amplitude, phase, UVW coverage

**QA Plot Types:**
- Calibration solutions (bandpass, gains)
- Flagging statistics
- Image quality metrics
- Source detection plots

### API Endpoints Used

- `GET /api/metrics/system` - System metrics
- `GET /api/metrics/system/history` - Historical metrics
- `GET /api/status` - Queue statistics
- `GET /api/groups/{group_id}` - Group details
- `GET /api/calibration/registry` - Calibration registry
- `GET /api/qa` - QA artifacts list

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

**Current Operations:**
- Operation type (conversion, calibration, imaging, mosaicking, QA)
- Operation status (pending, in-progress, completed, failed)
- Progress percentage (0-100%)
- Started timestamp
- Estimated completion time
- Resource usage (CPU, memory)

**Resource Usage:**
- CPU percentage (with progress bar)
- Memory usage (MB)
- Real-time updates

#### Queue Statistics

**Queue Depth:**
- Pending groups
- In-progress groups
- Completed groups (last 24h)
- Failed groups

**Processing Rate:**
- Groups processed per hour
- Average processing time
- Throughput metrics

#### Configuration Management

**Current Configuration:**
- Input directory
- Output directory
- Max workers
- Expected subbands
- Other settings

**Configuration Editor:**
- Edit configuration values
- Validation before save
- Apply without restart (if supported)
- Reset to defaults

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

**Dual Window Mode:**
- Compare two FITS files side-by-side
- Synchronized zoom/pan
- Difference mode

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

#### Data Lineage Graph

**Visualization:**
- Data flow from raw data to products
- Dependencies and relationships
- Interactive exploration
- Click to view details

**Lineage Information:**
- Source data (UVH5 files)
- Intermediate products (MS files)
- Final products (images, mosaics)
- Processing steps

### API Endpoints Used

- `GET /api/products` - List data products
- `GET /api/products/{product_id}` - Get product details
- `GET /api/lineage/{product_id}` - Get data lineage

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

