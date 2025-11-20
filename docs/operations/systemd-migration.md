# Systemd Service Migration Note

## Issue

The existing `contimg-api.service` was using the **old module path**:

```bash
uvicorn dsa110_contimg.api:app
```

This conflicts with the new control panel implementation which uses the
**factory pattern**:

```bash
uvicorn dsa110_contimg.api.routes:create_app --factory
```

## Resolution

1. **Disabled old service** to prevent conflicts:

   ```bash
   sudo systemctl disable contimg-api.service
   sudo systemctl stop contimg-api.service
   ```

2. **Use service management script** for development:

   ```bash
   /data/dsa110-contimg/scripts/manage-services.sh start api
   ```

3. **For production**, use the NEW systemd service:
   ```bash
   sudo cp /data/dsa110-contimg/ops/systemd/contimg-api.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable dsa110-api.service
   sudo systemctl start dsa110-api.service
   ```

## Key Differences

| Old Service              | New Service                                      |
| ------------------------ | ------------------------------------------------ |
| `contimg-api.service`    | `dsa110-api.service`                             |
| `dsa110_contimg.api:app` | `dsa110_contimg.api.routes:create_app --factory` |
| Port from env var        | Port 8000 (hardcoded)                            |
| Override in drop-in      | Clean service file                               |

## Checking Status

```bash
# Old service (should be disabled)
sudo systemctl status contimg-api.service

# New service (if using systemd)
sudo systemctl status dsa110-api.service

# Or use service script
/data/dsa110-contimg/scripts/manage-services.sh status
```

## Migration Steps

If you want to migrate to the new systemd service:

1. **Stop old service**:

   ```bash
   sudo systemctl stop contimg-api.service
   sudo systemctl disable contimg-api.service
   ```

2. **Install new service**:

   ```bash
   sudo cp /data/dsa110-contimg/ops/systemd/contimg-api.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

3. **Update override** (if needed):

   ```bash
   # Remove old override
   sudo rm -rf /etc/systemd/system/contimg-api.service.d/
   ```

4. **Enable and start**:

   ```bash
   sudo systemctl enable dsa110-api.service
   sudo systemctl start dsa110-api.service
   ```

5. **Verify**:
   ```bash
   sudo systemctl status dsa110-api.service
   curl http://localhost:8000/api/status
   curl http://localhost:8000/api/ms
   ```

## Current Recommendation

**For now, use the service management script** which handles everything
automatically:

```bash
/data/dsa110-contimg/scripts/manage-services.sh start api
```

This avoids systemd complexity and works immediately.

---

**Date**: 2025-10-27  
**Status**: Old service disabled, new service available but not enabled
