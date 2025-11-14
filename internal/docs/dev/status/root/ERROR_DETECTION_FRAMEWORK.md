# Comprehensive Error Detection Framework

## Overview

A systematic approach to detecting, handling, and preventing errors in software
development workflows, based on real-world experience and edge case analysis.

---

## Core Principles

### Principle 1: Multi-Layer Detection

Errors can occur at multiple levels - don't rely on a single detection method.

### Principle 2: State-Aware Validation

Check context and state, not just exit codes. Many failures are state-related.

### Principle 3: Fail Fast, Fail Clearly

Detect errors early with clear, actionable messages.

### Principle 4: Context Preservation

When errors occur, preserve full context for diagnosis.

### Principle 5: Continuous Improvement

Learn from mistakes and update detection mechanisms.

---

## Error Detection Layers

### Layer 1: Pre-Flight Checks (Before Execution)

**Purpose:** Catch errors before they occur

**Checks:**

- Environment compatibility (Node.js version, tool versions)
- File system state (required files exist, correct directory)
- Dependencies (node_modules present, lock files in sync)
- Permissions (write access, file permissions)
- Resources (memory, disk space)
- Process conflicts (other processes running)
- Configuration (config files valid, env vars set)

**Example:**

```bash
# Pre-flight validation
check_node_version "18.0.0" || exit 1
verify_required_files || exit 1
check_dependencies || exit 1
validate_permissions || exit 1
check_resources || exit 1
check_process_conflicts || exit 1
validate_config || exit 1
```

---

### Layer 2: Execution Monitoring (During Execution)

**Purpose:** Detect errors as they occur

**Methods:**

- Exit code monitoring
- Error prefix detection (npm ERR!, ERROR:, etc.)
- Error code parsing (ENOENT, EACCES, etc.)
- Output pattern matching
- Resource monitoring (memory, CPU)
- Timeout detection

**Example:**

```bash
# Execute with monitoring
OUTPUT=$(command 2>&1)
EXIT_CODE=$?

# Check exit code
if [ $EXIT_CODE -ne 0 ]; then
  error "Command failed: exit $EXIT_CODE"
fi

# Check for error patterns
if echo "$OUTPUT" | grep -qE "(npm ERR!|ERROR:|Failed)"; then
  error "Error detected in output"
fi
```

---

### Layer 3: Post-Execution Validation (After Execution)

**Purpose:** Catch silent failures and validate results

**Checks:**

- Output file validation (files exist, not empty, not corrupted)
- Test result parsing (tests actually ran, passed count)
- Warning detection (critical warnings in output)
- Build artifact validation (dist files valid)
- API health checks (server responding)
- Resource cleanup (no leaks, temp files cleaned)

**Example:**

```bash
# Post-execution validation
if [[ "$COMMAND" == *"build"* ]]; then
  validate_build_output || exit 1
fi

if [[ "$COMMAND" == *"test"* ]]; then
  validate_test_results || exit 1
fi

check_for_warnings || exit 1
```

---

### Layer 4: Edge Case Detection (Special Scenarios)

**Purpose:** Catch edge cases that standard detection misses

**Scenarios:**

- Silent failures (exit 0, but wrong)
- Partial failures (some succeed, some fail)
- Race conditions (timing issues)
- Cache issues (stale cache)
- Network issues (API not accessible)
- File system issues (permissions, corruption)

**Example:**

```bash
# Edge case detection
check_silent_failures || exit 1
check_partial_failures || exit 1
check_race_conditions || exit 1
check_cache_issues || exit 1
check_network_issues || exit 1
check_file_system_issues || exit 1
```

---

## Error Recognition Mechanisms

### Mechanism 1: Exit Code Analysis

**What:** Process exit code (0 = success, non-zero = failure)

**Detection:**

```bash
command
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
  echo "[ERROR] Command failed: exit $EXIT_CODE"
fi
```

**Edge Cases:**

- Exit code 0 but wrong (silent failure)
- Exit code non-zero but expected (some commands)

**Solution:** Combine with output analysis

---

### Mechanism 2: Error Prefix Detection

**What:** Pattern matching for error prefixes (npm ERR!, ERROR:, etc.)

**Detection:**

```bash
if echo "$OUTPUT" | grep -qE "(npm ERR!|ERROR:|Failed)"; then
  echo "[ERROR] Error detected in output"
fi
```

**Edge Cases:**

- False positives ("No errors" contains "error")
- Context-dependent errors

**Solution:** Context-aware pattern matching

---

### Mechanism 3: Error Code Parsing

**What:** Parse specific error codes (ENOENT, EACCES, etc.)

**Detection:**

```bash
ERROR_CODE=$(echo "$OUTPUT" | grep "npm ERR! code" | awk '{print $3}')

case "$ERROR_CODE" in
  "ENOENT")
    echo "[ERROR] File not found"
    ;;
  "EACCES")
    echo "[ERROR] Permission denied"
    ;;
esac
```

**Edge Cases:**

- Error code not in expected format
- Multiple error codes

**Solution:** Robust parsing with fallbacks

---

### Mechanism 4: Output Pattern Matching

**What:** Match patterns in output (warnings, critical messages)

**Detection:**

```bash
CRITICAL_PATTERNS=("failed to resolve" "cannot find module" "out of memory")

for pattern in "${CRITICAL_PATTERNS[@]}"; do
  if echo "$OUTPUT" | grep -qi "$pattern"; then
    echo "[ERROR] Critical issue: $pattern"
  fi
done
```

**Edge Cases:**

- False positives
- Pattern variations

**Solution:** Context-aware matching with exclusions

---

### Mechanism 5: State Validation

**What:** Check file system state, process state, environment state

**Detection:**

```bash
# File system state
if [ ! -f "package.json" ]; then
  echo "[ERROR] Missing required file: package.json"
fi

# Process state
if pgrep -f "vite" > /dev/null; then
  echo "[WARNING] Conflicting process detected: vite"
fi

# Environment state
if [ -z "$NODE_ENV" ]; then
  echo "[WARNING] NODE_ENV not set"
fi
```

**Edge Cases:**

- State changes between checks
- Race conditions

**Solution:** Atomic checks, locking mechanisms

---

## Self-Correction Protocol

### Step 1: STOP

**Action:** Stop immediately when error detected **Why:** Prevent compounding
mistakes

### Step 2: LOG

**Action:** Log mistake with full context **Format:**

```
[MISTAKE] Phase X.Y: Description
- What happened: [details]
- Impact: [time wasted, incorrect result]
- Error: [exact error message]
- Root cause: [why it happened]
- Correction: [what was done to fix]
- Prevention: [how to avoid in future]
```

### Step 3: ASSESS

**Action:** Evaluate impact and severity **Consider:**

- Time wasted
- Data loss/corruption
- Blocker vs. warning
- Scope of impact

### Step 4: FIX

**Action:** Correct the issue immediately **Principles:**

- Fix root cause, not symptoms
- Verify fix works
- Don't compound mistakes

### Step 5: VERIFY

**Action:** Confirm fix resolved the issue **Methods:**

- Re-run command
- Check output
- Validate state

### Step 6: LEARN

**Action:** Update protocol to prevent recurrence **Actions:**

- Update checkpoints
- Add prevention strategies
- Document learnings

---

## Implementation Framework

### Phase 1: Pre-Flight Validation

```bash
preflight_checks() {
  echo "=== Pre-Flight Checks ==="

  # Environment
  check_node_version || return 1
  check_npm_version || return 1

  # File system
  verify_required_files || return 1
  check_permissions || return 1

  # Dependencies
  check_dependencies || return 1
  check_lock_file_sync || return 1

  # Resources
  check_memory || return 1
  check_disk_space || return 1

  # Process conflicts
  check_process_conflicts || return 1

  # Configuration
  validate_config_files || return 1
  validate_environment_variables || return 1

  echo "[SUCCESS] Pre-flight checks passed"
  return 0
}
```

---

### Phase 2: Execution with Monitoring

```bash
execute_with_monitoring() {
  local command="$@"

  echo "=== Executing: $command ==="

  # Capture output
  OUTPUT=$(eval "$command" 2>&1)
  EXIT_CODE=$?

  # Check exit code
  if [ $EXIT_CODE -ne 0 ]; then
    error "Command failed: exit $EXIT_CODE"
    return 1
  fi

  # Check for error patterns
  if detect_errors "$OUTPUT"; then
    error "Errors detected in output"
    return 1
  fi

  # Check for warnings
  if detect_critical_warnings "$OUTPUT"; then
    warning "Critical warnings detected"
    # Decide if this should be an error
  fi

  echo "[SUCCESS] Command completed"
  return 0
}
```

---

### Phase 3: Post-Execution Validation

```bash
post_execution_validation() {
  local command="$@"

  echo "=== Post-Execution Validation ==="

  # Build validation
  if [[ "$command" == *"build"* ]]; then
    validate_build_output || return 1
  fi

  # Test validation
  if [[ "$command" == *"test"* ]]; then
    validate_test_results || return 1
  fi

  # Server validation
  if [[ "$command" == *"dev"* ]]; then
    validate_server_ready || return 1
  fi

  # File integrity
  check_file_integrity || return 1

  echo "[SUCCESS] Post-execution validation passed"
  return 0
}
```

---

### Phase 4: Edge Case Detection

```bash
edge_case_detection() {
  echo "=== Edge Case Detection ==="

  # Silent failures
  check_silent_failures || return 1

  # Partial failures
  check_partial_failures || return 1

  # Race conditions
  check_race_conditions || return 1

  # Cache issues
  check_cache_issues || return 1

  # Network issues
  check_network_issues || return 1

  # File system issues
  check_file_system_issues || return 1

  echo "[SUCCESS] Edge case checks passed"
  return 0
}
```

---

## Complete Workflow

### Main Execution Function

```bash
run_with_comprehensive_detection() {
  local command="$@"

  # Phase 1: Pre-flight
  preflight_checks || {
    error "Pre-flight checks failed"
    return 1
  }

  # Phase 2: Execution
  execute_with_monitoring "$command" || {
    error "Execution failed"
    return 1
  }

  # Phase 3: Post-execution
  post_execution_validation "$command" || {
    error "Post-execution validation failed"
    return 1
  }

  # Phase 4: Edge cases
  edge_case_detection || {
    warning "Edge case issues detected"
    # Decide if this should be an error
  }

  echo "[SUCCESS] All checks passed"
  return 0
}
```

---

## Usage Examples

### Example 1: Build Command

```bash
run_with_comprehensive_detection "npm run build"
```

**What Happens:**

1. Pre-flight: Check Node version, deps, permissions
2. Execute: Run build, monitor output
3. Validate: Check dist files exist, not empty
4. Edge cases: Check for stale cache, corruption

---

### Example 2: Test Command

```bash
run_with_comprehensive_detection "npm test"
```

**What Happens:**

1. Pre-flight: Check test environment, deps
2. Execute: Run tests, monitor output
3. Validate: Parse test results, check pass count
4. Edge cases: Check for skipped tests, partial failures

---

### Example 3: Dev Server

```bash
run_with_comprehensive_detection "npm run dev"
```

**What Happens:**

1. Pre-flight: Check port availability, process conflicts
2. Execute: Start server, monitor startup
3. Validate: Check server responds, correct port
4. Edge cases: Check for race conditions, timing issues

---

## Error Categories & Detection Strategies

### Category 1: Command Failures

**Detection:** Exit codes, error prefixes **Solution:** Standard error handling

### Category 2: Silent Failures

**Detection:** Post-execution validation, output analysis **Solution:** Result
validation, health checks

### Category 3: State Issues

**Detection:** Pre-flight checks, state validation **Solution:** State
management, cleanup

### Category 4: Environment Issues

**Detection:** Compatibility checks, version validation **Solution:**
Environment setup, version management

### Category 5: Resource Issues

**Detection:** Resource monitoring, pre-flight checks **Solution:** Resource
management, cleanup

### Category 6: Timing Issues

**Detection:** Timeout detection, readiness checks **Solution:** Wait
mechanisms, retry logic

---

## Best Practices

### 1. Always Check Exit Codes

```bash
command || error "Command failed"
```

### 2. Parse Output for Errors

```bash
OUTPUT=$(command 2>&1)
if echo "$OUTPUT" | grep -q "ERROR"; then
  error "Error in output"
fi
```

### 3. Validate Results, Not Just Success

```bash
command
# Don't just check exit code - validate output
validate_output || error "Output invalid"
```

### 4. Check State Before Commands

```bash
# Pre-flight checks
verify_environment || exit 1
verify_files || exit 1
command
```

### 5. Log Everything

```bash
# Log command, output, exit code, context
log_command "$command" "$output" "$EXIT_CODE" "$(pwd)"
```

### 6. Fail Fast, Fail Clearly

```bash
# Clear error messages with context
error "Command failed: $command (exit $EXIT_CODE, dir: $(pwd))"
```

### 7. Learn from Mistakes

```bash
# Log mistakes, update protocol
log_mistake "$description" "$impact" "$prevention"
update_protocol "$prevention"
```

---

## Tools & Integration

### Static Analysis Tools

- ShellCheck (shell scripts)
- ESLint (JavaScript/TypeScript)
- TypeScript Compiler (type checking)

### Runtime Monitoring

- Error detection wrappers
- Health check scripts
- Resource monitoring

### CI/CD Integration

- Pre-commit hooks
- GitHub Actions
- GitLab CI

### Production Monitoring

- Sentry (error tracking)
- Datadog (APM)
- Custom monitoring scripts

---

## Summary

**Framework Components:**

1. ✓ Multi-layer detection (pre-flight, execution, post-execution, edge cases)
2. ✓ Multiple recognition mechanisms (exit codes, patterns, state)
3. ✓ Self-correction protocol (stop, log, assess, fix, verify, learn)
4. ✓ Comprehensive workflow (all phases integrated)
5. ✓ Real-world edge cases (based on actual experience)

**Key Principles:**

- Check state, not just exit codes
- Multiple detection layers
- Context-aware validation
- Continuous improvement

**Next Steps:**

- Implement framework in scripts
- Integrate into CI/CD
- Monitor and improve
