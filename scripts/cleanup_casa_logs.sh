#!/usr/bin/env bash
set -euo pipefail
cd /bin/..
mkdir -p logs/casa
shopt -s nullglob
moved=0
for pat in 'casa-*.log' 'casapy*.log' 'casalog*.log'; do
  for f in ; do
    if [ -f  ]; then
      mv -f  logs/casa/
      moved=1
    fi
  done
done
# Move from common casa-like subdirs at repo root
for d in casalogs core/casa; do
  if [ -d  ]; then
    for f in /*.log; do
      [ -f  ] && mv -f  logs/casa/
    done
    rmdir  2>/dev/null || true
  fi
done
# Summary
if [  -eq 1 ]; then
  echo CASA
