# Control Panel Quick Reference Card

> **⚠️ Migration Note:** This cheatsheet references the `legacy.backend` API.
> The new `backend` is under development. See `legacy.backend/` for reference.


## 🚀 Starting Services

```bash
# Kill port conflicts and start API
sudo fuser -k 8000/tcp
/data/dsa110-contimg/scripts/manage-services.sh start api

# Check status
/data/dsa110-contimg/scripts/manage-services.sh status

# View logs
/data/dsa110-contimg/scripts/manage-services.sh logs api
```

## 🌐 URLs

- **API**: http://localhost:8000
- **Dashboard**: http://localhost:5173 (dev) / http://localhost:3000 (Docker)
- **Control Panel**: http://localhost:5173/control

## 📡 API Endpoints

```bash
# List Measurement Sets
curl http://localhost:8000/api/ms

# List jobs
curl http://localhost:8000/api/jobs

# Get job details
curl http://localhost:8000/api/jobs/1

# Stream logs (SSE)
curl -N http://localhost:8000/api/jobs/id/1/logs

# Create calibration job
curl -X POST http://localhost:8000/api/jobs/calibrate \
  -H "Content-Type: application/json" \
  -d '{"ms_path": "/path/to/ms", "params": {"field": "0", "refant": "103"}}'
```

## 🔧 Service Management

```bash
# Start/Stop/Restart
./scripts/manage-services.sh start api
./scripts/manage-services.sh stop api
./scripts/manage-services.sh restart api

# Status
./scripts/manage-services.sh status

# Logs (follow)
./scripts/manage-services.sh logs api
./scripts/manage-services.sh logs dashboard
```

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill it
sudo fuser -k 8000/tcp

# Or use service script (it auto-kills)
./scripts/manage-services.sh start api
```

### API Won't Start

```bash
# Check logs
tail -50 /var/log/dsa110/api.log

# Test manually
cd /data/dsa110-contimg
conda activate casa6
export PYTHONPATH=/data/dsa110-contimg/src
uvicorn dsa110_contimg.api.routes:create_app --factory --host 0.0.0.0 --port 8000
```

### Logs Not Streaming

```bash
# Check SSE connection in browser DevTools → Network tab
# Look for /api/jobs/id/{job_id}/logs with type "eventsource"

# Test SSE endpoint
curl -N http://localhost:8000/api/jobs/id/1/logs
```

### Job Stuck in Pending

```bash
# Check backend logs
./scripts/manage-services.sh logs api

# Check if casa6 environment exists
conda env list | grep casa6

# Verify PYTHONPATH
echo $PYTHONPATH
```

## 📊 Database Queries

```bash
# List recent jobs
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
  "SELECT id, type, status, datetime(created_at, 'unixepoch')
   FROM jobs ORDER BY id DESC LIMIT 10;"

# View job logs
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
  "SELECT logs FROM jobs WHERE id=1;"

# Clear failed jobs
sqlite3 /data/dsa110-contimg/state/products.sqlite3 \
  "DELETE FROM jobs WHERE status='failed';"
```

## 📝 Job Parameters

### Calibrate

```json
{
  "ms_path": "/scratch/.../ms/file.ms",
  "params": {
    "field": "0",
    "refant": "103"
  }
}
```

### Apply

```json
{
  "ms_path": "/scratch/.../ms/file.ms",
  "params": {
    "gaintables": [
      "/scratch/.../file.kcal",
      "/scratch/.../file.bpcal",
      "/scratch/.../file.gpcal"
    ]
  }
}
```

### Image

```json
{
  "ms_path": "/scratch/.../ms/file.ms",
  "params": {
    "gridder": "wproject",
    "wprojplanes": -1,
    "datacolumn": "corrected",
    "quick": false,
    "skip_fits": true
  }
}
```

## 🔍 Health Checks

```bash
# Check API health
curl -f http://localhost:8000/api/status || echo "API down"

# Check dashboard health (dev mode)
curl -f http://localhost:5173 || echo "Dashboard down"

# Check ports
netstat -tlnp | grep -E ":(8000|5173)"

# Check processes
ps aux | grep -E "uvicorn|dsa110"
```

## 📂 Important Paths

```
/data/dsa110-contimg/
├── backend/src/dsa110_contimg/
│   ├── api/
│   │   ├── routes.py          # API endpoints
│   │   ├── models.py          # Pydantic models
│   │   └── job_runner.py      # Background jobs
│   └── database/
│       └── jobs.py            # Job database
├── frontend/src/
│   ├── pages/
│   │   └── ControlPage.tsx    # Control UI
│   └── api/
│       ├── queries.ts         # React Query hooks
│       └── types.ts           # TypeScript types
├── scripts/
│   └── manage-services.sh     # Service manager
├── systemd/
│   ├── dsa110-api.service     # Systemd unit
│   └── INSTALL.md             # Install guide
├── state/
│   └── products.sqlite3       # Job database
└── /var/log/dsa110/
    ├── api.log                # API logs
    └── dashboard.log          # Dashboard logs
```

## 🎯 Common Workflows

### Full Calibration Pipeline

```bash
# 1. Start API
sudo fuser -k 8000/tcp
./scripts/manage-services.sh start api

# 2. Open control panel
# Navigate to http://localhost:5173/control

# 3. Calibrate calibrator MS
# Select MS → Calibrate tab → Set field=0, refant=103 → Run

# 4. Apply to target MS
# Select target → Apply tab → Paste caltable paths → Run

# 5. Image calibrated MS
# Select same target → Image tab → Set gridder=wproject → Run
```

### Check Job Status

```bash
# Via API
curl http://localhost:8000/api/jobs | jq '.items[] | {id, type, status}'

# Via database
sqlite3 state/products.sqlite3 \
  "SELECT id, type, status FROM jobs ORDER BY id DESC LIMIT 5;"

# Via service script (check if running)
./scripts/manage-services.sh status
```

## 🔑 Key Technical Details

- **API Factory**: `uvicorn dsa110_contimg.api.routes:create_app --factory`
- **Python Env**: Jobs run in `casa6` (Python 3.11), base is Python 3.6
- **Log Batching**: Every 10 lines to database for performance
- **SSE Protocol**: Server-Sent Events for log streaming
- **Job States**: pending → running → done/failed
- **Ports**: 8000 (API), 3000 (Dashboard)

## 📚 Documentation

- `CONTROL_PANEL_README.md` - Full architecture docs
- `CONTROL_PANEL_QUICKSTART.md` - User guide with examples
- `PORT_MANAGEMENT.md` - Service management guide
- `IMPLEMENTATION_SUMMARY.md` - Technical implementation details
- `MEMORY.md` - Project memory and lessons learned

---

**Quick Help**: `./scripts/manage-services.sh` (no args shows usage)
