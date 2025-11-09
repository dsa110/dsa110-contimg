# CASA Log Daemon Protection Summary

## What's Been Set Up

You now have **multiple layers of protection** to prevent the casa log daemon from failing silently:

### 1. **Systemd Service Protection** ✓
- **Auto-restart**: Service automatically restarts if it crashes
- **Start limits**: Prevents restart loops (max 5 restarts in 5 minutes)
- **Watchdog timeout**: 600 seconds - if service doesn't respond, systemd restarts it
- **Enabled on boot**: Service starts automatically on system reboot

### 2. **Health Check Script** ✓
- **Location**: `scripts/casa_log_daemon_health_check.sh`
- **Checks**:
  - Daemon process is running
  - Systemd service is active
  - Log file is recent (updated in last 10 minutes)
  - Files aren't accumulating excessively (>10 files threshold)
  - Target directory is accessible
- **Status file**: Creates JSON status at `state/logs/.casa_log_daemon_status.json`

### 3. **Watchdog Timer** ✓
- **Runs**: Every 5 minutes
- **Action**: Runs health check, automatically restarts daemon if unhealthy
- **Installation**: Use setup script (see below)

### 4. **Enhanced Logging** ✓
- **Log files**: `state/logs/casa-log-daemon.out` and `.err`
- **Health check logs**: `state/logs/casa_log_daemon_health_YYYYMMDD.log`
- **Daemon logs**: `state/logs/casa_log_daemon_YYYYMMDD.log`

## Quick Setup

To enable all protection features:

```bash
cd /data/dsa110-contimg
sudo bash scripts/setup_casa_log_daemon_monitoring.sh
```

This will:
1. Install systemd service files
2. Enable watchdog timer
3. Restart services with new configuration
4. Run initial health check

## What You Don't Need to Do

With this setup, you **don't need to**:
- ✓ Manually check if daemon is running
- ✓ Manually restart the daemon if it crashes
- ✓ Worry about files accumulating (periodic cleanup handles it)
- ✓ Monitor logs constantly (watchdog does it for you)
- ✓ Set up cron jobs (systemd timer handles it)

## What Happens Automatically

1. **If daemon crashes**: Systemd restarts it within 10 seconds
2. **If daemon becomes unresponsive**: Watchdog detects and restarts it
3. **If files accumulate**: Periodic cleanup moves them (every 5 min, or 1 min if >5 files)
4. **If health check fails**: Watchdog timer restarts the service
5. **On system reboot**: Service starts automatically

## Monitoring (Optional)

If you want to monitor the system:

```bash
# Check health status
cat /data/dsa110-contimg/state/logs/.casa_log_daemon_status.json | jq .

# Check service status
systemctl status casa-log-daemon-inotify.service

# Check watchdog timer
systemctl status casa-log-daemon-watchdog.timer

# View recent health checks
tail -20 /data/dsa110-contimg/state/logs/casa_log_daemon_health_*.log
```

## Alerting (Optional)

You can add alerting by creating a cron job or monitoring script:

```bash
# Example: Check health every hour and alert if unhealthy
0 * * * * /data/dsa110-contimg/scripts/casa_log_daemon_health_check.sh || echo "Alert: CASA Log Daemon unhealthy" | mail -s "Alert" admin@example.com
```

Or integrate with your monitoring system (Prometheus, Nagios, etc.) by reading the JSON status file.

## Files Created

- `scripts/casa_log_daemon_health_check.sh` - Health check script
- `scripts/casa-log-daemon-watchdog.service` - Watchdog service
- `scripts/casa-log-daemon-watchdog.timer` - Watchdog timer
- `scripts/setup_casa_log_daemon_monitoring.sh` - Setup script
- `docs/operations/CASA_LOG_DAEMON_MONITORING.md` - Full documentation

## Current Status

The daemon is currently running and protected. To enable the watchdog timer:

```bash
sudo bash /data/dsa110-contimg/scripts/setup_casa_log_daemon_monitoring.sh
```

After running this, the system will be fully protected and self-healing.

