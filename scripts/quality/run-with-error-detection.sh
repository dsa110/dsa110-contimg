#!/bin/bash
# Error Detection Wrapper
# Runs any command and kills execution if errors are detected in output
#
# Usage:
#   ./scripts/run-with-error-detection.sh <command> [args...]
#   ./scripts/run-with-error-detection.sh pytest tests/ -v
#   ./scripts/run-with-error-detection.sh python script.py
#
# Features:
#   - Detects common error patterns in output
#   - Checks exit codes
#   - Preserves full output (unbuffered, logged)
#   - Exits with error if any errors detected
#   - Context-aware error detection (avoids false positives)
#   - Structured pytest parsing (supports --junitxml)

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
error() {
  echo -e "${RED}[ERROR-DETECTION]${NC} $1" >&2
}

warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if command provided
if [ $# -eq 0 ]; then
  error "No command provided"
  echo "Usage: $0 <command> [args...]"
  echo "Example: $0 pytest tests/ -v"
  exit 1
fi

# Create log file with timestamp
LOG_DIR="${LOG_DIR:-/tmp}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/error-detection-${TIMESTAMP}.log"

info "Running command: $*"
info "Log file: $LOG_FILE"

# Comprehensive error patterns
# These patterns detect common error words/phrases across different systems
declare -a ERROR_PATTERNS=(
  # Python errors
  "Traceback"
  "Exception:"
  "^Error:"           # Error at start of line (more specific)
  "^ERROR:"           # ERROR at start of line
  "Fatal error"
  "SyntaxError"
  "TypeError"
  "ValueError"
  "AttributeError"
  "ImportError"
  "ModuleNotFoundError"
  "FileNotFoundError"
  "PermissionError"
  "OSError"
  "RuntimeError"
  "KeyError"
  "IndexError"
  "NameError"
  "UnboundLocalError"
  "AssertionError"
  "sqlite3.OperationalError"
  "sqlite3.IntegrityError"
  "sqlite3.DatabaseError"
  
  # Test failures
  "^FAILED"           # FAILED at start of line
  "FAILURE"
  "failure"
  "test.*failed"
  ".*tests? failed"
  "assert.*failed"
  
  # Shell/system errors
  "command not found"
  "Permission denied"
  "No such file or directory"
  "^Cannot"           # Cannot at start of line
  "^can't"            # can't at start of line
  "^Unable to"        # Unable to at start of line
  "^unable to"        # unable to at start of line
  "^Failed to"        # Failed to at start of line
  "^failed to"        # failed to at start of line
  "Error occurred"
  "error occurred"
  
  # CASA errors
  "SEVERE"
  "Exception Reported"
  "Table.*does not exist"
  "invalid table"
  
  # Database errors
  "OperationalError"
  "IntegrityError"
  "DatabaseError"
  "table.*has no column"
  "no such table"
  "database.*locked"
  "database.*corrupt"
  
  # Build/compilation errors
  "Build failed"
  "Compilation error"
  "Compilation failed"
  "build error"
  "compilation error"
  
  # Network/API errors
  "ConnectionError"
  "TimeoutError"
  "HTTPError"
  "Connection refused"
  "Connection timeout"
  "Network error"
  
  # General error indicators
  "^CRITICAL"         # CRITICAL at start of line
  "^FATAL"            # FATAL at start of line
  "^fatal"            # fatal at start of line
  "^Aborted"          # Aborted at start of line
  "^aborted"          # aborted at start of line
  "^Killed"           # Killed at start of line
  "^killed"           # killed at start of line
  "Segmentation fault"
  "segfault"
  "core dumped"
  "Abort trap"
)

# Patterns to exclude (false positives)
# These are checked in context - must appear on same line or nearby
declare -a EXCLUDE_PATTERNS=(
  "No errors"
  "no errors"
  "Error handling"
  "error handling"
  "Error recovery"
  "error recovery"
  "Error detection"   # Our own script messages
  "ERROR-DETECTION"   # Our own script messages
  "Error patterns"    # Documentation
  "error patterns"    # Documentation
  "Error: 0"          # Zero errors
  "errors: 0"         # Zero errors
  "0 failed"          # Zero failures
  "0 errors"          # Zero errors
  "passed.*failed.*0" # All passed, 0 failed
  "#.*Error"          # Comments containing Error
  "#.*error"           # Comments containing error
  "def.*error"         # Function definitions
  "class.*Error"       # Class definitions
  "test.*error"        # Test names containing error
  "test.*Error"        # Test names containing Error
)

# Commands that may legitimately exit with non-zero codes
# These are checked by command name prefix
declare -a EXPECTED_NONZERO_COMMANDS=(
  "grep"
  "diff"
  "test"
  "["
)

# Function to check if command is expected to exit non-zero
is_expected_nonzero() {
  local command="$1"
  local first_word=$(echo "$command" | awk '{print $1}')
  
  for expected_cmd in "${EXPECTED_NONZERO_COMMANDS[@]}"; do
    if [[ "$first_word" == "$expected_cmd" ]] || [[ "$command" == *"$expected_cmd"* ]]; then
      return 0  # Expected non-zero
    fi
  done
  
  return 1  # Not expected
}

# Function to check if error pattern is in a false positive context
is_false_positive_line() {
  local line="$1"
  local pattern="$2"
  
  # Check if line contains exclude patterns
  for exclude in "${EXCLUDE_PATTERNS[@]}"; do
    if echo "$line" | grep -qiE "$exclude"; then
      return 0  # Is false positive
    fi
  done
  
  # Check if error pattern appears in comment context
  # Remove comments and check if pattern still appears
  local line_no_comment=$(echo "$line" | sed 's/#.*$//')
  if echo "$line_no_comment" | grep -qiE "$pattern"; then
    # Pattern exists outside comment - check for exclude patterns nearby
    # For now, if exclude pattern exists anywhere in line, consider false positive
    return 1  # Not false positive (pattern in actual code/output)
  fi
  
  # If pattern only in comment, it's a false positive
  if echo "$line" | grep -qiE "$pattern" && ! echo "$line_no_comment" | grep -qiE "$pattern"; then
    return 0  # Is false positive (only in comment)
  fi
  
  return 1  # Not false positive
}

# Function to detect errors in output with context awareness
detect_errors() {
  local output="$1"
  local errors_found=0
  local error_lines=()
  
  # Split output into lines for context checking
  local line_num=0
  while IFS= read -r line || [ -n "$line" ]; do
    line_num=$((line_num + 1))
    
    # Check each error pattern
    for pattern in "${ERROR_PATTERNS[@]}"; do
      if echo "$line" | grep -qiE "$pattern"; then
        # Check if this is a false positive
        if ! is_false_positive_line "$line" "$pattern"; then
          errors_found=$((errors_found + 1))
          error_lines+=("Line $line_num: $line")
          # Only report first match per line
          break
        fi
      fi
    done
  done <<< "$output"
  
  # Return error lines
  if [ $errors_found -gt 0 ]; then
    # Print first 10 error lines
    echo "=== ERROR LINES DETECTED ===" >&2
    printf '%s\n' "${error_lines[@]}" | head -10 >&2
    return 1
  fi
  
  return 0
}

# Function to parse pytest JUnit XML if available
parse_pytest_junitxml() {
  local junit_file="$1"
  
  if [ ! -f "$junit_file" ]; then
    return 1
  fi
  
  # Extract failures and errors from JUnit XML
  # This is more reliable than parsing text output
  local failures=$(grep -o 'failures="[0-9]*"' "$junit_file" 2>/dev/null | grep -o '[0-9]*' | head -1 || echo "0")
  local errors=$(grep -o 'errors="[0-9]*"' "$junit_file" 2>/dev/null | grep -o '[0-9]*' | head -1 || echo "0")
  
  # Ensure we have numeric values
  failures=${failures:-0}
  errors=${errors:-0}
  
  if [ "$failures" -gt 0 ] || [ "$errors" -gt 0 ]; then
    error "JUnit XML reports: $failures failures, $errors errors"
    return 1
  fi
  
  return 0
}

# Function to check test results specifically
check_test_results() {
  local output="$1"
  local exit_code="$2"
  local command="$3"
  
  # Check for pytest-style test results
  if echo "$output" | grep -qE "pytest|test.*passed|test.*failed"; then
    # Try to find JUnit XML file (if pytest was run with --junitxml)
    local junit_file=""
    if echo "$command" | grep -qE "--junitxml"; then
      # Extract path from command - handle both --junitxml=path and --junitxml path formats
      junit_file=$(echo "$command" | sed -n 's/.*--junitxml=\([^ ]*\).*/\1/p')
      if [ -z "$junit_file" ]; then
        # Try space-separated format: --junitxml path
        junit_file=$(echo "$command" | sed -n 's/.*--junitxml \([^ ]*\).*/\1/p')
      fi
    else
      # Check common locations
      for loc in "junit.xml" "test-results.xml" "pytest.xml"; do
        if [ -f "$loc" ]; then
          junit_file="$loc"
          break
        fi
      done
    fi
    
    # Use JUnit XML if available (more reliable)
    if [ -n "$junit_file" ] && [ -f "$junit_file" ]; then
      if ! parse_pytest_junitxml "$junit_file"; then
        return 1
      fi
    else
      # Fall back to text parsing
      # Extract test counts with better regex
      local passed=$(echo "$output" | grep -oE "[0-9]+ passed" | grep -oE "[0-9]+" | head -1 || echo "0")
      local failed=$(echo "$output" | grep -oE "[0-9]+ failed" | grep -oE "[0-9]+" | head -1 || echo "0")
      local errors=$(echo "$output" | grep -oE "[0-9]+ error" | grep -oE "[0-9]+" | head -1 || echo "0")
      
      # Ensure we have numeric values
      passed=${passed:-0}
      failed=${failed:-0}
      errors=${errors:-0}
      
      # Also check for "FAILED" in test names (but exclude false positives)
      local failed_tests=0
      if echo "$output" | grep -qE "FAILED|failed"; then
        # Count actual FAILED test lines (not in comments or test names)
        failed_tests=$(echo "$output" | grep -E "FAILED|failed" | grep -vE "#.*FAILED|test.*failed|def.*failed" | wc -l || echo "0")
      fi
      
      if [ "$failed" -gt 0 ] || [ "$errors" -gt 0 ] || [ "$failed_tests" -gt 0 ]; then
        error "Test failures detected: $failed failed, $errors errors"
        return 1
      fi
      
      # Check for "no tests collected" or similar
      if echo "$output" | grep -qiE "no tests collected|no tests found"; then
        if [ "$exit_code" -ne 0 ]; then
          error "No tests found and exit code is $exit_code"
          return 1
        fi
      fi
      
      # If no tests passed and exit code is non-zero, that's suspicious
      if [ "$passed" -eq 0 ] && [ "$exit_code" -ne 0 ] && [ "$failed" -eq 0 ] && [ "$errors" -eq 0 ]; then
        # This might be a setup error, not a test failure
        warning "No tests executed and exit code is $exit_code (might be setup error)"
      fi
    fi
  fi
  
  return 0
}

# Trap handler for better error context
trap_handler() {
  local line_num=$1
  error "Error occurred at line $line_num in command execution"
}

# Main execution
main() {
  local command="$*"
  local exit_code=0
  local output=""
  local errors_detected=false
  
  # Set trap for error handling
  trap 'trap_handler $LINENO' ERR
  
  # Run command with unbuffered output, capturing both stdout and stderr
  # Use tee to simultaneously write to log and display
  # Use stdbuf for line buffering
  set +e  # Don't exit on error, we'll check exit code manually
  output=$(stdbuf -oL -eL bash -c "$command" 2>&1 | stdbuf -oL tee "$LOG_FILE")
  exit_code=$?
  set -e
  
  # Always show output (preserve full complexity per output-suppression rule)
  echo "$output"
  
  # Check exit code (with exceptions for commands that legitimately exit non-zero)
  if [ $exit_code -ne 0 ]; then
    if ! is_expected_nonzero "$command"; then
      error "Command exited with non-zero code: $exit_code"
      errors_detected=true
    else
      # Command is expected to exit non-zero (e.g., grep), but still check for actual errors
      warning "Command exited with non-zero code: $exit_code (expected for this command type)"
    fi
  fi
  
  # Check for error patterns in output
  if ! detect_errors "$output"; then
    error "Error patterns detected in command output"
    errors_detected=true
  fi
  
  # Check test results if this looks like a test run
  if ! check_test_results "$output" "$exit_code" "$command"; then
    errors_detected=true
  fi
  
  # Final decision
  if [ "$errors_detected" = true ]; then
    error "=========================================="
    error "ERROR DETECTION: Command execution failed"
    error "Exit code: $exit_code"
    error "Log file: $LOG_FILE"
    error "Command: $command"
    error "=========================================="
    exit 1
  else
    success "Command completed successfully"
    info "Log file: $LOG_FILE"
    exit 0
  fi
}

# Run main function
main "$@"
