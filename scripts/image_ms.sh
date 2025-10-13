#!/usr/bin/env bash

set -euo pipefail

# Usage:
#   scripts/image_ms.sh \
#     /path/to/data.ms \
#     /path/to/output/image_prefix \
#     [--field ""] [--spw ""] [--imsize 1024] [--cell-arcsec 2.0] \
#     [--weighting briggs] [--robust 0.0] [--niter 1000] [--threshold 0.0Jy] \
#     [--no-pbcor]

MS_PATH=${1:?"Provide path to input MS as first argument"}
OUT_PREFIX=${2:?"Provide output image prefix as second argument"}
shift 2 || true

export PYTHONPATH=/data/dsa110-contimg/src:${PYTHONPATH:-}

python -m dsa110_contimg.imaging.cli \
  --ms "$MS_PATH" \
  --imagename "$OUT_PREFIX" \
  "$@"

echo "Imaging complete: ${OUT_PREFIX}.* (CASA images and FITS exported if present)"


