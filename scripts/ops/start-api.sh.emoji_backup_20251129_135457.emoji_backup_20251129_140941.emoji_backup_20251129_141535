#!/bin/bash
# Start the backend API with warning suppression

# Suppress CASA warnings via environment variable (belt and suspenders approach)
export PYTHONWARNINGS="ignore:pkg_resources is deprecated:UserWarning:casaconfig.private.measures_update"

# Activate casa6
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Start uvicorn
echo ":rocket: Starting backend API on port 8000..."
echo "   Warnings suppressed via PYTHONWARNINGS"
echo ""
exec uvicorn dsa110_contimg.api:app --host 0.0.0.0 --port 8000 "$@"
