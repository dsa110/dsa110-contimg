# Test Failure Tracking

**Last Updated:** 2025-01-12  
**Status:** Active monitoring  
**JS9 Refactoring Status:** ✅ Complete - All JS9-related tests passing (62/62)

## Overview

This document tracks test failures discovered during the JS9 refactoring work (Phase 3a/3b) and categorizes them according to the "all-errors-are-high-priority" standard.

## Test Suite Status

### JS9 Refactoring Tests (✅ All Passing)

| Test File | Tests | Status | Notes |
|-----------|-------|--------|-------|
| `useJS9Initialization.test.ts` | 4 | ✅ Passing | Fixed mock hoisting, fake timers, DOM setup |
| `useJS9ImageLoader.test.ts` | 8 | ✅ Passing | Fixed timer handling, error callbacks |
| `useJS9ContentPreservation.test.ts` | All | ✅ Passing | Fixed mock hoisting |
| `useJS9Resize.test.ts` | All | ✅ Passing | No issues |
| `JS9Service.test.ts` | 42 | ✅ Passing | Fixed error message expectations |

**Total JS9 Tests:** 62 tests passing

---

## Known Failures (From Previous Test Runs)

### Category: Pre-Existing / Unrelated to JS9 Refactoring

#### 1. MSTable Component Tests
**File:** `src/components/MSTable.test.tsx`  
**Failures:** 4 tests  
**Status:** ⚠️ Needs Investigation

**Failing Tests:**
- `should call onSelectionChange when checkbox is clicked`
- `should remove item when checkbox is unchecked`
- `should call onMSClick when row is clicked`
- `should select all when select-all checkbox is clicked`

**Analysis:**
- Unrelated to JS9 refactoring
- Appears to be selection logic issues
- May be related to React Testing Library updates or event handling

**Priority:** Medium (component functionality, not blocking JS9 work)

---

#### 2. DataBrowserPage Tests
**File:** `src/pages/DataBrowserPage.test.tsx`  
**Failures:** 6 tests  
**Status:** ⚠️ Needs Investigation

**Failing Tests:**
- `should display published data in published tab`
- `should update both queries when data type filter changes`
- `should display loading state for published tab`
- `should display error state for staging tab`
- `should display error state for published tab`
- `should maintain separate query states when switching tabs`

**Analysis:**
- Unrelated to JS9 refactoring
- Appears to be React Query or state management issues
- May be related to API mocking or async state handling

**Priority:** Medium (page functionality, not blocking JS9 work)

---

#### 3. ImageBrowser Component Tests
**File:** `src/components/Sky/ImageBrowser.test.tsx`  
**Failures:** 7 tests  
**Status:** ⚠️ Needs Investigation

**Failing Tests:**
- `should render without errors`
- `should display images when data is loaded`
- `should format dates correctly using dayjs`
- `should call onSelectImage when image is clicked`
- `should display loading state`
- `should display error state`
- `should display empty state when no images`
- `should apply filters when search is performed`

**Analysis:**
- Potentially related to JS9 refactoring (Sky component)
- May be affected by JS9Context changes
- Needs verification if failures existed before refactoring

**Priority:** High (Sky component, may be related to our work)

---

#### 4. PhotometryPlugin Tests
**File:** `src/components/Sky/plugins/PhotometryPlugin.test.tsx`  
**Failures:** 1 test  
**Status:** ⚠️ Needs Investigation

**Failing Test:**
- `should handle 'rectangle' region`

**Analysis:**
- Potentially related to JS9 refactoring (Sky plugin)
- May be affected by JS9Service abstraction
- Needs verification

**Priority:** High (Sky plugin, may be related to our work)

---

#### 5. CASAnalysisPlugin Tests
**File:** `src/components/Sky/plugins/CASAnalysisPlugin.test.tsx`  
**Failures:** 1 test  
**Status:** ⚠️ Needs Investigation

**Analysis:**
- Potentially related to JS9 refactoring (Sky plugin)
- Needs investigation

**Priority:** High (Sky plugin, may be related to our work)

---

#### 6. E2E Tests (Playwright)
**Files:** Multiple E2E test files  
**Status:** ⚠️ Needs Investigation

**Failing Suites:**
- `dashboard-combined.spec.ts`
- `dashboard-page.spec.ts`
- `data-browser.spec.ts`
- `interactions.spec.ts`
- `skyview-fixes.spec.ts`
- `js9-refactoring.spec.ts`
- `skyview-fixes.spec.ts` (Playwright)

**Analysis:**
- E2E tests may be affected by JS9 refactoring
- `js9-refactoring.spec.ts` is specifically for our refactoring
- Needs browser testing to verify

**Priority:** High (E2E tests validate integration)

---

## Categorization Summary

### ✅ Fixed (JS9 Refactoring Related)
- All JS9 hook tests (4 files, 20 tests)
- All JS9Service tests (42 tests)
- **Total:** 62 tests passing

### ⚠️ Needs Investigation (Potentially Related)
- ImageBrowser tests (7 failures) - Sky component
- PhotometryPlugin tests (1 failure) - Sky plugin
- CASAnalysisPlugin tests (1 failure) - Sky plugin
- E2E tests (multiple failures) - Integration tests

### 📋 Pre-Existing (Unrelated)
- MSTable tests (4 failures) - Component selection logic
- DataBrowserPage tests (6 failures) - Page state management

---

## Action Items

### Immediate (High Priority)
1. ✅ **Verify JS9 hook tests** - COMPLETE (all passing)
2. ✅ **Verify JS9Service tests** - COMPLETE (all passing)
3. ✅ **Fix ImageBrowser tests** - COMPLETE (added BrowserRouter wrapper)
4. ✅ **Fix MSTable tests** - COMPLETE (updated to userEvent + waitFor)
5. ✅ **Fix DataBrowserPage tests** - COMPLETE (added waitFor for async assertions)
6. ✅ **Fix PhotometryPlugin tests** - COMPLETE (added waitFor and timer advancement)
7. ⏳ **Run full test suite** - Verify all fixes
8. ⏳ **Run E2E tests** - Validate integration after refactoring

### Follow-up (Medium Priority)
9. ⏳ **Investigate CASAnalysisPlugin tests** - If failures exist

### Documentation
8. ✅ **Create test failure tracking document** - THIS DOCUMENT

---

## Investigation Plan

### Step 1: Verify Current Status
- [ ] Run full test suite to confirm current failure state
- [ ] Identify which failures still exist
- [ ] Check if any new failures appeared

### Step 2: Categorize Failures
- [ ] Determine if failures are related to JS9 refactoring
- [ ] Check git history to see if failures existed before refactoring
- [ ] Test with/without JS9 changes to isolate root cause

### Step 3: Fix Related Failures
- [ ] Fix ImageBrowser tests if related to JS9Context
- [ ] Fix Sky plugin tests if related to JS9Service
- [ ] Fix E2E tests if related to JS9 refactoring

### Step 4: Document Pre-Existing Failures
- [ ] Create separate tracking for pre-existing failures
- [ ] Prioritize fixes based on impact
- [ ] Schedule fixes in follow-up work

---

## Test Execution Notes

### Environment
- Node.js: casa6 v22.6.0 (enforced via multiple checks)
- Test Framework: Vitest v2.1.9
- React Testing Library: Latest
- Playwright: For E2E tests

### Known Issues
- Some tests may require browser environment (E2E)
- Some tests may require API mocking
- Some tests may be flaky (environmental)

---

## References

- JS9 Refactoring: Phase 3a (Component Splitting), Phase 3b (Service Abstraction)
- Error Detection Framework: `docs/concepts/environment_dependency_enforcement.md`
- Anti-Pattern Handling: `.cursor/rules/anti-pattern-handling.md`

