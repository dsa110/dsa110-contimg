# API Restart and Troubleshooting Guide

## Quick Reference: Restarting the API

The API runs in a **Docker container** using the `casa6` conda environment.

```bash
cd /data/dsa110-contimg/ops/docker
docker-compose restart api
```

To view logs:

```bash
docker logs contimg-api --tail 50 -f
```

---

## Architecture Overview

### API Deployment

- **Container**: `contimg-api`
- **Port**: 8010 (configurable via `CONTIMG_API_PORT`)
- **Conda Environment**: `casa6` (NOT `contimg`)
- **Python**: 3.11.13 (in `casa6` conda environment)
- **Framework**: FastAPI with uvicorn
- **Management**: Docker Compose
  (`/data/dsa110-contimg/ops/docker/docker-compose.yml`)

### Important Paths

- **Code**: `/data/dsa110-contimg/src/dsa110_contimg/api/routes.py`
- **Docker Compose**: `/data/dsa110-contimg/ops/docker/docker-compose.yml`
- **Environment Config**: `/data/dsa110-contimg/ops/docker/.env`
- **Systemd Config**: `/data/dsa110-contimg/ops/systemd/contimg.env`
- **Logs**: `/data/dsa110-contimg/state/logs/contimg-api.out` and `.err`

---

## Common Issues and Solutions

### Issue 1: API Can't Access MS Files (`MS not found`)

**Symptom**: API returns `404 MS not found` even though files exist on the host.

**Root Cause**: Docker container doesn't have `/scratch` mounted.

**Solution**: Ensure `/scratch` is mounted in `docker-compose.yml`:

```yaml
volumes:
  - ${REPO_ROOT}:/app:rw
  - ${CONTIMG_STATE_DIR}:${CONTIMG_STATE_DIR}:rw
  - ${CONTIMG_SCRATCH_DIR}:${CONTIMG_SCRATCH_DIR}:rw
  - /scratch:/scratch:ro # ← This line is required!
```

**Verify**:

```bash
docker exec contimg-api ls -ld /scratch/ms/timesetv3/caltables/
```

**Fix**:

1. Edit `/data/dsa110-contimg/ops/docker/docker-compose.yml`
2. Add `/scratch:/scratch:ro` to the API service volumes
3. Recreate container: `docker-compose up -d --force-recreate api`

---

### Issue 2: Wrong Conda Environment

**Symptom**: Service fails with "command not found" or Python version errors.

**Root Cause**: Systemd service or Docker config references wrong conda
environment.

**Important**: The API uses the **`casa6`** conda environment, NOT `contimg`.

**Docker**: Uses `casa6` automatically (configured in Dockerfile) **Systemd**:
Must explicitly use `/opt/miniforge/envs/casa6/bin/python3`

**Verify Conda Environment**:

```bash
# Check which Python the container uses
docker exec contimg-api which python3
docker exec contimg-api python3 --version

# Should show Python 3.11.13 from casa6
```

---

### Issue 3: Path Handling with Colons in URLs

**Symptom**: API returns `MS not found` for paths containing colons (e.g.,
timestamps like `2025-10-29T13:54:17`).

**Root Cause**: FastAPI path parameters need proper URL decoding for special
characters.

**Solution**: Code already handles this in `routes.py`:

- Uses `urllib.parse.unquote()` to decode path parameters
- Tries multiple path constructions as fallback
- Returns detailed error messages for debugging

**Test**:

```bash
# Colon must be URL-encoded as %3A
curl "http://localhost:8010/api/qa/calibration/scratch%2Fms%2Ftimesetv3%2Fcaltables%2F2025-10-29T13%3A54%3A17.cal.ms/bandpass-plots"
```

---

### Issue 4: Code Changes Not Reflected

**Symptom**: Code changes don't appear after restart.

**Root Cause**: Container needs to be recreated, not just restarted.

**Solution**:

```bash
# Force recreate to pick up code changes
cd /data/dsa110-contimg/ops/docker
docker-compose up -d --force-recreate api

# Or rebuild if Dockerfile changed
docker-compose up -d --build api
```

**Note**: The API code is mounted as a volume (`${REPO_ROOT}:/app`), so code
changes should be picked up automatically. However, Python bytecode caching may
require a restart.

---

### Issue 5: Port Already in Use

**Symptom**: `docker-compose up` fails with "port already in use".

**Root Cause**: Another process (or old container) is using port 8010.

**Solution**:

```bash
# Find what's using the port
sudo lsof -i :8010

# Stop the API container
docker stop contimg-api

# Or kill the process
sudo pkill -f "uvicorn.*8010"

# Then restart
docker-compose up -d api
```

---

## Restart Procedures

### Standard Restart (Code Changes)

```bash
cd /data/dsa110-contimg/ops/docker
docker-compose restart api
```

### Force Recreate (Config Changes)

```bash
cd /data/dsa110-contimg/ops/docker
docker-compose up -d --force-recreate api
```

### Full Rebuild (Dockerfile Changes)

```bash
cd /data/dsa110-contimg/ops/docker
docker-compose up -d --build api
```

### Manual Restart (If Docker Compose Fails)

```bash
# Stop
docker stop contimg-api
docker rm contimg-api

# Start (using docker-compose)
cd /data/dsa110-contimg/ops/docker
docker-compose up -d api
```

---

## Verification Steps

After restarting, verify the API is working:

1. **Check Container Status**:

   ```bash
   docker ps | grep contimg-api
   ```

2. **Check Logs**:

   ```bash
   docker logs contimg-api --tail 20
   ```

   Should see: `Uvicorn running on http://0.0.0.0:8010`

3. **Test Health Endpoint**:

   ```bash
   curl http://localhost:8010/api/health
   ```

4. **Test Bandpass Plots Endpoint**:
   ```bash
   curl "http://localhost:8010/api/qa/calibration/scratch%2Fms%2Ftimesetv3%2Fcaltables%2F2025-10-29T13%3A54%3A17.cal.ms/bandpass-plots"
   ```

---

## Environment Variables

Key environment variables (set in `/data/dsa110-contimg/ops/docker/.env`):

- `CONTIMG_API_PORT`: API port (default: 8010)
- `CONTIMG_SCRATCH_DIR`: Scratch directory path (default:
  `/tmp/contimg-scratch`)
- `CONTIMG_STATE_DIR`: State directory path
- `PIPELINE_PRODUCTS_DB`: Products database path
- `UVICORN_RELOAD`: Set to `1` for auto-reload (development only)

**Note**: Even though `CONTIMG_SCRATCH_DIR` may point to `/tmp/contimg-scratch`,
the actual MS files are in `/scratch` on the host. The docker-compose.yml mounts
`/scratch` separately.

---

## Systemd Service (Not Currently Used)

There is a systemd service file at `/etc/systemd/system/contimg-api.service`,
but it's **not active**. The API runs via Docker Compose instead.

If you need to use systemd instead of Docker:

1. **Stop Docker container**:

   ```bash
   docker stop contimg-api
   ```

2. **Update systemd service** to use `casa6` environment:

   ```ini
   ExecStart=/opt/miniforge/envs/casa6/bin/python3 -m uvicorn dsa110_contimg.api.routes:create_app --factory --host 0.0.0.0 --port 8010
   ```

3. **Start systemd service**:
   ```bash
   sudo systemctl start contimg-api
   ```

**However, Docker is the recommended deployment method.**

---

## Debugging Tips

### View Real-Time Logs

```bash
docker logs contimg-api -f
```

### Execute Commands in Container

```bash
# Check Python version
docker exec contimg-api python3 --version

# Check if path exists
docker exec contimg-api ls -ld /scratch/ms/timesetv3/caltables/

# Check environment variables
docker exec contimg-api env | grep CONTIMG
```

### Test API Endpoints

```bash
# List MS files
curl "http://localhost:8010/api/ms"

# Get bandpass plots (URL-encode colons as %3A)
curl "http://localhost:8010/api/qa/calibration/scratch%2Fms%2Ftimesetv3%2Fcaltables%2F2025-10-29T13%3A54%3A17.cal.ms/bandpass-plots"
```

### Check Container Configuration

```bash
# View mounted volumes
docker inspect contimg-api | grep -A 10 "Mounts"

# View environment variables
docker inspect contimg-api | grep -A 20 "Env"
```

---

## Key Learnings from Troubleshooting

1. **Always check Docker first**: The API runs in Docker, not directly on the
   host
2. **Use `casa6` environment**: Not `contimg` - this is critical
3. **Mount `/scratch`**: Required for accessing MS files
4. **URL-encode special characters**: Colons in paths must be `%3A`
5. **Force recreate for config changes**: `docker-compose restart` doesn't pick
   up volume mount changes
6. **Check logs immediately**: `docker logs contimg-api` shows startup errors

---

## Related Documentation

- API Routes: `/data/dsa110-contimg/src/dsa110_contimg/api/routes.py`
- Docker Compose: `/data/dsa110-contimg/ops/docker/docker-compose.yml`
- Calibration Documentation:
  `/data/dsa110-contimg/docs/how-to/CALIBRATION_DETAILED_PROCEDURE.md`

---

## Quick Command Reference

```bash
# Restart API
cd /data/dsa110-contimg/ops/docker && docker-compose restart api

# View logs
docker logs contimg-api --tail 50 -f

# Check status
docker ps | grep contimg-api

# Force recreate
cd /data/dsa110-contimg/ops/docker && docker-compose up -d --force-recreate api

# Test endpoint
curl "http://localhost:8010/api/qa/calibration/scratch%2Fms%2Ftimesetv3%2Fcaltables%2F2025-10-29T13%3A54%3A17.cal.ms/bandpass-plots"
```
