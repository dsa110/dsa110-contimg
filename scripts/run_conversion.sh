#!/usr/bin/env bash
set -euo pipefail

# Resolve script and repo paths so relative calls work from any CWD
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Python to use (prefer casa6 env if available)
PYTHON_BIN="/opt/miniforge/envs/casa6/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python"
fi

# 1) Define run-specific variables
RUN_ID=0834_555_transit
INPUT_DIR=/data/incoming/${RUN_ID}
SCRATCH_ROOT=/scratch/dsa110-contimg
SCRATCH_MS=${SCRATCH_ROOT}/data-samples/ms/${RUN_ID}
# Use the group timestamp for tight selection
START_TIME="2025-10-03 15:15:50"
END_TIME="2025-10-03 15:16:00"

# 2) Confirm scratch usage (optional)
echo "Checking scratch usage..."
"${SCRIPT_DIR}/scratch_sync.sh" status || echo "scratch_sync.sh status skipped (helper not found)"

# 3) Stage UVH5 inputs to SSD (ext4) and switch INPUT_DIR to the staged path when available
echo "Staging UVH5 inputs to SSD..."
if "${SCRIPT_DIR}/scratch_sync.sh" stage incoming/${RUN_ID}; then
  STAGED_INPUT_DIR="${SCRATCH_ROOT}/incoming/${RUN_ID}"
  if [[ -d "${STAGED_INPUT_DIR}" ]]; then
    INPUT_DIR="${STAGED_INPUT_DIR}"
    echo "Using staged INPUT_DIR=${INPUT_DIR}"
  fi
else
  echo "scratch staging skipped (helper not found or failed); continuing with INPUT_DIR=${INPUT_DIR}"
fi

# 4) Run the converter on the casa6 environment (or current python), outputting to scratch
PYTHONPATH=${PYTHONPATH:-}
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

echo "Running converter..."
"${PYTHON_BIN}" -m dsa110_contimg.conversion.uvh5_to_ms_converter_v2 \
    "${INPUT_DIR}" \
    "${SCRATCH_MS}" \
    "${START_TIME}" \
    "${END_TIME}" \
    --log-level INFO \
    --scratch-dir "${SCRATCH_ROOT}" \
    --tmpfs-path /dev/shm \
    --field-per-integration \
    --dask-write-failfast \
    --daskms-row-chunks 8192 \
    --daskms-cube-row-chunks 8192

# 5) Validate results on scratch (QA / imaging as needed)
echo "Verifying MS FIELD/SPW structure..."
# Find latest MS in the run output directory
MS_PATH="$(ls -1dt "${SCRATCH_MS}"/*.ms 2>/dev/null | head -n1 || true)"
if [[ -z "${MS_PATH}" ]]; then
  echo "No MS found under ${SCRATCH_MS} yet." >&2
else
  echo "MS_PATH=${MS_PATH}"
  export MS_PATH
  "${PYTHON_BIN}" - <<'PY'
from casacore.tables import table
import numpy as np, os
ms = os.environ.get('MS_PATH')
print(f"Verifying: {ms}")
with table(ms+'::FIELD') as tf:
    n = tf.nrows(); names = list(tf.getcol('NAME'))
    print('FIELD rows:', n)
    if n: print('First 5 names:', names[:5])
    pd = tf.getcol('PHASE_DIR')
    print('PHASE_DIR shape:', pd.shape)
with table(ms) as tb:
    fids = tb.getcol('FIELD_ID')
    u = np.unique(fids)
    print('Unique FIELD_IDs:', u.tolist(), 'count=', len(u))
    # print counts per FIELD_ID (first 10)
    counts = [(int(x), int((fids==x).sum())) for x in u[:10]]
    print('Counts per FIELD_ID (first 10):', counts)
with table(ms+'::SPECTRAL_WINDOW') as spw:
    print('SPW rows:', spw.nrows())
PY
fi

# 6) Archive the finished MS back to /data (remove --dry-run when ready)
echo "Archiving finished MS back to /data..."
"${SCRIPT_DIR}/scratch_sync.sh" archive data-samples/ms/${RUN_ID} --dry-run || echo "archive skipped (helper not found)"

# 7) Clean up scratch copy after confirming archive (remove --dry-run to delete)
echo "Cleaning up scratch copy..."
"${SCRIPT_DIR}/scratch_sync.sh" clean data-samples/ms/${RUN_ID} --dry-run || echo "cleanup skipped (helper not found)"
