# Hard-to-Catch Runtime Errors - Analysis and Solutions

**Date:** 2025-11-17  
**Status:** ✅ Active Prevention Implemented

---

## Summary

This document catalogs runtime errors that are difficult to catch with standard
linting and TypeScript checks, along with the custom solutions implemented to
prevent them.

---

## 1. React Router Hooks Missing React Import (React 19)

### The Error

```
TypeError: Cannot read properties of null (reading 'useContext')
```

**Root Cause:** React Router hooks (`useNavigate`, `useLocation`, `useParams`,
etc.) internally use React's `useContext`. In React 19, hooks that use React
internals require React to be explicitly imported and in scope.

**Why It's Hard to Catch:**

- **Runtime Error:** Only occurs when the component renders, not at compile time
- **Indirect Dependency:** The error happens inside React Router's code, not
  directly in user code
- **TypeScript Doesn't Catch:** TypeScript validates types, not runtime module
  scope
- **Standard ESLint Doesn't Catch:** No built-in rule checks for this pattern

**Impact:** 13 pages were at risk in the codebase.

### Solution Implemented

**Custom ESLint Rule:** `scripts/eslint-rules/require-react-for-router-hooks.js`

- Detects usage of `react-router-dom` hooks
- Requires `import React` or `import React, { ... }` when these hooks are used
- Provides clear error message with fix guidance

**Configuration:** Added to `eslint.config.js` as an error-level rule.

**Files Affected:** All pages using `react-router-dom` hooks without React
import.

---

## 2. Lazy-Loading Export Pattern (React.lazy)

### The Error

```
TypeError: Cannot convert object to primitive value
```

**Root Cause:** `React.lazy()` requires default exports, but components were
exported as named exports (`export function Component()` instead of
`export default function Component()`).

**Why It's Hard to Catch:**

- **Runtime Error:** Only occurs when React Router tries to render the lazy
  component
- **TypeScript May Not Catch:** Depends on how `React.lazy()` is typed
- **No Standard ESLint Rule:** No built-in rule enforces default exports for
  lazy-loaded components

**Impact:** Caused complete route failure (component wouldn't render).

### Solution Implemented

**Custom Verification Script:** `scripts/verify-page-exports.js`

- Checks all page components for default exports
- Prevents commits if violations found
- Integrated into pre-commit hooks

**Additional Safeguards:**

1. TypeScript type checking (catches some cases)
2. Route rendering integration tests (catches runtime errors)
3. Pre-commit hook enforcement

**Documentation:** `docs/analysis/lazy-loading-export-issues.md`

---

## 3. Similar Patterns to Watch For

### Context Provider Missing

**Pattern:** Using `useContext` without wrapping component in provider.

**Detection:** Could be caught by:

- Custom ESLint rule checking context usage
- Runtime error boundary (already implemented)
- Integration tests

**Status:** Currently caught at runtime via error boundary.

### Hook Call Order Violations

**Pattern:** Calling hooks conditionally or in wrong order.

**Detection:** Already caught by `react-hooks/rules-of-hooks` ESLint rule.

**Status:** ✅ Already prevented.

### Missing Dependency Arrays

**Pattern:** `useEffect` or `useMemo` with incorrect dependencies.

**Detection:** Already caught by `react-hooks/exhaustive-deps` ESLint rule.

**Status:** ✅ Already prevented.

---

## Prevention Strategy

### Multi-Layer Defense

1. **ESLint Rules (Pre-commit):**
   - Custom rules for known patterns
   - Standard React hooks rules
   - TypeScript type checking

2. **Verification Scripts:**
   - `verify-page-exports.js` - Default export checking
   - `check-imports.js` - Import validation
   - Can be extended for other patterns

3. **Runtime Error Boundaries:**
   - Catches errors that slip through
   - Provides user-friendly error messages
   - Logs errors for debugging

4. **Integration Tests:**
   - E2E tests that actually render routes
   - Catches runtime errors in CI/CD
   - Prevents regressions

### Adding New Rules

When encountering a new hard-to-catch runtime error:

1. **Document the pattern** in this file
2. **Create ESLint rule** in `scripts/eslint-rules/`
3. **Add to config** in `eslint.config.js`
4. **Test on codebase** to find all instances
5. **Fix violations** before merging
6. **Update documentation**

---

## Related Files

- `scripts/eslint-rules/require-react-for-router-hooks.js` - React Router hooks
  rule
- `scripts/verify-page-exports.js` - Default export verification
- `eslint.config.js` - ESLint configuration
- `docs/analysis/lazy-loading-export-issues.md` - Lazy loading analysis

---

## Lessons Learned

1. **Runtime errors need custom detection:** Standard tooling often misses
   runtime-specific issues
2. **Multi-layer defense works:** Combine linting, scripts, tests, and error
   boundaries
3. **Document patterns:** When a pattern emerges, document and prevent it
4. **React 19 changes:** New React versions may introduce new runtime
   requirements

---

**Last Updated:** 2025-11-17  
**Maintainer:** Development Team
