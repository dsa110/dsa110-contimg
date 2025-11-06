#!/bin/bash
# CASA Log Daemon using inotifywait - Pure bash version (lowest CPU/memory)
# Monitors all subdirectories recursively with minimal resource usage

SOURCE_ROOT="${1:-/data/dsa110-contimg}"
TARGET_ROOT="${2:-/data/dsa110-contimg/state/logs}"
LOG_FILE="${TARGET_ROOT}/casa_log_daemon_$(date +%Y%m%d).log"

# Ensure target directory exists
mkdir -p "$TARGET_ROOT"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Function to move a casa log file
move_file() {
    local file_path="$1"
    local rel_path="${file_path#$SOURCE_ROOT/}"
    
    # Skip files already in state/logs/
    if [[ "$rel_path" == state/logs/* ]]; then
        return
    fi
    
    local filename=$(basename "$file_path")
    local target_path="$TARGET_ROOT/$filename"
    
    # Handle filename collisions
    if [[ -f "$target_path" ]]; then
        local timestamp=$(date +%Y%m%d-%H%M%S)
        local stem="${filename%.*}"
        local ext="${filename##*.}"
        target_path="$TARGET_ROOT/${stem}_${timestamp}.${ext}"
    fi
    
    # Wait briefly to ensure file is fully written
    sleep 0.5
    
    # Check if file still exists
    if [[ ! -f "$file_path" ]]; then
        log "WARNING: File no longer exists: $file_path"
        return
    fi
    
    # Move the file
    if mv "$file_path" "$target_path" 2>/dev/null; then
        log "INFO: Moved $file_path -> $target_path"
    else
        log "ERROR: Failed to move $file_path"
    fi
}

# Global variable for inotifywait PID
INOTIFY_PID=""

# Signal handler
cleanup() {
    log "Received signal, shutting down..."
    if [[ -n "$INOTIFY_PID" ]]; then
        kill "$INOTIFY_PID" 2>/dev/null
        wait "$INOTIFY_PID" 2>/dev/null
    fi
    exit 0
}

trap cleanup SIGTERM SIGINT

log "Starting CASA Log Daemon (inotifywait)..."
log "Monitoring: $SOURCE_ROOT (recursive)"
log "Target: $TARGET_ROOT"

# Process existing files in background (non-blocking) - start this first
log "Checking for existing casa-*.log files in background..."
(
    find "$SOURCE_ROOT" -type f -name "casa-*.log" -not -path "$TARGET_ROOT/*" | while read -r file_path; do
        move_file "$file_path"
    done
    log "Finished processing existing casa log files"
) &

# Start inotifywait IMMEDIATELY to catch new files
# -m: monitor (continuous)
# -r: recursive
# -e create,moved_to: only file creation and moves
# --format: output full path
# --exclude: exclude target directory
log "Starting inotifywait to monitor for new files..."
inotifywait -m -r -e create,moved_to \
    --format '%w%f' \
    --exclude "^$TARGET_ROOT" \
    "$SOURCE_ROOT" 2>>"$LOG_FILE" | while IFS= read -r file_path; do
    
    # Check if it's a casa-*.log file
    if [[ "$(basename "$file_path")" =~ ^casa-.*\.log$ ]]; then
        log "Detected casa log file: $file_path"
        move_file "$file_path"
    fi
done

# Note: inotifywait PID is in the pipe, cleanup handler will work via process group

