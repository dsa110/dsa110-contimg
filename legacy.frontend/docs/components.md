# Frontend Component Documentation

**Purpose:** Documentation for key React components in the DSA-110 dashboard  
**Last Updated:** 2025-11-26  
**Status:** Production

---

## Overview

The DSA-110 frontend is built with React 18, TypeScript, and Material-UI (MUI).
Components are organized by feature area:

```
src/components/
├── dashboard/       # Dashboard page components
├── images/          # Image browser components
├── pipeline/        # Pipeline control components
├── streaming/       # Streaming status components
└── common/          # Shared UI components
```

---

## Dashboard Components

### `WorkflowStatusPanel`

**Location:** `src/components/dashboard/WorkflowStatusPanel.tsx`  
**Issue:** #53 - Add Unified Workflow Status Visualization to Dashboard

A real-time visualization of the complete streaming pipeline workflow, showing
queue depths, processing status, and bottleneck detection for each stage.

#### Features

- **Pipeline Flow Visualization:** Horizontal display of all 11 pipeline stages
  connected by arrows
- **Queue Depth Display:** Color-coded chips showing pending/processing/completed
  counts per stage
- **Bottleneck Detection:** Highlights stages with high pending-to-completed
  ratios
- **Health Status:** Overall health indicator (Healthy/Degraded/Stalled)
- **Estimated Completion:** Shows ETA for clearing pending items
- **Auto-Refresh:** Updates every 15 seconds via React Query

#### Usage

```tsx
import { WorkflowStatusPanel } from "./components/dashboard/WorkflowStatusPanel";

function DashboardPage() {
  return (
    <Box>
      <WorkflowStatusPanel />
      {/* Other dashboard content */}
    </Box>
  );
}
```

#### Props

This component takes no props - it fetches data internally using the
`useWorkflowStatus()` hook.

#### API Integration

Uses the `/api/pipeline/workflow-status` endpoint via React Query:

```typescript
// From src/api/queries.ts
export function useWorkflowStatus() {
  return useQuery({
    queryKey: ["workflow-status"],
    queryFn: async () => {
      const response = await fetch("/api/pipeline/workflow-status");
      return response.json() as Promise<WorkflowStatus>;
    },
    refetchInterval: 15000, // Auto-refresh every 15s
  });
}
```

#### Response Type

```typescript
// From src/api/types.ts
interface WorkflowStageStatus {
  name: string;           // Stage identifier (e.g., "conversion")
  display_name: string;   // Human-readable name (e.g., "Conversion")
  pending: number;        // Items waiting to be processed
  processing: number;     // Items currently being processed
  completed_today: number; // Items completed in last 24h
  failed_today: number;   // Items failed in last 24h
}

interface WorkflowStatus {
  stages: WorkflowStageStatus[];
  overall_health: "healthy" | "degraded" | "stalled";
  bottleneck: string | null;          // Name of bottleneck stage, if any
  total_pending: number;
  total_completed_today: number;
  total_failed_today: number;
  estimated_completion: string | null; // ISO timestamp
}
```

#### Visual States

| Condition | Indicator |
|-----------|-----------|
| Healthy | Green success chip |
| Degraded | Yellow warning chip with bottleneck alert |
| Stalled | Red error chip |
| Loading | Skeleton placeholders |
| API Error | Error alert message |

#### Sub-Components

- **`StageCard`:** Individual stage box with queue counts and status color
- **`StageConnector`:** Arrow icon between stages
- **`HealthBadge`:** Chip showing overall health status

#### Styling

Uses MUI's `useTheme()` hook for consistent colors:
- Success (green): No activity or completed
- Info (blue): Items currently processing
- Warning (yellow): Items pending or bottleneck
- Error (red): Failed items

---

## Pipeline Components

### `PipelineControlPage`

**Location:** `src/pages/PipelineControlPage.tsx`

Main pipeline control interface with tabs for:
- **Dashboard:** Quick overview with WorkflowStatusPanel
- **Executions:** List of pipeline runs
- **Streaming:** Real-time streaming converter status
- **Settings:** Pipeline configuration

---

## Streaming Components

### `StreamingTab`

**Location:** `src/components/streaming/StreamingTab.tsx`

Real-time status of the streaming converter daemon, including:
- Queue status (collecting, pending, in_progress)
- Recent conversions with timing metrics
- Mosaic trigger status
- Auto-refresh every 10 seconds

---

## State Management

The frontend uses **React Query** for server state management:

```typescript
// Query client configuration (src/api/queryClient.ts)
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,      // 30 seconds
      gcTime: 5 * 60_000,     // 5 minutes
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});
```

### Key Hooks

| Hook | Endpoint | Description |
|------|----------|-------------|
| `useWorkflowStatus()` | `/api/pipeline/workflow-status` | Workflow stage queue depths |
| `useStreamingStatus()` | `/api/streaming/status` | Streaming converter status |
| `useImages()` | `/api/images` | Image browser data |
| `useJobs()` | `/api/jobs` | Job queue data |

---

## Best Practices

1. **Use React Query hooks** for API data - avoid manual `fetch()` in components
2. **Leverage MUI theme** for consistent styling
3. **Implement loading states** with Skeleton components
4. **Handle errors gracefully** with Alert components
5. **Use TypeScript interfaces** for all API responses
6. **Auto-refresh** for real-time dashboards (15-30 second intervals)

---

## Related Documentation

- [API Endpoints](../../docs/reference/api-endpoints.md)
- [Dashboard Backend API](../../docs/reference/dashboard_backend_api.md)
- [State Management](../../docs/reference/state-management/README.md)
