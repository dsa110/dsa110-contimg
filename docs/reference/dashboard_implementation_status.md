# DSA-110 Dashboard: Implementation Status Summary

**Date:** 2025-01-XX  
**Purpose:** Clear overview of what is implemented, partially implemented, and planned  
**Last Updated:** 2025-01-XX

---

## Status Legend

- ✅ **Implemented** - Feature is fully implemented and working in production
- 🔄 **Partially Implemented** - Feature exists but may be incomplete, missing some functionality, or in active development
- 📋 **Planned** - Feature is planned but not yet implemented (may have design/docs but no code)
- 💡 **Future** - Feature is in backlog or future consideration

---

## Pages Implementation Status

### ✅ Fully Implemented Pages

1. **Dashboard Page** (`/dashboard`)
   - Pipeline status panel ✅
   - System health metrics ✅
   - ESE candidates panel ✅
   - Pointing visualization ✅
   - Recent observations table ✅

2. **Control Page** (`/control`)
   - Job submission forms ✅
   - MS list and selection ✅
   - Calibration QA display ✅
   - Job status monitoring ✅

3. **Streaming Page** (`/streaming`)
   - Service control (start/stop/restart) ✅
   - Status monitoring ✅
   - Configuration management ✅
   - Resource usage display ✅

4. **QA Visualization Page** (`/qa`)
   - Directory browser ✅
   - FITS viewer ✅
   - CASA table viewer ✅
   - QA notebook generator 🔄 (in progress)

5. **Data Browser Page** (`/data`)
   - Data product browser ✅
   - Staging/Published tabs ✅
   - Data type filtering ✅

6. **Sky View Page** (`/sky`)
   - Image gallery with advanced filtering ✅
   - Image detail view with JS9 ✅
   - Interactive sky map (SkyMap component) ✅
   - Catalog overlay ✅
   - Region tools ✅
   - Profile tool ✅
   - Image fitting tool ✅
   - Photometry plugin ✅

7. **Sources Page** (`/sources`)
   - Source search ✅
   - Source table (AG Grid) ✅
   - Advanced filtering (variability threshold, declination range, ESE filter) ✅
   - Source detail view ✅ (basic with metadata and detections table)
   - Light curve visualization 📋 (placeholder)

8. **Observing Page** (`/observing`)
   - Current pointing display ✅
   - Pointing history visualization ✅
   - Calibrator tracking table ✅
   - Calibrator flux vs time plot ✅
   - Pipeline status integration ✅

9. **Health Page** (`/health`)
   - System monitoring tab ✅
   - Queue status tab ✅
   - QA diagnostics tab ✅
   - ESE candidates table ✅

**Note:** Some advanced features within pages are still planned or partially implemented (e.g., light curve visualization, Aladin Lite, historical metrics plots). See individual page documentation for detailed feature status.

---

## Feature Implementation Status

### Core Infrastructure

**Status:** ✅ **Completed**

- ✅ React 18 + TypeScript setup
- ✅ Material-UI v6 theme
- ✅ React Router v6 routing
- ✅ React Query integration
- ✅ API client with error handling
- ✅ WebSocket client (basic)
- ✅ Error boundaries
- ✅ Navigation component

### Real-Time Updates

**Status:** ✅ **Implemented** (Basic)

- ✅ HTTP polling (10s intervals for most pages)
- ✅ WebSocket client (basic connection)
- ✅ React Query integration with polling
- 📋 Advanced WebSocket integration with React Query (in progress)
- 📋 SSE fallback (planned)
- 📋 Connection state UI indicators (planned)

### ESE Detection

**Status:** ✅ **Implemented**

- ✅ Auto-flagging (>5σ threshold)
- ✅ Candidate list display
- ✅ Real-time updates
- 🔄 Slack notification integration (in progress)
- 📋 User-configurable thresholds (planned)

### Source Monitoring

**Status:** ✅ **Implemented**

- ✅ Source search
- ✅ Source table with AG Grid
- ✅ Source detail view with metadata and detections table
- ✅ Advanced filtering (variability threshold, declination range, ESE filter)
- ✅ Clickable source IDs (navigate to detail page)
- ✅ Filter management (chips, clear button)
- 📋 Light curve visualization (placeholder)
- 📋 Aladin Lite sky view (placeholder)

### Mosaic Features

**Status:** ✅ **Implemented** (on Mosaic Gallery page, not Sky View)

- ✅ Mosaic query by time range
- ✅ Mosaic list display
- ✅ Mosaic detail view
- ✅ Mosaic generation UI
- 📋 Mosaic preview coverage map (planned)
- 📋 Mosaic comparison tools (planned)

### Image Features

**Status:** ✅ **Implemented**

- ✅ Image gallery with advanced filtering
- ✅ Image detail view with JS9
- ✅ FITS file download
- ✅ Image metadata display
- ✅ Catalog overlay (JS9 integration)
- ✅ Region tools
- ✅ Profile tool
- ✅ Image fitting tool
- ✅ Photometry plugin

### QA Visualization

**Status:** ✅ **Implemented**

- ✅ Directory browser
- ✅ FITS viewer (JS9)
- ✅ CASA table viewer
- 🔄 QA notebook generator (in progress)
- 📋 Advanced QA analysis tools (planned)

### Control & Job Management

**Status:** ✅ **Implemented**

- ✅ Job submission forms
- ✅ MS list and selection
- ✅ Job status monitoring
- ✅ Calibration QA display
- ✅ Workflow job execution
- 📋 Job history and logs (planned)
- 📋 Job scheduling (planned)

### Streaming Service Control

**Status:** ✅ **Implemented**

- ✅ Service start/stop/restart
- ✅ Status monitoring
- ✅ Configuration management
- ✅ Resource usage display
- ✅ Queue statistics
- 📋 Historical metrics graphs (planned)
- 📋 Alert notifications (planned)

---

## API Endpoints Implementation Status

### ✅ Implemented Endpoints

**Core Status:**
- ✅ `GET /api/status` - Pipeline status
- ✅ `GET /api/metrics/system` - System metrics

**ESE Detection:**
- ✅ `GET /api/ese/candidates` - ESE candidates list
- ✅ `GET /api/alerts/history` - Alert history

**Sources:**
- ✅ `POST /api/sources/search` - Source search
- ✅ `GET /api/sources/{sourceId}` - Source details

**Mosaics:**
- ✅ `POST /api/mosaics/query` - Query mosaics
- ✅ `GET /api/mosaics/{mosaicId}` - Mosaic details

**Streaming:**
- ✅ `GET /api/streaming/status` - Service status
- ✅ `POST /api/streaming/start` - Start service
- ✅ `POST /api/streaming/stop` - Stop service
- ✅ `POST /api/streaming/restart` - Restart service
- ✅ `GET /api/streaming/config` - Get config
- ✅ `POST /api/streaming/config` - Update config

**QA:**
- ✅ `GET /api/qa/directories` - Browse directories
- ✅ `GET /api/qa/fits/{path}` - FITS info
- ✅ `GET /api/qa/casa/{path}` - CASA table info

**Control:**
- ✅ `GET /api/control/ms/list` - MS list
- ✅ `POST /api/control/jobs/create` - Create job
- ✅ `GET /api/control/jobs` - Job list

### 🔄 Partially Implemented Endpoints

- 🔄 `POST /api/mosaics/generate` - Mosaic generation (backend exists, UI in progress)
- 🔄 `GET /api/sources/{sourceId}/timeseries` - Timeseries (basic exists, advanced features planned)

**Observing:**
- ✅ `GET /api/pointing_history` - Pointing history
- ✅ `GET /api/calibrator_matches` - Calibrator matches

**Health:**
- ✅ `GET /api/metrics/system` - System metrics
- ✅ `GET /api/status` - Queue statistics
- ✅ `GET /api/ese/candidates` - ESE candidates

### 📋 Planned Endpoints

- 📋 `GET /api/metrics/system/history` - Historical metrics (for Health page trends)
- 📋 `GET /api/observing/current` - Current telescope pointing (with LST, Alt/Az)
- 📋 `GET /api/antenna/status` - Antenna status
- 📋 `POST /api/ese/candidates/{id}/dismiss` - Dismiss candidate
- 📋 `POST /api/ese/candidates/{id}/flag` - Flag candidate

---

## Database Schema Implementation Status

### ✅ Implemented Tables

**Ingest Queue Database:**
- ✅ `ingest_queue` - Observation groups
- ✅ `subband_files` - Subband file tracking
- ✅ `performance_metrics` - Processing performance

**Products Database:**
- ✅ `ms_index` - Measurement Sets
- ✅ `images` - Image products
- ✅ `photometry` - Photometry measurements
- ✅ `variability_stats` - Variability statistics
- ✅ `ese_candidates` - ESE candidates
- ✅ `mosaics` - Mosaic products
- ✅ `qa_artifacts` - QA artifacts
- ✅ `pointing_history` - Pointing history
- ✅ `alert_history` - Alert history

**Calibration Registry:**
- ✅ `caltables` - Calibration tables

**Master Sources Catalog:**
- ✅ `sources` - Crossmatched catalog
- ✅ Views: `good_references`, `final_references`

---

## Frontend Components Implementation Status

### ✅ Implemented Components

**Dashboard:**
- ✅ `DashboardPage` - Main dashboard
- ✅ `ESECandidatesPanel` - ESE alerts
- ✅ `PointingVisualization` - Sky map

**Control:**
- ✅ `ControlPage` - Job submission
- ✅ `MSTable` - MS selection table
- ✅ `CalibrationQAPanel` - Calibration QA

**Streaming:**
- ✅ `StreamingPage` - Service control

**QA:**
- ✅ `QAVisualizationPage` - QA browser
- ✅ `DirectoryBrowser` - File browser
- ✅ `FITSViewer` - FITS viewer
- ✅ `CasaTableViewer` - CASA table viewer

**Data:**
- ✅ `DataBrowserPage` - Data browser

**Sources:**
- ✅ `SourceMonitoringPage` - Source table
- ✅ `SourceDetailPage` - Source details (basic)

**Sky:**
- ✅ `SkyViewPage` - Full implementation with SkyMap
- ✅ `ImageBrowser` - Image browser with advanced filters
- ✅ `SkyMap` - Interactive sky map component
- ✅ `MosaicGalleryPage` - Mosaic gallery
- ✅ `MosaicViewPage` - Mosaic detail view

**Observing:**
- ✅ `ObservingPage` - Telescope status and pointing history

**Health:**
- ✅ `HealthPage` - System diagnostics and queue monitoring

### 📋 Planned Components (Advanced Features)

- 📋 Advanced light curve visualization component (for SourceDetailPage)
- 📋 Aladin Lite integration component (for SourceDetailPage)
- 📋 Source comparison tools
- 📋 Image comparison tools
- 📋 Historical metrics visualization components

---

## Backend Features Implementation Status

### ✅ Implemented

- ✅ FastAPI application structure
- ✅ 100+ REST API endpoints
- ✅ WebSocket support (basic)
- ✅ SQLite database access layer
- ✅ Error handling and validation
- ✅ Streaming service manager
- ✅ Job management system
- ✅ Data access functions

### 🔄 Partially Implemented

- 🔄 WebSocket broadcasting (basic exists, advanced features planned)
- 🔄 Mosaic generation (backend exists, async job handling in progress)
- 🔄 ESE candidate detection (auto-flagging exists, advanced features planned)

### 📋 Planned

- 📋 Authentication system
- 📋 Rate limiting
- 📋 Advanced caching
- 📋 Metrics export (Prometheus)
- 📋 Health check endpoints
- 📋 Telescope status integration

---

## See Also

- [Pages & Features Reference](./dashboard_pages_and_features.md) - Detailed feature documentation with status indicators
- [Future Roadmap](../concepts/dashboard_future_roadmap.md) - Planned features by phase
- [Architecture](../concepts/dashboard_architecture.md) - System architecture

