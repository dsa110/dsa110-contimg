#!/bin/bash
# Generic environment dependency checker
# Can be used for any dependency (Node.js, Python, tools, paths, etc.)

set -e

# Usage: check_environment_dependency <name> <check-command> <expected-value> <error-message> <fix-instructions>
# Example: check_environment_dependency "Node.js" "node --version" "v22.6.0" "Wrong Node.js version" "conda activate casa6"

check_environment_dependency() {
  local name="$1"
  local check_command="$2"
  local expected_value="$3"
  local error_message="${4:-Wrong $name}"
  local fix_instructions="${5:-Please configure $name correctly}"
  
  if ! command -v "$(echo "$check_command" | awk '{print $1}')" > /dev/null 2>&1; then
    error "$name is not available"
    error "Fix: $fix_instructions"
    return 1
  fi
  
  local current_value
  if ! current_value=$(eval "$check_command" 2>&1); then
    error "Failed to check $name"
    error "Fix: $fix_instructions"
    return 1
  fi
  
  current_value=$(echo "$current_value" | tr -d '\n' | xargs)
  
  if [ "$current_value" != "$expected_value" ]; then
    error "$error_message"
    error "Current: $current_value"
    error "Expected: $expected_value"
    error "Fix: $fix_instructions"
    return 1
  fi
  
  success "$name OK: $current_value"
  return 0
}

# Usage: check_path_dependency <name> <which-command> <expected-path> <error-message> <fix-instructions>
check_path_dependency() {
  local name="$1"
  local which_command="$2"
  local expected_path="$3"
  local error_message="${4:-Wrong $name path}"
  local fix_instructions="${5:-Please configure $name correctly}"
  
  if ! command -v "$which_command" > /dev/null 2>&1; then
    error "$name is not available"
    error "Fix: $fix_instructions"
    return 1
  fi
  
  local current_path
  current_path=$(which "$which_command")
  
  if [ "$current_path" != "$expected_path" ]; then
    error "$error_message"
    error "Current: $current_path"
    error "Expected: $expected_path"
    error "Fix: $fix_instructions"
    return 1
  fi
  
  success "$name path OK: $current_path"
  return 0
}

# Usage: check_version_dependency <name> <version-command> <min-version> <error-message> <fix-instructions>
check_version_dependency() {
  local name="$1"
  local version_command="$2"
  local min_version="$3"
  local error_message="${4:-$name version too old}"
  local fix_instructions="${5:-Please upgrade $name}"
  
  if ! command -v "$(echo "$version_command" | awk '{print $1}')" > /dev/null 2>&1; then
    error "$name is not available"
    error "Fix: $fix_instructions"
    return 1
  fi
  
  local current_version
  if ! current_version=$(eval "$version_command" 2>&1); then
    error "Failed to check $name version"
    error "Fix: $fix_instructions"
    return 1
  fi
  
  # Remove 'v' prefix if present
  current_version=$(echo "$current_version" | sed 's/^v//' | tr -d '\n' | xargs)
  min_version=$(echo "$min_version" | sed 's/^v//' | tr -d '\n' | xargs)
  
  # Compare versions (simple numeric comparison)
  if [ "$(printf '%s\n' "$min_version" "$current_version" | sort -V | head -n1)" != "$min_version" ]; then
    error "$error_message"
    error "Current: $current_version"
    error "Required: $min_version+"
    error "Fix: $fix_instructions"
    return 1
  fi
  
  success "$name version OK: $current_version"
  return 0
}

# Export functions for use in other scripts
export -f check_environment_dependency
export -f check_path_dependency
export -f check_version_dependency

