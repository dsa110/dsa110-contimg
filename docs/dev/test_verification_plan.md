# Test Verification Plan

**Date:** 2025-11-12  
**Status:** Fixes Applied - Verification Needed

## Summary

All test fixes have been applied to the following files:
1. `ImageBrowser.test.tsx` - BrowserRouter wrapper added
2. `MSTable.test.tsx` - userEvent + waitFor pattern applied
3. `DataBrowserPage.test.tsx` - Async handling with waitFor
4. `PhotometryPlugin.test.tsx` - Timer advancement + waitFor

## Verification Steps

### 1. Unit Test Verification

Run the following commands to verify fixes:

```bash
cd /data/dsa110-contimg/frontend
source /opt/miniforge/etc/profile.d/conda.sh
conda activate casa6

# Test individual files
npm test -- --run src/components/Sky/ImageBrowser.test.tsx
npm test -- --run src/components/MSTable.test.tsx
npm test -- --run src/pages/DataBrowserPage.test.tsx
npm test -- --run src/components/Sky/plugins/PhotometryPlugin.test.tsx

# Run full test suite
npm test -- --run
```

### 2. Expected Results

**ImageBrowser Tests:**
- All 7 tests should pass
- No "useSearchParams must be used within a BrowserRouter" errors

**MSTable Tests:**
- All 4 selection logic tests should pass
- Checkbox clicks should work correctly
- Row clicks should trigger onMSClick

**DataBrowserPage Tests:**
- All 6+ tests should pass
- Tab switching should work correctly
- Loading/error states should display properly

**PhotometryPlugin Tests:**
- Rectangle region test should pass
- All region type tests should pass

### 3. E2E Test Verification

E2E tests require Docker Compose:

```bash
# Ensure Docker Compose is running
docker compose ps

# Run E2E tests
cd /data/dsa110-contimg/frontend
npm run test:e2e

# Or run smoke tests only
npm run test:e2e:smoke
```

### 4. Common Issues to Check

1. **Router Issues:** Ensure BrowserRouter is properly wrapped
2. **Async Timing:** Ensure waitFor is used for async state updates
3. **Timer Issues:** Ensure fake timers are advanced correctly
4. **Mock Issues:** Ensure mocks are reset between tests

## Next Steps After Verification

1. ✅ **If all tests pass:**
   - Update test status documents
   - Mark fixes as verified
   - Proceed with deployment

2. ⚠️ **If tests fail:**
   - Document specific failures
   - Investigate root causes
   - Apply additional fixes
   - Re-run verification

3. 📝 **Documentation:**
   - Update test_failure_tracking.md with results
   - Update test_status_summary.md with final status
   - Document any new patterns discovered

## Notes

- Terminal output capture has been problematic - using alternative verification methods
- All code changes have been applied and accepted
- Test files follow React Testing Library best practices
- E2E tests require Docker environment setup

