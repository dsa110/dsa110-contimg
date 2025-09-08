#!/usr/bin/env bash
set -euo pipefail

root="/data/jfaber/dsa110-contimg"
cd "$root"

# Create canonical data subdirs
mkdir -p data/ms data/cal_tables data/sky_models data/tmp

# Add keep-only .gitignore files inside data subdirs where appropriate
for d in data/ms data/sky_models data/tmp; do
  mkdir -p "$d"
  printf '%s\n' '*' '!.gitignore' > "$d/.gitignore"
done

# Ensure repo .gitignore has appropriate ignores
add_gitignore_entry() {
  local entry="$1"
  grep -Fqx "$entry" .gitignore 2>/dev/null || echo "$entry" >> .gitignore
}

echo "" >> .gitignore
echo "# Data artifacts" >> .gitignore
add_gitignore_entry "data/ms/"
add_gitignore_entry "data/sky_models/"
add_gitignore_entry "data/tmp/"

# Preserve calibration tables under version control; do not ignore data/cal_tables
echo "Data layout standardized under data/ (ms/, cal_tables/, sky_models/, tmp/)." 


