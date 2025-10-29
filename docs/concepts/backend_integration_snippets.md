# Backend Integration Code Snippets

Implementation examples for new front-end features integrated with the existing FastAPI backend.

---

## 1. Slack Alert Integration

### Environment Configuration

Add to `ops/systemd/contimg.env`:
```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/HERE
SLACK_ALERT_CHANNEL=#dsa110-alerts
ALERT_RATE_LIMIT_SECONDS=3600
ESE_THRESHOLD_SIGMA=5.0
```

### Alert Module (`src/dsa110_contimg/alerts/slack.py`)

```python
"""Slack notification system for ESE candidates and system alerts."""

import os
import time
import json
from typing import Dict, Optional
from datetime import datetime
import requests

# In-memory cache for rate limiting (production: use Redis)
_alert_cache: Dict[str, float] = {}

def send_ese_alert(
    source_id: str,
    nvss_id: str,
    significance_sigma: float,
    flux_change_pct: float,
    flux_old_mjy: float,
    flux_new_mjy: float,
    obs_time_utc: str,
    source_url: str,
) -> bool:
    """Send ESE candidate alert to Slack.
    
    Returns:
        True if alert sent successfully, False if rate-limited or error
    """
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        return False
    
    # Rate limiting: max 1 alert per source per hour
    rate_limit = int(os.getenv('ALERT_RATE_LIMIT_SECONDS', '3600'))
    now = time.time()
    last_alert = _alert_cache.get(source_id, 0)
    
    if now - last_alert < rate_limit:
        return False  # Rate limited
    
    # Determine color based on significance
    if significance_sigma >= 8.0:
        color = "danger"
        emoji = "🔴"
    elif significance_sigma >= 5.0:
        color = "warning"
        emoji = "🟠"
    else:
        color = "good"
        emoji = "🟡"
    
    # Format flux change
    flux_direction = "↗" if flux_change_pct > 0 else "↘"
    flux_str = f"{flux_direction} {abs(flux_change_pct):.1f}% ({flux_old_mjy:.1f}→{flux_new_mjy:.1f} mJy)"
    
    payload = {
        "text": f"{emoji} *ESE Candidate Detected!*",
        "attachments": [{
            "color": color,
            "fields": [
                {
                    "title": "Source",
                    "value": nvss_id,
                    "short": True
                },
                {
                    "title": "Significance",
                    "value": f"{significance_sigma:.1f}σ",
                    "short": True
                },
                {
                    "title": "Flux Change",
                    "value": flux_str,
                    "short": True
                },
                {
                    "title": "Observation Time",
                    "value": obs_time_utc,
                    "short": True
                }
            ],
            "actions": [{
                "type": "button",
                "text": "View Source Details",
                "url": source_url
            }],
            "footer": "DSA-110 Continuum Pipeline",
            "ts": int(now)
        }]
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        if response.status_code == 200:
            _alert_cache[source_id] = now
            return True
        else:
            print(f"Slack webhook failed: {response.status_code} {response.text}")
            return False
            
    except Exception as e:
        print(f"Slack alert error: {e}")
        return False


def send_system_alert(
    title: str,
    message: str,
    severity: str = "warning",  # "good", "warning", "danger"
) -> bool:
    """Send system-level alert (calibrator loss, disk space, etc.)."""
    webhook_url = os.getenv('SLACK_WEBHOOK_URL')
    if not webhook_url:
        return False
    
    emoji_map = {
        "good": "✓",
        "warning": "⚠",
        "danger": "✗"
    }
    
    payload = {
        "text": f"{emoji_map.get(severity, '•')} *{title}*",
        "attachments": [{
            "color": severity,
            "text": message,
            "footer": "DSA-110 Continuum Pipeline",
            "ts": int(time.time())
        }]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False
```

### Integration in Photometry Pipeline

Add to `src/dsa110_contimg/photometry/cli.py`:

```python
from dsa110_contimg.alerts.slack import send_ese_alert

# After photometry measurement and variability calculation
if chi_squared_nu > float(os.getenv('ESE_THRESHOLD_SIGMA', '5.0')):
    source_url = f"https://dsa110-pipeline.caltech.edu/sources/{source_id}"
    send_ese_alert(
        source_id=source_id,
        nvss_id=nvss_id,
        significance_sigma=chi_squared_nu,
        flux_change_pct=flux_change_percent,
        flux_old_mjy=nvss_flux_mjy,
        flux_new_mjy=measured_flux_mjy,
        obs_time_utc=obs_time.strftime('%Y-%m-%d %H:%M UTC'),
        source_url=source_url
    )
```

---

## 2. Mosaic Query API

### API Route (`src/dsa110_contimg/api/routes.py`)

Add to existing router:

```python
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
import asyncio

class MosaicQueryRequest(BaseModel):
    start_mjd: float
    end_mjd: float
    dec_min: Optional[float] = None
    dec_max: Optional[float] = None

class MosaicQueryResponse(BaseModel):
    images: List[str]
    coverage: Dict[str, List[float]]
    total_images: int
    time_span_hours: float
    job_id: Optional[str] = None
    mosaic_url: Optional[str] = None

@router.post("/mosaic/query", response_model=MosaicQueryResponse)
def mosaic_query(request: MosaicQueryRequest) -> MosaicQueryResponse:
    """Query images for mosaic generation by time range and declination."""
    
    # Query products database for images in range
    with _connect(cfg.products_db) as conn:
        query = """
            SELECT i.path, m.mid_mjd, m.start_mjd, m.end_mjd
              FROM images i
              JOIN ms_index m ON i.ms_path = m.path
             WHERE m.mid_mjd >= ? AND m.mid_mjd <= ?
               AND i.type = 'image.pbcor'
        """
        params = [request.start_mjd, request.end_mjd]
        
        if request.dec_min is not None and request.dec_max is not None:
            # Note: requires dec_deg column in ms_index (future enhancement)
            query += " AND m.dec_deg >= ? AND m.dec_deg <= ?"
            params.extend([request.dec_min, request.dec_max])
        
        query += " ORDER BY m.mid_mjd"
        
        rows = conn.execute(query, params).fetchall()
        image_paths = [r[0] for r in rows]
    
    # Calculate coverage (RA/Dec bounds)
    # This is simplified - real implementation would parse FITS headers
    coverage = {
        "ra_range": [0, 360],  # Placeholder
        "dec_range": [request.dec_min or -90, request.dec_max or 90]
    }
    
    time_span = (request.end_mjd - request.start_mjd) * 24  # hours
    
    return MosaicQueryResponse(
        images=image_paths,
        coverage=coverage,
        total_images=len(image_paths),
        time_span_hours=time_span,
        job_id=None,  # Async generation not yet implemented
        mosaic_url=None
    )


@router.post("/mosaic/generate")
async def mosaic_generate(request: MosaicQueryRequest):
    """Generate mosaic from queried images (async job)."""
    # Placeholder for async mosaic generation
    # Production: Use Celery or similar for background processing
    
    job_id = f"mosaic_{int(time.time())}"
    
    # Kick off background task (simplified example)
    # In production: submit to job queue
    asyncio.create_task(_generate_mosaic_async(job_id, request))
    
    return {
        "job_id": job_id,
        "status": "queued",
        "status_url": f"/api/mosaic/status/{job_id}"
    }


async def _generate_mosaic_async(job_id: str, request: MosaicQueryRequest):
    """Background task to generate mosaic."""
    # Call existing mosaic CLI tools
    # Save output to /scratch/mosaics/{job_id}.fits
    # Update job status in database
    pass


@router.get("/mosaic/status/{job_id}")
def mosaic_status(job_id: str):
    """Check status of mosaic generation job."""
    # Query job database (to be implemented)
    return {
        "job_id": job_id,
        "status": "processing",  # or "completed", "failed"
        "progress": 0.45,
        "download_url": None  # Set when completed
    }
```

---

## 3. ESE Candidate API Enhancements

### New Endpoint for Active Alerts

Add to `src/dsa110_contimg/api/routes.py`:

```python
from datetime import datetime, timedelta

class ESECandidate(BaseModel):
    source_id: str
    nvss_id: str
    ra_deg: float
    dec_deg: float
    significance_sigma: float
    flux_change_pct: float
    nvss_flux_mjy: float
    latest_flux_mjy: float
    last_obs_utc: datetime
    slack_sent: bool
    user_dismissed: bool

class ESECandidateList(BaseModel):
    items: List[ESECandidate]
    total: int
    threshold_sigma: float

@router.get("/alerts/ese_candidates", response_model=ESECandidateList)
def get_ese_candidates(
    min_sigma: float = 5.0,
    hours_ago: int = 24,
    include_dismissed: bool = False
) -> ESECandidateList:
    """Get list of ESE candidates above threshold."""
    
    threshold = float(os.getenv('ESE_THRESHOLD_SIGMA', str(min_sigma)))
    cutoff_time = datetime.utcnow() - timedelta(hours=hours_ago)
    
    with _connect(cfg.products_db) as conn:
        query = """
            SELECT 
                p.source_id,
                p.nvss_id,
                p.ra_deg,
                p.dec_deg,
                p.chi_squared_nu as significance,
                p.flux_change_pct,
                p.nvss_flux_mjy,
                p.latest_flux_mjy,
                p.last_obs_time,
                p.slack_sent,
                COALESCE(p.user_dismissed, 0) as dismissed
            FROM (
                SELECT 
                    image_path,
                    ra_deg,
                    dec_deg,
                    nvss_flux_mjy,
                    peak_jyb * 1000 as latest_flux_mjy,
                    measured_at as last_obs_time,
                    -- Calculate variability stats (simplified)
                    ABS((peak_jyb * 1000 - nvss_flux_mjy) / nvss_flux_mjy) * 100 as flux_change_pct,
                    -- Placeholder chi_squared_nu calculation
                    5.5 as chi_squared_nu,
                    0 as slack_sent,
                    0 as user_dismissed
                FROM photometry
                WHERE measured_at >= ?
            ) p
            WHERE p.chi_squared_nu >= ?
        """
        
        if not include_dismissed:
            query += " AND p.user_dismissed = 0"
        
        query += " ORDER BY p.chi_squared_nu DESC"
        
        rows = conn.execute(
            query, 
            (cutoff_time.timestamp(), threshold)
        ).fetchall()
        
        candidates = [
            ESECandidate(
                source_id=f"src_{i}",
                nvss_id=f"NVSS J{int(r['ra_deg']):06d}{'+-'[r['dec_deg']<0]}{abs(int(r['dec_deg'])):02d}",
                ra_deg=r['ra_deg'],
                dec_deg=r['dec_deg'],
                significance_sigma=r['significance'],
                flux_change_pct=r['flux_change_pct'],
                nvss_flux_mjy=r['nvss_flux_mjy'],
                latest_flux_mjy=r['latest_flux_mjy'],
                last_obs_utc=datetime.fromtimestamp(r['last_obs_time']),
                slack_sent=bool(r['slack_sent']),
                user_dismissed=bool(r['dismissed'])
            )
            for i, r in enumerate(rows)
        ]
    
    return ESECandidateList(
        items=candidates,
        total=len(candidates),
        threshold_sigma=threshold
    )


@router.post("/alerts/dismiss/{source_id}")
def dismiss_alert(source_id: str):
    """Dismiss an ESE candidate alert."""
    # Update database to mark as dismissed
    # Production: add user_id tracking
    return {"ok": True, "source_id": source_id}
```

---

## 4. VO Cone Search Endpoint (Phase 3)

### Simple Cone Search Implementation

```python
from astropy.io.votable import from_table
from astropy.table import Table
from astropy.coordinates import SkyCoord
import astropy.units as u

@router.get("/vo/conesearch")
def vo_conesearch(
    RA: float,
    DEC: float,
    SR: float,  # Search radius in degrees
    VERB: int = 2  # Verbosity level
):
    """Simple Cone Search protocol endpoint.
    
    Complies with IVOA Simple Cone Search v1.03.
    Returns sources within search radius as VOTable.
    """
    
    center = SkyCoord(ra=RA*u.deg, dec=DEC*u.deg, frame='icrs')
    
    # Query photometry database
    with _connect(cfg.products_db) as conn:
        rows = conn.execute("""
            SELECT 
                ra_deg, dec_deg, nvss_flux_mjy,
                peak_jyb * 1000 as latest_flux_mjy,
                measured_at
            FROM photometry
            ORDER BY measured_at DESC
            LIMIT 10000
        """).fetchall()
    
    # Filter by cone search
    sources = []
    for r in rows:
        src_coord = SkyCoord(ra=r['ra_deg']*u.deg, dec=r['dec_deg']*u.deg)
        sep = center.separation(src_coord).deg
        
        if sep <= SR:
            sources.append({
                'RA': r['ra_deg'],
                'DEC': r['dec_deg'],
                'NVSS_FLUX_MJY': r['nvss_flux_mjy'],
                'LATEST_FLUX_MJY': r['latest_flux_mjy'],
                'SEPARATION_DEG': sep
            })
    
    # Create Astropy table
    table = Table(sources)
    
    # Convert to VOTable
    votable = from_table(table)
    
    # Return as XML
    from io import BytesIO
    buf = BytesIO()
    votable.to_xml(buf)
    
    return Response(
        content=buf.getvalue(),
        media_type='application/x-votable+xml'
    )
```

---

## 5. Database Schema Updates

### Add columns to support new features

```sql
-- Add to products.sqlite3 (ms_index table)
ALTER TABLE ms_index ADD COLUMN dec_deg REAL;  -- For mosaic Dec filtering

-- Add ESE tracking table
CREATE TABLE IF NOT EXISTS ese_candidates (
    id INTEGER PRIMARY KEY,
    source_id TEXT NOT NULL,
    nvss_id TEXT NOT NULL,
    ra_deg REAL NOT NULL,
    dec_deg REAL NOT NULL,
    chi_squared_nu REAL NOT NULL,
    flux_change_pct REAL,
    detected_at REAL NOT NULL,
    slack_sent INTEGER DEFAULT 0,
    user_dismissed INTEGER DEFAULT 0,
    dismissed_at REAL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_ese_detected ON ese_candidates(detected_at);
CREATE INDEX IF NOT EXISTS idx_ese_dismissed ON ese_candidates(user_dismissed);

-- Add mosaic jobs table
CREATE TABLE IF NOT EXISTS mosaic_jobs (
    job_id TEXT PRIMARY KEY,
    start_mjd REAL NOT NULL,
    end_mjd REAL NOT NULL,
    dec_min REAL,
    dec_max REAL,
    status TEXT NOT NULL,  -- queued, processing, completed, failed
    progress REAL DEFAULT 0.0,
    created_at REAL NOT NULL,
    completed_at REAL,
    output_path TEXT,
    error_message TEXT
);
```

---

## 6. Frontend Environment Configuration

Create `.env` file in React project root:

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws

# Feature Flags
VITE_ESE_THRESHOLD_SIGMA=5.0
VITE_REFRESH_INTERVAL_MS=10000
VITE_ENABLE_SLACK_ALERTS=true
VITE_ENABLE_VO_CONESEARCH=false  # Enable in Phase 3

# UI Configuration
VITE_SOURCES_PER_PAGE=50
VITE_IMAGES_PER_PAGE=24
VITE_DEFAULT_SURVEY=NVSS

# External Links
VITE_SIMBAD_URL=http://simbad.u-strasbg.fr/simbad/sim-coo
VITE_NED_URL=https://ned.ipac.caltech.edu/conesearch
```

---

## Testing

### Example Slack Alert Test

```bash
# Test Slack webhook
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Test ESE Alert",
    "attachments": [{
      "color": "danger",
      "fields": [
        {"title": "Source", "value": "NVSS J123456+420312", "short": true},
        {"title": "Significance", "value": "6.2σ", "short": true}
      ]
    }]
  }'
```

### Example Mosaic Query Test

```bash
# Query images for 1-hour window
curl "http://localhost:8000/api/mosaic/query?start_mjd=60238.0&end_mjd=60238.042&dec_min=40&dec_max=45"
```

### Example ESE Candidates Test

```bash
# Get active ESE candidates
curl "http://localhost:8000/api/alerts/ese_candidates?min_sigma=5.0&hours_ago=24"
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-24  
**Status**: Implementation Reference

