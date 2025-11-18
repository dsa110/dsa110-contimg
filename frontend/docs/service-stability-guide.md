# Service Stability Guide

**Date:** 2025-11-17  
**Status:** ✅ Active

---

## Overview

This guide explains how to ensure both frontend (Vite dev server) and backend
(Docker API) remain perfectly stable unless explicitly restarted.

---

## Current Stability Features

### Backend (Docker API - Port 8000)

**Already configured with:**

- ✅ **Restart policy:** `unless-stopped` (survives reboots)
- ✅ **Health checks:** Every 30s, auto-restart on failure
- ✅ **Resource limits:** Managed by Docker
- ✅ **Logging:** Container logs via Docker

**Status check:**

```bash
docker ps | grep dsa110-api
curl -s http://localhost:8000/api/status | jq .
```

**Manual restart:**

```bash
docker restart dsa110-api
# or
/data/dsa110-contimg/restart_backend.sh
```

### Frontend (Vite Dev Server - Port 3210)

**New stability features added:**

- ✅ **Process manager:** `manage-dev-server.sh`
- ✅ **Health monitoring:** Automatic health checks
- ✅ **Auto-restart:** Up to 3 attempts on failure
- ✅ **Log rotation:** Prevents disk fill (>100MB)
- ✅ **Graceful shutdown:** Clean termination
- ✅ **Resource monitoring:** CPU/memory tracking

---

## Quick Start

### Option 1: Manual Management (Simple)

```bash
cd /data/dsa110-contimg/frontend

# Start the server
./scripts/manage-dev-server.sh start

# Check status
./scripts/manage-dev-server.sh status

# Watch logs
./scripts/manage-dev-server.sh logs

# Restart
./scripts/manage-dev-server.sh restart

# Stop
./scripts/manage-dev-server.sh stop
```

### Option 2: Systemd Service (Recommended for Production)

```bash
# Install service (one-time setup)
sudo cp frontend/scripts/vite-dev.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable vite-dev
sudo systemctl start vite-dev

# Check status
sudo systemctl status vite-dev

# Restart
sudo systemctl restart vite-dev

# View logs
sudo journalctl -u vite-dev -f
```

### Option 3: Monitoring Mode (Auto-restart on failure)

```bash
cd /data/dsa110-contimg/frontend

# Start with monitoring (runs in foreground)
./scripts/manage-dev-server.sh monitor

# Or run in background with screen/tmux
screen -dmS vite-monitor ./scripts/manage-dev-server.sh monitor
```

---

## Complete Monitoring Solution

Monitor both frontend and backend together:

```bash
# Single health check
/data/dsa110-contimg/scripts/monitor-services.sh

# Continuous monitoring (manual restart)
/data/dsa110-contimg/scripts/monitor-services.sh --interval 30

# Auto-restart on failure
/data/dsa110-contimg/scripts/monitor-services.sh --interval 30 --auto-restart

# Run in background
screen -dmS service-monitor \
    /data/dsa110-contimg/scripts/monitor-services.sh --interval 30 --auto-restart
```

---

## Stability Best Practices

### 1. Start Both Services on Boot

**Backend (already configured):**

```bash
docker update --restart unless-stopped dsa110-api
```

**Frontend (systemd):**

```bash
sudo systemctl enable vite-dev
```

### 2. Monitor Continuously

Run the monitoring script in the background:

```bash
# Add to crontab to ensure monitor is always running
crontab -e

# Add this line:
*/5 * * * * pgrep -f "monitor-services.sh" || screen -dmS service-monitor /data/dsa110-contimg/scripts/monitor-services.sh --interval 30 --auto-restart
```

### 3. Log Management

**Frontend logs:**

```bash
# View current logs
tail -f /tmp/vite-dev-server.log

# Logs rotate automatically at 100MB
ls -lh /tmp/vite-dev-server.log*
```

**Backend logs:**

```bash
# Docker logs
docker logs dsa110-api --tail 100 -f

# Or backend log file
tail -f /tmp/backend.log
```

### 4. Resource Monitoring

**Check resource usage:**

```bash
# Frontend (if using systemd)
systemctl status vite-dev

# Backend
docker stats dsa110-api --no-stream

# Both
/data/dsa110-contimg/frontend/scripts/manage-dev-server.sh status
docker stats dsa110-api --no-stream
```

---

## Troubleshooting

### Frontend Won't Start

```bash
# Check if port is in use
lsof -i :3210

# Check logs
cat /tmp/vite-dev-server.log

# Force stop and restart
pkill -f "node.*vite"
./scripts/manage-dev-server.sh start
```

### Backend Won't Start

```bash
# Check Docker container status
docker ps -a | grep dsa110-api

# Check logs
docker logs dsa110-api --tail 50

# Restart
docker restart dsa110-api

# Full rebuild if needed
cd /data/dsa110-contimg
docker-compose up -d --build api
```

### Both Services Failing

```bash
# Check disk space
df -h

# Check system resources
free -h
top

# Check for port conflicts
lsof -i :3210
lsof -i :8000

# Nuclear option: restart both
docker restart dsa110-api
./scripts/manage-dev-server.sh restart
```

---

## Automated Recovery

### Health Check Intervals

- **Frontend:** Every 30s (configurable in `manage-dev-server.sh`)
- **Backend:** Every 30s (configured in `docker-compose.yml`)
- **Combined monitor:** Every 30s (adjustable via `--interval`)

### Restart Policies

**Frontend:**

- Max 3 restart attempts
- 10s delay between attempts
- Requires manual intervention after max attempts

**Backend:**

- Docker `unless-stopped` policy
- Automatic restart on failure
- Health check retries: 3

---

## Status Dashboard

Quick status check:

```bash
echo "=== DSA-110 Services Status ==="
echo ""
echo "Frontend:"
curl -sf http://localhost:3210/ > /dev/null && echo "  ✅ Healthy" || echo "  ❌ Down"
echo ""
echo "Backend:"
curl -sf http://localhost:8000/api/status > /dev/null && echo "  ✅ Healthy" || echo "  ❌ Down"
```

---

## Files Reference

**Frontend Management:**

- `frontend/scripts/manage-dev-server.sh` - Process manager
- `frontend/scripts/vite-dev.service` - Systemd service
- `/tmp/vite-dev-server.log` - Frontend logs
- `/tmp/vite-dev-server.pid` - Process ID file

**Combined Monitoring:**

- `scripts/monitor-services.sh` - Health monitor for both services
- `/tmp/services-monitor.log` - Monitor logs

**Backend Management:**

- `docker-compose.yml` - Docker configuration
- `restart_backend.sh` - Backend restart script
- `/tmp/backend.log` - Backend logs

---

## Production Deployment

For production deployment, use the built dashboard:

```bash
cd /data/dsa110-contimg/frontend
npm run build

# Deploy via Docker (port 3210)
docker-compose up -d dashboard
```

The production dashboard has the same stability features via Docker's restart
policies.

---

**Last Updated:** 2025-11-17  
**Maintainer:** Development Team
