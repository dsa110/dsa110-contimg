# DSA-110 Front-End: Next Steps & Implementation Guide

## Status: Design Complete ✓

All strategic design decisions finalized. Ready for development kickoff.

---

## Quick Reference: Finalized Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Source Naming** | NVSS IDs | Survey-specific for current Dec pointings |
| **ESE Threshold** | 5σ | Balance sensitivity vs. false positives |
| **Alerts** | In-app + Slack | Real-time UI + async notifications |
| **Data Retention** | Persistent | Indefinite storage, no expiration |
| **Current Priority** | Hour-long mosaics | Time-range queryable mosaics |
| **VO Cone Search** | Phase 3 | Design includes, implement later |

---

## Immediate Next Steps (Week 1)

### 1. Development Environment Setup

```bash
# Initialize React project with Vite
cd /data/dsa110-contimg
npm create vite@latest frontend -- --template react-ts

# Install core dependencies
cd frontend
npm install

# UI Framework
npm install @mui/material @emotion/react @emotion/styled

# Visualization
npm install plotly.js react-plotly.js d3

# Data Management
npm install @tanstack/react-query axios

# Routing
npm install react-router-dom

# Tables
npm install ag-grid-react ag-grid-community

# Dev dependencies
npm install -D @types/d3 @types/plotly.js
```

### 2. Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── Dashboard/
│   │   │   ├── PipelineStatus.tsx
│   │   │   ├── SystemHealth.tsx
│   │   │   ├── RecentObservations.tsx
│   │   │   ├── LatestImages.tsx
│   │   │   └── ActiveAlerts.tsx
│   │   ├── Sky/
│   │   │   ├── ImageGallery.tsx
│   │   │   ├── MosaicBuilder.tsx
│   │   │   └── FITSViewer.tsx
│   │   ├── Sources/
│   │   │   ├── SourceTable.tsx
│   │   │   ├── SourceDetail.tsx
│   │   │   └── ESECandidates.tsx
│   │   ├── Observing/
│   │   │   ├── TelescopeStatus.tsx
│   │   │   ├── PointingHistory.tsx
│   │   │   └── CalibratorTracking.tsx
│   │   ├── Health/
│   │   │   ├── SystemMetrics.tsx
│   │   │   ├── QueueStatus.tsx
│   │   │   └── PerformanceMetrics.tsx
│   │   └── shared/
│   │       ├── Navigation.tsx
│   │       ├── LoadingSpinner.tsx
│   │       └── ErrorBoundary.tsx
│   ├── pages/
│   │   ├── DashboardPage.tsx
│   │   ├── SkyPage.tsx
│   │   ├── SourcesPage.tsx
│   │   ├── ObservingPage.tsx
│   │   └── HealthPage.tsx
│   ├── api/
│   │   ├── client.ts          # Axios instance
│   │   ├── queries.ts         # React Query hooks
│   │   └── types.ts           # TypeScript interfaces
│   ├── utils/
│   │   ├── formatters.ts      # Date, flux, coordinate formatters
│   │   ├── calculations.ts    # Variability statistics
│   │   └── constants.ts       # Thresholds, colors, etc.
│   ├── theme/
│   │   ├── darkTheme.ts       # MUI dark theme config
│   │   └── colors.ts          # Color palette
│   ├── App.tsx
│   └── main.tsx
├── public/
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### 3. API Client Setup

**src/api/client.ts**:
```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptors for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);
```

**src/api/types.ts** (map to existing API models):
```typescript
export interface QueueStats {
  total: number;
  pending: number;
  in_progress: number;
  failed: number;
  completed: number;
  collecting: number;
}

export interface CalibratorMatch {
  name: string;
  ra_deg: number;
  dec_deg: number;
  sep_deg: number;
  weighted_flux: number | null;
}

export interface QueueGroup {
  group_id: string;
  state: string;
  received_at: string;
  last_update: string;
  subbands_present: number;
  expected_subbands: number;
  has_calibrator: boolean | null;
  matches: CalibratorMatch[] | null;
}

export interface PipelineStatus {
  queue: QueueStats;
  recent_groups: QueueGroup[];
  calibration_sets: CalibrationSet[];
  matched_recent: number;
}

export interface SystemMetrics {
  ts: string;
  cpu_percent: number | null;
  mem_percent: number | null;
  mem_total: number | null;
  mem_used: number | null;
  disk_total: number | null;
  disk_used: number | null;
  load_1: number | null;
  load_5: number | null;
  load_15: number | null;
}

// Add more interfaces as needed
```

**src/api/queries.ts**:
```typescript
import { useQuery, UseQueryResult } from '@tanstack/react-query';
import { apiClient } from './client';
import { PipelineStatus, SystemMetrics } from './types';

export function usePipelineStatus(): UseQueryResult<PipelineStatus> {
  return useQuery({
    queryKey: ['pipeline', 'status'],
    queryFn: async () => {
      const { data } = await apiClient.get<PipelineStatus>('/api/status');
      return data;
    },
    refetchInterval: 10000, // Poll every 10s
  });
}

export function useSystemMetrics(): UseQueryResult<SystemMetrics> {
  return useQuery({
    queryKey: ['system', 'metrics'],
    queryFn: async () => {
      const { data } = await apiClient.get<SystemMetrics>('/api/metrics/system');
      return data;
    },
    refetchInterval: 10000,
  });
}

export function useSystemMetricsHistory(limit: number = 60): UseQueryResult<SystemMetrics[]> {
  return useQuery({
    queryKey: ['system', 'metrics', 'history', limit],
    queryFn: async () => {
      const { data } = await apiClient.get<SystemMetrics[]>(
        `/api/metrics/system/history?limit=${limit}`
      );
      return data;
    },
    refetchInterval: 10000,
  });
}

// Add more query hooks...
```

### 4. Dark Theme Setup

**src/theme/darkTheme.ts**:
```typescript
import { createTheme } from '@mui/material/styles';

export const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    background: {
      default: '#0D1117',
      paper: '#161B22',
    },
    primary: {
      main: '#58A6FF',
    },
    success: {
      main: '#3FB950',
    },
    warning: {
      main: '#D29922',
    },
    error: {
      main: '#F85149',
    },
    info: {
      main: '#79C0FF',
    },
    text: {
      primary: '#C9D1D9',
      secondary: '#8B949E',
    },
  },
  typography: {
    fontFamily: 'Inter, Roboto, sans-serif',
    h1: { fontWeight: 600 },
    h2: { fontWeight: 600 },
    h3: { fontWeight: 600 },
    h4: { fontWeight: 600 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
  },
});
```

### 5. First Component: Dashboard

**src/pages/DashboardPage.tsx**:
```typescript
import React from 'react';
import { Container, Grid, Paper, Typography } from '@mui/material';
import { usePipelineStatus, useSystemMetrics } from '../api/queries';
import PipelineStatus from '../components/Dashboard/PipelineStatus';
import SystemHealth from '../components/Dashboard/SystemHealth';
import RecentObservations from '../components/Dashboard/RecentObservations';
import LatestImages from '../components/Dashboard/LatestImages';
import ActiveAlerts from '../components/Dashboard/ActiveAlerts';

export default function DashboardPage() {
  const { data: status, isLoading: statusLoading } = usePipelineStatus();
  const { data: metrics, isLoading: metricsLoading } = useSystemMetrics();

  if (statusLoading || metricsLoading) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h3" gutterBottom>
        DSA-110 Continuum Pipeline
      </Typography>

      <Grid container spacing={3}>
        {/* Top Row: Status + Health */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <PipelineStatus data={status} />
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <SystemHealth metrics={metrics} />
          </Paper>
        </Grid>

        {/* Recent Observations */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <RecentObservations groups={status?.recent_groups || []} />
          </Paper>
        </Grid>

        {/* Latest Images */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <LatestImages />
          </Paper>
        </Grid>

        {/* Alerts + Quick Stats */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <ActiveAlerts />
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            {/* Quick Stats Component */}
          </Paper>
        </Grid>
      </Grid>
    </Container>
  );
}
```

---

## Phase 1 Checklist (Weeks 1-3)

### Week 1: Setup & Infrastructure
- [ ] Initialize Vite + React + TypeScript project
- [ ] Install dependencies (MUI, React Query, Plotly, D3, AG Grid)
- [ ] Configure dark theme
- [ ] Set up API client and TypeScript types
- [ ] Create project structure (directories, base components)
- [ ] Configure routing (React Router)

### Week 2: Dashboard Page
- [ ] Pipeline Status component (queue stats, uptime)
- [ ] System Health component (CPU, memory, disk, load)
- [ ] Recent Observations table
- [ ] Latest Images thumbnail grid
- [ ] Active Alerts panel (ESE candidates >5σ)
- [ ] Wire up React Query hooks with 10s polling

### Week 3: Health Page
- [ ] Queue Status component (detailed group table)
- [ ] System Metrics time-series plots (Plotly.js)
- [ ] Calibration Registry table
- [ ] Performance Metrics table
- [ ] QA diagnostic thumbnail gallery

---

## Mosaic Builder (High Priority - Phase 2)

### API Endpoint Design

**Backend Addition** (FastAPI routes):
```python
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

class MosaicRequest(BaseModel):
    start_mjd: float
    end_mjd: float
    dec_min: float | None = None
    dec_max: float | None = None

@router.post("/api/mosaic/generate")
async def generate_mosaic(req: MosaicRequest, background_tasks: BackgroundTasks):
    """Generate mosaic from time range."""
    job_id = f"mosaic_{int(req.start_mjd * 1000)}"
    
    # Queue async mosaic generation task
    background_tasks.add_task(
        build_mosaic,
        start_mjd=req.start_mjd,
        end_mjd=req.end_mjd,
        dec_range=(req.dec_min, req.dec_max),
        output_dir=Path(f"/scratch/dsa110-contimg/mosaics/{job_id}"),
    )
    
    return {"job_id": job_id, "status": "queued"}

@router.get("/api/mosaic/{job_id}/status")
async def mosaic_status(job_id: str):
    """Check mosaic generation status."""
    # Check job status from database or file system
    return {"job_id": job_id, "status": "processing", "progress": 0.6}

@router.get("/api/mosaic/{job_id}/download")
async def download_mosaic(job_id: str, format: str = "fits"):
    """Download completed mosaic."""
    # Serve FITS or PNG
    pass
```

**Frontend Component**:
```typescript
// src/components/Sky/MosaicBuilder.tsx
import React, { useState } from 'react';
import { TextField, Button, LinearProgress } from '@mui/material';
import { useMutation } from '@tanstack/react-query';

export default function MosaicBuilder() {
  const [startMJD, setStartMJD] = useState(60238.0);
  const [endMJD, setEndMJD] = useState(60238.042);

  const generateMutation = useMutation({
    mutationFn: async ({ start_mjd, end_mjd }) => {
      const { data } = await apiClient.post('/api/mosaic/generate', {
        start_mjd,
        end_mjd,
      });
      return data;
    },
    onSuccess: (data) => {
      console.log('Mosaic job queued:', data.job_id);
      // Poll status endpoint
    },
  });

  const handleGenerate = () => {
    generateMutation.mutate({ start_mjd: startMJD, end_mjd: endMJD });
  };

  return (
    <Box>
      <Typography variant="h5">Time Range Mosaic Generator</Typography>
      <TextField
        label="Start MJD"
        type="number"
        value={startMJD}
        onChange={(e) => setStartMJD(parseFloat(e.target.value))}
      />
      <TextField
        label="End MJD"
        type="number"
        value={endMJD}
        onChange={(e) => setEndMJD(parseFloat(e.target.value))}
      />
      <Button
        variant="contained"
        onClick={handleGenerate}
        disabled={generateMutation.isLoading}
      >
        Generate Mosaic
      </Button>
      {generateMutation.isLoading && <LinearProgress />}
    </Box>
  );
}
```

---

## Slack Integration (Phase 2)

### Backend Setup

**Environment Variable**:
```bash
# Add to contimg.env
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_ALERT_CHANNEL=#ese-alerts
```

**Alert Function** (`src/dsa110_contimg/alerts/slack.py`):
```python
import os
import requests
from datetime import datetime

def send_ese_alert(source_id: str, significance: float, flux_change: tuple, last_obs: datetime):
    """Send ESE candidate alert to Slack."""
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        return
    
    flux_old, flux_new = flux_change
    pct_change = ((flux_new - flux_old) / flux_old) * 100
    
    payload = {
        "text": "ESE Candidate Detected!",
        "attachments": [{
            "color": "danger",
            "fields": [
                {"title": "Source", "value": source_id, "short": True},
                {"title": "Significance", "value": f"{significance:.1f}σ", "short": True},
                {"title": "Flux Change", "value": f"{pct_change:+.1f}% ({flux_old:.0f}→{flux_new:.0f} mJy)", "short": True},
                {"title": "Last Obs", "value": last_obs.strftime("%Y-%m-%d %H:%M UTC"), "short": True}
            ],
            "actions": [{
                "type": "button",
                "text": "View Source",
                "url": f"https://dsa110-pipeline.caltech.edu/sources/{source_id}"
            }]
        }]
    }
    
    try:
        requests.post(webhook_url, json=payload, timeout=5)
    except Exception as e:
        print(f"Slack alert failed: {e}")
```

**Integration Point** (after photometry):
```python
# In photometry/cli.py or imaging worker
from dsa110_contimg.alerts.slack import send_ese_alert

# After measuring flux
if chi2_nu > 5.0:  # ESE threshold
    send_ese_alert(
        source_id=nvss_id,
        significance=chi2_nu,
        flux_change=(nvss_flux, measured_flux),
        last_obs=datetime.utcnow()
    )
```

---

## Testing Strategy

### Unit Tests
```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
```

**Example Test** (`src/components/Dashboard/__tests__/PipelineStatus.test.tsx`):
```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import PipelineStatus from '../PipelineStatus';

describe('PipelineStatus', () => {
  it('renders queue stats correctly', () => {
    const mockData = {
      queue: { total: 10, pending: 3, in_progress: 1, completed: 6, failed: 0 },
      // ...
    };
    
    render(<PipelineStatus data={mockData} />);
    
    expect(screen.getByText('3 pending')).toBeInTheDocument();
    expect(screen.getByText('1 in progress')).toBeInTheDocument();
  });
});
```

---

## Deployment

### Production Build
```bash
cd frontend
npm run build  # Outputs to dist/
```

### Serve via FastAPI (Static Files)
```python
# In api/routes.py
from fastapi.staticfiles import StaticFiles

app.mount("/ui", StaticFiles(directory="frontend/dist", html=True), name="ui")
```

### Or Nginx
```nginx
location /ui {
    root /data/dsa110-contimg/frontend/dist;
    try_files $uri $uri/ /index.html;
}

location /api {
    proxy_pass http://localhost:8000;
}
```

---

## Resources

**Official Docs**:
- [React](https://react.dev)
- [Vite](https://vitejs.dev)
- [Material-UI](https://mui.com/material-ui/getting-started/)
- [React Query](https://tanstack.com/query/latest/docs/framework/react/overview)
- [AG Grid](https://www.ag-grid.com/react-data-grid/)
- [Plotly.js](https://plotly.com/javascript/)

**Example Astronomy UIs**:
- [Gaia Archive](https://gea.esac.esa.int/archive/)
- [ZTF Fritz](https://fritz.science/)
- [LOFAR LTA](https://lta.lofar.eu/)

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-24  
**Status**: Implementation Guide

