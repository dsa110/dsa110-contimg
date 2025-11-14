# Infrastructure & Deployment Improvements

## Summary

This document outlines the production-ready infrastructure improvements made to
the DSA-110 Continuum Imaging Pipeline dashboard and API services.

## Changes Made

### 1. Production Build Scripts

**Created:**

- `/data/dsa110-contimg/scripts/build-dashboard-production.sh`
  - Builds frontend for production
  - Uses casa6 npm environment
  - Validates build output
  - Logs build process

- `/data/dsa110-contimg/scripts/serve-dashboard-production.sh`
  - Serves built static files
  - Uses Python http.server (available in casa6)
  - Configurable port via environment variable

### 2. Enhanced Systemd Services

**Updated:**

- `dsa110-contimg-dashboard.service`
  - **Before**: Dev mode (`npm run dev`)
  - **After**: Production build + static file serving
  - Added resource limits (2GB memory, 2 CPU cores)
  - Added security hardening (NoNewPrivileges, PrivateTmp, etc.)
  - ExecStartPre builds before serving

- `dsa110-contimg-api.service`
  - Added resource limits (4GB memory, 3 CPU cores)
  - Added security hardening
  - Improved restart policies with rate limiting

### 3. Enhanced Health Check Endpoint

**Updated:** `/health` endpoint in API

**Before:**

```json
{
  "status": "healthy",
  "service": "dsa110-contimg-api"
}
```

**After:**

```json
{
  "status": "healthy",
  "service": "dsa110-contimg-api",
  "version": "0.1.0",
  "timestamp": "2025-01-XX...",
  "system": {
    "cpu_percent": 25.5,
    "memory_percent": 45.2,
    "disk_usage": {
      "total": ...,
      "used": ...,
      "free": ...,
      "percent": ...
    }
  },
  "database": "connected"
}
```

**Features:**

- System metrics (CPU, memory, disk) via psutil
- Database connectivity check
- Status degradation on database errors
- Graceful handling of missing dependencies

### 4. Health Check Scripts

**Created:**

- `/data/dsa110-contimg/scripts/health-check-api.sh`
  - Verifies API health endpoint
  - Returns exit code 0 if healthy, non-zero if unhealthy
  - Can be used by monitoring tools

- `/data/dsa110-contimg/scripts/health-check-dashboard.sh`
  - Verifies dashboard is serving files
  - Returns exit code 0 if healthy, non-zero if unhealthy

### 5. Documentation

**Created:**

- `PRODUCTION_DEPLOYMENT.md`: Complete deployment guide
- `INFRASTRUCTURE_IMPROVEMENTS.md`: This document

## Resource Limits

### Dashboard Service

- **MemoryMax**: 2GB (hard limit)
- **MemoryHigh**: 1.5GB (soft limit, triggers throttling)
- **CPUQuota**: 200% (2 CPU cores)
- **CPUWeight**: 100 (relative priority)

### API Service

- **MemoryMax**: 4GB (hard limit)
- **MemoryHigh**: 3GB (soft limit)
- **CPUQuota**: 300% (3 CPU cores)
- **CPUWeight**: 200 (higher priority than dashboard)

## Security Hardening

Both services now include:

- `NoNewPrivileges=true`: Prevents privilege escalation
- `PrivateTmp=true`: Isolated temporary directories
- `ProtectSystem=strict`: Read-only system directories
- `ProtectHome=true`: Protected home directories
- `ReadWritePaths`: Explicit write permissions only where needed

## Restart Policies

- `Restart=always`: Automatic restart on failure
- `RestartSec=5`: Wait 5 seconds before restart
- `StartLimitInterval=300`: Rate limit window (5 minutes)
- `StartLimitBurst=5`: Maximum 5 restarts per window

## Deployment Architecture

### Current Setup

- **Frontend**: Standalone static file server (port 3210)
- **Backend**: FastAPI/Uvicorn (port 8000)
- **Note**: FastAPI also serves static files at `/ui/` if build exists

### Options

1. **Standalone** (current): Dashboard service serves static files
2. **Integrated**: FastAPI serves dashboard at `/ui/` (remove dashboard service)

Both options are supported. The standalone option provides:

- Separation of concerns
- Independent scaling
- Easier debugging

## Next Steps (Future Improvements)

1. **Reverse Proxy**: Set up nginx/traefik
   - HTTPS/TLS termination
   - Load balancing
   - Request routing

2. **Monitoring Integration**
   - Prometheus metrics endpoint
   - Grafana dashboards
   - Alerting rules

3. **High Availability**
   - Multiple API instances
   - Load balancer configuration
   - Database replication

4. **Backup Strategy**
   - Automated database backups
   - Configuration backups
   - Disaster recovery plan

## Testing

To test the improvements:

```bash
# Build frontend
./scripts/build-dashboard-production.sh

# Test health checks
./scripts/health-check-api.sh
./scripts/health-check-dashboard.sh

# Test API health endpoint
curl http://localhost:8000/health | jq

# Verify services
sudo systemctl status dsa110-contimg-api.service
sudo systemctl status dsa110-contimg-dashboard.service
```

## Migration Notes

**From Dev to Production:**

1. Build frontend: `./scripts/build-dashboard-production.sh`
2. Update systemd services: Copy new service files
3. Reload systemd: `sudo systemctl daemon-reload`
4. Restart services: `sudo systemctl restart dsa110-contimg-*.service`

**Rollback:**

- Old service files are backed up (if using version control)
- Can revert to dev mode by changing ExecStart back to `npm run dev`
