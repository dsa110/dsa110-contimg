# Enabling CARTA in Production Dashboard

This guide explains how to enable CARTA (Cube Analysis and Rendering Tool for
Astronomy) integration in the production dashboard running on port 3210.

## Current Status

**CARTA is currently disabled** because:

1. CARTA environment variables are not configured in `.env.production`
2. Production dashboard needs to be rebuilt with CARTA configuration
3. CARTA backend service is not running (optional, but recommended)

## Prerequisites

1. **CARTA Backend** (optional but recommended):
   - CARTA backend server running and accessible
   - Default ports: 9002 (WebSocket), 9003 (HTTP frontend)
   - See [CARTA Testing Guide](./carta_testing_guide.md) for setup instructions

2. **Production Dashboard**:
   - Dashboard build script available: `scripts/build-dashboard-production.sh`
   - Dashboard serve script available: `scripts/serve-dashboard-production.sh`

## Step 1: Configure CARTA Environment Variables

Edit `frontend/.env.production`:

```bash
# CARTA Integration Configuration
# CARTA Backend WebSocket URL
VITE_CARTA_BACKEND_URL=ws://localhost:9002

# CARTA Frontend URL (for iframe integration)
VITE_CARTA_FRONTEND_URL=http://localhost:9003
```

**For production deployments**, replace `localhost` with the actual CARTA
backend hostname/IP:

```bash
# Example: CARTA backend on same machine
VITE_CARTA_BACKEND_URL=ws://lxd110h17:9002
VITE_CARTA_FRONTEND_URL=http://lxd110h17:9003

# Example: CARTA backend on different machine
VITE_CARTA_BACKEND_URL=ws://carta-backend.dsa110.org:9002
VITE_CARTA_FRONTEND_URL=http://carta-backend.dsa110.org:9003
```

## Step 2: Rebuild Production Dashboard

Vite environment variables (`VITE_*`) are embedded at build time, so the
dashboard must be rebuilt:

```bash
cd /data/dsa110-contimg
./scripts/build-dashboard-production.sh
```

This will:

- Clean previous build
- Install dependencies (if needed)
- Build frontend with CARTA environment variables
- Output to `frontend/dist/`

## Step 3: Restart Production Dashboard

After rebuilding, restart the production dashboard service:

### If using systemd service:

```bash
sudo systemctl restart contimg-dashboard
```

### If using Docker Compose:

```bash
docker compose restart dashboard
```

### If using manual serve script:

```bash
# Stop existing service (if running)
pkill -f "serve-dashboard-production"

# Start new service
./scripts/serve-dashboard-production.sh
```

## Step 4: Verify CARTA is Enabled

1. **Access Dashboard**: Navigate to `http://localhost:3210` (or your production
   URL)

2. **Navigate to CARTA Page**: Click "CARTA" in the navigation menu or go to
   `/carta`

3. **Check CARTA Configuration**:
   - CARTA page should load without errors
   - Backend URL should show the configured value (not default `localhost:9002`)
   - Frontend URL should show the configured value (not default
     `localhost:9003`)

4. **Test CARTA Connection** (if backend is running):
   - Select "WebSocket" integration mode
   - Check connection status (should show "Connected" if backend is accessible)
   - Try opening a FITS file

## Optional: Set Up CARTA Backend

If you want to use CARTA functionality, you need to run the CARTA backend:

### Option 1: Docker (Recommended)

```bash
# Pull CARTA backend image
docker pull cartavis/carta-backend:latest

# Run CARTA backend
docker run -d \
  --name carta-backend \
  -p 9002:3002 \
  -p 9003:3000 \
  cartavis/carta-backend:latest
```

### Option 2: From Source

See [CARTA Testing Guide](./carta_testing_guide.md) for detailed instructions.

### Verify CARTA Backend

```bash
# Check health endpoint
curl http://localhost:9002/api/health

# Check if ports are listening
netstat -tlnp | grep -E ":(9002|9003)"
```

## Troubleshooting

### CARTA Page Shows Default URLs

**Problem**: CARTA page still shows `localhost:9002` and `localhost:9003` even
after configuration.

**Solution**:

1. Verify `.env.production` has correct `VITE_CARTA_*` variables
2. Rebuild dashboard: `./scripts/build-dashboard-production.sh`
3. Restart dashboard service
4. Clear browser cache and hard refresh (Ctrl+Shift+R)

### CARTA Connection Fails

**Problem**: CARTA page shows "Disconnected" or connection errors.

**Possible Causes**:

1. CARTA backend is not running
2. Incorrect backend URL (wrong hostname/IP)
3. Network/firewall blocking ports 9002/9003
4. CORS issues (if backend is on different domain)

**Solution**:

1. Verify CARTA backend is running: `curl http://localhost:9002/api/health`
2. Check backend URL matches actual CARTA backend location
3. Verify ports 9002/9003 are accessible from dashboard host
4. Check browser console for connection errors

### Environment Variables Not Applied

**Problem**: Changes to `.env.production` don't take effect.

**Solution**:

- Vite environment variables are embedded at **build time**, not runtime
- You **must rebuild** the dashboard after changing `.env.production`
- Restart the dashboard service after rebuilding

## Integration Modes

The CARTA page supports two integration modes:

1. **Iframe Mode** (Option 1):
   - Embeds CARTA frontend in an iframe
   - Requires both CARTA backend and frontend running
   - Best for quick validation
   - Uses `VITE_CARTA_FRONTEND_URL`

2. **WebSocket Mode** (Option 2):
   - Native React component connecting directly to CARTA backend
   - Requires only CARTA backend running
   - Provides full integration with dashboard
   - Uses `VITE_CARTA_BACKEND_URL`

## Port Allocation

According to the port allocation strategy:

- **Port 9002**: CARTA Backend (WebSocket) - External Integrations range
  (9000-9099)
- **Port 9003**: CARTA Frontend (HTTP) - External Integrations range (9000-9099)

See [CARTA Port Allocation](./carta_port_allocation.md) for details.

## Summary

To enable CARTA in production:

1. ✅ Edit `frontend/.env.production` with CARTA URLs
2. ✅ Rebuild: `./scripts/build-dashboard-production.sh`
3. ✅ Restart dashboard service
4. ✅ (Optional) Start CARTA backend
5. ✅ Verify: Navigate to `/carta` page

CARTA is now enabled and ready to use!
