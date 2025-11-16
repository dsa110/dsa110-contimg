# Source Monitoring Page - Code Analysis & Bug Report

## Summary

Analysis of `frontend/src/pages/SourceMonitoringPage.tsx` for potential bugs,
issues, and improvements.

## Issues Found

### 1. **CRITICAL: Missing Dependency in useMemo for columnDefs**

**Location**: Line 95-178

**Issue**: The `columnDefs` useMemo hook uses `navigate` function inside the
cellRenderer but doesn't include it in the dependency array. This can cause
stale closures.

```typescript
const columnDefs = useMemo<ColDef<SourceTimeseries>[]>(
  () => [
    {
      // ...
      cellRenderer: (params: any) => (
        <span onClick={() => navigate(`/sources/${encodeURIComponent(params.value)}`)}>
          {params.value}
        </span>
      ),
    },
  ],
  [] // ❌ Missing 'navigate' dependency
);
```

**Impact**:

- The navigate function reference might become stale
- Could cause navigation to fail or use outdated route handlers
- React will warn about missing dependencies in strict mode

**Fix**:

```typescript
const columnDefs = useMemo<ColDef<SourceTimeseries>[]>(
  () => [
    // ... column definitions
  ],
  [navigate] // ✅ Add navigate to dependencies
);
```

---

### 2. **MEDIUM: Potential Null/Undefined Handling in Value Formatters**

**Location**: Lines 120, 126, 137, 143, 149, 174

**Issue**: Value formatters may receive null/undefined values without proper
checks.

**Examples**:

```typescript
// Line 120 - Could fail if ra_deg is null
valueFormatter: (params) => params.value?.toFixed(5),

// Line 137 - Could fail if mean_flux_jy is null/undefined
valueFormatter: (params) => (params.value * 1000).toFixed(2),

// Line 174 - Safe with optional chaining
valueFormatter: (params) => `${params.value?.length || 0} points`,
```

**Impact**:

- Runtime errors if data contains null/undefined values
- Grid cells may display "NaN" or "undefined"
- Poor user experience

**Fix**:

```typescript
valueFormatter: (params) => {
  if (params.value == null) return "—";
  return params.value.toFixed(5);
},

valueFormatter: (params) => {
  if (params.value == null) return "—";
  return (params.value * 1000).toFixed(2);
},
```

---

### 3. **MEDIUM: Search Logic Issue with Advanced Filters Only**

**Location**: Lines 53-75

**Issue**: When `showAdvancedFilters` is true but no `source_id` is provided,
the search request is created with only filter parameters. However, based on the
analysis document, the backend API may only support `source_id` and ignore other
parameters.

```typescript
const handleSearch = () => {
  const request: SourceSearchRequest = {};

  if (sourceId.trim()) {
    request.source_id = sourceId.trim();
  } else if (!showAdvancedFilters) {
    // Early return - good
    setSearchRequest(null);
    return;
  }

  if (showAdvancedFilters) {
    request.limit = 1000;
    request.variability_threshold = variabilityThreshold;
    request.ese_only = eseOnly;
    request.dec_min = decMin;
    request.dec_max = decMax;
  } else {
    request.limit = 100;
  }

  setSearchRequest(request); // ⚠️ May create request with only filters, no source_id
};
```

**Impact**:

- Users can trigger searches with only advanced filters
- Backend may ignore these filters and return empty results
- Misleading UX - users think filters work but they don't

**Recommendation**:

- Add validation to prevent search when only advanced filters are set (if
  backend doesn't support them)
- Or add UI feedback indicating backend limitation
- Document backend API support status

---

### 4. **LOW: Unused gridRef**

**Location**: Line 49, 309

**Issue**: `gridRef` is created but never used for any grid operations.

```typescript
const gridRef = useRef<AgGridReact>(null);
// ...
<AgGridReact ref={gridRef} ... />
```

**Impact**:

- Minor - no functional impact
- Could be useful for programmatic grid operations (export, select all, etc.)

**Recommendation**: Either remove it or use it for useful features like:

- Export to CSV
- Select all rows
- Scroll to specific row

---

### 5. **LOW: Type Safety - Using 'any' in cellRenderer**

**Location**: Lines 103, 164

**Issue**: Using `any` type reduces type safety.

```typescript
cellRenderer: (params: any) => (
  // ...
)
```

**Impact**:

- Loss of type safety
- Potential runtime errors if AG Grid API changes
- Harder to catch bugs during development

**Fix**:

```typescript
import type { ICellRendererParams } from "ag-grid-community";

cellRenderer: (params: ICellRendererParams<SourceTimeseries>) => (
  // ...
)
```

---

### 6. **MEDIUM: Missing Error Details**

**Location**: Lines 299-303

**Issue**: Generic error message doesn't provide useful debugging information.

```typescript
{error && (
  <Alert severity="warning">
    Source monitoring not available. This feature requires enhanced API endpoints.
  </Alert>
)}
```

**Impact**:

- Users can't understand what went wrong
- Developers can't debug issues easily
- No distinction between different error types (network, 404, 500, etc.)

**Fix**:

```typescript
{error && (
  <Alert severity="error">
    <AlertTitle>Error loading sources</AlertTitle>
    {error instanceof Error ? error.message : "Source monitoring not available. This feature requires enhanced API endpoints."}
    {process.env.NODE_ENV === "development" && (
      <pre style={{ fontSize: "0.75rem", marginTop: 8 }}>
        {JSON.stringify(error, null, 2)}
      </pre>
    )}
  </Alert>
)}
```

---

### 7. **LOW: Hard-coded Values**

**Location**: Multiple places

**Issue**: Magic numbers and strings scattered throughout code.

```typescript
request.limit = 1000; // Line 65
request.limit = 100;  // Line 71
setVariabilityThreshold(5); // Line 44, 79
setDecMin(-90); // Line 46, 81
setDecMax(90); // Line 47, 82
height: 600, // Line 307
paginationPageSize={20} // Line 314
```

**Impact**:

- Hard to maintain
- Inconsistent if used elsewhere
- No single source of truth

**Recommendation**: Extract to constants:

```typescript
const DEFAULT_LIMIT = 100;
const ADVANCED_FILTER_LIMIT = 1000;
const DEFAULT_VARIABILITY_THRESHOLD = 5;
const DEC_RANGE = { min: -90, max: 90 };
const GRID_HEIGHT = 600;
const PAGINATION_PAGE_SIZE = 20;
```

---

### 8. **MEDIUM: Potential Race Condition in Search**

**Location**: Lines 53-75

**Issue**: If user clicks search multiple times quickly, multiple requests could
be in flight.

**Impact**:

- Unnecessary API calls
- Results could arrive out of order
- Wasted resources

**Recommendation**: Add debouncing or disable button during search:

```typescript
<Button
  variant="contained"
  startIcon={<Search />}
  onClick={handleSearch}
  disabled={(!sourceId.trim() && !showAdvancedFilters) || isLoading}
>
  Search
</Button>
```

---

### 9. **LOW: Missing Accessibility Features**

**Location**: Throughout component

**Issues**:

- No ARIA labels on interactive elements
- Keyboard navigation not explicitly handled
- Screen reader support could be improved

**Recommendation**: Add ARIA attributes:

```typescript
<TextField
  label="Source ID"
  aria-label="Source ID search input"
  // ...
/>
<Button
  aria-label="Search for sources"
  // ...
/>
```

---

### 10. **MEDIUM: Grid Theme Class Name**

**Location**: Line 307

**Issue**: Using `ag-theme-alpine-dark` but no light theme variant available.

```typescript
<Box className="ag-theme-alpine-dark" sx={{ height: 600, width: "100%" }}>
```

**Impact**:

- May not match application theme
- Could be jarring if app uses light theme

**Recommendation**: Make theme configurable or match app theme.

---

## Summary of Priority

### High Priority (Should Fix)

1. Missing dependency in columnDefs useMemo (#1)

### Medium Priority (Should Consider)

2. Null/undefined handling in value formatters (#2)
3. Search logic with advanced filters only (#3)
4. Missing error details (#6)
5. Potential race condition (#8)

### Low Priority (Nice to Have)

4. Unused gridRef (#4)
5. Type safety improvements (#5)
6. Hard-coded values (#7)
7. Accessibility (#9)
8. Grid theme (#10)

---

## Testing Recommendations

1. **Test with null/undefined data**: Verify value formatters handle missing
   values gracefully
2. **Test rapid search clicks**: Verify no race conditions or duplicate requests
3. **Test advanced filters only**: Verify behavior when no source_id is provided
4. **Test error scenarios**: Network failures, 404, 500 errors
5. **Test navigation**: Verify source ID links work correctly
6. **Test with empty results**: Verify empty state displays correctly
7. **Test filter combinations**: All possible filter combinations

---

## Code Quality Improvements

1. Extract constants to configuration
2. Add TypeScript strict types
3. Add unit tests for handleSearch logic
4. Add integration tests for API interactions
5. Improve error handling and user feedback
6. Add loading states for better UX
7. Consider adding search history/autocomplete
