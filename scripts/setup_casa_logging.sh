#!/bin/bash
"""
Setup CASA logging environment.

This script sets up environment variables to force CASA to use the casalogs directory.
It should be sourced before running any CASA operations.
"""

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CASALOGS_DIR="$SCRIPT_DIR/casalogs"

# Ensure casalogs directory exists
mkdir -p "$CASALOGS_DIR"

# Set CASA environment variables
export CASA_LOG_DIR="$CASALOGS_DIR"
export CASA_LOG_FILE="$CASALOGS_DIR/casa.log"

# Set CASA configuration directory
export CASA_CONFIG_DIR="$SCRIPT_DIR/.casa"
mkdir -p "$CASA_CONFIG_DIR"

# Create CASA configuration file
cat > "$CASA_CONFIG_DIR/rc" << EOF
# CASA configuration for DSA-110 pipeline
# Log directory: $CASALOGS_DIR
logfile = '$CASALOGS_DIR/casa.log'
logdir = '$CASALOGS_DIR'
EOF

echo "CASA logging environment set up:"
echo "  Log directory: $CASALOGS_DIR"
echo "  Config file: $CASA_CONFIG_DIR/rc"
echo "  Environment variables exported"

# Function to run CASA with proper logging
run_casa() {
    echo "Running CASA with logging to: $CASALOGS_DIR"
    "$@"
}

# Function to run Python scripts with CASA logging
run_python_casa() {
    echo "Running Python script with CASA logging to: $CASALOGS_DIR"
    python "$@"
}
