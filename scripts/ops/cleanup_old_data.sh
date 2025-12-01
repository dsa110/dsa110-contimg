#!/usr/bin/env bash
#
# Data retention cleanup (scaffold)
# - Finds old HDF5/MS/image artifacts and removes them (dry-run by default)
# - Logs all actions to stdout and a log file
#
# Configuration (env overrides):
#   DRY_RUN=true|false                # Default: true (no deletion)
#   LOG_FILE=/data/dsa110-contimg/state/logs/cleanup_old_data.log
#   PRODUCTS_DB=/data/dsa110-contimg/state/db/products.sqlite3
#   HDF5_ROOT=/data/incoming
#   MS_SCIENCE_ROOT=/data/dsa110-contimg/ms/science
#   MS_CAL_ROOT=/data/dsa110-contimg/ms/calibrators
#   MS_FAILED_ROOT=/data/dsa110-contimg/ms/failed
#   IMAGES_ROOT=/data/dsa110-contimg/images
#   RETENTION_HDF5_DAYS=30
#   RETENTION_MS_SCIENCE_DAYS=30
#   RETENTION_MS_CALIBRATOR_DAYS=90
#   RETENTION_FAILED_DAYS=7
#   RETENTION_IMAGES_DAYS=180
#
# Usage:
#   DRY_RUN=false ./scripts/ops/cleanup_old_data.sh
#   ./scripts/ops/cleanup_old_data.sh --help
#
set -euo pipefail

DRY_RUN=${DRY_RUN:-true}
LOG_FILE=${LOG_FILE:-/data/dsa110-contimg/state/logs/cleanup_old_data.log}
PRODUCTS_DB=${PRODUCTS_DB:-/data/dsa110-contimg/state/db/products.sqlite3}

HDF5_ROOT=${HDF5_ROOT:-/data/incoming}
MS_SCIENCE_ROOT=${MS_SCIENCE_ROOT:-/data/dsa110-contimg/ms/science}
MS_CAL_ROOT=${MS_CAL_ROOT:-/data/dsa110-contimg/ms/calibrators}
MS_FAILED_ROOT=${MS_FAILED_ROOT:-/data/dsa110-contimg/ms/failed}
IMAGES_ROOT=${IMAGES_ROOT:-/data/dsa110-contimg/images}

RETENTION_HDF5_DAYS=${RETENTION_HDF5_DAYS:-30}
RETENTION_MS_SCIENCE_DAYS=${RETENTION_MS_SCIENCE_DAYS:-30}
RETENTION_MS_CALIBRATOR_DAYS=${RETENTION_MS_CALIBRATOR_DAYS:-90}
RETENTION_FAILED_DAYS=${RETENTION_FAILED_DAYS:-7}
RETENTION_IMAGES_DAYS=${RETENTION_IMAGES_DAYS:-180}

usage() {
  cat <<'EOF'
Data retention cleanup
  Finds old artifacts and removes them (dry-run by default).

Options:
  --help        Show this help
  --no-dry-run  Disable dry-run (same as DRY_RUN=false)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --no-dry-run)
      DRY_RUN=false
      shift
      ;;
    *)
      echo "Unknown option: $1" >&2
      exit 1
      ;;
  esac
done

mkdir -p "$(dirname "$LOG_FILE")"

log() {
  local level="$1"; shift
  local msg="$*"
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')
  echo "[$ts] [$level] $msg" | tee -a "$LOG_FILE"
}

safe_delete() {
  local path="$1"
  local base="$2"

  if [[ ! -e "$path" ]]; then
    log "WARN" "Path missing, skipping: $path"
    return
  fi

  # Ensure target is within base (defensive)
  local resolved_base resolved_path
  resolved_base=$(readlink -f "$base" || echo "$base")
  resolved_path=$(readlink -f "$path" || echo "$path")

  if [[ "$resolved_path" != "$resolved_base"* ]]; then
    log "ERROR" "Refusing to delete outside base (path=$resolved_path base=$resolved_base)"
    return
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    log "DRY-RUN" "Would remove: $resolved_path"
  else
    rm -rf "$resolved_path"
    log "INFO" "Removed: $resolved_path"
  fi
}

cleanup_bucket() {
  local label="$1"
  local base="$2"
  local days="$3"
  local find_expr=("${@:4}")

  if [[ ! -d "$base" ]]; then
    log "INFO" "Skip $label (missing $base)"
    return
  fi

  log "INFO" "Scanning $label in $base (older than ${days}d)"

  mapfile -t candidates < <(find "$base" "${find_expr[@]}" -mtime "+$days" -print 2>/dev/null | sort)

  if [[ "${#candidates[@]}" -eq 0 ]]; then
    log "INFO" "No candidates for $label"
    return
  fi

  for path in "${candidates[@]}"; do
    safe_delete "$path" "$base"
  done
}

main() {
  log "INFO" "Starting cleanup (DRY_RUN=$DRY_RUN)"
  log "INFO" "Products DB (for future audit hooks): $PRODUCTS_DB"

  cleanup_bucket "hdf5" "$HDF5_ROOT" "$RETENTION_HDF5_DAYS" -type f -name "*.hdf5"
  cleanup_bucket "science-ms" "$MS_SCIENCE_ROOT" "$RETENTION_MS_SCIENCE_DAYS" -type d -name "*.ms"
  cleanup_bucket "calibrator-ms" "$MS_CAL_ROOT" "$RETENTION_MS_CALIBRATOR_DAYS" -type d -name "*.ms"
  cleanup_bucket "failed-ms" "$MS_FAILED_ROOT" "$RETENTION_FAILED_DAYS" -type d -name "*.ms"
  cleanup_bucket "images" "$IMAGES_ROOT" "$RETENTION_IMAGES_DAYS" -type f \( -name "*.fits" -o -name "*.img" \)

  log "INFO" "Cleanup complete"
}

main "$@"
