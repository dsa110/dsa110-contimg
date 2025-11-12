# Browser Testing & Integration Validation Guide

## Overview

This guide covers browser testing and integration validation for the refactored JS9 components (Phase 3a & 3b).

## Prerequisites

1. Development server running: `npm run dev` (or `docker compose up`)
2. Application accessible at: `http://localhost:5173`
3. Playwright installed and configured

## Test Files

### 1. `js9-refactoring.spec.ts`
Comprehensive integration tests for refactored components:
- Component rendering
- JS9 initialization
- Image loading flow
- Resize handling
- Content preservation
- Error handling
- Memory leak detection

### 2. `skyview-fixes.spec.ts`
Existing tests for SkyView page fixes (MUI Grid, JS9 display)

## Running Tests

### Option 1: Docker (Recommended)
```bash
cd frontend
npm run test:e2e
```

### Option 2: With UI
```bash
npm run test:e2e:ui
```

### Option 3: Debug Mode
```bash
npm run test:e2e:debug
```

### Option 4: Direct Playwright
```bash
cd frontend
npx playwright test tests/playwright/js9-refactoring.spec.ts
```

## Manual Browser Validation

### 1. Component Rendering
- Navigate to: `http://localhost:5173/sky`
- Verify: SkyViewer component renders without errors
- Check: Console for any errors (should be clean)

### 2. JS9 Initialization
- Verify: JS9 container is visible (`#js9Display` or similar)
- Check: Container has correct dimensions
- Verify: No initialization errors in console

### 3. Image Loading
- Select an image from the browser
- Verify: Loading indicator appears
- Verify: Image loads successfully
- Check: No loading errors

### 4. Resize Handling
- Resize browser window
- Verify: Container adapts to new size
- Verify: Canvas maintains aspect ratio
- Check: No resize errors in console

### 5. Content Preservation
- Trigger a re-render (navigate away and back, or change state)
- Verify: JS9 content persists
- Verify: Image remains visible
- Check: No content loss errors

### 6. Error Handling
- Test with invalid image path
- Verify: Error message displays
- Verify: Component remains functional
- Check: Errors are handled gracefully

## Validation Checklist

- [ ] All Playwright tests pass
- [ ] No console errors (except expected)
- [ ] Component renders correctly
- [ ] JS9 initializes properly
- [ ] Images load successfully
- [ ] Resize works correctly
- [ ] Content persists on re-render
- [ ] Errors are handled gracefully
- [ ] No memory leaks detected
- [ ] Performance is acceptable

## Troubleshooting

### Tests Fail to Run
- Ensure dev server is running
- Check Playwright is installed: `npx playwright install`
- Verify Docker containers are up (if using Docker)

### Component Not Rendering
- Check browser console for errors
- Verify JS9 library is loaded
- Check network tab for failed requests

### JS9 Not Initializing
- Verify JS9 files are accessible at `/ui/js9/`
- Check browser console for JS9 errors
- Verify container div exists with correct ID

### Memory Leaks
- Use browser DevTools Memory profiler
- Check for growing number of observers
- Verify cleanup functions are called

## Expected Results

### Console Output
- No critical errors
- JS9 initialization messages (debug level)
- Image loading messages (debug level)

### Performance
- Initial render: < 2 seconds
- Image load: < 5 seconds (depending on size)
- Resize handling: < 100ms response

### Memory
- No growing memory usage
- Observers cleaned up properly
- No event listener leaks

## Reporting Issues

If tests fail or issues are found:
1. Capture console output
2. Take screenshots of errors
3. Note browser and version
4. Document steps to reproduce
5. Check test logs for details

