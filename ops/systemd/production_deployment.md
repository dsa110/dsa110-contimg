# Production Deployment Guide

**Date:** 2025-11-13  
**Status:** complete  
**Related:** [Infrastructure Improvements](infrastructure_improvements.md),
[Testing Results](testing_results.md)

---

## Overview

This guide covers production deployment of the DSA-110 Continuum Imaging
Pipeline dashboard and API services.

## Prerequisites

- casa6 conda environment installed at `/opt/miniforge/envs/casa6`
- Systemd service manager
- Environment file configured at `/data/dsa110-contimg/ops/systemd/contimg.env`

## Service Architecture

### Dashboard Service (`dsa110-contimg-dashboard.service`)

- **Purpose**: Serves the React frontend application
- **Port**: Configured via `CONTIMG_DASHBOARD_PORT` (default: 3210)
- **Mode**: Production build (static files)
- **Resource Limits**:
  - Memory: 2GB max, 1.5GB high watermark
  - CPU: 200% quota (2 cores)

### API Service (`dsa110-contimg-api.service`)

- **Purpose**: FastAPI backend serving REST API and WebSocket endpoints
- **Port**: Configured via `CONTIMG_API_PORT` (default: 8000)
- **Resource Limits**:
  - Memory: 4GB max, 3GB high watermark
  - CPU: 300% quota (3 cores)

## Deployment Steps

### 1. Build Frontend for Production

```bash
cd /data/dsa110-contimg
./scripts/build-dashboard-production.sh
```

This will:

- Install/update npm dependencies
- Run TypeScript type checking
- Build optimized production bundle
- Output to `frontend/dist/`

### 2. Install Systemd Services

```bash
# Copy service files to systemd directory
sudo cp /data/dsa110-contimg/ops/systemd/dsa110-contimg-*.service /etc/systemd/system/

# Reload systemd configuration
sudo systemctl daemon-reload
```

### 3. Configure Environment

Edit `/data/dsa110-contimg/ops/systemd/contimg.env` to set:

- `CONTIMG_DASHBOARD_PORT` (default: 3210)
- `CONTIMG_API_PORT` (default: 8000)
- Other pipeline configuration variables

### 4. Enable and Start Services

```bash
# Enable services to start on boot
sudo systemctl enable dsa110-contimg-api.service
sudo systemctl enable dsa110-contimg-dashboard.service

# Start services
sudo systemctl start dsa110-contimg-api.service
sudo systemctl start dsa110-contimg-dashboard.service
```

### 5. Verify Services

```bash
# Check service status
sudo systemctl status dsa110-contimg-api.service
sudo systemctl status dsa110-contimg-dashboard.service

# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:3210/index.html

# View logs
sudo journalctl -u dsa110-contimg-api.service -f
sudo journalctl -u dsa110-contimg-dashboard.service -f
```

## Health Checks

### API Health Endpoint

```bash
curl http://localhost:8000/health
```

Returns:

```json
{
  "status": "healthy",
  "service": "dsa110-contimg-api",
  "version": "0.1.0",
  "timestamp": "2025-01-XX...",
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "disk_usage": {...}
  },
  "database": "connected"
}
```

### Dashboard Health Check

```bash
curl http://localhost:3210/index.html
```

Should return the dashboard HTML.

### Health Check Scripts

```bash
# API health check
/data/dsa110-contimg/scripts/health-check-api.sh

# Dashboard health check
/data/dsa110-contimg/scripts/health-check-dashboard.sh
```

## Service Management

### Restart Services

```bash
sudo systemctl restart dsa110-contimg-api.service
sudo systemctl restart dsa110-contimg-dashboard.service
```

### Stop Services

```bash
sudo systemctl stop dsa110-contimg-api.service
sudo systemctl stop dsa110-contimg-dashboard.service
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u dsa110-contimg-api.service -f
sudo journalctl -u dsa110-contimg-dashboard.service -f

# Log files (also written to)
tail -f /data/dsa110-contimg/state/logs/dsa110-contimg-api.out
tail -f /data/dsa110-contimg/state/logs/dsa110-contimg-dashboard.out
```

## Resource Limits

Services are configured with systemd resource limits to prevent resource
exhaustion:

- **Dashboard**: 2GB memory max, 2 CPU cores
- **API**: 4GB memory max, 3 CPU cores

Adjust limits in service files if needed.

## Security Features

- `NoNewPrivileges=true`: Prevents privilege escalation
- `PrivateTmp=true`: Isolated temporary directories
- `ProtectSystem=strict`: Read-only system directories
- `ProtectHome=true`: Protected home directories
- `ReadWritePaths`: Explicit write permissions only where needed

## Troubleshooting

### Service Won't Start

1. Check logs: `sudo journalctl -u dsa110-contimg-*.service -n 50`
2. Verify environment file: `cat /data/dsa110-contimg/ops/systemd/contimg.env`
3. Check file permissions
4. Verify casa6 environment: `/opt/miniforge/envs/casa6/bin/python --version`

### Build Fails

1. Ensure casa6 npm is available: `/opt/miniforge/envs/casa6/bin/npm --version`
2. Check disk space: `df -h`
3. Review build logs in `/data/dsa110-contimg/state/logs/`

### Health Check Fails

1. Verify service is running: `sudo systemctl status dsa110-contimg-api.service`
2. Check port conflicts: `sudo netstat -tulpn | grep :8000`
3. Review service logs for errors

## Next Steps

For production deployment, consider:

1. **Reverse Proxy**: Set up nginx/traefik for HTTPS and load balancing
2. **HTTPS/TLS**: Configure SSL certificates
3. **Monitoring**: Integrate with monitoring tools (Prometheus, Grafana)
4. **Backup**: Set up automated backups of state databases
5. **High Availability**: Consider multiple instances with load balancing
