# Environment Dependency Enforcement Framework

## Overview

A zero-bypass prevention pattern for environment dependency issues that can be applied to any non-obvious prerequisite or configuration requirement.

## Core Principle

**Enforce environment dependencies automatically at the lowest possible level, rather than relying on documentation or human memory.**

## Pattern Structure

### 1. Identify the Dependency
- What environment/configuration is required?
- What happens if it's wrong? (silent failure vs. obvious error)
- Where does the dependency manifest? (startup, runtime, tests)

### 2. Implement Multi-Layer Checks

#### Layer 1: Lowest-Level Check (Cannot Be Bypassed)
- **Location**: Configuration file that loads first (e.g., `vitest.config.ts`, `vite.config.ts`, `jest.config.js`)
- **Purpose**: Runs before any tool/library loads
- **Behavior**: Check dependency, exit with clear error if wrong
- **Effectiveness**: 100% (cannot be bypassed)

#### Layer 2: Secondary Check (Before Execution)
- **Location**: Setup file that runs before code execution (e.g., `setup.ts`, `setupFiles`)
- **Purpose**: Second layer protection
- **Behavior**: Verify dependency again before tests/code run
- **Effectiveness**: 100% (catches any bypass of Layer 1)

#### Layer 3: Integration Check (Command Level)
- **Location**: npm scripts, Makefile targets, wrapper scripts
- **Purpose**: Enforce at command invocation level
- **Behavior**: Check dependency before executing command
- **Effectiveness**: 95% (can be bypassed by direct tool calls, but Layer 1 catches it)

#### Layer 4: CI/CD Enforcement
- **Location**: GitHub Actions, GitLab CI, Jenkins pipelines
- **Purpose**: Prevent merging/deploying with wrong environment
- **Behavior**: Verify dependency in CI/CD pipeline
- **Effectiveness**: 100% (enforced in automated pipeline)

#### Layer 5: Improved Error Messages
- **Location**: Error handlers, try-catch blocks, fallback checks
- **Purpose**: Make root cause obvious if checks somehow fail
- **Behavior**: Error messages explicitly mention dependency requirement
- **Effectiveness**: 100% (makes debugging trivial)

### 3. Error Message Template

```typescript
console.error('\n❌ ERROR: [Tool/System] requires [Dependency]');
console.error(`   Current: ${currentValue}`);
console.error(`   Required: ${requiredValue}`);
console.error('\n   Fix: [Clear instructions]\n');
process.exit(1);
```

## Application Examples

### Example 1: Node.js Version (Current Implementation)
- **Dependency**: casa6 Node.js v22.6.0
- **Layer 1**: `vitest.config.ts` check
- **Layer 2**: `src/test/setup.ts` check
- **Layer 3**: `npm test` script integration
- **Layer 4**: GitHub Actions workflow
- **Layer 5**: Improved crypto error messages

### Example 2: Python Version
- **Dependency**: casa6 Python 3.x
- **Layer 1**: `pytest.ini` or `conftest.py` check
- **Layer 2**: Test fixture that verifies Python path
- **Layer 3**: Makefile target that checks Python
- **Layer 4**: CI/CD Python version check
- **Layer 5**: Import error messages point to Python version

### Example 3: Database Connection
- **Dependency**: Database available and accessible
- **Layer 1**: Connection check in application startup
- **Layer 2**: Health check endpoint
- **Layer 3**: Database migration script check
- **Layer 4**: CI/CD database availability check
- **Layer 5**: Connection error messages point to configuration

### Example 4: API Keys / Environment Variables
- **Dependency**: Required environment variables set
- **Layer 1**: Config file that validates on load
- **Layer 2**: Application startup check
- **Layer 3**: Script that validates before execution
- **Layer 4**: CI/CD secret validation
- **Layer 5**: Error messages list missing variables

### Example 5: File System Paths
- **Dependency**: Required directories/files exist
- **Layer 1**: Config file path validation
- **Layer 2**: Application startup path check
- **Layer 3**: Script pre-flight checks
- **Layer 4**: CI/CD path validation
- **Layer 5**: File not found errors include setup instructions

## Implementation Checklist

### For Any Environment Dependency:

- [ ] **Identify dependency** - What exactly is required?
- [ ] **Identify failure mode** - What happens if wrong? (silent vs. obvious)
- [ ] **Find lowest-level entry point** - Where does the tool/system load?
- [ ] **Implement Layer 1 check** - In config file that loads first
- [ ] **Implement Layer 2 check** - In setup file that runs before code
- [ ] **Implement Layer 3 check** - In command/script integration
- [ ] **Implement Layer 4 check** - In CI/CD pipeline
- [ ] **Improve error messages** - Make root cause obvious
- [ ] **Test bypass scenarios** - Verify checks catch all bypasses
- [ ] **Document the requirement** - For reference (backup to enforcement)

## Code Templates

### Template 1: Config File Check (Layer 1)

```typescript
// In vitest.config.ts, vite.config.ts, jest.config.js, etc.
import { execSync } from 'child_process';

const REQUIRED_VALUE = 'expected-value';
const REQUIRED_PATH = '/expected/path';

function checkDependency(): void {
  try {
    const currentValue = execSync('command-to-check', { encoding: 'utf-8' }).trim();
    
    if (currentValue !== REQUIRED_VALUE) {
      console.error('\n❌ ERROR: [System] requires [Dependency]');
      console.error(`   Current: ${currentValue}`);
      console.error(`   Required: ${REQUIRED_VALUE}`);
      console.error('\n   Fix: [Clear instructions]\n');
      process.exit(1);
    }
  } catch (error) {
    console.error('\n❌ ERROR: Failed to check [Dependency]');
    console.error('   Fix: [Clear instructions]\n');
    process.exit(1);
  }
}

// Run check before tool loads
checkDependency();
```

### Template 2: Setup File Check (Layer 2)

```typescript
// In setup.ts, setupFiles, conftest.py, etc.
import { execSync } from 'child_process';

const REQUIRED_PATH = '/expected/path';

function verifyDependency(): void {
  try {
    const currentPath = execSync('which tool', { encoding: 'utf-8' }).trim();
    if (currentPath !== REQUIRED_PATH) {
      const currentVersion = execSync('tool --version', { encoding: 'utf-8' }).trim();
      console.error('\n❌ ERROR: [Tests] require [Dependency]');
      console.error(`   Current: ${currentPath} (${currentVersion})`);
      console.error(`   Required: ${REQUIRED_PATH}`);
      console.error('\n   Fix: [Clear instructions]\n');
      throw new Error('Invalid environment');
    }
  } catch (error: any) {
    if (error.message === 'Invalid environment') {
      throw error;
    }
    // Allow other errors (test environment)
  }
}

// Verify before tests run
verifyDependency();
```

### Template 3: npm Script Integration (Layer 3)

```json
{
  "scripts": {
    "test": "bash scripts/check-dependency.sh && vitest",
    "build": "bash scripts/check-dependency.sh && vite build"
  }
}
```

### Template 4: CI/CD Check (Layer 4)

```yaml
- name: Verify [Dependency]
  run: |
    tool --version
    which tool
    if [ "$(which tool)" != "/expected/path" ]; then
      echo "ERROR: Wrong [Dependency]"
      exit 1
    fi
```

## Anti-Patterns to Avoid

### ❌ Relying Only on Documentation
- **Problem**: Humans forget, don't read, or skip steps
- **Solution**: Enforce automatically

### ❌ Single Check Point
- **Problem**: Easy to bypass
- **Solution**: Multiple layers at different levels

### ❌ Vague Error Messages
- **Problem**: Doesn't point to root cause
- **Solution**: Explicit error messages with fix instructions

### ❌ Checks Only at High Level
- **Problem**: Can be bypassed by direct tool calls
- **Solution**: Check at lowest possible level (config files)

### ❌ No CI/CD Enforcement
- **Problem**: Wrong environment can be merged
- **Solution**: Enforce in CI/CD pipeline

## Success Criteria

A dependency enforcement implementation is successful when:

1. ✅ **0% bypass probability** - All execution paths include checks
2. ✅ **Clear error messages** - Root cause is immediately obvious
3. ✅ **Fail fast** - Issue caught before execution, not during
4. ✅ **Multiple layers** - Even if one fails, others catch it
5. ✅ **CI/CD enforced** - Cannot merge/deploy with wrong environment

## Related Patterns

- **Fail Fast Principle** - Catch errors early
- **Defense in Depth** - Multiple layers of protection
- **Explicit is Better Than Implicit** - Clear requirements
- **Make the Right Way Easy** - Enforce correct usage

## References

- Current implementation: `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`
- Prevention analysis: `frontend/PREVENTION_EFFECTIVENESS_ANALYSIS.md`
- Zero bypass implementation: `frontend/ZERO_BYPASS_IMPLEMENTATION.md`

