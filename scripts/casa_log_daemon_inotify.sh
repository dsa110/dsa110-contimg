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
    
    # Check if file exists
    if [[ ! -f "$file_path" ]]; then
        return 0
    fi
    
    local rel_path="${file_path#$SOURCE_ROOT/}"
    
    # Skip files already in state/logs/
    if [[ "$rel_path" == state/logs/* ]]; then
        return 0
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
    
    # Wait briefly to ensure file is fully written (only if file is very new)
    local file_age=$(($(date +%s) - $(stat -c %Y "$file_path" 2>/dev/null || echo 0)))
    if [[ $file_age -lt 2 ]]; then
        sleep 0.5
    fi
    
    # Check if file still exists
    if [[ ! -f "$file_path" ]]; then
        return 0
    fi
    
    # Move the file with better error handling
    if mv "$file_path" "$target_path" 2>/dev/null; then
        log "INFO: Moved $file_path -> $target_path"
        return 0
    else
        # Try again with error output to diagnose
        local err_msg=$(mv "$file_path" "$target_path" 2>&1)
        log "ERROR: Failed to move $file_path: $err_msg"
        return 1
    fi
}

# Global variables
INOTIFY_PID=""
PERIODIC_PID=""

# Signal handler
cleanup() {
    log "Received signal, shutting down..."
    if [[ -n "$PERIODIC_PID" ]]; then
        kill "$PERIODIC_PID" 2>/dev/null
        wait "$PERIODIC_PID" 2>/dev/null
    fi
    if [[ -n "$INOTIFY_PID" ]]; then
        kill "$INOTIFY_PID" 2>/dev/null
        wait "$INOTIFY_PID" 2>/dev/null
    fi
    rm -f "$LOCK_FILE"
    exit 0
}

trap cleanup SIGTERM SIGINT

log "Starting CASA Log Daemon (inotifywait)..."
log "Monitoring: $SOURCE_ROOT (recursive)"
log "Target: $TARGET_ROOT"

# Lock file to prevent multiple cleanup processes
LOCK_FILE="${TARGET_ROOT}/.casa_log_cleanup.lock"

# Function to process existing files
process_existing_files() {
    # Use lock file to prevent concurrent cleanup
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_age=$(($(date +%s) - $(stat -c %Y "$LOCK_FILE" 2>/dev/null || echo 0)))
        # If lock is older than 10 minutes, remove it (stale lock)
        if [[ $lock_age -gt 600 ]]; then
            rm -f "$LOCK_FILE"
        else
            return 0
        fi
    fi
    
    touch "$LOCK_FILE"
    trap "rm -f '$LOCK_FILE'" EXIT
    
    local count=0
    local moved=0
    
    # Use find with -print0 and read -d '' to handle filenames with spaces
    while IFS= read -r -d '' file_path; do
        count=$((count + 1))
        if move_file "$file_path"; then
            moved=$((moved + 1))
        fi
    done < <(find "$SOURCE_ROOT" -type f -name "casa-*.log" -not -path "$TARGET_ROOT/*" -print0 2>/dev/null)
    
    log "Processed $count existing casa log files, moved $moved"
    rm -f "$LOCK_FILE"
    trap - EXIT
}

# Function to check if directory is ready for inotifywait
check_directory_ready() {
    local dir="$1"
    local max_attempts=10
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if [[ -d "$dir" ]] && [[ -r "$dir" ]]; then
            # Test if we can actually watch it
            if timeout 1 inotifywait -e create "$dir" --quiet 2>/dev/null; then
                return 0
            fi
        fi
        sleep 0.5
        attempt=$((attempt + 1))
    done
    return 1
}

# Function to start inotifywait with retry logic
start_inotifywait() {
    local max_attempts=5
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        # Ensure directory is ready
        if ! check_directory_ready "$SOURCE_ROOT"; then
            log "WARNING: Directory not ready for inotifywait, attempt $((attempt + 1))/$max_attempts"
            sleep 2
            attempt=$((attempt + 1))
            continue
        fi
        
        # Try to start inotifywait
        log "Starting inotifywait (attempt $((attempt + 1))/$max_attempts)..."
        
        # Test if inotifywait can start (non-blocking test)
        if timeout 2 inotifywait -m -r -e create,moved_to \
            --format '%w%f' \
            --exclude "^$TARGET_ROOT" \
            "$SOURCE_ROOT" >/dev/null 2>&1 &
        then
            # Give it a moment to start and check if it's still running
            sleep 1
            local test_pid=$!
            if kill -0 $test_pid 2>/dev/null; then
                kill $test_pid 2>/dev/null
                log "inotifywait test successful, starting monitoring..."
                return 0
            fi
        fi
        
        log "WARNING: inotifywait test failed, retrying..."
        attempt=$((attempt + 1))
        sleep 2
    done
    
    log "ERROR: Failed to start inotifywait after $max_attempts attempts, falling back to periodic cleanup only"
    return 1
}

# More aggressive periodic cleanup function
# Runs every 5 minutes, or more frequently if files are accumulating
periodic_cleanup() {
    local interval=300  # Start with 5 minutes
    local short_interval=60  # Use 1 minute if files are accumulating
    
    while true; do
        sleep "$interval"
        
        # Check how many files exist anywhere (recursively, excluding target directory)
        local file_count=$(find "$SOURCE_ROOT" -type f -name "casa-*.log" -not -path "$TARGET_ROOT/*" 2>/dev/null | wc -l)
        
        if [[ $file_count -gt 0 ]]; then
            log "Running periodic cleanup: found $file_count casa log files (anywhere in $SOURCE_ROOT)"
            process_existing_files
            
            # If files are accumulating, use shorter interval
            if [[ $file_count -gt 5 ]]; then
                interval=$short_interval
                log "Files accumulating, switching to aggressive cleanup (every $interval seconds)"
            else
                interval=300  # Back to 5 minutes
            fi
        else
            # No files, can use longer interval
            interval=300
        fi
    done
}

# Process existing files FIRST (blocking) to ensure clean state
log "Processing existing casa-*.log files..."
process_existing_files

# Start periodic cleanup in background (more aggressive)
log "Starting periodic cleanup daemon (every 5 minutes, or 1 minute if files accumulate)..."
periodic_cleanup &
PERIODIC_PID=$!

# Wait a moment for periodic cleanup to start
sleep 1

# Now start inotifywait for real-time monitoring
if start_inotifywait; then
    log "Starting inotifywait monitoring loop..."
    # Monitor inotifywait output
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
else
    # Fallback: if inotifywait fails, rely entirely on periodic cleanup
    log "Running in fallback mode: periodic cleanup only (every 60 seconds)"
    # Update interval to be more aggressive in fallback mode
    pkill -P $PERIODIC_PID 2>/dev/null || true
    sleep 1
    
    # Restart with more aggressive interval
    (
        while true; do
            sleep 60
            process_existing_files
        done
    ) &
    PERIODIC_PID=$!
    
    # Keep script running
    wait $PERIODIC_PID
fi

