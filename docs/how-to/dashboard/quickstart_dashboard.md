# Dashboard Quick Start

## TL;DR

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

## What You Get

- **Dashboard** - Pipeline status, system health, ESE alerts
- **Mosaics** - Time-range queries, generation, gallery view
- **Sources** - Search by NVSS ID, flux timeseries, AG Grid table
- **Sky View** - Coordinate navigation, FITS viewer placeholder

## Features at a Glance

### ESE Detection (5σ threshold)

Auto-flagging for extreme scattering events with live monitoring.

### Mosaic Generator

Query hour-long mosaics by UTC time range, view thumbnails, download FITS/PNG.

### Source Monitoring

High-performance AG Grid table with 10,000+ row capacity, interactive Plotly
charts.

### Real-Time Updates

10-second polling for pipeline status, system metrics, and variability alerts.

## Documentation

- **User Guide:** [Dashboard Quick Start](dashboard-quickstart.md)
- **Development:** [Dashboard Development](dashboard-development.md)
- **API Reference:**
  [../reference/dashboard_backend_api.md](../reference/dashboard_backend_api.md)

## Tech Stack

React 18 + TypeScript + Vite + Material-UI + React Query + Plotly.js + AG Grid

## Troubleshooting

**Dashboard not loading?**

1. Check both services are running: `ps aux | grep -E "node.*vite|uvicorn"`
2. Test backend: `curl http://localhost:8000/api/status`
3. Hard refresh browser: Ctrl+Shift+R

**CORS errors?** CORS middleware is enabled in
`src/dsa110_contimg/api/routes.py` for localhost.

**Need help?** See full [Dashboard Quick Start](dashboard-quickstart.md) or
[Troubleshooting](../troubleshooting/frontend-restart-needed.md).
