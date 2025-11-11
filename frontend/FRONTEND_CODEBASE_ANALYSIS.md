# DSA-110 Dashboard Frontend Codebase Analysis

**Date:** 2025-01-XX  
**Purpose:** Analysis of existing frontend implementation vs. documented features

---

## 1. Pages Structure (`frontend/src/pages/`)

### ✅ Implemented Pages

1. **DashboardPage.tsx** (`/dashboard`)
   - Uses: `usePipelineStatus()`, `useSystemMetrics()`
   - Components: `ESECandidatesPanel`, `PointingVisualization`
   - Status: ✅ Fully implemented

2. **ControlPage.tsx** (`/control`)
   - Job submission forms
   - MS list and selection
   - Status: ✅ Fully implemented

3. **StreamingPage.tsx** (`/streaming`)
   - Service control (start/stop/restart)
   - Status monitoring
   - Status: ✅ Fully implemented

4. **QAVisualizationPage.tsx** (`/qa`)
   - Directory browser
   - FITS viewer
   - CASA table viewer
   - Status: ✅ Fully implemented

5. **QACartaPage.tsx** (`/qa/carta`)
   - Alternative QA viewer
   - Status: ✅ Implemented

6. **DataBrowserPage.tsx** (`/data`)
   - Data product browser
   - Status: ✅ Fully implemented

7. **DataDetailPage.tsx** (`/data/:type/:id`)
   - Data detail view
   - Status: ✅ Implemented

8. **SkyViewPage.tsx** (`/sky`)
   - Image gallery (basic)
   - JS9 viewer integration
   - Image browser sidebar
   - Status: 🔄 Partially implemented (matches docs)

9. **MosaicGalleryPage.tsx** (`/mosaics`)
   - Mosaic query and list
   - Status: ✅ Implemented

10. **MosaicViewPage.tsx** (`/mosaics/:mosaicId`)
    - Mosaic detail view
    - Status: ✅ Implemented

11. **SourceMonitoringPage.tsx** (`/sources`)
    - Source search
    - AG Grid table
    - Status: 🔄 Partially implemented (matches docs)

12. **SourceDetailPage.tsx** (`/sources/:sourceId`)
    - Source detail view
    - Flux timeseries
    - Status: 🔄 Partially implemented (matches docs)

13. **ImageDetailPage.tsx** (`/images/:imageId`)
    - Image detail view
    - Status: ✅ Implemented

### 📋 Missing Pages (Planned but Not Implemented)

1. **ObservingPage.tsx** (`/observing`)
   - Telescope status display
   - Pointing history visualization
   - Calibrator tracking
   - Status: 📋 Not implemented (empty `components/Observing/` directory)

2. **HealthPage.tsx** (`/health`)
   - System diagnostics
   - Queue monitoring
   - QA diagnostic gallery
   - Status: 📋 Not implemented (empty `components/Health/` directory)

---

## 2. Custom Hooks (`frontend/src/hooks/`)

### Available Custom Hooks

1. **useLocalStorage.ts**
   - Type-safe localStorage wrapper
   - Handles SSR (returns initialValue on server)
   - Error handling with logger

2. **useSelectionState.test.ts**
   - Test file (implementation likely in utils/)

### Note on React Query Hooks

All API hooks are in `frontend/src/api/queries.ts` (not in `hooks/` directory). See Section 3 for complete list.

---

## 3. API Client & WebSocket (`frontend/src/api/`)

### API Client (`client.ts`)

**Features:**
- Axios-based client with interceptors
- Circuit breaker pattern (`circuitBreaker.ts`)
- Retry logic with exponential backoff (3 retries: 1s, 2s, 4s)
- Error classification (`errorUtils.ts`)
- User-friendly error messages
- Base URL handling for dev/prod

**Configuration:**
- Timeout: 30 seconds
- Circuit breaker: 5 failures threshold, 30s reset timeout
- Retry: Up to 3 attempts for retryable errors

### WebSocket Client (`websocket.ts`)

**Features:**
- WebSocket client with SSE fallback
- Automatic reconnection with exponential backoff
- Message handler system (subscribe/unsubscribe)
- Ping/pong keepalive (30s interval)
- Connection state tracking

**Usage Pattern:**
```typescript
const wsClient = createWebSocketClient({
  url: wsUrl,
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
  useSSE: false,
});
wsClient.connect();
wsClient.on('status_update', (data) => { ... });
```

### React Query Hooks (`queries.ts`)

**69+ hooks available** organized by feature:

#### Pipeline Status & Metrics
- `usePipelineStatus()` - Pipeline queue status (real-time)
- `useSystemMetrics()` - System health metrics (real-time)
- `useESECandidates()` - ESE detection alerts (real-time)
- `useAlertHistory(limit)` - Alert history

#### Mosaics
- `useMosaicQuery(request)` - Query mosaics by time range
- `useMosaic(mosaicId)` - Get mosaic details
- `useCreateMosaic()` - Create new mosaic (mutation)

#### Sources
- `useSourceSearch(request)` - Search sources
- `useSourceDetail(sourceId)` - Get source details
- `useSourceDetections(sourceId)` - Get source detections

#### Control Panel (MS & Jobs)
- `useMSList(filters?)` - List Measurement Sets
- `useDiscoverMS()` - Discover MS files (mutation)
- `useMSMetadata(msPath)` - Get MS metadata
- `useCalibratorMatches(msPath)` - Get calibrator matches
- `useJobs(limit, status?)` - List jobs
- `useJob(jobId)` - Get job details
- `useCreateCalibrateJob()` - Create calibration job (mutation)
- `useCreateApplyJob()` - Create apply job (mutation)
- `useCreateImageJob()` - Create imaging job (mutation)
- `useCreateWorkflowJob()` - Create workflow job (mutation)
- `useCreateConvertJob()` - Create conversion job (mutation)

#### Calibration
- `useCalTables(calDir?)` - List calibration tables
- `useExistingCalTables(msPath)` - Get existing cal tables for MS
- `useValidateCalTable()` - Validate cal table (mutation)
- `useCalibrationQA(msPath)` - Get calibration QA
- `useBandpassPlots(msPath)` - Get bandpass plots

#### Images
- `useImages(filters?)` - List images with filters
- `useImageDetail(imageId)` - Get image details
- `useImageMeasurements(imageId)` - Get image measurements
- `useImageQA(msPath)` - Get image QA

#### Streaming Service
- `useStreamingStatus()` - Get service status
- `useStreamingHealth()` - Get health check
- `useStreamingConfig()` - Get configuration
- `useStreamingMetrics()` - Get processing metrics
- `useStartStreaming()` - Start service (mutation)
- `useStopStreaming()` - Stop service (mutation)
- `useRestartStreaming()` - Restart service (mutation)
- `useUpdateStreamingConfig()` - Update config (mutation)

#### Pointing
- `usePointingMonitorStatus()` - Get pointing monitor status
- `usePointingHistory(startMjd, endMjd)` - Get pointing history

#### Data Browser
- `useDataInstances(filters?)` - List data instances
- `useDataInstance(dataId)` - Get data instance details
- `useAutoPublishStatus(dataId)` - Get auto-publish status
- `useDataLineage(dataId)` - Get data lineage

#### Catalog & Regions
- `useCatalogValidation(msPath)` - Get catalog validation
- `useCatalogOverlay(msPath)` - Get catalog overlay data
- `useRunCatalogValidation()` - Run validation (mutation)
- `useCatalogOverlayByCoords(ra, dec, radius)` - Get overlay by coordinates
- `useRegions(imagePath)` - List regions
- `useCreateRegion()` - Create region (mutation)
- `useUpdateRegion()` - Update region (mutation)
- `useDeleteRegion()` - Delete region (mutation)
- `useRegionStatistics(regionId)` - Get region statistics

#### Image Analysis
- `useProfileExtraction()` - Extract profile (mutation)
- `useImageFitting()` - Fit image (mutation)

#### QA Visualization
- `useDirectoryListing(path)` - Browse directories
- `useDirectoryThumbnails(path)` - Get directory thumbnails
- `useFITSInfo(path)` - Get FITS file info
- `useCasaTableInfo(path)` - Get CASA table info
- `useGenerateNotebook()` - Generate QA notebook (mutation)
- `useRunQA()` - Run QA analysis (mutation)
- `useQAMetrics(msPath)` - Get QA metrics

#### Batch Jobs
- `useBatchJobs(limit, status?)` - List batch jobs
- `useBatchJob(batchId)` - Get batch job details
- `useCreateBatchCalibrateJob()` - Create batch calibrate job (mutation)
- `useCreateBatchApplyJob()` - Create batch apply job (mutation)
- `useCreateBatchImageJob()` - Create batch image job (mutation)
- `useCancelBatchJob()` - Cancel batch job (mutation)

#### UVH5 Files
- `useUVH5Files(inputDir?)` - List UVH5 files

**Real-Time Query Pattern:**
```typescript
function useRealtimeQuery<T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  wsClient: WebSocketClient | null,
  pollInterval: number = 10000
): UseQueryResult<T>
```

- Automatically subscribes to WebSocket updates
- Falls back to polling if WebSocket unavailable
- Updates React Query cache on WebSocket messages

---

## 4. Dependencies (`frontend/package.json`)

### Core Framework
- **React:** `^19.1.1` (latest)
- **React DOM:** `^19.1.1`
- **TypeScript:** `~5.9.3`

### UI Framework
- **Material-UI (MUI):** `^7.3.4` ✅ **Version 7** (not v6 as docs suggest)
- **@mui/icons-material:** `^7.3.4`
- **@mui/x-date-pickers:** `^8.15.0`
- **@emotion/react:** `^11.14.0`
- **@emotion/styled:** `^11.14.1`

### State Management & Data Fetching
- **@tanstack/react-query:** `^5.90.5` (React Query v5)
- **@tanstack/react-query-devtools:** `^5.62.0`
- **zustand:** `^5.0.8` (state management)

### Routing
- **react-router-dom:** `^7.9.4` (v7, latest)

### Data Visualization
- **plotly.js:** `^3.1.2`
- **react-plotly.js:** `^2.6.0`
- **d3:** `^7.9.0`
- **ag-grid-community:** `^34.3.0`
- **ag-grid-react:** `^34.3.0`

### HTTP Client
- **axios:** `^1.12.2`

### Utilities
- **dayjs:** `^1.11.18` (date handling)
- **golden-layout:** `^2.6.0` (layout manager)

### Build Tools
- **vite:** `^4.5.14`
- **vitest:** `^2.1.8` (testing)

### Testing
- **@testing-library/react:** `^16.1.0`
- **@testing-library/jest-dom:** `^6.6.3`
- **@testing-library/user-event:** `^14.5.2`

---

## 5. Component Patterns

### Page Component Pattern

```typescript
import { Container, Typography, Paper, Box, CircularProgress, Alert } from '@mui/material';
import { useSomeQuery } from '../api/queries';

export default function SomePage() {
  const { data, isLoading, error } = useSomeQuery();

  if (isLoading) {
    return (
      <Container maxWidth="xl" sx={{ py: 8, textAlign: 'center' }}>
        <CircularProgress />
        <Typography variant="body1" sx={{ mt: 2 }}>Loading...</Typography>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="xl" sx={{ py: 4 }}>
        <Alert severity="error">Error message</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Page content */}
    </Container>
  );
}
```

### Key Patterns Observed

1. **Error Handling:**
   - Loading states with `CircularProgress`
   - Error states with `Alert` component
   - Error boundaries (`ErrorBoundary.tsx`)

2. **Layout:**
   - `Container maxWidth="xl"` for page containers
   - `Paper` components for panels
   - `Stack` for vertical/horizontal layouts
   - `Grid` for responsive layouts

3. **Data Fetching:**
   - React Query hooks from `api/queries.ts`
   - Conditional rendering based on `isLoading` and `error`
   - Real-time updates via WebSocket integration

4. **Styling:**
   - Material-UI `sx` prop for styling
   - Dark theme (`darkTheme.ts`)
   - Responsive breakpoints (`xs`, `sm`, `md`, `lg`, `xl`)

5. **Navigation:**
   - React Router v7
   - `Navigation` component with AppBar
   - Active route highlighting

---

## 6. Material-UI Version & Components

### Version Discrepancy

**Documentation says:** Material-UI v6  
**Actual version:** Material-UI v7.3.4 ✅

**Note:** MUI v7 is the latest version and is backward compatible with v6 patterns. The codebase uses v7 features.

### Available MUI Components (Based on Usage)

**Layout:**
- `Container`, `Box`, `Stack`, `Grid`, `Paper`

**Navigation:**
- `AppBar`, `Toolbar`, `Drawer`, `Button`, `IconButton`

**Data Display:**
- `Typography`, `Alert`, `Chip`, `Card`, `CardContent`

**Feedback:**
- `CircularProgress`, `LinearProgress`, `Snackbar`, `Dialog`

**Inputs:**
- `TextField`, `Select`, `Switch`, `Checkbox`, `Radio`

**Date Pickers:**
- `@mui/x-date-pickers` components (DateTimePicker, DatePicker)

**Icons:**
- `@mui/icons-material` (comprehensive icon set)

---

## 7. Gaps: Implemented vs. Planned Features

### ✅ Fully Implemented (Matches Docs)

1. **Dashboard Page** - All features implemented
2. **Control Page** - All features implemented
3. **Streaming Page** - All features implemented
4. **QA Visualization Page** - All features implemented
5. **Data Browser Page** - All features implemented

### 🔄 Partially Implemented (Matches Docs Status)

1. **Sky View Page** (`/sky`)
   - ✅ Image gallery (basic)
   - ✅ Image detail view (JS9 viewer)
   - ✅ Mosaic builder (query/list)
   - 📋 Interactive sky map (planned, not implemented)
   - 🔄 Advanced filtering (partial)

2. **Sources Page** (`/sources`)
   - ✅ Source search
   - ✅ Source table (AG Grid)
   - 🔄 Source detail view (basic exists, advanced features planned)
   - ✅ Flux timeseries display
   - 🔄 Variability statistics (partial)
   - 🔄 Advanced filtering (partial)

### 📋 Missing Pages (Planned but Not Implemented)

1. **Observing Page** (`/observing`)
   - 📋 Telescope status display
   - 📋 Pointing history visualization
   - 📋 Calibrator tracking
   - 📋 Observing plan display
   - **Status:** Empty `components/Observing/` directory exists

2. **Health Page** (`/health`)
   - 📋 System diagnostics
   - 📋 Queue monitoring
   - 📋 QA diagnostic gallery
   - 📋 Performance metrics
   - **Status:** Empty `components/Health/` directory exists

### 🔄 Partially Implemented Features

1. **Real-Time Updates**
   - ✅ HTTP polling (10s intervals)
   - ✅ WebSocket client (basic connection)
   - 🔄 WebSocket integration with React Query (in progress)
   - 📋 SSE fallback (planned, but SSE support exists in WebSocket client)
   - 📋 Connection state UI indicators (planned)

2. **ESE Detection**
   - ✅ Auto-flagging (>5σ threshold)
   - ✅ Candidate list display
   - ✅ Real-time updates
   - 🔄 Slack notification integration (in progress)
   - 📋 User-configurable thresholds (planned)

3. **Mosaic Features**
   - ✅ Mosaic query by time range
   - ✅ Mosaic list display
   - ✅ Mosaic detail view
   - 🔄 Mosaic generation UI (in progress)
   - 📋 Mosaic preview coverage map (planned)

4. **Image Features**
   - ✅ Image gallery (basic)
   - ✅ Image detail view with JS9
   - ✅ FITS file download
   - 🔄 Advanced image metadata display (partial)
   - 📋 Image comparison tools (planned)

5. **Source Monitoring**
   - ✅ Source search
   - ✅ Source table with AG Grid
   - ✅ Basic source detail view
   - ✅ Flux timeseries display
   - 🔄 Advanced variability statistics (partial)
   - 🔄 Advanced filtering (partial)
   - 📋 Source comparison tools (planned)

### 📋 Missing API Endpoints (Referenced in Docs but Not Found)

1. **Observing:**
   - `GET /api/observing/status` - Telescope status
   - `GET /api/observing/pointing` - Pointing history (but `usePointingHistory` exists)
   - `GET /api/calibrator_matches` - Calibrator detection history (but `useCalibratorMatches` exists)

2. **Health:**
   - `GET /api/health/diagnostics` - System diagnostics
   - `GET /api/health/qa/gallery` - QA gallery

3. **ESE:**
   - `POST /api/ese/candidates/{id}/dismiss` - Dismiss candidate
   - `POST /api/ese/candidates/{id}/flag` - Flag candidate

---

## 8. Recommendations

### For New Development

1. **Follow Existing Patterns:**
   - Use React Query hooks from `api/queries.ts`
   - Follow page component structure (loading/error/content)
   - Use Material-UI v7 components (not v6)
   - Use `sx` prop for styling

2. **Real-Time Updates:**
   - Use `useRealtimeQuery` pattern for real-time data
   - WebSocket client is available but needs React Query integration
   - Fallback to polling is automatic

3. **Error Handling:**
   - Use `ErrorBoundary` for component errors
   - Display user-friendly error messages
   - Handle loading states consistently

4. **Missing Pages:**
   - Observing Page: Use `usePointingHistory`, `usePointingMonitorStatus`
   - Health Page: Use `useSystemMetrics`, `usePipelineStatus`, `useQAMetrics`

5. **Component Organization:**
   - Page components in `pages/`
   - Reusable components in `components/`
   - Feature-specific components in subdirectories (e.g., `components/Sky/`)

---

## Summary

### Strengths

- ✅ Comprehensive API hook library (69+ hooks)
- ✅ Robust error handling and retry logic
- ✅ WebSocket support with polling fallback
- ✅ Material-UI v7 (latest version)
- ✅ TypeScript throughout
- ✅ Well-organized component structure

### Gaps

- 📋 Observing Page not implemented
- 📋 Health Page not implemented
- 🔄 Some advanced features partially implemented
- 📋 Some API endpoints referenced in docs not found in hooks

### Version Notes

- **MUI v7** (not v6 as docs suggest) - This is fine, v7 is backward compatible
- **React Router v7** (latest)
- **React Query v5** (latest)
- **React 19** (latest)

---

**Last Updated:** 2025-01-XX

