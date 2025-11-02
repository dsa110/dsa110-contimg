# CASA Log Management Scripts

This directory contains scripts for managing casa-*.log files in the dsa110-contimg project.

## Files

- **`casa_log_daemon.py`** - Python daemon that continuously monitors for new casa-*.log files and automatically moves them to the state directory
- **`move_casa_logs.sh`** - Bash script for one-time bulk moves of existing casa-*.log files
- **`cleanup_casa_logs.sh`** - Bash script for cleaning up old casa-*.log files (with optional retention period)
- **`casa-log-daemon.service`** - Systemd service file for running the daemon as a system service
- **`casa-log-cleanup.service`** - Systemd service file for cleaning up old logs
- **`casa-log-cleanup.timer`** - Systemd timer file for automatic cleanup every 6 hours

## Usage

### Automatic Cleanup (Recommended)

The cleanup runs automatically every 6 hours via systemd timer, keeping only logs from the last 6 hours:

```bash
# Install and enable the timer
sudo cp scripts/casa-log-cleanup.service /etc/systemd/system/
sudo cp scripts/casa-log-cleanup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable casa-log-cleanup.timer
sudo systemctl start casa-log-cleanup.timer

# Check timer status
sudo systemctl status casa-log-cleanup.timer

# View recent cleanup runs
sudo journalctl -u casa-log-cleanup.service -n 20
```

### Manual Cleanup

You can run the cleanup script manually:

```bash
# Delete all casa-*.log files
./scripts/cleanup_casa_logs.sh

# Keep logs from last 24 hours, delete older ones
./scripts/cleanup_casa_logs.sh --keep-hours 24

# Preview what would be deleted (dry run)
./scripts/cleanup_casa_logs.sh --keep-hours 6 --dry-run
```

### Continuous Monitoring (Legacy - Not Needed with Code Changes)

The daemon runs automatically as a system service and monitors `/data/dsa110-contimg/` for new casa-*.log files.

**Service Management:**
```bash
# Check status
sudo systemctl status casa-log-daemon

# Start/stop/restart
sudo systemctl start casa-log-daemon
sudo systemctl stop casa-log-daemon
sudo systemctl restart casa-log-daemon

# View logs
sudo journalctl -u casa-log-daemon -f
```

**Manual Daemon:**
```bash
# Run in foreground
python3 casa_log_daemon.py

# Run as daemon (background)
python3 casa_log_daemon.py --daemon

# Custom source/target directories
python3 casa_log_daemon.py --source /path/to/source --target /path/to/target
```

### One-time Bulk Move

For moving existing casa-*.log files:

```bash
# Preview what would be moved (dry run)
./move_casa_logs.sh --dry-run

# Actually move the files
./move_casa_logs.sh
```

## How It Works

1. **Log Redirection**: CASA log files are automatically written to `/data/dsa110-contimg/state/logs/` via code changes in `job_runner.py` (no CPU overhead)
2. **Automatic Cleanup**: Systemd timer runs cleanup every 6 hours, keeping only logs from the last 6 hours
3. **Manual Cleanup**: The cleanup script can be run manually with custom retention periods

## Requirements

- Python 3.6+
- `watchdog` library (for daemon, optional: `pip install watchdog`)
- Systemd (for service and timer management)

## Installation

1. Install the watchdog library (if using daemon):
   ```bash
   pip install watchdog
   ```

2. Install automatic cleanup timer:
   ```bash
   sudo cp scripts/casa-log-cleanup.service /etc/systemd/system/
   sudo cp scripts/casa-log-cleanup.timer /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable casa-log-cleanup.timer
   sudo systemctl start casa-log-cleanup.timer
   ```

3. Install daemon (optional, for legacy compatibility):
   ```bash
   sudo cp scripts/casa-log-daemon.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable casa-log-daemon
   sudo systemctl start casa-log-daemon
   ```

## Logs

- **CASA logs**: `/data/dsa110-contimg/state/logs/casa-*.log` (automatically cleaned every 6 hours)
- **Daemon logs**: `/data/dsa110-contimg/state/logs/casa_log_daemon_YYYYMMDD.log` (if daemon is running)
- **Cleanup logs**: `sudo journalctl -u casa-log-cleanup.service`
- **System logs**: `sudo journalctl -u casa-log-daemon` (if daemon is running)
