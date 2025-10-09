# CASA Log Management Scripts

This directory contains scripts for managing casa-*.log files in the dsa110-contimg project.

## Files

- **`casa_log_daemon.py`** - Python daemon that continuously monitors for new casa-*.log files and automatically moves them to the state directory
- **`move_casa_logs.sh`** - Bash script for one-time bulk moves of existing casa-*.log files
- **`casa-log-daemon.service`** - Systemd service file for running the daemon as a system service

## Usage

### Continuous Monitoring (Recommended)

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

1. **File Detection**: The daemon uses the `watchdog` library to monitor file system events
2. **Automatic Movement**: When a casa-*.log file is created or moved into the monitored directory, it's automatically moved to `/data/dsa110-contimg/state/`
3. **Path Preservation**: The original directory structure is preserved (e.g., `src/casa-*.log` → `state/src/casa-*.log`)
4. **Logging**: All operations are logged to `/data/dsa110-contimg/state/logs/`

## Requirements

- Python 3.6+
- `watchdog` library (`pip install watchdog`)
- Systemd (for service management)

## Installation

1. Install the watchdog library:
   ```bash
   pip install watchdog
   ```

2. Copy the service file to systemd:
   ```bash
   sudo cp casa-log-daemon.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable casa-log-daemon
   sudo systemctl start casa-log-daemon
   ```

## Logs

- **Daemon logs**: `/data/dsa110-contimg/state/logs/casa_log_daemon_YYYYMMDD.log`
- **System logs**: `sudo journalctl -u casa-log-daemon`
