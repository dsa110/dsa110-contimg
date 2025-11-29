# Port Mapping Reference

This document lists all network ports used by the DSA-110 Continuum Imaging
Pipeline services, monitoring stack, and development tools.

**Last Updated:** 2025-11-29

## Quick Reference

| Port | Service            | Protocol | Access           | Configurable          |
| ---- | ------------------ | -------- | ---------------- | --------------------- |
| 80   | Nginx              | HTTP     | Public           | No                    |
| 3000 | Vite Dev Server    | HTTP     | Dev only         | No (hardcoded)        |
| 3030 | Grafana            | HTTP     | Localhost        | grafana.ini           |
| 5173 | Vite Dev (default) | HTTP     | Dev only         | No (hardcoded)        |
| 6379 | Redis              | TCP      | Localhost        | REDIS_PORT            |
| 8000 | FastAPI            | HTTP     | Private networks | CONTIMG_API_PORT      |
| 8001 | MkDocs             | HTTP     | Dev only         | CONTIMG_DOCS_PORT     |
| 9090 | Prometheus         | HTTP     | Localhost        | prometheus.yml        |

## Production Services

### Port 80 - Nginx Reverse Proxy

- **Config:** `/etc/nginx/sites-available/dsa110-contimg`
- **Service:** `nginx.service`
- **Purpose:**
  - Serves frontend static files from `/data/dsa110-contimg/frontend/dist`
  - Proxies `/api/` requests to FastAPI on port 8000
  - Restricts `/metrics` to localhost only
- **Access:** Publicly accessible (firewall permitting)

### Port 8000 - FastAPI Backend

- **Config:** `/etc/systemd/system/dsa110-api.service`
- **Service:** `dsa110-api.service`
- **Environment Variable:** `CONTIMG_API_PORT`
- **Purpose:**
  - REST API for pipeline data
  - Prometheus metrics at `/metrics`
  - Health check at `/api/health`
- **Access:** Localhost and private networks (10.x, 172.16.x, 192.168.x)
- **Docs:** Interactive API docs at `/api/docs`

### Port 6379 - Redis

- **Config:** `/etc/redis/redis.conf`
- **Service:** `redis-server.service`
- **Environment Variable:** `REDIS_PORT`
- **Purpose:**
  - API response caching with TTL-based expiration
  - Cache management via `/api/cache` endpoints
- **Access:** Localhost only (no authentication)

## Monitoring Stack

### Port 9090 - Prometheus Server

- **Config:** `/etc/prometheus/prometheus.yml`
- **Service:** `prometheus.service`
- **Purpose:**
  - Scrapes metrics from dsa110-api every 15 seconds
  - Stores time-series data for Grafana
- **UI:** Query interface at `http://localhost:9090`
- **Access:** Localhost only

### Port 3030 - Grafana

- **Config:** `/etc/grafana/grafana.ini` (http_port = 3030)
- **Service:** `grafana-simple.service`
- **Default Credentials:** admin / admin
- **Purpose:** Prometheus visualization and dashboards
- **Dashboard:** `/d/dsa110-pipeline/dsa-110-continuum-imaging-pipeline`
- **Note:** Uses 3030 to avoid conflict with Vite dev server on 3000

## Development Services

### Port 3000 / 5173 - Vite Dev Server

- **Command:** `npm run dev` in `/data/dsa110-contimg/frontend`
- **Purpose:** Hot-reload development server for Vue.js frontend
- **Access:** Development only, not for production
- **Note:** Port varies by Vite version (3000 or 5173)

### Port 8001 - MkDocs Documentation

- **Command:** `mkdocs serve`
- **Environment Variable:** `CONTIMG_DOCS_PORT`
- **Purpose:** Local documentation preview
- **Access:** Development only

## Reserved Ranges

- **3210-3220**: Dashboard fallback ports (auto-selected if 3210 busy)
- **8010**: Alternative API port (if needed)

## Common Commands

```bash
# List all listening ports
ss -tlnp

# Check specific port
lsof -i :8000

# Kill process on port
sudo fuser -k 8000/tcp

# Check all DSA-110 services
sudo systemctl status nginx prometheus dsa110-api redis-server grafana-simple

# Start/stop services
./scripts/manage-services.sh start all
./scripts/manage-services.sh stop all
./scripts/manage-services.sh status
```

## Port Conflict Resolution

### Find What's Using a Port

```bash
sudo lsof -i :<port>
# or
sudo netstat -tlnp | grep :<port>
```

### Kill Process by Port

```bash
# Graceful
sudo fuser -k <port>/tcp

# Force
sudo kill -9 $(lsof -ti :<port>)
```

### Common Conflicts

| Conflict              | Resolution                                       |
| --------------------- | ------------------------------------------------ |
| Grafana vs Vite       | Grafana moved to 3030                            |
| Multiple uvicorn      | `pkill -f "dsa110_contimg.api"`                  |
| Port 80 in use        | Stop other web server or change nginx port       |

## Firewall Configuration

```bash
# Allow HTTP (Nginx only, internal services stay blocked)
sudo ufw allow 80/tcp

# Check firewall status
sudo ufw status

# Internal services (8000, 9090, 3030, 6379) should NOT be exposed
```

## Related Documentation

- [API Reference](api.md) - REST API endpoints
- [Security](security.md) - IP-based access control
- [Monitoring](monitoring.md) - Prometheus metrics
- [Nginx Configuration](nginx.md) - Reverse proxy setup
