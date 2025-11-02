#!/bin/bash

# Move CASA Log Files to Centralized Directory
# This script moves all casa-*.log files from /data/ subdirectories to /data/dsa110-contimg/state/
# while preserving the original subdirectory structure.

set -e  # Exit on any error

# Configuration
SOURCE_ROOT="/data/dsa110-contimg"
TARGET_ROOT="/data/dsa110-contimg/state/logs"
LOG_PATTERN="casa-*.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --dry-run    Show what would be moved without actually moving files"
    echo "  -h, --help       Show this help message"
    echo ""
    echo "This script moves all casa-*.log files from /data/dsa110-contimg/ to /data/dsa110-contimg/state/logs/"
    echo "All log files will be moved directly to the logs directory (no subdirectory structure preserved)."
}

# Parse command line arguments
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if running as dry-run
if [ "$DRY_RUN" = true ]; then
    print_info "DRY RUN MODE - No files will actually be moved"
    echo ""
fi

# Create target directory if it doesn't exist
if [ ! -d "$TARGET_ROOT" ]; then
    if [ "$DRY_RUN" = true ]; then
        print_info "Would create directory: $TARGET_ROOT"
    else
        print_info "Creating target directory: $TARGET_ROOT"
        mkdir -p "$TARGET_ROOT"
        print_success "Created directory: $TARGET_ROOT"
    fi
fi

# Find all casa-*.log files, excluding the target directory
print_info "Searching for casa-*.log files in $SOURCE_ROOT..."
FILES_TO_MOVE=$(find "$SOURCE_ROOT" -type f -name "$LOG_PATTERN" -not -path "*/state/logs/*" 2>/dev/null)

if [ -z "$FILES_TO_MOVE" ]; then
    print_warning "No casa-*.log files found in $SOURCE_ROOT"
    exit 0
fi

# Count files
FILE_COUNT=$(echo "$FILES_TO_MOVE" | wc -l)
print_info "Found $FILE_COUNT casa-*.log files to move"

if [ "$DRY_RUN" = true ]; then
    echo ""
    print_info "Files that would be moved:"
    echo "$FILES_TO_MOVE" | while read -r file; do
        if [ -n "$file" ]; then
            # Extract just the filename
            filename=$(basename "$file")
            target_path="$TARGET_ROOT/$filename"
            echo "  $file -> $target_path"
        fi
    done
    echo ""
    print_info "Dry run complete. Use without --dry-run to actually move files."
    exit 0
fi

# Move files
MOVED_COUNT=0
FAILED_COUNT=0

# Use process substitution instead of pipe to avoid subshell issues
while IFS= read -r file; do
    if [ -n "$file" ]; then
        # Extract just the filename
        filename=$(basename "$file")
        target_path="$TARGET_ROOT/$filename"
        
        # Handle filename collisions by appending a number
        if [ -f "$target_path" ]; then
            base="${filename%.log}"
            counter=1
            while [ -f "$TARGET_ROOT/${base}_${counter}.log" ]; do
                ((counter++))
            done
            target_path="$TARGET_ROOT/${base}_${counter}.log"
        fi
        
        # Move the file
        if mv "$file" "$target_path" 2>/dev/null; then
            print_success "Moved: $file -> $target_path"
            ((MOVED_COUNT++))
        else
            print_error "Failed to move: $file"
            ((FAILED_COUNT++))
        fi
    fi
done < <(echo "$FILES_TO_MOVE")

# Summary
echo ""
print_info "Move operation completed:"
print_success "Successfully moved: $MOVED_COUNT files"
if [ $FAILED_COUNT -gt 0 ]; then
    print_error "Failed to move: $FAILED_COUNT files"
fi

print_info "All casa-*.log files have been moved to $TARGET_ROOT"
