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
MERGE_SPW=false         # Optional: combine all SPWs into one via mstransform

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
    --merge-spw) MERGE_SPW=true; shift 1;;
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

# Optional pre-step: merge all SPWs into a single SPW
if [[ "$MERGE_SPW" == true ]]; then
  echo "[0/3] Merging all SPWs into a single SPW (mstransform)"
  MS_MERGED="${MS%/.ms}_spw1.ms"
  # If the pattern above didn't match, fall back to appending suffix
  if [[ "$MS_MERGED" == "$MS" ]]; then
    MS_MERGED="${MS}_spw1.ms"
  fi
  # Run mstransform to combine SPWs and regrid to a contiguous band
  MS_IN="$MS" MS_OUT="$MS_MERGED" "$PY" - <<'PY'
import os, numpy as np
from casacore.tables import table
from casatasks import mstransform

ms_in = os.environ['MS_IN']
ms_out = os.environ['MS_OUT']

# Build global frequency grid
with table(ms_in+'::SPECTRAL_WINDOW') as spw:
    cf = np.asarray(spw.getcol('CHAN_FREQ'))  # shape (nspw, nchan)

all_freq = np.sort(cf.reshape(-1))
dnu = float(np.median(np.diff(all_freq)))
nchan = int(all_freq.size)
start = float(all_freq[0])

# Remove existing output if present
import shutil
if os.path.isdir(ms_out):
    shutil.rmtree(ms_out, ignore_errors=True)

mstransform(
    vis=ms_in,
    outputvis=ms_out,
    datacolumn='DATA',
    combinespws=True,
    regridms=True,
    mode='frequency',
    nchan=nchan,
    start=f'{start}Hz',
    width=f'{dnu}Hz',
    interpolation='linear',
    keepflags=True,
)
print(f"Merged SPWs -> {ms_out}")
PY
  if [[ -d "$MS_MERGED" ]]; then
    MS="$MS_MERGED"
    echo "Using merged MS: $MS"
  else
    echo "SPW merge failed; continuing with original MS" >&2
  fi
fi

echo "[1/3] Fast QA to rank refant -> $QA_DIR"
"$PY" -m dsa110_contimg.qa.fast_plots --ms "$MS" --output-dir "$QA_DIR" >/dev/null || true

# Reference antenna selection precedence:
# 1) CAL_REFANT env var (explicit override)
# 2) refant_ranking.json from QA
# 3) Fallback median antenna from MS baselines
REFANT_ARG=( )
if [[ -n "${CAL_REFANT:-}" ]]; then
  echo "Using CAL_REFANT override: ${CAL_REFANT}"
  REFANT_ARG=( --refant "${CAL_REFANT}" )
elif [[ ! -s "$QA_DIR/refant_ranking.json" ]]; then
  echo "QA ranking not available; selecting a fallback reference antenna from MS"
  # Fallback: choose a median antenna ID present in the MS baselines
  REFANT_FALLBACK=$(MS="$MS" "$PY" - <<'PY'
import os, numpy as np
from casacore.tables import table
ms = os.environ.get('MS')
try:
    with table(ms) as tb:
        a1 = tb.getcol('ANTENNA1')
        a2 = tb.getcol('ANTENNA2')
    ants = np.unique(np.concatenate([a1, a2]))
    if ants.size:
        print(int(np.median(ants)))
    else:
        print(0)
except Exception:
    print(0)
PY
)
  echo "Using fallback refant=${REFANT_FALLBACK}"
  REFANT_ARG=( --refant "$REFANT_FALLBACK" )
else
  echo "✓ refant_ranking.json ready"
fi

echo "[2/3] Calibrate with auto fields (PB-threshold) and auto refant"
CAL_ARGS=(
  -m dsa110_contimg.calibration.cli calibrate
  --ms "$MS"
  --field 0  # fallback if auto field selection fails
  --auto-fields
  --cal-catalog "$CATALOG"
  --cal-search-radius-deg "$RADIUS"
  --bp-window "$WINDOW"
)
if [[ -n "${CAL_REFANT:-}" ]]; then
  CAL_ARGS+=( "${REFANT_ARG[@]}" )
elif [[ -s "$QA_DIR/refant_ranking.json" ]]; then
  CAL_ARGS+=( --refant-ranking "$QA_DIR/refant_ranking.json" )
else
  CAL_ARGS+=( "${REFANT_ARG[@]}" )
fi
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
