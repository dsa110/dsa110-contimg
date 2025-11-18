#!/bin/bash
#
# organize_casa_logs.sh
#
# This script finds all CASA log files (casa-*.log) in the project root
# directory and moves them to the designated log directory.
# This helps keep the root directory clean.

set -e

# The root directory of the project
ROOT_DIR="/data/dsa110-contimg"
# The designated directory for all logs
LOG_DIR="$ROOT_DIR/state/logs"

# Ensure the log directory exists
mkdir -p "$LOG_DIR"

echo "Searching for CASA logs in $ROOT_DIR..."

# Find and move the log files.
# The -maxdepth 1 ensures we only search the root and not subdirectories.
# The find command will exit with an error if no files are found,
# so we add || true to prevent the script from exiting if there are no logs to move.
find "$ROOT_DIR" -maxdepth 1 -name "casa-*.log" -print0 | while IFS= read -r -d $'\0' file; do
  echo "Moving $(basename "$file") to $LOG_DIR/"
  mv "$file" "$LOG_DIR/"
done

echo "CASA log organization complete."
