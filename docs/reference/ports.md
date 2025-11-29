# Port Mapping Reference

This document lists all network ports used by the DSA-110 Continuum Imaging
Pipeline services, monitoring stack, and development tools.

**Last Updated:** 2025-11-29

## Robust Port Reservation

All production services are configured with **robust port reservation**. This
means:

1. **Exclusive Port Ownership**: Each service is assigned a specific port that
   it owns exclusively
2. **Automatic Conflict Resolution**: Before starting, each service runs
   `/usr/local/bin/claim-port.sh` which:
   - Checks if the assigned port is in use
   - Sends SIGTERM to any occupying process (graceful shutdown)
   - Waits up to 5 seconds for graceful termination
   - Sends SIGKILL if the process doesn't exit
   - Only then starts the service
3. **No Fallback Ports**: Services will NOT move to alternative ports - they
   will claim their assigned port

This is implemented via `ExecStartPre` in systemd service files.

## Quick Reference

| Port | Service            | Protocol | Access           | Configurable      | Robust? |
| ---- | ------------------ | -------- | ---------------- | ----------------- | ------- |
| 80   | Nginx              | HTTP     | Public           | No                | No†     |
| 3000 | Vite Dev Server    | HTTP     | Dev only         | No (hardcoded)    | No      |
| 3030 | Grafana            | HTTP     | Localhost        | grafana.ini       | **Yes** |
| 5173 | Vite Dev (default) | HTTP     | Dev only         | No (hardcoded)    | No      |
| 6379 | Redis              | TCP      | Localhost        | REDIS_PORT        | **Yes** |
| 8000 | FastAPI            | HTTP     | Private networks | CONTIMG_API_PORT  | **Yes** |
| 8001 | MkDocs             | HTTP     | Dev only         | CONTIMG_DOCS_PORT | No      |
| 9090 | Prometheus         | HTTP     | Localhost        | prometheus.yml    | **Yes** |

†Nginx doesn't need robust reservation as port 80 typically has no conflicts.

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

## Port Claim Utility

The `/usr/local/bin/claim-port.sh` script provides robust port reservation. It
is automatically invoked by systemd before starting services, but can also be
used manually.

### Usage

```bash
# Check if port would be freed (dry run)
/usr/local/bin/claim-port.sh 8000 --dry-run

# Actually free the port
sudo /usr/local/bin/claim-port.sh 8000

# Custom timeout (default 5 seconds)
sudo /usr/local/bin/claim-port.sh 8000 --timeout=10

# Skip graceful shutdown, use SIGKILL immediately
sudo /usr/local/bin/claim-port.sh 8000 --force
```

### How It Works

1. Checks if the port has a **listening** process with `lsof -sTCP:LISTEN`
   (ignores client connections to that port)
2. If free, exits successfully
3. If occupied by a listener:
   - **Validates** the process is not protected (systemd, sshd, init, etc.)
   - Sends SIGTERM to the listening process
   - Waits up to 5 seconds (configurable) for graceful shutdown
   - Sends SIGKILL to any remaining listener
   - Verifies port is now free

### Safety Features

- **Protected Process Detection**: Will not kill systemd, systemd-\*, journald,
  sshd, init, dbus-daemon, or any process with PID ≤ 2
- **Structured Logging**: All output prefixed with `[claim-port:<port>]` for
  easy filtering in journalctl
- **Port Validation**: Rejects invalid port numbers (must be 1-65535)
- **Timeout Validation**: Ensures `--timeout` is a valid number
- **Dependency Check**: Verifies `lsof` is installed before running
- **Detailed Process Info**: Logs full command line of processes being killed

### Systemd Integration

All services use `ExecStartPre=+` to run the script as root (required to kill
processes owned by other users):

```ini
# The + prefix ensures claim-port runs as root regardless of service User=
ExecStartPre=+/usr/local/bin/claim-port.sh <port>
```

### Configured Services

| Service        | Port | Configuration Location                                       |
| -------------- | ---- | ------------------------------------------------------------ |
| dsa110-api     | 8000 | `/etc/systemd/system/dsa110-api.service`                     |
| prometheus     | 9090 | `/etc/systemd/system/prometheus.service.d/claim-port.conf`   |
| redis-server   | 6379 | `/etc/systemd/system/redis-server.service.d/claim-port.conf` |
| grafana-simple | 3030 | `/etc/systemd/system/grafana-simple.service`                 |

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

| Conflict         | Resolution                                 |
| ---------------- | ------------------------------------------ |
| Grafana vs Vite  | Grafana moved to 3030                      |
| Multiple uvicorn | `pkill -f "dsa110_contimg.api"`            |
| Port 80 in use   | Stop other web server or change nginx port |

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

### Testing & Health Checks

#### Self-Test

The script includes built-in self-tests:

```bash
# Run self-tests
/usr/local/bin/claim-port.sh --test
```

This validates:
- Argument parsing
- Port range validation  
- Timeout validation
- Error handling

#### Health Check Script

A comprehensive health check is available:

```bash
# Run port reservation health check
/data/dsa110-contimg/scripts/ops/port-health-check.sh
```

This checks:
- Script availability and dependencies
- Systemd configuration for all services
- Port status (listening vs not)
- Conflict detection

Exit codes:
- `0`: All checks passed
- `1`: Errors found (critical issues)
- `2`: Warnings only (non-critical)

#### Monitoring via Cron

Add to crontab for periodic health checks:

```bash
# Check port health every 5 minutes
*/5 * * * * /data/dsa110-contimg/scripts/ops/port-health-check.sh >> /var/log/port-health.log 2>&1
```
