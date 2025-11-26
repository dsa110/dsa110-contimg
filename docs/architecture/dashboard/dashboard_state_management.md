# DSA-110 Dashboard: State Management & Real-Time Updates

**Date:** 2025-11-12  
**Status:** Consolidated state management documentation  
**Audience:** Frontend developers, architects

---

## Table of Contents

1. [State Management Architecture](#state-management-architecture)
2. [React Query Integration](#react-query-integration)
3. [Real-Time Updates](#real-time-updates)
4. [WebSocket Client](#websocket-client)
5. [Polling Fallback](#polling-fallback)
6. [Cache Management](#cache-management)
7. [Optimistic Updates](#optimistic-updates)
8. [State Synchronization](#state-synchronization)

---

## State Management Architecture

### Overview

The dashboard uses a **hybrid state management approach**:

- **Server State**: Managed by TanStack React Query
- **Local State**: Managed by React `useState`
- **Global UI State**: Managed by React Context
- **Real-Time Updates**: WebSocket + SSE + Polling fallback

### State Categories

**Server State (React Query):**

- Pipeline status
- System metrics
- ESE candidates
- Source data
- Mosaic data
- Job status

**Local State (useState):**

- Form inputs
- UI toggles (dialogs, menus)
- Temporary selections
- Component-specific state

**Global UI State (Context):**

- Notifications
- Theme preferences
- User preferences

---

## React Query Integration

### Query Client Configuration

**Setup (`App.tsx`):**

```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (failureCount >= 3) return false;
        return isRetryableError(error);
      },
      retryDelay: (attemptIndex) => {
        return Math.min(1000 * Math.pow(2, attemptIndex), 10000);
      },
      refetchOnWindowFocus: false,
      staleTime: 30000, // 30 seconds
    },
    mutations: {
      retry: (failureCount, error) => {
        if (failureCount >= 1) return false;
        return isRetryableError(error);
      },
      retryDelay: 1000,
    },
  },
});
```

### Query Hooks Pattern

**Standard Query:**

```typescript
const { data, isLoading, error } = useQuery({
  queryKey: ["pipeline", "status"],
  queryFn: () => apiClient.get("/status"),
  staleTime: 30000,
});
```

**Real-Time Query:**

```typescript
const { data } = useRealtimeQuery(
  ["pipeline", "status"],
  () => apiClient.get("/status"),
  wsClient,
  10000 // poll interval
);
```

### Query Key Structure

**Hierarchical Keys:**

- `['pipeline', 'status']` - Pipeline status
- `['system', 'metrics']` - System metrics
- `['ese', 'candidates']` - ESE candidates
- `['sources', sourceId]` - Specific source
- `['mosaics', mosaicId]` - Specific mosaic

**Benefits:**

- Efficient cache invalidation
- Granular updates
- Easy debugging

---

## Real-Time Updates

### Architecture

**Three-Tier Fallback System:**

1. **WebSocket** (Primary) - Real-time bidirectional
2. **Server-Sent Events** (Fallback) - Real-time unidirectional
3. **HTTP Polling** (Final Fallback) - Periodic requests

### Update Flow

```
Backend Broadcast (every 10s)
    ↓
WebSocket/SSE Message
    ↓
Frontend WebSocket Client
    ↓
React Query Cache Update
    ↓
Component Re-render
```

---

## WebSocket Client

### Client Implementation (`websocket.ts`)

**Features:**

- Automatic reconnection with exponential backoff
- SSE fallback support
- Message handler registration
- Ping/pong keepalive (30s interval)
- Connection state tracking

**Usage:**

```typescript
const wsClient = createWebSocketClient({
  url: "/api/ws/status",
  reconnectInterval: 3000,
  maxReconnectAttempts: 10,
});

wsClient.on("status_update", (data) => {
  // Handle update
});
```

### Reconnection Strategy

**Exponential Backoff:**

```typescript
const delay = Math.min(
  reconnectInterval * Math.pow(2, reconnectAttempts - 1),
  30000 // Max 30 seconds
);
```

**Reconnection Attempts:**

- Initial: 3 seconds
- After 1 failure: 6 seconds
- After 2 failures: 12 seconds
- After 3 failures: 24 seconds
- Max: 30 seconds

---

## Polling Fallback

### Implementation

**When WebSocket Unavailable:**

```typescript
const shouldPoll = !wsClient || !wsClient.connected;

return useQuery({
  queryKey,
  queryFn,
  refetchInterval: shouldPoll ? pollInterval : false,
});
```

### Polling Intervals

**By Data Type:**

- Pipeline status: 10 seconds
- System metrics: 10 seconds
- ESE candidates: 10 seconds
- Streaming status: 5 seconds
- MS list: 30 seconds
- Jobs: 5 seconds

**Optimization:**

- Longer intervals for less critical data
- Shorter intervals for real-time monitoring
- Adaptive intervals based on connection state

---

## Cache Management

### Cache Invalidation

**Manual Invalidation:**

```typescript
queryClient.invalidateQueries(["pipeline", "status"]);
```

**After Mutations:**

```typescript
const mutation = useMutation({
  mutationFn: (data) => apiClient.post("/resource", data),
  onSuccess: () => {
    queryClient.invalidateQueries(["related", "queries"]);
  },
});
```

### Cache Updates from WebSocket

**Automatic Updates:**

```typescript
wsClient.on("status_update", (data) => {
  if (data.data?.pipeline_status) {
    queryClient.setQueryData(["pipeline", "status"], data.data.pipeline_status);
  }
  if (data.data?.metrics) {
    queryClient.setQueryData(["system", "metrics"], data.data.metrics);
  }
  if (data.data?.ese_candidates) {
    queryClient.setQueryData(["ese", "candidates"], data.data.ese_candidates);
  }
});
```

### Stale Time Strategy

**Default: 30 seconds**

- Balance between freshness and performance
- Reduces unnecessary refetches
- Allows stale-while-revalidate pattern

**Per-Query Overrides:**

- Static data: Longer stale time (5 minutes)
- Real-time data: Shorter stale time (10 seconds)

---

## Optimistic Updates

### Pattern

**Update UI Immediately:**

```typescript
const mutation = useMutation({
  mutationFn: updateSource,
  onMutate: async (newData) => {
    // Cancel outgoing queries
    await queryClient.cancelQueries(["sources", newData.id]);

    // Snapshot previous value
    const previous = queryClient.getQueryData(["sources", newData.id]);

    // Optimistically update
    queryClient.setQueryData(["sources", newData.id], newData);

    return { previous };
  },
  onError: (err, newData, context) => {
    // Rollback on error
    queryClient.setQueryData(["sources", newData.id], context.previous);
  },
  onSettled: () => {
    // Refetch to ensure consistency
    queryClient.invalidateQueries(["sources"]);
  },
});
```

### Use Cases

- Source status updates
- ESE candidate status changes
- Job creation
- Configuration updates

---

## State Synchronization

### WebSocket Message Types

**Status Updates:**

```json
{
  "type": "status_update",
  "data": {
    "pipeline_status": { ... },
    "metrics": { ... },
    "ese_candidates": { ... }
  }
}
```

**Metrics Updates:**

```json
{
  "type": "metrics_update",
  "data": {
    "cpu_percent": 45.2,
    "mem_percent": 62.8,
    ...
  }
}
```

**ESE Updates:**

```json
{
  "type": "ese_update",
  "data": {
    "candidates": [ ... ]
  }
}
```

### Synchronization Strategy

**Immediate Updates:**

- WebSocket messages update cache immediately
- No refetch required
- UI updates automatically via React Query

**Conflict Resolution:**

- Last write wins
- Server state is source of truth
- Periodic refetch ensures consistency

---

## See Also

- [Frontend Architecture](./dashboard_frontend_architecture.md) - Component
  architecture
- [Backend API & Integration](../../reference/dashboard_backend_api.md) - API
  endpoints
- [Error Handling & Resilience](./dashboard_error_handling.md) - Error handling
  patterns
