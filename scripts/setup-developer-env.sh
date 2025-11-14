#!/bin/bash
# Setup script for developer environment
# Automatically configures shell to prevent common mistakes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect shell
SHELL_NAME=$(basename "$SHELL")
SHELL_RC=""

case "$SHELL_NAME" in
    bash)
        if [ -f "$HOME/.bashrc" ]; then
            SHELL_RC="$HOME/.bashrc"
        elif [ -f "$HOME/.bash_profile" ]; then
            SHELL_RC="$HOME/.bash_profile"
        fi
        ;;
    zsh)
        if [ -f "$HOME/.zshrc" ]; then
            SHELL_RC="$HOME/.zshrc"
        fi
        ;;
    *)
        echo "Warning: Unsupported shell: $SHELL_NAME" >&2
        echo "Please manually add the configuration to your shell RC file." >&2
        exit 1
        ;;
esac

if [ -z "$SHELL_RC" ]; then
    echo "ERROR: Could not find shell RC file for $SHELL_NAME" >&2
    exit 1
fi

# Check if already configured
if grep -q "DSA110_CONTIMG_DEV_ENV" "$SHELL_RC" 2>/dev/null; then
    echo "Developer environment already configured in $SHELL_RC"
    echo "To reconfigure, remove the DSA110_CONTIMG_DEV_ENV section and run again."
    exit 0
fi

# Create configuration block
CONFIG_BLOCK="# DSA110_CONTIMG_DEV_ENV - Auto-configured by setup-developer-env.sh
# This section prevents common developer mistakes
# Generated: $(date)

# Auto-source error detection for agentic sessions
if [ -f \"$PROJECT_ROOT/scripts/agent-setup.sh\" ]; then
    source \"$PROJECT_ROOT/scripts/agent-setup.sh\"
fi

# Python wrapper - redirects python/python3 to casa6
if [ -f \"$PROJECT_ROOT/scripts/python-wrapper.sh\" ]; then
    # Create aliases that use the wrapper
    alias python=\"$PROJECT_ROOT/scripts/python-wrapper.sh\"
    alias python3=\"$PROJECT_ROOT/scripts/python-wrapper.sh\"
    
    # Warn if someone tries to use system python directly
    _system_python_warning() {
        echo \"WARNING: You're using system Python. This project requires casa6.\" >&2
        echo \"Use: /opt/miniforge/envs/casa6/bin/python\" >&2
        echo \"Or the 'python' alias (which uses casa6 automatically)\" >&2
    }
    
    # Override PATH to prefer wrapper (if in project directory)
    if [[ \"\$PWD\" == \"$PROJECT_ROOT\"* ]]; then
        export PATH=\"$PROJECT_ROOT/scripts:\$PATH\"
    fi
fi

# Pytest wrapper - prevents 2>&1 errors
if [ -f \"$PROJECT_ROOT/scripts/pytest-safe.sh\" ]; then
    alias pytest=\"$PROJECT_ROOT/scripts/pytest-safe.sh\"
    # Also create python -m pytest alias
    _pytest_wrapper() {
        if [[ \"\$*\" == *\"2>&1\"* ]] && [[ \"\$*\" != *\"|\"* ]]; then
            echo \"WARNING: Detected 2>&1 in pytest command. Using safe wrapper.\" >&2
            \"$PROJECT_ROOT/scripts/pytest-safe.sh\" \"\$@\"
        else
            \"$PROJECT_ROOT/scripts/pytest-safe.sh\" \"\$@\"
        fi
    }
fi

# Prevent common command output suppression mistakes
_prevent_output_suppression() {
    local cmd=\"\$1\"
    shift
    local args=(\"\$@\")
    
    # Check for problematic patterns
    for arg in \"\${args[@]}\"; do
        if [[ \"\$arg\" == \"2>/dev/null\" ]] || [[ \"\$arg\" == \">/dev/null\" ]] || [[ \"\$arg\" == \"&>/dev/null\" ]]; then
            echo \"WARNING: Detected output suppression (\$arg) in command.\" >&2
            echo \"This project requires full output for error detection.\" >&2
            echo \"If you really need to suppress output, use explicit --quiet flags.\" >&2
            # Don't block, just warn
        fi
    done
}

# End DSA110_CONTIMG_DEV_ENV"

# Append to shell RC
echo "" >> "$SHELL_RC"
echo "$CONFIG_BLOCK" >> "$SHELL_RC"

echo "✓ Developer environment configured in $SHELL_RC"
echo ""
echo "To activate, run:"
echo "  source $SHELL_RC"
echo ""
echo "Or restart your terminal."

