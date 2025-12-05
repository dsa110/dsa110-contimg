# Dashboard Guide

The DSA-110 web dashboard provides real-time monitoring, data visualization, and pipeline control.

## Accessing the Dashboard

| Environment | URL                       |
| ----------- | ------------------------- |
| Production  | http://localhost:3210/ui/ |
| Development | http://localhost:5173     |

## Main Dashboard

**URL:** `/dashboard`

The main dashboard provides an overview of pipeline health and activity:

- **Pipeline Status Panel**: Queue statistics, active calibrations, recent observations
- **System Health Panel**: CPU, memory, disk usage
- **ESE Candidates Panel**: Real-time variability alerts (5σ threshold)

## Observation Timeline

**URL:** `/observations`

Interactive timeline for exploring observations:

- Interactive timeline of observations
- Filter by time range, calibrator, status
- Quick access to MS and image files
- Click observations to view details

## Image Gallery

**URL:** `/images`

Browse and download pipeline images:

- Grid view of all images
- Filter by time range, source, quality
- Download FITS files directly
- Quick preview with zoom

## Mosaic Gallery

**URL:** `/mosaics`

View and create mosaic products:

- Time-range query interface
- Mosaic metadata (source count, noise, image count)
- Create new mosaics from time ranges
- Download options (FITS, PNG)

## Control Panel

**URL:** `/control-panel`

Administrative controls for pipeline operation:

- Manual pipeline execution
- Calibration controls
- Imaging controls
- Service restart buttons

> **Note:** Some operations require authentication.

## Running Dashboard Persistently

### Using tmux (Recommended for Development)

```bash
# Start in tmux session
bash /data/dsa110-contimg/scripts/start-dashboard-tmux.sh

# Attach to session
tmux attach -t dsa110-dashboard

# Detach (keeps running): Ctrl+B, then D
```

### Using systemd (Production)

```bash
# Install and start service
sudo systemctl enable --now dsa110-contimg-dashboard

# Check status
sudo systemctl status dsa110-contimg-dashboard
```

## Port Reference

| Port | Service                | Environment |
| ---- | ---------------------- | ----------- |
| 3210 | Dashboard (production) | Production  |
| 5173 | Vite dev server        | Development |
| 6006 | Storybook              | Development |
| 8000 | FastAPI backend        | Both        |

## Related Documentation

- [Streaming Pipeline Operations](../../backend/docs/ops/streaming-pipeline.md) - Service management
- [Visualization Guide](visualization.md) - CARTA integration for FITS viewing
- [Troubleshooting](../TROUBLESHOOTING.md) - Common issues
