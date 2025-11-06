# Dashboard Development Guide

## Introduction

This guide covers how to develop and extend the DSA-110 Pipeline Dashboard frontend.

## Prerequisites

- Node.js v22.6.0+ (available in `casa6` conda environment)
- Basic knowledge of React, TypeScript, and Material-UI
- Familiarity with REST APIs and async data fetching

## Development Environment Setup

### 1. Install Dependencies

```bash
cd /data/dsa110-contimg/frontend
conda activate casa6
npm install
```

### 2. Start Development Servers

**Terminal 1 - Backend:**
```bash
cd /data/dsa110-contimg
conda activate casa6
uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 - Frontend:**
```bash
cd /data/dsa110-contimg/frontend
conda activate casa6
npm run dev -- --host 0.0.0.0 --port 5173
```

### 3. Verify Setup

Open `http://localhost:5173` in your browser. You should see the dashboard.

## Project Structure

```
frontend/
├── public/                     # Static assets
├── src/
│   ├── api/                    # API layer
│   │   ├── client.ts           # Axios HTTP client
│   │   ├── types.ts            # TypeScript type definitions
│   │   └── queries.ts          # React Query hooks
│   ├── components/             # Reusable UI components
│   │   ├── Navigation.tsx
│   │   ├── ESECandidatesPanel.tsx
│   │   └── FluxChartPanel.tsx
│   ├── pages/                  # Route-level components
│   │   ├── DashboardPage.tsx
│   │   ├── MosaicGalleryPage.tsx
│   │   ├── SourceMonitoringPage.tsx
│   │   └── SkyViewPage.tsx
│   ├── theme/                  # MUI theme configuration
│   │   └── darkTheme.ts
│   ├── App.tsx                 # Root component with routing
│   ├── main.tsx                # Application entry point
│   └── index.css               # Global styles
├── index.html                  # HTML template
├── package.json                # Dependencies and scripts
├── tsconfig.json               # TypeScript configuration
└── vite.config.ts              # Vite build configuration
```

## Core Technologies

### React Query (TanStack Query)

Used for server state management, caching, and polling.

**Example: Creating a new query hook**

```typescript
// src/api/queries.ts
export function useNewFeature() {
  return useQuery({
    queryKey: ['newfeature'],  // Unique cache key
    queryFn: async () => {
      const response = await apiClient.get('/new-endpoint');
      return response.data;
    },
    refetchInterval: 10000,  // Poll every 10s
    retry: 1,                 // Retry once on failure
  });
}
```

**Using in a component:**

```typescript
import { useNewFeature } from '../api/queries';

export default function MyPage() {
  const { data, isLoading, error } = useNewFeature();
  
  if (isLoading) return <CircularProgress />;
  if (error) return <Alert severity="error">{error.message}</Alert>;
  
  return <div>{JSON.stringify(data)}</div>;
}
```

### Material-UI (MUI)

Component library for building the UI.

**Key components used:**

- `Container`, `Box`, `Stack` - Layout
- `Paper`, `Card` - Surfaces
- `Typography` - Text
- `Button`, `TextField` - Inputs
- `Table`, `TableRow`, `TableCell` - Tables
- `Alert`, `CircularProgress` - Feedback
- `Chip` - Status indicators

**Dark theme:**

```typescript
// src/theme/darkTheme.ts
import { createTheme } from '@mui/material';

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#90caf9' },
    background: {
      default: '#0a1929',
      paper: '#1e1e1e',
    },
  },
});
```

### TypeScript

Strict type checking for API data and component props.

**Example: Defining API types**

```typescript
// src/api/types.ts
export interface NewDataType {
  id: number;
  name: string;
  value: number;
  timestamp: string;
}

export interface NewDataResponse {
  data: NewDataType[];
  total: number;
}
```

### AG Grid

High-performance data table for displaying large datasets.

**Example:**

```typescript
import { AgGridReact } from 'ag-grid-react';
import { ColDef } from 'ag-grid-community';

const columnDefs: ColDef[] = [
  { field: 'id', headerName: 'ID', width: 80 },
  { field: 'name', headerName: 'Name', flex: 1 },
  { 
    field: 'value', 
    headerName: 'Value', 
    valueFormatter: (p) => p.value.toFixed(2) 
  },
];

<AgGridReact
  rowData={data}
  columnDefs={columnDefs}
  pagination={true}
  paginationPageSize={20}
/>
```

### Plotly.js

Interactive charting library for scientific visualizations.

**Example:**

```typescript
import Plot from 'react-plotly.js';

<Plot
  data={[
    {
      x: timestamps,
      y: values,
      type: 'scatter',
      mode: 'lines+markers',
    },
  ]}
  layout={{
    title: 'Time Series',
    xaxis: { title: 'Time' },
    yaxis: { title: 'Value' },
  }}
/>
```

## Common Development Tasks

### Adding a New Page

**1. Create the page component:**

```typescript
// src/pages/NewFeaturePage.tsx
import { Container, Typography, Paper } from '@mui/material';

export default function NewFeaturePage() {
  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h3" gutterBottom>
        New Feature
      </Typography>
      
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="body1">
          Feature content goes here
        </Typography>
      </Paper>
    </Container>
  );
}
```

**2. Add route:**

```typescript
// src/App.tsx
import NewFeaturePage from './pages/NewFeaturePage';

// In <Routes>:
<Route path="/newfeature" element={<NewFeaturePage />} />
```

**3. Add navigation link:**

```typescript
// src/components/Navigation.tsx
import NewIcon from '@mui/icons-material/NewReleases';

<Button 
  color="inherit" 
  component={NavLink} 
  to="/newfeature"
  startIcon={<NewIcon />}
>
  New Feature
</Button>
```

### Adding a New API Endpoint

**1. Define TypeScript types:**

```typescript
// src/api/types.ts
export interface MyData {
  id: number;
  value: string;
}
```

**2. Create query hook:**

```typescript
// src/api/queries.ts
export function useMyData(params: { filter?: string }) {
  return useQuery({
    queryKey: ['mydata', params],
    queryFn: async () => {
      const response = await apiClient.post<{ data: MyData[] }>(
        '/myendpoint',
        params
      );
      return response.data;
    },
  });
}
```

**3. Use in component:**

```typescript
const { data, isLoading } = useMyData({ filter: 'active' });
```

### Creating a Reusable Component

**Example: Status Badge**

```typescript
// src/components/StatusBadge.tsx
import { Chip } from '@mui/material';

interface StatusBadgeProps {
  status: 'active' | 'completed' | 'failed';
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const colors = {
    active: 'warning',
    completed: 'success',
    failed: 'error',
  } as const;
  
  return (
    <Chip 
      label={status} 
      color={colors[status]} 
      size="small" 
    />
  );
}
```

**Usage:**

```typescript
import StatusBadge from '../components/StatusBadge';

<StatusBadge status="completed" />
```

### Adding a Chart

**Example: Line chart with Plotly**

```typescript
// src/components/MyChart.tsx
import Plot from 'react-plotly.js';
import { Box } from '@mui/material';

interface MyChartProps {
  data: { x: string[]; y: number[] };
}

export default function MyChart({ data }: MyChartProps) {
  return (
    <Box sx={{ width: '100%', height: 400 }}>
      <Plot
        data={[
          {
            x: data.x,
            y: data.y,
            type: 'scatter',
            mode: 'lines+markers' as any,
            marker: { color: '#90caf9' },
          },
        ]}
        layout={{
          autosize: true,
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          font: { color: '#ffffff' },
          xaxis: { 
            title: 'Time' as any, 
            gridcolor: '#333' 
          },
          yaxis: { 
            title: 'Value' as any, 
            gridcolor: '#333' 
          },
        }}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
        config={{ responsive: true }}
      />
    </Box>
  );
}
```

## Testing

### Manual Testing

1. **Start dev servers** (backend + frontend)
2. **Open browser** to http://localhost:5173
3. **Test each page:**
   - Navigation works
   - Data loads correctly
   - Error states display properly
   - Loading states show spinners

### Browser Console

Monitor for errors:

1. Open DevTools (F12)
2. Check Console tab for errors/warnings
3. Check Network tab for failed API requests

### TypeScript Type Checking

```bash
npm run build
```

Ensures no type errors before deployment.

## Building for Production

### Create Production Build

```bash
cd /data/dsa110-contimg/frontend
npm run build
```

Output: `dist/` directory with optimized static files.

### Preview Production Build

```bash
npm run preview
```

Access at http://localhost:4173

### Bundle Analysis

Check bundle size:

```bash
npm run build
# Look for dist/assets/*.js size in output
```

Current bundle: ~1.4 MB (gzipped: ~406 KB)

## Code Style Guidelines

### Component Structure

```typescript
// 1. Imports
import { useState } from 'react';
import { Container, Typography } from '@mui/material';
import { useMyData } from '../api/queries';

// 2. Interfaces
interface MyComponentProps {
  id: string;
}

// 3. Component
export default function MyComponent({ id }: MyComponentProps) {
  // 4. Hooks
  const { data, isLoading } = useMyData(id);
  const [selected, setSelected] = useState<string | null>(null);
  
  // 5. Event handlers
  const handleClick = () => {
    setSelected(id);
  };
  
  // 6. Early returns
  if (isLoading) return <CircularProgress />;
  
  // 7. Main render
  return (
    <Container>
      <Typography>{data.name}</Typography>
    </Container>
  );
}
```

### Naming Conventions

- **Components:** PascalCase (`MyComponent.tsx`)
- **Hooks:** camelCase with `use` prefix (`useMyData`)
- **Variables:** camelCase (`myVariable`)
- **Constants:** UPPER_SNAKE_CASE (`API_BASE_URL`)
- **Types/Interfaces:** PascalCase (`MyDataType`)

### File Organization

- One component per file
- Co-locate related files (component + styles + tests)
- Keep files under 300 lines (split if longer)
- Export default for components, named exports for utilities

## Debugging Tips

### React Query Devtools

Add to `App.tsx`:

```typescript
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

<QueryClientProvider client={queryClient}>
  <App />
  <ReactQueryDevtools initialIsOpen={false} />
</QueryClientProvider>
```

### Console Logging

```typescript
console.log('Data loaded:', data);
console.error('API error:', error);
```

### Network Inspection

1. Open DevTools (F12)
2. Network tab
3. Filter: XHR/Fetch
4. Check request/response for API calls

### Common Issues

**Issue:** Blank page after changes

- **Solution:** Check browser console for errors, restart dev server

**Issue:** Data not updating

- **Solution:** Check `refetchInterval` in query, verify API is responding

**Issue:** TypeScript errors

- **Solution:** Run `npm run build` to see all errors

**Issue:** CORS errors

- **Solution:** Verify backend CORS middleware, try using Vite proxy

## Next Steps

- See [Dashboard Guide](dashboard.md) for user documentation
- See [API Reference](../reference/dashboard_api.md) for endpoint details
- See [Frontend Design](../concepts/frontend_design.md) for architecture decisions

