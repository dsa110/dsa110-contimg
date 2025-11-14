# Dashboard Server

## Overview

Custom HTTP server for serving the DSA-110 dashboard production build with proper `/ui/` base path support.

## Problem

The production frontend build is configured with a `/ui/` base path (as defined in `frontend/vite.config.ts`). This is necessary because FastAPI serves the frontend at the `/ui/` endpoint. However, when using a standalone HTTP server, Python's standard `http.server` module doesn't handle this base path correctly, causing all asset references to fail with 404 errors.

## Solution

The `dashboard_server.py` script provides a custom HTTP request handler that:

1. **Strips `/ui/` prefix** from incoming requests
2. **Serves files correctly** from the `dist/` directory
3. **Handles client-side routing** by serving `index.html` for routes without file extensions
4. **Provides proper MIME types** and CORS headers for development

## Usage

### Standalone Execution

```bash
# Basic usage
python3 scripts/dashboard_server.py --port 3210 --directory frontend/dist

# Custom port
python3 scripts/dashboard_server.py --port 8080 --directory frontend/dist
```

### Via Production Serve Script

```bash
# Uses environment variable for port (default: 3210)
./scripts/serve-dashboard-production.sh

# Custom port via environment
CONTIMG_DASHBOARD_PORT=8080 ./scripts/serve-dashboard-production.sh
```

### Via Systemd Service

```bash
# Start the dashboard service
sudo systemctl start dsa110-contimg-dashboard.service

# Check status
sudo systemctl status dsa110-contimg-dashboard.service

# View logs
sudo journalctl -u dsa110-contimg-dashboard.service -f
```

## Path Translation

The server translates URLs as follows:

| Request URL                        | Filesystem Path          |
|------------------------------------|--------------------------|
| `/`                                | `index.html`             |
| `/ui/`                             | `index.html`             |
| `/ui/index.html`                   | `index.html`             |
| `/ui/assets/app.js`                | `assets/app.js`          |
| `/ui/js9/js9Prefs.json`            | `js9/js9Prefs.json`      |
| `/ui/some-route` (no extension)    | `index.html` (SPA route) |

## Testing

### Manual Testing

```bash
# Start the server
python3 scripts/dashboard_server.py --port 3210 --directory frontend/dist

# In another terminal, test endpoints
curl -I http://localhost:3210/ui/                    # Should return 200
curl -I http://localhost:3210/ui/assets/index.js     # Should return 200
curl -I http://localhost:3210/ui/js9/js9Prefs.json   # Should return 200
```

### Automated Testing

```bash
# Run unit tests
python3 tests/unit/test_dashboard_server.py
```

## Features

- **Base Path Support**: Correctly handles `/ui/` prefix in production builds
- **Client-Side Routing**: Serves `index.html` for SPA routes
- **CORS Headers**: Enables cross-origin requests for development
- **Proper MIME Types**: Automatically detects and serves correct content types
- **Security**: Prevents directory traversal attacks

## Deployment Modes

The DSA-110 dashboard can be deployed in two ways:

### 1. Integrated Mode (Recommended for Production)

FastAPI serves both the API and frontend:
- **Port**: 8000 (default)
- **URL**: `http://localhost:8000/ui/`
- **Service**: `dsa110-contimg-api.service`
- **Advantages**: Single service, shared origin (no CORS issues)

### 2. Standalone Mode

Separate HTTP server for frontend only:
- **Port**: 3210 (default)
- **URL**: `http://localhost:3210/ui/`
- **Service**: `dsa110-contimg-dashboard.service`
- **Advantages**: Independent scaling, simpler debugging

## Troubleshooting

### Assets Fail to Load (404 errors)

**Symptom**: Browser console shows 404 errors for `/ui/assets/*.js`

**Cause**: Using standard `python -m http.server` instead of `dashboard_server.py`

**Solution**: Use the custom dashboard server:
```bash
python3 scripts/dashboard_server.py --port 3210 --directory frontend/dist
```

### Page Shows Blank Screen

**Symptom**: Dashboard loads but shows blank page

**Possible Causes**:
1. API backend is not running (expected - dashboard needs API for data)
2. Browser console shows JavaScript errors

**Solution**: 
- Start the API server: `uvicorn dsa110_contimg.api:app --port 8000`
- Check browser console for specific errors

### Port Already in Use

**Symptom**: `OSError: [Errno 48] Address already in use`

**Solution**: 
```bash
# Find process using the port
lsof -i :3210

# Kill the process or use a different port
python3 scripts/dashboard_server.py --port 3211 --directory frontend/dist
```

## Related Files

- `scripts/dashboard_server.py` - Custom HTTP server implementation
- `scripts/serve-dashboard-production.sh` - Production serve script
- `scripts/build-dashboard-production.sh` - Production build script
- `frontend/vite.config.ts` - Vite configuration (defines `/ui/` base path)
- `ops/systemd/dsa110-contimg-dashboard.service` - Systemd service file

## References

- [Production Deployment Guide](../../ops/systemd/production_deployment.md)
- [Infrastructure Improvements](../../ops/systemd/infrastructure_improvements.md)
