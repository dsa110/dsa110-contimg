# Plotly Module Export Fix

**Date:** 2025-11-17 **Type:** Bug Fix **Status:** ✅ Fixed

---

## Problem

The dashboard was showing this error:

```
TypeError: Plotly.purge is not a function
```

This occurred in the `PlotlyLazy.tsx` component when trying to render Plotly
charts.

---

## Root Cause

The issue was in how we were importing and using `plotly.js-dist-min`:

**INCORRECT (previous code):**

```typescript
const Plot = lazy(() =>
  import("plotly.js-dist-min").then((Plotly) =>
    import("react-plotly.js/factory").then((factory) => ({
      default: factory.default(Plotly), // ❌ Wrong: Plotly is the module, not the Plotly object
    }))
  )
);
```

The module object was being passed directly to the factory, but
`react-plotly.js/factory` expects the **actual Plotly object** with methods like
`purge`, `newPlot`, etc.

---

## Solution

Access the **default export** from the module:

**CORRECT (fixed code):**

```typescript
const Plot = lazy(() =>
  import("plotly.js-dist-min").then((PlotlyModule) =>
    import("react-plotly.js/factory").then((factory) => ({
      default: factory.default(PlotlyModule.default), // ✅ Correct: extract Plotly from module.default
    }))
  )
);
```

---

## Technical Details

### Module Export Structure

`plotly.js-dist-min` exports its module as:

```javascript
{
  default: Plotly,  // The actual Plotly object with all methods
  __esModule: true,
  // ... other module metadata
}
```

### Why This Matters

`react-plotly.js/factory` needs the Plotly object to have these methods:

- `Plotly.newPlot()` - Create a new plot
- `Plotly.purge()` - Clean up a plot (this was failing)
- `Plotly.react()` - Update a plot
- Many other Plotly API methods

When we passed the module object instead of `module.default`, the factory
couldn't find these methods, resulting in `Plotly.purge is not a function`.

---

## Files Changed

- **`src/components/PlotlyLazy.tsx`** - Fixed the import to access
  `PlotlyModule.default`

---

## Verification

After the fix:

1. The dev server hot-reloaded the component
2. `plotly.js-dist-min` was optimized by Vite
3. No more `Plotly.purge is not a function` errors

---

## Related Issues

This is related to the previous fixes for:

- **Error 18:** `ReferenceError: exports is not defined` (fixed by
  pre-transforming `react-plotly.js`)
- **Error 40:** `Failed to resolve import: plotly.js-dist-min` (fixed by using
  correct package)

---

## Prevention

To prevent similar issues in the future:

1. Always check the module export structure when using dynamic imports
2. Use `.default` for ES modules that export a default
3. Test lazy-loaded components thoroughly
4. Use TypeScript to catch missing methods at compile time

---

## References

- [Plotly.js Documentation](https://plotly.com/javascript/)
- [react-plotly.js Factory Pattern](https://github.com/plotly/react-plotly.js#customizing-the-plotlyjs-bundle)
- [ES Module Default Exports](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/export#using_the_default_export)
