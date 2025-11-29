# DSA-110 Dashboard: System Architecture & Technology Stack

**Date:** 2025-11-12  
**Status:** Consolidated architecture documentation  
**Audience:** Frontend developers, backend developers, system architects

---

## Table of Contents

1. [High-Level Architecture](#high-level-architecture)
2. [Technology Stack](#technology-stack)
3. [System Components](#system-components)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Deployment Architecture](#deployment-architecture)

---

## High-Level Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser (React Frontend)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  React 18 + TypeScript + Material-UI v6                  │   │
│  │  ├── Pages (8 routes)                                    │   │
│  │  ├── Components (50+ reusable)                          │   │
│  │  ├── API Client (Axios + React Query)                    │   │
│  │  └── State Management (React Query + WebSocket)         │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP/REST + WebSocket
                                 │ Port 5173 (dev) / 8000 (prod)
┌───────────────────────────────▼─────────────────────────────────┐
│                    FastAPI Backend (Python)                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  API Routes (100+ endpoints)                             │   │
│  │  ├── Pipeline Status & Monitoring                       │   │
│  │  ├── Streaming Service Control                          │   │
│  │  ├── Job Management (convert/calibrate/image/workflow)  │   │
│  │  ├── Mosaic Management                                  │   │
│  │  ├── Source Monitoring & ESE Detection                 │   │
│  │  ├── QA Visualization                                  │   │
│  │  └── Data Browser                                       │   │
│  │                                                          │   │
│  │  Data Access Layer                                      │   │
│  │  ├── SQLite queries (queue, products, calibration)      │   │
│  │  ├── File system operations                            │   │
│  │  └── Streaming service manager                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
┌───────▼──────────┐  ┌──────────▼──────────┐  ┌─────────▼─────────┐
│  SQLite DBs      │  │  Streaming Service  │  │  Pipeline Jobs    │
│  - ingest.sqlite3│  │  Manager            │  │  - Conversion     │
│  - products.sqlite│  │  - Docker/Process   │  │  - Calibration    │
│  - cal_registry  │  │  - Config JSON      │  │  - Imaging        │
│  - catalogs      │  └────────────────────┘  │  - Mosaicking     │
└──────────────────┘                          └───────────────────┘
```

### Architecture Principles

1. **Separation of Concerns** - Clear boundaries between frontend, backend, and
   data layers
2. **RESTful API** - Standard REST endpoints for data access
3. **Real-Time Updates** - WebSocket for live updates with HTTP polling fallback
4. **Stateless Backend** - Backend is stateless; state stored in databases
5. **Client-Side Routing** - Single-page application with client-side routing
6. **Progressive Enhancement** - Works with JavaScript disabled (limited
   functionality)

---

## Technology Stack

### Frontend Technologies

#### Core Framework

- **React 18.3** - UI framework with concurrent features
  - Concurrent rendering for better performance
  - Suspense for code splitting
  - Server components support (future)
- **TypeScript 5.x** - Type safety throughout
  - Strict type checking
  - Type inference
  - Interface definitions for all API responses

#### Build & Development

- **Vite 7** - Build tool and dev server
  - Fast HMR (Hot Module Replacement)
  - Optimized production builds
  - Plugin ecosystem
- **ESLint** - Code linting and style enforcement
- **Prettier** - Code formatting

#### UI Framework

- **Material-UI v6 (MUI)** - Component library
  - Comprehensive component set
  - Dark theme support
  - Accessibility built-in
  - Customizable theming
- **MUI X Date Pickers** - Date/time selection components

#### State Management

- **TanStack React Query v5** - Server state management
  - Automatic caching
  - Background refetching
  - Optimistic updates
  - Query invalidation
- **React Router v6** - Client-side routing
  - Nested routes
  - Route guards
  - Code splitting

#### Data Visualization

- **Plotly.js** - Scientific plotting
  - Interactive charts
  - Time-series plots
  - 3D visualization support
- **D3.js** - Custom visualizations
  - Sky maps
  - Custom charts
  - Data transformations
- **AG Grid Community** - High-performance data tables
  - Virtual scrolling
  - Sorting and filtering
  - Export capabilities

#### HTTP & Real-Time

- **Axios** - HTTP client
  - Request/response interceptors
  - Automatic JSON parsing
  - Error handling
- **WebSocket API** - Real-time bidirectional communication
  - Auto-reconnect
  - Message queuing
  - Fallback to polling

#### Astronomy Tools

- **JS9** - FITS image viewer
  - Standard astronomy tool
  - Zoom, pan, colormap controls
  - Catalog overlay support

### Backend Technologies

#### Web Framework

- **FastAPI** - Modern Python web framework
  - Automatic API documentation (OpenAPI/Swagger)
  - Type validation with Pydantic
  - Async/await support
  - High performance

#### Data Validation

- **Pydantic v2** - Data validation and serialization
  - Type validation
  - Automatic JSON serialization
  - Field validation
  - Model documentation

#### Database

- **SQLite3** - Embedded database
  - 4 separate databases for different concerns
  - ACID compliance
  - No server required
  - File-based storage

#### System Monitoring

- **psutil** - System metrics collection
  - CPU, memory, disk usage
  - Process monitoring
  - System load averages

#### Real-Time Communication

- **WebSocket** - Real-time bidirectional communication
  - FastAPI WebSocket support
  - Connection management
  - Message broadcasting
- **Server-Sent Events (SSE)** - Fallback for real-time updates
  - One-way server-to-client
  - Automatic reconnection
  - Simpler than WebSocket

### Infrastructure

#### Containerization

- **Docker** - Containerization for streaming service
  - Isolated execution environment
  - Consistent deployment
  - Resource management

#### Service Management

- **Systemd** - Service management (optional)
  - Process management
  - Auto-restart on failure
  - Logging integration

#### Radio Astronomy Environment

- **CASA6** - Radio astronomy data processing
  - Python environment with CASA tools
  - Measurement Set handling
  - Calibration and imaging tools
  - Required for pipeline operations

---

## System Components

### Frontend Components

#### 1. Unified Command Center (Dashboard Shell)

- Adaptive UI that changes based on dashboard state
- State-driven component rendering
- Contextual action bar
- Workflow guidance system

#### 2. Streaming Pipeline Monitor

- Real-time operation tracking
- Progress monitoring
- Resource usage display
- Queue statistics

#### 3. State Machine

- Dashboard state management (idle, autonomous, discovery, investigation,
  debugging, manual-control, analysis)
- State transition logic
- State persistence
- Context tracking

#### 4. Pre-fetch Engine

- Anticipatory data loading
- Preload target calculation
- Context-based prefetching
- Workflow-based prefetching

#### 5. Contextual Intelligence

- Action suggestion engine
- Workflow guidance
- State-aware UI
- User intent detection

#### 6. Workflow State Machine

- Complex task guidance
- Step-by-step workflows
- Progress tracking
- Workflow completion

#### 7. Autonomous Operations Tracker

- Operation type tracking
- Status monitoring
- Progress display
- History tracking

#### 8. Manual Override Controller

- Override trigger detection
- Control scope management
- Override workflow
- Return to autonomous

#### 9. Analysis Workspace

- Flexible layout system (Golden Layout)
- Multiple analysis tools
- Data product integration
- Reproducibility system

### Backend Components

#### 1. API Server (FastAPI)

- REST endpoint routing
- Request/response handling
- Authentication (future)
- Rate limiting (future)

#### 2. Data Access Layer

- Database query functions
- File system operations
- Data transformation
- Error handling

#### 3. Streaming Service Manager

- Service lifecycle management
- Configuration persistence
- Status monitoring
- Health checks

#### 4. WebSocket Manager

- Connection management
- Message broadcasting
- Connection state tracking
- Reconnection handling

#### 5. Job Queue Manager

- Job submission
- Job status tracking
- Job execution
- Job logging

#### 6. Calibration Registry

- Calibration table management
- Validity window tracking
- Calibration lookup
- Registry queries

---

## Data Flow Architecture

### Pipeline Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│  1. HDF5 Group Detection (16 subband files)                 │
│     Input: /data/incoming/*.hdf5                            │
│     Action: Register group in ingest_queue                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  2. HDF5 :arrow_right: MS Conversion                                    │
│     Input: 16 subband HDF5 files                            │
│     Output: Single Measurement Set                          │
│     Register: ms_index (stage="converted")                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  3. Group Formation (10 MS files)                           │
│     Trigger: 10 MS files with stage="converted"             │
│     Action: Form group, select calibration MS (5th of 10)   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  4. Calibration Solving                                     │
│     Input: 5th MS (middle by time)                          │
│     Check: Registry for existing valid solutions            │
│     If not found: Solve bandpass + gains                    │
│     Register: cal_registry (validity windows)               │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  5. Calibration Application                                 │
│     Input: All 10 MS files                                  │
│     Query: Registry for valid solutions per MS              │
│     Action: Apply calibration tables                        │
│     Update: ms_index (stage="calibrated", cal_applied=1)   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  6. Individual Imaging                                     │
│     Input: 10 calibrated MS files                           │
│     Action: Image each MS individually                      │
│     Output: 10 FITS images                                 │
│     Register: images table                                 │
│     Update: ms_index (stage="imaged")                      │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  7. Mosaic Generation                                       │
│     Input: 10 individual images (tiles)                     │
│     Action: Create weighted mosaic                          │
│     Output: Single mosaic FITS file                        │
│     Register: mosaics table                                │
│     Update: ms_index (stage="mosaicked")                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  8. Photometry & ESE Detection                              │
│     Input: Images                                           │
│     Action: Extract flux measurements                       │
│     Output: Photometry timeseries                          │
│     Register: photometry_timeseries, variability_stats    │
│     Detect: ESE candidates (5σ threshold)                   │
└─────────────────────────────────────────────────────────────┘
```

### Dashboard Data Flow

```
User Action :arrow_right: Frontend Component :arrow_right: API Request :arrow_right: Backend Handler :arrow_right: Database Query :arrow_right: Response :arrow_right: Frontend Update

Real-Time Flow:
Backend Event :arrow_right: WebSocket Broadcast :arrow_right: Frontend WebSocket Client :arrow_right: React Query Cache Update :arrow_right: UI Re-render

Polling Fallback:
Frontend Polling Timer :arrow_right: API Request :arrow_right: Backend Handler :arrow_right: Database Query :arrow_right: Response :arrow_right: React Query Cache Update :arrow_right: UI Re-render
```

### Database Architecture

**4 SQLite Databases:**

1. **`ingest.sqlite3`** - Queue management
   - `ingest_queue` - Observation groups
   - `subband_files` - Individual UVH5 files
   - `performance_metrics` - Processing times

2. **`products.sqlite3`** - Data products
   - `ms_index` - Measurement Sets
   - `images` - Image products
   - `photometry_timeseries` - Flux measurements
   - `variability_stats` - Variability metrics
   - `ese_candidates` - ESE detection
   - `mosaics` - Mosaic products

3. **`cal_registry.sqlite3`** - Calibration tracking
   - `caltables` - Calibration tables
   - Validity windows
   - Calibration sets

4. **`catalogs/master_sources.sqlite3`** - Source catalog
   - `sources` - NVSS/VLASS/FIRST crossmatch
   - Source associations

---

## Deployment Architecture

### Development Environment

```
┌─────────────────────────────────────────────────────────────┐
│  Development Machine                                         │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Frontend Dev     │         │  Backend API     │         │
│  │  (Vite)           │         │  (FastAPI)       │         │
│  │  Port: 5173      │◄───────►│  Port: 8000      │         │
│  │  HMR Enabled     │  HTTP   │  Auto-reload     │         │
│  └──────────────────┘         └──────────────────┘         │
│         │                              │                    │
│         │                              │                    │
│         └──────────────┬───────────────┘                    │
│                        │                                     │
│         ┌──────────────▼───────────────┐                    │
│         │  SQLite Databases            │                    │
│         │  /state/*.sqlite3            │                    │
│         └──────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### Production Environment

```
┌─────────────────────────────────────────────────────────────┐
│  Production Server                                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Nginx / Apache (Reverse Proxy)                       │   │
│  │  Port: 80/443 (HTTPS)                                 │   │
│  └───────────────┬──────────────────┬──────────────────┘   │
│                  │                  │                       │
│    ┌─────────────▼──────────┐  ┌────▼──────────────────┐   │
│    │  Static Files          │  │  FastAPI Backend      │   │
│    │  (React Build)         │  │  (Uvicorn)            │   │
│    │  /var/www/dashboard/   │  │  Port: 8000           │   │
│    └────────────────────────┘  └────┬───────────────────┘   │
│                                     │                       │
│              ┌──────────────────────┼──────────────────┐   │
│              │                      │                  │   │
│    ┌─────────▼──────────┐  ┌────────▼──────────┐  ┌───▼──┐│
│    │  SQLite Databases  │  │  Streaming Service │  │ Jobs ││
│    │  /state/*.sqlite3  │  │  (Docker/Process)  │  │Queue ││
│    └────────────────────┘  └────────────────────┘  └──────┘│
└─────────────────────────────────────────────────────────────┘
```

### Docker Deployment (Optional)

```
┌─────────────────────────────────────────────────────────────┐
│  Docker Compose Stack                                         │
│                                                              │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Frontend        │         │  Backend API     │         │
│  │  Container       │◄───────►│  Container       │         │
│  │  (Nginx)         │  HTTP   │  (FastAPI)       │         │
│  └──────────────────┘         └──────────────────┘         │
│         │                              │                    │
│         │                              │                    │
│         └──────────────┬───────────────┘                    │
│                        │                                     │
│         ┌──────────────▼───────────────┐                    │
│         │  Volume Mounts                │                    │
│         │  - /state (databases)         │                    │
│         │  - /scratch (data products)   │                    │
│         └──────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- **[Dashboard Vision & Design](./dashboard_frontend_architecture.md)** - Design
  principles and vision
- **[Frontend Architecture](./dashboard_frontend_architecture.md)** -
  Detailed frontend architecture
- **[Backend API Reference](../../reference/dashboard_backend_api.md)** - API
  endpoint documentation
- **[Streaming Architecture](../pipeline/streaming-architecture.md)** - Streaming service
  architecture

---

**Last Updated:** 2025-11-12  
**Status:** Consolidated Architecture Document
