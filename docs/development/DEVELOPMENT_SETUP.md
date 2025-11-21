# DSA-110 Dashboard Development Setup

**Last Updated:** 2025-11-12  
**Target System:** lxd110h17  
**User:** ubuntu

## Prerequisites

- SSH access to lxd110h17
- Python 3.9+ with casa6 environment (`/opt/miniforge/envs/casa6/bin/python`)
- Node.js 20.19+ (for frontend)
- Port forwarding configured (if accessing from local machine)

## Quick Start

### Start Backend API

```bash
# On lxd110h17
cd /data/dsa110-contimg

# Source environment variables
source ops/systemd/contimg.env

# Start FastAPI server
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port ${CONTIMG_API_PORT:-8000}

# Expected output:
# INFO:     Started server process
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
# INFO:     Uvicorn running on http://0.0.0.0:8000

# Verify it's running:
curl http://localhost:8000/api/status
```

**Alternative: Use startup scripts**

```bash
# Using screen (persists after SSH disconnect)
./scripts/start-dashboard-screen.sh

# Using tmux (persists after SSH disconnect)
./scripts/start-dashboard-tmux.sh
```

### Start Frontend Dev Server

```bash
# On lxd110h17 (separate terminal)
cd /data/dsa110-contimg/frontend

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev

# Expected output:
#   VITE v5.x.x  ready in xxx ms
#   ➜  Local:   http://localhost:5173/
#   ➜  Network: http://0.0.0.0:5173/

# Verify it's running:
curl http://localhost:5173
```

## Port Configuration

### Backend API

- **Port:** `8000` (default, configurable via `CONTIMG_API_PORT`)
- **Process:** `uvicorn` (ASGI server)
- **Config location:** `ops/systemd/contimg.env` (`CONTIMG_API_PORT=8000`)
- **Startup command:**
  `/opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000`
- **Entry point:** `src/dsa110_contimg/api/__init__.py` (exposes `app`)

### Frontend Dev Server

- **Port:** `3210` (configured in `frontend/vite.config.ts` and
  `config/ports.yaml`)
- **Process:** `vite` (via `npm run dev`)
- **Config location:** `frontend/vite.config.ts` (uses `VITE_PORT` env var,
  defaults to 3210)
- **Startup command:** `npm run dev` (or `npm run dev:safe` for duplicate
  prevention)
- **API Proxy:** Proxies `/api/*` requests to `http://127.0.0.1:8000`

### Other Services

- **Port 3000:** Grafana (Docker container `docker-grafana-1`)
- **Port 8080:** DSA-110 Pipeline (Docker container `dsa110-pipeline`)
- **Port 8111:** Not in use (available)
- **Port 9090:** Not in use (available)

## Remote Access (SSH Port Forwarding)

If accessing from a local machine, set up SSH port forwarding:

### Option 1: Command Line

```bash
# On your LOCAL machine (not lxd110h17)
ssh -L 8000:localhost:8000 \
    -L 3210:localhost:3210 \
    ubuntu@lxd110h17
```

### Option 2: SSH Config

```bash
# Add to ~/.ssh/config on your LOCAL machine
Host lxd110h17
    HostName lxd110h17
    User ubuntu
    LocalForward 8000 localhost:8000
    LocalForward 3210 localhost:3210
```

Then connect: `ssh lxd110h17`

### Verify Port Forwarding

```bash
# On your LOCAL machine
curl http://localhost:8000/api/status

# Should return JSON (not "connection refused")
# Example response:
# {"status":"ok","version":"..."}
```

## Testing the Image Filtering Feature

### Backend API Tests

```bash
# Test working filters (should be fast <200ms)
curl "http://localhost:8000/api/images?noise_max=0.001&limit=5"
curl "http://localhost:8000/api/images?start_date=2025-01-01T00:00:00&limit=5"
curl "http://localhost:8000/api/images?end_date=2025-12-31T23:59:59&limit=5"

# Test combined working filters
curl "http://localhost:8000/api/images?noise_max=0.001&start_date=2025-01-01T00:00:00&limit=10"

# Test experimental filters (may be slow 1-5s)
curl "http://localhost:8000/api/images?dec_min=40&dec_max=50&limit=5"
curl "http://localhost:8000/api/images?has_calibrator=true&limit=5"

# Test edge cases (should not crash)
curl "http://localhost:8000/api/images?start_date=not-a-date&limit=5"
curl "http://localhost:8000/api/images?dec_min=-100&dec_max=200&limit=5"
```

**Expected Results:**

- Working filters: Fast response (<200ms), accurate results
- Experimental filters: Slower response (1-5s acceptable), may have pagination
  issues
- Edge cases: No crashes, graceful handling

### Frontend UI Tests

1. **Open browser:** `http://localhost:5173/sky` (or forwarded port)
2. **Open DevTools** (F12) → Console tab
3. **Verify no JavaScript errors**
4. **Test filters** as described in
   `docs/reference/image_filters_manual_testing_guide.md`

**Quick UI Test Checklist:**

- [ ] Navigate to Sky View page (`/sky`)
- [ ] ImageBrowser component loads without errors
- [ ] Expand/collapse advanced filters works
- [ ] Date range pickers work
- [ ] Noise threshold filter works
- [ ] Declination slider works (may be slow)
- [ ] Calibrator checkbox works
- [ ] Clear All Filters button works
- [ ] URL parameters sync correctly

## Environment Variables

### Backend API

**File:** `ops/systemd/contimg.env`

```bash
# API Port
CONTIMG_API_PORT=8000

# Database paths
PIPELINE_STATE_DB=/data/dsa110-contimg/state/pipeline.sqlite3
PRODUCTS_DB=/data/dsa110-contimg/state/products.sqlite3
CAL_REGISTRY_DB=/data/dsa110-contimg/state/cal_registry.sqlite3
```

**Usage:**

```bash
source ops/systemd/contimg.env
# Now $CONTIMG_API_PORT is set
```

### Frontend

**Files:**

- `frontend/.env.local` - Local development (uses `/api` proxy)
- `frontend/.env.development` - Development environment
- `frontend/.env.production` - Production builds

**Key variables:**

- `VITE_API_URL` - API base URL (defaults to `/api` for proxy)
- `API_PROXY_TARGET` - Override API proxy target (defaults to
  `http://127.0.0.1:8000`)

## Troubleshooting

### Backend won't start

**Problem:** Port already in use

```bash
# Check if port already in use
sudo lsof -i :8000

# Kill process if needed (replace PID)
sudo kill -9 <PID>

# Or use different port
CONTIMG_API_PORT=8001 uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8001
```

**Problem:** Python environment not found

```bash
# Check Python environment
which python
# Should show: /opt/miniforge/envs/casa6/bin/python

# Verify casa6 environment exists
test -x /opt/miniforge/envs/casa6/bin/python && echo "OK" || echo "MISSING"

# Activate conda environment if needed
conda activate casa6
```

**Problem:** Syntax errors

```bash
# Check for syntax errors
/opt/miniforge/envs/casa6/bin/python -m py_compile src/dsa110_contimg/api/__init__.py

# Check imports
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/python -c "from dsa110_contimg.api import app; print('OK')"
```

**Problem:** Module not found

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/data/dsa110-contimg/src

# Or use inline
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000
```

### Frontend won't start

**Problem:** Port already in use

```bash
# Check if port already in use
sudo lsof -i :3210

# Kill process if needed
sudo kill -9 <PID>

# Or use different port
CONTIMG_FRONTEND_DEV_PORT=3211 npm run dev
```

**Problem:** Node version incompatible

```bash
# Check Node version
node --version
# Should be 20.19+ for Vite 5

# Update Node if needed (using nvm)
nvm install 20
nvm use 20
```

**Problem:** Dependencies missing

```bash
# Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Problem:** API proxy not working

```bash
# Check API proxy target in vite.config.ts
# Default: http://127.0.0.1:8000

# Override if needed
API_PROXY_TARGET=http://localhost:8000 npm run dev
```

### Cannot access from local machine

**Problem:** SSH port forwarding not working

```bash
# On LOCAL machine, verify SSH tunnel
ps aux | grep ssh | grep 8000

# Test connection
curl http://localhost:8000/api/status

# If fails, restart SSH with forwarding
ssh -L 8000:localhost:8000 -L 3210:localhost:3210 ubuntu@lxd110h17
```

**Problem:** Server not listening on correct interface

```bash
# Backend should listen on 0.0.0.0 (all interfaces)
# Check startup command includes --host 0.0.0.0

# Frontend should listen on 0.0.0.0 (configured in vite.config.ts)
# Check: server.host: '0.0.0.0'
```

**Problem:** Firewall blocking ports

```bash
# Check firewall rules
sudo iptables -L -n | grep 8000
sudo iptables -L -n | grep 5173

# If needed, allow ports (example for ufw)
sudo ufw allow 8000/tcp
sudo ufw allow 5173/tcp
```

### API returns 404 for /api/images

**Problem:** Routes not registered

```bash
# Check router registration
grep "include_router.*images" src/dsa110_contimg/api/routes.py

# Verify images router exists
ls src/dsa110_contimg/api/routers/images.py

# Test base endpoint first
curl http://localhost:8000/api/status
```

**Problem:** Database not accessible

```bash
# Check database files exist
ls -la /data/dsa110-contimg/state/*.sqlite3

# Check permissions
ls -l /data/dsa110-contimg/state/products.sqlite3
```

### Frontend shows "Cannot connect to API"

**Problem:** API not running

```bash
# Check API is running
curl http://localhost:8000/api/status

# If fails, start API (see "Start Backend API" section)
```

**Problem:** Proxy configuration incorrect

```bash
# Check vite.config.ts proxy settings
cat frontend/vite.config.ts | grep -A10 "proxy"

# Verify API_PROXY_TARGET
echo $API_PROXY_TARGET

# Test direct API access
curl http://127.0.0.1:8000/api/status
```

## Production Deployment

### Systemd Services

**API Service:** `ops/systemd/contimg-api.service`

```bash
# Install service
sudo cp ops/systemd/contimg-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable contimg-api
sudo systemctl start contimg-api

# Check status
sudo systemctl status contimg-api

# View logs
sudo journalctl -u contimg-api -f
```

**Configuration:**

- Uses `ops/systemd/contimg.env` for environment variables
- Runs as `ubuntu` user
- Auto-restarts on failure

### Docker Deployment

See `ops/docker/README.md` for Docker deployment instructions.

**Key files:**

- `ops/docker/docker-compose.yml` - Docker Compose configuration
- `ops/docker/.env` - Docker environment variables

## Development Workflow

### Typical Development Session

1. **Start Backend:**

   ```bash
   cd /data/dsa110-contimg
   source ops/systemd/contimg.env
   PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Start Frontend (separate terminal):**

   ```bash
   cd /data/dsa110-contimg/frontend
   npm run dev
   ```

3. **Make code changes:**
   - Backend: Auto-reloads with `--reload` flag
   - Frontend: Hot module replacement (HMR) enabled

4. **Test changes:**
   - Backend: Use curl commands or browser DevTools Network tab
   - Frontend: Browser auto-refreshes on save

5. **Stop services:**
   - Backend: `Ctrl+C` in terminal
   - Frontend: `Ctrl+C` in terminal

### Persistent Development (Screen/Tmux)

**Using Screen:**

```bash
./scripts/start-dashboard-screen.sh
# Attach: screen -r dsa110-dashboard
# Detach: Ctrl+A then D
# Kill: screen -S dsa110-dashboard -X quit
```

**Using Tmux:**

```bash
./scripts/start-dashboard-tmux.sh
# Attach: tmux attach -t dsa110-dashboard
# Detach: Ctrl+B then D
# Kill: tmux kill-session -t dsa110-dashboard
```

## References

- **Backend API:** `src/dsa110_contimg/api/`
- **Frontend:** `frontend/src/`
- **API Routes:** `src/dsa110_contimg/api/routers/`
- **Startup Scripts:** `scripts/start-dashboard-*.sh`
- **Systemd Services:** `ops/systemd/`
- **Docker Config:** `ops/docker/`
- **Manual Testing Guide:**
  `docs/reference/image_filters_manual_testing_guide.md`
- **Implementation Status:**
  `docs/reference/image_filters_implementation_status.md`
- **Test Report:** `docs/reference/image_filters_test_report.md`

## Quick Reference Commands

```bash
# Start API
cd /data/dsa110-contimg && source ops/systemd/contimg.env && PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000

# Start Frontend
cd /data/dsa110-contimg/frontend && npm run dev

# Test API
curl http://localhost:8000/api/status

# Test Images Endpoint
curl "http://localhost:8000/api/images?limit=5"

# Check running services
sudo lsof -i :8000
sudo lsof -i :5173

# View API logs (if using systemd)
sudo journalctl -u contimg-api -f
```

---

**Last Updated:** 2025-11-12  
**Maintained by:** Development Team
