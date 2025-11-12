# JS9 Phase 3: Abstraction Layer Proposal

## Current Status

**Completed:**
- ✅ Phase 1: Utilities & Quick Wins
- ✅ Phase 2: Context Provider & State Management

**Remaining Issues:**
- **157** direct `window.JS9.*` calls across 13 files
- **956** lines in SkyViewer.tsx (still large)
- Only **3** components migrated to context
- Direct JS9 API access scattered throughout codebase

## Phase 3: JS9 Service Abstraction Layer

### Objective
Create a clean abstraction layer (`JS9Service`) that wraps common JS9 APIs, providing:
- Type-safe interfaces
- Consistent error handling
- Easier testing (mockable)
- Better maintainability
- Backward compatibility

### Proposed Structure

```typescript
// frontend/src/services/js9/JS9Service.ts

export interface JS9Service {
  // Display Management
  getDisplay(displayId: string): Display | null;
  getAllDisplays(): Display[];
  createDisplay(displayId: string, container: HTMLElement): Promise<Display>;
  
  // Image Operations
  loadImage(displayId: string, imagePath: string, options?: LoadOptions): Promise<void>;
  getImageId(displayId: string): string | null;
  hasImage(displayId: string): boolean;
  
  // View Operations
  setZoom(displayId: string, zoom: number | 'fit' | 'in' | 'out'): void;
  getZoom(displayId: string): number;
  setPan(displayId: string, ra: number, dec: number): void;
  getPan(displayId: string): { x: number; y: number } | null;
  
  // Colormap & Display
  setColormap(displayId: string, colormap: string): void;
  getColormap(displayId: string): string | null;
  setScale(displayId: string, scale: string): void;
  setGrid(displayId: string, visible: boolean): void;
  
  // WCS Operations
  pixToWCS(displayId: string, x: number, y: number): { ra: number; dec: number } | null;
  wcsToPix(displayId: string, ra: number, dec: number): { x: number; y: number } | null;
  getWCS(displayId: string): WCSInfo | null;
  
  // Regions
  getRegions(displayId: string): Region[];
  addRegion(displayId: string, region: Region): void;
  removeRegion(displayId: string, regionId: string): void;
  
  // Events
  addEventListener(event: string, handler: Function): void;
  removeEventListener(event: string, handler: Function): void;
  
  // Utilities
  getVal(displayId: string, key: string): any;
  setVal(displayId: string, key: string, value: any): void;
}

// Implementation
export class JS9ServiceImpl implements JS9Service {
  // Wraps window.JS9 calls with error handling and type safety
}

// Hook for React components
export function useJS9Service(): JS9Service {
  // Returns service instance from context or creates default
}
```

### Benefits

1. **Type Safety**
   - Proper TypeScript interfaces
   - No more `any` types for JS9 objects
   - Compile-time error checking

2. **Error Handling**
   - Consistent error handling across all JS9 operations
   - Better error messages
   - Graceful degradation

3. **Testability**
   - Easy to mock for unit tests
   - Can test components without JS9 loaded
   - Isolated test scenarios

4. **Maintainability**
   - Single place to update JS9 API calls
   - Easier to handle API changes
   - Clear separation of concerns

5. **Backward Compatibility**
   - Can fall back to direct `window.JS9` if needed
   - Gradual migration possible
   - No breaking changes

### Migration Strategy

**Step 1: Create Service Interface**
- Define `JS9Service` interface
- Implement `JS9ServiceImpl` wrapping `window.JS9`
- Add to context

**Step 2: Migrate High-Impact Components**
- SkyViewer.tsx (most complex)
- ImageControls.tsx (many API calls)
- WCSDisplay.tsx (WCS operations)

**Step 3: Migrate Remaining Components**
- ImageMetadata.tsx
- ProfileTool.tsx
- Plugins (PhotometryPlugin, CASAnalysisPlugin, etc.)

**Step 4: Remove Direct window.JS9 Access**
- Update ESLint rules to warn on direct access
- Document preferred patterns

### Example Migration

**Before:**
```typescript
const display = window.JS9.displays?.find((d: any) => d.id === displayId);
if (display?.im) {
  window.JS9.SetZoom(display.im.id, 2);
  window.JS9.SetColormap(display.im.id, 'heat');
}
```

**After:**
```typescript
const js9Service = useJS9Service();
const zoom = js9Service.getZoom(displayId);
js9Service.setZoom(displayId, 2);
js9Service.setColormap(displayId, 'heat');
```

### Estimated Impact

- **157** direct `window.JS9.*` calls → **0** (all via service)
- **Type safety** → **100%** (no more `any` types)
- **Testability** → **Significantly improved** (mockable service)
- **Maintainability** → **Much better** (single abstraction layer)

### Timeline

- **Week 1:** Create service interface and implementation
- **Week 2:** Migrate high-impact components
- **Week 3:** Migrate remaining components
- **Week 4:** Testing, documentation, cleanup

### Alternative: Phase 3.5 - Component Splitting

If abstraction layer is too much, we could split Phase 3 into:
- **Phase 3a:** Component Splitting (SkyViewer → smaller components)
- **Phase 3b:** Service Abstraction (after components are smaller)

### Recommendation

**Proceed with Phase 3: Abstraction Layer**

This provides the most value:
- Reduces technical debt
- Improves maintainability
- Enables better testing
- Sets foundation for future improvements

The abstraction layer will make Phase 4 (State Management) and Phase 5 (Component Splitting) much easier.

