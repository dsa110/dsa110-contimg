# CARTA Service Management

## Overview

CARTA is now managed via docker-compose with automatic restart and health
monitoring.

## Configuration

- **File**: `docker-compose.carta.yml`
- **Port**: 9002 (both frontend and backend)
- **Frontend URL**: http://localhost:9002
- **Data Volumes**:
  - `/data/dsa110-contimg` → `/images/data` (read-only)
  - `/stage/dsa110-contimg` → `/images/stage` (read-only)

## Management Commands

### Start CARTA

```bash
cd /data/dsa110-contimg/docker
docker-compose -f docker-compose.carta.yml up -d
```

### Stop CARTA

```bash
cd /data/dsa110-contimg/docker
docker-compose -f docker-compose.carta.yml down
```

### Restart CARTA

```bash
cd /data/dsa110-contimg/docker
docker-compose -f docker-compose.carta.yml restart
```

### Check Status

```bash
docker ps --filter "name=carta"
docker inspect carta-backend --format '{{.State.Health.Status}}'
```

### View Logs

```bash
docker-compose -f docker-compose.carta.yml logs -f
# Or just recent logs:
docker logs carta-backend --tail 50
```

## Health Monitoring

- **Check Interval**: Every 30 seconds
- **Method**: Verifies `carta_backend` process is running
- **Auto-Restart**: Container automatically restarts on failure

## Troubleshooting

### Connection Reset on Port 9002

1. Check health status:
   `docker inspect carta-backend --format '{{.State.Health.Status}}'`
2. If unhealthy, restart: `docker-compose -f docker-compose.carta.yml restart`
3. Check logs: `docker logs carta-backend --tail 50`

### Container Won't Start

1. Check for port conflicts: `netstat -tuln | grep 9002`
2. View container logs: `docker logs carta-backend`
3. Verify volumes exist: `ls -la /data/dsa110-contimg /stage/dsa110-contimg`

### Frontend Not Loading

1. Verify CARTA is listening:
   `docker exec carta-backend ps aux | grep carta_backend`
2. Test connection: `curl -I http://localhost:9002`
3. Check browser console for WebSocket errors

## Automatic Recovery

The container is configured with `restart: unless-stopped`, which means:

- **Automatically restarts** if the process crashes
- **Starts on boot** if Docker daemon is configured to start on boot
- **Only stops** when explicitly stopped via `docker-compose down` or
  `docker stop`

## Log Management

Logs are automatically rotated to prevent disk bloat:

- Max size per file: 10 MB
- Max number of files: 3
- Total max log size: ~30 MB

## Migration from Manual Container

If you previously ran CARTA manually with `docker run`, remove the old container
first:

```bash
docker stop carta-backend && docker rm carta-backend
# Then start with docker-compose as shown above
```
