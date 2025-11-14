# Automated Testing Strategy for Frontend

## Problem: Catching Import Errors Without Human Testing

When we fixed the `date-fns` import error, a human had to manually test the page to discover it. This document outlines how to catch such errors automatically.

## Multi-Layer Testing Approach

### Layer 1: Import Verification (Fastest - Catches Missing Dependencies)

**Script:** `frontend/scripts/check-imports.js`

**What it does:**
- Scans all source files for problematic imports (e.g., `date-fns`)
- Verifies required dependencies are in `package.json`
- Runs in < 1 second

**When to run:**
- Pre-commit hook
- CI/CD pipeline
- Before building

**Example:**
```bash
node frontend/scripts/check-imports.js
```

**Would have caught:** The `date-fns` import error immediately

---

### Layer 2: Type Checking (Fast - Catches Type Errors)

**Command:** `npx tsc --noEmit`

**What it does:**
- Verifies TypeScript types are correct
- Checks that all imports resolve
- Validates component props and interfaces

**When to run:**
- Pre-commit hook
- CI/CD pipeline
- Before building

**Example:**
```bash
cd frontend && npx tsc --noEmit
```

**Would have caught:** Type errors from missing imports

---

### Layer 3: Build Verification (Medium - Catches Build Errors)

**Script:** `frontend/scripts/verify-build.sh`

**What it does:**
- Runs TypeScript compilation
- Runs ESLint
- Attempts production build
- Verifies all dependencies are installed

**When to run:**
- Pre-commit hook
- CI/CD pipeline
- Before deploying

**Example:**
```bash
cd frontend && ./scripts/verify-build.sh
```

**Would have caught:** Build failures from missing imports

---

### Layer 4: Component Tests (Medium - Catches Runtime Errors)

**File:** `frontend/src/components/Sky/ImageBrowser.test.tsx`

**What it does:**
- Renders component in isolation
- Verifies component renders without errors
- Tests date formatting functionality
- Tests user interactions

**When to run:**
- Pre-commit hook (on changed files)
- CI/CD pipeline
- During development (watch mode)

**Example:**
```bash
cd frontend && npm test -- ImageBrowser.test.tsx
```

**Would have caught:** Runtime errors from missing imports when component tries to render

---

### Layer 5: Integration Tests (Slower - Catches Integration Issues)

**What it does:**
- Tests multiple components working together
- Tests API integration
- Tests routing

**When to run:**
- CI/CD pipeline
- Before major releases

**Example:**
```bash
cd frontend && npm test -- --run
```

---

### Layer 6: E2E Tests (Slowest - Catches Full Stack Issues)

**Tools:** Playwright, Cypress, or similar

**What it does:**
- Tests full user workflows
- Tests in real browser
- Tests with real API

**When to run:**
- Nightly builds
- Before releases
- On staging environment

**Example:**
```bash
npm run test:e2e
```

---

## Recommended CI/CD Pipeline

```yaml
# .github/workflows/frontend-tests.yml
name: Frontend Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: cd frontend && npm ci
      
      # Layer 1: Import check (fastest)
      - name: Check imports
        run: cd frontend && node scripts/check-imports.js
      
      # Layer 2: Type check
      - name: Type check
        run: cd frontend && npx tsc --noEmit
      
      # Layer 3: Build verification
      - name: Build verification
        run: cd frontend && ./scripts/verify-build.sh
      
      # Layer 4: Component tests
      - name: Run tests
        run: cd frontend && npm test -- --run
      
      # Layer 5: Linting
      - name: Lint
        run: cd frontend && npm run lint
```

---

## Pre-Commit Hook Setup

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Pre-commit hook for frontend

cd frontend

# Fast checks first
echo "Checking imports..."
node scripts/check-imports.js || exit 1

echo "Type checking..."
npx tsc --noEmit || exit 1

echo "Running tests on changed files..."
npm test -- --run --changed || exit 1

echo "✓ All checks passed"
```

---

## Quick Test Script

**Script:** `frontend/scripts/test-skyview.sh`

Runs all layers for SkyView components:

```bash
cd frontend && ./scripts/test-skyview.sh
```

This single command runs:
1. Import checking
2. Type checking
3. Build verification
4. Component tests
5. Linting

---

## What Each Layer Would Have Caught

### The `date-fns` Error

| Layer | Would Catch? | Speed | When |
|-------|--------------|-------|------|
| Import Check | ✅ Yes | < 1s | Immediately |
| Type Check | ✅ Yes | ~5s | Before commit |
| Build Verify | ✅ Yes | ~30s | Before deploy |
| Component Test | ✅ Yes | ~10s | On test run |
| Integration Test | ✅ Yes | ~1min | In CI |
| E2E Test | ✅ Yes | ~5min | Nightly |

---

## Best Practices

1. **Run fast checks frequently** - Import and type checks should run on every save
2. **Run medium checks before commit** - Build and component tests
3. **Run slow checks in CI** - Integration and E2E tests
4. **Fail fast** - Stop at first error to save time
5. **Parallelize** - Run independent tests in parallel

---

## Tools Summary

| Tool | Purpose | Speed | When |
|------|---------|-------|------|
| `check-imports.js` | Find missing imports | Fast | Pre-commit |
| `tsc --noEmit` | Type checking | Fast | Pre-commit |
| `verify-build.sh` | Build verification | Medium | Pre-deploy |
| `vitest` | Unit/component tests | Medium | CI/CD |
| `playwright` | E2E tests | Slow | Nightly |

---

## Example: Catching the `date-fns` Error

If we had run the import check:

```bash
$ node frontend/scripts/check-imports.js
❌ Import errors found:

  src/components/Sky/ImageBrowser.tsx: date-fns is not installed, use dayjs instead
```

This would have caught the error **immediately** without needing to:
1. Start the dev server
2. Navigate to the page
3. See the error in browser
4. Debug the issue

---

## Conclusion

By implementing these automated checks, we can catch import errors and other issues **before** they reach a human tester. The key is running fast checks frequently and slower checks in CI/CD.

