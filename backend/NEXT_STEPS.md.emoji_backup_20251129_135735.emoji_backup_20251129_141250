# Next Steps - DSA-110 Continuum Imaging Pipeline

## Status: Full Stack Complete ✅ (Updated 2025-11-29)

The API backend is fully operational with real data, monitoring, and caching.

### Current State

| Component          | Status         | Details                      |
| ------------------ | -------------- | ---------------------------- |
| API Server         | ✅ Running     | Port 8000, systemd enabled   |
| MS Records         | ✅ 12 records  | Real measurement sets        |
| Images             | ✅ 4 records   | FITS files registered        |
| Photometry         | ✅ 21 records  | 5 unique sources             |
| Cal Tables         | ✅ 3 records   | Linked to source MS          |
| Batch Jobs         | ✅ 7 jobs      | Provenance tracking          |
| Lightcurve         | ✅ Implemented | Returns real flux data       |
| Nginx              | ✅ Configured  | Reverse proxy on port 80     |
| Prometheus Metrics | ✅ Enabled     | Metrics at /metrics          |
| Prometheus Server  | ✅ Running     | Scraping API on port 9090    |
| Redis Cache        | ✅ Connected   | TTL-based caching enabled    |
| Stats API          | ✅ Implemented | Summary counts at /api/stats |
| IP Security        | ✅ Active      | Localhost + private networks |
| Grafana            | ✅ Running     | Dashboard on port 3030       |
| Scientific Metrics | ✅ Enabled     | MS, images, sources gauges   |

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

### 11. Prometheus Server ✅

- Prometheus server running on port 9090
- Scraping DSA-110 API every 15 seconds
- 927 unique metrics collected
- Config at `/etc/prometheus/prometheus.yml`
- Access UI: `http://localhost:9090`

### 12. Redis Caching ✅

- Redis connected and caching enabled
- TTL-based expiration (no event-driven invalidation needed)
- Cache management endpoints at `/api/cache`
- Blacklist prevents caching of real-time data (open lightcurves, active jobs)

**Cache TTL Configuration:** | Key Prefix | TTL | Rationale |
|------------|-----|-----------| | `stats` | 30s | Frequently accessed summary |
| `sources:list` | 5 min | Changes only on new detections | | `images:list` | 5
min | Changes only on new imaging | | `cal:tables` | 1 hour | Nearly static
calibrator catalog | | `jobs:list` | 1 min | Changes during pipeline runs |

**Never Cached:**

- Open-ended lightcurves (scientists expect current data)
- Active job status
- Real-time logs

---

## Completed Tasks ✅

### 13. Grafana Dashboard ✅

- Grafana running on port 3030 (3000 used by frontend dev server)
- Prometheus datasource configured
- DSA-110 Pipeline Dashboard imported with 10 panels:
  - API Status, Error Rate, Request Rate, P95 Latency
  - Total Images, Total Sources, Pending Jobs
  - Cache Hit Rate, API Memory Usage, Request Rate by Endpoint
- Access: `http://localhost:3030` (admin/admin)
- Dashboard path: `/d/dsa110-pipeline/dsa-110-continuum-imaging-pipeline`

### 14. Custom Scientific Metrics ✅

- `dsa110_ms_count{stage}` - Measurement sets discovered
- `dsa110_images_count{type}` - Images by type (image/mosaic)
- `dsa110_sources_count` - Unique sources detected
- `dsa110_photometry_count` - Total photometry measurements
- `dsa110_pending_jobs` / `dsa110_running_jobs` - Job status
- `dsa110_image_noise_jy` - Histogram of image RMS noise
- Gauges sync from database every 60 seconds

---

## Long-term Improvements

### Performance

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
