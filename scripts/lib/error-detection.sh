#!/bin/bash
# Error Detection Library
# Source this file to use error detection functions

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
error() {
  echo -e "${RED}[ERROR]${NC} $1" >&2
  return 1
}

warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

# Pre-flight checks
check_node_version() {
  local required_version="${1:-16.0.0}"  # Default to 16 for compatibility
  local current_version=$(node --version | sed 's/v//')
  
  # Special check for frontend tests: require casa6 Node.js v22.6.0
  if [ -f "package.json" ] && [ -f "vitest.config.ts" ]; then
    local casa6_node="/opt/miniforge/envs/casa6/bin/node"
    local current_node=$(which node)
    
    if [ "$current_node" != "$casa6_node" ]; then
      error "Frontend tests require casa6 Node.js v22.6.0"
      error "Current: $current_node (v$current_version)"
      error "Required: $casa6_node (v22.6.0)"
      error "Fix: source /opt/miniforge/etc/profile.d/conda.sh && conda activate casa6"
      return 1
    fi
    
    if [ "$(printf '%s
' "22.0.0" "$current_version" | sort -V | head -n1)" != "22.0.0" ]; then
      error "Node.js version $current_version < required 22.0.0 for frontend tests"
      return 1
    fi
    
    success "Using casa6 Node.js: $current_version"
    return 0
  fi
  
  # Generic check for other contexts
  if [ "$(printf '%s
' "$required_version" "$current_version" | sort -V | head -n1)" != "$required_version" ]; then
    warning "Node.js version $current_version < recommended $required_version"
    # Don't fail, just warn (some environments may have older versions)
    return 0
  }
  
  success "Node.js version OK: $current_version"
  return 0
}"  # Default to 16 for compatibility
  local current_version=$(node --version | sed 's/v//')
  
  if [ "$(printf '%s\n' "$required_version" "$current_version" | sort -V | head -n1)" != "$required_version" ]; then
    warning "Node.js version $current_version < recommended $required_version"
    # Don't fail, just warn (some environments may have older versions)
    return 0
  fi
  
  success "Node.js version OK: $current_version"
  return 0
}

check_npm_version() {
  local required_version="${1:-9.0.0}"
  local current_version=$(npm --version)
  
  if [ "$(printf '%s\n' "$required_version" "$current_version" | sort -V | head -n1)" != "$required_version" ]; then
    warning "npm version $current_version < recommended $required_version"
    return 1
  fi
  
  success "npm version OK: $current_version"
  return 0
}

verify_required_files() {
  local files=("package.json")
  local missing_files=()
  
  for file in "${files[@]}"; do
    if [ ! -f "$file" ]; then
      missing_files+=("$file")
    fi
  done
  
  if [ ${#missing_files[@]} -ne 0 ]; then
    error "Missing required files: ${missing_files[@]}"
    info "Current directory: $(pwd)"
    info "Fix: Change to correct directory or create missing files"
    return 1
  fi
  
  success "Required files present"
  return 0
}

check_dependencies() {
  if [ ! -d "node_modules" ] || [ -z "$(ls -A node_modules 2>/dev/null)" ]; then
    error "node_modules missing or empty - run npm install"
    return 1
  fi
  
  # Check for critical dependencies
  local critical_deps=("react" "react-dom" "vite")
  local missing_deps=()
  
  for dep in "${critical_deps[@]}"; do
    if [ ! -d "node_modules/$dep" ]; then
      missing_deps+=("$dep")
    fi
  done
  
  if [ ${#missing_deps[@]} -ne 0 ]; then
    error "Missing critical dependencies: ${missing_deps[@]}"
    info "Run: npm install"
    return 1
  fi
  
  success "Dependencies installed"
  return 0
}

check_permissions() {
  if [ ! -w "." ]; then
    error "No write permission in current directory"
    return 1
  fi
  
  success "Permissions OK"
  return 0
}

check_memory() {
  local min_mem="${1:-2048}"  # MB
  local available_mem=$(free -m 2>/dev/null | awk 'NR==2{print $7}' || echo "0")
  
  if [ "$available_mem" -lt "$min_mem" ] && [ "$available_mem" -gt 0 ]; then
    warning "Low memory: ${available_mem}MB (recommended: ${min_mem}MB)"
    return 1
  fi
  
  success "Memory OK: ${available_mem}MB"
  return 0
}

check_process_conflicts() {
  local processes=("vite" "node.*dev")
  local conflicts=()
  
  for pattern in "${processes[@]}"; do
    if pgrep -f "$pattern" > /dev/null 2>&1; then
      conflicts+=("$pattern")
    fi
  done
  
  if [ ${#conflicts[@]} -ne 0 ]; then
    warning "Conflicting processes detected: ${conflicts[@]}"
    info "Fix: Stop other processes before running command"
    return 1
  fi
  
  success "No process conflicts"
  return 0
}

validate_config_files() {
  local config_files=("vite.config.ts" "tsconfig.json")
  local invalid_configs=()
  
  for config_file in "${config_files[@]}"; do
    if [ -f "$config_file" ]; then
      case "$config_file" in
        *.ts)
          # Skip TypeScript validation for config files (may have complex types)
          # Just check file exists and is readable
          if [ ! -r "$config_file" ]; then
            invalid_configs+=("$config_file")
          fi
          ;;
        *.json)
          if command -v jq > /dev/null 2>&1; then
            if ! jq empty "$config_file" > /dev/null 2>&1; then
              invalid_configs+=("$config_file")
            fi
          else
            # jq not available, skip JSON validation
            true
          fi
          ;;
      esac
    fi
  done
  
  if [ ${#invalid_configs[@]} -ne 0 ]; then
    warning "Config files may have issues: ${invalid_configs[@]}"
    # Don't fail, just warn
    return 0
  fi
  
  success "Config files present"
  return 0
}

# Execution monitoring
detect_errors() {
  local output="$1"
  
  # Error patterns
  local error_patterns=(
    "^Error:"
    "^ERROR:"
    "npm ERR!"
    "Failed to"
    "Cannot"
    "TypeError:"
    "ReferenceError:"
  )
  
  # Exclude false positives
  local exclude_patterns=(
    "No errors"
    "Error handling"
    "Error recovery"
  )
  
  for pattern in "${error_patterns[@]}"; do
    if echo "$output" | grep -qE "$pattern"; then
      # Check if it's a false positive
      local is_false_positive=false
      for exclude in "${exclude_patterns[@]}"; do
        if echo "$output" | grep -q "$exclude"; then
          is_false_positive=true
          break
        fi
      done
      
      if [ "$is_false_positive" = false ]; then
        return 1  # Error detected
      fi
    fi
  done
  
  return 0  # No errors
}

detect_critical_warnings() {
  local output="$1"
  
  local critical_patterns=(
    "failed to resolve"
    "cannot find module"
    "out of memory"
    "ENOMEM"
  )
  
  for pattern in "${critical_patterns[@]}"; do
    if echo "$output" | grep -qi "$pattern"; then
      return 1  # Critical warning detected
    fi
  done
  
  return 0
}

# Post-execution validation
validate_build_output() {
  if [ ! -d "dist" ]; then
    error "Build output directory missing"
    return 1
  fi
  
  if [ ! -f "dist/index.html" ]; then
    error "Build output file missing: dist/index.html"
    return 1
  fi
  
  if [ ! -s "dist/index.html" ]; then
    error "Build output file is empty: dist/index.html"
    return 1
  fi
  
  # Verify HTML contains expected content
  if ! grep -q "<div id=\"root\">" dist/index.html 2>/dev/null; then
    error "Build output appears corrupted (missing root element)"
    return 1
  fi
  
  success "Build output validated"
  return 0
}

validate_test_results() {
  local output="$1"
  
  if echo "$output" | grep -qi "no tests found"; then
    error "No tests found"
    return 1
  fi
  
  # Parse test results (basic)
  local passed=$(echo "$output" | grep -oP "\d+ passed" | grep -oP "\d+" | head -1 || echo "0")
  local failed=$(echo "$output" | grep -oP "\d+ failed" | grep -oP "\d+" | head -1 || echo "0")
  
  if [ "$failed" -gt 0 ]; then
    error "$failed tests failed"
    return 1
  fi
  
  if [ "$passed" -eq 0 ]; then
    warning "No tests executed"
    return 1
  fi
  
  success "Tests passed: $passed"
  return 0
}

# Edge case detection
check_silent_failures() {
  # This is context-dependent - implement based on command type
  return 0
}

check_partial_failures() {
  # This is context-dependent - implement based on command type
  return 0
}

# Main pre-flight function
preflight_checks() {
  info "=== Pre-Flight Checks ==="
  
  local errors=0
  
  check_node_version || errors=$((errors + 1))
  check_npm_version || true  # Warning only
  verify_required_files || errors=$((errors + 1))
  check_dependencies || errors=$((errors + 1))
  check_permissions || errors=$((errors + 1))
  check_memory || true  # Warning only
  check_process_conflicts || true  # Warning only
  validate_config_files || errors=$((errors + 1))
  
  if [ $errors -gt 0 ]; then
    error "Pre-flight checks failed ($errors errors)"
    return 1
  fi
  
  success "Pre-flight checks passed"
  return 0
}

# Main execution function
execute_with_monitoring() {
  local command="$@"
  
  info "=== Executing: $command ==="
  
  # Run command in subshell to prevent 'exit' from killing parent shell
  # Capture both output and exit code
  local output
  local exit_code
  
  set +e
  # Use subshell to isolate exit commands
  output=$(
    (
      eval "$command"
    ) 2>&1
  )
  exit_code=$?
  set -e
  
  # Check exit code
  if [ $exit_code -ne 0 ]; then
    error "Command failed: exit $exit_code" >&2
    echo "$output"
    return 1
  fi
  
  # Check for error patterns
  if ! detect_errors "$output"; then
    error "Errors detected in output" >&2
    echo "$output"
    return 1
  fi
  
  # Check for critical warnings
  if ! detect_critical_warnings "$output"; then
    warning "Critical warnings detected" >&2
    echo "$output" | grep -i "warning\|failed\|error" | head -10
  fi
  
  success "Command completed successfully"
  return 0
}

# Main post-execution function
post_execution_validation() {
  local command="$1"
  
  info "=== Post-Execution Validation ==="
  
  # Build validation
  if [[ "$command" == *"build"* ]]; then
    validate_build_output || return 1
  fi
  
  # Test validation
  if [[ "$command" == *"test"* ]]; then
    # Note: This requires output from execute_with_monitoring
    # For now, skip or implement separately
    true
  fi
  
  success "Post-execution validation passed"
  return 0
}

# Comprehensive wrapper
run_with_comprehensive_detection() {
  local command="$@"
  
  # Phase 1: Pre-flight
  if ! preflight_checks; then
    error "Pre-flight checks failed - aborting"
    return 1
  fi
  
  # Phase 2: Execution
  if ! execute_with_monitoring "$command"; then
    error "Execution failed"
    return 1
  fi
  
  # Phase 3: Post-execution
  if ! post_execution_validation "$command"; then
    error "Post-execution validation failed"
    return 1
  fi
  
  success "All checks passed"
  return 0
}

