#!/bin/bash
# Example error detection wrapper

run_with_detection() {
  local cmd="$@"
  echo "Running: $cmd"
  
  output=$(eval "$cmd" 2>&1)
  exit_code=$?
  
  if [ $exit_code -ne 0 ]; then
    echo "[ERROR] Command failed (exit code: $exit_code)"
    
    # Detect npm errors
    if echo "$output" | grep -q "npm ERR!"; then
      error_code=$(echo "$output" | grep "npm ERR! code" | awk '{print $3}' || echo "unknown")
      echo "[ERROR] npm error code: $error_code"
      
      # Auto-fix: wrong directory
      if [ "$error_code" = "ENOENT" ]; then
        if echo "$output" | grep -q "package.json" && [[ ! "$PWD" =~ "frontend" ]]; then
          echo "[FIX] Wrong directory detected, changing to frontend/"
          cd frontend 2>/dev/null && echo "[FIX] Changed to: $(pwd)"
        fi
      fi
    fi
    
    return $exit_code
  fi
  
  return 0
}

# Usage example
# run_with_detection "npm test"
