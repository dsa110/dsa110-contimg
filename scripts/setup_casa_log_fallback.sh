#!/bin/bash
# Comprehensive solution: Create a symlink/catch-all approach
# Since CASA writes logs to CWD, we'll create a symlink that redirects casa-*.log files

LOG_DIR="/data/dsa110-contimg/state/logs"
SOURCE_DIR="/data/dsa110-contimg"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Create a script that runs in the background to move any new logs
# This is a fallback for any processes we can't control

cat > /tmp/cleanup_casa_logs_loop.sh << 'SCRIPT'
#!/bin/bash
LOG_DIR="/data/dsa110-contimg/state/logs"
SOURCE_DIR="/data/dsa110-contimg"

while true; do
    # Move any casa-*.log files from root to logs directory
    find "$SOURCE_DIR" -maxdepth 1 -type f -name "casa-*.log" -exec mv {} "$LOG_DIR/" \; 2>/dev/null
    
    # Sleep for 30 seconds
    sleep 30
done
SCRIPT

chmod +x /tmp/cleanup_casa_logs_loop.sh

echo "Background cleanup script created at /tmp/cleanup_casa_logs_loop.sh"
echo "To run it: nohup /tmp/cleanup_casa_logs_loop.sh &"

