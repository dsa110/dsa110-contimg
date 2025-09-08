#!/usr/bin/env bash
# Configure CASA logging to keep the repo root clean.

# Absolute project root
DSA_CONTIMG_ROOT="/data/jfaber/dsa110-contimg"

# Ensure logs directory exists
CASA_LOG_DIR="$DSA_CONTIMG_ROOT/logs/casa"
mkdir -p "$CASA_LOG_DIR" 2>/dev/null || true

# If not already defined in this shell, set per-session logfile
if [[ -z "$CASA_LOGFILE" ]]; then
  ts=$(date +%Y%m%d_%H%M%S)
  export CASA_LOGFILE="$CASA_LOG_DIR/casa_${ts}_$$.log"
fi

# Optional log level knob for tools that honor it
export CASA_LOG_LEVEL="INFO"

# One-time notice per shell
if [[ -z "$__CASA_LOG_NOTICE_SHOWN" ]]; then
  echo "[casa-log] Logging to $CASA_LOGFILE"
  export __CASA_LOG_NOTICE_SHOWN=1
fi

return 0 2>/dev/null || true


