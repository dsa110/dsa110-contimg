# DSA-110 Continuum Pipeline - Frontend

**Date:** 2025-11-16

> 📚 **Documentation Index**: For complete documentation navigation, see
> [Documentation Home](../docs/index.md)  
> 📝 **Quick Reference**: For formatting and structure guidelines, see
> [Quick Reference](../docs/reference/quick_ref.md)  
> 🤖 **AI Agent Guidelines**: For creating/updating docs, see
> [Agent Guidelines](../docs/reference/agent_guidelines.md)

React + TypeScript web interface for monitoring the DSA-110 continuum imaging
pipeline.

## Tech Stack

- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite 6
- **UI Library**: Material-UI (MUI) v7
- **State Management**: TanStack React Query (for API state)
- **Routing**: React Router v7
- **Visualization**: Plotly.js, D3.js
- **Tables**: AG Grid
- **HTTP Client**: Axios

## Development Setup

### Prerequisites

- Node.js v22+ (available in `casa6` conda environment)
- Backend API running on `localhost:8000`

### Installation

```bash
# Using casa6 conda environment (recommended for Ubuntu 18.x)
cd /data/dsa110-contimg/frontend
conda run -n casa6 npm install
```

### Development Server

```bash
# Start dev server with hot reload
conda run -n casa6 npm run dev

# Or specify custom port
conda run -n casa6 npm run dev
```

Frontend will be available at http://localhost:3210

### Build for Production

```bash
# Create optimized production build
conda run -n casa6 npm run build

# Output in dist/ directory
```

### Preview Production Build

```bash
conda run -n casa6 npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/                # API client & React Query hooks
│   │   ├── client.ts       # Axios instance
│   │   ├── types.ts        # TypeScript interfaces
│   │   └── queries.ts      # React Query hooks
│   ├── components/         # React components
│   │   ├── CARTA/          # CARTA integration components
│   │   ├── Cache/          # Cache management components
│   │   ├── CircuitBreaker/ # Circuit breaker components
│   │   ├── DeadLetterQueue/# Dead letter queue components
│   │   ├── Events/         # Event handling components
│   │   ├── MSDetails/      # Measurement set detail components
│   │   ├── Pipeline/       # Pipeline workflow components
│   │   ├── QA/             # Quality assurance components
│   │   ├── Sky/            # Sky/image gallery components
│   │   └── workflows/      # Workflow orchestration components
│   ├── pages/              # Page-level components
│   │   ├── DashboardPage.tsx
│   │   ├── HealthPage.tsx
│   │   ├── ObservingPage.tsx
│   │   └── [many more page components...]
│   ├── theme/              # MUI theme configuration
│   │   └── darkTheme.ts    # Dark mode theme
│   ├── utils/              # Utility functions
│   ├── App.tsx             # Main app component
│   └── main.tsx            # Entry point
├── public/                 # Static assets
├── .env.development        # Dev environment vars
├── .env.production         # Prod environment vars
├── package.json
├── tsconfig.json
└── vite.config.ts
```

## Environment Variables

Create `.env.local` to override defaults:

```bash
VITE_API_URL=http://localhost:8000
```

## Backend API Integration

The frontend expects the following API endpoints:

- `GET /api/status` - Pipeline status and queue stats
- `GET /api/metrics/system` - Current system metrics
- `GET /api/metrics/system/history` - Historical metrics
- `GET /api/qa` - QA artifacts
- `GET /api/qa/file/{group}/{name}` - Serve QA files

See `src/api/types.ts` for complete interface definitions.

## Features

### Implemented (Phase 1)

- [x] Dashboard with pipeline status
- [x] System health metrics
- [x] Recent observations table
- [x] Real-time polling (10s refresh)
- [x] Dark mode optimized for astronomy

### Planned (Phase 2-4)

- [ ] ESE candidate panel with >5σ auto-flagging
- [ ] Mosaic gallery (display existing mosaics)
- [ ] Source monitoring table with NVSS IDs
- [ ] Flux timeseries plots
- [ ] Sky coverage visualization
- [ ] FITS image viewer
- [ ] Slack alert integration

## Development Notes

### Ubuntu 18.x Compatibility

This project uses the `casa6` conda environment which provides Node.js v22.6.0.
While Vite officially requires v22.12.0+, v22.6.0 works fine for our use case.
If you encounter issues:

1. Use Docker alternative:

   ```bash
   docker run -it -v /data/dsa110-contimg:/workspace -w /workspace/frontend node:22 npm install
   ```

2. Or upgrade Node in a separate conda env (not recommended on Ubuntu 18.x)

### API Connection Issues

If frontend can't connect to backend:

1. Check backend is running: `curl http://localhost:8000/api/status`
2. Check CORS settings in FastAPI backend
3. Verify `.env.development` has correct `VITE_API_URL`

### TypeScript Errors

```bash
# Run type checking
conda run -n casa6 npm run type-check

# Check linting
conda run -n casa6 npm run lint
```

## Deployment

### Static Build (Nginx/Apache)

```bash
conda run -n casa6 npm run build
# Serve dist/ directory
```

### With FastAPI Backend

```python
# In api/routes.py
from fastapi.staticfiles import StaticFiles

app.mount("/ui", StaticFiles(directory="frontend/dist", html=True), name="ui")
```

Access at: http://your-server/ui

## Contributing

1. Create feature branch
2. Make changes with TypeScript type safety
3. Test locally with `npm run dev`
4. Build and verify: `npm run build && npm run preview`
5. Submit PR

## License

Internal project - DSA-110 @ Caltech
