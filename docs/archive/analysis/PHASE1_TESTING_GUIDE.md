# Phase 1 Testing Guide

## Overview

This guide provides testing instructions for Phase 1 components: GenericTable, Dashboard Store, SourceDetailPage, and ImageDetailPage.

## Prerequisites

1. **Backend API running**
   - Ensure the FastAPI backend is running
   - Default: `http://localhost:8000`
   - Or set `VITE_API_URL` environment variable

2. **Frontend development server**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Zustand installed** ✅
   ```bash
   cd frontend
   npm install zustand
   ```

## Testing GenericTable Component

### Manual Testing

1. **Navigate to a page that uses GenericTable**
   - Example: Create a test page or use an existing page
   - Or navigate to `/sources/:sourceId` and check the detections table

2. **Test Features:**

   **Pagination:**
   - [ ] Navigate between pages
   - [ ] Verify page numbers update correctly
   - [ ] Verify "Showing X to Y of Z results" displays correctly

   **Search:**
   - [ ] Enter search text
   - [ ] Verify results filter correctly
   - [ ] Verify search resets to page 1
   - [ ] Clear search and verify all results return

   **Sorting:**
   - [ ] Click column headers to sort
   - [ ] Verify ascending/descending toggle works
   - [ ] Verify sort indicator appears
   - [ ] Verify sorting resets to page 1

   **Column Visibility:**
   - [ ] Click visibility icon
   - [ ] Toggle columns on/off
   - [ ] Verify columns show/hide correctly
   - [ ] Verify at least one column remains visible

   **Export:**
   - [ ] Click export button
   - [ ] Verify CSV file downloads
   - [ ] Open CSV and verify data is correct
   - [ ] Verify only visible columns are exported

   **Row Click:**
   - [ ] Click on a row (if `onRowClick` is provided)
   - [ ] Verify navigation works correctly

   **Loading State:**
   - [ ] Verify loading spinner appears while fetching
   - [ ] Verify loading state clears when data arrives

   **Error State:**
   - [ ] Simulate API error (stop backend or use invalid endpoint)
   - [ ] Verify error message displays
   - [ ] Verify error is user-friendly

### Unit Testing

Create test file: `frontend/src/components/GenericTable.test.tsx`

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import GenericTable from './GenericTable';

// Mock API client
jest.mock('../api/client', () => ({
  apiClient: {
    get: jest.fn(),
  },
}));

describe('GenericTable', () => {
  it('renders with data', async () => {
    // Test implementation
  });
  
  it('handles pagination', async () => {
    // Test implementation
  });
  
  // ... more tests
});
```

## Testing Dashboard Store

### Manual Testing

1. **Open browser console**
   - Navigate to any page
   - Open DevTools console

2. **Test State Transitions:**

```typescript
// In browser console or React DevTools
import { useDashboardStore } from './stores/dashboardStore';

// Get store instance
const store = useDashboardStore.getState();

// Test idle state
store.transitionTo('idle', { status: 'healthy' });
console.log(store.state); // Should show idle state

// Test autonomous state
store.transitionTo('autonomous', {
  streamingPipeline: {
    status: 'running',
    currentOperations: [],
    metrics: { throughput: 100, latency: 50, errorRate: 0 },
    config: {},
  },
});
console.log(store.state); // Should show autonomous state

// Test helper functions
console.log(store.isIdle()); // false (we're in autonomous)
console.log(store.isAutonomous()); // true

// Test context updates
store.setUserIntent({
  type: 'view-source',
  sourceId: 'test-123',
});
console.log(store.context.userIntent); // Should show intent

// Test workflow steps
store.addWorkflowStep({
  id: 'step-1',
  type: 'navigation',
  timestamp: new Date(),
  data: { page: 'source-detail' },
});
console.log(store.context.workflowHistory.length); // Should be 1
```

### Expected Behavior

- [ ] State transitions update correctly
- [ ] Helper functions return correct boolean values
- [ ] Context updates persist
- [ ] Recent actions limited to 10
- [ ] Workflow history limited to 50
- [ ] State persists across component re-renders

## Testing SourceDetailPage

### Manual Testing

1. **Navigate to source detail page**
   ```
   http://localhost:3000/sources/{sourceId}
   ```

2. **Test Features:**

   **Page Load:**
   - [ ] Page loads without errors
   - [ ] Loading spinner appears initially
   - [ ] Source data displays correctly
   - [ ] Error state works if source not found

   **Three-Column Layout:**
   - [ ] Details column displays source information
   - [ ] Sky view column shows placeholder (Aladin Lite)
   - [ ] Comments column shows placeholder

   **Details Section:**
   - [ ] Source name displays
   - [ ] Coordinates formatted correctly (RA/Dec)
   - [ ] Flux statistics display
   - [ ] Measurement counts display
   - [ ] ESE metrics display (if applicable)
   - [ ] ESE candidate badge shows (if applicable)
   - [ ] New source badge shows (if applicable)

   **Navigation:**
   - [ ] Previous button navigates (if available)
   - [ ] Next button navigates (if available)
   - [ ] External links (SIMBAD, NED) open in new tab

   **Collapsible Sections:**
   - [ ] Light curve section toggles
   - [ ] Detections table section toggles
   - [ ] Related sources section toggles (if applicable)
   - [ ] Sections remember expanded state

   **Detections Table:**
   - [ ] GenericTable displays correctly
   - [ ] Pagination works
   - [ ] Search works
   - [ ] Sorting works
   - [ ] Row clicks navigate to detection detail

   **API Integration:**
   - [ ] Source data fetched from `/api/sources/:sourceId`
   - [ ] Detections fetched from `/api/sources/:sourceId/detections`
   - [ ] Navigation IDs fetched (if endpoint exists)

### Test Cases

**Happy Path:**
- Source exists and has detections
- All data displays correctly
- Navigation works

**Edge Cases:**
- Source has no detections
- Source has no related sources
- Source is not an ESE candidate
- Source is not new
- Previous/next navigation unavailable

**Error Cases:**
- Source ID doesn't exist (404)
- API server down (network error)
- Invalid source ID format

## Testing ImageDetailPage

### Manual Testing

1. **Navigate to image detail page**
   ```
   http://localhost:3000/images/{imageId}
   ```

2. **Test Features:**

   **Page Load:**
   - [ ] Page loads without errors
   - [ ] Loading spinner appears initially
   - [ ] Image data displays correctly
   - [ ] Error state works if image not found

   **Three-Column Layout:**
   - [ ] Details column displays image information
   - [ ] Sky view column shows placeholder
   - [ ] Comments column shows placeholder

   **Details Section:**
   - [ ] Image name displays
   - [ ] Coordinates formatted correctly
   - [ ] Beam parameters display (BMAJ, BMIN, BPA)
   - [ ] RMS statistics display
   - [ ] Frequency/bandwidth display
   - [ ] Measurement and run counts display
   - [ ] Path displays (if available)

   **Collapsible Sections:**
   - [ ] Measurements table section toggles
   - [ ] Runs table section toggles
   - [ ] Sections remember expanded state

   **Measurements Table:**
   - [ ] GenericTable displays correctly
   - [ ] All measurement columns display
   - [ ] Pagination works
   - [ ] Search works
   - [ ] Sorting works
   - [ ] Row clicks navigate to measurement detail

   **Runs Table:**
   - [ ] GenericTable displays correctly
   - [ ] All run columns display
   - [ ] Pagination works
   - [ ] Row clicks navigate to run detail

### Test Cases

**Happy Path:**
- Image exists and has measurements
- Image is included in runs
- All data displays correctly

**Edge Cases:**
- Image has no measurements
- Image is not in any runs
- Image path not available

**Error Cases:**
- Image ID doesn't exist (404)
- API server down
- Invalid image ID format

## API Endpoints Required

### SourceDetailPage

- `GET /api/sources/:sourceId` - Get source details
  ```json
  {
    "id": "string",
    "name": "string",
    "wavg_ra": 0.0,
    "wavg_dec": 0.0,
    ...
  }
  ```

- `GET /api/sources/:sourceId/detections` - Get source detections (paginated)
  ```json
  {
    "results": [...],
    "count": 100
  }
  ```

- `GET /api/sources/:sourceId/navigation` - Get previous/next IDs (optional)
  ```json
  {
    "previousId": "string | null",
    "nextId": "string | null"
  }
  ```

### ImageDetailPage

- `GET /api/images/:imageId` - Get image details
  ```json
  {
    "id": "string",
    "name": "string",
    "ra": 0.0,
    "dec": 0.0,
    ...
  }
  ```

- `GET /api/images/:imageId/measurements` - Get image measurements (paginated)
  ```json
  {
    "results": [...],
    "count": 100
  }
  ```

- `GET /api/images/:imageId/runs` - Get runs containing image (paginated)
  ```json
  {
    "results": [...],
    "count": 10
  }
  ```

- `GET /api/images/:imageId/navigation` - Get previous/next IDs (optional)

## Mock Data for Testing

If API endpoints don't exist yet, create mock data:

```typescript
// frontend/src/mocks/sourceMock.ts
export const mockSource = {
  id: 'test-source-1',
  name: 'J123456.78+123456.7',
  wavg_ra: 123.456789,
  wavg_dec: 12.345678,
  // ... more fields
};

// frontend/src/mocks/imageMock.ts
export const mockImage = {
  id: 'test-image-1',
  name: 'image_20240101_120000.fits',
  ra: 123.456789,
  dec: 12.345678,
  // ... more fields
};
```

## Integration Testing Checklist

### GenericTable Integration

- [ ] Works with real API endpoints
- [ ] Handles API pagination correctly
- [ ] Handles API search parameters
- [ ] Handles API sorting parameters
- [ ] Handles API errors gracefully
- [ ] Works with different data types
- [ ] Column links navigate correctly

### SourceDetailPage Integration

- [ ] Fetches source data correctly
- [ ] Fetches detections correctly
- [ ] Displays all source fields
- [ ] Handles missing optional fields
- [ ] Navigation works
- [ ] External links work
- [ ] GenericTable integration works

### ImageDetailPage Integration

- [ ] Fetches image data correctly
- [ ] Fetches measurements correctly
- [ ] Fetches runs correctly
- [ ] Displays all image fields
- [ ] Handles missing optional fields
- [ ] Navigation works
- [ ] GenericTable integration works

### Dashboard Store Integration

- [ ] State persists across page navigation
- [ ] State updates trigger re-renders
- [ ] Multiple components can access store
- [ ] State transitions don't cause errors
- [ ] Context updates work correctly

## Performance Testing

### GenericTable

- [ ] Handles large datasets (1000+ rows)
- [ ] Pagination loads quickly
- [ ] Search is responsive
- [ ] Sorting is responsive
- [ ] Export doesn't freeze browser

### Detail Pages

- [ ] Page loads in < 2 seconds
- [ ] Tables load in < 1 second
- [ ] No unnecessary re-renders
- [ ] Smooth transitions

## Browser Compatibility

Test in:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari
- [ ] Mobile browsers (responsive design)

## Known Issues / TODOs

1. **Aladin Lite Integration**
   - Placeholder in place
   - Need to add Aladin Lite script/package
   - Need to initialize in component

2. **Light Curve Visualization**
   - Placeholder in place
   - Need to create Plotly component
   - Need API endpoint for light curve data

3. **Comments System**
   - Placeholder in place
   - Need to create CommentsPanel component
   - Need API endpoints for comments

4. **Navigation IDs**
   - Currently returns null
   - Need API endpoint or calculate client-side

5. **JS9 Integration** (for ImageDetailPage)
   - Not yet implemented
   - Can add FITS viewer later

## Success Criteria

Phase 1 is complete when:

- ✅ GenericTable works with real APIs
- ✅ SourceDetailPage displays source data correctly
- ✅ ImageDetailPage displays image data correctly
- ✅ Dashboard store transitions work
- ✅ All components handle errors gracefully
- ✅ All components have loading states
- ✅ No TypeScript errors
- ✅ No console errors in browser
- ✅ Responsive design works

## Next Steps After Testing

1. Fix any bugs found
2. Add missing API endpoints
3. Integrate Aladin Lite
4. Create light curve visualization
5. Create comments component
6. Add unit tests
7. Add integration tests
8. Document API endpoints
9. Create user guide

