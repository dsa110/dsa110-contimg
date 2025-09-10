#!/usr/bin/env bash
# Use absolute paths to avoid CWD surprises
ROOT="/data/jfaber/dsa110-contimg"
mkdir -p "${ROOT}/logs/casa"
TS="$(date +%Y%m%d_%H%M%S)"
export CASA_LOG="${ROOT}/logs/casa/casa_${TS}_$$.log"
export PYTHONUNBUFFERED=1
