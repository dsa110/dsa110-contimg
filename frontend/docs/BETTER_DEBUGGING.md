# Better Debugging Approach for React State Management

## Current Problem
Manual testing is slow and error-prone. We need automated tests to catch state management bugs before they reach production.

## Solution: Test-Driven Development with Docker

### Quick Start with Docker

```bash
cd frontend

# Build and run tests
docker-compose -f docker-compose.test.yml run --rm frontend-test

# Run tests in watch mode (auto-reruns on file changes)
docker-compose -f docker-compose.test.yml run --rm frontend-test -- --watch
```

### What Changed

1. **Extracted Pure Function** (`frontend/src/utils/selectionLogic.ts`)
   - Selection logic moved to pure function
   - No side effects, easy to test

2. **Created Test Infrastructure**
   - Docker setup for consistent Node version
   - Vitest configured for testing
   - Test files ready to run

3. **Refactored ControlPage**
   - Now uses pure function for selection logic
   - Cleaner, more maintainable code

### 1. **Extract Pure Functions**
The selection logic is now in `frontend/src/utils/selectionLogic.ts` - a pure function that's easy to test:

```typescript
// Pure function - no side effects, easy to test
export function computeSelectedMS(
  paths: string[],
  prevList: string[],
  currentSelectedMS: string
): string {
  // All the logic here - testable in isolation
}
```

### 2. **Write Tests First**
Before fixing bugs, write a test that reproduces the issue:

```typescript
// useSelectionState.test.ts
it('should deselect MS when checkbox is unchecked', () => {
  const result = computeSelectedMS(
    [],                    // paths (empty)
    ['/data/ms1.ms'],      // prevList
    '/data/ms1.ms'         // currentSelectedMS
  );
  expect(result).toBe(''); // Should be empty
});
```

### 3. **Run Tests in Docker**
```bash
cd frontend

# Run all tests once
docker-compose -f docker-compose.test.yml run --rm frontend-test

# Run tests in watch mode (auto-reruns on file changes)
docker-compose -f docker-compose.test.yml run --rm frontend-test -- --watch
```

### 4. **Use React DevTools**
Install React DevTools browser extension to inspect state in real-time:
- View component props and state
- Track state changes
- Inspect React Query cache

## Quick Setup

1. **Run tests with Docker** (no local Node version needed):
   ```bash
   cd frontend
   docker-compose -f docker-compose.test.yml run --rm frontend-test
   ```

2. **When you find a bug:**
   - Write a test that reproduces it
   - Fix the code
   - Verify test passes
   - Check for edge cases

## Benefits

✅ **Catch bugs instantly** - Tests run in milliseconds  
✅ **Prevent regressions** - Tests catch when fixes break other things  
✅ **Document behavior** - Tests show how code should work  
✅ **Refactor safely** - Tests ensure refactoring doesn't break functionality  
✅ **Faster iteration** - No need to manually test every change  
✅ **Consistent environment** - Docker ensures same Node version everywhere

## Test Structure

```
frontend/
  src/
    utils/
      selectionLogic.ts          ← Pure function (easy to test)
    hooks/
      useSelectionState.test.ts  ← Unit tests for pure function
    components/
      MSTable.test.tsx           ← Component tests
    pages/
      ControlPage.test.tsx       ← Integration tests
  Dockerfile.dev                 ← Docker setup for testing
  docker-compose.test.yml        ← Docker Compose for test commands
```

## Immediate Benefits

Even without running tests yet, extracting the logic provides:
- **Easier debugging** - You can test the logic in isolation
- **Better code organization** - Logic separated from UI
- **Easier to understand** - Pure functions are easier to reason about
- **Ready for testing** - Tests are ready to run with Docker

## Docker Commands

```bash
# Run tests once
docker-compose -f docker-compose.test.yml run --rm frontend-test

# Run tests in watch mode
docker-compose -f docker-compose.test.yml run --rm frontend-test -- --watch

# Run tests with UI (requires port forwarding)
docker-compose -f docker-compose.test.yml run --rm -p 51204:51204 frontend-test -- --ui

# Build production bundle
docker-compose -f docker-compose.test.yml run --rm frontend-build
```


