# Phase 3a: Component Splitting Plan

## Current State

- **SkyViewer.tsx**: 956 lines
- **14** hooks (useEffect, useLayoutEffect, useCallback, useRef, useState)
- **5** major responsibilities mixed together

## Identified Sections

1. **JS9 Initialization** (~lines 64-290)
   - Wait for JS9 availability
   - Create display
   - Configure JS9 options
   - Handle initialization errors

2. **Content Preservation** (~lines 290-353)
   - useLayoutEffect to preserve JS9 content
   - MutationObserver to detect React clearing content
   - Restore JS9 display when needed

3. **Image Loading** (~lines 353-739)
   - Load image when path changes
   - Handle loading states
   - Hide JS9 loading indicators
   - Error handling and retries

4. **Resize Handling** (~lines 739-800)
   - Window resize listener
   - Container resize observer
   - JS9 display resize

5. **UI Rendering** (~lines 800-956)
   - Loading spinner
   - Error display
   - Empty state
   - JS9 container div

## Proposed Split

### Custom Hooks

1. **`useJS9Initialization`**
   - Handles JS9 availability checking
   - Creates and configures display
   - Returns: `{ initialized, error, initialize }`

2. **`useJS9ImageLoader`**
   - Handles image loading logic
   - Manages loading/error states
   - Returns: `{ loading, error, loadImage, imageLoaded }`

3. **`useJS9ContentPreservation`**
   - Preserves JS9 content across React renders
   - Detects and restores cleared content
   - Returns: `{ preserveContent }`

4. **`useJS9Resize`**
   - Handles window/container resize
   - Resizes JS9 display
   - Returns: `{ handleResize }`

### Main Component

**`SkyViewer.tsx`** (reduced to ~200-300 lines)
- Uses all hooks
- Manages props
- Renders UI
- Coordinates between hooks

## Benefits

1. **Separation of Concerns**
   - Each hook has single responsibility
   - Easier to understand and maintain

2. **Testability**
   - Test hooks independently
   - Mock dependencies easily
   - Isolated test scenarios

3. **Reusability**
   - Hooks can be reused in other components
   - Share initialization logic
   - Share image loading logic

4. **Maintainability**
   - Smaller, focused files
   - Easier to find and fix bugs
   - Clearer code organization

## File Structure

```
frontend/src/components/Sky/
├── SkyViewer.tsx (main component, ~200-300 lines)
└── hooks/
    ├── useJS9Initialization.ts (~150 lines)
    ├── useJS9ImageLoader.ts (~200 lines)
    ├── useJS9ContentPreservation.ts (~100 lines)
    └── useJS9Resize.ts (~80 lines)
```

## Migration Strategy

1. **Extract hooks one by one**
   - Start with `useJS9Initialization` (most isolated)
   - Then `useJS9Resize` (simple)
   - Then `useJS9ContentPreservation` (moderate complexity)
   - Finally `useJS9ImageLoader` (most complex)

2. **Test after each extraction**
   - Verify functionality unchanged
   - Check for regressions
   - Update tests

3. **Refactor main component**
   - Use extracted hooks
   - Simplify component logic
   - Clean up imports

## Success Metrics

- SkyViewer.tsx: **< 300 lines** (from 956)
- Each hook: **< 200 lines**
- Test coverage: **Maintained or improved**
- Functionality: **100% preserved**

