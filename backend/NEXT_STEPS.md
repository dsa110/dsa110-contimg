# Next Steps - DSA-110 Continuum Imaging Pipeline

## Status: Core Setup Complete ✅ (Updated 2025-11-28)

The API backend is fully operational with real data. Database tables are
populated and all endpoints are returning real data.

### Current State

| Component  | Status         | Details                    |
| ---------- | -------------- | -------------------------- |
| API Server | ✅ Running     | Port 8000, systemd enabled |
| MS Records | ✅ 12 records  | Real measurement sets      |
| Images     | ✅ 4 records   | FITS files registered      |
| Photometry | ✅ 21 records  | 5 unique sources           |
| Cal Tables | ✅ 3 records   | Linked to source MS        |
| Batch Jobs | ✅ 7 jobs      | Provenance tracking        |
| Lightcurve | ✅ Implemented | Returns real flux data     |

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

---

## Remaining Tasks

### 7. Build and Deploy Frontend

**Goal:** Build production frontend and serve it

```bash
cd /data/dsa110-contimg/frontend

# Build for production
npm run build:scratch

# Option A: Serve with Nginx (recommended)
sudo tee /etc/nginx/sites-available/dsa110-frontend > /dev/null <<EOF
server {
    listen 80;
    server_name dsa110.local;
    root /data/dsa110-contimg/frontend/dist;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://localhost:8000/api/;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/dsa110-frontend /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 8. Add Authentication (Optional)

**Goal:** Secure API with authentication

**Simple API Key approach:**

```python
# In backend/src/dsa110_contimg/api/app.py
from fastapi import Header, HTTPException, Depends

API_KEY = os.getenv("DSA110_API_KEY", "your-secret-key")

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return x_api_key

# Add to endpoints:
@app.get("/api/images/{id}", dependencies=[Depends(verify_api_key)])
```

### 9. Add Monitoring (Optional)

```bash
# Add Prometheus metrics
pip install prometheus-fastapi-instrumentator

# In app.py:
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

---

## Long-term Improvements

### Performance

- Add Redis caching for frequently accessed data
- Implement database connection pooling
- Add pagination to large result sets

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
