# Custom Element Duplicate Registration Fix

## Issue

**Error:**
`Uncaught Error: A custom element with name 'mce-autosize-textarea' has already been defined.`

**Location:** `overlay_bundle.js:149:5562` (third-party library, likely TinyMCE
or similar)

**Root Cause:** A third-party library is attempting to register a custom element
(`mce-autosize-textarea`) that has already been registered. This commonly occurs
during:

- Hot module reloading in development
- Multiple imports of the same library
- Library code that doesn't check if an element is already defined before
  registering it

## Solution Implemented

### 1. Custom Element Guard Utility

**File:** `frontend/src/utils/customElementGuard.ts`

**Features:**

- `safeDefineCustomElement()` - Safely define custom elements with duplicate
  checking
- `patchCustomElementsDefine()` - Patch the global `customElements.define()` to
  prevent duplicate registration errors
- Automatic detection and graceful handling of duplicate registration attempts

**How it works:**

1. Checks if element is already defined using `customElements.get()`
2. If already defined, silently skips registration (returns false)
3. If registration fails with "already been defined" error, catches and ignores
   it
4. Re-throws unexpected errors

### 2. Early Initialization Module

**File:** `frontend/src/utils/initCustomElementGuard.ts`

**Purpose:**

- Applies the patch immediately when the module loads
- Ensures the patch is active before any third-party libraries register custom
  elements

**Usage:** Import this module early in your application entry point:

```typescript
// In index.tsx or main.tsx, before any other imports
import "./utils/initCustomElementGuard";
```

## Implementation Details

### Patching Strategy

The solution patches `window.customElements.define` to:

1. Check if element is already defined before attempting registration
2. Silently skip if already defined (prevents errors)
3. Catch and ignore "already been defined" errors
4. Re-throw unexpected errors

### Why This Works

**Original Problem:**

```javascript
// Third-party library code (overlay_bundle.js)
customElements.define("mce-autosize-textarea", MyElement); // First call - OK
customElements.define("mce-autosize-textarea", MyElement); // Second call - ERROR!
```

**With Patch:**

```javascript
// Patched customElements.define
customElements.define("mce-autosize-textarea", MyElement); // First call - OK
customElements.define("mce-autosize-textarea", MyElement); // Second call - silently skipped, no error
```

## Integration Steps

### Step 1: Import Early Initialization

Add to your application entry point (e.g., `index.tsx` or `main.tsx`):

```typescript
// Import BEFORE any other code that might load third-party libraries
import "./utils/initCustomElementGuard";

// ... rest of your imports
```

### Step 2: Verify Fix

1. **Refresh the browser** - The patch should be active
2. **Check console** - Should see:
   `[CustomElementGuard] customElements.define patched...`
3. **Trigger the error** - Perform actions that previously caused the duplicate
   registration error
4. **Verify** - Error should no longer occur, or should be caught and logged as
   debug message

## Expected Results

### Before Fix

- Error:
  `Uncaught Error: A custom element with name 'mce-autosize-textarea' has already been defined.`
- Application may crash or fail to load
- Console shows uncaught exception

### After Fix

- No error thrown
- Duplicate registration attempts are silently ignored
- Console shows debug message (in development):
  `[CustomElementGuard] Preventing duplicate registration of 'mce-autosize-textarea'`
- Application continues to work normally

## Files Created

1. ✅ `frontend/src/utils/customElementGuard.ts` - Core guard utility
2. ✅ `frontend/src/utils/initCustomElementGuard.ts` - Early initialization
   module
3. ✅ `docs/CUSTOM_ELEMENT_DUPLICATE_REGISTRATION_FIX.md` - This document

## Notes

- The patch is **non-invasive** - it only affects duplicate registration
  attempts
- **No breaking changes** - all existing functionality preserved
- Works with **any custom element**, not just `mce-autosize-textarea`
- **Development-friendly** - provides debug logging in development mode
- **Production-safe** - console statements are typically stripped by bundlers

## Alternative: Manual Usage

If you prefer not to patch globally, you can use `safeDefineCustomElement()`
directly:

```typescript
import { safeDefineCustomElement } from "./utils/customElementGuard";

// Instead of:
customElements.define("my-element", MyElement);

// Use:
safeDefineCustomElement("my-element", MyElement);
```

## Troubleshooting

### Patch Not Working

1. **Verify import order** - Ensure `initCustomElementGuard` is imported before
   libraries that register custom elements
2. **Check console** - Should see patch confirmation message
3. **Verify customElements API** - Ensure browser supports custom elements

### Still Seeing Errors

1. **Check error message** - If it's not "already been defined", it might be a
   different issue
2. **Verify patch is active** - Check console for patch confirmation
3. **Check import timing** - Library might be loading before the patch

## Status

✅ **Fix Implemented** - Ready for testing

Import `initCustomElementGuard` in your entry point to activate the fix!
