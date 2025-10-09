# 1) Define run-specific variables
RUN_ID=0834_555_transit
INPUT_DIR=/data/incoming/${RUN_ID}
SCRATCH_ROOT=/scratch/dsa110-contimg
SCRATCH_MS=${SCRATCH_ROOT}/data-samples/ms/${RUN_ID}
START_TIME="2025-10-03 15:15:30"
END_TIME="2025-10-03 15:16:00"

# 2) Confirm scratch usage (optional)
echo "Checking scratch usage..."
scripts/scratch_sync.sh status

# 3) Optionally stage UVH5 inputs to ext4 (remove --dry-run to execute)
echo "Staging UVH5 inputs to ext4..."
DATA_ROOT=/data scripts/scratch_sync.sh stage incoming/${RUN_ID} --dry-run

# 4) Run the converter on the `casa6` environment, outputting to scratch
PYTHONPATH=${PYTHONPATH:-}
export PYTHONPATH=/data/dsa110-contimg/src${PYTHONPATH:+:${PYTHONPATH}}

echo "Running converter..."
python -m dsa110_contimg.conversion.uvh5_to_ms_converter_v2 \
    "${INPUT_DIR}" \
    "${SCRATCH_MS}" \
    "${START_TIME}" \
    "${END_TIME}" \
    --log-level INFO \
    --scratch-dir "${SCRATCH_ROOT}"

# 5) Validate results on scratch (QA / imaging as needed)

# 6) Archive the finished MS back to /data (remove --dry-run when ready)
echo "Archiving finished MS back to /data..."
scripts/scratch_sync.sh archive data-samples/ms/${RUN_ID} --dry-run

# 7) Clean up scratch copy after confirming archive (remove --dry-run to delete)
echo "Cleaning up scratch copy..."
scripts/scratch_sync.sh clean data-samples/ms/${RUN_ID} --dry-run
