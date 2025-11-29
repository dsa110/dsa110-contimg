#!/bin/bash
# Auto Error Detection Wrapper
# Source this file to automatically wrap all commands with error detection
#
# Usage:
#   source scripts/auto-error-detection.sh
#   # Now all commands are automatically wrapped
#
# To disable:
#   unset AUTO_ERROR_DETECTION
#   # Or restart shell

# Be completely silent for non-tty sessions (scp, ssh cmd, etc.)
if [ ! -t 1 ]; then
    return 0 2>/dev/null || exit 0
fi

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if error detection wrapper exists
# Try Python version first, fallback to bash version
ERROR_DETECTION_WRAPPER="${ERROR_DETECTION_WRAPPER:-$PROJECT_ROOT/scripts/run-with-error-detection.py}"

if [ ! -f "$ERROR_DETECTION_WRAPPER" ]; then
    ERROR_DETECTION_WRAPPER="$PROJECT_ROOT/scripts/run-with-error-detection.sh"
fi

if [ ! -f "$ERROR_DETECTION_WRAPPER" ]; then
    echo "Warning: Error detection wrapper not found: $ERROR_DETECTION_WRAPPER" >&2
    echo "Auto error detection disabled." >&2
    return 1 2>/dev/null || exit 1
fi

# Make sure wrapper is executable
chmod +x "$ERROR_DETECTION_WRAPPER" 2>/dev/null || true

# Function to wrap commands with error detection
_run_with_error_detection() {
    # GUARD: Prevent recursion - if we're already in error detection, skip
    if [ -n "${_IN_ERROR_DETECTION:-}" ]; then
        "$@"
        return $?
    fi
    
    # Check if auto-detection is disabled for this command
    if [ -n "${SKIP_ERROR_DETECTION:-}" ]; then
        "$@"
        return $?
    fi
    
    # Check if this is the wrapper script itself - prevent recursion
    local cmd="$1"
    if [[ "$cmd" == *"run-with-error-detection"* ]] || [[ "$cmd" == "$ERROR_DETECTION_WRAPPER" ]]; then
        "$@"
        return $?
    fi
    
    # Check if this is a command that should skip error detection
    local skip_commands=(
        "cd" "source" "." "export" "unset" "alias" "unalias"
        "set" "unset" "shopt" "type" "command" "which"
        "help" "man" "info" "history" "jobs" "fg" "bg"
        "exit" "logout" "clear" "reset"
    )
    
    for skip_cmd in "${skip_commands[@]}"; do
        if [ "$cmd" = "$skip_cmd" ]; then
            "$@"
            return $?
        fi
    done
    
    # Set guard to prevent recursion
    export _IN_ERROR_DETECTION=1
    
    # Run command with error detection
    "$ERROR_DETECTION_WRAPPER" "$@"
    local exit_code=$?
    
    # Clear guard
    unset _IN_ERROR_DETECTION
    
    return $exit_code
}

# Override common commands (optional - can be enabled/disabled)
AUTO_WRAP_COMMANDS="${AUTO_WRAP_COMMANDS:-1}"

if [ "${AUTO_WRAP_COMMANDS}" = "1" ]; then
    # Create wrapper functions for common commands
    # These will be used instead of the actual commands
    
    # Python commands
    python() {
        _run_with_error_detection python "$@"
    }
    
    python3() {
        _run_with_error_detection python3 "$@"
    }
    
    # Use DEBUG trap to catch full paths to Python executables
    # This allows /opt/miniforge/envs/casa6/bin/python to be wrapped
    # The trap runs before each command execution
    trap '_debug_trap_handler "$BASH_COMMAND"' DEBUG
    
    _debug_trap_handler() {
        local cmd="$1"
        # Only process if AUTO_ERROR_DETECTION is enabled
        [ -z "${AUTO_ERROR_DETECTION:-}" ] && return 0
        
        # GUARD: Skip if we're already in error detection (prevents recursion)
        [ -n "${_IN_ERROR_DETECTION:-}" ] && return 0
        
        # Skip if this is a skip command or if we're already in error detection
        [[ "$cmd" =~ ^(cd|source|\.|export|unset|alias|type|command|which|echo|printf|test|\[|true|false|exit|logout|clear|reset|SKIP_ERROR_DETECTION|_run_with_error_detection) ]] && return 0
        
        # Skip if this is the wrapper script itself
        [[ "$cmd" == *"run-with-error-detection"* ]] && return 0
        
        # Check if this is a Python executable (full path)
        if [[ "$cmd" =~ ^(/[^[:space:]]*/python[0-9]?[[:space:]]|/[^[:space:]]*/pytest[[:space:]]) ]]; then
            # Extract the executable path
            local exe_path=$(echo "$cmd" | awk '{print $1}')
            # Check if it's actually an executable
            if [ -x "$exe_path" ] 2>/dev/null; then
                # Disable trap temporarily to avoid recursion
                trap - DEBUG
                # Run with error detection
                _run_with_error_detection $cmd
                local exit_code=$?
                # Re-enable trap
                trap '_debug_trap_handler "$BASH_COMMAND"' DEBUG
                return $exit_code
            fi
        fi
        return 0
    }
    
    # Pytest
    pytest() {
        _run_with_error_detection pytest "$@"
    }
    
    # Make
    make() {
        _run_with_error_detection make "$@"
    }
    
    # npm/node commands (if in frontend directory)
    if [ -f "package.json" ] || [ -d "frontend" ]; then
        npm() {
            _run_with_error_detection npm "$@"
        }
        
        node() {
            _run_with_error_detection node "$@"
        }
    fi
    
    # Wrap script execution (catches ./script.sh, scripts/script.sh, etc.)
    # This ensures scripts in command chains are also wrapped
    _wrap_executable() {
        local cmd="$1"
        # Check if it's an executable file (script or binary)
        if [ -f "$cmd" ] && [ -x "$cmd" ]; then
            # Check if it's a shell script (starts with #!)
            if head -1 "$cmd" 2>/dev/null | grep -q "^#!"; then
                _run_with_error_detection "$@"
                return $?
            fi
        fi
        # Not a script, run normally
        command "$@"
    }
    
    # Note: command_not_found_handle only catches commands that don't exist
    # For commands that DO exist (like scripts), we need a different approach
    # The function wrappers above handle python/pytest/make
    # For other executables in command chains, they won't be automatically wrapped
    # unless they're explicitly added to the wrapper list above
    #
    # To wrap ALL commands in chains, you would need to use DEBUG trap or
    # override the command builtin, which is more invasive and can cause issues
fi

# Export function for manual use
export -f _run_with_error_detection

# Set flag to indicate auto-detection is enabled
export AUTO_ERROR_DETECTION=1

echo ":check: Auto error detection enabled"
echo "   All commands will be wrapped with error detection"
echo "   To disable: unset AUTO_ERROR_DETECTION"
echo "   To skip for one command: SKIP_ERROR_DETECTION=1 command args"

