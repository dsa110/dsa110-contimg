#!/usr/bin/env bash
# End-to-end bandpass calibration runner (QA -> auto-fields -> K/BA/BP/G)
#
# Usage:
#   bash scripts/calibrate_bandpass.sh \
#       --ms /path/to.ms \
#       [--catalog /data/dsa110-contimg/data-samples/catalogs/vlacalibrators.txt] \
#       [--min-pb 0.99] [--window 3] [--radius 2.0] [--combine] [--no-flagging] \
#       [--qa-dir /tmp/qa-auto]
#
# Notes:
#  - Runs CASA tasks in a separate process for stability vs. notebooks.
#  - Uses QA fast plots to generate refant_ranking.json, which the calibrate CLI consumes.
#  - Selects a contiguous FIELD window by PB gain threshold (min_pb); falls back to fixed --window.

set -euo pipefail

MS=""
CATALOG="/data/dsa110-contimg/data-samples/catalogs/vlacalibrators.txt"
# Defaults so you don't need to pass flags
MIN_PB="0.99"           # PB gain threshold (relative to peak)
WINDOW="3"              # Fallback fixed window if threshold not used downstream
RADIUS="2.0"            # Calibrator catalog search radius (deg)
COMBINE=true            # Combine across selected fields for BP/G (single solution)
DO_FLAGGING=false       # Flagging disabled by default (set --flagging to enable)
QA_DIR="/tmp/qa-auto"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ms) MS="$2"; shift 2;;
    --catalog) CATALOG="$2"; shift 2;;
    --min-pb) MIN_PB="$2"; shift 2;;
    --window) WINDOW="$2"; shift 2;;
    --radius) RADIUS="$2"; shift 2;;
    --combine) COMBINE=true; shift 1;;
    --no-combine) COMBINE=false; shift 1;;
    --no-flagging) DO_FLAGGING=false; shift 1;;
    --flagging) DO_FLAGGING=true; shift 1;;
    --qa-dir) QA_DIR="$2"; shift 2;;
    -h|--help)
      sed -n '1,80p' "$0"; exit 0;;
    *) echo "Unknown arg: $1" >&2; exit 1;;
  esac
done

if [[ -z "$MS" ]]; then
  echo "--ms is required" >&2; exit 2
fi
if [[ ! -d "$MS" ]]; then
  echo "MS not found: $MS" >&2; exit 3
fi
mkdir -p "$QA_DIR"

# Environment hygiene for CASA stability
export OMP_NUM_THREADS="1"
export OPENBLAS_NUM_THREADS="1"
export MKL_NUM_THREADS="1"
export NUMEXPR_NUM_THREADS="1"
export HDF5_USE_FILE_LOCKING="FALSE"
export CASALOGFILE="${QA_DIR}/casalog_calibrate.log"

# Resolve repo src for PYTHONPATH
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
export PYTHONPATH="${REPO_ROOT}/src:${PYTHONPATH:-}"

PY="/opt/miniforge/envs/casa6/bin/python"

echo "[1/3] Fast QA to rank refant -> $QA_DIR"
"$PY" -m dsa110_contimg.qa.fast_plots --ms "$MS" --output-dir "$QA_DIR" >/dev/null || true
if [[ ! -s "$QA_DIR/refant_ranking.json" ]]; then
  echo "refant_ranking.json not found; QA step may have failed" >&2
  exit 4
fi
echo "✓ refant_ranking.json ready"

echo "[2/3] Calibrate with auto fields (PB-threshold) and auto refant"
CAL_ARGS=(
  -m dsa110_contimg.calibration.cli calibrate
  --ms "$MS"
  --auto-fields
  --cal-catalog "$CATALOG"
  --cal-search-radius-deg "$RADIUS"
  --bp-window "$WINDOW"
  --refant-ranking "$QA_DIR/refant_ranking.json"
)
## Always provide PB threshold by default
CAL_ARGS+=( --bp-min-pb "$MIN_PB" )

## Combine fields by default unless --no-combine supplied
if [[ "$COMBINE" == true ]]; then
  CAL_ARGS+=( --bp-combine-field )
fi

## Flagging off by default; add switch to disable the CLI's default flagging
if [[ "$DO_FLAGGING" != true ]]; then
  CAL_ARGS+=( --no-flagging )
fi

set -x
"$PY" "${CAL_ARGS[@]}"
set +x

echo "[3/3] Done. CASA log: $CASALOGFILE"
