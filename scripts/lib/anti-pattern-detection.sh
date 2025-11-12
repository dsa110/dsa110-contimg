#!/bin/bash
# Anti-Pattern Detection Library
# Detects common anti-patterns in code, process, and tests

set -e
set -o pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error() { echo -e "${RED}[ERROR]${NC} $1" >&2; return 1; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1" >&2; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
info() { echo -e "${BLUE}[INFO]${NC} $1"; }

# Process Pattern Detection

detect_dismissive_language() {
  local text="$1"
  local context="${2:-general}"
  
  # Dismissive language patterns
  local dismissive_patterns=(
    "doesn't matter"
    "doesn't affect"
    "not important"
    "not critical"
    "can ignore"
    "can skip"
    "edge case"
    "won't happen"
    "rare case"
    "unlikely"
    "probably fine"
    "should be ok"
    "might work"
    "good enough"
    "fix later"
    "technical debt"
    "known issue"
    "acceptable"
  )
  
  local found_patterns=()
  local text_lower=$(echo "$text" | tr '[:upper:]' '[:lower:]')
  
  for pattern in "${dismissive_patterns[@]}"; do
    if echo "$text_lower" | grep -qi "$pattern"; then
      found_patterns+=("$pattern")
    fi
  done
  
  if [ ${#found_patterns[@]} -gt 0 ]; then
    warning "Dismissive language detected in $context:"
    for pattern in "${found_patterns[@]}"; do
      echo "  - '$pattern'"
    done
    return 1
  fi
  
  return 0
}

detect_rationalizing_language() {
  local text="$1"
  
  local rationalizing_patterns=(
    "works in practice"
    "works for now"
    "seems to work"
    "appears fine"
    "looks ok"
    "probably fine"
    "should work"
    "might be ok"
  )
  
  local found_patterns=()
  local text_lower=$(echo "$text" | tr '[:upper:]' '[:lower:]')
  
  for pattern in "${rationalizing_patterns[@]}"; do
    if echo "$text_lower" | grep -qi "$pattern"; then
      found_patterns+=("$pattern")
    fi
  done
  
  if [ ${#found_patterns[@]} -gt 0 ]; then
    warning "Rationalizing language detected:"
    for pattern in "${found_patterns[@]}"; do
      echo "  - '$pattern'"
    done
    return 1
  fi
  
  return 0
}

# Code Pattern Detection

detect_magic_numbers() {
  local file="$1"
  local threshold="${2:-5}"  # Default: flag numbers > 5 digits or common magic numbers
  
  if [ ! -f "$file" ]; then
    return 0
  fi
  
  # Common magic numbers (without context)
  local magic_numbers=(
    " 3600"    # 1 hour in seconds
    " 86400"   # 1 day in seconds
    " 1024"    # Common size
    " 2048"    # Common size
    " 4096"    # Common size
  )
  
  local found_numbers=()
  
  # Check for large numbers without explanation
  while IFS= read -r line; do
    # Look for numbers > threshold digits without context
    if echo "$line" | grep -qE "[^0-9][0-9]{$threshold,}[^0-9]"; then
      # Check if it's in a comment or has context
      if ! echo "$line" | grep -qE "(//|#|/\*|TODO|FIXME|seconds|minutes|hours|days|bytes|kb|mb)"; then
        found_numbers+=("$line")
      fi
    fi
  done < "$file"
  
  if [ ${#found_numbers[@]} -gt 0 ]; then
    warning "Potential magic numbers in $file:"
    printf '%s\n' "${found_numbers[@]}" | head -5
    return 1
  fi
  
  return 0
}

detect_code_duplication() {
  local file="$1"
  local min_lines="${2:-5}"  # Minimum lines to consider duplication
  
  if [ ! -f "$file" ]; then
    return 0
  fi
  
  # Simple duplication detection: look for repeated blocks
  # This is a basic check - more sophisticated tools exist
  
  local temp_file=$(mktemp)
  local line_count=$(wc -l < "$file")
  
  # Check for repeated sequences
  if [ "$line_count" -gt $((min_lines * 2)) ]; then
    # Use a simple approach: check for identical consecutive blocks
    # More sophisticated: use tools like PMD, SonarQube, etc.
    warning "Code duplication check requires specialized tools (PMD, SonarQube)"
    warning "Manual review recommended for $file"
  fi
  
  rm -f "$temp_file"
  return 0
}

detect_complexity() {
  local file="$1"
  local max_complexity="${2:-10}"  # Cyclomatic complexity threshold
  
  if [ ! -f "$file" ]; then
    return 0
  fi
  
  # Basic complexity check: count control flow statements
  # More sophisticated: use tools like lizard, radon, etc.
  
  local complexity_indicators=(
    "if"
    "else"
    "elif"
    "for"
    "while"
    "case"
    "switch"
    "catch"
    "&&"
    "||"
  )
  
  local complexity_score=0
  
  for indicator in "${complexity_indicators[@]}"; do
    local count=$(grep -c "$indicator" "$file" 2>/dev/null || echo "0")
    complexity_score=$((complexity_score + count))
  done
  
  if [ "$complexity_score" -gt "$max_complexity" ]; then
    warning "High complexity detected in $file: $complexity_score (threshold: $max_complexity)"
    info "Consider refactoring to reduce complexity"
    return 1
  fi
  
  return 0
}

# Test Pattern Detection

detect_brittle_tests() {
  local test_file="$1"
  
  if [ ! -f "$test_file" ]; then
    return 0
  fi
  
  # Signs of brittle tests
  local brittle_patterns=(
    "sleep"
    "wait"
    "timeout"
    "setTimeout"
    "setInterval"
    "\.only"
    "\.skip"
    "TODO"
    "FIXME"
  )
  
  local found_patterns=()
  
  for pattern in "${brittle_patterns[@]}"; do
    if grep -q "$pattern" "$test_file" 2>/dev/null; then
      found_patterns+=("$pattern")
    fi
  done
  
  if [ ${#found_patterns[@]} -gt 0 ]; then
    warning "Potential brittle test patterns in $test_file:"
    for pattern in "${found_patterns[@]}"; do
      echo "  - '$pattern'"
    done
    return 1
  fi
  
  return 0
}

detect_happy_path_only() {
  local test_file="$1"
  
  if [ ! -f "$test_file" ]; then
    return 0
  fi
  
  # Check for error handling tests
  local error_keywords=(
    "error"
    "fail"
    "exception"
    "throw"
    "reject"
    "catch"
  )
  
  local has_error_tests=false
  
  for keyword in "${error_keywords[@]}"; do
    if grep -qi "$keyword" "$test_file" 2>/dev/null; then
      has_error_tests=true
      break
    fi
  done
  
  if [ "$has_error_tests" = false ]; then
    warning "Test file $test_file may only test happy path"
    info "Consider adding error case tests"
    return 1
  fi
  
  return 0
}

# Main Detection Functions

detect_process_anti_patterns() {
  local commit_msg="$1"
  local errors=0
  
  info "=== Process Anti-Pattern Detection ==="
  
  if ! detect_dismissive_language "$commit_msg" "commit message"; then
    errors=$((errors + 1))
  fi
  
  if ! detect_rationalizing_language "$commit_msg"; then
    errors=$((errors + 1))
  fi
  
  if [ $errors -gt 0 ]; then
    error "Process anti-patterns detected"
    return 1
  fi
  
  success "No process anti-patterns detected"
  return 0
}

detect_code_anti_patterns() {
  local files="${@:-*.sh *.js *.ts *.py}"
  local errors=0
  
  info "=== Code Anti-Pattern Detection ==="
  
  # This is a simplified version - in practice, use proper file discovery
  for file in $files; do
    if [ -f "$file" ]; then
      detect_magic_numbers "$file" || errors=$((errors + 1))
      detect_code_duplication "$file" || true  # Warning only
      detect_complexity "$file" || errors=$((errors + 1))
    fi
  done
  
  if [ $errors -gt 0 ]; then
    warning "Code anti-patterns detected (see warnings above)"
    return 1
  fi
  
  success "No code anti-patterns detected"
  return 0
}

detect_test_anti_patterns() {
  local test_files="${@:-*test*.sh *test*.js *test*.ts *spec*.js *spec*.ts}"
  local errors=0
  
  info "=== Test Anti-Pattern Detection ==="
  
  for file in $test_files; do
    if [ -f "$file" ]; then
      detect_brittle_tests "$file" || errors=$((errors + 1))
      detect_happy_path_only "$file" || errors=$((errors + 1))
    fi
  done
  
  if [ $errors -gt 0 ]; then
    warning "Test anti-patterns detected (see warnings above)"
    return 1
  fi
  
  success "No test anti-patterns detected"
  return 0
}

# Comprehensive Detection

detect_all_anti_patterns() {
  local commit_msg="${1:-}"
  local errors=0
  
  if [ -n "$commit_msg" ]; then
    if ! detect_process_anti_patterns "$commit_msg"; then
      errors=$((errors + 1))
    fi
  fi
  
  # Code and test detection would be called with proper file discovery
  # For now, this is a framework
  
  if [ $errors -gt 0 ]; then
    error "Anti-patterns detected - please review and fix"
    return 1
  fi
  
  success "All anti-pattern checks passed"
  return 0
}

