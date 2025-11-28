# Pipeline API Reference

**Purpose:** REST API documentation for pipeline execution and monitoring  
**Last Updated:** 2025-11-26  
**Status:** Reference (Legacy Backend)

> **⚠️ Migration Note:** These endpoints are implemented in `legacy.backend` and
> serve as the specification for the new `backend` implementation.

---

## Overview

The Pipeline API provides RESTful endpoints for controlling and monitoring the
DSA-110 continuum imaging pipeline. This includes workflow execution status,
stage metrics, and real-time monitoring.

**Base URL:** `http://localhost:8010/api/pipeline`

**Authentication:** None (internal tool)

**Content-Type:** `application/json`

---

## Endpoints

### GET /api/pipeline/workflow-status

Get real-time status of the complete streaming workflow, including queue depths
for each stage, bottleneck detection, and health indicators.

**Use Case:** Powers the `WorkflowStatusPanel` dashboard component for unified
workflow visualization.

**Response:**

```json
{
  "stages": [
    {
      "name": "catalog_setup",
      "display_name": "Catalog Setup",
      "pending": 0,
      "processing": 0,
      "completed_today": 15,
      "failed_today": 0
    },
    {
      "name": "conversion",
      "display_name": "Conversion",
      "pending": 2,
      "processing": 1,
      "completed_today": 12,
      "failed_today": 1
    },
    {
      "name": "calibration_solve",
      "display_name": "Calibration Solve",
      "pending": 5,
      "processing": 2,
      "completed_today": 10,
      "failed_today": 0
    },
    {
      "name": "calibration_apply",
      "display_name": "Calibration Apply",
      "pending": 3,
      "processing": 1,
      "completed_today": 9,
      "failed_today": 0
    },
    {
      "name": "imaging",
      "display_name": "Imaging",
      "pending": 2,
      "processing": 1,
      "completed_today": 8,
      "failed_today": 0
    },
    {
      "name": "mosaic",
      "display_name": "Mosaic",
      "pending": 1,
      "processing": 0,
      "completed_today": 3,
      "failed_today": 0
    },
    {
      "name": "validation",
      "display_name": "Validation",
      "pending": 0,
      "processing": 0,
      "completed_today": 3,
      "failed_today": 0
    },
    {
      "name": "crossmatch",
      "display_name": "Cross-Match",
      "pending": 0,
      "processing": 0,
      "completed_today": 3,
      "failed_today": 0
    },
    {
      "name": "adaptive_photometry",
      "display_name": "Photometry",
      "pending": 1,
      "processing": 1,
      "completed_today": 5,
      "failed_today": 0
    },
    {
      "name": "light_curve",
      "display_name": "Light Curve",
      "pending": 0,
      "processing": 0,
      "completed_today": 4,
      "failed_today": 0
    },
    {
      "name": "transient_detection",
      "display_name": "Transient Detection",
      "pending": 0,
      "processing": 0,
      "completed_today": 4,
      "failed_today": 0
    }
  ],
  "overall_health": "healthy",
  "bottleneck": null,
  "total_pending": 14,
  "total_completed_today": 76,
  "total_failed_today": 1,
  "estimated_completion": "2025-11-26T16:45:00Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `stages` | array | List of stage status objects (see below) |
| `overall_health` | string | Overall pipeline health: `"healthy"`, `"degraded"`, or `"stalled"` |
| `bottleneck` | string\|null | Name of bottleneck stage, or null if none detected |
| `total_pending` | number | Total items pending across all stages |
| `total_completed_today` | number | Total items completed in last 24 hours |
| `total_failed_today` | number | Total items failed in last 24 hours |
| `estimated_completion` | string\|null | ISO timestamp for estimated completion, or null |

**Stage Status Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Stage identifier (snake_case) |
| `display_name` | string | Human-readable stage name |
| `pending` | number | Items waiting to be processed |
| `processing` | number | Items currently being processed |
| `completed_today` | number | Items completed in last 24 hours |
| `failed_today` | number | Items that failed in last 24 hours |

**Health Status Logic:**

- `"healthy"`: No bottleneck detected, failure rate < 5%
- `"degraded"`: Bottleneck detected OR failure rate 5-20%
- `"stalled"`: Nothing processed in last hour OR failure rate > 20%

**Bottleneck Detection:**

A stage is flagged as a bottleneck when:
- `pending > completed_today * 2` (backlog growing faster than processing)
- `pending > 10` and `processing == 0` (queue stalled)

**Example:**

```bash
curl http://localhost:8010/api/pipeline/workflow-status
```

**TypeScript Usage:**

```typescript
interface WorkflowStageStatus {
  name: string;
  display_name: string;
  pending: number;
  processing: number;
  completed_today: number;
  failed_today: number;
}

interface WorkflowStatus {
  stages: WorkflowStageStatus[];
  overall_health: "healthy" | "degraded" | "stalled";
  bottleneck: string | null;
  total_pending: number;
  total_completed_today: number;
  total_failed_today: number;
  estimated_completion: string | null;
}

// React Query hook
import { useQuery } from "@tanstack/react-query";

export function useWorkflowStatus() {
  return useQuery({
    queryKey: ["workflow-status"],
    queryFn: async () => {
      const response = await fetch("/api/pipeline/workflow-status");
      if (!response.ok) throw new Error("Failed to fetch workflow status");
      return response.json() as Promise<WorkflowStatus>;
    },
    refetchInterval: 15000, // Auto-refresh every 15 seconds
  });
}
```

---

### GET /api/pipeline/executions

List pipeline executions with optional filtering.

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status: `running`, `completed`, `failed` |
| `limit` | number | Maximum results (default: 50) |
| `offset` | number | Pagination offset (default: 0) |

**Response:**

```json
{
  "executions": [
    {
      "id": "exec-2025-11-26-001",
      "workflow": "streaming_workflow",
      "status": "completed",
      "started_at": "2025-11-26T14:00:00Z",
      "completed_at": "2025-11-26T14:35:00Z",
      "duration_seconds": 2100,
      "stages_completed": 11,
      "stages_total": 11
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
```

---

### GET /api/pipeline/executions/active

Get currently running pipeline executions.

**Response:**

```json
{
  "active_executions": [
    {
      "id": "exec-2025-11-26-005",
      "workflow": "streaming_workflow",
      "current_stage": "imaging",
      "started_at": "2025-11-26T15:30:00Z",
      "progress_percent": 45.5
    }
  ]
}
```

---

### GET /api/pipeline/executions/{execution_id}

Get details for a specific execution.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `execution_id` | string | Execution identifier |

**Response:**

```json
{
  "id": "exec-2025-11-26-001",
  "workflow": "streaming_workflow",
  "status": "completed",
  "config": {
    "mosaic_enabled": true,
    "photometry_enabled": true,
    "light_curve_enabled": true
  },
  "started_at": "2025-11-26T14:00:00Z",
  "completed_at": "2025-11-26T14:35:00Z",
  "stages": [
    {"name": "catalog_setup", "status": "completed", "duration_seconds": 12},
    {"name": "conversion", "status": "completed", "duration_seconds": 180}
  ],
  "outputs": {
    "ms_path": "/stage/dsa110-contimg/ms/2025-11-26T14:00:00.ms",
    "image_path": "/stage/dsa110-contimg/images/2025-11-26T14:00:00.fits"
  }
}
```

---

### GET /api/pipeline/dependency-graph

Get the dependency graph for pipeline stages.

**Response:**

```json
{
  "nodes": [
    {"id": "catalog_setup", "label": "Catalog Setup"},
    {"id": "conversion", "label": "Conversion"},
    {"id": "calibration_solve", "label": "Calibration Solve"}
  ],
  "edges": [
    {"from": "catalog_setup", "to": "conversion"},
    {"from": "conversion", "to": "calibration_solve"}
  ]
}
```

---

### GET /api/pipeline/metrics/summary

Get summary metrics for pipeline performance.

**Response:**

```json
{
  "total_executions_24h": 45,
  "successful_24h": 42,
  "failed_24h": 3,
  "success_rate": 93.3,
  "avg_duration_seconds": 1850,
  "median_duration_seconds": 1720,
  "p95_duration_seconds": 2800
}
```

---

### GET /api/pipeline/stages/metrics

Get metrics for all pipeline stages.

**Response:**

```json
{
  "stages": [
    {
      "name": "conversion",
      "avg_duration_seconds": 185,
      "success_rate": 98.5,
      "total_runs_24h": 45,
      "failed_runs_24h": 1
    }
  ]
}
```

---

### GET /api/pipeline/stages/{stage_name}/metrics

Get detailed metrics for a specific stage.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `stage_name` | string | Stage name (snake_case) |

**Response:**

```json
{
  "name": "imaging",
  "avg_duration_seconds": 420,
  "min_duration_seconds": 180,
  "max_duration_seconds": 1200,
  "p50_duration_seconds": 380,
  "p95_duration_seconds": 850,
  "success_rate": 97.2,
  "total_runs_24h": 45,
  "failed_runs_24h": 1,
  "retries_24h": 3,
  "common_errors": [
    {"error": "WSClean timeout", "count": 1}
  ]
}
```

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "Not Found",
  "message": "Execution exec-unknown not found",
  "status_code": 404
}
```

**Common Status Codes:**

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (invalid parameters) |
| 404 | Not Found (execution/stage not found) |
| 500 | Internal Server Error |

---

## See Also

- [Pipeline Stage Architecture](../architecture/pipeline/pipeline_stage_architecture.md) -
  Stage design and workflows
- [Streaming API](./streaming-api.md) - Streaming converter endpoints
- [Dashboard Backend API](./dashboard_backend_api.md) - Full endpoint list
