# Moved

See `docs/how-to/dashboard.md` (Deployment section).

---

## Table of Contents

1. [Deployment Overview](#deployment-overview)
2. [Build Process](#build-process)
3. [Docker Deployment](#docker-deployment)
4. [Systemd Deployment](#systemd-deployment)
5. [Static File Serving](#static-file-serving)
6. [Environment Configuration](#environment-configuration)
7. [Monitoring & Health Checks](#monitoring--health-checks)
8. [Troubleshooting](#troubleshooting)

---

## Deployment Overview

### Deployment Options

1. **Docker Compose** - Recommended for development/staging
2. **Systemd Services** - Recommended for production
3. **Static File Serving** - Nginx/Apache for frontend only
4. **FastAPI Static Mount** - Integrated with backend

### Architecture

```
┌─────────────────────────────────────────┐
│         Nginx/Apache (Optional)         │
│         Port: 80/443                    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      FastAPI Backend                     │
│      Port: 8000                          │
│      ┌──────────────────────────────┐   │
│      │  Static Files Mount (/ui)    │   │
│      │  Frontend Build (dist/)      │   │
│      └──────────────────────────────┘   │
└──────────────────────────────────────────┘
```

---

## Build Process

### Production Build

**Build Command:**

```bash
cd /data/dsa110-contimg/frontend
conda activate casa6
npm run build
```

**Output:**

- Build artifacts in `dist/` directory
- Optimized, minified JavaScript
- Optimized CSS
- Static assets

**Build Features:**

- Code splitting
- Tree shaking
- Minification
- Asset optimization
- Source maps (optional)

### Build Verification

**Preview Build:**

```bash
npm run preview
# Available at http://localhost:4173
```

**Check Build Output:**

```bash
ls -lh dist/
# Should see: index.html, assets/, etc.
```

---

## Docker Deployment

### Docker Compose

**Configuration (`docker-compose.yml`):**

```yaml
services:
  api:
    image: continuumdevs/dsa110-api:latest
    ports:
      - "8000:8000"
    volumes:
      - ./src:/app/src
      - ./state:/app/state
    environment:
      - PYTHONPATH=/app/src
    restart: unless-stopped

  dashboard:
    image: continuumdevs/dsa110-dashboard:latest
    ports:
      - "3000:3000"
    environment:
      - REACT_APP_API_URL=http://api:8000
    depends_on:
      - api
    restart: unless-stopped
```

**Deploy:**

```bash
docker-compose up -d
```

**Check Status:**

```bash
docker-compose ps
docker-compose logs -f dashboard
```

### Docker Image Build

**Build Frontend Image:**

```bash
cd frontend
docker build -t dsa110-dashboard:latest -f Dockerfile.prod .
```

**Dockerfile.prod:**

```dockerfile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## Systemd Deployment

### API Service

**Service File (`contimg-api.service`):**

```ini
[Unit]
Description=DSA-110 Continuum Pipeline API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/data/dsa110-contimg
Environment="PATH=/opt/miniforge/envs/casa6/bin"
ExecStart=/opt/miniforge/envs/casa6/bin/uvicorn dsa110_contimg.api.server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Install:**

```bash
sudo cp ops/systemd/contimg-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable contimg-api.service
sudo systemctl start contimg-api.service
```

**Manage:**

```bash
# Status
sudo systemctl status contimg-api.service

# Logs
sudo journalctl -u contimg-api.service -f

# Restart
sudo systemctl restart contimg-api.service
```

### Dashboard Service (Optional)

**If serving separately:**

```bash
# Build frontend
cd /data/dsa110-contimg/frontend
npm run build

# Install serve
sudo npm install -g serve

# Create service
sudo nano /etc/systemd/system/dsa110-dashboard.service
```

**Service File:**

```ini
[Unit]
Description=DSA-110 Dashboard
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/data/dsa110-contimg/frontend
ExecStart=/usr/local/bin/serve -s dist -l 3000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Static File Serving

### FastAPI Static Mount (Recommended)

**Integrated with Backend:**

```python
# In api/routes.py
from fastapi.staticfiles import StaticFiles

app.mount("/ui", StaticFiles(directory="frontend/dist", html=True), name="ui")
```

**Access:**

- Frontend: `http://localhost:8000/ui`
- API: `http://localhost:8000/api`

**Benefits:**

- Single service to manage
- Same port for frontend and API
- Simplified deployment

### Nginx Reverse Proxy

**Configuration (`nginx.conf`):**

```nginx
server {
    listen 80;
    server_name dsa110-pipeline.caltech.edu;

    # Frontend
    location /ui {
        alias /data/dsa110-contimg/frontend/dist;
        try_files $uri $uri/ /ui/index.html;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Root redirect
    location / {
        return 301 /ui;
    }
}
```

---

## Environment Configuration

### Environment Variables

**Development (`.env.development`):**

```bash
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

**Production (`.env.production`):**

```bash
VITE_API_URL=https://dsa110-pipeline.caltech.edu/api
VITE_WS_URL=wss://dsa110-pipeline.caltech.edu/api/ws
```

**Build-Time Variables:**

- Variables prefixed with `VITE_` are embedded at build time
- Must rebuild frontend after changing environment variables

### Configuration Files

**Backend Configuration:**

- `ops/systemd/contimg.env` - Environment variables for systemd
- `.env` - Local development environment

---

## Monitoring & Health Checks

### Health Check Endpoints

**API Health:**

```bash
curl http://localhost:8000/api/status
```

**Frontend Health:**

```bash
curl http://localhost:3000/
# Should return HTML
```

### Monitoring Scripts

**Check Services:**

```bash
# Check API
curl -f http://localhost:8000/api/status || echo "API down"

# Check Frontend
curl -f http://localhost:3000/ || echo "Frontend down"
```

### Log Monitoring

**Systemd Logs:**

```bash
# Follow logs
sudo journalctl -u contimg-api.service -f

# Last 100 lines
sudo journalctl -u contimg-api.service -n 100
```

**Docker Logs:**

```bash
docker-compose logs -f api
docker-compose logs -f dashboard
```

---

## Troubleshooting

### Build Failures

**Problem:** Build fails with errors

**Solutions:**

1. Check Node.js version: `node --version` (should be v22+)
2. Clean install: `rm -rf node_modules && npm install`
3. Check for TypeScript errors: `npm run type-check`
4. Check disk space: `df -h`

### Service Won't Start

**Problem:** Systemd service fails to start

**Solutions:**

1. Check service status: `sudo systemctl status contimg-api.service`
2. Check logs: `sudo journalctl -u contimg-api.service`
3. Verify paths in service file
4. Check permissions: `ls -l /data/dsa110-contimg`

### Port Conflicts

**Problem:** Port already in use

**Solutions:**

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in service file
```

### Frontend Not Loading

**Problem:** Frontend shows blank page or errors

**Solutions:**

1. Check browser console for errors
2. Verify API URL in environment variables
3. Check CORS settings in backend
4. Verify build output exists: `ls -l dist/`

---

## See Also

- [Development Workflow](./dashboard_development_workflow.md) - Development
  setup
- [Architecture](../concepts/dashboard_architecture.md) - System architecture
- [Backend API](../reference/dashboard_backend_api.md) - API documentation
