#!/bin/bash
# Start CASA logging monitoring

# Set environment variables
export CASA_LOG_DIR="/data/jfaber/dsa110-contimg/casalogs"
export CASA_LOG_FILE="/data/jfaber/dsa110-contimg/casalogs/casa.log"

# Start the poller
cd "/data/jfaber/dsa110-contimg"
python "/data/jfaber/dsa110-contimg/scripts/casa_log_poller.py" --daemon
