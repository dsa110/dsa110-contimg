# CASA Log Daemon (inotifywait) - Deployment Guide

## Overview

This new daemon uses `inotifywait` (kernel-level inotify) to monitor **all directories recursively** with minimal CPU and memory usage.

## Key Advantages

- **Low CPU**: ~0% when idle (kernel-level monitoring)
- **Low Memory**: ~10-50MB (vs ~10GB for watchdog recursive mode)
- **Recursive**: Monitors all subdirectories automatically
- **Efficient**: Only watches `create` and `moved_to` events
- **Smart**: Excludes target directory to avoid watching moved files

## Files Created

1. **`casa_log_daemon_inotify.sh`** - Pure bash version (lowest overhead)
2. **`casa_log_daemon_inotify.py`** - Python version (better logging/error handling)
3. **`casa-log-daemon-inotify.service`** - Systemd service for bash version
4. **`casa-log-daemon-inotify-python.service`** - Systemd service for Python version

## Deployment Steps

### Option 1: Bash Version (Recommended - Lowest Resource Usage)

1. **Stop old services:**
   ```bash
   sudo systemctl stop casa-log-daemon.service
   sudo systemctl stop casa-log-mover.service
   sudo systemctl disable casa-log-daemon.service
   sudo systemctl disable casa-log-mover.service
   ```

2. **Install new service:**
   ```bash
   sudo cp /data/dsa110-contimg/scripts/casa-log-daemon-inotify.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable casa-log-daemon-inotify.service
   sudo systemctl start casa-log-daemon-inotify.service
   ```

3. **Verify it's running:**
   ```bash
   sudo systemctl status casa-log-daemon-inotify.service
   ```

### Option 2: Python Version (Better Error Handling)

1. **Stop old services** (same as above)

2. **Install new service:**
   ```bash
   sudo cp /data/dsa110-contimg/scripts/casa-log-daemon-inotify-python.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable casa-log-daemon-inotify-python.service
   sudo systemctl start casa-log-daemon-inotify-python.service
   ```

3. **Verify it's running:**
   ```bash
   sudo systemctl status casa-log-daemon-inotify-python.service
   ```

## Testing

After deployment, test by creating a test casa log file:

```bash
touch /data/dsa110-contimg/src/test-casa-$(date +%Y%m%d-%H%M%S).log
```

Check that it gets moved to `/data/dsa110-contimg/state/logs/` within a few seconds.

## Monitoring

- **Logs**: `/data/dsa110-contimg/state/logs/casa_log_daemon_YYYYMMDD.log`
- **Systemd logs**: `sudo journalctl -u casa-log-daemon-inotify.service -f`
- **Resource usage**: `top -p $(pgrep -f casa_log_daemon_inotify)`

## Current Issues Fixed

The old daemon was missing:
- Files in `/src/` directory (not monitored)
- Files in `/state/` directory (not monitored)
- Only watched 4 specific directories (root, ms, tmp, scratch)

The new daemon:
- Monitors ALL directories recursively
- Uses kernel inotify (very efficient)
- Will catch casa logs from any location

## Resource Comparison

| Method | CPU (idle) | Memory | Coverage |
|--------|------------|--------|----------|
| Old watchdog (non-recursive) | ~0% | ~100MB | Limited (4 dirs) |
| Old watchdog (recursive) | ~0% | ~10GB | Full |
| New inotifywait (bash) | ~0% | ~10-20MB | Full |
| New inotifywait (Python) | ~0% | ~50-100MB | Full |

## Rollback

If you need to rollback to the old daemon:

```bash
sudo systemctl stop casa-log-daemon-inotify.service
sudo systemctl disable casa-log-daemon-inotify.service
sudo systemctl enable casa-log-daemon.service
sudo systemctl start casa-log-daemon.service
```

