# DSA-110 Dashboard Frontend Analysis Summary

**Date:** 2025-11-16  
**Purpose:** Comprehensive analysis of frontend structure, patterns, and
implementation status

---

## 1. Pages Structure (`frontend/src/pages/`)

### Implemented Pages (✅)

1. **DashboardPage.tsx** (`/dashboard`)
   - Pipeline status panel with queue statistics
   - System health metrics display
   - ESE candidates panel
   - Pointing visualization component
   - Recent observations table
   - Uses: `usePipelineStatus()`, `useSystemMetrics()`

2. **ControlPage.tsx** (`/control`)
   - Multi-tab interface (Convert, Calibrate, Apply, Image)
   - MS selection and metadata display
   - Job submission forms with validation
   - Real-time job logs via SSE
   - Calibration QA panels
   - Uses: Multiple hooks (`useMSList`, `useJobs`, `useCreateCalibrateJob`,
     etc.)

3. **StreamingPage.tsx** (`/streaming`)
   - Service control (start/stop/restart)
   - Configuration management dialog
   - Resource usage monitoring
   - Queue statistics display
   - Uses: `useStreamingStatus()`, `useStreamingHealth()`,
     `useStreamingConfig()`

4. **QAVisualizationPage.tsx** (`/qa`)
   - Tabbed interface (Directory Browser, FITS Viewer, CASA Table Viewer,
     Notebook Generator)
   - File selection and navigation
   - Uses: Component-based architecture

5. **DataBrowserPage.tsx** (`/data`)
   - Tabbed interface (Staging, Published)
   - Data instance listing with filters
   - Data lineage visualization
   - Uses: `useDataInstances()`, `useDataLineage()`

### Partially Implemented Pages (🔄)

6. **SkyViewPage.tsx** (`/sky`)
   - Image browser sidebar ✅
   - JS9 FITS viewer ✅
   - Image metadata display ✅
   - Catalog overlay ✅
   - Region tools ✅
   - **Missing:** Interactive sky map (planned)

7. **SourceMonitoringPage.tsx** (`/sources`)
   - Source search functionality ✅
   - Flux timeseries charts ✅
   - **Missing:** Some advanced filtering features

8. **MosaicGalleryPage.tsx** (`/mosaics`)
   - Mosaic query and listing ✅
   - **Missing:** Full generation UI

### Detail Pages

- **ImageDetailPage.tsx** - Image detail view
- **SourceDetailPage.tsx** - Source detail view
- **DataDetailPage.tsx** - Data instance detail view
- **MosaicViewPage.tsx** - Mosaic detail view

### Additional Implemented Pages

- **ObservingPage.tsx** (`/observing`) - Telescope status, calibrator tracking
  - Uses: `usePointingHistory()`, `usePipelineStatus()`
  - Status: ✅ Implemented (modified Nov 15, 2025)
- **HealthPage.tsx** (`/health`) - System diagnostics, QA gallery
  - Uses: `useSystemMetrics()`, `usePipelineStatus()`, `useQAMetrics()`
  - Status: ✅ Implemented (modified Nov 15, 2025)

### Planned Pages (📋)

_(All previously planned pages are now implemented)_

---

## 2. Custom Hooks (`frontend/src/hooks/`)

### Available Hooks

1. **useLocalStorage.ts**
   - Type-safe localStorage wrapper
   - Handles JSON serialization/deserialization
   - Error handling with logger integration
   - Usage: `const [value, setValue] = useLocalStorage<T>(key, initialValue)`

2. **useSelectionState.test.ts**
   - Test file (implementation may be elsewhere)

### API Hooks Pattern

All API hooks are defined in `frontend/src/api/queries.ts` using React Query:

**Query Hooks (Data Fetching):**

- `usePipelineStatus()` - Pipeline queue status
- `useSystemMetrics()` - System health metrics
- `useESECandidates()` - ESE detection alerts
- `useMosaicQuery(request)` - Mosaic search
- `useMosaic(mosaicId)` - Single mosaic details
- `useSourceSearch(request)` - Source search
- `useMSList(filters)` - Measurement set listing
- `useMSMetadata(msPath)` - MS metadata
- `useImages(filters)` - Image listing
- `useJobs(limit, status)` - Job listing
- `useStreamingStatus()` - Streaming service status
- `useStreamingHealth()` - Streaming health check
- `useStreamingConfig()` - Streaming configuration
- `useDataInstances(type, status)` - Data instance listing
- `useDataLineage(dataId)` - Data lineage graph
- `usePointingHistory(days)` - Telescope pointing history
- And 30+ more specialized hooks

**Mutation Hooks (Data Modification):**

- `useCreateCalibrateJob()` - Create calibration job
- `useCreateApplyJob()` - Create apply calibration job
- `useCreateImageJob()` - Create imaging job
- `useCreateConvertJob()` - Create conversion job
- `useCreateWorkflowJob()` - Create workflow job
- `useStartStreaming()` - Start streaming service
- `useStopStreaming()` - Stop streaming service
- `useRestartStreaming()` - Restart streaming service
- `useUpdateStreamingConfig()` - Update streaming config
- `useCreateMosaic()` - Create mosaic
- And more...

**Real-Time Updates:**

- Hooks use `useRealtimeQuery()` wrapper
- WebSocket client with polling fallback
- Automatic reconnection logic
- 10-second polling interval as fallback

---

## 3. API Client & Services (`frontend/src/api/`)

### API Client (`client.ts`)

**Configuration:**

- Base URL: Handles `/ui` prefix for Docker, falls back to proxy in dev
- Timeout: 30 seconds
- Circuit breaker integration
- Automatic retry with exponential backoff (3 retries)
- Error classification and user-friendly messages

**Features:**

- Request/response interceptors
- Circuit breaker for fault tolerance
- Retry logic for transient failures
- Error classification (network, server, client, timeout)
- User-friendly error messages

### WebSocket Client (`websocket.ts`)

**Implementation:**

- WebSocket with SSE fallback
- Automatic reconnection with exponential backoff
- Message handler system (subscribe/unsubscribe)
- Ping/pong keepalive (30-second interval)
- Singleton pattern for connection management

**Usage Pattern:**

```typescript
const wsClient = getWebSocketClient();
useRealtimeQuery(["pipeline", "status"], fetchFn, wsClient, 10000);
```

### Query Hooks (`queries.ts`)

**Pattern:**

- All hooks use `@tanstack/react-query`
- Query hooks return `UseQueryResult<T>`
- Mutation hooks return `UseMutationResult<T>`
- Automatic caching and refetching
- Error handling built-in

**Real-Time Query Pattern:**

```typescript
function useRealtimeQuery<T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  wsClient: WebSocketClient | null,
  pollInterval: number = 10000
): UseQueryResult<T>;
```

---

## 4. Dependencies (`frontend/package.json`)

### Core Framework

- **React:** `^19.1.1` (latest)
- **React DOM:** `^19.1.1`
- **TypeScript:** `~5.9.3`
- **Vite:** `^4.5.14` (build tool)

### UI Framework

- **Material-UI (MUI):** `^7.3.4` ⚠️ **Version 7** (latest)
  - `@mui/material` - Core components
  - `@mui/icons-material` - Icon library
  - `@mui/x-date-pickers` - Date/time pickers
  - `@emotion/react` & `@emotion/styled` - Styling engine

### State Management

- **@tanstack/react-query:** `^5.90.5` - Server state management
- **zustand:** `^5.0.8` - Client state management (minimal usage)

### Data Visualization

- **plotly.js:** `^3.1.2` - Interactive charts
- **react-plotly.js:** `^2.6.0` - React wrapper for Plotly
- **d3:** `^7.9.0` - Data visualization utilities

### Data Grid

- **ag-grid-community:** `^34.3.0` - Advanced data grid
- **ag-grid-react:** `^34.3.0` - React wrapper

### Utilities

- **axios:** `^1.12.2` - HTTP client
- **dayjs:** `^1.11.18` - Date manipulation
- **react-router-dom:** `^7.9.4` - Routing
- **golden-layout:** `^2.6.0` - Layout manager

### Development

- **vitest:** `^2.1.8` - Testing framework
- **@testing-library/react:** `^16.1.0` - React testing utilities
- **eslint:** `^9.36.0` - Linting
- **typescript-eslint:** `^8.45.0` - TypeScript linting

---

## 5. Component Patterns

### Page Component Pattern

```typescript
export default function PageName() {
  // 1. State management
  const [localState, setLocalState] = useState();

  // 2. React Query hooks
  const { data, isLoading, error } = useQueryHook();
  const mutation = useMutationHook();

  // 3. Loading state
  if (isLoading) return <CircularProgress />;

  // 4. Error state
  if (error) return <Alert severity="error">...</Alert>;

  // 5. Main render
  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      {/* Page content */}
    </Container>
  );
}
```

### Material-UI Component Usage

**Common Components:**

- `Container` - Page wrapper with max width
- `Paper` - Elevated content sections
- `Typography` - Text with variant system
- `Box` - Layout and spacing utility
- `Stack` - Flex layout container
- `Grid` - Responsive grid system
- `Tabs` / `Tab` - Tabbed interfaces
- `Table` / `TableContainer` - Data tables
- `Button` - Actions
- `TextField` - Form inputs
- `Select` / `MenuItem` - Dropdowns
- `Chip` - Status indicators
- `Alert` - Notifications
- `CircularProgress` - Loading indicators
- `Dialog` - Modals

**Styling Pattern:**

- Uses `sx` prop for styling (not CSS modules)
- Theme-aware colors (`text.secondary`, `error.main`, etc.)
- Responsive breakpoints (`xs`, `md`, `lg`)
- Spacing system (`sx={{ p: 2, mb: 3 }}`)

### API Hook Usage Pattern

```typescript
// Query hook
const { data, isLoading, error, refetch } = useQueryHook(params);

// Mutation hook
const mutation = useMutationHook();
mutation.mutate(data, {
  onSuccess: (result) => {
    /* handle success */
  },
  onError: (error) => {
    /* handle error */
  },
});
```

---

## 6. Implementation Gaps

### Planned Features Not Yet Implemented

_(ObservingPage and HealthPage are now implemented as of Nov 15, 2025)_

1. **Advanced Sky Map Features**
   - Interactive sky map (JS9 viewer exists, map enhancements planned)
   - Advanced region editing capabilities
2. **Enhanced Source Monitoring**
   - Additional source search filters
   - Advanced flux timeseries analysis

3. **Sky View - Interactive Map**
   - Coverage visualization
   - Source density heatmap
   - Field selection on map
   - Status: 📋 Planned (JS9 viewer exists, map missing)

4. **Sources Page - Advanced Features**
   - Some filtering options
   - Batch operations
   - Export functionality
   - Status: 🔄 Partially implemented

5. **Mosaic Builder - Generation UI**
   - Progress tracking UI
   - Status indicators
   - Status: 🔄 Partially implemented (query/list exists)

### Missing Infrastructure

1. **WebSocket Integration**
   - WebSocket client exists but not fully utilized
   - Most pages use polling instead of WebSocket
   - Real-time updates limited to dashboard

2. **Error Boundaries**
   - `ErrorBoundary.tsx` exists but may not be comprehensive
   - Need to verify coverage across all pages

3. **Loading States**
   - Inconsistent loading indicators
   - Some pages lack loading states

4. **Error Handling**
   - Error messages could be more user-friendly
   - Some API errors not properly displayed

---

## 7. Key Patterns to Follow

### 1. Page Structure

- Use `Container maxWidth="xl"` for page wrapper
- Use `Paper` for content sections
- Implement loading and error states
- Use React Query hooks for data fetching

### 2. Material-UI Components

- Always use MUI v7 components (not v5 or v6)
- Use `sx` prop for styling (not CSS modules)
- Follow MUI theme system
- Use responsive breakpoints

### 3. API Integration

- Use hooks from `api/queries.ts`
- Handle loading/error states
- Use mutations for data modification
- Leverage React Query caching

### 4. State Management

- Use React Query for server state
- Use `useState` for local UI state
- Use `useLocalStorage` for persistent local state
- Avoid global state unless necessary

### 5. Type Safety

- All API types defined in `api/types.ts`
- Use TypeScript interfaces for props
- Leverage React Query type inference

### 6. Real-Time Updates

- Use `useRealtimeQuery` wrapper for real-time data
- WebSocket client handles reconnection
- Polling fallback automatically enabled

---

## 8. Recommendations

### For New Pages

1. **Follow Existing Patterns**
   - Use same page structure as `DashboardPage.tsx`
   - Implement loading/error states
   - Use Material-UI components consistently

2. **API Integration**
   - Check `api/queries.ts` for existing hooks
   - Create new hooks following existing patterns
   - Use React Query for all data fetching

3. **Component Reuse**
   - Check `components/` directory for reusable components
   - Use shared components (e.g., `GenericTable`, `ErrorBoundary`)
   - Follow component patterns from existing pages

4. **Material-UI Version**
   - Always use MUI v7 components
   - Check MUI v7 documentation for API changes
   - Use `sx` prop for styling

### For Missing Features

1. **Observing Page**
   - Create new page component
   - Use `usePointingHistory()` hook
   - Implement telescope status display
   - Add calibrator tracking table

2. **Health Page**
   - Create new page component
   - Use `useSystemMetrics()` hook
   - Implement diagnostics dashboard
   - Add QA gallery component

3. **Sky View Map**
   - Integrate mapping library (e.g., Leaflet, Mapbox)
   - Use `usePointingHistory()` for coverage
   - Implement interactive field selection
   - Add source density visualization

---

## 9. Quick Reference

### Most Used Hooks

**Data Fetching:**

- `usePipelineStatus()` - Dashboard status
- `useSystemMetrics()` - System health
- `useESECandidates()` - ESE alerts
- `useImages(filters)` - Image listing
- `useMSList(filters)` - MS listing
- `useSourceSearch(request)` - Source search

**Mutations:**

- `useCreateCalibrateJob()` - Calibration
- `useCreateImageJob()` - Imaging
- `useCreateConvertJob()` - Conversion
- `useStartStreaming()` - Service control

### Most Used Components

- `Container` - Page wrapper
- `Paper` - Content sections
- `Typography` - Text
- `Box` - Layout
- `Stack` - Flex layout
- `Table` - Data display
- `Button` - Actions
- `TextField` - Inputs
- `Alert` - Notifications
- `CircularProgress` - Loading

### File Locations

- **Pages:** `frontend/src/pages/`
- **Components:** `frontend/src/components/`
- **API Hooks:** `frontend/src/api/queries.ts`
- **API Client:** `frontend/src/api/client.ts`
- **WebSocket:** `frontend/src/api/websocket.ts`
- **Types:** `frontend/src/api/types.ts`
- **Hooks:** `frontend/src/hooks/`
- **Utils:** `frontend/src/utils/`

---

## Summary

The DSA-110 dashboard frontend is built with:

- **React 19** + **TypeScript**
- **Material-UI v7** (latest version)
- **React Query v5** for server state
- **Vite** for building
- **Axios** for HTTP requests
- **WebSocket** client for real-time updates

**Implementation Status:**

- ✅ 7 pages fully implemented (including HealthPage and ObservingPage as of Nov
  15, 2025)
- 🔄 3 pages partially implemented
- 📋 Advanced features planned (all core pages are implemented)

**Key Patterns:**

- React Query hooks for all API calls
- Material-UI components throughout
- Consistent page structure
- Real-time updates with WebSocket fallback
- Type-safe API integration

**Gaps:**

- Observing and Health pages not implemented
- Some advanced features missing
- WebSocket not fully utilized
- Some error handling improvements needed
