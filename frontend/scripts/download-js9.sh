#!/bin/bash
# Download JS9 files and generate minimal source maps
# This allows us to serve JS9 locally and provide source maps to prevent 404 errors

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PUBLIC_DIR="${FRONTEND_DIR}/public"
JS9_DIR="${PUBLIC_DIR}/js9"
JS9_CDN_BASE="https://cdn.jsdelivr.net/gh/ericmandel/js9@latest"

echo "Downloading JS9 files to ${JS9_DIR}..."

# Create JS9 directory
mkdir -p "${JS9_DIR}"

# Files to download
JS9_FILES=(
    "js9support.js"
    "js9support.css"
    "js9.min.js"
    "js9Prefs.json"
    "js9worker.js"
    "astroemw.wasm"
    "astroemw.js"
)

# Download each file
for file in "${JS9_FILES[@]}"; do
    echo "  Downloading ${file}..."
    curl -sL "${JS9_CDN_BASE}/${file}" -o "${JS9_DIR}/${file}" || {
        echo "ERROR: Failed to download ${file}" >&2
        exit 1
    }
done

# Generate minimal identity source maps for JS files
# These prevent 404 errors while providing no debugging benefit (identity mapping)
generate_source_map() {
    local js_file="$1"
    local map_file="${js_file}.map"
    local filename=$(basename "${js_file}")
    
    # Create minimal valid source map (version 3, identity mapping)
    cat > "${map_file}" <<EOF
{
  "version": 3,
  "file": "${filename}",
  "sources": [],
  "mappings": "",
  "names": []
}
EOF
    echo "  Generated ${map_file}"
}

# Generate source maps for JS files
echo "Generating source maps..."
for js_file in "${JS9_DIR}/js9support.js" "${JS9_DIR}/js9.min.js"; do
    if [ -f "${js_file}" ]; then
        generate_source_map "${js_file}"
    fi
done

echo "JS9 files downloaded successfully to ${JS9_DIR}"
echo "Source maps generated for JavaScript files"

