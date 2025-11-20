# Development Environment Analysis Report

**Date:** 2025-11-12  
**System:** lxd110h17  
**User:** ubuntu

---

## Services Identified

### Backend API

- **Status:** ❌ **NOT RUNNING**
- **Port:** `8000` (default, configurable via `CONTIMG_API_PORT`)
- **Process:** None (defunct processes found from Nov 3)
- **Start command:**
  ```bash
  cd /data/dsa110-contimg
  source ops/systemd/contimg.env
  PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000
  ```
- **Config location:** `ops/systemd/contimg.env` (`CONTIMG_API_PORT=8000`)
- **Entry point:** `src/dsa110_contimg/api/__init__.py` (exposes `app`)
- **Systemd service:** `ops/systemd/contimg-api.service` (available but not
  active)

### Frontend Dev Server

- **Status:** ✅ **RUNNING**
- **Port:** `5173`
- **Process:** Multiple Node/Vite processes running
  - PID 2151109: `node /app/frontend/node_modules/.bin/vite` (root user,
    Docker?)
  - PID 11829: `node /data/dsa110-contimg/frontend/node_modules/.bin/vite`
    (ubuntu user)
  - PID 24626: `node /data/dsa110-contimg/frontend/node_modules/.bin/vite`
    (ubuntu user)
- **Start command:** `cd /data/dsa110-contimg/frontend && npm run dev`
- **Config location:** `frontend/vite.config.ts` (`server.port: 5173`)
- **API Proxy:** Proxies `/api/*` to `http://127.0.0.1:8000`
- **Response:** HTTP 200 OK (service accessible)

### Port 8111

- **Status:** ⚪ **NOT IN USE** (Available)
- **Purpose:** Unknown (not configured in project)

### Port 9090

- **Status:** ⚪ **NOT IN USE** (Available)
- **Purpose:** Unknown (not configured in project)

### Port 3000

- **Status:** ✅ **IN USE**
- **Purpose:** Grafana (Docker container `docker-grafana-1`)
- **Process:** Docker proxy (PID 2969947)
- **Note:** Not related to DSA-110 dashboard

### Port 8080

- **Status:** ✅ **IN USE**
- **Purpose:** DSA-110 Pipeline (Docker container `dsa110-pipeline`)
- **Process:** Docker proxy (PID 3027357)
- **Note:** Related to pipeline, not dashboard API

---

## Files Created

- ✅ `docs/development/DEVELOPMENT_SETUP.md` - Comprehensive setup guide (400+
  lines)

---

## Current Service Status Summary

| Service      | Port | Status         | Process                 | Notes                       |
| ------------ | ---- | -------------- | ----------------------- | --------------------------- |
| Backend API  | 8000 | ❌ Not Running | None                    | Needs to be started         |
| Frontend Dev | 5173 | ✅ Running     | Multiple Vite instances | Multiple instances detected |
| Grafana      | 3000 | ✅ Running     | Docker                  | Not part of dashboard       |
| Pipeline     | 8080 | ✅ Running     | Docker                  | Related service             |
| Port 8111    | 8111 | ⚪ Available   | None                    | Not configured              |
| Port 9090    | 9090 | ⚪ Available   | None                    | Not configured              |

---

## Key Findings

### Backend API

1. **Not Currently Running:**
   - Port 8000 is not listening
   - Defunct uvicorn processes found (from Nov 3) - need cleanup
   - API needs to be started manually

2. **Configuration Found:**
   - Default port: 8000 (in `ops/systemd/contimg.env`)
   - Startup command: Uses casa6 Python environment
   - Systemd service available but not active

3. **Startup Options:**
   - Manual: Direct uvicorn command
   - Screen: `scripts/start-dashboard-screen.sh`
   - Tmux: `scripts/start-dashboard-tmux.sh`
   - Systemd: `ops/systemd/contimg-api.service` (for production)

### Frontend Dev Server

1. **Multiple Instances Running:**
   - At least 3 Vite processes detected
   - One running as root (likely Docker)
   - Two running as ubuntu user
   - All listening on port 5173

2. **Configuration:**
   - Port 5173 configured in `vite.config.ts`
   - API proxy configured to `http://127.0.0.1:8000`
   - Environment files present (`.env.local`, `.env.development`)

3. **Accessible:**
   - Service responds with HTTP 200 OK
   - Can be accessed at `http://localhost:5173`

### Port Usage

1. **Development Ports:**
   - 8000: Backend API (not running)
   - 5173: Frontend dev server (running)

2. **Other Services:**
   - 3000: Grafana (Docker)
   - 8080: Pipeline (Docker)

3. **Available Ports:**
   - 8111: Available
   - 9090: Available

---

## Next Steps for Human

### Immediate Actions

1. **Start Backend API:**

   ```bash
   cd /data/dsa110-contimg
   source ops/systemd/contimg.env
   PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000
   ```

2. **Verify API is Running:**

   ```bash
   curl http://localhost:8000/api/status
   # Should return JSON response
   ```

3. **Clean Up Defunct Processes:**

   ```bash
   # Check for defunct processes
   ps aux | grep defunct | grep uvicorn

   # Kill if needed (replace PID)
   kill -9 <PID>
   ```

4. **Review Multiple Frontend Instances:**

   ```bash
   # Check all Vite processes
   ps aux | grep vite

   # Consider consolidating to single instance
   # Kill unnecessary instances if needed
   ```

### Testing Steps

1. **Test Backend API:**
   - Start API (see above)
   - Run curl tests from `docs/reference/image_filters_manual_testing_guide.md`
   - Verify working filters respond quickly
   - Verify experimental filters work (even if slow)

2. **Test Frontend:**
   - Access `http://localhost:5173/sky`
   - Open DevTools → Console
   - Test filters as documented
   - Verify URL synchronization

3. **Test Port Forwarding (if accessing remotely):**
   - Set up SSH port forwarding
   - Test from local machine
   - Verify both services accessible

---

## Ready for Manual Testing?

**Status:** ⚠️ **PARTIALLY READY**

### What's Ready:

- ✅ Frontend dev server is running and accessible
- ✅ Configuration files identified and documented
- ✅ Setup guide created with exact commands
- ✅ Troubleshooting guide included

### What's Needed:

- ❌ Backend API needs to be started
- ⚠️ Multiple frontend instances should be reviewed
- ⚠️ Defunct processes should be cleaned up

### To Proceed with Testing:

1. **Start Backend API** (see commands above)
2. **Verify API responds** (`curl http://localhost:8000/api/status`)
3. **Test Image Filtering** (follow
   `docs/reference/image_filters_manual_testing_guide.md`)
4. **Test Frontend UI** (access `http://localhost:5173/sky`)

### Estimated Time to Ready:

- **Backend startup:** 1-2 minutes
- **Verification:** 1 minute
- **Total:** ~3 minutes to be fully ready

---

## Configuration Summary

### Backend API Configuration

**File:** `ops/systemd/contimg.env`

```bash
CONTIMG_API_PORT=8000
```

**Startup Command:**

```bash
PYTHONPATH=/data/dsa110-contimg/src /opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000
```

**Systemd Service:** `ops/systemd/contimg-api.service`

- Uses environment file: `ops/systemd/contimg.env`
- Runs as: `ubuntu` user
- Auto-restart: Enabled

### Frontend Configuration

**File:** `frontend/vite.config.ts`

```typescript
server: {
  host: '0.0.0.0',
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: true,
    }
  }
}
```

**Startup Command:**

```bash
cd frontend && npm run dev
```

**Environment Files:**

- `.env.local`: Uses `/api` proxy (default)
- `.env.development`: Uses `http://localhost:8010` (override)

---

## Recommendations

1. **Consolidate Frontend Instances:**
   - Review why multiple Vite processes are running
   - Consider stopping unnecessary instances
   - Use single dev server for development

2. **Clean Up Defunct Processes:**
   - Remove defunct uvicorn processes
   - Consider using systemd or process managers for production

3. **Document Port Usage:**
   - Document what ports 8111 and 9090 are reserved for (if any)
   - Update port allocation documentation

4. **Automate Startup:**
   - Consider using systemd for development
   - Or use startup scripts (screen/tmux) for persistence

---

**Report Generated:** 2025-11-12  
**Next Review:** After backend API is started and tested
