# DSA-110 Dashboard & Frontend: Consolidated Documentation Outline

**Date:** 2025-11-12  
**Purpose:** Comprehensive consolidated outline organizing all topics from 84+ dashboard/frontend documentation files

**Status:** Master outline for documentation reorganization

---

## Table of Contents

1. [Vision, Philosophy & Design Principles](#1-vision-philosophy-design-principles)
2. [System Architecture & Technology Stack](#2-system-architecture-technology-stack)
3. [User Experience & Interface Design](#3-user-experience-interface-design)
4. [Dashboard Pages & Features](#4-dashboard-pages-features)
5. [Frontend Architecture & Implementation](#5-frontend-architecture-implementation)
6. [Backend API & Integration](#6-backend-api-integration)
7. [Data Models & Database Schema](#7-data-models-database-schema)
8. [State Management & Real-Time Updates](#8-state-management-real-time-updates)
9. [Visualization & Analysis Tools](#9-visualization-analysis-tools)
10. [Streaming Service & Control](#10-streaming-service-control)
11. [Quality Assurance & QA Visualization](#11-quality-assurance-qa-visualization)
12. [Development Workflow & Setup](#12-development-workflow-setup)
13. [Testing & Quality Assurance](#13-testing-quality-assurance)
14. [Deployment & Operations](#14-deployment-operations)
15. [Troubleshooting & Debugging](#15-troubleshooting-debugging)
16. [Future Enhancements & Roadmap](#16-future-enhancements-roadmap)

---

## 1. Vision, Philosophy & Design Principles

### 1.1 Core Vision
- **Unified Command Center**: Single interface for all pipeline operations
- **Autonomous-First Design**: Dashboard monitors autonomous operations, intervenes only when needed
- **Anticipatory UX**: Anticipates user needs, eliminates unnecessary steps
- **Workflow-Focused**: Guides users seamlessly through complex workflows
- **Science-First**: Direct access to scientific data and discoveries

### 1.2 Design Philosophy
- **Jony Ive's Minimalism**: Clean, focused interfaces
- **Steve Jobs' Workflow UX**: "It just works"
- **Information Density Over Volume**: One excellent, information-rich figure beats 100 individual diagnostics
- **Ease of Use**: Radio astronomers should quickly find what they need
- **Professional Aesthetic**: Clean, modern, data-dense interfaces for working scientists

### 1.3 Core Design Principles
1. **Unified Command Center** - Single interface for all pipeline operations
2. **Autonomous-First** - Dashboard monitors autonomous operations, intervenes only when needed
3. **State-Driven UI** - Interface adapts to current context (autonomous vs manual vs analysis)
4. **Predictive Loading** - Data loads before it's requested
5. **Contextual Actions** - Only show relevant actions
6. **Workflow Guidance** - Guide users through complex tasks
7. **Zero Configuration** - Smart defaults, optional overrides
8. **Manual Override** - Full control when autonomous operations need intervention
9. **Flexible Analysis** - Powerful yet trustworthy exploratory tools for data products
10. **Deterministic Results** - All analysis operations are reproducible and traceable

### 1.4 User Personas
1. **Operations Monitor** - Needs to know: "Is the pipeline healthy?"
2. **Data Quality Scientist** - Needs to know: "Is the data good?"
3. **Science User** - Needs to know: "Did we detect any interesting variability?"

### 1.5 Design Patterns & Inspiration
- Trading dashboards (information density)
- Mission control centers (real-time monitoring)
- Astronomical observatories (scientific workflows)
- CARTA (radio astronomy UI patterns)
- Grafana (dashboard panel system)
- JupyterLab (file browser, tabbed interface)

---

## 2. System Architecture & Technology Stack

### 2.1 High-Level Architecture
- **Frontend**: React 18 + TypeScript + Vite + Material-UI v6
- **Backend**: FastAPI (Python) with 100+ REST endpoints
- **State Management**: TanStack React Query + WebSocket
- **Databases**: SQLite3 (4 databases: queue, products, calibration, catalogs)
- **Real-Time**: WebSocket + HTTP polling fallback
- **Infrastructure**: Docker, Systemd, CASA6 environment

### 2.2 Technology Stack Details

#### Frontend Technologies
- **React 18.3** - UI framework with concurrent features
- **TypeScript 5.x** - Type safety throughout
- **Vite 7** - Build tool and dev server (HMR)
- **Material-UI v6** - Component library (MUI)
- **TanStack React Query v5** - Server state management
- **React Router v6** - Client-side routing
- **Plotly.js** - Scientific plotting (timeseries, pointing maps)
- **AG Grid Community** - High-performance data tables
- **Axios** - HTTP client with interceptors
- **JS9** - FITS image viewer (astronomy standard)
- **MUI X Date Pickers** - Date/time selection

#### Backend Technologies
- **FastAPI** - Modern Python web framework
- **Pydantic v2** - Data validation and serialization
- **SQLite3** - Embedded database (4 databases)
- **psutil** - System metrics collection
- **WebSocket** - Real-time bidirectional communication
- **Server-Sent Events (SSE)** - Fallback for real-time updates

#### Infrastructure
- **Docker** - Containerization for streaming service
- **Systemd** - Service management (optional)
- **CASA6** - Radio astronomy data processing (Python environment)

### 2.3 System Components
- **Unified Command Center** (Dashboard Shell)
- **Streaming Pipeline Monitor**
- **State Machine** (Dashboard state management)
- **Pre-fetch Engine** (Anticipatory data loading)
- **Contextual Intelligence** (Action suggestions)
- **Workflow State Machine** (Complex task guidance)
- **Autonomous Operations Tracker**
- **Manual Override Controller**
- **Analysis Workspace** (Exploratory tools)

### 2.4 Data Flow Architecture
- **Ingest**: UVH5 files → Queue database
- **Conversion**: Queue → Measurement Sets
- **Calibration**: MS → Calibration tables
- **Imaging**: Calibrated MS → Images
- **Photometry**: Images → Source measurements
- **ESE Detection**: Photometry → Variability alerts
- **Mosaicking**: Images → Combined mosaics

---

## 3. User Experience & Interface Design

### 3.1 Dashboard States & Modes
- **Idle**: Normal monitoring, autonomous operations running smoothly
- **Autonomous**: Streaming pipeline operating autonomously (monitoring mode)
- **Discovery**: ESE candidate detected
- **Investigation**: User investigating something
- **Debugging**: System issue detected
- **Manual Control**: User has taken manual control (override mode)
- **Analysis**: Analysis/exploration workspace for data products

### 3.2 Navigation Structure
- **Dashboard** - Executive summary (pipeline status, latest images, alerts)
- **Sky** - Image gallery, mosaics, sky coverage visualization
- **Sources** - Source monitoring, flux timeseries, variability detection
- **Observing** - Telescope status, pointing history, calibrator tracking
- **Health** - System metrics, queue monitoring, diagnostic plots
- **Control** - Manual job execution (convert, calibrate, apply, image, workflow)
- **Streaming** - Streaming service control and monitoring
- **QA** - Quality assurance visualization and tools
- **Data** - Data browser and lineage visualization

### 3.3 Visual Design Specifications
- **Color Palette**: Professional dark mode (GitHub-inspired)
- **Typography**: Inter/Roboto for headers, Fira Code/JetBrains Mono for data
- **Spacing**: 8px base unit (padding, margins in multiples of 8)
- **Layout**: Grid-based, responsive breakpoints
- **Components**: Material-UI components with custom styling

### 3.4 UI Patterns & Techniques
- **Small Multiples**: Show many sources/images in compact, comparable grids
- **Sparklines**: Inline flux trends without taking full-figure space
- **Color Coding**: Quick visual status (green=healthy, yellow=warning, red=critical)
- **Drill-Down**: Summary → Detail → Deep Dive on demand
- **Live Updates**: WebSocket or polling for real-time status changes
- **Contextual Actions**: Only show relevant actions based on state
- **Workflow Guidance**: Step-by-step guidance for complex tasks

### 3.5 Responsive Design
- **Desktop**: 1920×1080 (primary target)
- **Laptop**: 1440×900
- **Tablet**: 768×1024
- **Mobile**: 390×844 (fallback, limited functionality)

### 3.6 Accessibility
- **WCAG 2.1 AA** compliance minimum
- Keyboard navigation for all interactive elements
- Screen reader compatibility (ARIA labels)
- Color-blind friendly palettes
- Sufficient contrast ratios (4.5:1 for text)
- Zoom support up to 200% without breaking layout

---

## 4. Dashboard Pages & Features

### 4.1 Dashboard Page (`/dashboard`)
**Purpose**: At-a-glance pipeline health and recent activity

**Features**:
- **Pipeline Status Panel**
  - Queue statistics (total, pending, in progress, completed, failed, collecting)
  - Calibration sets (active groups, targets per set, timestamps)
  - Recent observations table (last 20 groups, states, subband counts)
- **System Health Panel**
  - Resource metrics (CPU, memory, disk, load averages)
  - Real-time updates (polls every 10 seconds)
- **ESE Candidates Panel**
  - Real-time variability alerts (5σ threshold)
  - Source ID (NVSS naming), maximum σ deviation
  - Status indicators (active, resolved, false_positive)
- **Pointing Visualization**
  - Interactive sky map showing telescope pointing
  - Historical pointing trail
  - Current position display

### 4.2 Sky View Page (`/sky`)
**Purpose**: Visual exploration of sky coverage and images

**Features**:
- **Interactive Sky Map**
  - Observed fields (color-coded by observation time)
  - Source density heatmap
  - Calibrator positions
  - Current/upcoming telescope pointing
- **Image Gallery**
  - Grid of thumbnails (4-6 per row)
  - Filters: date range, declination, quality, search
  - Click → full-res image + metadata + NVSS overlay
- **Image Detail View**
  - Large image display with zoom/pan
  - Overlays: NVSS sources, measured sources, noise contours
  - Metadata panel (noise, beam, frequency, integration time)
  - Actions: Download FITS/PNG, View Source List, Reprocess
- **Mosaic Builder**
  - Time-range query (start/end UTC or MJD)
  - Declination range filter
  - Preview coverage map before generation
  - Generate stitched mosaic (async job)
  - Download FITS/PNG when complete

### 4.3 Sources Page (`/sources`)
**Purpose**: Monitor source flux variability and identify ESE candidates

**Features**:
- **Source Search & Filters**
  - Quick search (source name or RA/Dec)
  - Filters: variability, Dec range, flux, NVSS match quality, observation count
- **Source Table** (sortable, paginated)
  - Source ID (NVSS catalog), RA/Dec
  - NVSS flux, latest flux, variability metrics (σ, χ²)
  - Trend sparkline (last 20 observations)
- **Source Detail View**
  - Large flux vs. time plot (Plotly.js)
  - Statistics panel (observations, mean flux, NVSS flux, variability)
  - Catalog info (RA/Dec, NVSS/VLASS/FIRST, confusion flag)
  - Recent measurements table
  - Actions: Export data, Flag as candidate, View images, Literature search
- **ESE Candidate Dashboard**
  - Automatically flagged sources with strong variability
  - "Extreme" defined as: >5σ deviation OR flux change >50% on <1 day timescale
  - Sort by significance, recency, or deviation magnitude
  - Quick-approve or dismiss interface

### 4.4 Observing Page (`/observing`)
**Purpose**: Real-time telescope status and observing plan

**Features**:
- **Current Status Panel**
  - Telescope pointing (RA, Dec, LST, Alt, Az)
  - Next transit information
  - Observing mode and cadence
- **Antenna Status**
  - Online/flagged/offline counts
  - Antenna map with color-coded status markers
- **Pointing History Visualization**
  - Sky map showing pointing centers over last 24h/7d/30d
  - Color-coded by time
  - Declination strip coverage overlay
  - Interactive: click pointing → show observation details
- **Calibrator Tracking**
  - Active calibrators (last 6h)
  - Detections, average flux, expected flux, deviation
  - Plot: calibrator flux vs. elevation over time
- **Calibrator Plan**
  - Upcoming calibrator transits (next 6h)
  - Expected elevation, parallactic angle coverage
  - Visibility windows for standard calibrators

### 4.5 Health Page (`/health`)
**Purpose**: Deep diagnostics for pipeline and data quality monitoring

**Features**:
- **System Monitoring**
  - Resource usage plots (CPU, Memory, Disk I/O, Load) - last 6h
  - Thresholds marked, color-coded zones
- **Processing Queue Status**
  - Total groups, pending, in progress, failed, completed
  - Recent groups detailed table
  - State distribution visualization
- **Calibration Registry**
  - Active calibration sets
  - Set name, tables, valid MJD range, last used, uses, status
- **Data Quality Metrics**
  - Image quality trends (last 7 days)
  - Image noise vs. time (expected thermal noise marked)
  - Source detection rate vs. time
  - Calibration solution success rate
- **QA Diagnostic Gallery**
  - Recent QA plots (amplitude, phase, UVW coverage)
  - Thumbnail grid, click to expand
  - Filter by: All, Calibrators only, Failed groups
- **Performance Metrics**
  - Conversion time (UVH5 → MS): mean, p50, p95
  - Calibration time (K+BP+G): mean, p50, p95
  - Imaging time (tclean): mean, p50, p95
  - End-to-end latency (data arrival → final image)
  - Throughput: images/hour, sources measured/hour

### 4.6 Control Page (`/control`)
**Purpose**: Manual job execution for selected Measurement Sets

**Features**:
- **Job Submission Forms**
  - Convert job (UVH5 → MS)
  - Calibrate job (K, Bandpass, Gain)
  - Apply job (apply calibration tables)
  - Image job (tclean imaging)
  - Workflow job (end-to-end pipeline)
- **MS Browser**
  - List available Measurement Sets
  - Filter by path, date, state
  - Select MS for job submission
- **Job Management**
  - List recent jobs (with status filter)
  - Job details (parameters, logs, artifacts, timestamps)
  - Live log streaming via Server-Sent Events (SSE)
  - Job status tracking (pending, running, completed, failed)
- **Calibration QA Display**
  - Show calibration quality for selected MS
  - Metrics: K-table SNR, bandpass RMS, gain solutions
  - Bandpass plots

### 4.7 Streaming Page (`/streaming`)
**Purpose**: Control and monitor the streaming converter service

**Features**:
- **Service Control**
  - Start/stop/restart streaming service
  - Service status (running, stopped, error)
  - Configuration management
- **Real-Time Status**
  - Current operations (conversion, calibration, imaging, mosaicking, QA)
  - Operation progress (0-100%)
  - Resource usage (CPU, memory)
- **Queue Statistics**
  - Queue depth, processing rate
  - Recent groups processed
- **Configuration**
  - Input directory, output directory
  - Max workers, expected subbands
  - Update configuration (with validation)

### 4.8 QA Visualization Page (`/qa`)
**Purpose**: Quality assurance data visualization and exploration

**Features**:
- **Directory Browser**
  - Browse QA artifact directories
  - File tree navigation
  - Filter by file type (FITS, images, logs, tables)
- **FITS Viewer**
  - JS9 integration for FITS image viewing
  - Scale/colormap controls
  - Zoom/pan, coordinate display
- **CASA Table Viewer**
  - Browse Measurement Set tables
  - Column selection, filtering, sorting
  - Subtable navigation
- **QA Notebook Generator**
  - Generate Jupyter notebooks for QA analysis
  - Automated report generation
  - Customizable templates

### 4.9 Data Browser Page (`/data`)
**Purpose**: Browse data products and visualize data lineage

**Features**:
- **Data Product Browser**
  - Browse images, mosaics, catalogs
  - Filter by date, type, quality
  - Search functionality
- **Data Lineage Graph**
  - Visualize data flow from raw data to products
  - Show dependencies and relationships
  - Interactive exploration

---

## 5. Frontend Architecture & Implementation

### 5.1 Project Structure
```
frontend/
├── src/
│   ├── api/                    # API client layer
│   │   ├── client.ts          # Axios instance with interceptors
│   │   ├── queries.ts         # React Query hooks (100+ hooks)
│   │   ├── types.ts           # TypeScript interfaces
│   │   ├── websocket.ts       # WebSocket client
│   │   ├── circuitBreaker.ts  # Circuit breaker pattern
│   │   └── retry.ts           # Retry logic utilities
│   ├── components/             # Reusable UI components
│   │   ├── Health/            # Health monitoring components
│   │   ├── Observing/         # Observation-related
│   │   ├── QA/                # QA visualization
│   │   ├── Sky/               # Sky/FITS viewing
│   │   ├── Sources/           # Source-related
│   │   └── shared/            # Shared components
│   ├── pages/                  # Page-level components
│   │   ├── DashboardPage.tsx
│   │   ├── ControlPage.tsx
│   │   ├── StreamingPage.tsx
│   │   ├── MosaicGalleryPage.tsx
│   │   ├── SourceMonitoringPage.tsx
│   │   ├── SkyViewPage.tsx
│   │   ├── QAVisualizationPage.tsx
│   │   └── DataBrowserPage.tsx
│   ├── stores/                 # State management
│   │   ├── dashboardState.ts  # Dashboard state types
│   │   └── dashboardStore.ts  # Zustand store
│   ├── contexts/               # React contexts
│   │   └── NotificationContext.tsx
│   ├── hooks/                  # Custom React hooks
│   ├── utils/                  # Utility functions
│   └── theme/                  # Material-UI theme
│       └── darkTheme.ts
```

### 5.2 Component Architecture
- **Page Components**: Top-level route components
- **Feature Components**: Domain-specific components (Health, QA, Sky, Sources)
- **Shared Components**: Reusable UI components (tables, charts, forms)
- **Widget Components**: Modular dashboard widgets (can be docked/undocked)

### 5.3 State Management Patterns
- **Server State**: TanStack React Query (API data, caching, refetching)
- **Client State**: React useState/useReducer (UI state, form state)
- **Global State**: Zustand store (dashboard state, user preferences)
- **Real-Time State**: WebSocket subscriptions (live updates)

### 5.4 Data Fetching Patterns
- **React Query Hooks**: Custom hooks for each API endpoint
- **Query Keys**: Hierarchical query keys for cache invalidation
- **Optimistic Updates**: Immediate UI updates before server confirmation
- **Prefetching**: Anticipatory data loading based on user context
- **Polling**: Automatic refetching for critical data (10s intervals)
- **WebSocket**: Real-time updates for live data

### 5.5 Error Handling
- **Circuit Breaker Pattern**: Prevent cascading failures
- **Retry Logic**: Exponential backoff for failed requests
- **Error Boundaries**: React error boundaries for component errors
- **User-Friendly Messages**: Clear error messages for users
- **Error Classification**: Network errors, server errors, validation errors

### 5.6 Performance Optimization
- **Code Splitting**: Lazy loading for routes
- **Virtual Scrolling**: AG Grid for large tables (10k+ rows)
- **Memoization**: React.memo, useMemo, useCallback
- **Image Optimization**: Thumbnails, lazy loading
- **Bundle Optimization**: Tree shaking, minification

### 5.7 UI Component Patterns
- **Material-UI Components**: Leverage MUI components instead of custom
- **Form Handling**: React Hook Form + Zod validation
- **Table Components**: AG Grid for high-performance tables
- **Chart Components**: Plotly.js for scientific plots
- **Dialog/Modal Components**: MUI Dialog for modals
- **Loading States**: MUI Skeleton/CircularProgress
- **Toast Notifications**: notistack for notifications

---

## 6. Backend API & Integration

### 6.1 API Architecture
- **FastAPI Framework**: Modern Python web framework
- **REST Endpoints**: 100+ REST API endpoints
- **WebSocket Support**: Real-time bidirectional communication
- **Server-Sent Events**: Fallback for real-time updates
- **Pydantic Models**: Request/response validation

### 6.2 API Endpoint Categories

#### Pipeline Status & Monitoring
- `GET /api/status` - Queue stats, recent groups, cal sets
- `GET /api/metrics/system` - Current system metrics
- `GET /api/metrics/system/history` - Historical system metrics
- `GET /api/groups/{group_id}` - Detailed group information

#### Streaming Service Control
- `GET /api/streaming/status` - Streaming service status
- `GET /api/streaming/health` - Service health check
- `GET /api/streaming/config` - Current configuration
- `GET /api/streaming/metrics` - Service metrics
- `POST /api/streaming/start` - Start streaming service
- `POST /api/streaming/stop` - Stop streaming service
- `POST /api/streaming/restart` - Restart streaming service
- `PUT /api/streaming/config` - Update configuration

#### Job Management
- `GET /api/jobs` - List recent jobs (with status filter)
- `GET /api/jobs/{job_id}` - Get job details
- `GET /api/jobs/{job_id}/logs` - Stream job logs via SSE
- `POST /api/jobs/calibrate` - Create calibration job
- `POST /api/jobs/apply` - Create apply job
- `POST /api/jobs/image` - Create imaging job
- `POST /api/jobs/workflow` - Create workflow job

#### Mosaic Management
- `GET /api/mosaics/query` - Query mosaics by time range
- `GET /api/mosaics/{mosaic_id}` - Get mosaic details
- `POST /api/mosaics/create` - Create new mosaic
- `GET /api/mosaics/{mosaic_id}/download` - Download mosaic

#### Source Monitoring & ESE Detection
- `GET /api/sources/search` - Search sources
- `GET /api/sources/{source_id}` - Get source details
- `GET /api/sources/{source_id}/light-curve` - Get flux timeseries
- `GET /api/ese/candidates` - Get ESE candidates

#### QA Visualization
- `GET /api/visualization/browse` - Browse QA directory
- `GET /api/visualization/fits/view` - View FITS file
- `GET /api/visualization/casa/table` - Browse CASA table
- `POST /api/visualization/qa/run` - Run QA analysis
- `GET /api/visualization/qa/notebook` - Generate QA notebook

#### Data Products
- `GET /api/products` - Recent image products
- `GET /api/products/{product_id}` - Get product details
- `GET /api/ms` - List available Measurement Sets
- `GET /api/ms_index` - MS processing stage tracking

#### Calibration
- `GET /api/calibrator_matches` - Calibrator detection history
- `GET /api/calibration/qa` - Calibration QA for MS

#### Pointing & Observing
- `GET /api/pointing_history` - Telescope pointing over time
- `GET /api/pointing/current` - Current telescope pointing

### 6.3 API Client Implementation
- **Axios Instance**: Configured with base URL, timeout, interceptors
- **Request Interceptors**: Add authentication, logging
- **Response Interceptors**: Error handling, response transformation
- **Circuit Breaker**: Prevent cascading failures
- **Retry Logic**: Exponential backoff for failed requests

### 6.4 WebSocket Integration
- **Connection Management**: Auto-reconnect, connection state tracking
- **Message Types**: Status updates, operation updates, alerts
- **Fallback Mechanism**: HTTP polling when WebSocket unavailable
- **Message Format**: JSON with type and payload

### 6.5 API Error Handling
- **Error Classification**: Network errors, server errors, validation errors
- **User-Friendly Messages**: Clear error messages for users
- **Retry Strategy**: Exponential backoff for transient errors
- **Circuit Breaker**: Prevent cascading failures

---

## 7. Data Models & Database Schema

### 7.1 Database Architecture
- **SQLite3 Databases**: 4 separate databases for different concerns
- **Database Locations**: `/state/` directory
- **Connection Management**: Connection pooling, proper cleanup

### 7.2 Database Schemas

#### Ingest Database (`ingest.sqlite3`)
- **Queue Table**: Observation groups, states, timestamps
- **Subband Files Table**: Individual UVH5 files, group associations
- **Performance Metrics Table**: Processing times, resource usage

**Pipeline States**: `collecting` → `pending` → `in_progress` → `processing_fresh` → `completed`

#### Products Database (`products.sqlite3`)
- **MS Index Table**: Measurement Sets, processing stages, paths
- **Images Table**: Image products, metadata, paths
- **Photometry Table**: Per-image, per-source measurements
- **Variability Table**: Variability metrics, ESE candidates
- **ESE Candidates Table**: Extreme scattering event candidates
- **Mosaics Table**: Mosaic products, time ranges, coverage

**MS Processing Stages**: `converted` → `calibrated` → `imaged` → `photometry_complete`

#### Calibration Registry (`cal_registry.sqlite3`)
- **Calibration Sets Table**: Calibration groups, validity windows
- **Calibration Tables Table**: K, Bandpass, Gain tables, paths
- **Calibrator Matches Table**: Calibrator detection history

#### Catalogs Database (`catalogs/master_sources.sqlite3`)
- **Master Sources Table**: NVSS/VLASS/FIRST crossmatch catalog
- **Source Associations Table**: Associations between surveys

### 7.3 Data Models (Pydantic/TypeScript)

#### Pipeline Status Models
- `PipelineStatus`: Queue stats, recent groups, calibration sets
- `QueueStats`: Total, pending, in_progress, completed, failed, collecting
- `RecentGroup`: Group ID, state, subbands, calibrator, timestamp
- `CalibrationSet`: Set name, tables, valid MJD range, last used

#### System Metrics Models
- `SystemMetrics`: CPU, memory, disk, load averages
- `SystemMetricsHistory`: Time-series metrics data

#### Job Models
- `Job`: Job ID, type, status, MS path, parameters, logs, artifacts, timestamps
- `JobParams`: Job configuration (field, refant, gaintables, gridder, etc.)
- `JobCreateRequest`: Request payload for job creation

#### Source Models
- `Source`: Source ID, RA/Dec, NVSS flux, latest flux, variability metrics
- `ESECandidate`: Source ID, max σ deviation, status, detection timestamp
- `FluxTimeseries`: Time-series flux measurements for a source

#### Mosaic Models
- `Mosaic`: Mosaic ID, time range, coverage, image count, status
- `MosaicQuery`: Query parameters (start/end MJD, Dec range)

#### QA Models
- `QADirectoryEntry`: File/directory entry in QA directory
- `FITSViewOptions`: Scale, colormap, dual window options
- `CasaTableData`: CASA table data with columns and rows

### 7.4 Data Flow & Relationships
- **Raw Data**: UVH5 files → Queue database
- **Measurement Sets**: Queue → MS Index → Products database
- **Calibration**: MS → Calibration Registry → Calibration tables
- **Images**: Calibrated MS → Images table → Products database
- **Photometry**: Images → Photometry table → Variability analysis
- **ESE Detection**: Variability → ESE Candidates table
- **Mosaics**: Images → Mosaics table

---

## 8. State Management & Real-Time Updates

### 8.1 Dashboard State Management
- **State Types**: idle, autonomous, discovery, investigation, debugging, manual-control, analysis
- **State Transitions**: Automatic transitions based on events
- **State Store**: Zustand store for global dashboard state
- **State Persistence**: LocalStorage for user preferences

### 8.2 Real-Time Update Mechanisms
- **WebSocket**: Primary mechanism for real-time updates
- **HTTP Polling**: Fallback when WebSocket unavailable
- **Server-Sent Events**: For job log streaming
- **Refresh Intervals**: 10 seconds for critical monitoring data

### 8.3 Pre-fetching & Anticipation Engine
- **Pre-fetch Strategy**: Load data before user requests it
- **Preload Targets**: Calculate likely next data needs
- **Context-Based Prefetching**: Pre-fetch based on current state
- **Workflow-Based Prefetching**: Pre-fetch based on workflow steps

### 8.4 Contextual Intelligence
- **Action Suggestion Engine**: Suggest relevant actions based on context
- **Workflow Guidance**: Guide users through complex tasks
- **State-Aware UI**: UI adapts to current dashboard state
- **User Intent Detection**: Detect user intent from actions

### 8.5 Caching Strategy
- **React Query Cache**: Server state caching
- **Cache Invalidation**: Invalidate on mutations
- **Stale Time**: Configure stale time per query type
- **Cache Persistence**: Optional cache persistence to localStorage

---

## 9. Visualization & Analysis Tools

### 9.1 Scientific Plotting
- **Plotly.js**: Primary plotting library
- **Flux Timeseries**: Interactive flux vs. time plots
- **Pointing Maps**: Sky maps with telescope pointing
- **System Metrics**: Time-series system resource plots
- **Calibration Plots**: Bandpass, gain solutions

### 9.2 FITS Image Viewing
- **JS9 Integration**: FITS image viewer (astronomy standard)
- **Image Controls**: Scale, colormap, zoom, pan
- **Coordinate Display**: RA/Dec, pixel coordinates
- **Catalog Overlays**: NVSS/VLASS source overlays
- **Measurement Tools**: Flux measurement, region selection

### 9.3 Sky Visualization
- **Sky Maps**: Interactive RA/Dec coordinate maps
- **Pointing Visualization**: Telescope pointing trail
- **Coverage Visualization**: Sky coverage heatmaps
- **Source Density Maps**: Source density visualization

### 9.4 Data Tables
- **AG Grid**: High-performance data tables
- **Virtual Scrolling**: Handle 10k+ rows efficiently
- **Sorting & Filtering**: Client-side and server-side
- **Export**: CSV, Excel export functionality

### 9.5 Analysis Workspace (Future)
- **Golden Layout**: Flexible, dockable panel system
- **Widget System**: Modular analysis widgets
- **Catalog Comparison Tool**: Compare sources with catalogs
- **Image Analysis Tool**: Image quality analysis
- **Source Investigation Tool**: Deep source analysis
- **Reproducibility System**: Generate reproduction scripts

---

## 10. Streaming Service & Control

### 10.1 Streaming Service Architecture
- **Service Manager**: Python service manager for streaming converter
- **Docker Integration**: Optional Docker containerization
- **Process Management**: PID file management, process monitoring
- **Configuration Management**: JSON configuration file

### 10.2 Service Lifecycle
- **Start**: Start streaming service with configuration
- **Stop**: Graceful shutdown of streaming service
- **Restart**: Restart service with updated configuration
- **Status Monitoring**: Real-time status and health checks

### 10.3 Autonomous Operation Tracking
- **Operation Types**: Conversion, calibration, imaging, mosaicking, QA
- **Operation Status**: Pending, in-progress, completed, failed
- **Progress Tracking**: 0-100% progress for operations
- **Resource Usage**: CPU, memory usage per operation

### 10.4 Manual Override & Control
- **Override Triggers**: User-initiated, autonomous failure, intervention required
- **Control Scope**: Streaming, calibration, imaging, mosaicking
- **Override Workflow**: Confirm → Select scope → Stop autonomous → Manual control
- **Return to Autonomous**: Validate → Restart autonomous → Resume monitoring

---

## 11. Quality Assurance & QA Visualization

### 11.1 QA Framework Architecture
- **In-House Framework**: RadioPadre-like functionality without external dependencies
- **Components**: FITS file handling, CASA table browsing, directory browsing, HTML rendering, notebook generation
- **JS9 Integration**: Browser-based FITS viewing
- **Jupyter Notebooks**: Automated QA report generation

### 11.2 QA Visualization Features
- **Directory Browser**: Browse QA artifact directories
- **FITS Viewer**: Interactive FITS image viewing with JS9
- **CASA Table Viewer**: Browse Measurement Set tables
- **QA Notebook Generator**: Generate Jupyter notebooks for QA analysis

### 11.3 QA Artifact Organization
- **Directory Structure**: Per-group subdirectories in `/state/qa/`
- **File Types**: FITS files, images, plots, logs, tables
- **Naming Conventions**: Consistent naming for easy discovery
- **Metadata**: File metadata for filtering and search

### 11.4 QA Integration Points
- **Dashboard Integration**: QA page in dashboard navigation
- **API Endpoints**: REST API for QA visualization
- **Backend Integration**: Python QA visualization framework
- **Frontend Components**: React components for QA tools

---

## 12. Development Workflow & Setup

### 12.1 Development Environment Setup
- **Prerequisites**: Node.js, npm, Python, CASA6 environment
- **Frontend Setup**: `npm install`, `npm run dev`
- **Backend Setup**: Python virtual environment, dependencies
- **Database Setup**: SQLite databases in `/state/` directory

### 12.2 Development Server
- **Frontend Dev Server**: Vite dev server (port 5173)
- **Backend API Server**: FastAPI/Uvicorn (port 8000)
- **Hot Module Replacement**: Fast refresh for React components
- **Proxy Configuration**: Proxy API requests to backend

### 12.3 Project Structure & Organization
- **Frontend Structure**: Component-based architecture
- **Backend Structure**: API routes, data access, models
- **Documentation Structure**: Organized by type (how-to, concepts, reference)
- **Testing Structure**: Unit tests, integration tests, E2E tests

### 12.4 Code Quality & Standards
- **TypeScript**: Strict type checking
- **ESLint**: Code linting and style enforcement
- **Prettier**: Code formatting
- **Git Hooks**: Pre-commit hooks for quality checks

### 12.5 Build & Deployment
- **Frontend Build**: `npm run build` (Vite production build)
- **Backend Deployment**: FastAPI/Uvicorn production server
- **Docker**: Optional Docker containerization
- **Static Assets**: Serve frontend as static files

---

## 13. Testing & Quality Assurance

### 13.1 Testing Strategy
- **Unit Tests**: Component tests, utility function tests
- **Integration Tests**: API integration tests, database tests
- **E2E Tests**: End-to-end user workflow tests
- **Visual Regression Tests**: Screenshot comparison tests

### 13.2 Testing Tools
- **Vitest**: Unit testing framework
- **React Testing Library**: Component testing
- **Playwright**: E2E testing
- **Mock Service Worker**: API mocking

### 13.3 Test Coverage
- **Component Coverage**: Test all major components
- **API Coverage**: Test all API endpoints
- **Workflow Coverage**: Test user workflows
- **Error Handling Coverage**: Test error scenarios

### 13.4 QA Testing
- **QA Visualization Testing**: Test QA tools and features
- **Dashboard Endpoint Testing**: Test dashboard API endpoints
- **Real Data Testing**: Test with real observational data
- **Performance Testing**: Test with large datasets

---

## 14. Deployment & Operations

### 14.1 Deployment Architecture
- **Frontend**: Static files served via Nginx or FastAPI StaticFiles
- **Backend**: FastAPI/Uvicorn production server
- **Database**: SQLite databases in `/state/` directory
- **Streaming Service**: Docker container or systemd service

### 14.2 Production Configuration
- **Environment Variables**: API URLs, feature flags, thresholds
- **Port Management**: Frontend (5173 dev, 80/443 prod), Backend (8000)
- **SSL/TLS**: HTTPS configuration for production
- **CORS**: Cross-origin resource sharing configuration

### 14.3 Monitoring & Logging
- **System Metrics**: CPU, memory, disk, load monitoring
- **Application Logs**: Structured logging for debugging
- **Error Tracking**: Error logging and alerting
- **Performance Monitoring**: Response times, throughput

### 14.4 Service Management
- **Systemd**: Optional systemd service management
- **Docker Compose**: Docker Compose for local development
- **Process Management**: PID file management, process monitoring
- **Health Checks**: Health check endpoints for monitoring

### 14.5 Backup & Recovery
- **Database Backups**: Regular SQLite database backups
- **Configuration Backups**: Configuration file backups
- **Disaster Recovery**: Recovery procedures and documentation

---

## 15. Troubleshooting & Debugging

### 15.1 Common Issues
- **Frontend Restart Needed**: When to restart frontend dev server
- **API Connection Issues**: Network connectivity problems
- **Database Lock Issues**: SQLite database locking
- **WebSocket Connection Issues**: WebSocket connection problems

### 15.2 Debugging Tools
- **Browser DevTools**: React DevTools, Network tab, Console
- **Backend Logging**: Structured logging for debugging
- **API Testing**: Postman/curl for API testing
- **Database Inspection**: SQLite browser for database inspection

### 15.3 Troubleshooting Guides
- **Frontend Issues**: Common frontend problems and solutions
- **Backend Issues**: Common backend problems and solutions
- **Database Issues**: Database problems and solutions
- **Streaming Service Issues**: Streaming service problems and solutions

### 15.4 Performance Debugging
- **Performance Profiling**: React Profiler, Chrome DevTools
- **Network Analysis**: Network request analysis
- **Database Query Analysis**: Slow query identification
- **Memory Leak Detection**: Memory leak identification and fixing

---

## 16. Future Enhancements & Roadmap

### 16.1 Planned Features
- **Analysis Workspace**: Flexible analysis workspace with Golden Layout
- **Advanced Filtering**: Multi-parameter source filtering
- **VO Cone Search**: IVOA-compliant cone search endpoint
- **User Authentication**: Multi-user support with authentication
- **Collaborative Features**: Shared candidate lists, comments

### 16.2 Enhancement Areas
- **Performance**: Further optimization for large datasets
- **Accessibility**: Enhanced accessibility features
- **Mobile Support**: Better mobile/tablet support
- **Offline Support**: Offline functionality for critical features
- **Export Features**: Enhanced export capabilities (PDF, Excel)

### 16.3 Integration Opportunities
- **External Catalogs**: SIMBAD, NED integration
- **Alert Systems**: Slack, email notification integration
- **Data Archives**: Integration with data archives
- **Analysis Tools**: Integration with external analysis tools

### 16.4 Technical Debt
- **Code Refactoring**: Component refactoring opportunities
- **Documentation**: Documentation improvements
- **Test Coverage**: Increased test coverage
- **Performance**: Performance optimization opportunities

---

## Appendix: Key Documents Reference

### Essential Reading
1. **Conceptual Design**: `docs/analysis/ANTICIPATORY_DASHBOARD_IMPLEMENTATION.md`
2. **Strategic Design**: `docs/concepts/frontend_design.md`
3. **Technical Overview**: `docs/analysis/DASHBOARD_OVERVIEW_DETAILED.md`
4. **API Reference**: `docs/reference/dashboard_api.md`
5. **Visual Design**: `docs/concepts/dashboard_mockups.md`

### Implementation Guides
- **Development Setup**: `docs/how-to/dashboard-development.md`
- **Quick Start**: `docs/how-to/dashboard-quickstart.md`
- **UI Recommendations**: `docs/dashboard_ui_recommendations.md`
- **Template Recommendations**: `docs/analysis/DASHBOARD_TEMPLATE_RECOMMENDATIONS.md`

### Feature-Specific Documentation
- **SkyView**: `docs/SKYVIEW_IMPLEMENTATION_PLAN.md`
- **QA Visualization**: `docs/QA_VISUALIZATION_DESIGN.md`
- **Streaming Control**: `docs/concepts/streaming-architecture.md`
- **Control Panel**: `docs/concepts/control-panel.md`

---

**Last Updated:** 2025-11-12  
**Status:** Master Outline - Ready for Documentation Reorganization

