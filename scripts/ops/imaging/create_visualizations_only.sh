#!/bin/bash
# Create visualizations only (assumes mosaic already exists)
# Run this in foreground to see progress

cd /data/dsa110-contimg
export PYTHONPATH=/data/dsa110-contimg/backend/src:$PYTHONPATH

/opt/miniforge/envs/casa6/bin/python scripts/create_mosaic_visualizations.py
