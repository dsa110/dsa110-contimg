# DSA-110 Continuum Imaging Pipeline - Comprehensive Dashboard Overview

**Audience:** Frontend Developers & Radio Astronomers  
**Date:** 2025-11-12  
**Status:** Detailed technical and scientific overview

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Frontend Architecture (Developer-Focused)](#frontend-architecture-developer-focused)
4. [Backend API Architecture](#backend-api-architecture)
5. [Database Schema & Data Models](#database-schema--data-models)
6. [Dashboard Pages - Technical Deep Dive](#dashboard-pages---technical-deep-dive)
7. [Scientific Context (Astronomer-Focused)](#scientific-context-astronomer-focused)
8. [Data Flow & Workflows](#data-flow--workflows)
9. [Real-Time Updates & State Management](#real-time-updates--state-management)
10. [API Reference with Examples](#api-reference-with-examples)
11. [Component Implementation Details](#component-implementation-details)
12. [Production Readiness](#production-readiness)

---

## Executive Summary

The DSA-110 Continuum Imaging Pipeline Dashboard is a production-grade web application serving as the primary interface for monitoring and controlling an autonomous radio astronomy data processing pipeline. The pipeline processes streaming radio interferometry data from the DSA-110 telescope array, converting raw visibility data (UVH5 format) into calibrated images and mosaics for scientific analysis.

**For Radio Astronomers:** This dashboard provides real-time monitoring of the pipeline that processes your observations, detects extreme scattering events (ESE) in compact radio sources, and generates calibrated continuum images. You can monitor pipeline health, explore data products, and manually intervene when needed.

**For Frontend Developers:** This is a modern React 18 + TypeScript application with 100+ REST API endpoints, WebSocket real-time updates, comprehensive error handling, and a sophisticated state management system. The codebase demonstrates production patterns for data-intensive scientific applications.

**Key Metrics:**
- **8 major pages** with distinct functionality
- **100+ REST API endpoints** (FastAPI backend)
- **50+ React components** organized by domain
- **4 SQLite databases** for state management
- **Real-time updates** via WebSocket + HTTP polling fallback
- **10-second refresh intervals** for critical monitoring data

---

## System Architecture

### High-Level Architecture

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

### Technology Stack

**Frontend:**
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

**Backend:**
- **FastAPI** - Modern Python web framework
- **Pydantic v2** - Data validation and serialization
- **SQLite3** - Embedded database (4 databases)
- **psutil** - System metrics collection
- **WebSocket** - Real-time bidirectional communication
- **Server-Sent Events (SSE)** - Fallback for real-time updates

**Infrastructure:**
- **Docker** - Containerization for streaming service
- **Systemd** - Service management (optional)
- **CASA6** - Radio astronomy data processing (Python environment)

---

## Frontend Architecture (Developer-Focused)

### Project Structure

```
frontend/
├── src/
│   ├── api/                          # API client layer
│   │   ├── client.ts                # Axios instance with interceptors
│   │   ├── queries.ts               # React Query hooks (100+ hooks)
│   │   ├── types.ts                 # TypeScript interfaces
│   │   ├── websocket.ts             # WebSocket client
│   │   ├── circuitBreaker.ts        # Circuit breaker pattern
│   │   └── retry.ts                 # Retry logic utilities
│   │
│   ├── components/                   # Reusable UI components
│   │   ├── Health/                  # Health monitoring components
│   │   ├── Observing/                # Observation-related
│   │   ├── QA/                      # QA visualization
│   │   │   ├── DirectoryBrowser.tsx
│   │   │   ├── FITSViewer.tsx
│   │   │   ├── CasaTableViewer.tsx
│   │   │   └── QANotebookGenerator.tsx
│   │   ├── Sky/                     # Sky/FITS viewing
│   │   │   ├── SkyViewer.tsx        # JS9 integration
│   │   │   ├── ImageBrowser.tsx
│   │   │   ├── CatalogOverlayJS9.tsx
│   │   │   ├── ImageFittingTool.tsx
│   │   │   └── ProfileTool.tsx
│   │   ├── Sources/                 # Source-related
│   │   ├── Navigation.tsx           # Top navigation bar
│   │   ├── ESECandidatesPanel.tsx   # ESE detection display
│   │   ├── PointingVisualization.tsx # Telescope pointing map
│   │   └── MSTable.tsx              # Measurement Set table
│   │
│   ├── pages/                        # Page-level components (routes)
│   │   ├── DashboardPage.tsx        # Main monitoring page
│   │   ├── ControlPage.tsx          # Manual job execution
│   │   ├── StreamingPage.tsx        # Streaming service control
│   │   ├── MosaicGalleryPage.tsx    # Mosaic query/generation
│   │   ├── SourceMonitoringPage.tsx # Source flux monitoring
│   │   ├── SkyViewPage.tsx          # FITS image viewer
│   │   ├── QAVisualizationPage.tsx # QA data exploration
│   │   └── DataBrowserPage.tsx      # Data product browser
│   │
│   ├── stores/                       # State management
│   │   ├── dashboardState.ts        # Dashboard-specific state
│   │   └── dashboardStore.ts        # Global store (if needed)
│   │
│   ├── contexts/                      # React contexts
│   │   └── NotificationContext.tsx  # Toast notifications
│   │
│   ├── hooks/                         # Custom React hooks
│   │   ├── useLocalStorage.ts       # LocalStorage persistence
│   │   └── useSelectionState.ts     # Selection state management
│   │
│   ├── utils/                         # Utility functions
│   │   ├── errorUtils.ts            # Error classification
│   │   ├── logger.ts                # Logging utility
│   │   └── selectionLogic.ts        # MS selection logic
│   │
│   ├── theme/                         # MUI theme configuration
│   │   └── darkTheme.ts             # Dark theme for astronomy
│   │
│   ├── App.tsx                        # Root component
│   └── main.tsx                      # Entry point
│
├── public/                            # Static assets
│   ├── js9/                          # JS9 FITS viewer library
│   └── astroemw.js/wasm             # JS9 WebAssembly support
│
├── package.json                       # Dependencies
├── tsconfig.json                      # TypeScript config
├── vite.config.ts                     # Vite configuration
└── vitest.config.ts                   # Test configuration
```

### API Client Architecture

The API client uses a sophisticated error handling and retry strategy:

```typescript
// frontend/src/api/client.ts

// Circuit breaker pattern prevents cascading failures
const circuitBreaker = createCircuitBreaker({
  failureThreshold: 5,        // Open after 5 failures
  resetTimeout: 30000,         // 30 seconds cooldown
  monitoringPeriod: 60000,     // 1 minute window
});

// Axios instance with interceptors
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,              // 30 seconds (for long-running jobs)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Check circuit breaker
apiClient.interceptors.request.use((config) => {
  if (!circuitBreaker.canAttempt()) {
    throw new Error('Service temporarily unavailable');
  }
  return config;
});

// Response interceptor: Retry logic with exponential backoff
apiClient.interceptors.response.use(
  (response) => {
    circuitBreaker.recordSuccess();
    return response;
  },
  async (error: AxiosError) => {
    const classified = classifyError(error);
    
    // Retry up to 3 times for retryable errors
    if (classified.retryable && retryCount < 3) {
      const delay = Math.min(1000 * Math.pow(2, retryCount), 10000);
      await new Promise(resolve => setTimeout(resolve, delay));
      return await apiClient.request(config);
    }
    
    return Promise.reject(error);
  }
);
```

**Error Classification:**
- **Network errors** (ECONNREFUSED, ETIMEDOUT) → Retryable
- **5xx server errors** → Retryable
- **4xx client errors** → Not retryable
- **Circuit breaker open** → Not retryable

### React Query Integration

React Query provides automatic caching, background refetching, and optimistic updates:

```typescript
// frontend/src/api/queries.ts

// Pipeline status with WebSocket + polling fallback
export function usePipelineStatus(): UseQueryResult<PipelineStatus> {
  const wsClient = getWebSocketClient();
  
  return useRealtimeQuery(
    ['pipeline', 'status'],
    async () => {
      const response = await apiClient.get<PipelineStatus>('/api/status');
      return response.data;
    },
    wsClient,
    10000 // Fallback polling: 10 seconds
  );
}

// Mutation for creating jobs
export function useCreateCalibrateJob() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (params: CalibrateJobParams & { ms_path: string }) => {
      const response = await apiClient.post<Job>('/api/jobs/calibrate', params);
      return response.data;
    },
    onSuccess: () => {
      // Invalidate and refetch job list
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });
}
```

**Query Configuration:**
- **Stale time:** 30 seconds (default)
- **Cache time:** 5 minutes
- **Retry:** Up to 3 times with exponential backoff
- **Refetch on window focus:** Disabled (prevents unnecessary requests)

### Component Patterns

**Example: ESE Candidates Panel**

```typescript
// frontend/src/components/ESECandidatesPanel.tsx

export default function ESECandidatesPanel() {
  const { data, isLoading, error } = useESECandidates();
  
  // Auto-refresh every 10 seconds via React Query
  // WebSocket updates invalidate cache automatically
  
  if (isLoading) {
    return <CircularProgress />;
  }
  
  const activeCandidates = data?.candidates.filter(
    c => c.status === 'active'
  ) || [];
  
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5">
        ESE Candidates
        {activeCandidates.length > 0 && (
          <Chip label={activeCandidates.length} color="error" />
        )}
      </Typography>
      
      <Table>
        {data?.candidates.map((candidate) => (
          <TableRow
            key={candidate.source_id}
            sx={{
              backgroundColor: candidate.status === 'active' 
                ? 'rgba(244, 67, 54, 0.05)' 
                : 'inherit',
            }}
          >
            <TableCell>
              <Typography fontFamily="monospace">
                {candidate.source_id}
              </Typography>
            </TableCell>
            <TableCell align="right">
              <Typography
                fontWeight="bold"
                color={candidate.max_sigma_dev >= 10 ? 'error' : 'warning'}
              >
                {candidate.max_sigma_dev.toFixed(1)}σ
              </Typography>
            </TableCell>
            {/* ... more cells ... */}
          </TableRow>
        ))}
      </Table>
    </Paper>
  );
}
```

**Key Patterns:**
- **Conditional rendering** based on loading/error states
- **Type-safe** props and data structures
- **Material-UI** components for consistent styling
- **React Query** for automatic data fetching and caching

---

## Backend API Architecture

### FastAPI Application Structure

```python
# src/dsa110_contimg/api/routes.py

def create_app(config: ApiConfig | None = None) -> FastAPI:
    """Factory for the monitoring API application."""
    
    cfg = config or ApiConfig.from_env()
    app = FastAPI(
        title="DSA-110 Continuum Pipeline API",
        version="0.1.0"
    )
    
    # CORS middleware for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # WebSocket manager for real-time updates
    @app.on_event("startup")
    async def start_status_broadcaster():
        async def broadcast_status():
            while True:
                await asyncio.sleep(10)  # Broadcast every 10 seconds
                # Fetch and broadcast pipeline status, metrics, ESE candidates
                await manager.broadcast_status_update(create_status_update())
        
        asyncio.create_task(broadcast_status())
    
    # Include routers
    router = APIRouter()
    # ... route definitions ...
    app.include_router(router)
    
    return app
```

### API Endpoint Organization

Endpoints are organized by functional domain:

**1. Pipeline Status & Monitoring** (`/api/status`, `/api/metrics/system`)
**2. Streaming Service** (`/api/streaming/*`)
**3. Job Management** (`/api/jobs/*`)
**4. Measurement Sets** (`/api/ms/*`)
**5. Calibration** (`/api/cal_tables/*`)
**6. Mosaics** (`/api/mosaics/*`)
**7. Sources** (`/api/sources/*`)
**8. Images** (`/api/images/*`)
**9. QA Visualization** (`/api/visualization/*`)
**10. WebSocket** (`/api/ws/status`)

### Data Access Layer

The backend uses a clean separation between routes and data access:

```python
# src/dsa110_contimg/api/data_access.py

def fetch_queue_stats(queue_db: Path) -> QueueStats:
    """Fetch queue statistics from ingest database."""
    with closing(_connect(queue_db)) as conn:
        row = conn.execute("""
            SELECT 
                COUNT(*) AS total,
                SUM(CASE WHEN state = 'pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN state = 'in_progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN state = 'failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN state = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN state = 'collecting' THEN 1 ELSE 0 END) AS collecting
            FROM ingest_queue
        """).fetchone()
        
        return QueueStats(
            total=row["total"] or 0,
            pending=row["pending"] or 0,
            in_progress=row["in_progress"] or 0,
            failed=row["failed"] or 0,
            completed=row["completed"] or 0,
            collecting=row["collecting"] or 0,
        )
```

**Benefits:**
- **Testable** - Data access functions can be unit tested
- **Reusable** - Same functions used by CLI and API
- **Type-safe** - Pydantic models ensure correct data structures

### Pydantic Models

All API responses use Pydantic models for validation:

```python
# src/dsa110_contimg/api/models.py

class QueueStats(BaseModel):
    total: int
    pending: int
    in_progress: int
    failed: int
    completed: int
    collecting: int

class QueueGroup(BaseModel):
    group_id: str = Field(..., description="Normalized observation timestamp")
    state: str = Field(
        ..., 
        description="Queue state (collecting|pending|in_progress|completed|failed)"
    )
    received_at: datetime
    last_update: datetime
    subbands_present: int = Field(
        ..., 
        description="Number of subbands ingested for this group"
    )
    expected_subbands: int = Field(
        ..., 
        description="Expected subbands per group (usually 16)"
    )
    has_calibrator: bool | None = Field(
        None, 
        description="True if any calibrator was matched in beam"
    )
    matches: list[CalibratorMatch] | None = Field(
        None, 
        description="Top matched calibrators for this group"
    )

class PipelineStatus(BaseModel):
    queue: QueueStats
    recent_groups: List[QueueGroup]
    calibration_sets: List[CalibrationSet]
    matched_recent: int = Field(
        0, 
        description="Number of recent groups with calibrator matches"
    )
```

**Pydantic Benefits:**
- **Automatic validation** - Invalid data rejected at API boundary
- **Type coercion** - Strings converted to appropriate types
- **Documentation** - Field descriptions appear in OpenAPI docs
- **Serialization** - Automatic JSON serialization

---

## Database Schema & Data Models

### Database Overview

The pipeline uses **4 SQLite databases** for state management:

| Database | Location | Purpose | Key Tables |
|----------|----------|---------|------------|
| `ingest.sqlite3` | `/data/dsa110-contimg/state/` | Queue management | `ingest_queue`, `subband_files`, `performance_metrics` |
| `products.sqlite3` | `/data/dsa110-contimg/state/` | Data products | `ms_index`, `images`, `photometry_timeseries`, `mosaics` |
| `cal_registry.sqlite3` | `/data/dsa110-contimg/state/` | Calibration tracking | `caltables` |
| `master_sources.sqlite3` | `/data/dsa110-contimg/state/catalogs/` | Source catalog | `sources`, `variability_stats`, `ese_candidates` |

### Ingest Queue Database (`ingest.sqlite3`)

**Table: `ingest_queue`**
Tracks observation groups through the pipeline lifecycle.

```sql
CREATE TABLE ingest_queue (
    group_id TEXT PRIMARY KEY,              -- YYYY-MM-DDTHH:MM:SS format
    state TEXT NOT NULL,                    -- collecting|pending|in_progress|completed|failed
    received_at REAL NOT NULL,              -- Unix timestamp
    last_update REAL NOT NULL,              -- Unix timestamp
    expected_subbands INTEGER DEFAULT 16,   -- Usually 16 subbands per group
    has_calibrator INTEGER,                 -- 0/1 boolean (NULL if not checked)
    calibrators TEXT,                       -- JSON array of matched calibrators
    retry_count INTEGER DEFAULT 0,
    error_message TEXT
);

CREATE INDEX idx_ingest_state ON ingest_queue(state);
CREATE INDEX idx_ingest_received ON ingest_queue(received_at);
```

**For Astronomers:** Each row represents a 5-minute observation group. The `state` field tracks where the group is in processing: `collecting` means we're still waiting for all 16 subband files to arrive, `pending` means ready for processing, `in_progress` means currently being converted/calibrated/imaged, `completed` means successfully processed, and `failed` means an error occurred.

**For Developers:** The `group_id` is a normalized timestamp (ISO format) that serves as the primary key. The `calibrators` field stores JSON, which is parsed by the API layer into `CalibratorMatch` objects.

**Table: `subband_files`**
Tracks individual subband files per observation group.

```sql
CREATE TABLE subband_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,
    subband_idx INTEGER NOT NULL,          -- 0-15 (16 subbands total)
    file_path TEXT NOT NULL,
    file_size INTEGER,
    discovered_at REAL NOT NULL,
    FOREIGN KEY (group_id) REFERENCES ingest_queue(group_id),
    UNIQUE(group_id, subband_idx)
);
```

**For Astronomers:** DSA-110 observes in 16 frequency subbands simultaneously. Each subband is recorded as a separate file. The pipeline waits until all 16 subbands are present before processing a group.

**For Developers:** The `UNIQUE(group_id, subband_idx)` constraint ensures we don't duplicate subband files. The `subband_idx` ranges from 0-15.

### Products Database (`products.sqlite3`)

**Table: `ms_index`**
Tracks Measurement Set files (the intermediate data format between raw visibilities and images).

```sql
CREATE TABLE ms_index (
    path TEXT PRIMARY KEY,                  -- Full filesystem path to MS
    start_mjd REAL,                        -- Start time (Modified Julian Date)
    end_mjd REAL,                          -- End time (MJD)
    mid_mjd REAL,                          -- Middle time (MJD) - used for calibration lookup
    processed_at REAL,                     -- When MS was created
    status TEXT,                           -- converted|calibrated|imaged|mosaicked
    stage TEXT,                            -- Processing stage
    stage_updated_at REAL,
    cal_applied INTEGER DEFAULT 0,         -- 0/1 boolean
    imagename TEXT                         -- Path to resulting image
);
```

**For Astronomers:** A Measurement Set (MS) is the standard radio astronomy data format (CASA format). It contains visibility data (complex amplitudes) from the interferometer. The `mid_mjd` field is critical - it's used to look up which calibration solutions should be applied to this observation.

**For Developers:** The `path` is the primary key. The `stage` field tracks processing progress: `converted` (UVH5 → MS), `calibrated` (calibration applied), `imaged` (MS → image), `mosaicked` (image → mosaic).

**Table: `images`**
Tracks continuum images produced from Measurement Sets.

```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,                     -- Path to FITS image file
    ms_path TEXT NOT NULL,                  -- Source Measurement Set
    created_at REAL NOT NULL,
    type TEXT NOT NULL,                     -- image|pbcor|residual|psf|pb
    beam_major_arcsec REAL,                 -- Synthesized beam major axis
    beam_minor_arcsec REAL,                 -- Synthesized beam minor axis
    beam_pa_deg REAL,                       -- Beam position angle
    noise_jy REAL,                          -- Image noise level (Jy)
    peak_flux_jy REAL,                      -- Peak flux in image (Jy)
    pbcor INTEGER DEFAULT 0                 -- Primary-beam corrected flag
);
```

**For Astronomers:** The `type` field indicates image type: `image` is the standard continuum image, `pbcor` is primary-beam corrected (accounts for sensitivity falloff away from pointing center), `residual` is the difference between data and model (used for quality assessment), `psf` is the point-spread function (beam pattern), and `pb` is the primary beam response pattern.

**For Developers:** Images are stored as FITS files. The `noise_jy` field is computed during imaging and represents the RMS noise level, critical for source detection thresholds.

**Table: `photometry_timeseries`**
Flux measurements per source per epoch (for variability monitoring).

```sql
CREATE TABLE photometry_timeseries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,                -- NVSS ID format: "NVSS J123456.7+420312"
    ms_path TEXT NOT NULL,
    image_path TEXT NOT NULL,
    epoch_mjd REAL NOT NULL,                -- Observation time (MJD)
    flux_jy REAL NOT NULL,                  -- Measured flux (Jy)
    flux_err_jy REAL,                      -- Flux uncertainty (Jy)
    normalized_flux_jy REAL,               -- Flux normalized to reference epoch
    normalized_flux_err_jy REAL,
    is_reference INTEGER DEFAULT 0,        -- Is this the reference epoch?
    snr REAL                               -- Signal-to-noise ratio
);

CREATE INDEX idx_photometry_source ON photometry_timeseries(source_id);
CREATE INDEX idx_photometry_epoch ON photometry_timeseries(epoch_mjd);
```

**For Astronomers:** This table stores the light curves (flux vs. time) for each monitored source. The `normalized_flux_jy` field normalizes all measurements to a reference epoch, making it easier to detect variability. The `snr` field helps filter out low-quality measurements.

**For Developers:** This is a time-series database optimized for queries like "get all flux measurements for source X" or "get all sources observed at time Y". The `source_id` uses NVSS naming convention (survey + J2000 coordinates).

**Table: `variability_stats`**
Pre-computed variability metrics per source (for ESE detection).

```sql
CREATE TABLE variability_stats (
    source_id TEXT PRIMARY KEY,
    n_epochs INTEGER,                      -- Number of observations
    chi2_reduced REAL,                      -- Reduced chi-squared (variability test)
    fractional_variability REAL,            -- Fractional RMS variability
    significance REAL,                      -- Variability significance (sigma)
    ese_score REAL,                         -- ESE detection score
    asymmetry_index REAL,                   -- Light curve asymmetry
    characteristic_timescale_days REAL,     -- Variability timescale
    peak_to_trough_amplitude REAL,          -- Maximum flux variation
    last_updated REAL
);
```

**For Astronomers:** These statistics are computed from the `photometry_timeseries` data. The `chi2_reduced` tests whether the source is consistent with constant flux (values >5 indicate variability). The `ese_score` is a custom metric that identifies sources with ESE-like behavior (rapid flux increases followed by gradual decreases).

**For Developers:** These are pre-computed aggregates to avoid expensive calculations on every query. The `significance` field is the key metric - sources with `significance >= 5` are flagged as ESE candidates.

**Table: `ese_candidates`**
Flagged ESE candidate sources.

```sql
CREATE TABLE ese_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    first_detection_at REAL NOT NULL,       -- When variability first detected
    last_detection_at REAL NOT NULL,        -- Most recent detection
    max_sigma_dev REAL NOT NULL,            -- Maximum sigma deviation
    current_flux_jy REAL,                   -- Current flux measurement
    baseline_flux_jy REAL,                  -- Baseline (reference) flux
    status TEXT,                            -- active|resolved|false_positive
    notes TEXT
);

CREATE INDEX idx_ese_status ON ese_candidates(status);
CREATE INDEX idx_ese_source ON ese_candidates(source_id);
```

**For Astronomers:** This table tracks sources that have exceeded the 5σ variability threshold. The `status` field indicates: `active` (currently variable), `resolved` (variability has returned to baseline), or `false_positive` (manually flagged as not a real ESE).

**For Developers:** This is the source of truth for the ESE Candidates panel on the dashboard. The `max_sigma_dev` field is displayed prominently in the UI.

**Table: `mosaics`**
Mosaic plans and metadata.

```sql
CREATE TABLE mosaics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,              -- Mosaic identifier
    method TEXT,                            -- Mosaic generation method
    created_at REAL NOT NULL,
    built_at REAL,                          -- When mosaic was actually built
    output_path TEXT,                       -- Path to mosaic FITS file
    n_tiles INTEGER,                        -- Number of input images
    status TEXT,                            -- pending|in_progress|completed|failed
    start_mjd REAL,                         -- Start time (MJD)
    end_mjd REAL,                           -- End time (MJD)
    source_count INTEGER,                    -- Number of sources detected
    noise_jy REAL                           -- Mosaic noise level (Jy)
);
```

**For Astronomers:** A mosaic combines multiple individual images (tiles) into a single larger image covering a wider area of sky. Mosaics are typically created from ~1 hour of observations (10 tiles × 5 minutes each).

**For Developers:** The `status` field tracks mosaic generation progress. The `n_tiles` field indicates how many input images were combined.

### Calibration Registry (`cal_registry.sqlite3`)

**Table: `caltables`**
Tracks calibration tables and their validity windows.

```sql
CREATE TABLE caltables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    set_name TEXT NOT NULL,                 -- Logical set name (e.g., "bp_3c286_60238")
    path TEXT NOT NULL UNIQUE,             -- Full path to caltable file
    table_type TEXT NOT NULL,               -- K|BP|G (delay|bandpass|gain)
    order_index INTEGER NOT NULL,           -- Application order (K=0, BP=1, G=2)
    cal_field TEXT,                         -- Source/field used to solve
    refant TEXT,                            -- Reference antenna
    created_at REAL NOT NULL,
    valid_start_mjd REAL NOT NULL,         -- Start of validity window (MJD)
    valid_end_mjd REAL NOT NULL,           -- End of validity window (MJD)
    status TEXT DEFAULT 'active',           -- active|retired|failed
    notes TEXT
);

CREATE INDEX idx_caltables_set ON caltables(set_name);
CREATE INDEX idx_caltables_valid ON caltables(valid_start_mjd, valid_end_mjd);
CREATE INDEX idx_caltables_status ON caltables(status);
```

**For Astronomers:** Calibration tables correct for instrumental effects (antenna gains, bandpass response, delays). The `valid_start_mjd` and `valid_end_mjd` fields define when a calibration solution is valid - bandpass solutions are typically valid for ±12 hours around calibrator transit, while gain solutions are valid for ±30 minutes.

**For Developers:** The registry is the **authoritative source** for calibration decisions. When applying calibration to a Measurement Set, the pipeline queries the registry for tables whose validity windows include the MS observation time (`mid_mjd`). The `order_index` ensures tables are applied in the correct order (K → BP → G).

---

## Dashboard Pages - Technical Deep Dive

### 1. Dashboard Page (`/dashboard`)

**Purpose:** Main monitoring interface for pipeline health and status

**Component Structure:**

```typescript
// frontend/src/pages/DashboardPage.tsx

export default function DashboardPage() {
  // React Query hooks for data fetching
  const { data: status, isLoading, error } = usePipelineStatus();
  const { data: metrics } = useSystemMetrics();
  
  // Auto-refresh every 10 seconds via React Query
  // WebSocket updates invalidate cache automatically
  
  return (
    <Container maxWidth="xl">
      {/* Pipeline Status Panel */}
      <Paper>
        <Typography variant="h5">Pipeline Status</Typography>
        <Box>
          <Typography>Total: {status?.queue.total || 0}</Typography>
          <Typography>Pending: {status?.queue.pending || 0}</Typography>
          {/* ... more queue stats ... */}
        </Box>
        
        {/* Recent Observations Table */}
        <Table>
          {status?.recent_groups.map((group) => (
            <TableRow key={group.group_id}>
              <TableCell>{group.group_id}</TableCell>
              <TableCell>{group.state}</TableCell>
              <TableCell>
                {group.subbands_present}/{group.expected_subbands}
              </TableCell>
              <TableCell>
                {group.has_calibrator ? '✓' : '—'}
              </TableCell>
            </TableRow>
          ))}
        </Table>
      </Paper>
      
      {/* System Health Panel */}
      <Paper>
        <Typography variant="h5">System Health</Typography>
        <Box>
          <Typography>CPU: {metrics?.cpu_percent?.toFixed(1)}%</Typography>
          <Typography>Memory: {metrics?.mem_percent?.toFixed(1)}%</Typography>
          {/* ... more metrics ... */}
        </Box>
      </Paper>
      
      {/* Pointing Visualization */}
      <PointingVisualization 
        height={500} 
        showHistory={true} 
        historyDays={7} 
      />
      
      {/* ESE Candidates Panel */}
      <ESECandidatesPanel />
    </Container>
  );
}
```

**API Endpoints Used:**

1. **`GET /api/status`** - Pipeline queue statistics
   ```json
   {
     "queue": {
       "total": 150,
       "pending": 12,
       "in_progress": 3,
       "completed": 130,
       "failed": 5,
       "collecting": 2
     },
     "recent_groups": [
       {
         "group_id": "2025-10-24T14:00:00",
         "state": "completed",
         "subbands_present": 16,
         "expected_subbands": 16,
         "has_calibrator": true
       }
     ],
     "calibration_sets": [
       {
         "set_name": "bp_3c286_60238",
         "tables": ["/path/to/bp.cal", "/path/to/g.cal"],
         "active": 2,
         "total": 2
       }
     ],
     "matched_recent": 18
   }
   ```

2. **`GET /api/metrics/system`** - System health metrics
   ```json
   {
     "ts": "2025-10-24T14:30:00Z",
     "cpu_percent": 45.2,
     "mem_percent": 62.8,
     "mem_total": 68719476736,
     "mem_used": 43117412352,
     "disk_total": 5000000000000,
     "disk_used": 3200000000000,
     "load_1": 2.15,
     "load_5": 1.87,
     "load_15": 1.54
   }
   ```

3. **`GET /api/ese/candidates`** - ESE detection alerts
   ```json
   {
     "candidates": [
       {
         "source_id": "NVSS J123456.7+420312",
         "ra_deg": 188.736,
         "dec_deg": 42.053,
         "first_detection_at": "2025-10-24T12:00:00Z",
         "last_detection_at": "2025-10-24T14:00:00Z",
         "max_sigma_dev": 7.3,
         "current_flux_jy": 0.125,
         "baseline_flux_jy": 0.085,
         "status": "active"
       }
     ],
     "total": 1
   }
   ```

**For Astronomers:** This page gives you a real-time view of pipeline health. The queue statistics tell you how many observations are waiting to be processed, currently processing, or completed. The ESE Candidates panel shows sources that have exceeded the 5σ variability threshold - these are potential extreme scattering events that need follow-up observation.

**For Developers:** The page uses React Query's `useQuery` hooks which automatically handle caching, refetching, and error states. The WebSocket connection provides real-time updates without polling overhead.

### 2. Streaming Service Control (`/streaming`)

**Purpose:** Complete control interface for the autonomous streaming converter service

**Component Structure:**

```typescript
// frontend/src/pages/StreamingPage.tsx

export default function StreamingPage() {
  // Status queries (poll every 5 seconds)
  const { data: status } = useStreamingStatus();
  const { data: health } = useStreamingHealth();
  const { data: config } = useStreamingConfig();
  const { data: metrics } = useStreamingMetrics();
  
  // Mutations for control actions
  const startMutation = useStartStreaming();
  const stopMutation = useStopStreaming();
  const restartMutation = useRestartStreaming();
  const updateConfigMutation = useUpdateStreamingConfig();
  
  const handleStart = () => {
    startMutation.mutate(undefined, {
      onSuccess: (data) => {
        if (!data.success) {
          alert(`Failed to start: ${data.message}`);
        }
      },
    });
  };
  
  return (
    <Container>
      {/* Service Status Card */}
      <Card>
        <Chip
          label={status?.running ? 'Running' : 'Stopped'}
          color={status?.running ? 'success' : 'default'}
        />
        {status?.pid && <Typography>PID: {status.pid}</Typography>}
        {status?.uptime_seconds && (
          <Typography>Uptime: {formatUptime(status.uptime_seconds)}</Typography>
        )}
      </Card>
      
      {/* Resource Usage Card */}
      <Card>
        {status?.cpu_percent != null && (
          <Box>
            <LinearProgress value={status.cpu_percent} />
            <Typography>CPU: {status.cpu_percent.toFixed(1)}%</Typography>
          </Box>
        )}
        {status?.memory_mb != null && (
          <Typography>Memory: {status.memory_mb.toFixed(0)} MB</Typography>
        )}
      </Card>
      
      {/* Queue Statistics */}
      <Card>
        {metrics?.queue_stats && (
          <Stack>
            {Object.entries(metrics.queue_stats).map(([state, count]) => (
              <Box key={state}>
                <Typography>{state}: {count}</Typography>
              </Box>
            ))}
          </Stack>
        )}
        {metrics?.processing_rate_per_hour && (
          <Typography>
            Processing Rate: {metrics.processing_rate_per_hour} groups/hour
          </Typography>
        )}
      </Card>
      
      {/* Control Buttons */}
      <Stack direction="row" spacing={2}>
        <Button onClick={handleStart} disabled={status?.running}>
          Start
        </Button>
        <Button onClick={handleStop} disabled={!status?.running}>
          Stop
        </Button>
        <Button onClick={handleRestart} disabled={!status?.running}>
          Restart
        </Button>
      </Stack>
    </Container>
  );
}
```

**API Endpoints:**

1. **`GET /api/streaming/status`** - Service status
   ```json
   {
     "running": true,
     "pid": 12345,
     "started_at": "2025-10-24T10:00:00Z",
     "uptime_seconds": 16200,
     "cpu_percent": 35.2,
     "memory_mb": 2048,
     "error": null
   }
   ```

2. **`POST /api/streaming/start`** - Start service
   ```json
   {
     "success": true,
     "message": "Streaming service started",
     "pid": 12345
   }
   ```

3. **`GET /api/streaming/metrics`** - Processing metrics
   ```json
   {
     "queue_stats": {
       "pending": 5,
       "in_progress": 2,
       "completed": 150,
       "failed": 3
     },
     "processing_rate_per_hour": 12.5
   }
   ```

**For Astronomers:** The streaming service automatically processes incoming observations. This page lets you start/stop the service, monitor its resource usage, and see how many observations are being processed per hour.

**For Developers:** The streaming service manager (`StreamingServiceManager`) handles Docker container lifecycle or direct process management. Configuration is persisted to JSON (`state/streaming_config.json`) and survives API restarts.

### 3. Control Page (`/control`)

**Purpose:** Manual job execution and pipeline workflow control

**Component Structure:**

```typescript
// frontend/src/pages/ControlPage.tsx

export default function ControlPage() {
  const [selectedMS, setSelectedMS] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  
  // Data queries
  const { data: msList } = useMSList({ scan: true });
  const { data: msMetadata } = useMSMetadata(selectedMS);
  const { data: calMatches } = useCalibratorMatches(selectedMS);
  const { data: existingTables } = useExistingCalTables(selectedMS);
  
  // Mutations
  const calibrateMutation = useCreateCalibrateJob();
  const imageMutation = useCreateImageJob();
  
  const handleCalibrate = () => {
    calibrateMutation.mutate({
      ms_path: selectedMS,
      params: {
        field: '',
        refant: '103',
        solve_bandpass: true,
        solve_gains: true,
        gain_solint: 'inf',
        gain_calmode: 'ap',
        auto_fields: true,
        min_pb: 0.5,
      },
    });
  };
  
  return (
    <Container>
      <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
        <Tab label="Measurement Sets" />
        <Tab label="Calibration" />
        <Tab label="Imaging" />
        <Tab label="Workflow" />
      </Tabs>
      
      {/* MS Selection */}
      <MSTable
        msList={msList?.items || []}
        selectedMS={selectedMS}
        onSelectMS={setSelectedMS}
      />
      
      {/* Calibration Form */}
      {activeTab === 1 && (
        <Paper>
          <TextField
            label="Reference Antenna"
            value="103"
            onChange={(e) => setRefant(e.target.value)}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={solveBandpass}
                onChange={(e) => setSolveBandpass(e.target.checked)}
              />
            }
            label="Solve Bandpass"
          />
          <Button onClick={handleCalibrate}>
            Run Calibration
          </Button>
        </Paper>
      )}
      
      {/* Calibration QA Panel */}
      {selectedMS && (
        <CalibrationQAPanel msPath={selectedMS} />
      )}
    </Container>
  );
}
```

**Job Types:**

1. **Conversion Jobs** - Convert UVH5 → Measurement Set
2. **Calibration Jobs** - Solve for calibration solutions
3. **Apply Jobs** - Apply calibration tables to data
4. **Imaging Jobs** - Create continuum images from MS
5. **Workflow Jobs** - End-to-end processing (convert → calibrate → image)

**API Endpoints:**

1. **`POST /api/jobs/calibrate`** - Create calibration job
   ```json
   {
     "ms_path": "/scratch/dsa110-contimg/ms/2025-10-24T14:00:00.ms",
     "params": {
       "field": "",
       "refant": "103",
       "solve_bandpass": true,
       "solve_gains": true,
       "gain_solint": "inf",
       "gain_calmode": "ap",
       "auto_fields": true,
       "min_pb": 0.5
     }
   }
   ```

2. **`GET /api/jobs`** - List all jobs
   ```json
   {
     "items": [
       {
         "id": 1,
         "type": "calibrate",
         "status": "completed",
         "ms_path": "/path/to/ms",
         "params": {...},
         "created_at": "2025-10-24T14:00:00Z",
         "started_at": "2025-10-24T14:01:00Z",
         "finished_at": "2025-10-24T14:05:00Z"
       }
     ]
   }
   ```

**For Astronomers:** This page lets you manually run calibration and imaging when the autonomous pipeline needs intervention. You can select a Measurement Set, configure calibration parameters (reference antenna, solution intervals), and run calibration. The Calibration QA panel shows quality metrics to verify the calibration worked correctly.

**For Developers:** Jobs are submitted asynchronously and tracked in a job queue. The API returns a job ID immediately, and the frontend polls for status updates. Job logs are available via `GET /api/jobs/{job_id}/logs`.

### 4. Mosaic Gallery (`/mosaics`)

**Purpose:** Time-range query interface for hour-long mosaics

**Component Structure:**

```typescript
// frontend/src/pages/MosaicGalleryPage.tsx

export default function MosaicGalleryPage() {
  const [startTime, setStartTime] = useState(dayjs().subtract(1, 'hour'));
  const [endTime, setEndTime] = useState(dayjs());
  const [queryRequest, setQueryRequest] = useState(null);
  
  const { data, isLoading } = useMosaicQuery(queryRequest);
  const createMosaic = useCreateMosaic();
  
  const handleQuery = () => {
    setQueryRequest({
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
    });
  };
  
  const handleCreateMosaic = () => {
    createMosaic.mutate({
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
    });
  };
  
  return (
    <Container>
      {/* Time Range Selection */}
      <Paper>
        <DateTimePicker
          label="Start Time (UTC)"
          value={startTime}
          onChange={setStartTime}
        />
        <DateTimePicker
          label="End Time (UTC)"
          value={endTime}
          onChange={setEndTime}
        />
        <Button onClick={handleQuery}>Query Mosaics</Button>
        <Button onClick={handleCreateMosaic}>Create New Mosaic</Button>
      </Paper>
      
      {/* Mosaic Grid */}
      <Grid container spacing={3}>
        {data?.mosaics.map((mosaic) => (
          <Grid item key={mosaic.id}>
            <Card>
              <CardMedia>
                {mosaic.thumbnail_path && (
                  <img src={mosaic.thumbnail_path} alt={mosaic.name} />
                )}
              </CardMedia>
              <CardContent>
                <Typography variant="h6">{mosaic.name}</Typography>
                <Chip label={mosaic.status} color={getStatusColor(mosaic.status)} />
                <Typography>
                  {mosaic.source_count} sources | {mosaic.noise_jy * 1000} mJy noise
                </Typography>
              </CardContent>
              <CardActions>
                <Button>Download FITS</Button>
                <Button onClick={() => navigate(`/mosaics/${mosaic.id}`)}>
                  View
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Container>
  );
}
```

**API Endpoints:**

1. **`POST /api/mosaics/query`** - Query mosaics by time range
   ```json
   {
     "start_time": "2025-10-24T13:00:00Z",
     "end_time": "2025-10-24T14:00:00Z"
   }
   ```
   Response:
   ```json
   {
     "mosaics": [
       {
         "id": 1,
         "name": "mosaic_2025-10-24T13:00:00_1h",
         "start_time": "2025-10-24T13:00:00Z",
         "end_time": "2025-10-24T14:00:00Z",
         "status": "completed",
         "source_count": 1250,
         "noise_jy": 0.0005,
         "image_count": 10,
         "thumbnail_path": "/api/mosaics/1/thumbnail"
       }
     ],
     "total": 1
   }
   ```

2. **`POST /api/mosaics/create`** - Create new mosaic
   ```json
   {
     "start_time": "2025-10-24T13:00:00Z",
     "end_time": "2025-10-24T14:00:00Z"
   }
   ```

**For Astronomers:** Mosaics combine multiple 5-minute images into a single 1-hour image covering a wider area. You can query existing mosaics by time range or create new ones. The mosaic status shows whether it's still being built (`in_progress`) or ready for analysis (`completed`).

**For Developers:** Mosaic creation is asynchronous - the API returns immediately with a `pending` status, and the frontend polls for updates. The mosaic generation workflow processes groups of 10 Measurement Sets in a sliding window pattern.

### 5. Source Monitoring (`/sources`)

**Purpose:** Per-source flux timeseries monitoring and variability detection

**Component Structure:**

```typescript
// frontend/src/pages/SourceMonitoringPage.tsx

export default function SourceMonitoringPage() {
  const [sourceId, setSourceId] = useState('');
  const [searchRequest, setSearchRequest] = useState(null);
  
  const { data, isLoading } = useSourceSearch(searchRequest);
  
  const columnDefs = useMemo(() => [
    {
      field: 'source_id',
      headerName: 'Source ID',
      width: 200,
      pinned: 'left',
      cellStyle: { fontFamily: 'monospace' },
    },
    {
      field: 'mean_flux_jy',
      headerName: 'Mean Flux (mJy)',
      valueFormatter: (params) => (params.value * 1000).toFixed(2),
    },
    {
      field: 'chi_sq_nu',
      headerName: 'χ²/ν',
      cellStyle: (params) => {
        if (params.value && params.value > 5) {
          return { backgroundColor: 'rgba(244, 67, 54, 0.1)' };
        }
        return undefined;
      },
    },
    {
      field: 'is_variable',
      headerName: 'Variable?',
      cellRenderer: (params) => (
        <span style={{ color: params.value ? '#f44336' : '#4caf50' }}>
          {params.value ? '✓ Yes' : '− No'}
        </span>
      ),
    },
  ], []);
  
  return (
    <Container>
      {/* Search Interface */}
      <Paper>
        <TextField
          label="Source ID (e.g., NVSS J123456.7+420312)"
          value={sourceId}
          onChange={(e) => setSourceId(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        />
        <Button onClick={handleSearch}>Search</Button>
      </Paper>
      
      {/* AG Grid Table */}
      <Paper>
        <AgGridReact
          rowData={data?.sources || []}
          columnDefs={columnDefs}
          pagination={true}
          paginationPageSize={20}
          loading={isLoading}
        />
      </Paper>
      
      {/* Flux Timeseries Chart */}
      {selectedSource && (
        <FluxChartPanel sourceId={selectedSource.source_id} />
      )}
    </Container>
  );
}
```

**API Endpoints:**

1. **`POST /api/sources/search`** - Search sources
   ```json
   {
     "source_id": "NVSS J123456.7+420312"
   }
   ```
   Response:
   ```json
   {
     "sources": [
       {
         "source_id": "NVSS J123456.7+420312",
         "ra_deg": 188.736,
         "dec_deg": 42.053,
         "catalog": "NVSS",
         "mean_flux_jy": 0.085,
         "std_flux_jy": 0.012,
         "chi_sq_nu": 7.3,
         "is_variable": true,
         "flux_points": [
           {
             "mjd": 60238.5,
             "time": "2025-10-24T12:00:00Z",
             "flux_jy": 0.125,
             "flux_err_jy": 0.008
           }
         ]
       }
     ],
     "total": 1
   }
   ```

2. **`GET /api/sources/{source_id}/timeseries`** - Get flux timeseries
   ```json
   {
     "source_id": "NVSS J123456.7+420312",
     "flux_points": [
       {
         "mjd": 60238.5,
         "time": "2025-10-24T12:00:00Z",
         "flux_jy": 0.125,
         "flux_err_jy": 0.008,
         "image_id": "img_123"
       }
     ],
     "mean_flux_jy": 0.085,
     "std_flux_jy": 0.012,
     "chi_sq_nu": 7.3
   }
   ```

**For Astronomers:** This page lets you search for sources by NVSS ID and view their flux light curves. The `χ²/ν` (reduced chi-squared) statistic tests whether the source is consistent with constant flux - values >5 indicate significant variability. Sources with `is_variable: true` are candidates for extreme scattering events.

**For Developers:** AG Grid provides high-performance rendering for large datasets (10,000+ rows). The flux timeseries data is displayed using Plotly.js for interactive zooming and panning.

### 6. Sky View (`/sky`)

**Purpose:** FITS image viewer and sky navigation

**Component Structure:**

```typescript
// frontend/src/pages/SkyViewPage.tsx

export default function SkyViewPage() {
  const [selectedImage, setSelectedImage] = useState<ImageInfo | null>(null);
  const [catalogOverlayVisible, setCatalogOverlayVisible] = useState(false);
  
  const fitsUrl = selectedImage
    ? `/api/images/${selectedImage.id}/fits`
    : null;
  
  return (
    <Container>
      <Grid container spacing={3}>
        {/* Image Browser Sidebar */}
        <Grid item xs={12} md={4}>
          <ImageBrowser
            onSelectImage={setSelectedImage}
            selectedImageId={selectedImage?.id}
          />
        </Grid>
        
        {/* Main Image Display */}
        <Grid item xs={12} md={8}>
          <Paper>
            {/* JS9 FITS Viewer */}
            <SkyViewer
              imagePath={fitsUrl}
              displayId="skyViewDisplay"
              height={600}
            />
            
            {/* Catalog Overlay Toggle */}
            <FormControlLabel
              control={
                <Switch
                  checked={catalogOverlayVisible}
                  onChange={(e) => setCatalogOverlayVisible(e.target.checked)}
                />
              }
              label="Show Catalog Overlay"
            />
            
            {catalogOverlayVisible && (
              <CatalogOverlayJS9
                displayId="skyViewDisplay"
                ra={selectedImage.center_ra_deg}
                dec={selectedImage.center_dec_deg}
                radius={1.5}
                catalog="all"
              />
            )}
            
            {/* Region Tools */}
            <RegionTools
              displayId="skyViewDisplay"
              imagePath={selectedImage.path}
            />
            
            {/* Profile Tool */}
            <ProfileTool
              displayId="skyViewDisplay"
              imagePath={selectedImage.path}
            />
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}
```

**JS9 Integration:**

JS9 is a JavaScript FITS image viewer used throughout radio astronomy. The dashboard integrates JS9 for interactive FITS viewing:

```typescript
// frontend/src/components/Sky/SkyViewer.tsx

export default function SkyViewer({ imagePath, displayId }: SkyViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!window.JS9 || !imagePath) return;
    
    // Load FITS file into JS9 display
    window.JS9.Load(imagePath, {
      display: displayId,
      scale: 'log',
      colormap: 'grey',
    });
  }, [imagePath, displayId]);
  
  return (
    <Box
      ref={containerRef}
      id={displayId}
      sx={{ width: '100%', height: 600 }}
    />
  );
}
```

**API Endpoints:**

1. **`GET /api/images`** - List images
   ```json
   {
     "items": [
       {
         "id": 1,
         "path": "/scratch/dsa110-contimg/images/img_001.fits",
         "ms_path": "/scratch/dsa110-contimg/ms/ms_001.ms",
         "type": "pbcor",
         "beam_major_arcsec": 15.2,
         "noise_jy": 0.0005,
         "center_ra_deg": 188.736,
         "center_dec_deg": 42.053
       }
     ],
     "total": 100
   }
   ```

2. **`GET /api/images/{image_id}/fits`** - Download FITS file
   Returns FITS file binary data with appropriate headers.

**For Astronomers:** This page provides an interactive FITS viewer (JS9) for examining continuum images. You can overlay catalog sources (NVSS, VLASS, FIRST) to identify known sources, draw regions for flux measurements, and extract profiles across sources.

**For Developers:** JS9 is loaded from the `public/js9/` directory. The FITS files are served via the API with proper CORS headers. Catalog overlays are rendered as JS9 regions using the JS9 API.

### 7. QA Visualization (`/qa`)

**Purpose:** Quality assurance data visualization and exploration

**Component Structure:**

```typescript
// frontend/src/pages/QAVisualizationPage.tsx

export default function QAVisualizationPage() {
  const [tabValue, setTabValue] = useState(0);
  const [selectedFITSPath, setSelectedFITSPath] = useState<string | null>(null);
  
  return (
    <Box>
      <Tabs value={tabValue} onChange={(_, v) => setTabValue(v)}>
        <Tab label="Directory Browser" />
        <Tab label="FITS Viewer" />
        <Tab label="CASA Table Viewer" />
        <Tab label="Notebook Generator" />
      </Tabs>
      
      <TabPanel value={tabValue} index={0}>
        <DirectoryBrowser
          onSelectFile={(path, type) => {
            if (type === 'fits') {
              setSelectedFITSPath(path);
              setTabValue(1);
            }
          }}
        />
      </TabPanel>
      
      <TabPanel value={tabValue} index={1}>
        <FITSViewer path={selectedFITSPath} />
      </TabPanel>
      
      <TabPanel value={tabValue} index={2}>
        <CasaTableViewer path={selectedTablePath} />
      </TabPanel>
      
      <TabPanel value={tabValue} index={3}>
        <QANotebookGenerator />
      </TabPanel>
    </Box>
  );
}
```

**API Endpoints:**

1. **`GET /api/visualization/browse`** - Browse directories
   ```
   GET /api/visualization/browse?path=/state/qa&recursive=false
   ```
   Response:
   ```json
   {
     "path": "/state/qa/my_ms",
     "entries": [
       {
         "name": "image.fits",
         "path": "/state/qa/my_ms/image.fits",
         "type": "fits",
         "size": "2.5 MB",
         "modified_time": "2025-10-24T14:00:00Z",
         "is_dir": false
       }
     ],
     "total_files": 10,
     "total_dirs": 2
   }
   ```

2. **`GET /api/visualization/fits/view`** - FITS viewer HTML
   ```
   GET /api/visualization/fits/view?path=/state/qa/my_ms/image.fits
   ```
   Returns HTML with embedded JS9 viewer.

3. **`GET /api/visualization/casatable/view`** - CASA table viewer HTML
   ```
   GET /api/visualization/casatable/view?path=/scratch/dsa110-contimg/ms/my_ms.ms
   ```
   Returns HTML table viewer for CASA Measurement Set structure.

**For Astronomers:** This page lets you explore QA artifacts (calibration plots, flagging statistics, image quality metrics) generated during pipeline processing. You can browse directories, view FITS files, examine CASA table structures, and generate interactive Jupyter notebooks for detailed analysis.

**For Developers:** The QA visualization endpoints serve HTML viewers that can be embedded in iframes or opened in new windows. The directory browser uses recursive directory scanning with pattern matching for filtering file types.

---

## Scientific Context (Astronomer-Focused)

### What is DSA-110?

The DSA-110 (Deep Synoptic Array 110) is a radio interferometer array consisting of 110 antennas observing at ~2.8 GHz. The telescope performs a continuous survey monitoring thousands of compact radio sources for variability, with a primary science goal of detecting extreme scattering events (ESE).

### Extreme Scattering Events (ESE)

**What are ESEs?** Extreme scattering events are rapid increases in radio flux followed by gradual decreases, caused by plasma clouds in the interstellar medium passing between Earth and a compact radio source. These events provide unique probes of the interstellar medium structure.

**Why 5σ threshold?** The pipeline uses a 5σ (5 standard deviations) threshold for ESE detection. This means a source's flux must deviate from its baseline by more than 5 times the measurement uncertainty to be flagged as an ESE candidate. This threshold balances sensitivity (detecting real events) with false positive rate (avoiding noise fluctuations).

**Detection Algorithm:** The pipeline computes variability statistics (`chi_sq_nu`, `significance`) from flux timeseries. Sources with `significance >= 5` are flagged and displayed in the ESE Candidates panel.

### Calibration in Radio Astronomy

**Why calibration is critical:** Radio interferometers measure complex visibilities (amplitude and phase) that are corrupted by instrumental effects:
- **Antenna gains** - Each antenna has different sensitivity and phase response
- **Bandpass response** - Frequency-dependent gain variations
- **Delays** - Signal propagation delays between antennas

**Calibration process:**
1. **Bandpass calibration** - Solve for frequency-dependent gains using a bright calibrator source (e.g., 3C286) at transit
2. **Gain calibration** - Solve for time-dependent antenna gains using calibrator observations
3. **Application** - Apply calibration solutions to target field observations

**Validity windows:** Calibration solutions are valid for limited time ranges:
- **Bandpass:** ±12 hours around calibrator transit (changes slowly)
- **Gain:** ±30 minutes (changes rapidly with atmospheric conditions)

The calibration registry tracks these validity windows and automatically selects appropriate solutions for each observation.

### Mosaics in Radio Astronomy

**What is a mosaic?** A mosaic combines multiple individual images (tiles) into a single larger image covering a wider area of sky. Each tile is a 5-minute observation, and mosaics typically combine 10 tiles (50 minutes total) with 2-tile overlap between consecutive mosaics.

**Why mosaics?** Radio interferometers have limited field of view (set by primary beam size). To cover larger areas, multiple pointings are required. Mosaics combine these pointings with proper weighting to create seamless larger images.

**Mosaic workflow:**
1. Convert 10 Measurement Sets (5 minutes each)
2. Solve calibration on middle MS (5th of 10)
3. Apply calibration to all 10 MS files
4. Image each MS individually
5. Combine 10 images into weighted mosaic

### Measurement Sets (MS)

**What is a Measurement Set?** A Measurement Set is the standard radio astronomy data format (CASA format) containing:
- **Visibility data** - Complex amplitudes (amplitude + phase) for each baseline
- **Metadata** - Antenna positions, frequency setup, time stamps
- **Flags** - Data quality flags (bad data marked)

**Data flow:** Raw telescope data (UVH5 format) → Measurement Set → Calibrated Measurement Set → Continuum Image → Mosaic

### Source Monitoring

**Why monitor sources?** The DSA-110 survey monitors thousands of compact radio sources for variability. Sources are identified from catalogs (NVSS, VLASS, FIRST) and tracked across multiple epochs.

**Flux measurements:** For each source in each image, the pipeline measures:
- **Peak flux** - Maximum flux in source region
- **Integrated flux** - Total flux within source region
- **Flux uncertainty** - Measurement error (based on image noise)

**Variability detection:** The pipeline computes statistics across epochs:
- **Mean flux** - Average flux across all epochs
- **Standard deviation** - Flux scatter
- **χ²/ν** - Reduced chi-squared (tests constant flux hypothesis)
- **Significance** - Variability significance in sigma units

---

## Data Flow & Workflows

### Autonomous Streaming Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  1. HDF5 Group Detection (16 subband files)                 │
│     Input: /data/incoming/*.hdf5                            │
│     Action: Register group in ingest_queue                  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│  2. HDF5 → MS Conversion                                    │
│     Input: 16 subband HDF5 files                            │
│     Output: Single Measurement Set                         │
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
│  8. Sliding Window for Next Mosaic                          │
│     Trigger: 8 additional MS files (total 18)              │
│     Action: Last 2 MS from previous → first 2 of next     │
│     Repeat: Steps 4-7 for new group                        │
└─────────────────────────────────────────────────────────────┘
```

### Manual Job Workflow

```
User Action (Dashboard) → API Request → Job Queue → Pipeline Execution → Status Updates

1. User selects MS and configures parameters
2. Frontend sends POST /api/jobs/calibrate
3. Backend creates job record, returns job ID
4. Background worker processes job
5. Frontend polls GET /api/jobs/{job_id} for status
6. Job completes, status updates to "completed"
7. User views results in dashboard
```

### ESE Detection Workflow

```
1. Photometry Pipeline
   - Extract flux measurements from images
   - Store in photometry_timeseries table
   
2. Variability Analysis
   - Compute statistics (mean, std, chi²/ν)
   - Store in variability_stats table
   
3. ESE Candidate Detection
   - Query: significance >= 5
   - Insert into ese_candidates table
   
4. Dashboard Display
   - Frontend queries GET /api/ese/candidates
   - Displays in ESE Candidates panel
   - Auto-refresh every 10 seconds
```

---

## Real-Time Updates & State Management

### WebSocket Architecture

The dashboard uses WebSocket for real-time updates with HTTP polling fallback:

```typescript
// frontend/src/api/websocket.ts

export function createWebSocketClient(config: WebSocketConfig): WebSocketClient {
  const ws = new WebSocket(config.url);
  
  ws.onopen = () => {
    console.log('WebSocket connected');
    client.connected = true;
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Handle different message types
    if (data.type === 'status_update') {
      // Update React Query cache
      queryClient.setQueryData(['pipeline', 'status'], data.data.pipeline_status);
      queryClient.setQueryData(['system', 'metrics'], data.data.metrics);
      queryClient.setQueryData(['ese', 'candidates'], data.data.ese_candidates);
    }
  };
  
  ws.onerror = () => {
    // Fallback to HTTP polling
    console.warn('WebSocket error, falling back to polling');
  };
  
  return client;
}
```

**Backend WebSocket Broadcast:**

```python
# src/dsa110_contimg/api/routes.py

@app.on_event("startup")
async def start_status_broadcaster():
    async def broadcast_status():
        while True:
            await asyncio.sleep(10)  # Broadcast every 10 seconds
            
            # Fetch current status
            pipeline_status = fetch_pipeline_status()
            metrics = fetch_system_metrics()
            ese_candidates = fetch_ese_candidates()
            
            # Broadcast to all connected clients
            await manager.broadcast({
                "type": "status_update",
                "data": {
                    "pipeline_status": pipeline_status.dict(),
                    "metrics": metrics.dict(),
                    "ese_candidates": ese_candidates.dict(),
                }
            })
    
    asyncio.create_task(broadcast_status())
```

### React Query State Management

React Query provides automatic caching and background refetching:

```typescript
// Query configuration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,        // Data considered fresh for 30 seconds
      cacheTime: 300000,        // Cache kept for 5 minutes
      refetchOnWindowFocus: false,  // Don't refetch on window focus
      retry: (failureCount, error) => {
        if (failureCount >= 3) return false;
        return isRetryableError(error);
      },
      retryDelay: (attemptIndex) => {
        return Math.min(1000 * Math.pow(2, attemptIndex), 10000);
      },
    },
  },
});
```

**Query Hooks Pattern:**

```typescript
export function usePipelineStatus() {
  return useQuery({
    queryKey: ['pipeline', 'status'],
    queryFn: async () => {
      const response = await apiClient.get('/api/status');
      return response.data;
    },
    refetchInterval: 10000,  // Poll every 10 seconds
  });
}
```

**Mutation Hooks Pattern:**

```typescript
export function useStartStreaming() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post('/api/streaming/start');
      return response.data;
    },
    onSuccess: () => {
      // Invalidate streaming status to refetch
      queryClient.invalidateQueries({ queryKey: ['streaming', 'status'] });
    },
  });
}
```

---

## API Reference with Examples

### Pipeline Status Endpoints

**`GET /api/status`**
Returns pipeline queue statistics and recent observations.

**Request:**
```bash
curl http://localhost:8000/api/status
```

**Response:**
```json
{
  "queue": {
    "total": 150,
    "pending": 12,
    "in_progress": 3,
    "completed": 130,
    "failed": 5,
    "collecting": 2
  },
  "recent_groups": [
    {
      "group_id": "2025-10-24T14:00:00",
      "state": "completed",
      "received_at": "2025-10-24T14:00:00Z",
      "last_update": "2025-10-24T14:05:00Z",
      "subbands_present": 16,
      "expected_subbands": 16,
      "has_calibrator": true,
      "matches": [
        {
          "name": "3C286",
          "ra_deg": 202.784,
          "dec_deg": 30.509,
          "sep_deg": 0.5,
          "weighted_flux": 14.5
        }
      ]
    }
  ],
  "calibration_sets": [
    {
      "set_name": "bp_3c286_60238",
      "tables": [
        "/scratch/dsa110-contimg/cal/bp_3c286_60238.bpcal",
        "/scratch/dsa110-contimg/cal/bp_3c286_60238.gpcal"
      ],
      "active": 2,
      "total": 2
    }
  ],
  "matched_recent": 18
}
```

**For Astronomers:** The `queue` object shows how many observations are in each processing stage. The `recent_groups` array shows the last 20 observation groups with their processing state. The `calibration_sets` array shows active calibration solutions available for use.

**For Developers:** This endpoint queries the `ingest_queue` and `cal_registry` databases. The response is cached for 10 seconds to reduce database load. WebSocket updates invalidate this cache automatically.

### Streaming Service Endpoints

**`GET /api/streaming/status`**
Returns current streaming service status and resource usage.

**Request:**
```bash
curl http://localhost:8000/api/streaming/status
```

**Response:**
```json
{
  "running": true,
  "pid": 12345,
  "started_at": "2025-10-24T10:00:00Z",
  "uptime_seconds": 16200,
  "cpu_percent": 35.2,
  "memory_mb": 2048,
  "error": null
}
```

**`POST /api/streaming/start`**
Starts the streaming converter service.

**Request:**
```bash
curl -X POST http://localhost:8000/api/streaming/start
```

**Response:**
```json
{
  "success": true,
  "message": "Streaming service started",
  "pid": 12345
}
```

**For Developers:** The streaming service manager detects whether Docker is available and uses Docker containers if possible, otherwise falls back to direct process execution. Configuration is persisted to `state/streaming_config.json`.

### Job Management Endpoints

**`POST /api/jobs/calibrate`**
Creates a calibration job.

**Request:**
```bash
curl -X POST http://localhost:8000/api/jobs/calibrate \
  -H "Content-Type: application/json" \
  -d '{
    "ms_path": "/scratch/dsa110-contimg/ms/2025-10-24T14:00:00.ms",
    "params": {
      "field": "",
      "refant": "103",
      "solve_bandpass": true,
      "solve_gains": true,
      "gain_solint": "inf",
      "gain_calmode": "ap",
      "auto_fields": true,
      "min_pb": 0.5
    }
  }'
```

**Response:**
```json
{
  "id": 1,
  "type": "calibrate",
  "status": "pending",
  "ms_path": "/scratch/dsa110-contimg/ms/2025-10-24T14:00:00.ms",
  "params": {...},
  "created_at": "2025-10-24T14:00:00Z"
}
```

**For Astronomers:** This endpoint lets you manually run calibration when the autonomous pipeline needs intervention. The `refant` parameter specifies the reference antenna (usually "103" for DSA-110). The `gain_solint` parameter controls solution interval ("inf" means one solution for entire observation).

**For Developers:** Jobs are processed asynchronously by background workers. The API returns immediately with a job ID, and clients poll `GET /api/jobs/{job_id}` for status updates.

### Source Monitoring Endpoints

**`POST /api/sources/search`**
Searches for sources by ID or coordinates.

**Request:**
```bash
curl -X POST http://localhost:8000/api/sources/search \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "NVSS J123456.7+420312"
  }'
```

**Response:**
```json
{
  "sources": [
    {
      "source_id": "NVSS J123456.7+420312",
      "ra_deg": 188.736,
      "dec_deg": 42.053,
      "catalog": "NVSS",
      "mean_flux_jy": 0.085,
      "std_flux_jy": 0.012,
      "chi_sq_nu": 7.3,
      "is_variable": true,
      "flux_points": [
        {
          "mjd": 60238.5,
          "time": "2025-10-24T12:00:00Z",
          "flux_jy": 0.125,
          "flux_err_jy": 0.008,
          "image_id": "img_123"
        }
      ]
    }
  ],
  "total": 1
}
```

**For Astronomers:** This endpoint returns source information including flux timeseries. The `chi_sq_nu` field tests whether the source is consistent with constant flux (values >5 indicate variability). The `flux_points` array contains the light curve data.

**For Developers:** This endpoint queries the `master_sources` and `photometry_timeseries` databases. The response includes pre-computed variability statistics from the `variability_stats` table.

---

## Component Implementation Details

### Error Handling

The dashboard uses a comprehensive error handling strategy:

```typescript
// frontend/src/utils/errorUtils.ts

export function classifyError(error: AxiosError): ErrorClassification {
  if (!error.response) {
    // Network error
    return {
      type: 'network',
      retryable: true,
      userMessage: 'Network error. Please check your connection.',
    };
  }
  
  const status = error.response.status;
  
  if (status >= 500) {
    // Server error - retryable
    return {
      type: 'server',
      retryable: true,
      userMessage: 'Server error. Please try again.',
    };
  }
  
  if (status === 404) {
    return {
      type: 'not_found',
      retryable: false,
      userMessage: 'Resource not found.',
    };
  }
  
  // ... more classifications ...
}
```

### Loading States

Components use consistent loading state patterns:

```typescript
export default function MyComponent() {
  const { data, isLoading, error } = useMyQuery();
  
  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
        <Typography sx={{ ml: 2 }}>Loading...</Typography>
      </Box>
    );
  }
  
  if (error) {
    return (
      <Alert severity="error">
        {getUserFriendlyMessage(error)}
      </Alert>
    );
  }
  
  if (!data) {
    return <Alert severity="info">No data available</Alert>;
  }
  
  // Render component with data
  return <div>{/* ... */}</div>;
}
```

### Form Handling

Forms use controlled components with validation:

```typescript
const [formData, setFormData] = useState({
  refant: '103',
  solve_bandpass: true,
  solve_gains: true,
});

const handleSubmit = async () => {
  try {
    await mutation.mutateAsync(formData);
    showSuccess('Job submitted successfully');
  } catch (error) {
    showError(getUserFriendlyMessage(error));
  }
};

return (
  <form onSubmit={handleSubmit}>
    <TextField
      value={formData.refant}
      onChange={(e) => setFormData({ ...formData, refant: e.target.value })}
      error={!formData.refant}
      helperText={!formData.refant ? 'Reference antenna required' : ''}
    />
    {/* ... more fields ... */}
  </form>
);
```

---

## Production Readiness

### Current Status

**Implemented Features:**
- ✓ Complete dashboard UI (8 pages)
- ✓ 100+ API endpoints
- ✓ Real-time updates (WebSocket + polling)
- ✓ Streaming service control
- ✓ Manual job execution
- ✓ Data exploration (mosaics, sources, images)
- ✓ QA visualization

**Testing Status:**
- Unit tests for critical components
- Integration tests for API endpoints
- End-to-end workflow testing needed

**Performance:**
- API response times: <100ms for most endpoints
- Frontend rendering: Optimized with React Query caching
- Database queries: Indexed for fast lookups

### Known Limitations

1. **Mosaic Generation:** End-to-end workflow needs validation
2. **Error Handling:** Some error messages could be more informative
3. **Mobile Responsiveness:** Some pages need mobile optimization
4. **Documentation:** API documentation needs completion

### Next Steps

1. **End-to-End Testing:** Validate complete streaming → mosaic workflow
2. **Performance Optimization:** Optimize slow database queries
3. **Error Handling:** Improve error messages and recovery
4. **Documentation:** Complete API documentation and user guides

---

## Conclusion

The DSA-110 Continuum Imaging Pipeline Dashboard provides a comprehensive, production-ready interface for monitoring and controlling an autonomous radio astronomy data processing pipeline. With 100+ API endpoints, 8 major pages, and extensive visualization capabilities, the dashboard serves both frontend developers (with modern React patterns and TypeScript type safety) and radio astronomers (with scientific context and domain-specific features).

**Key Strengths:**
- Modern technology stack (React 18, TypeScript, FastAPI)
- Comprehensive error handling and retry logic
- Real-time updates via WebSocket
- Extensive data exploration capabilities
- Scientific accuracy (proper calibration workflows, ESE detection)

**Areas for Enhancement:**
- End-to-end workflow validation
- Performance optimization
- Enhanced error recovery
- Expanded documentation

The dashboard is ready for production deployment with focused testing and validation of the end-to-end streaming → mosaic workflow.

