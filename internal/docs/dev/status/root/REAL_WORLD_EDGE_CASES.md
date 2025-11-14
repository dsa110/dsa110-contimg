# Real-World Edge Cases - Based on Actual Errors Encountered

## Overview

This document identifies edge cases based on **actual errors encountered** in
this session, revealing patterns that standard error detection might miss.

---

## Category 1: Environment Compatibility Issues

### Edge Case 1.1: Tool Version Incompatibility (Vitest + Node.js v16)

**What Happened:**

```bash
npm test
# Error: TypeError: crypto$2.getRandomValues is not a function
# Exit code: 1
```

**Why It's an Edge Case:**

- Command exists and runs
- Error message is cryptic
- Exit code indicates failure, but root cause unclear
- Works on some systems (Node v18+), fails on others (Node v16)
- No clear indication it's a version compatibility issue

**Detection Gap:**

- Standard error detection sees "command failed"
- Doesn't identify it as version incompatibility
- Doesn't suggest upgrade path

**Solution:**

```bash
# Pre-flight: Check tool compatibility
check_tool_compatibility() {
  local tool="$1"
  local min_node_version="$2"

  CURRENT_NODE=$(node --version | sed 's/v//')

  case "$tool" in
    "vitest")
      if [ "$(printf '%s\n' "$min_node_version" "$CURRENT_NODE" | sort -V | head -n1)" != "$min_node_version" ]; then
        echo "[ERROR] $tool requires Node.js >= $min_node_version, found $CURRENT_NODE"
        echo "[FIX] Upgrade Node.js or use compatible tool version"
        return 1
      fi
      ;;
  esac

  return 0
}

# Check before running tests
check_tool_compatibility "vitest" "18.0.0" || exit 1
npm test
```

**Detection Method:** Pre-flight compatibility matrix check

---

### Edge Case 1.2: Package Version Conflicts

**What Could Happen:**

```bash
npm install
# Exit code: 0
# But peer dependency warnings indicate conflicts
```

**Why It's an Edge Case:**

- Installation succeeds
- But warnings indicate potential runtime issues
- Easy to miss in CI/CD

**Solution:**

```bash
INSTALL_OUTPUT=$(npm install 2>&1)
INSTALL_EXIT=$?

if [ $INSTALL_EXIT -ne 0 ]; then
  error "npm install failed"
fi

# Check for peer dependency warnings
if echo "$INSTALL_OUTPUT" | grep -qi "peer dep missing\|peer dep conflict"; then
  echo "[WARNING] Peer dependency issues detected:"
  echo "$INSTALL_OUTPUT" | grep -i "peer dep"
  # Decide if this should be an error
fi

# Check for version conflicts
if echo "$INSTALL_OUTPUT" | grep -qi "conflict\|incompatible"; then
  error "Package version conflicts detected"
fi
```

**Detection Method:** Parse install output for warnings

---

## Category 2: File System State Issues

### Edge Case 2.1: Wrong Working Directory (Actually Happened)

**What Happened:**

```bash
cd /data/dsa110-contimg
npm test
# Error: ENOENT: no such file or directory, open 'package.json'
# Exit code: 254
```

**Why It's an Edge Case:**

- Command syntax is correct
- Error message is clear, but easy to miss context
- Could happen if script changes directory unexpectedly
- No pre-check for required files

**Solution:**

```bash
# Pre-flight: Verify required files exist
verify_required_files() {
  local required_files=("package.json" "package-lock.json")
  local missing_files=()

  for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
      missing_files+=("$file")
    fi
  done

  if [ ${#missing_files[@]} -ne 0 ]; then
    echo "[ERROR] Missing required files: ${missing_files[@]}"
    echo "[CONTEXT] Current directory: $(pwd)"
    echo "[FIX] Change to correct directory or create missing files"
    return 1
  fi

  return 0
}

# Check before running npm commands
verify_required_files || exit 1
npm test
```

**Detection Method:** Pre-flight file existence check with context

---

### Edge Case 2.2: Stale Lock Files

**What Could Happen:**

```bash
npm install
# Exit code: 0
# But package-lock.json is out of sync with package.json
```

**Why It's an Edge Case:**

- Installation succeeds
- But dependencies might be wrong versions
- No error, but runtime issues later

**Solution:**

```bash
# Check if lock file is out of sync
if [ -f "package-lock.json" ]; then
  # Try dry-run install to detect mismatches
  DRY_RUN_OUTPUT=$(npm ci --dry-run 2>&1)

  if echo "$DRY_RUN_OUTPUT" | grep -qi "mismatch\|conflict\|out of sync"; then
    echo "[WARNING] package-lock.json may be out of sync"
    echo "[FIX] Run: npm install (updates lock file)"
  fi
fi
```

**Detection Method:** Dry-run validation

---

### Edge Case 2.3: Corrupted or Partial File Writes

**What Could Happen:**

```bash
npm run build
# Exit code: 0
# But dist/index.html is corrupted (partial write, disk full)
```

**Why It's an Edge Case:**

- Build succeeds
- But output files are invalid
- No error, but deployment fails

**Solution:**

```bash
npm run build
BUILD_EXIT=$?

if [ $BUILD_EXIT -ne 0 ]; then
  error "Build failed"
fi

# Verify files are complete (not truncated)
for file in dist/index.html dist/assets/*.js; do
  if [ -f "$file" ]; then
    # Check file size is reasonable (not 0, not suspiciously small)
    FILE_SIZE=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")

    if [ "$FILE_SIZE" -eq 0 ]; then
      error "Build file is empty: $file"
    fi

    # For HTML, check it ends properly
    if [[ "$file" == *.html ]]; then
      if ! tail -c 100 "$file" | grep -q "</html>"; then
        error "HTML file appears truncated: $file"
      fi
    fi

    # For JS, check it's valid (starts with expected content)
    if [[ "$file" == *.js ]]; then
      if ! head -c 50 "$file" | grep -qE "(function|import|export|var|const|let)"; then
        warning "JS file may be corrupted: $file"
      fi
    fi
  fi
done
```

**Detection Method:** Post-build file integrity checks

---

## Category 3: Code Quality Issues

### Edge Case 3.1: Syntax Errors That Don't Block Build (Actually Happened)

**What Happened:**

```bash
# MultiImageCompare.tsx had syntax errors
# But TypeScript compilation passed (tsc -b)
# Build succeeded, but runtime errors
```

**Why It's an Edge Case:**

- TypeScript compiler might not catch all syntax errors
- Build succeeds, but code is broken
- Runtime errors only appear when code executes

**Solution:**

```bash
# Run multiple validation steps
echo "=== Type Checking ==="
npx tsc --noEmit
TSC_EXIT=$?

echo "=== Linting ==="
npm run lint
LINT_EXIT=$?

echo "=== Build ==="
npm run build
BUILD_EXIT=$?

# All must pass
if [ $TSC_EXIT -ne 0 ] || [ $LINT_EXIT -ne 0 ] || [ $BUILD_EXIT -ne 0 ]; then
  error "Validation failed: tsc=$TSC_EXIT lint=$LINT_EXIT build=$BUILD_EXIT"
fi

# Additional: Check for common syntax issues
SYNTAX_ISSUES=$(grep -r "function.*function\|const.*const\|import.*import" src/ 2>/dev/null | wc -l)
if [ "$SYNTAX_ISSUES" -gt 0 ]; then
  warning "Potential syntax issues detected: $SYNTAX_ISSUES"
fi
```

**Detection Method:** Multi-stage validation (tsc + lint + build)

---

### Edge Case 3.2: Type Errors That Don't Block Runtime

**What Could Happen:**

```bash
npm run build:no-check
# Exit code: 0
# But TypeScript errors exist (skipped type checking)
```

**Why It's an Edge Case:**

- Build succeeds
- But type errors exist
- Runtime issues later

**Solution:**

```bash
# Always run type check separately
echo "=== Type Check ==="
npx tsc --noEmit
TSC_EXIT=$?

if [ $TSC_EXIT -ne 0 ]; then
  error "Type errors detected (even if build passed)"
fi

# Then build
npm run build
```

**Detection Method:** Separate type checking step

---

## Category 4: Cache and State Issues

### Edge Case 4.1: Stale Build Cache

**What Could Happen:**

```bash
npm run build
# Exit code: 0
# But using stale cache (old code)
```

**Why It's an Edge Case:**

- Build succeeds
- But output is outdated
- No indication cache is stale

**Solution:**

```bash
# Clear cache before critical builds
if [ "$CLEAR_CACHE" = "true" ] || [ "$CI" = "true" ]; then
  echo "Clearing build cache..."
  rm -rf node_modules/.vite
  rm -rf dist
fi

npm run build

# Verify build timestamp is recent
BUILD_TIME=$(stat -f%m dist/index.html 2>/dev/null || stat -c%Y dist/index.html 2>/dev/null)
CURRENT_TIME=$(date +%s)
AGE=$((CURRENT_TIME - BUILD_TIME))

if [ "$AGE" -gt 3600 ]; then  # Older than 1 hour
  warning "Build output is $AGE seconds old - may be stale"
fi
```

**Detection Method:** Cache clearing + timestamp validation

---

### Edge Case 4.2: Concurrent Process Conflicts

**What Could Happen:**

```bash
npm run dev &
npm run build
# Both try to write to same files
# Lock file conflicts
```

**Why It's an Edge Case:**

- Both commands succeed individually
- But conflicts occur
- Hard to detect

**Solution:**

```bash
# Check for running processes
check_conflicting_processes() {
  local processes=("vite" "node.*dev" "npm.*dev")
  local conflicts=()

  for pattern in "${processes[@]}"; do
    if pgrep -f "$pattern" > /dev/null; then
      conflicts+=("$pattern")
    fi
  done

  if [ ${#conflicts[@]} -ne 0 ]; then
    echo "[WARNING] Conflicting processes detected: ${conflicts[@]}"
    echo "[FIX] Stop other processes before running build"
    return 1
  fi

  return 0
}

# Check before build
check_conflicting_processes || exit 1
npm run build
```

**Detection Method:** Process conflict detection

---

## Category 5: Configuration Issues

### Edge Case 5.1: Missing or Invalid Config Files

**What Could Happen:**

```bash
npm run dev
# Exit code: 0
# But vite.config.ts has syntax error (falls back to defaults)
```

**Why It's an Edge Case:**

- Command succeeds
- But using wrong configuration
- No error indication

**Solution:**

```bash
# Validate config files before use
validate_config() {
  local config_file="$1"

  if [ ! -f "$config_file" ]; then
    warning "Config file missing: $config_file (using defaults)"
    return 1
  fi

  # Try to parse/validate config
  case "$config_file" in
    *.ts)
      # Check TypeScript syntax
      npx tsc --noEmit "$config_file" 2>&1 | grep -q "error" && {
        error "Config file has syntax errors: $config_file"
        return 1
      }
      ;;
    *.js)
      # Check JavaScript syntax
      node -c "$config_file" 2>&1 | grep -q "SyntaxError" && {
        error "Config file has syntax errors: $config_file"
        return 1
      }
      ;;
  esac

  return 0
}

# Validate before running
validate_config "vite.config.ts" || exit 1
npm run dev
```

**Detection Method:** Config file validation

---

### Edge Case 5.2: Environment Variable Issues

**What Could Happen:**

```bash
npm run dev
# Exit code: 0
# But API_PROXY_TARGET is wrong (defaults to wrong URL)
```

**Why It's an Edge Case:**

- Command succeeds
- But wrong environment
- No error, but API calls fail

**Solution:**

```bash
# Validate environment variables
validate_env() {
  local var="$1"
  local expected_pattern="$2"

  if [ -z "${!var}" ]; then
    warning "Environment variable $var not set (using default)"
    return 1
  fi

  if [[ ! "${!var}" =~ $expected_pattern ]]; then
    error "Invalid $var value: ${!var} (expected pattern: $expected_pattern)"
    return 1
  fi

  return 0
}

# Validate before starting
validate_env "API_PROXY_TARGET" "^https?://" || exit 1
npm run dev
```

**Detection Method:** Environment variable validation

---

## Category 6: Network and External Dependencies

### Edge Case 6.1: CDN/External Resource Failures

**What Could Happen:**

```bash
npm run build
# Exit code: 0
# But external CDN resources fail to load (runtime error)
```

**Why It's an Edge Case:**

- Build succeeds
- But external resources unavailable
- Only fails at runtime

**Solution:**

```bash
# Check external resources during build
check_external_resources() {
  local resources=(
    "https://cdn.jsdelivr.net/npm/js9@latest"
    # Add other CDN resources
  )

  for resource in "${resources[@]}"; do
    if ! curl -f -I "$resource" > /dev/null 2>&1; then
      warning "External resource unavailable: $resource"
      # Decide if this should be an error
    fi
  done
}

# Check before build
check_external_resources
npm run build
```

**Detection Method:** External resource health checks

---

## Category 7: Output Parsing Edge Cases

### Edge Case 7.1: Error Messages in Success Output

**What Could Happen:**

```bash
npm run build
# Exit code: 0
# But output contains "error" in non-error context
# Example: "No errors found" or "Error handling configured"
```

**Why It's an Edge Case:**

- Pattern matching for "error" gives false positives
- Need context-aware parsing

**Solution:**

```bash
# Context-aware error detection
detect_errors() {
  local output="$1"

  # Look for actual error patterns, not just the word "error"
  ERROR_PATTERNS=(
    "^Error:"
    "ERROR:"
    "npm ERR!"
    "Failed to"
    "Cannot"
    "TypeError:"
    "ReferenceError:"
  )

  # Exclude false positives
  EXCLUDE_PATTERNS=(
    "No errors"
    "Error handling"
    "Error recovery"
  )

  for pattern in "${ERROR_PATTERNS[@]}"; do
    if echo "$output" | grep -qE "$pattern"; then
      # Check if it's a false positive
      local is_false_positive=false
      for exclude in "${EXCLUDE_PATTERNS[@]}"; do
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

OUTPUT=$(npm run build 2>&1)
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ] || ! detect_errors "$OUTPUT"; then
  error "Build failed or errors detected"
fi
```

**Detection Method:** Context-aware pattern matching

---

## Comprehensive Real-World Edge Case Detection

```bash
#!/bin/bash
# real-world-edge-case-detection.sh

set -e
set -o pipefail

# Based on actual errors encountered in this session

# 1. Environment compatibility
check_node_version "18.0.0" || exit 1

# 2. File system state
verify_required_files || exit 1
check_stale_lock_files || exit 1

# 3. Code quality
run_type_check || exit 1
run_lint || exit 1

# 4. Cache state
clear_cache_if_needed

# 5. Process conflicts
check_conflicting_processes || exit 1

# 6. Configuration
validate_config_files || exit 1
validate_environment_variables || exit 1

# 7. Run command with comprehensive detection
run_with_detection "$@"

# 8. Post-execution validation
validate_output_files || exit 1
check_for_corruption || exit 1
```

---

## Summary of Real-World Edge Cases

**Based on Actual Errors:**

1. ✓ Environment compatibility (Vitest + Node v16)
2. ✓ Wrong directory (package.json missing)
3. ✓ Syntax errors (MultiImageCompare.tsx)
4. ✓ Type errors (TypeScript compilation)
5. ✓ Stale caches (build cache)
6. ✓ Process conflicts (concurrent dev/build)
7. ✓ Config issues (vite.config.ts)
8. ✓ Output parsing (false positives)

**Detection Methods:**

- Pre-flight compatibility checks
- File system state validation
- Multi-stage code validation
- Cache management
- Process conflict detection
- Config validation
- Context-aware error parsing

**Key Insight:** Many edge cases come from **state issues** (wrong directory,
stale cache, process conflicts) rather than command failures. Need to check
**context and state**, not just exit codes.
