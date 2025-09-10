#!/usr/bin/env bash
set -euo pipefail
# Move to repo root
cd "$(dirname "$0")/.."
# Ensure destination exists
if [ ! -d logs/casa ]; then
  echo "logs/casa missing" >&2
  exit 1
fi
shopt -s nullglob
moved=0
for pat in casa-*.log casapy*.log casalog*.log; do
  for f in $pat; do
    [ -f "$f" ] || continue
    mv -f "$f" logs/casa/
    moved=1
  done
done
for d in casalogs core/casa; do
  if [ -d "$d" ]; then
    for f in "$d"/*.log; do
      [ -f "$f" ] && mv -f "$f" logs/casa/
    done
    rmdir "$d" 2>/dev/null || true
  fi
done
if [ "$moved" -eq 1 ]; then
  echo "Moved root CASA logs to logs/casa"
else
  echo "No root CASA logs to move"
fi
