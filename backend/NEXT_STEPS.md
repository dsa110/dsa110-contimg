# Next Steps - DSA-110 Continuum Imaging Pipeline

## Status: Core Setup Complete ✅ (Updated 2025-11-29)

The API backend is fully operational with real data. Database tables are
populated and all endpoints are returning real data.

### Current State

| Component   | Status         | Details                      |
| ----------- | -------------- | ---------------------------- |
| API Server  | ✅ Running     | Port 8000, systemd enabled   |
| MS Records  | ✅ 12 records  | Real measurement sets        |
| Images      | ✅ 4 records   | FITS files registered        |
| Photometry  | ✅ 21 records  | 5 unique sources             |
| Cal Tables  | ✅ 3 records   | Linked to source MS          |
| Batch Jobs  | ✅ 7 jobs      | Provenance tracking          |
| Lightcurve  | ✅ Implemented | Returns real flux data       |
| Nginx       | ✅ Configured  | Reverse proxy on port 80     |
| Prometheus  | ✅ Enabled     | Metrics at /metrics          |
| Stats API   | ✅ Implemented | Summary counts at /api/stats |
| IP Security | ✅ Active      | Localhost + private networks |

---

## Completed Tasks ✅

### 1. API Server & Endpoints ✅

- All 14 test endpoints pass
- Health check, images, sources, MS, calibration, jobs, QA endpoints working
- Lightcurve endpoint returns real photometry data

### 2. Image Database ✅

- Registered 4 FITS images from `/stage/dsa110-contimg/`
- Images linked to MS records with proper metadata

### 3. Calibration Table Linking ✅

- All 3 cal tables have `source_ms_path` set
- Cal table detail endpoint returns source MS info

### 4. Source Photometry ✅

- 21 photometry records for 5 unique sources
- Lightcurve endpoint returns flux measurements

### 5. Pipeline Job Records ✅

- 7 batch jobs with 23 job items
- Imaging, calibration, and conversion jobs tracked

### 6. Systemd Service ✅

- Service file at `/etc/systemd/system/dsa110-api.service`
- Enabled for auto-start on boot

### 7. IP-Based Access Control ✅

- Restricts API access to localhost and private networks (10.x, 172.16.x,
  192.168.x)
- Health endpoint always accessible for monitoring
- Custom IPs via `DSA110_ALLOWED_IPS` environment variable

### 8. Nginx Reverse Proxy ✅

- Config at `/etc/nginx/sites-available/dsa110-contimg`
- Serves frontend from `/data/dsa110-contimg/frontend/dist`
- Proxies `/api/` to FastAPI on port 8000
- Metrics endpoint restricted to localhost only
- Security headers (X-Frame-Options, X-Content-Type-Options)
- Gzip compression enabled

### 9. Prometheus Monitoring ✅

- Metrics endpoint at `/metrics`
- Collects request latency, count, and status codes
- Python GC and process metrics included
- Access via `curl http://localhost:8000/metrics`

### 10. Stats Endpoint ✅

- Summary statistics at `/api/stats`
- Returns counts for MS, images, photometry, sources, jobs
- Includes job status breakdown and recent images
- Cache hint for clients (30s recommended refresh)

---

## Remaining Tasks

### 11. Optional: Prometheus Server & Grafana

> **Note:** Only needed when you require historical metrics (>24h) or alerting.
> Current `/metrics` endpoint works for spot-checks without a server.

**When to implement:**

- Operations team needs dashboards
- Want alerting on error rates or latency
- Need to track trends over days/weeks

```bash
# Install Prometheus server
sudo apt-get install prometheus

# Configure scraping (/etc/prometheus/prometheus.yml)
scrape_configs:
  - job_name: 'dsa110-api'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics
    scrape_interval: 15s

# Install Grafana
sudo apt-get install grafana
sudo systemctl enable grafana-server
sudo systemctl start grafana-server
# Access at http://localhost:3000 (admin/admin)
```

### 12. Optional: Redis Caching

> **Current scale:** 12 MS, 4 images, 21 photometry records **Recommendation:**
> Defer until photometry >10,000 records OR p95 latency >100ms

**When to implement:**

- Dashboard loads feel slow (>500ms)
- Multiple concurrent users cause lock contention
- Lightcurve queries for sources with 1000+ observations

**Safe caching strategy (when needed):**

```python
# Only cache truly static data with poll-based invalidation
CACHEABLE = {
    "stats:summary": 30,      # Refresh every 30s
    "cal:tables:all": 3600,   # Calibrator catalog (hourly)
}

# NEVER cache:
# - Lightcurves without explicit end_date (scientists expect current data)
# - Job status during pipeline runs
# - Individual record lookups (low hit rate, not worth complexity)
```

**Cache invalidation approach:** Since the API is read-only and the pipeline
writes directly to SQLite, use TTL-based expiration rather than event-driven
invalidation.

---

## Long-term Improvements

### Performance (When Scale Requires)

- Redis caching (see above - defer until needed)
- Database connection pooling (SQLite handles current load)
- Add pagination to large result sets (already implemented with limit/offset)

### Features

- WebSocket support for real-time updates
- Batch operations API
- Export API (CSV/JSON downloads)
- GraphQL API for flexible queries

---

## Troubleshooting

### API not responding

```bash
lsof -i :8000                              # Check if running
sudo systemctl status dsa110-api.service   # Check service status
sudo journalctl -u dsa110-api.service -n 50 # Check logs
sudo systemctl restart dsa110-api.service  # Restart
```

### Database locked errors

```bash
sqlite3 /data/dsa110-contimg/state/products.sqlite3 "PRAGMA journal_mode=WAL;"
```

### CORS errors in frontend

Update `allow_origins` in `backend/src/dsa110_contimg/api/app.py`

### Verify database state

```bash
sqlite3 /data/dsa110-contimg/state/products.sqlite3 "
SELECT 'MS:', COUNT(*) FROM ms_index;
SELECT 'Images:', COUNT(*) FROM images;
SELECT 'Photometry:', COUNT(*) FROM photometry;
"
```

---

## Quick Reference

```bash
# Check API health
curl http://localhost:8000/api/health

# Run endpoint tests
cd /data/dsa110-contimg/backend && bash test_api_endpoints.sh

# View API docs
open http://localhost:8000/api/docs

# Check systemd service
sudo systemctl status dsa110-api.service
```
