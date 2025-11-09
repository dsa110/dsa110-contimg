# CASA Log Daemon Fixes - November 2025

## Problem Summary

Two issues were identified:
1. **casa-*.log files** accumulating in various directories throughout `/data/dsa110-contimg/` (including root and subdirectories) instead of being moved to the centralized `/data/dsa110-contimg/state/logs/` directory
2. **TMPPOINTING* directories** created by CASA/casacore accumulating in root directory without cleanup

## Root Causes

### Casa Log Files
- The daemon's background process for moving existing files only ran once at startup
- If files were created after startup but before inotifywait was ready, they were missed
- No periodic cleanup to catch missed files
- inotifywait had timing issues starting up

### TMPPOINTING Directories
- No cleanup service existed for these temporary directories
- They accumulated indefinitely in the root directory

## Solutions Implemented

### 1. Enhanced Casa Log Daemon (`scripts/casa_log_daemon_inotify.sh`)

#### Improvements:
- **Improved startup sequence**: Process existing files FIRST (blocking) before starting monitoring
- **Recursive monitoring**: Monitors ALL subdirectories recursively, not just root directory
- **inotifywait retry logic**: Added `check_directory_ready()` and retry mechanism (5 attempts)
- **Periodic cleanup**: Runs every 5 minutes, or 1 minute if files accumulate (>5 files) - checks ALL directories recursively
- **Adaptive intervals**: Automatically adjusts cleanup frequency based on file count across entire directory tree
- **Fallback mechanism**: If inotifywait fails, falls back to periodic cleanup only (60-second intervals)
- **Better error handling**: Improved `move_file()` function with better diagnostics
- **Lock mechanism**: Prevents concurrent cleanup processes

#### Key Features:
- Processes existing files at startup (blocking)
- Starts periodic cleanup daemon (adaptive intervals)
- Starts inotifywait for real-time monitoring (with retry)
- Falls back to periodic-only mode if inotifywait fails

### 2. TMPPOINTING Cleanup (`ops/pipeline/housekeeping.py`)

#### New Function:
- `cleanup_tmppointing_dirs()`: Removes old TMPPOINTING* directories from root directory
- Integrated into main housekeeping script
- Uses same age threshold as other temp cleanup (default: 24 hours)
- Added `--root-dir` argument for flexibility

## Testing Results

### Casa Log Daemon:
- ✅ Successfully processed 247 existing files on restart
- ✅ inotifywait started successfully ("Watches established")
- ✅ Real-time monitoring working (test file detected and moved within seconds)
- ✅ Periodic cleanup daemon running (adaptive intervals)

### TMPPOINTING Cleanup:
- ✅ Function tested and working correctly
- ✅ Integrated into housekeeping script
- ✅ Ready for regular execution via cron/systemd timer

## Usage

### Casa Log Daemon
The daemon runs automatically via systemd service or manually:
```bash
/bin/bash /data/dsa110-contimg/scripts/casa_log_daemon_inotify.sh
```

### TMPPOINTING Cleanup
Run via housekeeping script:
```bash
/opt/miniforge/envs/casa6/bin/python ops/pipeline/housekeeping.py --temp-age 3600 --root-dir /data/dsa110-contimg
```

Or as part of regular housekeeping (default age: 24 hours):
```bash
/opt/miniforge/envs/casa6/bin/python ops/pipeline/housekeeping.py
```

## Monitoring

### Log Files
- Daemon log: `/data/dsa110-contimg/state/logs/casa_log_daemon_YYYYMMDD.log`
- Check for "Detected", "Moved", "ERROR" messages

### Process Status
```bash
ps aux | grep casa_log_daemon_inotify
```

### File Count (All Directories)
```bash
find /data/dsa110-contimg -type f -name "casa-*.log" -not -path "*/state/logs/*" | wc -l
```

## Maintenance

### Restart Daemon
If running via systemd:
```bash
sudo systemctl restart casa-log-daemon-inotify.service
```

If running manually:
```bash
pkill -f casa_log_daemon_inotify
nohup /bin/bash /data/dsa110-contimg/scripts/casa_log_daemon_inotify.sh > /dev/null 2>&1 &
```

### Clean Up Existing Files
The daemon will automatically process existing files on startup. To manually trigger:
```bash
# The daemon processes files automatically, but you can also use:
find /data/dsa110-contimg -type f -name "casa-*.log" -not -path "*/state/logs/*" -exec mv {} /data/dsa110-contimg/state/logs/ \;
```

## Files Modified

1. `scripts/casa_log_daemon_inotify.sh` - Enhanced with retry logic, periodic cleanup, fallback mechanism
2. `ops/pipeline/housekeeping.py` - Added TMPPOINTING cleanup function

## Status

✅ **FIXED** - Both issues resolved and tested
✅ **OPERATIONAL** - Daemon running with new strategy
✅ **MONITORED** - Logs and processes verified working

