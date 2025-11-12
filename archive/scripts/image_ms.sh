#!/usr/bin/env bash

set -euo pipefail

# Usage:
#   scripts/image_ms.sh \
#     /path/to/data.ms \
#     /path/to/output/image_prefix \
#     [--field ""] [--spw ""] [--imsize 1024] [--cell-arcsec 2.0] \
#     [--weighting briggs] [--robust 0.0] [--niter 1000] [--threshold 0.0Jy] \
#     [--no-pbcor] [--quick] [--skip-fits] [--uvrange '>1klambda']

MS_PATH=${1:?"Provide path to input MS as first argument"}
OUT_PREFIX=${2:?"Provide output image prefix as second argument"}
shift 2 || true

export PYTHONPATH=/data/dsa110-contimg/src:${PYTHONPATH:-}

# Route temporary files to scratch to avoid polluting the repo directory
CONTIMG_SCRATCH_DIR=${CONTIMG_SCRATCH_DIR:-/scratch/dsa110-contimg}
TMPBASE="${CONTIMG_SCRATCH_DIR%/}/tmp"
mkdir -p "$TMPBASE"
export CONTIMG_SCRATCH_DIR
export TMPDIR="$TMPBASE" TMP="$TMPBASE" TEMP="$TMPBASE" CASA_TMPDIR="$TMPBASE"
export HDF5_USE_FILE_LOCKING="FALSE"

python -m dsa110_contimg.imaging.cli \
  --ms "$MS_PATH" \
  --imagename "$OUT_PREFIX" \
  "$@"

echo "Imaging complete: ${OUT_PREFIX}.* (CASA images and FITS exported if present)"

