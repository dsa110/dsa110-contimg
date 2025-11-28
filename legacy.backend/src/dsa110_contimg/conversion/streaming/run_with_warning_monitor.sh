#!/bin/bash
#
# Wrapper script to run a Python script with deterministic warning monitoring.
# Captures stdout/stderr in real-time and terminates immediately if warnings are detected.
#
# Usage:
#   ./run_with_warning_monitor.sh <script.py> [script_args...]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${LOG_FILE:-run_with_monitor.log}"

# Warning patterns (case-insensitive matching)
WARNING_PATTERNS=(
    # Logging levels
    "warning" "WARNING" "warn" "WARN"
    "error" "ERROR" "SEVERE" "FATAL" "fatal"
    
    # Fallback/compromise patterns
    "fallback" "falling back" "using default" "defaulting to"
    
    # Failure patterns
    "failed" "failure" "cannot" "can't" "unable to" "abort" "aborting"
    
    # Exception patterns
    "exception" "Exception" "traceback" "Traceback"
    "RuntimeError" "ValueError" "KeyError" "FileNotFoundError" "PermissionError"
    
    # File system issues
    "permission denied" "no such file" "no space left" "disk full" "read-only"
    
    # Database issues
    "database is locked" "sqlite error" "connection failed"
    
    # Calibration-specific
    "calibration failed" "no valid data" "insufficient data" "calibrator not found" "no calibrator"
    
    # CASA task failures
    "task failed" "Task failed" "cannot proceed"
    
    # Resource issues
    "MemoryError" "out of memory" "timeout" "Timeout"
    
    # Configuration issues
    "missing required" "invalid configuration" "not configured" "not found"
)

# Patterns to ignore (not actual warnings)
IGNORE_PATTERNS=(
    "debug" "info" "completed" "success"
    "logging error"  # Common Python logging handler issue, usually non-critical
    "could not extract" "will use fallback" "using filename timestamp"  # Time extraction fallbacks are non-critical
    "erfawarning" "dubious year" "erfa function"  # ERFA library warnings about astronomical time calculations are non-critical
    "phase center separation" "time-dependent phasing" "meridian-tracking" "expected and correct"  # Phase center incoherence is EXPECTED for time-dependent phasing
)

# Check if script provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <script.py> [script_args...]" >&2
    exit 1
fi

SCRIPT="$1"
shift
SCRIPT_ARGS=("$@")

# Check if script is a module path (contains dots) or a file path
IS_MODULE=false
if [[ "$SCRIPT" == *"."* ]] && [[ "$SCRIPT" != *"/"* ]]; then
    IS_MODULE=true
    MODULE_NAME="$SCRIPT"
elif [[ "$SCRIPT" == *".py" ]] && [ -f "$SCRIPT" ]; then
    IS_MODULE=false
    SCRIPT_PATH="$SCRIPT"
elif [[ "$SCRIPT" != /* ]]; then
    SCRIPT_PATH="$SCRIPT_DIR/$SCRIPT"
    if [ ! -f "$SCRIPT_PATH" ]; then
        echo "Error: Script not found: $SCRIPT" >&2
        exit 1
    fi
else
    SCRIPT_PATH="$SCRIPT"
    if [ ! -f "$SCRIPT_PATH" ]; then
        echo "Error: Script not found: $SCRIPT" >&2
        exit 1
    fi
fi

# Use Python from casa6 environment if available
if command -v conda &> /dev/null; then
    PYTHON=$(conda run -n casa6 which python3 2>/dev/null || which python3)
else
    PYTHON=$(which python3)
fi

# Set PYTHONPATH to include the project root
PROJECT_ROOT="/data/dsa110-contimg/src"
export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

if [ "$IS_MODULE" = true ]; then
    echo "Running: $PYTHON -m $MODULE_NAME ${SCRIPT_ARGS[*]}"
else
    echo "Running: $PYTHON $SCRIPT_PATH ${SCRIPT_ARGS[*]}"
fi
echo "Log file: $LOG_FILE"
echo "================================================================================"
echo ""

# Create log file
> "$LOG_FILE"

# Function to check if line contains warning
check_warning() {
    local line="$1"
    local line_lower="${line,,}"  # Convert to lowercase
    
    # Check ignore patterns first
    for ignore in "${IGNORE_PATTERNS[@]}"; do
        if [[ "$line_lower" == *"$ignore"* ]]; then
            return 1  # Not a warning
        fi
    done
    
    # Check warning patterns
    for pattern in "${WARNING_PATTERNS[@]}"; do
        if [[ "$line_lower" == *"${pattern,,}"* ]]; then
            # Special handling for "error" - ignore "no error" or "without error"
            if [[ "${pattern,,}" == "error" ]]; then
                if [[ "$line_lower" == *"no error"* ]] || [[ "$line_lower" == *"without error"* ]]; then
                    continue
                fi
            fi
            return 0  # Warning detected
        fi
    done
    
    return 1  # Not a warning
}

# Run script and monitor output
# Use a temp file to communicate warning status from subshell
WARNING_FILE=$(mktemp)
trap "rm -f $WARNING_FILE" EXIT

# Use stdbuf to ensure line buffering for real-time monitoring
if command -v stdbuf &> /dev/null; then
    STDBUF="stdbuf -oL -eL"
else
    STDBUF=""
fi

# Use Python unbuffered mode for immediate output
PYTHON_FLAGS="-u"

# Create a named pipe for monitoring
FIFO=$(mktemp -u)
mkfifo "$FIFO"
trap "rm -f $FIFO" EXIT

# Start Python process in background, redirecting output through FIFO
if [ "$IS_MODULE" = true ]; then
    $STDBUF "$PYTHON" $PYTHON_FLAGS -m "$MODULE_NAME" "${SCRIPT_ARGS[@]}" > "$FIFO" 2>&1 &
else
    $STDBUF "$PYTHON" $PYTHON_FLAGS "$SCRIPT_PATH" "${SCRIPT_ARGS[@]}" > "$FIFO" 2>&1 &
fi
PYTHON_PID=$!

# Function to cleanup and exit
cleanup_and_exit() {
    local exit_code=$1
    kill "$PYTHON_PID" 2>/dev/null || true
    pkill -P "$PYTHON_PID" 2>/dev/null || true
    sleep 0.5
    kill -9 "$PYTHON_PID" 2>/dev/null || true
    pkill -9 -P "$PYTHON_PID" 2>/dev/null || true
    exit "$exit_code"
}

# Monitor output from FIFO and write to both log file and stdout with immediate flushing
# Use stdbuf with tee to ensure line-buffered writes for immediate output
while IFS= read -r line < "$FIFO"; do
    # Write to log file and stdout simultaneously with immediate flush
    # tee handles buffering better than separate echo commands
    if command -v stdbuf &> /dev/null; then
        printf '%s\n' "$line" | stdbuf -oL tee -a "$LOG_FILE"
    else
        printf '%s\n' "$line" | tee -a "$LOG_FILE"
    fi
    
    # Check for warnings
    if check_warning "$line"; then
        echo "$line" > "$WARNING_FILE"
        echo "" >&2
        echo "================================================================================" >&2
        echo "WARNING DETECTED: $line" >&2
        echo "================================================================================" >&2
        cleanup_and_exit 1
    fi
done

# Wait for Python process
wait "$PYTHON_PID" 2>/dev/null
EXIT_CODE=$?
WARNING_DETECTED=false
WARNING_LINE=""

if [ -s "$WARNING_FILE" ]; then
    WARNING_DETECTED=true
    WARNING_LINE=$(cat "$WARNING_FILE")
fi

if [ "$EXIT_CODE" -ne 0 ] || [ "$WARNING_DETECTED" = true ]; then
    echo "" >&2
    echo "================================================================================" >&2
    echo "PROCESS STOPPED DUE TO WARNING DETECTION" >&2
    if [ -n "$WARNING_LINE" ]; then
        echo "Warning line: $WARNING_LINE" >&2
    fi
    echo "Full log: $LOG_FILE" >&2
    echo "================================================================================" >&2
    exit 1
fi

echo "" >&2
echo "================================================================================" >&2
echo "PROCESS COMPLETED SUCCESSFULLY" >&2
echo "Exit code: $EXIT_CODE" >&2
echo "Full log: $LOG_FILE" >&2
echo "================================================================================" >&2

exit "$EXIT_CODE"

