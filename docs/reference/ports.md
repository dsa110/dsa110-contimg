# Port Mapping Reference

This document lists all network ports used by the DSA-110 Continuum Imaging
Pipeline monitoring and API stack.

## Port Summary

| Port | Service          | Protocol | Access            | Description                    |
| ---- | ---------------- | -------- | ----------------- | ------------------------------ |
| 80   | Nginx            | HTTP     | Public            | Reverse proxy, frontend        |
| 3000 | Vite Dev Server  | HTTP     | Dev only          | Frontend development server    |
| 3030 | Grafana          | HTTP     | Localhost         | Monitoring dashboard           |
| 6379 | Redis            | TCP      | Localhost         | Cache server                   |
| 8000 | FastAPI          | HTTP     | Private networks  | REST API backend               |
| 9090 | Prometheus       | HTTP     | Localhost         | Metrics collection server      |

## Service Details

### Port 80 - Nginx Reverse Proxy

- **Config:** `/etc/nginx/sites-available/dsa110-contimg`
- **Service:** `nginx.service`
- **Purpose:** 
  - Serves frontend static files from `/data/dsa110-contimg/frontend/dist`
  - Proxies `/api/` requests to FastAPI on port 8000
  - Restricts `/metrics` to localhost only
- **Access:** Publicly accessible (firewall permitting)

### Port 3000 - Vite Development Server

- **Command:** `npm run dev` in `/data/dsa110-contimg/frontend`
- **Purpose:** Hot-reload development server for Vue.js frontend
- **Access:** Development only, not for production
- **Note:** Only run when actively developing frontend

### Port 3030 - Grafana

- **Config:** `/etc/grafana/grafana.ini` (http_port = 3030)
- **Service:** `grafana-simple.service`
- **Default Credentials:** admin / admin
- **Purpose:** Prometheus visualization and dashboards
- **Dashboard URL:** `/d/dsa110-pipeline/dsa-110-continuum-imaging-pipeline`
- **Note:** Runs on 3030 instead of default 3000 to avoid conflict with Vite

### Port 6379 - Redis

- **Config:** `/etc/redis/redis.conf`
- **Service:** `redis-server.service`
- **Purpose:** 
  - API response caching with TTL-based expiration
  - Cache management via `/api/cache` endpoints
- **Access:** Localhost only (no authentication configured)

### Port 8000 - FastAPI Backend

- **Config:** Systemd service at `/etc/systemd/system/dsa110-api.service`
- **Service:** `dsa110-api.service`
- **Purpose:**
  - REST API for pipeline data
  - Prometheus metrics at `/metrics`
  - Health check at `/api/health`
- **Access:** Restricted to localhost and private networks (10.x, 172.16.x, 192.168.x)
- **Docs:** Interactive API docs at `/api/docs`

### Port 9090 - Prometheus Server

- **Config:** `/etc/prometheus/prometheus.yml`
- **Service:** `prometheus.service`
- **Purpose:**
  - Scrapes metrics from dsa110-api every 15 seconds
  - Stores time-series data for Grafana
- **UI:** Query interface at `http://localhost:9090`
- **Access:** Localhost only

## Firewall Considerations

For production deployments, configure firewall rules:

```bash
# Allow HTTP (Nginx)
sudo ufw allow 80/tcp

# Block direct access to internal services
# (These should only be accessible via localhost)
# 8000, 9090, 3030, 6379 - keep blocked from external
```

## Checking Port Usage

```bash
# List all listening ports
ss -tlnp

# Check specific port
lsof -i :8000

# Verify all services running
sudo systemctl status nginx prometheus dsa110-api redis-server grafana-simple
```

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :<port>

# Kill process if needed
sudo kill -9 <pid>
```

### Service Not Listening

```bash
# Check service status
sudo systemctl status <service-name>

# View logs
sudo journalctl -u <service-name> -n 50

# Restart service
sudo systemctl restart <service-name>
```

### Cannot Connect to Port

1. Check if service is running: `systemctl status <service>`
2. Check if port is listening: `ss -tlnp | grep <port>`
3. Check firewall: `sudo ufw status`
4. Check IP restrictions (for port 8000, see security.md)

## Related Documentation

- [API Reference](api.md) - REST API endpoints
- [Security](security.md) - IP-based access control
- [Monitoring](monitoring.md) - Prometheus metrics
- [Nginx Configuration](nginx.md) - Reverse proxy setup
