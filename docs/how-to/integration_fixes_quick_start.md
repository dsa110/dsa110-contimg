# Dashboard Integration Fixes - Quick Start Guide

**Date:** 2025-11-19  
**Focus:** Get CARTA, Absurd, and data pipeline working

---

## TL;DR - What's Actually Broken

The dashboard UI is **working perfectly**. What's broken:

1. ❌ **CARTA not running** → CARTA tab shows errors
2. ❌ **Absurd not enabled** → Queue monitoring shows "Connection Failed"
3. ❌ **Pipeline not registering metadata** → Tables show "N/A"
4. ⚠️ **Pointing data sparse** → Sky map shows dots instead of paths

---

## Fix 1: Start CARTA Service (10 minutes)

CARTA is a FITS viewer. The UI is ready, but the service isn't running.

### Option A: Docker (Easiest)

```bash
# Pull and start CARTA
docker pull cartavis/carta:latest
docker run -d \
  --name carta \
  -p 9002:3002 \
  -p 9003:80 \
  -v /stage/dsa110-contimg/images:/images:ro \
  -v /data/dsa110-contimg/images:/data:ro \
  cartavis/carta:latest

# Verify
curl http://localhost:9003  # Should return HTML
docker logs carta  # Check for errors
```

### Option B: Via Backend API

```bash
# If the backend API route is enabled:
curl -X POST http://localhost:8000/api/visualization/carta/start
```

### Verify in Dashboard

1. Navigate to `http://localhost:3210/data`
2. Click "CARTA" tab
3. Should see CARTA interface, not error

---

## Fix 2: Enable Absurd Workflow Manager (5 minutes)

Absurd orchestrates workflows. The UI is ready, but it's disabled.

```bash
# Check current status
curl http://localhost:8000/api/absurd/health
# Returns 503? It's disabled

# Enable it
cd /data/dsa110-contimg
echo "ABSURD_ENABLED=true" >> .env
echo "ABSURD_API_URL=http://localhost:8001" >> .env

# Start Absurd service
nohup python -m dsa110_contimg.absurd.server \
  --port 8001 \
  --host 0.0.0.0 \
  > logs/absurd.log 2>&1 &

# Save PID
echo $! > /tmp/absurd.pid

# Verify
curl http://localhost:8000/api/absurd/health
# Should return {"status": "ok"} or similar
```

### Verify in Dashboard

1. Navigate to `http://localhost:3210/`
2. "Queue Depth Monitoring" should show data, not "Connection Failed"
3. "Pipeline Control" → "Absurd Workflow" tab should work

---

## Fix 3: Integrate Pipeline Metadata Registration (30 minutes)

When imaging creates FITS files, they need to be registered in the database.

### Step 1: Find the Imaging Pipeline Code

```bash
# Find where tclean is called
grep -r "tclean\|imaging_pipeline" /data/dsa110-contimg/src --include="*.py" | grep -v test | head -5
```

### Step 2: Add Metadata Registration

Create `/data/dsa110-contimg/src/dsa110_contimg/database/register_products.py`:

```python
"""
Product registration with metadata extraction.
"""
import sqlite3
from pathlib import Path
from astropy.io import fits
import logging

logger = logging.getLogger(__name__)

def register_image_with_metadata(filepath: str, db_path: str = None):
    """
    Register an image in the database with full metadata extraction.

    Args:
        filepath: Path to FITS image
        db_path: Path to products database (default: state/products.sqlite3)
    """
    if db_path is None:
        db_path = "/data/dsa110-contimg/state/products.sqlite3"

    filepath = Path(filepath)
    if not filepath.exists():
        logger.error(f"Image not found: {filepath}")
        return None

    try:
        # Extract metadata from FITS header
        with fits.open(filepath) as hdul:
            header = hdul[0].header

            metadata = {
                "filepath": str(filepath),
                "name": filepath.name,
                "ra_deg": header.get("CRVAL1"),
                "dec_deg": header.get("CRVAL2"),
                "noise_mjy": header.get("RMS") or header.get("NOISE"),
                "freq_mhz": header.get("CRVAL3", 0) / 1e6 if "CRVAL3" in header else None,
                "beam_maj": header.get("BMAJ"),
                "beam_min": header.get("BMIN"),
                "beam_pa": header.get("BPA"),
                "type": determine_image_type(filepath.name),
            }

        # Insert into database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO images
            (filepath, name, type, ra_deg, dec_deg, noise_mjy, freq_mhz,
             beam_maj, beam_min, beam_pa, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            metadata["filepath"],
            metadata["name"],
            metadata["type"],
            metadata["ra_deg"],
            metadata["dec_deg"],
            metadata["noise_mjy"],
            metadata["freq_mhz"],
            metadata["beam_maj"],
            metadata["beam_min"],
            metadata["beam_pa"],
        ))

        image_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Registered image {image_id}: {metadata['name']}")
        return image_id

    except Exception as e:
        logger.error(f"Error registering image {filepath}: {e}")
        return None

def determine_image_type(filename: str) -> str:
    """Determine image type from filename."""
    filename_lower = filename.lower()

    if 'pbcor' in filename_lower:
        return 'pbcor'
    elif 'pb.fits' in filename_lower or '.pb.' in filename_lower:
        return 'pb'
    elif 'residual' in filename_lower:
        return 'residual'
    elif 'model' in filename_lower:
        return 'model'
    elif 'psf' in filename_lower:
        return 'psf'
    elif 'image' in filename_lower:
        return 'image'
    else:
        return 'unknown'

def register_ms_with_metadata(filepath: str, db_path: str = None):
    """
    Register a measurement set in the database.

    Args:
        filepath: Path to MS directory
        db_path: Path to products database
    """
    if db_path is None:
        db_path = "/data/dsa110-contimg/state/products.sqlite3"

    filepath = Path(filepath)
    if not filepath.exists():
        logger.error(f"MS not found: {filepath}")
        return None

    try:
        # Extract scan_id from filename (format: YYYYMMDD_HHMMSS.ms)
        name = filepath.name
        scan_id = None

        if '_' in name:
            parts = name.replace('.ms', '').split('_')
            if len(parts) >= 2:
                scan_id = f"{parts[0]}_{parts[1]}"

        # Insert into database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO ms_index
            (filepath, name, scan_id, created_at)
            VALUES (?, ?, ?, datetime('now'))
        """, (str(filepath), name, scan_id))

        ms_id = cursor.lastrowid
        conn.commit()
        conn.close()

        logger.info(f"Registered MS {ms_id}: {name}")
        return ms_id

    except Exception as e:
        logger.error(f"Error registering MS {filepath}: {e}")
        return None
```

### Step 3: Call from Imaging Pipeline

Find your imaging code and add:

```python
# After tclean completes and creates FITS files:
from dsa110_contimg.database.register_products import register_image_with_metadata

# Register all output FITS files
for fits_file in output_dir.glob("*.fits"):
    image_id = register_image_with_metadata(str(fits_file))
    if image_id:
        logger.info(f"Registered image {fits_file.name} with ID {image_id}")
```

### Verify

```bash
# Run your imaging pipeline
# Then check database:
sqlite3 /data/dsa110-contimg/state/products.sqlite3 << EOF
SELECT name, ra_deg, dec_deg, noise_mjy FROM images ORDER BY id DESC LIMIT 5;
EOF

# Should show:
# - Filename in 'name' column
# - Coordinates in ra_deg/dec_deg
# - Noise values
# No more "N/A" in dashboard!
```

---

## Fix 4: Check Pointing Data Ingestion (10 minutes)

The sky map works, but needs more data points.

```bash
# Check current pointing data
sqlite3 /data/dsa110-contimg/state/products.sqlite3 << EOF
SELECT COUNT(*) as total,
       MIN(mjd) as earliest,
       MAX(mjd) as latest,
       MAX(mjd) - MIN(mjd) as span_days
FROM pointing_history;
EOF

# Check if pointing ingestion service is running
ps aux | grep pointing | grep -v grep

# If not running, start it:
# (Find the pointing ingestion script)
find /data/dsa110-contimg -name "*pointing*ingest*.py" -o -name "*pointing*daemon*.py"
```

---

## Verification Checklist

After fixes, verify:

```bash
# 1. CARTA
echo "=== CARTA Status ==="
curl -s http://localhost:9003 | head -5 | grep -i carta && echo "✓ CARTA responding" || echo "✗ CARTA not responding"
docker ps | grep carta && echo "✓ CARTA container running" || echo "✗ CARTA not running"

# 2. Absurd
echo "=== Absurd Status ==="
curl -s http://localhost:8000/api/absurd/health && echo "✓ Absurd responding" || echo "✗ Absurd not responding"

# 3. Database Metadata
echo "=== Database Metadata ==="
IMAGES=$(sqlite3 /data/dsa110-contimg/state/products.sqlite3 "SELECT COUNT(*), COUNT(name), COUNT(ra_deg) FROM images;")
echo "Images: $IMAGES"
[[ "$IMAGES" == *"23|23|"* ]] && echo "✓ Metadata populated" || echo "⚠ Some metadata missing"

# 4. Dashboard
echo "=== Dashboard Access ==="
curl -s http://localhost:3210 | grep -q "DSA-110" && echo "✓ Dashboard accessible" || echo "✗ Dashboard not accessible"
```

### Visual Verification

1. **Dashboard Main Page** (`http://localhost:3210/`)
   - ✓ System Health no longer "DEGRADED" (or only warnings, not critical)
   - ✓ Queue Depth shows data (not "Connection Failed")

2. **Data Browser** (`http://localhost:3210/data`)
   - ✓ Images tab: Name, RA, Dec columns populated (not "N/A")
   - ✓ MS tab: Name, Scan ID populated
   - ✓ CARTA tab: Shows CARTA interface (not connection error)

3. **Sky View** (`http://localhost:3210/sky`)
   - ✓ Sky Coverage Map shows many points with path traces
   - ✓ Image browser shows available images

---

## Quick Troubleshooting

### CARTA won't start

```bash
# Check Docker
docker ps -a | grep carta
docker logs carta

# Check ports
netstat -tulpn | grep -E "9002|9003"

# Try alternative Docker command
docker run -d \
  --name carta \
  --network host \
  -v /stage/dsa110-contimg:/data:ro \
  cartavis/carta:latest
```

### Absurd returns 503

```bash
# Check if actually disabled in code
grep -r "ABSURD_ENABLED" /data/dsa110-contimg/src

# Check process
ps aux | grep absurd | grep -v grep

# Check logs
tail -f /data/dsa110-contimg/logs/absurd.log

# Restart
kill $(cat /tmp/absurd.pid)
python -m dsa110_contimg.absurd.server --port 8001 &
```

### Database still shows N/A

```bash
# Check if columns exist
sqlite3 /data/dsa110-contimg/state/products.sqlite3 ".schema images"

# Run backfill for existing images
python /data/dsa110-contimg/scripts/backfill_metadata.py

# Check a specific image
sqlite3 /data/dsa110-contimg/state/products.sqlite3 << EOF
SELECT * FROM images WHERE id = 1;
EOF
```

---

## Summary: What We're Fixing

| Component    | Issue          | Fix                               | Time   |
| ------------ | -------------- | --------------------------------- | ------ |
| **CARTA**    | Not running    | Start Docker container            | 10 min |
| **Absurd**   | Disabled       | Enable config + start service     | 5 min  |
| **Metadata** | Not registered | Add register function to pipeline | 30 min |
| **Pointing** | Sparse data    | Check/restart ingestion           | 10 min |

**Total Time:** ~1 hour to get everything working

---

## Related Documentation

- **Architecture Analysis:** `UI_ARCHITECTURE_ISSUES.md`
- **Backend Issues:** `BACKEND_FIXES_README.md`

---

**Key Point:** The dashboard frontend is fully functional. We're just connecting
it to the services and data it expects.
