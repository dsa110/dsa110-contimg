#!/bin/bash
# Pre-commit hook to prevent markdown files in root directory
# Part of the pre-commit hook chain

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Check for markdown files being added to root
STAGED_MARKDOWN=$(git diff --cached --name-only --diff-filter=A | grep -E "^[^/]+\.md$" || true)

if [ -n "$STAGED_MARKDOWN" ]; then
    echo "ERROR: Attempting to commit markdown files to repository root!" >&2
    echo "" >&2
    echo "The following files are in the root directory:" >&2
    for file in $STAGED_MARKDOWN; do
        echo "  - $file" >&2
    done
    echo "" >&2
    echo "All markdown files MUST be in the docs/ structure." >&2
    echo "" >&2
    echo "Quick fix:" >&2
    echo "  1. Check docs/DOCUMENTATION_QUICK_REFERENCE.md for correct location" >&2
    echo "  2. Move file to appropriate docs/ subdirectory" >&2
    echo "  3. Use: scripts/migrate_docs.sh to move files automatically" >&2
    echo "" >&2
    echo "See .cursor/rules/documentation-location.mdc for details." >&2
    exit 1
fi

exit 0

