# DSA-110 Dashboard: Frontend Architecture & Implementation

**Date:** 2025-01-XX  
**Status:** Consolidated frontend architecture documentation  
**Audience:** Frontend developers, architects

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Technology Stack](#technology-stack)
3. [Component Architecture](#component-architecture)
4. [Routing & Navigation](#routing--navigation)
5. [State Management](#state-management)
6. [API Integration Layer](#api-integration-layer)
7. [Real-Time Updates](#real-time-updates)
8. [Styling & Theming](#styling--theming)
9. [Build & Development](#build--development)
10. [Performance Optimization](#performance-optimization)

---

## Project Structure

### Directory Layout

```
frontend/
├── src/
│   ├── api/                    # API client & React Query hooks
│   │   ├── client.ts          # Axios instance with interceptors
│   │   ├── queries.ts         # React Query hooks (1500+ lines)
│   │   ├── types.ts           # TypeScript interfaces (790 lines)
│   │   ├── websocket.ts       # WebSocket/SSE client
│   │   └── circuitBreaker.ts  # Circuit breaker pattern
│   ├── components/            # React components
│   │   ├── Dashboard/         # Dashboard-specific components
│   │   ├── Sky/               # Sky/image gallery components
│   │   ├── Sources/           # Source monitoring components
│   │   ├── Observing/          # Telescope status components
│   │   ├── Health/            # System health components
│   │   ├── QA/                # QA visualization components
│   │   └── shared/            # Shared/reusable components
│   ├── pages/                 # Page-level components
│   │   ├── DashboardPage.tsx
│   │   ├── ControlPage.tsx
│   │   ├── MosaicGalleryPage.tsx
│   │   ├── SourceMonitoringPage.tsx
│   │   ├── SkyViewPage.tsx
│   │   ├── StreamingPage.tsx
│   │   ├── QAVisualizationPage.tsx
│   │   └── ...
│   ├── contexts/              # React contexts
│   │   └── NotificationContext.tsx
│   ├── hooks/                 # Custom React hooks
│   ├── theme/                 # MUI theme configuration
│   │   └── darkTheme.ts
│   ├── utils/                 # Utility functions
│   │   ├── errorUtils.ts      # Error classification
│   │   └── logger.ts          # Logging utilities
│   ├── App.tsx                # Main app component
│   └── main.tsx               # Entry point
├── public/                    # Static assets
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

### Key Files

**`src/App.tsx`** - Main application component
- Sets up React Query client
- Configures routing (React Router v6)
- Applies Material-UI theme
- Provides error boundaries
- Sets up notification context

**`src/api/queries.ts`** - React Query hooks (1500+ lines)
- All API data fetching hooks
- Real-time query hooks with WebSocket integration
- Mutation hooks for data updates
- Query key management

**`src/api/client.ts`** - Axios API client
- Base URL configuration
- Request/response interceptors
- Circuit breaker integration
- Retry logic with exponential backoff
- Error classification

**`src/api/websocket.ts`** - WebSocket/SSE client
- WebSocket connection management
- SSE fallback support
- Automatic reconnection with exponential backoff
- Message handler registration
- Ping/pong keepalive

---

## Technology Stack

### Core Framework

- **React 18** - Component-based UI library
- **TypeScript** - Type safety throughout
- **Vite 7** - Fast build tool and dev server

### UI Library

- **Material-UI (MUI) v6** - Component library
- **MUI X Date Pickers** - Date/time selection
- **Dark theme** - Default theme for astronomers

### State Management

- **TanStack React Query** - Server state management
  - Automatic caching
  - Background refetching
  - Optimistic updates
  - Query invalidation

### Routing

- **React Router v6** - Client-side routing
- **Basename support** - `/ui` prefix for production

### Data Visualization

- **Plotly.js** - Interactive scientific plots
- **D3.js** - Custom visualizations
- **AG Grid Community** - High-performance data tables

### HTTP Client

- **Axios** - HTTP requests with interceptors
- **Circuit breaker** - Prevent cascading failures
- **Retry logic** - Exponential backoff

### Real-Time Communication

- **WebSocket** - Primary real-time updates
- **Server-Sent Events (SSE)** - Fallback mechanism
- **HTTP Polling** - Final fallback

### Build & Development

- **Vite** - Fast HMR and builds
- **TypeScript** - Type checking
- **ESLint** - Code linting

---

## Component Architecture

### Page Components

Each page is a top-level component that:
- Uses React Query hooks for data fetching
- Composes smaller components
- Handles page-specific state
- Provides error boundaries

**Example Structure:**
```typescript
export default function DashboardPage() {
  const { data: status } = usePipelineStatus();
  const { data: metrics } = useSystemMetrics();
  
  return (
    <Box>
      <PipelineStatusPanel status={status} />
      <SystemHealthPanel metrics={metrics} />
      <ESECandidatesPanel />
      <PointingVisualization />
    </Box>
  );
}
```

### Reusable Components

Components are organized by domain:
- **Dashboard/** - Pipeline status, system health
- **Sky/** - Image gallery, mosaics, sky maps
- **Sources/** - Source tables, flux timeseries
- **Observing/** - Telescope status, pointing
- **Health/** - System metrics, diagnostics
- **QA/** - QA visualization components
- **shared/** - Common UI components

### Component Patterns

**Data Fetching Pattern:**
```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ['resource', id],
  queryFn: () => apiClient.get(`/resource/${id}`),
  staleTime: 30000,
});
```

**Real-Time Pattern:**
```typescript
const { data } = useRealtimeQuery(
  ['pipeline', 'status'],
  () => apiClient.get('/status'),
  wsClient,
  10000 // poll interval
);
```

**Mutation Pattern:**
```typescript
const mutation = useMutation({
  mutationFn: (data) => apiClient.post('/resource', data),
  onSuccess: () => {
    queryClient.invalidateQueries(['resource']);
  },
});
```

---

## Routing & Navigation

### Route Configuration

**Routes defined in `App.tsx`:**
- `/` → Redirects to `/dashboard`
- `/dashboard` → DashboardPage
- `/control` → ControlPage
- `/mosaics` → MosaicGalleryPage
- `/mosaics/:mosaicId` → MosaicViewPage
- `/sources` → SourceMonitoringPage
- `/sources/:sourceId` → SourceDetailPage
- `/images/:imageId` → ImageDetailPage
- `/sky` → SkyViewPage
- `/streaming` → StreamingPage
- `/data` → DataBrowserPage
- `/data/:type/:id` → DataDetailPage
- `/qa` → QAVisualizationPage
- `/qa/carta` → QACartaPage

### Navigation Component

**`Navigation.tsx`** - Top navigation bar
- Material-UI AppBar
- Navigation links
- Active route highlighting
- Responsive design

### Basename Configuration

Production builds use `/ui` basename:
```typescript
const basename = import.meta.env.PROD ? '/ui' : undefined;
```

---

## State Management

### Server State (React Query)

**All API data managed via React Query:**
- Automatic caching
- Background refetching
- Stale-while-revalidate pattern
- Query invalidation on mutations

**Query Client Configuration:**
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 3,
      retryDelay: exponentialBackoff,
      staleTime: 30000,
      refetchOnWindowFocus: false,
    },
  },
});
```

### Local State (React useState)

**Component-local state:**
- Form inputs
- UI toggles
- Dialog open/close
- Temporary selections

### Global State (React Context)

**NotificationContext:**
- Global notification system
- Toast messages
- Error notifications
- Success confirmations

---

## API Integration Layer

### API Client (`client.ts`)

**Base Configuration:**
```typescript
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});
```

**Request Interceptor:**
- Circuit breaker check
- Request logging

**Response Interceptor:**
- Error classification
- Retry logic
- Circuit breaker updates
- User-friendly error messages

### Query Hooks (`queries.ts`)

**Data Fetching Hooks:**
- `usePipelineStatus()` - Pipeline queue status
- `useSystemMetrics()` - System health metrics
- `useESECandidates()` - ESE candidate sources
- `useMosaicQuery()` - Mosaic queries
- `useSourceSearch()` - Source search
- `useStreamingStatus()` - Streaming service status
- `useMSList()` - Measurement Set list
- `useJobs()` - Job list
- `useCalibrationQA()` - Calibration QA data
- And 50+ more hooks

**Real-Time Query Hook:**
```typescript
function useRealtimeQuery<T>(
  queryKey: string[],
  queryFn: () => Promise<T>,
  wsClient: WebSocketClient | null,
  pollInterval: number = 10000
): UseQueryResult<T>
```

**Features:**
- WebSocket subscription for real-time updates
- Automatic cache invalidation on WebSocket messages
- Polling fallback when WebSocket unavailable
- Seamless integration with React Query

### Mutation Hooks

**Data Update Hooks:**
- `useStartStreaming()` - Start streaming service
- `useStopStreaming()` - Stop streaming service
- `useCreateJob()` - Create pipeline job
- `useCreateMosaic()` - Generate mosaic
- And 20+ more mutation hooks

**Pattern:**
```typescript
const mutation = useMutation({
  mutationFn: (data) => apiClient.post('/endpoint', data),
  onSuccess: () => {
    queryClient.invalidateQueries(['related', 'queries']);
  },
});
```

### Type Definitions (`types.ts`)

**790 lines of TypeScript interfaces:**
- Mirrors backend Pydantic models
- Type-safe API calls
- IntelliSense support
- Compile-time error checking

**Example:**
```typescript
export interface PipelineStatus {
  queue: QueueStats;
  calibration_sets: CalibrationSet[];
  recent_groups: RecentGroup[];
}
```

---

## Real-Time Updates

### WebSocket Client (`websocket.ts`)

**Features:**
- Automatic reconnection with exponential backoff
- SSE fallback support
- Message handler registration
- Ping/pong keepalive (30s interval)
- Connection state tracking

**Usage:**
```typescript
const wsClient = createWebSocketClient({
  url: '/api/ws/status',
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
});

wsClient.on('status_update', (data) => {
  // Handle update
});
```

### Integration with React Query

**Real-time queries automatically:**
1. Subscribe to WebSocket messages
2. Update React Query cache on messages
3. Fall back to polling if WebSocket unavailable
4. Maintain consistent API with regular queries

**Message Types:**
- `status_update` - Pipeline status updates
- `metrics_update` - System metrics updates
- `ese_update` - ESE candidate updates

---

## Styling & Theming

### Material-UI Theme

**Dark Theme (`theme/darkTheme.ts`):**
- Optimized for astronomers (night work)
- High contrast for data visualization
- Consistent color palette
- Custom spacing and typography

**Theme Configuration:**
```typescript
export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#1976d2' },
    secondary: { main: '#dc004e' },
    // ... custom colors
  },
  typography: {
    fontFamily: 'Roboto, sans-serif',
    // ... custom typography
  },
});
```

### Component Styling

**Material-UI `sx` prop:**
- Inline styling with theme access
- Responsive breakpoints
- Theme-aware colors

**Example:**
```typescript
<Box
  sx={{
    p: 2,
    bgcolor: 'background.paper',
    borderRadius: 1,
  }}
>
```

---

## Build & Development

### Development Server

**Vite Dev Server:**
```bash
npm run dev
# Available at http://localhost:5173
```

**Features:**
- Hot Module Replacement (HMR)
- Fast refresh
- TypeScript support
- Proxy configuration for API

### Production Build

**Build Command:**
```bash
npm run build
# Output in dist/
```

**Build Features:**
- Code splitting
- Tree shaking
- Minification
- Asset optimization
- Source maps (optional)

### Environment Variables

**Development:**
- `VITE_API_BASE_URL` - Backend API URL
- `VITE_WS_URL` - WebSocket URL

**Production:**
- Served from `/ui` path
- Uses relative URLs for API

---

## Performance Optimization

### Code Splitting

**React Router lazy loading:**
```typescript
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
```

### Query Optimization

**Stale Time Configuration:**
- Reduces unnecessary refetches
- 30s default stale time
- Longer for static data

**Query Key Management:**
- Hierarchical keys for efficient invalidation
- Example: `['pipeline', 'status']`, `['sources', id]`

### Component Optimization

**React.memo for expensive components:**
```typescript
export default React.memo(ExpensiveComponent);
```

**useMemo for computed values:**
```typescript
const computed = useMemo(() => expensiveCalculation(data), [data]);
```

### Bundle Size

**Current Considerations:**
- Plotly.js is large (~2MB)
- Consider dynamic imports for less-used features
- Code splitting reduces initial load

---

## See Also

- [Backend API & Integration](./dashboard_backend_api.md) - API integration details
- [State Management & Real-Time Updates](./dashboard_state_management.md) - State management patterns
- [Error Handling & Resilience](./dashboard_error_handling.md) - Error handling strategies
- [Dashboard Pages & Features Reference](../reference/dashboard_pages_and_features.md) - Page documentation

