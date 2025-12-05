# DSA-110 Continuum Imaging Pipeline: Quick Start

Get the pipeline running in 5 minutes.

**Last Updated:** December 5, 2025

---

## Prerequisites

| Requirement           | Details                                                          |
| --------------------- | ---------------------------------------------------------------- |
| **Conda Environment** | `casa6` with Python 3.11, CASA 6.7, pyuvdata 3.2.4               |
| **Storage Access**    | `/data/incoming` (raw HDF5), `/stage/dsa110-contimg` (output MS) |
| **Network**           | Ports 8000 (API), 3210 (Dashboard) available                     |
| **PostgreSQL**        | ABSURD task queue database                                       |

---

## Quick Start: 3 Steps

### Step 1: Activate Environment (10 seconds)

```bash
conda activate casa6
cd /data/dsa110-contimg
```

### Step 2: Start Services (30 seconds)

**Option A: systemd (Production)**

```bash
# Start API and ABSURD worker
sudo systemctl start contimg-api contimg-absurd-worker

# Verify running
sudo systemctl status contimg-api contimg-absurd-worker
```

**Option B: Manual (Development)**

```bash
# Terminal 1 - Backend API
cd /data/dsa110-contimg/backend/src
uvicorn dsa110_contimg.api.app:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - ABSURD Worker
python -m dsa110_contimg.absurd.worker

# Terminal 3 - Frontend (optional)
cd /data/dsa110-contimg/frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

### Step 3: Access Dashboard (10 seconds)

Open browser to: **http://localhost:3210/ui/**

Or check API health:

```bash
curl http://localhost:8000/api/status
```

---

## Enable Automatic Ingestion

The ABSURD scheduler automatically polls for new files:

```python
# Run once to register the ingestion schedule
from dsa110_contimg.absurd import AbsurdClient, setup_ingestion_schedule
from dsa110_contimg.absurd.config import AbsurdConfig
import asyncio

async def setup():
    config = AbsurdConfig.from_env()
    async with AbsurdClient(config.database_url) as client:
        await setup_ingestion_schedule(client)

asyncio.run(setup())
```

---

## Your First Conversion

### Convert a Time Window

```bash
conda activate casa6

# Convert all observations in a 1-hour window
python -m dsa110_contimg.conversion.cli groups \
    /data/incoming \
    /stage/dsa110-contimg/ms \
    "2025-12-01T00:00:00" \
    "2025-12-01T01:00:00"
```

### Convert by Calibrator Transit

```bash
# Find and convert observations around a calibrator transit
python -m dsa110_contimg.conversion.cli groups \
    --calibrator "3C286" \
    /data/incoming \
    /stage/dsa110-contimg/ms
```

### Preview Without Converting (Dry Run)

```bash
python -m dsa110_contimg.conversion.cli groups --dry-run \
    /data/incoming /stage/dsa110-contimg/ms \
    "2025-12-01T00:00:00" "2025-12-01T01:00:00"
```

---

## Essential Commands

### Service Management

```bash
# Check service status
sudo systemctl status contimg-api contimg-absurd-worker

# View worker logs
journalctl -u contimg-absurd-worker -f --no-pager

# Restart services
sudo systemctl restart contimg-api contimg-absurd-worker
```

### API Endpoints

```bash
# Pipeline status
curl http://localhost:8000/api/status

# ABSURD queue status
curl http://localhost:8000/api/absurd/status

# List recent observations
curl http://localhost:8000/api/data/observations
```

### CLI Commands

```bash
# Conversion (UVH5 → MS)
python -m dsa110_contimg.conversion.cli --help

# Calibration
python -m dsa110_contimg.calibration.cli --help

# Imaging (MS → FITS)
python -m dsa110_contimg.imaging.cli --help

# Mosaicking
python -m dsa110_contimg.mosaic --help

# Photometry
python -m dsa110_contimg.photometry.cli --help
```

---

## Port Reference

| Port | Service                | URL                            |
| ---- | ---------------------- | ------------------------------ |
| 8000 | FastAPI Backend        | http://localhost:8000/api/docs |
| 3210 | Dashboard (Production) | http://localhost:3210/ui/      |
| 5173 | Vite Dev Server        | http://localhost:5173          |
| 3030 | Grafana Monitoring     | http://localhost:3030          |

---

## Troubleshooting

### Services Won't Start

```bash
# Check for port conflicts
sudo lsof -i :8000
sudo lsof -i :3210

# Check logs for errors
journalctl -u contimg-api -n 50 --no-pager
```

### Database Locked

```bash
# Check for long-running processes
fuser /data/dsa110-contimg/state/db/pipeline.sqlite3
```

### Import Errors

```bash
# Verify conda environment
conda activate casa6
python -c "import dsa110_contimg; print('OK')"
```

### No Data Converting

```bash
# Check if HDF5 files exist in the time range
ls -la /data/incoming/*.hdf5 | head -20

# Check streaming queue
sqlite3 /data/dsa110-contimg/state/db/pipeline.sqlite3 \
  "SELECT state, COUNT(*) FROM ingest_queue GROUP BY state;"
```

---

## Next Steps

| Goal                 | Documentation                                              |
| -------------------- | ---------------------------------------------------------- |
| Pipeline workflows   | [Storage & Files](guides/storage-and-file-organization.md) |
| Develop new features | [Developer Guide](DEVELOPER_GUIDE.md)                      |
| API integration      | [API Reference](API_REFERENCE.md)                          |
| System architecture  | [Architecture](ARCHITECTURE.md)                            |
| Fix issues           | [Troubleshooting](TROUBLESHOOTING.md)                      |

---

## Key Concepts

### File Structure

```
/data/incoming/           # Raw HDF5 subband files from correlator
  └── 2025-12-01T12:30:00_sb00.hdf5
  └── 2025-12-01T12:30:00_sb01.hdf5
  └── ... (16 subbands per observation)

/stage/dsa110-contimg/    # Processed output (NVMe SSD - fast)
  └── ms/                 # Measurement Sets
  └── images/             # FITS images
  └── mosaics/            # Combined mosaics

/data/dsa110-contimg/     # Code and databases (HDD - slower)
  └── backend/src/        # Python package
  └── frontend/           # React dashboard
  └── state/db/           # SQLite databases
```

### Processing Pipeline

```
UVH5 files → Group by timestamp → Combine 16 subbands →
→ Write MS → Calibrate → Image → Mosaic
```

### Subband Grouping

Each observation produces **16 subband files** (`_sb00.hdf5` through `_sb15.hdf5`).

- **Streaming mode**: Files are **normalized on ingest** (renamed to canonical timestamp)
- **Batch mode**: Files are **clustered by timestamp** (60-second tolerance)

Both ensure all 16 subbands are combined into a single Measurement Set.

---

## Getting Help

- **Local Docs Search**: `python -m dsa110_contimg.docsearch.cli search "your query"`
- **API Docs**: http://localhost:8000/api/docs
- **GitHub Issues**: https://github.com/dsa110/dsa110-contimg/issues
