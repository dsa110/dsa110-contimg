#!/bin/bash
# Clean Python and tool caches from the backend directory
#
# Usage:
#   ./scripts/clean_caches.sh        # Dry run (shows what would be deleted)
#   ./scripts/clean_caches.sh --force # Actually delete the files
#
# Removes:
#   - __pycache__/ directories
#   - .mypy_cache/ directories
#   - .pytest_cache/ directories
#   - coverage_html*/ directories
#   - *.pyc files
#   - .coverage files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

DRY_RUN=true
if [[ "$1" == "--force" ]] || [[ "$1" == "-f" ]]; then
    DRY_RUN=false
fi

echo "Cleaning caches in: $BACKEND_DIR"
echo ""

# Function to find and optionally remove directories
clean_dirs() {
    local pattern="$1"
    local description="$2"
    
    echo "=== $description ==="
    local dirs=$(find "$BACKEND_DIR" -type d -name "$pattern" 2>/dev/null)
    
    if [[ -z "$dirs" ]]; then
        echo "  (none found)"
    else
        echo "$dirs" | while read -r dir; do
            if $DRY_RUN; then
                echo "  [dry-run] would remove: $dir"
            else
                echo "  removing: $dir"
                rm -rf "$dir"
            fi
        done
    fi
    echo ""
}

# Function to find and optionally remove files
clean_files() {
    local pattern="$1"
    local description="$2"
    
    echo "=== $description ==="
    local files=$(find "$BACKEND_DIR" -type f -name "$pattern" 2>/dev/null)
    
    if [[ -z "$files" ]]; then
        echo "  (none found)"
    else
        echo "$files" | while read -r file; do
            if $DRY_RUN; then
                echo "  [dry-run] would remove: $file"
            else
                echo "  removing: $file"
                rm -f "$file"
            fi
        done
    fi
    echo ""
}

# Clean cache directories
clean_dirs "__pycache__" "Python bytecode caches"
clean_dirs ".mypy_cache" "MyPy type checking caches"
clean_dirs ".pytest_cache" "Pytest caches"
clean_dirs ".cache" "Generic caches"

# Clean coverage directories (pattern matching)
echo "=== Coverage HTML reports ==="
coverage_dirs=$(find "$BACKEND_DIR" -type d -name "coverage_html*" 2>/dev/null)
if [[ -z "$coverage_dirs" ]]; then
    echo "  (none found)"
else
    echo "$coverage_dirs" | while read -r dir; do
        if $DRY_RUN; then
            echo "  [dry-run] would remove: $dir"
        else
            echo "  removing: $dir"
            rm -rf "$dir"
        fi
    done
fi
echo ""

# Clean cache files
clean_files "*.pyc" "Compiled Python files"
clean_files ".coverage" "Coverage data files"

if $DRY_RUN; then
    echo "================================================"
    echo "This was a DRY RUN. No files were deleted."
    echo "Run with --force to actually delete these files."
    echo "================================================"
else
    echo "================================================"
    echo "Cache cleanup complete!"
    echo "================================================"
fi
