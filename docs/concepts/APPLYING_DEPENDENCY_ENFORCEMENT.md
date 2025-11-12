# Applying Dependency Enforcement Framework

## Quick Start Guide

### Step 1: Identify Your Dependency Issue

Ask yourself:
- What environment/configuration is required?
- What happens if it's wrong? (silent failure vs. obvious error)
- Where does the dependency manifest? (startup, runtime, tests)

### Step 2: Choose Your Layers

Not all layers are needed for every dependency. Choose based on:

- **Layer 1 (Config File)**: Always use - runs at lowest level
- **Layer 2 (Setup File)**: Use if you have setup files
- **Layer 3 (Command Integration)**: Use if you have npm scripts/Makefile
- **Layer 4 (CI/CD)**: Always use - prevents merging wrong config
- **Layer 5 (Error Messages)**: Always use - makes debugging easy

### Step 3: Implement Checks

#### For Node.js/Python/Tool Versions:

1. **Config File Check** (Layer 1):
   ```typescript
   // In vitest.config.ts, vite.config.ts, etc.
   import { execSync } from 'child_process';
   
   function checkDependency(): void {
     const current = execSync('tool --version', { encoding: 'utf-8' }).trim();
     if (current !== 'expected-version') {
       console.error('❌ ERROR: Wrong version');
       console.error(`Current: ${current}, Required: expected-version`);
       process.exit(1);
     }
   }
   checkDependency();
   ```

2. **Setup File Check** (Layer 2):
   ```typescript
   // In setup.ts, conftest.py, etc.
   import { execSync } from 'child_process';
   
   const current = execSync('which tool', { encoding: 'utf-8' }).trim();
   if (current !== '/expected/path') {
     throw new Error('Wrong tool path');
   }
   ```

3. **Command Integration** (Layer 3):
   ```json
   {
     "scripts": {
       "test": "bash scripts/check-tool.sh && vitest"
     }
   }
   ```

4. **CI/CD Check** (Layer 4):
   ```yaml
   - name: Verify Tool
     run: |
       tool --version
       if [ "$(which tool)" != "/expected/path" ]; then
         exit 1
       fi
   ```

#### For Environment Variables:

1. **Config File Check**:
   ```typescript
   const required = ['API_KEY', 'DATABASE_URL'];
   for (const key of required) {
     if (!process.env[key]) {
       console.error(`❌ ERROR: ${key} not set`);
       process.exit(1);
     }
   }
   ```

2. **Setup File Check**:
   ```typescript
   if (!process.env.API_KEY) {
     throw new Error('API_KEY environment variable required');
   }
   ```

#### For File System Paths:

1. **Config File Check**:
   ```typescript
   import { existsSync } from 'fs';
   
   if (!existsSync('/required/path')) {
     console.error('❌ ERROR: Required path not found');
     process.exit(1);
   }
   ```

## Real-World Examples

### Example: Python casa6 Requirement

**Problem**: Tests require casa6 Python, but system Python might be used.

**Solution**:
1. **Layer 1**: Check in `conftest.py`:
   ```python
   import sys
   import os
   
   CASA6_PYTHON = '/opt/miniforge/envs/casa6/bin/python'
   if sys.executable != CASA6_PYTHON:
       print(f'❌ ERROR: Tests require casa6 Python')
       print(f'Current: {sys.executable}')
       print(f'Required: {CASA6_PYTHON}')
       sys.exit(1)
   ```

2. **Layer 3**: Check in Makefile:
   ```makefile
   CASA6_PYTHON := /opt/miniforge/envs/casa6/bin/python
   
   test:
       @if [ "$(shell which python)" != "$(CASA6_PYTHON)" ]; then \
           echo "ERROR: Wrong Python"; exit 1; \
       fi
       $(CASA6_PYTHON) -m pytest
   ```

### Example: Database Connection

**Problem**: Application requires database, but connection might fail silently.

**Solution**:
1. **Layer 1**: Check in application startup:
   ```typescript
   async function checkDatabase(): Promise<void> {
     try {
       await db.authenticate();
     } catch (error) {
       console.error('❌ ERROR: Database connection failed');
       console.error('Fix: Ensure database is running and configured');
       process.exit(1);
     }
   }
   checkDatabase();
   ```

2. **Layer 4**: Check in CI/CD:
   ```yaml
   - name: Check Database
     run: |
       psql -h localhost -U user -d dbname -c "SELECT 1" || exit 1
   ```

## Testing Your Implementation

### Test Checklist:

- [ ] **Test with wrong dependency** - Should fail with clear error
- [ ] **Test with correct dependency** - Should pass
- [ ] **Test bypass scenarios** - Direct tool calls should still be caught
- [ ] **Test error messages** - Should be clear and actionable
- [ ] **Test CI/CD** - Should catch wrong environment before merge

### Test Commands:

```bash
# Test with wrong dependency
WRONG_ENV=1 npm test  # Should fail

# Test with correct dependency
CORRECT_ENV=1 npm test  # Should pass

# Test direct tool call (bypass)
tool directly  # Should still be caught by Layer 1
```

## Common Pitfalls

### ❌ Don't: Check only at high level
```bash
# BAD: Can be bypassed
npm test  # Check here only
```

### ✅ Do: Check at lowest level
```typescript
// GOOD: Cannot be bypassed
// In vitest.config.ts (runs before Vitest loads)
checkDependency();
```

### ❌ Don't: Vague error messages
```typescript
// BAD: Doesn't help
throw new Error('Configuration error');
```

### ✅ Do: Clear error messages
```typescript
// GOOD: Actionable
console.error('❌ ERROR: Wrong Node.js version');
console.error('Current: v16.20.2');
console.error('Required: v22.6.0');
console.error('Fix: conda activate casa6');
```

## Maintenance

### When to Update Checks:

- Dependency version changes
- Path changes
- New dependencies added
- Environment setup changes

### How to Update:

1. Update expected values in all layers
2. Test with wrong dependency (should fail)
3. Test with correct dependency (should pass)
4. Update documentation

## Resources

- Framework documentation: `docs/concepts/environment_dependency_enforcement.md`
- Template script: `scripts/templates/check-dependency-template.sh`
- Utility functions: `scripts/lib/environment-dependency-check.sh`
- Current example: `frontend/vitest.config.ts`, `frontend/src/test/setup.ts`

