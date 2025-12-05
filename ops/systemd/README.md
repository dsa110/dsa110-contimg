# Systemd Service Files

> **📖 For a complete guide to all services (dev + production), see
> [docs/ops/SERVICES.md](../../docs/ops/SERVICES.md)**

## Core Services

| Service                            | Purpose               | Port |
| ---------------------------------- | --------------------- | ---- |
| `contimg-api.service`              | FastAPI backend       | 8000 |
| `dsa110-contimg-dashboard.service` | Production frontend   | 3210 |
| `contimg-stream.service`           | Real-time data ingest | -    |

### Quick Commands

```bash
# Start core services
sudo systemctl start contimg-api dsa110-contimg-dashboard

# Check status
sudo systemctl status contimg-api dsa110-contimg-dashboard

# View logs
sudo journalctl -u contimg-api -f
```

---

## Editing Service Files

Systemd service files in `/etc/systemd/system/` are owned by `root` and cannot
be edited directly by regular users.

### Workflow for Editing Service Files

1. **Edit the source file** in this directory:

   ```bash
   vim /data/dsa110-contimg/ops/systemd/contimg-pointing-monitor.service
   ```

2. **Deploy to systemd** using the deployment script:

   ```bash
   cd /data/dsa110-contimg/ops/systemd
   ./deploy_service.sh
   ```

3. **Restart the service** (if needed):
   ```bash
   sudo systemctl restart contimg-pointing-monitor.service
   ```

### Manual Deployment

If you prefer to deploy manually:

```bash
# Copy service file
sudo cp /data/dsa110-contimg/ops/systemd/contimg-pointing-monitor.service \
       /etc/systemd/system/contimg-pointing-monitor.service

# Reload systemd
sudo systemctl daemon-reload

# Restart service (if needed)
sudo systemctl restart contimg-pointing-monitor.service
```

### Checking Service Status

```bash
# View service status
sudo systemctl status contimg-pointing-monitor.service

# View service logs
sudo journalctl -u contimg-pointing-monitor.service -n 50

# View real-time logs
sudo journalctl -u contimg-pointing-monitor.service -f
```

## Service Files

### Active Services

- `contimg-api.service` - FastAPI backend API (port 8000)
- `dsa110-contimg-dashboard.service` - Production frontend via vite preview
  (port 3210)
- `contimg-stream.service` - Real-time HDF5 → MS streaming converter
- `contimg-docs.service` - MkDocs documentation server (port 8001)
- `contimg-pointing-monitor.service` - Pointing monitor daemon

### Support Files

- `contimg.env` - Environment variables used by all contimg services
- `deploy_service.sh` - Helper script to deploy service files

## Important Notes

- **Always edit the source file in this directory**, not the file in
  `/etc/systemd/system/`
- The source file is version controlled and the proper record of the service
  configuration
- The file in `/etc/systemd/system/` is a deployed copy and may be overwritten
- After editing, always run `deploy_service.sh` to deploy changes
- Don't forget to reload systemd with `systemctl daemon-reload` after deployment

## Systemd Version Compatibility

This system runs **systemd v237**, which has some limitations:

- :cross: `StandardOutput=append:` syntax not supported (requires v240+)
- :check: Use journalctl for logs instead of file redirection
- :check: All logs available via `journalctl -u service-name`
