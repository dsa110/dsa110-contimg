#!/usr/bin/env bash
set -euo pipefail

repo_root="/data/jfaber/dsa110-contimg"
cd "$repo_root"

# Create target directories
mkdir -p scripts/diagnostics
mkdir -p tests/migrated

# Move diagnostic/utility Python scripts into scripts/diagnostics
shopt -s nullglob
for f in examine_*.py; do
  mv -f -- "$f" scripts/diagnostics/
done

# Move CASA helper scripts into scripts/
for f in setup_casa_logging.sh start_casa_logging.sh; do
  if [[ -f "$f" ]]; then mv -f -- "$f" scripts/; fi
done

# Move stray test scripts at repo root into tests/migrated (to review later)
for f in test_*.py; do
  # Skip if already under tests/
  if [[ "$f" == tests/* ]]; then continue; fi
  mv -f -- "$f" tests/migrated/
done

echo "Repository scripts and tests reorganized. Review scripts/ and tests/migrated/."


