#!/usr/bin/env bash
set -euo pipefail

# Create standardized logs directories
mkdir -p logs/casa logs/pipeline

# Ensure logs/ keeps a placeholder for empty dirs
printf '%s\n' '*' '!.gitignore' > logs/.gitignore

# Ensure repository .gitignore ignores logs and stray casa logs at root
if ! grep -Fqx 'logs/' .gitignore 2>/dev/null; then
  {
    echo ""
    echo "# Logs"
    echo "logs/"
    echo "casalogs/"
    echo "casa-*.log"
  } >> .gitignore
fi

# Move existing CASA logs at repo root into logs/casa
shopt -s nullglob
for f in casa-*.log; do
  mv -f -- "$f" logs/casa/
done

# Move any legacy casalogs content into logs/casa
if [[ -d casalogs ]]; then
  shopt -s nullglob
  mv -f -- casalogs/* logs/casa/ 2>/dev/null || true
  # Optionally remove empty legacy directory
  rmdir casalogs 2>/dev/null || true
fi

echo "Logs structure standardized. CASA logs in logs/casa/."


