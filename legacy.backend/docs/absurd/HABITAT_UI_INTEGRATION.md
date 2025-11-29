# Habitat UI Integration Analysis

## Executive Summary

**Yes, there is a straightforward path to integrating Habitat UI into the
DSA-110 dashboard.** The most practical approach is **API-based integration** -
using Habitat's Go backend REST API and building React components in the DSA-110
frontend that consume those APIs.

## Current Architecture

### DSA-110 Frontend

- **Framework**: React + TypeScript
- **Build Tool**: Vite
- **UI Library**: Material-UI (MUI)
- **State Management**: React Query (TanStack Query)
- **API Client**: Axios with circuit breaker
- **Location**: `/data/dsa110-contimg/frontend/`

### Habitat UI

- **Framework**: SolidJS + TypeScript
- **Build Tool**: Vite
- **UI Library**: Tailwind CSS + shadcn-solid components
- **Backend**: Go server with REST API
- **Location**: `/home/ubuntu/proj/absurd/habitat/`

### Key Insight

**Habitat's UI is framework-agnostic** - it's just a frontend that consumes REST
APIs. The Go backend (`habitat/internal/server/`) provides clean REST endpoints
that can be consumed by any frontend framework.

## Integration Strategies

### Strategy 1: API Integration (Recommended) ⭐

**Approach**: Use Habitat's Go backend API and build React components in DSA-110
frontend.

**Pros**:

- :white_heavy_check_mark: Clean separation of concerns
- :white_heavy_check_mark: No framework conflicts (React vs SolidJS)
- :white_heavy_check_mark: Reuse existing DSA-110 API patterns
- :white_heavy_check_mark: Can customize UI to match DSA-110 design system
- :white_heavy_check_mark: Minimal changes to Habitat codebase

**Cons**:

- Need to port UI components from SolidJS to React
- Need to maintain API compatibility

**Implementation Steps**:

1. **Run Habitat Backend as Service**

   ```bash
   # Build Habitat binary
   cd /home/ubuntu/proj/absurd/habitat
   make build

   # Run as service (or integrate into existing backend)
   ./bin/habitat run -db-name dsa110_absurd -listen :7890
   ```

2. **Create React API Client**

   ```typescript
   // frontend/src/api/absurd.ts
   import { apiClient } from "./client";

   export interface AbsurdTask {
     taskId: string;
     runId: string;
     queueName: string;
     taskName: string;
     status:
       | "pending"
       | "running"
       | "sleeping"
       | "completed"
       | "failed"
       | "cancelled";
     attempt: number;
     maxAttempts?: number | null;
     createdAt: string;
     updatedAt: string;
     completedAt?: string | null;
     workerId?: string;
   }

   export interface AbsurdQueueMetrics {
     queueName: string;
     queueLength: number;
     queueVisibleLength: number;
     newestMsgAgeSec?: number | null;
     oldestMsgAgeSec?: number | null;
     totalMessages: number;
     scrapeTime: string;
   }

   const HABITAT_API_BASE =
     process.env.VITE_HABITAT_API_URL || "http://localhost:7890";

   export const absurdApi = {
     // Get queue metrics
     getMetrics: async (): Promise<AbsurdQueueMetrics[]> => {
       const response = await apiClient.get(`${HABITAT_API_BASE}/api/metrics`);
       return response.data.queues || [];
     },

     // Get tasks with filtering
     getTasks: async (params?: {
       q?: string;
       status?: string;
       queue?: string;
       taskName?: string;
       taskId?: string;
       page?: number;
       perPage?: number;
     }): Promise<{ tasks: AbsurdTask[]; total: number }> => {
       const response = await apiClient.get(`${HABITAT_API_BASE}/api/tasks`, {
         params,
       });
       return response.data;
     },

     // Get task details
     getTaskDetail: async (taskId: string): Promise<any> => {
       const response = await apiClient.get(
         `${HABITAT_API_BASE}/api/tasks/${taskId}`
       );
       return response.data;
     },

     // Get queues
     getQueues: async (): Promise<string[]> => {
       const response = await apiClient.get(`${HABITAT_API_BASE}/api/queues`);
       return response.data.queues || [];
     },

     // Get events
     getEvents: async (params?: {
       q?: string;
       page?: number;
       perPage?: number;
     }): Promise<any> => {
       const response = await apiClient.get(`${HABITAT_API_BASE}/api/events`, {
         params,
       });
       return response.data;
     },
   };
   ```

3. **Create React Query Hooks**

   ```typescript
   // frontend/src/api/queries.ts (add to existing file)
   import { useQuery } from "@tanstack/react-query";
   import {
     absurdApi,
     type AbsurdTask,
     type AbsurdQueueMetrics,
   } from "./absurd";

   export const useAbsurdMetrics = () => {
     return useQuery<AbsurdQueueMetrics[]>({
       queryKey: ["absurd", "metrics"],
       queryFn: absurdApi.getMetrics,
       refetchInterval: 15000, // Refresh every 15 seconds
     });
   };

   export const useAbsurdTasks = (filters?: {
     status?: string;
     queue?: string;
     page?: number;
   }) => {
     return useQuery({
       queryKey: ["absurd", "tasks", filters],
       queryFn: () => absurdApi.getTasks(filters),
       refetchInterval: 15000,
     });
   };

   export const useAbsurdTaskDetail = (taskId: string) => {
     return useQuery({
       queryKey: ["absurd", "task", taskId],
       queryFn: () => absurdApi.getTaskDetail(taskId),
       refetchInterval: 5000, // More frequent for detail view
     });
   };
   ```

4. **Create React Components**

   ```typescript
   // frontend/src/components/AbsurdTaskList.tsx
   import React from 'react';
   import { useAbsurdTasks } from '../api/queries';
   import { Box, Card, CardContent, Typography, Chip, CircularProgress } from '@mui/material';

   export const AbsurdTaskList: React.FC = () => {
     const { data, isLoading, error } = useAbsurdTasks();

     if (isLoading) return <CircularProgress />;
     if (error) return <Typography color="error">Error loading tasks</Typography>;

     return (
       <Box>
         <Typography variant="h6">Absurd Tasks</Typography>
         {data?.tasks.map((task) => (
           <Card key={task.taskId} sx={{ mb: 2 }}>
             <CardContent>
               <Typography variant="subtitle1">{task.taskName}</Typography>
               <Chip
                 label={task.status}
                 color={getStatusColor(task.status)}
                 size="small"
               />
               <Typography variant="body2" color="text.secondary">
                 Queue: {task.queueName} | Attempt: {task.attempt}
               </Typography>
             </CardContent>
           </Card>
         ))}
       </Box>
     );
   };

   function getStatusColor(status: string) {
     switch (status) {
       case 'completed': return 'success';
       case 'failed': return 'error';
       case 'running': return 'info';
       case 'pending': return 'warning';
       default: return 'default';
     }
   }
   ```

5. **Add Route to Dashboard**

   ```typescript
   // frontend/src/App.tsx (add to existing routes)
   import { AbsurdWorkflowsPage } from './pages/AbsurdWorkflowsPage';

   // In Routes:
   <Route path="/workflows/absurd" element={<AbsurdWorkflowsPage />} />
   ```

### Strategy 2: Iframe Embedding (Quickest)

**Approach**: Embed Habitat UI as an iframe within DSA-110 dashboard.

**Pros**:

- :white_heavy_check_mark: Zero code changes needed
- :white_heavy_check_mark: Can be done in minutes
- :white_heavy_check_mark: Habitat UI works independently

**Cons**:

- :cross_mark: No integration with DSA-110 UI/UX
- :cross_mark: Separate authentication/authorization
- :cross_mark: Limited customization
- :cross_mark: Not ideal for production

**Implementation**:

```typescript
// frontend/src/pages/AbsurdIframePage.tsx
import React from 'react';
import { Box } from '@mui/material';

export const AbsurdIframePage: React.FC = () => {
  const habitatUrl = process.env.VITE_HABITAT_URL || 'http://localhost:7890';

  return (
    <Box sx={{ width: '100%', height: '100vh' }}>
      <iframe
        src={habitatUrl}
        style={{ width: '100%', height: '100%', border: 'none' }}
        title="Absurd Habitat Dashboard"
      />
    </Box>
  );
};
```

### Strategy 3: Component Porting (Most Integrated)

**Approach**: Port Habitat's SolidJS components to React, maintaining the same
UI/UX.

**Pros**:

- :white_heavy_check_mark: Full integration with DSA-110 design system
- :white_heavy_check_mark: Consistent user experience
- :white_heavy_check_mark: Can reuse Habitat's UI patterns

**Cons**:

- :cross_mark: Significant development effort
- :cross_mark: Need to maintain ported components
- :cross_mark: Framework differences (SolidJS → React)

**Implementation**: Port key components:

- `TaskList` → React component
- `TaskDetail` → React component
- `QueueMetrics` → React component
- `EventLog` → React component

## Recommended Approach: Hybrid Strategy

**Phase 1: Quick Integration (Iframe)**

- Embed Habitat UI as iframe for immediate visibility
- Time: 1-2 hours

**Phase 2: API Integration (React Components)**

- Build React components using Habitat API
- Port key views (Tasks, Queues, Metrics)
- Time: 1-2 weeks

**Phase 3: Full Integration (Optional)**

- Port remaining components if needed
- Customize to match DSA-110 design system
- Time: 2-4 weeks

## Technical Considerations

### API Endpoints Available

Habitat provides these REST endpoints:

- `GET /api/metrics` - Queue metrics
- `GET /api/tasks` - List tasks (with filtering, pagination)
- `GET /api/tasks/:taskId` - Task details
- `GET /api/queues` - List queues
- `GET /api/queues/:queueName` - Queue details
- `GET /api/events` - Event log
- `GET /api/config` - Configuration

### Backend Integration Options

**Option A: Separate Service**

- Run Habitat as standalone service on port 7890
- DSA-110 frontend calls Habitat API directly
- Simple, but requires separate service management

**Option B: Proxy Through DSA-110 Backend**

- Add proxy routes in DSA-110 backend
- Frontend calls `/api/absurd/*` → proxied to Habitat
- Better for unified authentication/authorization

**Option C: Embed Habitat Server**

- Integrate Habitat Go server into DSA-110 backend
- Single service, unified API
- More complex but better integration

### Authentication & Authorization

- Habitat currently has no built-in auth
- DSA-110 likely has auth system
- Options:
  1. Add auth middleware to Habitat
  2. Proxy through DSA-110 backend (adds auth layer)
  3. Run Habitat on internal network only

## Implementation Example: Quick Start

### Step 1: Set Up Habitat Backend

```bash
# Build Habitat
cd /home/ubuntu/proj/absurd/habitat
make build

# Run Habitat (adjust database connection)
./bin/habitat run \
  -db-name dsa110_absurd \
  -db-host localhost \
  -db-user postgres \
  -listen :7890
```

### Step 2: Add API Client to DSA-110 Frontend

```typescript
// frontend/src/api/absurd.ts (create new file)
// ... (use code from Strategy 1 above)
```

### Step 3: Create React Components

```typescript
// frontend/src/pages/AbsurdWorkflowsPage.tsx (create new file)
import React from 'react';
import { useAbsurdMetrics, useAbsurdTasks } from '../api/queries';
import { Box, Typography, Grid, Card, CardContent } from '@mui/material';
import { AbsurdTaskList } from '../components/AbsurdTaskList';

export const AbsurdWorkflowsPage: React.FC = () => {
  const { data: metrics } = useAbsurdMetrics();
  const { data: tasks } = useAbsurdTasks();

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Absurd Workflows
      </Typography>

      {/* Queue Metrics */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {metrics?.map((queue) => (
          <Grid item xs={12} sm={6} md={4} key={queue.queueName}>
            <Card>
              <CardContent>
                <Typography variant="h6">{queue.queueName}</Typography>
                <Typography>Total: {queue.totalMessages}</Typography>
                <Typography>Queued: {queue.queueLength}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Task List */}
      <AbsurdTaskList />
    </Box>
  );
};
```

### Step 4: Add Route

```typescript
// frontend/src/App.tsx
import { AbsurdWorkflowsPage } from './pages/AbsurdWorkflowsPage';

// In Routes:
<Route path="/workflows/absurd" element={<AbsurdWorkflowsPage />} />
```

### Step 5: Add Navigation Link

```typescript
// frontend/src/components/Navigation.tsx (add to existing nav)
<NavLink to="/workflows/absurd">Absurd Workflows</NavLink>
```

## File Structure

```
frontend/
├── src/
│   ├── api/
│   │   ├── absurd.ts          # NEW: Absurd API client
│   │   └── queries.ts          # MODIFY: Add Absurd queries
│   ├── components/
│   │   ├── AbsurdTaskList.tsx # NEW: Task list component
│   │   ├── AbsurdTaskDetail.tsx # NEW: Task detail component
│   │   └── AbsurdQueueMetrics.tsx # NEW: Queue metrics component
│   └── pages/
│       └── AbsurdWorkflowsPage.tsx # NEW: Main workflows page
```

## Environment Variables

Add to `.env.development` and `.env.production`:

```bash
# Habitat API URL (if running as separate service)
VITE_HABITAT_API_URL=http://localhost:7890

# Or if proxied through DSA-110 backend:
# VITE_HABITAT_API_URL=/api/absurd
```

## Conclusion

**Yes, there is a straightforward path** to integrating Habitat UI into the
DSA-110 dashboard. The recommended approach is:

1. **Start with API integration** (Strategy 1) - clean, maintainable, fits
   existing patterns
2. **Use React Query** - already in use, perfect for polling/refreshing
3. **Build React components** - match DSA-110 design system (Material-UI)
4. **Proxy through DSA-110 backend** - for unified auth/authorization

The integration can be done incrementally:

- **Week 1**: API client + basic task list
- **Week 2**: Task details + queue metrics
- **Week 3**: Event log + advanced filtering
- **Week 4**: Polish + integration with existing workflows

This approach leverages Habitat's clean API design while maintaining the DSA-110
frontend architecture and design system.
