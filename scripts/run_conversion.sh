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
# Prefer RAM disk when available for fastest writes
if mount | grep -q "/dev/shm"; then
  SCRATCH_ROOT=/dev/shm/dsa110-contimg
else
  SCRATCH_ROOT=/scratch/dsa110-contimg
fi
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
#    Default path uses the strategies module with the direct-subband writer for
#    parallel I/O and robust MS creation. Worker count is controlled by
#    CONTIMG_MAX_WORKERS (default 8).
PYTHONPATH=${PYTHONPATH:-}
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

# CASA/dask stability: keep thread pools small and avoid HDF5 file locking
export OMP_NUM_THREADS="1"
export OPENBLAS_NUM_THREADS="1"
export MKL_NUM_THREADS="1"
export NUMEXPR_NUM_THREADS="1"
export HDF5_USE_FILE_LOCKING="FALSE"

echo "Running converter (strategies: auto; tmpfs staging when available)..."
MAX_WORKERS="${CONTIMG_MAX_WORKERS:-8}"
"${PYTHON_BIN}" -m dsa110_contimg.conversion.strategies.uvh5_to_ms_converter \
    "${INPUT_DIR}" \
    "${SCRATCH_MS}" \
    "${START_TIME}" \
    "${END_TIME}" \
    --log-level INFO \
    --scratch-dir "${SCRATCH_ROOT}" \
    --writer auto \
    --stage-to-tmpfs \
    --tmpfs-path /dev/shm \
    --max-workers "${MAX_WORKERS}"

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
with table(ms+'::POLARIZATION') as pol:
    ct = np.asarray(pol.getcol('CORR_TYPE'))
    print('POL CORR_TYPE:', ct.tolist())
with table(ms) as tb:
    cols = set(tb.colnames())
    if 'INTERVAL' in cols:
        iv = tb.getcol('INTERVAL')
        print('INTERVAL min/max:', float(np.nanmin(iv)), float(np.nanmax(iv)))
        assert np.all(iv > 0), 'INTERVAL must be > 0'
    assert 'WEIGHT_SPECTRUM' in cols, 'WEIGHT_SPECTRUM missing'
    # Basic shape check
    d0 = tb.getcell('DATA', 0)
    ws0 = tb.getcell('WEIGHT_SPECTRUM', 0)
    assert d0.shape == ws0.shape, f'WEIGHT_SPECTRUM shape {ws0.shape} != DATA shape {d0.shape}'
    # OBSERVATION_ID should be 0 for all rows
    if 'OBSERVATION_ID' in cols:
        oid = tb.getcol('OBSERVATION_ID')
        u = np.unique(oid)
        print('OBSERVATION_ID uniques:', u.tolist())
        assert u.size == 1 and u[0] == 0, 'OBSERVATION_ID must be all zeros'
    # SCAN_NUMBER should be >= 1
    if 'SCAN_NUMBER' in cols:
        sc = tb.getcol('SCAN_NUMBER')
        print('SCAN_NUMBER min/max:', int(sc.min()), int(sc.max()))
        assert sc.min() >= 1, 'SCAN_NUMBER must be >= 1'
print('Strict MS checks passed.')
with table(ms+'::FEED') as feed:
    print('FEED rows:', feed.nrows())
    if feed.nrows() > 0 and 'POLARIZATION_TYPE' in feed.colnames():
        try:
            print('FEED POLARIZATION_TYPE[0]:', feed.getcol('POLARIZATION_TYPE')[0].tolist())
        except Exception:
            pass
with table(ms+'::FIELD') as tf:
    if 'TIME' in tf.colnames():
        tm = tf.getcol('TIME')
        print('FIELD TIME min/max:', float(np.nanmin(tm)), float(np.nanmax(tm)))
PY
fi

# 6) Archive the finished MS back to /data (remove --dry-run when ready)
echo "Archiving finished MS back to /data..."
"${SCRIPT_DIR}/scratch_sync.sh" archive data-samples/ms/${RUN_ID} --dry-run || echo "archive skipped (helper not found)"

# 7) Clean up scratch copy after confirming archive (remove --dry-run to delete)
echo "Cleaning up scratch copy..."
"${SCRIPT_DIR}/scratch_sync.sh" clean data-samples/ms/${RUN_ID} --dry-run || echo "cleanup skipped (helper not found)"
