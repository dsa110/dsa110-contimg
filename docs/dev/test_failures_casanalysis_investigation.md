# CASAnalysisPlugin Test Failures - Investigation

**Date:** 2025-11-12  
**Total Failures:** 14 tests  
**File:** `frontend/src/components/Sky/plugins/CASAnalysisPlugin.test.tsx`

## List of Failing Tests

### Component Rendering (2 failures)
1. `should render without crashing`
2. `should display all task options`

### Task Execution (3 failures)
3. `should execute analysis when run button clicked`
4. `should handle API errors gracefully`
5. `should show loading state during execution`

### Region Handling (2 failures)
6. `should toggle region usage`
7. `should include region in API call when useRegion is enabled`

### Batch Mode (3 failures)
8. `should enable batch mode toggle`
9. `should detect multiple regions in batch mode`
10. `should execute batch analysis`

### Contour Overlay (1 failure)
11. `should show contour toggle after imview task`

### Export Functionality (1 failure)
12. `should export results as JSON`

### JS9 Integration (2 failures)
13. `should register analysis tasks with JS9`
14. `should handle missing JS9 gracefully`

## Hypothesized Origins

### Primary Issue: Material-UI InputLabel/Select Association
**Error:** `TestingLibraryElementError: Found a label with the text of: /CASA Task/i, however no form control was found associated to that label.`

**Root Cause Hypothesis:**
The component uses both `InputLabel` and `label` prop on `Select`:
```tsx
<FormControl size="small" sx={{ minWidth: 200 }}>
  <InputLabel>CASA Task</InputLabel>
  <Select
    value={selectedTask}
    label="CASA Task"  // Duplicate label prop
    onChange={(e) => setSelectedTask(e.target.value)}
  >
```

In Material-UI v6, when using `InputLabel` as a child of `FormControl`, the `Select` should NOT have a `label` prop. The `InputLabel` should be associated via the `id` attribute, or the `Select` should use the `label` prop directly without `InputLabel`.

**Impact:** All tests fail because they can't find the form control associated with the label, preventing proper test queries.

### Secondary Issues (Cascading from Primary)

1. **Timer-related failures:** Some tests may be timing out (5+ seconds) because they're waiting for async operations that never complete due to the initial render failure.

2. **DOM container errors:** Some tests show "Target container is not a DOM element" which suggests the component isn't rendering properly due to the label issue.

3. **Mock setup issues:** Tests may not be properly mocking JS9 or API calls because the component fails to render.

## Root Causes Identified and Fixed

### 1. Material-UI InputLabel/Select Association ✅ FIXED
**Issue:** Component used both `InputLabel` and `label` prop on `Select`, causing label association failure.

**Fix:** Removed duplicate `label` prop and properly associated `InputLabel` with `Select` using `id` and `labelId`:
```tsx
<InputLabel id="casa-task-label">CASA Task</InputLabel>
<Select
  value={selectedTask}
  labelId="casa-task-label"  // Associates with InputLabel
  onChange={(e) => setSelectedTask(e.target.value)}
>
```

### 2. Fake Timers Conflict with userEvent ✅ FIXED
**Issue:** `vi.useFakeTimers()` in `beforeEach` conflicted with `userEvent` which requires real timers.

**Fix:** Removed fake timers from `beforeEach` - use real timers by default. Tests that need fake timers can enable them individually.

### 3. Multiple Element Queries ✅ FIXED
**Issue:** Tests found multiple elements with same text due to incomplete cleanup between tests.

**Fix:** 
- Added `cleanup()` in `afterEach` to properly clean up rendered components
- Changed `getByText` to `getAllByText` for elements that legitimately appear multiple times (Select value + menu items, error messages, loading states)

### 4. DOM Container Errors ✅ FIXED
**Issue:** Tests mocking `document.body.removeChild` broke React's ability to render.

**Fix:**
- Removed problematic `removeChild` mock
- Created real DOM anchor element instead of mock object
- Properly restored original `document.createElement` implementation to avoid infinite recursion
- Ensured `document.body` exists before rendering in all tests

## Final Status

**All 16 tests passing** ✅

**Fixes Applied:**
1. Component: Fixed `InputLabel`/`Select` association
2. Tests: Removed fake timers from `beforeEach`
3. Tests: Added proper cleanup between tests
4. Tests: Fixed multiple element queries using `getAllByText`
5. Tests: Fixed DOM container issues with proper mocking

