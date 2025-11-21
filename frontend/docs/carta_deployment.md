# CARTA Deployment Guide

**Date:** 2025-11-18  
**Type:** Deployment Documentation  
**Status:** ✅ Complete

---

## Overview

CARTA (Cube Analysis and Rendering Tool for Astronomy) is now deployed and
integrated with the DSA-110 dashboard. CARTA provides interactive visualization
of FITS images with advanced analysis capabilities.

---

## Current Deployment Status

### ✅ Active Services

- **CARTA Container:** `carta-backend` (running)
- **CARTA Version:** 5.0.3
- **Docker Image:** `cartavis/carta:latest`
- **Access URL:** http://localhost:9002/
- **Dashboard Integration:** http://localhost:3210/carta

### Port Configuration

- **Port 9002:** CARTA backend WebSocket API + frontend HTML
- **Port 9003:** _Not used_ (CARTA serves everything from port 9002)

### Data Volumes

The CARTA container has read-only access to:

- `/stage/dsa110-contimg` - Processed images and data
- `/data/dsa110-contimg` - Raw data and pipeline products

---

## Persistence Configuration

### Docker Restart Policy

The CARTA container is configured with `--restart unless-stopped`, which means:

- ✅ Survives system reboots
- ✅ Restarts automatically if it crashes
- ✅ Stays stopped only if manually stopped via `docker stop`

### Manual Control

```bash
# Check status
docker ps --filter "name=carta-backend"

# Stop CARTA
docker stop carta-backend

# Start CARTA
docker start carta-backend

# Restart CARTA
docker restart carta-backend

# View logs
docker logs carta-backend

# Remove container (will be recreated by dashboard if needed)
docker rm -f carta-backend
```

---

## Dashboard Integration

### Frontend Configuration

The dashboard's CARTA integration is configured in:

- **Default Backend URL:** `http://localhost:9002`
- **Default Frontend URL:** `http://localhost:9002` (same as backend)

### Integration Modes

The dashboard supports two integration modes:

1. **Iframe Mode (default):**
   - Embeds CARTA frontend via iframe
   - Full CARTA functionality
   - Component: `CARTAIframe.tsx`

2. **WebSocket Mode:**
   - Native React integration
   - Direct WebSocket connection
   - Component: `CARTAViewer.tsx`

### API Endpoints

The dashboard backend provides CARTA control endpoints:

- `GET /api/visualization/carta/status` - Check CARTA status
- `POST /api/visualization/carta/start` - Start CARTA services
- `POST /api/visualization/carta/stop` - Stop CARTA services
- `POST /api/visualization/carta/restart` - Restart CARTA services

---

## Accessing CARTA

### Via Dashboard

1. Navigate to: http://localhost:3210/carta
2. Select a FITS file from the file browser
3. Click to load the file in CARTA

### Direct Access

1. Navigate to: http://localhost:9002/
2. CARTA will open with default settings
3. Use the file browser to select FITS images from mounted volumes

---

## Troubleshooting

### Container Not Running

```bash
# Check container status
docker ps -a --filter "name=carta-backend"

# View container logs
docker logs carta-backend

# Restart container
docker restart carta-backend
```

### Port Conflicts

If port 9002 is already in use:

```bash
# Find process using port
sudo netstat -tlnp | grep :9002
# or
sudo ss -tlnp | grep :9002

# Stop the CARTA container
docker stop carta-backend

# Remove and recreate with different port
docker rm carta-backend
docker run -d \
  --name carta-backend \
  --restart unless-stopped \
  -p 9010:3002 \
  -v /stage/dsa110-contimg:/stage/dsa110-contimg:ro \
  -v /data/dsa110-contimg:/data/dsa110-contimg:ro \
  cartavis/carta:latest

# Update dashboard configuration to use new port
```

### Frontend Not Loading

1. Verify port 9002 is accessible: `curl http://localhost:9002/`
2. Check container logs: `docker logs carta-backend`
3. Verify data volumes are mounted: `docker inspect carta-backend`
4. Restart container: `docker restart carta-backend`

### Image Files Not Visible

- Ensure FITS files are in mounted directories:
  - `/stage/dsa110-contimg/`
  - `/data/dsa110-contimg/`
- Check container volume mounts: `docker inspect carta-backend`
- Verify file permissions (container runs as `cartauser`)

---

## Architecture

### CARTA Container Structure

```
carta-backend container
├── Backend WebSocket Server (port 3002 -> host 9002)
├── Frontend Static Files
│   └── Served from /usr/share/carta/frontend
├── Data Mounts (read-only)
│   ├── /stage/dsa110-contimg
│   └── /data/dsa110-contimg
└── Logs: /home/cartauser/.carta/log/carta.log
```

### Dashboard Integration Flow

```
User -> Dashboard (/carta) -> CARTAIframe/CARTAViewer -> CARTA Backend (9002)
                                                           |
                                                           v
                                                    FITS Files (mounted volumes)
```

---

## Security Considerations

### Data Access

- CARTA container has **read-only** access to data directories
- Container runs as non-root user (`cartauser`)
- No write access to pipeline data

### Network Exposure

- CARTA is exposed on localhost only (0.0.0.0:9002)
- For remote access, use SSH tunneling or reverse proxy
- No authentication by default (token-based access available)

### Recommended for Production

```bash
# Use authentication token
# (CARTA generates a token - see logs for URL)

# Or restrict to localhost only
docker run -d \
  --name carta-backend \
  --restart unless-stopped \
  -p 127.0.0.1:9002:3002 \
  -v /stage/dsa110-contimg:/stage/dsa110-contimg:ro \
  -v /data/dsa110-contimg:/data/dsa110-contimg:ro \
  cartavis/carta:latest
```

---

## Maintenance

### Updating CARTA

```bash
# Stop and remove current container
docker stop carta-backend
docker rm carta-backend

# Pull latest image
docker pull cartavis/carta:latest

# Recreate container
docker run -d \
  --name carta-backend \
  --restart unless-stopped \
  -p 9002:3002 \
  -p 9003:3000 \
  -v /stage/dsa110-contimg:/stage/dsa110-contimg:ro \
  -v /data/dsa110-contimg:/data/dsa110-contimg:ro \
  cartavis/carta:latest

# Verify new version
docker logs carta-backend | grep "Version"
```

### Monitoring

```bash
# Check container health
docker ps --filter "name=carta-backend"

# Monitor logs in real-time
docker logs -f carta-backend

# Check resource usage
docker stats carta-backend
```

---

## References

- **CARTA Website:** https://cartavis.org/
- **CARTA GitHub:** https://github.com/CARTAvis/carta-backend
- **Docker Image:** https://hub.docker.com/r/cartavis/carta
- **Documentation:** https://carta.readthedocs.io/

---

## Related Files

- `src/components/CARTA/CARTAIframe.tsx` - Iframe integration component
- `src/components/CARTA/CARTAViewer.tsx` - WebSocket integration component
- `src/pages/CARTAPage.tsx` - CARTA dashboard page
- `src/dsa110_contimg/api/carta_service.py` - Backend service manager
- `src/dsa110_contimg/api/visualization_routes.py` - API endpoints
