#!/bin/bash
# Documentation Consolidation Migration Script
# Purpose: Move files from root and source directories to organized docs/ structure
# Usage: ./scripts/migrate_docs.sh [--dry-run] [--verbose]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRY_RUN=false
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--verbose]"
            exit 1
            ;;
    esac
done

log() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo "[INFO] $*"
    fi
}

move_file() {
    local src="$1"
    local dst="$2"
    
    if [[ ! -f "$src" ]]; then
        log "Skipping (not found): $src"
        return
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY-RUN] Would move: $src -> $dst"
    else
        mkdir -p "$(dirname "$dst")"
        mv "$src" "$dst"
        log "Moved: $src -> $dst"
    fi
}

# Create directory structure
if [[ "$DRY_RUN" == "false" ]]; then
    mkdir -p "$PROJECT_ROOT/internal/docs/dev/analysis"
    mkdir -p "$PROJECT_ROOT/internal/docs/dev/status/2025-01"
    mkdir -p "$PROJECT_ROOT/internal/docs/dev/notes"
    mkdir -p "$PROJECT_ROOT/docs/archive/status_reports"
fi

echo "Starting documentation migration..."
echo "Dry run: $DRY_RUN"
echo ""

# Phase 1: Root directory status reports
echo "Phase 1: Moving root directory status reports..."
move_file "$PROJECT_ROOT/DASHBOARD_ENDPOINT_TEST_RESULTS.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/dashboard_endpoint_test_results.md"

move_file "$PROJECT_ROOT/DASHBOARD_REAL_DATA_IMPLEMENTATION.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/dashboard_real_data_implementation.md"

move_file "$PROJECT_ROOT/DASHBOARD_TBD_STATUS.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/dashboard_tbd_status.md"

move_file "$PROJECT_ROOT/ENDPOINT_TEST_SUMMARY.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/endpoint_test_summary.md"

move_file "$PROJECT_ROOT/ENDPOINT_VERIFICATION_COMPLETE.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/endpoint_verification_complete.md"

move_file "$PROJECT_ROOT/SKYVIEW_IMAGE_DISPLAY_VERIFICATION.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/skyview_image_display_verification.md"

move_file "$PROJECT_ROOT/SKYVIEW_SPRINT1_COMPLETE.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/skyview_sprint1_complete.md"

move_file "$PROJECT_ROOT/SKYVIEW_TEST_RESULTS.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/skyview_test_results.md"

move_file "$PROJECT_ROOT/SKYVIEW_TROUBLESHOOTING.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/skyview_troubleshooting.md"

move_file "$PROJECT_ROOT/TESTING_SUMMARY.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/testing_summary.md"

move_file "$PROJECT_ROOT/TEST_RESULTS.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/test_results.md"

move_file "$PROJECT_ROOT/VALIDATION_DEMONSTRATION.md" \
          "$PROJECT_ROOT/internal/docs/dev/status/2025-01/validation_demonstration.md"

# Phase 2: Root directory analysis reports
echo ""
echo "Phase 2: Moving root directory analysis reports..."
move_file "$PROJECT_ROOT/TIME_INVESTIGATION_REPORT.md" \
          "$PROJECT_ROOT/internal/docs/dev/analysis/time_investigation_report.md"

move_file "$PROJECT_ROOT/TIME_VALIDATION_STRATEGY.md" \
          "$PROJECT_ROOT/internal/docs/dev/analysis/time_validation_strategy.md"

move_file "$PROJECT_ROOT/DUPLICATE_TIME_INVESTIGATION.md" \
          "$PROJECT_ROOT/internal/docs/dev/analysis/duplicate_time_investigation.md"

move_file "$PROJECT_ROOT/BUG_REPORT.md" \
          "$PROJECT_ROOT/internal/docs/dev/analysis/bug_report.md"

# Phase 3: Root directory notes
echo ""
echo "Phase 3: Moving root directory notes..."
move_file "$PROJECT_ROOT/ARCHITECTURAL_ELEGANCE_BRAINSTORM.md" \
          "$PROJECT_ROOT/internal/docs/dev/notes/architectural_elegance_brainstorm.md"

move_file "$PROJECT_ROOT/ARCHITECTURE_OPTIMIZATION_RECOMMENDATIONS.md" \
          "$PROJECT_ROOT/internal/docs/dev/notes/architecture_optimization_recommendations.md"

move_file "$PROJECT_ROOT/PYUVDATA_USAGE_ANALYSIS.md" \
          "$PROJECT_ROOT/internal/docs/dev/notes/pyuvdata_usage_analysis.md"

# Phase 4: Reference documentation
echo ""
echo "Phase 4: Moving reference documentation..."
move_file "$PROJECT_ROOT/DEVELOPER_GUIDE.md" \
          "$PROJECT_ROOT/docs/reference/developer_guide.md"

# Phase 5: Source directory files
echo ""
echo "Phase 5: Moving source directory files..."
move_file "$PROJECT_ROOT/src/dsa110_contimg/RA_CALCULATION_ISSUE.md" \
          "$PROJECT_ROOT/internal/docs/dev/analysis/ra_calculation_issue.md"

move_file "$PROJECT_ROOT/src/dsa110_contimg/TIME_HANDLING_ISSUES.md" \
          "$PROJECT_ROOT/internal/docs/dev/analysis/time_handling_issues.md"

# Phase 6: Archive completed status reports
echo ""
echo "Phase 6: Archiving old status reports..."
# Add logic here to move files older than 1 year to archive/

echo ""
echo "Migration complete!"
echo ""
echo "Next steps:"
echo "1. Review moved files"
echo "2. Update cross-references in moved files"
echo "3. Update links in other documentation"
echo "4. Create entry point READMEs"
echo "5. Test all links"
