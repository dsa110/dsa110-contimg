# Browser Testing & Production Deployment Plan

## Overview

This document outlines the step-by-step plan for browser testing and production
deployment of the refactored JS9 components (Phase 3a & 3b).

## Phase 1: Pre-Deployment Validation

### 1.1 Code Compilation Check

- [ ] Run TypeScript compilation: `npm run type-check`
- [ ] Verify no type errors
- [ ] Check for any remaining `window.JS9` direct calls
- [ ] Verify all imports resolve correctly

### 1.2 Unit Tests

- [ ] Run unit tests: `npm test` (if available)
- [ ] Verify JS9Service tests pass
- [ ] Verify hook tests pass
- [ ] Check test coverage

### 1.3 Linting

- [ ] Run ESLint: `npm run lint` (if available)
- [ ] Fix any linting errors
- [ ] Verify code style consistency

### 1.4 Build Verification

- [ ] Run development build: `npm run build` (or `npm run build:dev`)
- [ ] Verify build succeeds without errors
- [ ] Check for build warnings
- [ ] Verify output files are generated

### 1.5 Critical File Review

- [ ] Review SkyViewer.tsx for any issues
- [ ] Review all hook files
- [ ] Review JS9Service.ts
- [ ] Check for console.log statements (remove if any)
- [ ] Verify error handling is in place

## Phase 2: Browser Testing

### 2.1 Development Server

- [ ] Start dev server: `npm run dev`
- [ ] Verify server starts successfully
- [ ] Check server is accessible at expected URL
- [ ] Verify hot reload works

### 2.2 Playwright Integration Tests

- [ ] Run existing tests: `npm run test:e2e`
- [ ] Run new refactoring tests:
      `npx playwright test tests/playwright/js9-refactoring.spec.ts`
- [ ] Verify all tests pass
- [ ] Review test output for any warnings
- [ ] Check for flaky tests

### 2.3 Manual Browser Validation

- [ ] Navigate to Sky View page: `http://localhost:5173/sky`
- [ ] Verify component renders without errors
- [ ] Check browser console for errors
- [ ] Verify JS9 container is visible
- [ ] Test image loading (if images available)
- [ ] Test resize functionality
- [ ] Verify content preservation on navigation

### 2.4 Console Error Check

- [ ] Open browser DevTools
- [ ] Check Console tab for errors
- [ ] Check Network tab for failed requests
- [ ] Verify no uncaught exceptions
- [ ] Check for memory warnings

### 2.5 JS9 Functionality Verification

- [ ] Verify JS9 library loads
- [ ] Test image loading (if possible)
- [ ] Verify resize handling works
- [ ] Check that content persists
- [ ] Test error scenarios (invalid image path)

### 2.6 Error Scenario Testing

- [ ] Test with missing JS9 library
- [ ] Test with invalid image path
- [ ] Test with network errors
- [ ] Verify error messages display correctly
- [ ] Verify component recovers gracefully

## Phase 3: Production Build

### 3.1 Production Build Creation

- [ ] Run production build: `npm run build`
- [ ] Verify build completes successfully
- [ ] Check for build warnings
- [ ] Verify optimization is enabled

### 3.2 Build Artifacts Verification

- [ ] Check dist/ directory exists
- [ ] Verify JavaScript bundles are generated
- [ ] Verify CSS files are generated
- [ ] Check for source maps (if needed)
- [ ] Verify asset paths are correct

### 3.3 Bundle Size Analysis

- [ ] Check bundle sizes
- [ ] Compare with previous build (if available)
- [ ] Verify no unexpected size increases
- [ ] Check for code splitting (if configured)

### 3.4 Local Production Build Validation

- [ ] Serve production build locally: `npm run preview` (or similar)
- [ ] Test functionality in production mode
- [ ] Verify performance is acceptable
- [ ] Check for production-specific issues

## Phase 4: Deployment

### 4.1 Deployment Configuration Review

- [ ] Review deployment configuration
- [ ] Check environment variables
- [ ] Verify build output directory
- [ ] Review deployment scripts
- [ ] Check Docker configuration (if used)

### 4.2 Deployment Execution

- [ ] Backup current production (if applicable)
- [ ] Execute deployment steps
- [ ] Monitor deployment logs
- [ ] Verify deployment completes successfully
- [ ] Check deployment status

### 4.3 Deployment Verification

- [ ] Verify files are deployed correctly
- [ ] Check file permissions
- [ ] Verify environment variables are set
- [ ] Check server logs for errors
- [ ] Verify application starts successfully

### 4.4 Production Smoke Test

- [ ] Access production URL
- [ ] Verify application loads
- [ ] Test critical functionality
- [ ] Check browser console for errors
- [ ] Verify JS9 components work
- [ ] Test image loading (if applicable)

## Phase 5: Post-Deployment

### 5.1 Error Monitoring

- [ ] Monitor application logs
- [ ] Check error tracking (if available)
- [ ] Monitor browser console errors
- [ ] Watch for user-reported issues
- [ ] Set up alerts (if available)

### 5.2 Functionality Verification

- [ ] Verify all features work in production
- [ ] Test on multiple browsers
- [ ] Test on different screen sizes
- [ ] Verify performance metrics
- [ ] Check for regressions

### 5.3 Documentation

- [ ] Document deployment date/time
- [ ] Document any issues encountered
- [ ] Update deployment notes
- [ ] Create deployment summary
- [ ] Update changelog (if applicable)

### 5.4 Knowledge Graph Update

- [ ] Add deployment episode to knowledge graph
- [ ] Document deployment status
- [ ] Record any issues or learnings
- [ ] Update project status

## Rollback Plan

If issues are discovered:

1. Identify the issue severity
2. Determine if rollback is needed
3. Execute rollback procedure
4. Investigate root cause
5. Fix issue and redeploy

## Success Criteria

- [ ] All tests pass
- [ ] No console errors in production
- [ ] All functionality works correctly
- [ ] Performance is acceptable
- [ ] No regressions introduced
- [ ] Documentation is updated

## Notes

- Keep deployment logs for reference
- Document any deviations from plan
- Note any issues for future improvements
- Update this plan based on learnings
