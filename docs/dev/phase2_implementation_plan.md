# Phase 2: Pipeline Stage Monitoring Dashboard

## Overview

Phase 2 focuses on creating a comprehensive monitoring dashboard for pipeline
stage execution, providing real-time visibility into:

- Active pipeline executions
- Stage-by-stage status and metrics
- Historical pipeline runs
- Stage execution times and resource usage
- Dependency graph visualization
- Prometheus metrics integration

## Components

### Backend API Endpoints

#### 1. Pipeline Execution Status

```
GET  /api/pipeline/executions              # List all pipeline executions
GET  /api/pipeline/executions/{id}          # Get specific execution details
GET  /api/pipeline/executions/active        # Get currently active executions
GET  /api/pipeline/executions/{id}/stages   # Get stage details for execution
```

#### 2. Stage Metrics

```
GET  /api/pipeline/stages/metrics           # Get aggregated stage metrics
GET  /api/pipeline/stages/{name}/metrics    # Get metrics for specific stage
GET  /api/pipeline/stages/{name}/history    # Get historical metrics for stage
```

#### 3. Pipeline State

```
GET  /api/pipeline/state                    # Get current pipeline state
GET  /api/pipeline/dependency-graph         # Get pipeline dependency graph
```

#### 4. Prometheus Metrics Integration

```
GET  /api/pipeline/metrics/summary          # Get summary of key metrics
GET  /api/pipeline/metrics/stages           # Get stage-specific metrics
```

### Frontend Components

#### 1. Pipeline Executions Page (`/pipeline`)

- **Active Executions View**
  - List of currently running pipelines
  - Real-time status updates (WebSocket/SSE)
  - Stage progress indicators
  - Estimated completion time

- **Execution Details View**
  - Stage-by-stage breakdown
  - Execution timeline
  - Resource usage graphs
  - Error logs and stack traces
  - Dependency graph visualization

- **Historical Executions View**
  - Table of past executions
  - Filtering by date, status, job type
  - Execution duration statistics
  - Success/failure rates

#### 2. Stage Metrics Dashboard (`/pipeline/metrics`)

- **Stage Performance Metrics**
  - Average execution time per stage
  - Success/failure rates
  - Resource usage (CPU, memory)
  - Throughput (stages/hour)

- **Visualizations**
  - Line charts for execution times over time
  - Bar charts for success rates
  - Heatmaps for resource usage
  - Dependency graph with metrics overlay

#### 3. Real-time Updates

- WebSocket connection for live updates
- Auto-refresh for metrics (30s interval)
- Push notifications for stage completions/failures

## Implementation Steps

### Step 1: Backend API Endpoints

1. Create `src/dsa110_contimg/api/routers/pipeline.py`
2. Add endpoints for pipeline executions
3. Add endpoints for stage metrics
4. Integrate with existing `PipelineOrchestrator` and `StateRepository`
5. Add Prometheus metrics aggregation endpoints

### Step 2: Frontend Components

1. Create `frontend/src/pages/PipelinePage.tsx`
2. Create `frontend/src/components/Pipeline/ActiveExecutions.tsx`
3. Create `frontend/src/components/Pipeline/ExecutionDetails.tsx`
4. Create `frontend/src/components/Pipeline/StageMetrics.tsx`
5. Create `frontend/src/components/Pipeline/DependencyGraph.tsx`
6. Add React Query hooks for API calls
7. Add WebSocket hooks for real-time updates

### Step 3: Integration

1. Add route to `frontend/src/App.tsx`
2. Add navigation link
3. Connect to existing WebSocket manager
4. Test with real pipeline executions

### Step 4: Testing

1. Create test pipeline executions
2. Verify API endpoints
3. Test frontend components
4. Verify real-time updates

## Dependencies

### Backend

- Existing: `PipelineOrchestrator`, `StateRepository`, `PipelineObserver`
- New: None (use existing infrastructure)

### Frontend

- Existing: React Query, Material-UI, WebSocket client
- New:
  - `recharts` or `@mui/x-charts` for visualizations
  - `react-flow` or `@mui/x-tree-view` for dependency graph

## Success Criteria

- ✅ Can view active pipeline executions
- ✅ Can see stage-by-stage progress
- ✅ Can view historical executions
- ✅ Can see stage metrics and performance
- ✅ Real-time updates work correctly
- ✅ Dependency graph displays correctly
- ✅ Metrics visualizations render properly

## Timeline

- **Step 1 (Backend)**: 2-3 hours
- **Step 2 (Frontend)**: 4-5 hours
- **Step 3 (Integration)**: 1 hour
- **Step 4 (Testing)**: 1-2 hours

**Total**: ~8-11 hours
