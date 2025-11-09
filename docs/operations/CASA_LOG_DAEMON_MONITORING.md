# CASA Log Daemon Monitoring and Health Checks

## Overview

The CASA Log Daemon is now protected with multiple layers of monitoring and automatic recovery:

1. **Systemd Service**: Auto-restarts on failure
2. **Health Check Script**: Monitors daemon health
3. **Watchdog Timer**: Periodic health checks with automatic recovery
4. **Status File**: JSON status for monitoring tools

## Components

### 1. Health Check Script (`scripts/casa_log_daemon_health_check.sh`)

Checks:
- ✓ Daemon process is running
- ✓ Systemd service is active
- ✓ Daemon log file is recent (updated in last 10 minutes)
- ✓ Files aren't accumulating excessively (>10 files)
- ✓ Target directory exists and is writable

**Usage:**
```bash
/data/dsa110-contimg/scripts/casa_log_daemon_health_check.sh
```

**Exit Codes:**
- `0`: Healthy
- `1`: Unhealthy (issues detected)

**Status File:**
Creates `/data/dsa110-contimg/state/logs/.casa_log_daemon_status.json` with current health status.

### 2. Watchdog Timer (`casa-log-daemon-watchdog.timer`)

Runs health check every 5 minutes and automatically restarts the daemon if unhealthy.

**Installation:**
```bash
sudo cp /data/dsa110-contimg/scripts/casa-log-daemon-watchdog.service /etc/systemd/system/
sudo cp /data/dsa110-contimg/scripts/casa-log-daemon-watchdog.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable casa-log-daemon-watchdog.timer
sudo systemctl start casa-log-daemon-watchdog.timer
```

**Check Status:**
```bash
systemctl status casa-log-daemon-watchdog.timer
```

### 3. Enhanced Systemd Service

The main service now includes:
- Auto-restart on failure
- Start limit (prevents restart loops)
- Watchdog timeout (600 seconds)
- Enhanced logging to files

## Monitoring

### Check Health Status

```bash
# Run health check manually
/data/dsa110-contimg/scripts/casa_log_daemon_health_check.sh

# View status file
cat /data/dsa110-contimg/state/logs/.casa_log_daemon_status.json | jq .

# Check service status
systemctl status casa-log-daemon-inotify.service

# Check watchdog timer
systemctl status casa-log-daemon-watchdog.timer
```

### Check Logs

```bash
# Daemon log
tail -f /data/dsa110-contimg/state/logs/casa_log_daemon_$(date +%Y%m%d).log

# Health check log
tail -f /data/dsa110-contimg/state/logs/casa_log_daemon_health_$(date +%Y%m%d).log

# Systemd journal
journalctl -u casa-log-daemon-inotify.service -f
```

### Check File Accumulation

```bash
# Count files waiting to be moved
find /data/dsa110-contimg -type f -name "casa-*.log" -not -path "*/state/logs/*" | wc -l

# List files waiting
find /data/dsa110-contimg -type f -name "casa-*.log" -not -path "*/state/logs/*"
```

## Automatic Recovery

The system automatically recovers from:

1. **Process Crash**: Systemd restarts service automatically
2. **Service Failure**: Watchdog detects and restarts
3. **Stale Daemon**: Health check detects stale log file and triggers restart
4. **File Accumulation**: Periodic cleanup handles missed files

## Alerting (Optional)

You can add alerting by monitoring the status file:

```bash
# Example: Alert if unhealthy
if ! /data/dsa110-contimg/scripts/casa_log_daemon_health_check.sh; then
    # Send alert (email, Slack, etc.)
    echo "CASA Log Daemon is unhealthy!" | mail -s "Alert" admin@example.com
fi
```

Or add to monitoring system (Prometheus, Nagios, etc.) by reading the JSON status file.

## Maintenance

### Manual Restart

```bash
sudo systemctl restart casa-log-daemon-inotify.service
```

### Disable Watchdog (if needed)

```bash
sudo systemctl stop casa-log-daemon-watchdog.timer
sudo systemctl disable casa-log-daemon-watchdog.timer
```

### View Health Check History

```bash
# View health check log
cat /data/dsa110-contimg/state/logs/casa_log_daemon_health_*.log

# Count failures
grep "FAILED" /data/dsa110-contimg/state/logs/casa_log_daemon_health_*.log | wc -l
```

## Troubleshooting

### Daemon Not Starting

1. Check service status: `systemctl status casa-log-daemon-inotify.service`
2. Check logs: `journalctl -u casa-log-daemon-inotify.service -n 50`
3. Check health: `/data/dsa110-contimg/scripts/casa_log_daemon_health_check.sh`
4. Check permissions: Ensure `/data/dsa110-contimg/state/logs` is writable

### Files Accumulating

1. Check if daemon is running: `pgrep -f casa_log_daemon_inotify`
2. Check for errors in log: `tail -50 /data/dsa110-contimg/state/logs/casa_log_daemon_*.log`
3. Manually trigger cleanup: The periodic cleanup will catch them within 5 minutes
4. Check disk space: `df -h /data/dsa110-contimg/state/logs`

### Watchdog Not Working

1. Check timer status: `systemctl status casa-log-daemon-watchdog.timer`
2. Check when it last ran: `systemctl list-timers casa-log-daemon-watchdog.timer`
3. Manually trigger: `systemctl start casa-log-daemon-watchdog.service`

## Status File Format

```json
{
  "timestamp": "2025-11-08T22:56:00-08:00",
  "healthy": true,
  "issues": [],
  "file_count": 2,
  "daemon_running": true,
  "target_directory": "/data/dsa110-contimg/state/logs",
  "source_root": "/data/dsa110-contimg"
}
```

## Best Practices

1. **Monitor the status file** regularly (via cron or monitoring system)
2. **Review health check logs** weekly for patterns
3. **Set up alerts** if health check fails
4. **Keep logs** for at least 30 days for troubleshooting
5. **Test recovery** periodically by stopping the service and verifying it restarts

