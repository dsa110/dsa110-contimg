#!/bin/bash
# Template for creating dependency checks
# Copy this file and customize for your specific dependency

set -e

# Source error detection utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/error-detection.sh"
source "$SCRIPT_DIR/../lib/environment-dependency-check.sh"

# ============================================================================
# CUSTOMIZE THESE VALUES FOR YOUR DEPENDENCY
# ============================================================================

DEPENDENCY_NAME="[Tool/System Name]"
CHECK_COMMAND="[command to check dependency]"
EXPECTED_VALUE="[expected value]"
EXPECTED_PATH="[expected path, if applicable]"
MIN_VERSION="[minimum version, if applicable]"
ERROR_MESSAGE="[Custom error message]"
FIX_INSTRUCTIONS="[Clear instructions on how to fix]"

# ============================================================================
# IMPLEMENTATION (Choose one or more check types)
# ============================================================================

# Option 1: Exact value check
# check_environment_dependency \
#   "$DEPENDENCY_NAME" \
#   "$CHECK_COMMAND" \
#   "$EXPECTED_VALUE" \
#   "$ERROR_MESSAGE" \
#   "$FIX_INSTRUCTIONS"

# Option 2: Path check
# check_path_dependency \
#   "$DEPENDENCY_NAME" \
#   "$(echo "$CHECK_COMMAND" | awk '{print $1}')" \
#   "$EXPECTED_PATH" \
#   "$ERROR_MESSAGE" \
#   "$FIX_INSTRUCTIONS"

# Option 3: Version check (minimum version)
# check_version_dependency \
#   "$DEPENDENCY_NAME" \
#   "$CHECK_COMMAND" \
#   "$MIN_VERSION" \
#   "$ERROR_MESSAGE" \
#   "$FIX_INSTRUCTIONS"

# ============================================================================
# EXAMPLE: Node.js casa6 check (for reference)
# ============================================================================

# check_path_dependency \
#   "Node.js" \
#   "node" \
#   "/opt/miniforge/envs/casa6/bin/node" \
#   "Frontend tests require casa6 Node.js v22.6.0" \
#   "source /opt/miniforge/etc/profile.d/conda.sh && conda activate casa6"

# ============================================================================
# EXIT WITH APPROPRIATE CODE
# ============================================================================

# If all checks pass, exit 0
# If any check fails, exit 1 (already handled by check functions)

