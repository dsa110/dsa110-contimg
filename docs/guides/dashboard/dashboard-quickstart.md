# Dashboard Quick Start Guide

**Status:** ✅ Authoritative Reference  
**Last Updated:** November 26, 2025

This is the primary dashboard documentation for the DSA-110 Continuum Imaging
Pipeline web interface.

## TL;DR - Quick Start

```bash
# Terminal 1 - Backend
cd /data/dsa110-contimg
conda activate casa6
uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend
cd /data/dsa110-contimg/frontend
conda activate casa6
npm run dev -- --host 0.0.0.0 --port 5173
```

**Access:** http://localhost:5173

**Tech Stack:** React 18 + TypeScript + Vite + Material-UI + React Query +
Plotly.js + AG Grid

---

## Accessing the Dashboard

Open your browser to:

```text
http://localhost:5173
```

The dashboard will automatically redirect to `/dashboard`.

## Features

### 1. Dashboard (Main Page)

**URL:** `/dashboard`

The main dashboard provides an at-a-glance view of pipeline health and system
status:

- **Pipeline Status Panel**

  - Queue statistics (total, pending, in-progress, completed, failed,
    collecting)
  - Active calibration sets
  - Recent observations table with group IDs and processing state

- **System Health Panel**

  - CPU usage percentage
  - Memory usage percentage
  - Disk usage percentage
  - System load (1-minute average)
  - Last update timestamp

- **ESE Candidates Panel** (New!)
  - Real-time variability alerts with 5σ threshold
  - Source ID (NVSS naming convention)
  - Maximum σ deviation
  - Status indicators (active, resolved, false_positive)
  - Last detection timestamp
  - Auto-refresh every 10 seconds

### 2. Mosaic Gallery

**URL:** `/mosaics`

Time-range query interface for hour-long mosaics:

- **Time Range Selection**

  - Start/End DateTime pickers (UTC timezone)
  - MJD conversion support
  - Default: last 1 hour

- **Mosaic Query**

  - Query existing mosaics by time range
  - View mosaic metadata (source count, noise level, image count)
  - Status tracking (pending, in_progress, completed, failed)

- **Mosaic Generation**

  - Create new mosaics from time ranges
  - Background processing with status updates
  - Progress tracking

- **Mosaic Grid View**
  - Thumbnail previews (when available)
  - Download options (FITS, PNG)
  - Quick view button
  - Responsive grid layout (1-3 columns based on screen size)

### 3. Source Monitoring

**URL:** `/sources`

Per-source flux timeseries monitoring with high-performance data table:

- **Source Search**

  - Search by NVSS ID (e.g., `NVSS J123456.7+420312`)
  - Support for other survey IDs (future)

- **Flux Time Series Chart**

  - Interactive Plotly.js visualization
  - Flux measurements with error bars
  - Mean flux reference line
  - Zoom, pan, and export capabilities
  - Dark theme optimized for astronomy

- **Data Table (AG Grid)**
  - High-performance rendering (handles 10,000+ rows)
  - Sortable columns
  - Filterable columns
  - Pagination (10 rows per page)
  - Columns:
    - Time (UTC)
    - Flux (Jy)
    - Flux Error (Jy)
    - χ²/ν (variability indicator)
    - σ deviation (highlight if >5)

### 4. Sky View

**URL:** `/sky`

FITS image viewer and sky navigation (integration in progress):

- **Coordinate Navigation**

  - RA/Dec input (J2000 coordinates)
  - Image path loading
  - Go to coordinate functionality

- **Image Controls**

  - Zoom controls
  - Pan/Reset buttons
  - Colormap selection
  - Image statistics display

- **FITS Viewer Placeholder**
  - Prepared for JS9 integration
  - Prepared for Aladin Lite integration
  - See [JS9 Documentation](https://js9.si.edu/) for integration details

## Technology Stack

### Frontend

- **Framework:** React 18 with TypeScript
- **Build Tool:** Vite (development server with HMR)
- **UI Library:** Material-UI v5 (MUI)
- **Data Fetching:** TanStack Query (React Query)
- **Routing:** React Router v6
- **Charts:** Plotly.js with react-plotly.js
- **Data Tables:** AG Grid Community
- **Date Pickers:** MUI X Date Pickers
- **Theme:** Custom dark theme optimized for astronomy

### Backend

- **API Framework:** FastAPI
- **CORS:** Enabled for localhost development
- **Endpoints:** RESTful JSON API
- **Database:** SQLite3 (ingest.sqlite3, products.sqlite3,
  master_sources.sqlite3)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser (localhost:5173)                │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  React App (TypeScript)                               │  │
│  │  ├── Navigation (React Router)                        │  │
│  │  ├── Theme Provider (MUI Dark Theme)                  │  │
│  │  ├── Query Client (React Query)                       │  │
│  │  └── Pages                                            │  │
│  │      ├── DashboardPage                                │  │
│  │      ├── MosaicGalleryPage                            │  │
│  │      ├── SourceMonitoringPage                         │  │
│  │      └── SkyViewPage                                  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼ HTTP/JSON (port 5173 → 8000)
┌─────────────────────────────────────────────────────────────┐
│                 FastAPI Backend (localhost:8000)             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  API Routes                                           │  │
│  │  ├── /api/status                                      │  │
│  │  ├── /api/metrics/system                              │  │
│  │  ├── /api/ese/candidates                              │  │
│  │  ├── /api/mosaics/query                               │  │
│  │  ├── /api/mosaics/create                              │  │
│  │  ├── /api/sources/search                              │  │
│  │  └── /api/alerts/history                              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼ SQLite
┌─────────────────────────────────────────────────────────────┐
│                        Databases                             │
│  ├── ingest.sqlite3 (queue management)                      │
│  ├── products.sqlite3 (images, photometry, mosaics)         │
│  ├── master_sources.sqlite3 (source catalog)                │
│  └── cal_registry.sqlite3 (calibration)                     │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### Real-Time Updates

The dashboard uses polling to fetch updates every 10 seconds:

1. **React Query** manages data fetching and caching
2. **Polling interval:** 10s for pipeline status, system metrics, ESE candidates
3. **On-demand queries:** Triggered by user actions (search, time range
   selection)
4. **Automatic retry:** 1 retry on failure, no refetch on window focus

### API Data Models

See [API Reference](../../reference/dashboard_backend_api.md) for detailed
endpoint documentation.

## Development

### Project Structure

```
frontend/
├── src/
│   ├── api/                    # API client and hooks
│   │   ├── client.ts           # Axios configuration
│   │   ├── types.ts            # TypeScript interfaces
│   │   └── queries.ts          # React Query hooks
│   ├── components/             # Reusable components
│   │   ├── Navigation.tsx      # Top navigation bar
│   │   ├── ESECandidatesPanel.tsx
│   │   └── FluxChartPanel.tsx
│   ├── pages/                  # Route components
│   │   ├── DashboardPage.tsx
│   │   ├── MosaicGalleryPage.tsx
│   │   ├── SourceMonitoringPage.tsx
│   │   └── SkyViewPage.tsx
│   ├── theme/                  # MUI theme configuration
│   │   └── darkTheme.ts
│   ├── App.tsx                 # Root component
│   └── main.tsx                # Entry point
├── package.json
├── tsconfig.json
└── vite.config.ts
```

### Adding a New Page

1. **Create page component:**

   ```typescript
   // src/pages/NewPage.tsx
   export default function NewPage() {
     return (
       <Container maxWidth="xl" sx={{ py: 4 }}>
         <Typography variant="h3" gutterBottom>
           New Feature
         </Typography>
       </Container>
     );
   }
   ```

2. **Add route in App.tsx:**

   ```typescript
   import NewPage from "./pages/NewPage";

   // In Routes:
   <Route path="/new" element={<NewPage />} />;
   ```

3. **Add navigation link:**
   ```typescript
   // In Navigation.tsx
   <Button component={NavLink} to="/new">
     New Feature
   </Button>
   ```

### Adding a New API Endpoint

1. **Define TypeScript interface:**

   ```typescript
   // src/api/types.ts
   export interface NewData {
     id: number;
     name: string;
   }
   ```

2. **Create React Query hook:**

   ```typescript
   // src/api/queries.ts
   export function useNewData() {
     return useQuery({
       queryKey: ["newdata"],
       queryFn: async () => {
         const response = await apiClient.get<NewData[]>("/new");
         return response.data;
       },
     });
   }
   ```

3. **Use in component:**
   ```typescript
   const { data, isLoading, error } = useNewData();
   ```

### Building for Production

```bash
cd /data/dsa110-contimg/frontend
npm run build
```

Output will be in `frontend/dist/`. Serve with:

```bash
npm run preview
```

Or use a static file server:

```bash
python -m http.server -d dist 5173
```

## Configuration

### Environment Variables

Create `frontend/.env.local`:

```bash
# API base URL
VITE_API_URL=http://localhost:8000

# Or use proxy (set to /api to enable Vite proxy)
VITE_API_URL=/api
```

### Vite Proxy Configuration

For development environments with SSH port forwarding, use the proxy:

```typescript
// vite.config.ts
export default defineConfig({
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

## Troubleshooting

### Dashboard Not Loading

1. **Check both services are running:**

   ```bash
   ps aux | grep -E "node.*vite|uvicorn.*dsa110"
   ```

2. **Test backend API:**

   ```bash
   curl http://localhost:8000/api/status
   ```

3. **Test frontend:**

   ```bash
   curl http://localhost:5173
   ```

4. **Check browser console (F12) for errors**

### CORS Errors

If you see CORS errors in the browser console:

1. **Verify CORS middleware is enabled** in `src/dsa110_contimg/api/routes.py`
2. **Check allowed origins** include your frontend URL
3. **Try using the Vite proxy** instead of direct API calls

### TypeScript Compilation Errors

```bash
cd /data/dsa110-contimg/frontend
npm run build
```

Fix any type errors before running the dev server.

### Port Already in Use

```bash
# Kill existing Vite process
pkill -f "node.*vite.*5173"

# Kill existing uvicorn process
pkill -f "uvicorn.*dsa110"
```

### Node.js Version Issues

The project requires Node.js ≥20.19.0 or ≥22.12.0. Check version:

```bash
conda activate casa6
node --version
```

## Next Steps

### Connecting Real Data

The dashboard currently uses mock data. To connect real data:

1. **Implement database queries** in `src/dsa110_contimg/api/routes.py`
2. **Replace mock generators** with actual SQLite queries
3. **Update data models** if schema differs from mock data
4. **Test with real pipeline data**

See [Connecting Real Data](../../reference/dashboard_backend_api.md) for
detailed API details and wiring notes.

### Phase 2 Features

- **Slack Alerting:** Webhook integration for ESE candidate notifications
- **VO Cone Search:** External API for TOPCAT/Aladin integration
- **User Authentication:** Login system for multi-user access
- **Custom Thresholds:** User-configurable ESE detection parameters
- **Advanced Filtering:** More query options for mosaics and sources

### FITS Viewer Integration

To integrate JS9 or Aladin Lite:

1. **JS9:** See
   [JS9 Integration Guide](https://js9.si.edu/js9/help/install.html)
2. **Aladin Lite:** See
   [Aladin Lite API](https://aladin.cds.unistra.fr/AladinLite/doc/)

Placeholder is ready in `frontend/src/pages/SkyViewPage.tsx`.

## Support

For issues or questions:

- Check [Troubleshooting](../../troubleshooting/)
- See [API Reference](../../reference/dashboard_backend_api.md)
- Consult [Frontend Design](../../architecture/dashboard/frontend_design.md)
