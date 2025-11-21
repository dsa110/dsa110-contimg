# CASA Log Organization System

**Date:** 2025-11-17  
**Type:** Operations Guide  
**Status:** ✅ Active

---

## Overview

The CASA log organization system automatically monitors the entire
`/data/dsa110-contimg/` directory tree for CASA log files and instantly moves
them to a centralized location. This keeps the project directory clean and
organized.

## Problem Solved

CASA creates log files (named `casa-YYYYMMDD-HHMMSS.log`) in the current working
directory where a CASA process is launched. This can result in:

- Log files scattered across multiple directories
- Cluttered project root directory
- Difficulty finding and managing logs
- Over 135,000+ log files accumulated in various locations

## Solution Architecture

### Simple Design

The system uses a single bash script with `inotifywait` (from the
`inotify-tools` package) to monitor filesystem events in real-time.

**Key Features:**

1. **Recursive Monitoring** - Watches all subdirectories
2. **Instant Action** - Moves files immediately upon detection
3. **Selective Exclusion** - Avoids monitoring the destination directory
4. **Pattern Matching** - Only acts on `casa-*.log` files
5. **No Daemon Required** - Runs as simple background process

### Architecture Diagram

```
/data/dsa110-contimg/
├── src/                    ← Monitored
├── scripts/                ← Monitored
├── docs/                   ← Monitored
├── [any directory]/        ← Monitored
│
└── state/logs/             ← DESTINATION (excluded from monitoring)
    └── [all casa-*.log files moved here]
```

## Implementation

### Script Location

`/data/dsa110-contimg/scripts/watch_and_organize_logs.sh`

### How It Works

```bash
#!/bin/bash
# Simplified pseudocode

SOURCE_DIR="/data/dsa110-contimg"
LOG_DIR="$SOURCE_DIR/state/logs"

# 1. Initial cleanup: Move existing logs
find "$SOURCE_DIR" -name "casa-*.log" | while read file; do
  mv "$file" "$LOG_DIR/"
done

# 2. Start recursive monitoring
inotifywait -m -r --exclude "$LOG_DIR" "$SOURCE_DIR" | \
while read filepath; do
  if [[ "$filepath" == casa-*.log ]]; then
    mv "$filepath" "$LOG_DIR/"
  fi
done
```

### Technical Details

**Command:**

```bash
inotifywait -m -r -e create -e moved_to \
  --format '%w%f' \
  --exclude "$LOG_DIR" \
  "$SOURCE_DIR"
```

**Flags:**

- `-m` - Monitor mode (continuous operation)
- `-r` - Recursive (watch all subdirectories)
- `-e create` - Watch for file creation events
- `-e moved_to` - Watch for files moved into directories
- `--exclude` - Exclude destination directory (prevents infinite loops)
- `--format '%w%f'` - Output full file path

**Events Monitored:**

- File creation (`create`) - New files written directly
- File move (`moved_to`) - Files moved from other locations

## Usage

### Starting the Service

```bash
cd /data/dsa110-contimg

# Start in background with logging
nohup ./scripts/watch_and_organize_logs.sh > /tmp/log_watcher.log 2>&1 &

# Save process ID
echo $! > /tmp/log_watcher.pid
```

### Monitoring Activity

```bash
# View real-time log activity
tail -f /tmp/log_watcher.log

# Check process status
ps -fp $(cat /tmp/log_watcher.pid)

# Check if inotifywait is running
ps aux | grep inotifywait
```

### Stopping the Service

```bash
# Kill using saved PID
kill $(cat /tmp/log_watcher.pid)

# Or kill by name
pkill -f 'watch_and_organize_logs.sh'
```

### Restarting the Service

```bash
cd /data/dsa110-contimg

# Stop existing process
pkill -f 'watch_and_organize_logs.sh' || true

# Clear old logs (optional)
rm -f /tmp/log_watcher.log

# Start fresh
nohup ./scripts/watch_and_organize_logs.sh > /tmp/log_watcher.log 2>&1 &
echo $! > /tmp/log_watcher.pid
```

## Log Output Format

The activity log (`/tmp/log_watcher.log`) shows:

```
Running initial cleanup of existing CASA logs...
Moving existing log 'casa-20251117-115653.log' to /data/dsa110-contimg/state/logs/
Initial cleanup complete.
Starting CASA log watcher and organizer...
  Watching: /data/dsa110-contimg (recursively) for new 'casa-*.log' files
  Excluding: /data/dsa110-contimg/state/logs (destination directory)
  Moving new logs to: /data/dsa110-contimg/state/logs
Setting up watches.  Beware: since -r was given, this may take a while!
Watches established.
2025-11-17 04:03:35: Detected new log 'casa-20251117-120335.log' at '/data/dsa110-contimg/casa-20251117-120335.log'. Moving to /data/dsa110-contimg/state/logs/
2025-11-17 04:03:46: Detected new log 'casa-test-in-src-1763381026.log' at '/data/dsa110-contimg/src/casa-test-in-src-1763381026.log'. Moving to /data/dsa110-contimg/state/logs/
```

Each move event includes:

- Timestamp
- Filename
- Full source path
- Destination directory

## Verification & Testing

### Test the System

```bash
# Create test file in random location
mkdir -p /data/dsa110-contimg/test/nested/dir
touch /data/dsa110-contimg/test/nested/dir/casa-test-$(date +%s).log

# Wait 2 seconds
sleep 2

# Verify file was moved
ls /data/dsa110-contimg/test/nested/dir/casa-*.log  # Should be empty
ls /data/dsa110-contimg/state/logs/casa-test-*.log  # Should show file

# Check log
tail -2 /tmp/log_watcher.log  # Should show the move event
```

### Verify Complete Coverage

The system monitors:

- ✅ Root directory: `/data/dsa110-contimg/casa-*.log`
- ✅ Source code: `/data/dsa110-contimg/src/casa-*.log`
- ✅ Scripts: `/data/dsa110-contimg/scripts/casa-*.log`
- ✅ Documentation: `/data/dsa110-contimg/docs/casa-*.log`
- ✅ Deeply nested: `/data/dsa110-contimg/any/deep/path/casa-*.log`

The system excludes:

- ❌ Destination: `/data/dsa110-contimg/state/logs/` (prevents loops)

## Performance Characteristics

### Resource Usage

- **CPU**: < 1% during idle, brief spike during directory tree scan on startup
- **Memory**: ~5-10 MB for inotifywait process
- **Disk I/O**: Minimal (only during file moves)

### Startup Time

The recursive watch setup can take 10-30 seconds on large directory trees. The
message "Setting up watches. Beware: since -r was given, this may take a while!"
is normal and expected.

### Scalability

Successfully handles:

- 135,000+ existing log files (moved during initial cleanup)
- Thousands of subdirectories
- Real-time monitoring with sub-second response

## Troubleshooting

### Process Not Running

**Check:**

```bash
ps -fp $(cat /tmp/log_watcher.pid 2>/dev/null) || echo "Not running"
```

**Solution:**

```bash
cd /data/dsa110-contimg
nohup ./scripts/watch_and_organize_logs.sh > /tmp/log_watcher.log 2>&1 &
echo $! > /tmp/log_watcher.pid
```

### Files Not Being Moved

**Check log for errors:**

```bash
tail -20 /tmp/log_watcher.log
```

**Common issues:**

1. Process died during startup - Check log for error messages
2. Destination directory doesn't exist - Script creates it automatically
3. Permission issues - Ensure script has write access to destination

### "Watches established" Never Appears

This means the recursive directory scan is still in progress. Wait longer or
check if the process is stuck:

```bash
ps aux | grep inotifywait
# Look for high CPU usage on the inotifywait process
```

### Old inotifywait Version

If you see error: `unrecognized option '--exclude'`

The script is designed to be compatible with older versions. Check that you're
running the latest version of the script.

## Comparison to Legacy System

### Old System (Archived)

- Multiple Python daemons (`casa_log_daemon.py`, `casa_log_daemon_inotify.py`)
- Health check scripts running periodically
- Complex setup and monitoring infrastructure
- Required daemon management
- Separate monitoring setup scripts

**Archived in:** `/data/dsa110-contimg/archive/legacy/casa_log_monitoring/`

### New System (Current)

- Single bash script
- No health checks needed (fails fast, easy to restart)
- Simple: one command to start, one to stop
- No daemon management overhead
- Self-contained with initial cleanup

**Benefits:**

- ✅ **Simpler** - 50 lines of bash vs 100+ lines of Python
- ✅ **More reliable** - Fewer moving parts
- ✅ **Easier to debug** - All activity logged to one file
- ✅ **Easier to maintain** - Standard Linux tools (`inotifywait`)
- ✅ **Better coverage** - Recursive monitoring of entire tree

## Production Deployment

### Systemd Service (Optional)

For production, consider creating a systemd service:

```ini
[Unit]
Description=CASA Log Organization Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/data/dsa110-contimg
ExecStart=/data/dsa110-contimg/scripts/watch_and_organize_logs.sh
Restart=always
RestartSec=10
StandardOutput=append:/tmp/log_watcher.log
StandardError=append:/tmp/log_watcher.log

[Install]
WantedBy=multi-user.target
```

Save as: `/etc/systemd/system/casa-log-watcher.service`

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable casa-log-watcher
sudo systemctl start casa-log-watcher
sudo systemctl status casa-log-watcher
```

### Cron Job (Alternative)

Or use a cron job to ensure it's always running:

```bash
# Add to crontab (crontab -e)
*/5 * * * * pgrep -f watch_and_organize_logs.sh > /dev/null || (cd /data/dsa110-contimg && nohup ./scripts/watch_and_organize_logs.sh > /tmp/log_watcher.log 2>&1 & echo $! > /tmp/log_watcher.pid)
```

This checks every 5 minutes and restarts if not running.

## Related Documentation

- **Legacy System:**
  `/data/dsa110-contimg/archive/legacy/casa_log_monitoring/README.md`
- **Directory Architecture:**
  `/data/dsa110-contimg/docs/concepts/DIRECTORY_ARCHITECTURE.md`
- **Script Source:** `/data/dsa110-contimg/scripts/watch_and_organize_logs.sh`

## Maintenance

### Regular Checks

**Weekly:**

- Verify process is running
- Check log file size: `ls -lh /tmp/log_watcher.log`
- Spot-check that CASA logs are being moved

**Monthly:**

- Review activity log for any anomalies
- Check destination directory size: `du -sh /data/dsa110-contimg/state/logs/`
- Consider archiving or compressing old CASA logs

### Log Rotation

The activity log (`/tmp/log_watcher.log`) can grow over time. Consider rotating
it:

```bash
# Manual rotation
pkill -f watch_and_organize_logs.sh
mv /tmp/log_watcher.log /tmp/log_watcher.log.$(date +%Y%m%d)
gzip /tmp/log_watcher.log.$(date +%Y%m%d)
cd /data/dsa110-contimg && nohup ./scripts/watch_and_organize_logs.sh > /tmp/log_watcher.log 2>&1 &
echo $! > /tmp/log_watcher.pid
```

## Future Enhancements

Potential improvements:

1. **Automatic archiving** - Compress CASA logs older than 30 days
2. **Size limits** - Automatically purge logs when directory exceeds threshold
3. **Statistics** - Track number of files moved per day
4. **Alerts** - Notify if process dies or stops moving files
5. **Web dashboard** - Real-time view of log organization activity

## Support

For issues or questions:

1. Check the activity log: `tail -f /tmp/log_watcher.log`
2. Verify process status: `ps aux | grep inotifywait`
3. Review this documentation
4. Check legacy system docs in archive if migrating

---

**Last Updated:** 2025-11-17  
**Script Version:** 1.0  
**Status:** Production Ready ✅
