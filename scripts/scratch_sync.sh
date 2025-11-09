#!/usr/bin/env bash
# Simple helper for staging large data on the fast SSD (/scratch) and archiving to /data.
# Usage details are printed when called with no arguments or --help.

set -euo pipefail

SCRATCH_ROOT=${SCRATCH_ROOT:-/stage/dsa110-contimg}
DATA_ROOT=${DATA_ROOT:-/data}

usage() {
  cat <<'EOF'
Usage:
  scratch_sync.sh stage <relative/path> [--delete] [--dry-run]
  scratch_sync.sh archive <relative/path> [--delete] [--dry-run]
  scratch_sync.sh clean <relative/path> [--dry-run]
  scratch_sync.sh list
  scratch_sync.sh status

Commands:
  stage    Copy data from ${DATA_ROOT} into ${SCRATCH_ROOT}.
  archive  Copy data from ${SCRATCH_ROOT} back to ${DATA_ROOT}.
  clean    Remove a staged path from ${SCRATCH_ROOT} once archived.
  list     Show top-level contents of ${SCRATCH_ROOT}.
  status   Display disk usage for ${SCRATCH_ROOT} and the root filesystem.

Options:
  --delete   Mirror the target by deleting files that are absent from the source.
  --dry-run  Show the actions rsync/clean would take without making changes.

Environment overrides:
  SCRATCH_ROOT  Location to use for fast staging (default: /stage/dsa110-contimg).
  DATA_ROOT     Repository/data root on the large volume (default: /data).

Examples:
  # Stage a measurement set directory into scratch
  scripts/scratch_sync.sh stage products/ms_run_001

  # Sync results back to /data and prune files removed locally
  scripts/scratch_sync.sh archive products/ms_run_001 --delete

  # Remove the scratch copy once archived
  scripts/scratch_sync.sh clean products/ms_run_001
EOF
}

require_rsync() {
  if ! command -v rsync >/dev/null 2>&1; then
    echo "Error: rsync is required but not installed." >&2
    exit 1
  fi
}

resolve_paths() {
  local direction=$1
  local rel=$2

  case "$direction" in
    stage)
      SRC_PATH="${DATA_ROOT}/${rel}"
      DEST_PATH="${SCRATCH_ROOT}/${rel}"
      ;;
    archive)
      SRC_PATH="${SCRATCH_ROOT}/${rel}"
      DEST_PATH="${DATA_ROOT}/${rel}"
      ;;
    *)
      echo "Internal error: unknown direction '$direction'" >&2
      exit 1
      ;;
  esac
}

sync_paths() {
  local direction=$1
  local rel=$2
  local delete_flag=$3
  local dry_run=$4

  resolve_paths "$direction" "$rel"

  if [ ! -e "$SRC_PATH" ]; then
    echo "Error: source path does not exist: $SRC_PATH" >&2
    exit 1
  fi

  require_rsync

  local rsync_opts=("-aH" "--info=stats1,progress2" "--human-readable")
  if [ "$delete_flag" = "true" ]; then
    rsync_opts+=("--delete")
  fi
  if [ "$dry_run" = "true" ]; then
    rsync_opts+=("--dry-run")
  fi

  local src="$SRC_PATH"
  local dest="$DEST_PATH"

  if [ -d "$SRC_PATH" ]; then
    mkdir -p "$DEST_PATH"
    src="${SRC_PATH%/}/"
    dest="${DEST_PATH%/}/"
  else
    mkdir -p "$(dirname "$DEST_PATH")"
  fi

  echo "Running rsync from $src to $dest"
  rsync "${rsync_opts[@]}" "$src" "$dest"
}

clean_path() {
  local rel=$1
  local dry_run=$2
  local target="${SCRATCH_ROOT}/${rel}"

  if [ "$dry_run" = "true" ]; then
    echo "Would remove $target"
    return 0
  fi

  if [ ! -e "$target" ]; then
    echo "Nothing to remove: $target does not exist."
    return 0
  fi

  rm -rf -- "$target"
  echo "Removed $target"
}

list_paths() {
  if [ ! -d "$SCRATCH_ROOT" ]; then
    echo "Scratch directory $SCRATCH_ROOT does not exist yet."
    return 0
  fi
  ls -alh "$SCRATCH_ROOT"
}

show_status() {
  echo "Scratch usage (${SCRATCH_ROOT}):"
  if [ -d "$SCRATCH_ROOT" ]; then
    du -sh "$SCRATCH_ROOT"/* 2>/dev/null || echo "  (empty)"
  else
    echo "  Scratch directory not created."
  fi
  echo
  echo "Filesystem usage:"
  df -h "$SCRATCH_ROOT" "/" "$DATA_ROOT" 2>/dev/null | uniq
}

command=${1:-}
if [ -z "$command" ] || [ "$command" = "--help" ] || [ "$command" = "-h" ]; then
  usage
  exit 0
fi
shift

case "$command" in
  stage|archive)
    rel=${1:-}
    if [ -z "$rel" ]; then
      echo "Error: relative path required for $command." >&2
      echo >&2
      usage
      exit 1
    fi
    shift
    delete_flag=false
    dry_run=false
    for arg in "$@"; do
      case "$arg" in
        --delete) delete_flag=true ;;
        --dry-run) dry_run=true ;;
        *)
          echo "Unknown option: $arg" >&2
          usage
          exit 1
          ;;
      esac
    done
    sync_paths "$command" "$rel" "$delete_flag" "$dry_run"
    ;;
  clean)
    rel=${1:-}
    if [ -z "$rel" ]; then
      echo "Error: relative path required for clean." >&2
      usage
      exit 1
    fi
    shift
    dry_run=false
    for arg in "$@"; do
      case "$arg" in
        --dry-run) dry_run=true ;;
        *)
          echo "Unknown option: $arg" >&2
          usage
          exit 1
          ;;
      esac
    done
    clean_path "$rel" "$dry_run"
    ;;
  list)
    list_paths
    ;;
  status)
    show_status
    ;;
  *)
    echo "Unknown command: $command" >&2
    echo >&2
    usage
    exit 1
    ;;
esac
