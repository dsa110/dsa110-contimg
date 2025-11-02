#!/bin/bash

# Cleanup CASA Log Files
# This script deletes casa-*.log files from /data/dsa110-contimg/state/logs/
# It can be configured to delete all logs or keep logs from the last N hours.

set -euo pipefail

# Configuration
LOG_DIR="/data/dsa110-contimg/state/logs"
LOG_PATTERN="casa-*.log"
KEEP_HOURS="${KEEP_HOURS:-0}"  # Keep logs from last N hours (0 = delete all)

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
    echo "  --keep-hours N    Keep logs from the last N hours (default: 0 = delete all)"
    echo "  --dry-run         Show what would be deleted without actually deleting"
    echo "  -h, --help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Delete all casa-*.log files"
    echo "  $0 --keep-hours 24    # Keep logs from last 24 hours"
    echo "  $0 --dry-run          # Preview what would be deleted"
}

# Parse command line arguments
DRY_RUN=false
KEEP_HOURS=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --keep-hours)
            KEEP_HOURS="$2"
            shift 2
            ;;
        --dry-run)
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

# Check if log directory exists
if [ ! -d "$LOG_DIR" ]; then
    print_error "Log directory does not exist: $LOG_DIR"
    exit 1
fi

# Check if running as dry-run
if [ "$DRY_RUN" = true ]; then
    print_info "DRY RUN MODE - No files will actually be deleted"
    echo ""
fi

# Find log files to delete
if [ "$KEEP_HOURS" -gt 0 ]; then
    # Delete files older than KEEP_HOURS
    CUTOFF_TIME=$(date -d "$KEEP_HOURS hours ago" +%s 2>/dev/null || date -v-${KEEP_HOURS}H +%s 2>/dev/null || echo "")
    if [ -z "$CUTOFF_TIME" ]; then
        print_error "Failed to calculate cutoff time. Your system may not support 'date -d' or 'date -v'"
        exit 1
    fi
    
    print_info "Keeping logs from the last $KEEP_HOURS hours"
    print_info "Cutoff time: $(date -d "@$CUTOFF_TIME" 2>/dev/null || date -r "$CUTOFF_TIME" 2>/dev/null || echo "unknown")"
    
    DELETED_COUNT=0
    KEPT_COUNT=0
    
    # Process each log file
    while IFS= read -r file; do
        if [ -n "$file" ] && [ -f "$file" ]; then
            FILE_TIME=$(stat -c %Y "$file" 2>/dev/null || stat -f %m "$file" 2>/dev/null || echo "0")
            
            if [ "$FILE_TIME" -lt "$CUTOFF_TIME" ]; then
                if [ "$DRY_RUN" = true ]; then
                    print_info "Would delete: $file ($(date -d "@$FILE_TIME" 2>/dev/null || date -r "$FILE_TIME" 2>/dev/null || echo "unknown"))"
                else
                    if rm "$file" 2>/dev/null; then
                        print_success "Deleted: $file"
                        ((DELETED_COUNT++))
                    else
                        print_error "Failed to delete: $file"
                    fi
                fi
            else
                ((KEPT_COUNT++))
            fi
        fi
    done < <(find "$LOG_DIR" -maxdepth 1 -type f -name "$LOG_PATTERN" 2>/dev/null)
    
    if [ "$DRY_RUN" = true ]; then
        print_info "Dry run complete. Would delete files older than $KEEP_HOURS hours."
    else
        print_info "Cleanup completed:"
        print_success "Deleted: $DELETED_COUNT files"
        print_info "Kept: $KEPT_COUNT files"
    fi
else
    # Delete all casa-*.log files
    print_info "Deleting all casa-*.log files from $LOG_DIR"
    
    FILES_TO_DELETE=$(find "$LOG_DIR" -maxdepth 1 -type f -name "$LOG_PATTERN" 2>/dev/null)
    
    if [ -z "$FILES_TO_DELETE" ]; then
        print_info "No casa-*.log files found to delete"
        exit 0
    fi
    
    FILE_COUNT=$(echo "$FILES_TO_DELETE" | wc -l)
    print_info "Found $FILE_COUNT casa-*.log files to delete"
    
    if [ "$DRY_RUN" = true ]; then
        echo ""
        print_info "Files that would be deleted:"
        echo "$FILES_TO_DELETE" | while read -r file; do
            if [ -n "$file" ]; then
                echo "  $file"
            fi
        done
        echo ""
        print_info "Dry run complete. Use without --dry-run to actually delete files."
    else
        DELETED_COUNT=0
        FAILED_COUNT=0
        
        while IFS= read -r file; do
            if [ -n "$file" ] && [ -f "$file" ]; then
                if rm "$file" 2>/dev/null; then
                    ((DELETED_COUNT++))
                else
                    print_error "Failed to delete: $file"
                    ((FAILED_COUNT++))
                fi
            fi
        done < <(echo "$FILES_TO_DELETE")
        
        print_info "Cleanup completed:"
        print_success "Successfully deleted: $DELETED_COUNT files"
        if [ $FAILED_COUNT -gt 0 ]; then
            print_error "Failed to delete: $FAILED_COUNT files"
        fi
    fi
fi

exit 0

