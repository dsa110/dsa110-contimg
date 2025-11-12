# CASAnalysisPlugin Test Fixes - Complete

**Date:** 2025-11-12  
**Status:** ✅ All 16 Tests Passing

## Summary

All 14 pre-existing test failures in `CASAnalysisPlugin.test.tsx` have been resolved. The failures were caused by multiple root causes that cascaded into test failures.

## Root Causes and Fixes

### 1. Material-UI InputLabel/Select Association Issue

**Problem:** Component used both `InputLabel` component and `label` prop on `Select`, causing React Testing Library to fail finding the associated form control.

**Error:** `Found a label with the text of: /CASA Task/i, however no form control was found associated to that label.`

**Fix:** Removed duplicate `label` prop and properly associated `InputLabel` with `Select`:
```tsx
// Before (broken):
<InputLabel>CASA Task</InputLabel>
<Select label="CASA Task" ...>

// After (fixed):
<InputLabel id="casa-task-label">CASA Task</InputLabel>
<Select labelId="casa-task-label" ...>
```

**File:** `frontend/src/components/Sky/plugins/CASAnalysisPlugin.tsx`

### 2. Fake Timers Conflict with userEvent

**Problem:** `vi.useFakeTimers()` in `beforeEach` conflicted with `userEvent.setup()` which requires real timers, causing tests to timeout.

**Error:** Tests timing out after 5 seconds

**Fix:** Removed fake timers from `beforeEach` - use real timers by default. Tests that need fake timers can enable them individually.

**File:** `frontend/src/components/Sky/plugins/CASAnalysisPlugin.test.tsx`

### 3. Multiple Element Queries

**Problem:** Tests found multiple elements with the same text because components weren't cleaned up between tests, causing multiple renders to accumulate.

**Error:** `Found multiple elements with the text: Image Statistics`

**Fix:** 
- Added `cleanup()` in `afterEach` to properly clean up rendered components
- Changed `getByText` to `getAllByText` for elements that legitimately appear multiple times:
  - Select dropdown shows selected value + menu items
  - Error messages appear in both heading and body
  - Loading messages may appear multiple times

**File:** `frontend/src/components/Sky/plugins/CASAnalysisPlugin.test.tsx`

### 4. DOM Container Errors

**Problem:** Tests mocking `document.body.removeChild` broke React's ability to render, causing "Target container is not a DOM element" errors.

**Error:** `Error: Target container is not a DOM element.`

**Fix:**
- Removed problematic `removeChild` mock
- Created real DOM anchor element instead of mock object for export functionality
- Properly restored original `document.createElement` implementation to avoid infinite recursion:
```typescript
const originalCreateElement = document.createElement.bind(document);
const createElementSpy = vi.spyOn(document, 'createElement');
createElementSpy.mockImplementation((tagName: string) => {
  if (tagName === 'a') {
    return realAnchor;
  }
  return originalCreateElement(tagName);
});
```
- Ensured `document.body` exists before rendering in all tests

**File:** `frontend/src/components/Sky/plugins/CASAnalysisPlugin.test.tsx`

## Test Results

**Before Fixes:**
- Total: 16 tests
- Passing: 2 tests
- Failing: 14 tests

**After Fixes:**
- Total: 16 tests
- Passing: 16 tests (100%)
- Failing: 0 tests

## Files Modified

1. `frontend/src/components/Sky/plugins/CASAnalysisPlugin.tsx`
   - Fixed `InputLabel`/`Select` association

2. `frontend/src/components/Sky/plugins/CASAnalysisPlugin.test.tsx`
   - Removed fake timers from `beforeEach`
   - Added `cleanup()` in `afterEach`
   - Fixed multiple element queries using `getAllByText`
   - Fixed DOM container issues with proper mocking
   - Ensured `document.body` exists in all tests

## Lessons Learned

1. **Material-UI v6:** When using `InputLabel` with `Select`, use `id`/`labelId` association, not both `InputLabel` and `label` prop.

2. **Test Isolation:** Always use `cleanup()` in `afterEach` to prevent test pollution.

3. **Timer Handling:** `userEvent` requires real timers - don't use fake timers globally if tests use `userEvent`.

4. **DOM Mocking:** When mocking DOM methods, preserve original implementations to avoid infinite recursion or breaking React rendering.

5. **Multiple Elements:** Use `getAllByText` when elements legitimately appear multiple times (e.g., Select dropdowns, error messages).

## Conclusion

All pre-existing test failures have been resolved. The fixes address root causes rather than symptoms, ensuring long-term stability of the test suite.

