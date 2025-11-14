#!/bin/bash
# Command Wrapper - Automatically wraps commands with error detection
# This can be used as a command_not_found_handle or via PROMPT_COMMAND

# Check if error detection wrapper exists
ERROR_DETECTION_WRAPPER="${ERROR_DETECTION_WRAPPER:-scripts/run-with-error-detection.py}"

if [ ! -f "$ERROR_DETECTION_WRAPPER" ]; then
    # Fallback to bash version if Python version doesn't exist
    ERROR_DETECTION_WRAPPER="${ERROR_DETECTION_WRAPPER:-scripts/run-with-error-detection.sh}"
fi

# Function to check if command should skip error detection
should_skip_error_detection() {
    local cmd="$1"
    
    # Skip built-in shell commands
    local skip_commands=(
        "cd" "source" "." "export" "unset" "alias" "unalias"
        "set" "shopt" "type" "command" "which" "help" "man"
        "info" "history" "jobs" "fg" "bg" "exit" "logout"
        "clear" "reset" "echo" "printf" "test" "[" "true" "false"
        "read" "readonly" "declare" "local" "return"
    )
    
    for skip_cmd in "${skip_commands[@]}"; do
        if [ "$cmd" = "$skip_cmd" ]; then
            return 0  # Should skip
        fi
    done
    
    return 1  # Should not skip
}

# Main wrapper function
wrap_command() {
    # Check if auto-detection is disabled
    if [ -n "${SKIP_ERROR_DETECTION:-}" ] || [ -z "${AUTO_ERROR_DETECTION:-}" ]; then
        "$@"
        return $?
    fi
    
    # Check if command should skip
    if should_skip_error_detection "$1"; then
        "$@"
        return $?
    fi
    
    # Run with error detection
    if [ -f "$ERROR_DETECTION_WRAPPER" ]; then
        "$ERROR_DETECTION_WRAPPER" "$@"
    else
        # Fallback: run normally if wrapper doesn't exist
        "$@"
    fi
}

# Export for use in other scripts
export -f wrap_command should_skip_error_detection

