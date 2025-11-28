# E2E Tests for New Components

This directory contains end-to-end tests for the newly implemented components:

1. **Dashboard Diagnostics Section** (`dashboard-diagnostics.spec.ts`)
2. **Control Page Live Operations** (`control-live-operations.spec.ts`)
3. **Data Browser QA Snapshot** (`data-browser-qa-snapshot.spec.ts`)
4. **Combined Smoke Tests** (`new-components-combined.spec.ts`)

## Test Files

### `dashboard-diagnostics.spec.ts`

Tests the consolidated Diagnostics & Alerts section on the Dashboard page:

- ✅ Diagnostics section visibility
- ✅ Queue Overview Card with statistics
- ✅ Pointing Summary Card
- ✅ Dead Letter Queue Stats
- ✅ Circuit Breaker Status
- ✅ Health Checks card
- ✅ ESE Candidates Panel
- ✅ Navigation buttons (View detailed diagnostics, Open Health Page, Open
  Observing View)
- ✅ Loading states
- ✅ Responsive layout

**Test Tags:** `@regression`

### `control-live-operations.spec.ts`

Tests the Live Operations card on the Control page:

- ✅ Live Operations card visibility
- ✅ Job statistics display (Total, Running, Completed, Failed)
- ✅ Success rate and average duration chips
- ✅ Active executions list
- ✅ Open Pipeline Monitor button navigation
- ✅ Loading states
- ✅ Empty state handling
- ✅ Layout positioning
- ✅ Responsive design
- ✅ Data update handling

**Test Tags:** `@regression`

### `data-browser-qa-snapshot.spec.ts`

Tests the QA Snapshot card in the Data Browser Published tab:

- ✅ QA Snapshot card visibility in Published tab
- ✅ ESE candidate counts (Active, Resolved, Warnings, Total)
- ✅ Top ESE candidates table
- ✅ Empty state handling
- ✅ Refresh button functionality
- ✅ Open QA Tools button navigation
- ✅ Loading states
- ✅ Card positioning above data table
- ✅ Responsive design
- ✅ Tab-specific visibility (only in Published tab)

**Test Tags:** `@regression`

### `new-components-combined.spec.ts`

Combined smoke tests for quick verification:

- ✅ All new components load without errors
- ✅ Navigation buttons work correctly

**Test Tags:** `@smoke`

## Running the Tests

### Run all new component tests:

```bash
cd /data/dsa110-contimg/frontend
npx playwright test tests/e2e/dashboard-diagnostics.spec.ts
npx playwright test tests/e2e/control-live-operations.spec.ts
npx playwright test tests/e2e/data-browser-qa-snapshot.spec.ts
npx playwright test tests/e2e/new-components-combined.spec.ts
```

### Run smoke tests only:

```bash
npx playwright test --grep "@smoke"
```

### Run regression tests:

```bash
npx playwright test --grep "@regression"
```

### Run with UI mode (interactive):

```bash
npx playwright test --ui tests/e2e/dashboard-diagnostics.spec.ts
```

### Run in headed browser:

```bash
npx playwright test --headed tests/e2e/dashboard-diagnostics.spec.ts
```

### Run with debug mode:

```bash
npx playwright test --debug tests/e2e/dashboard-diagnostics.spec.ts
```

## Prerequisites

1. **Backend API must be running** on `http://localhost:8000`
2. **Frontend dev server** should be running on `http://localhost:3210`
3. **Playwright browsers** must be installed:
   ```bash
   npx playwright install
   ```

## Test Dependencies

The tests use helper functions from:

- `tests/e2e/helpers/page-helpers.ts` - Navigation and waiting utilities
- `tests/e2e/fixtures/test-data.ts` - Test routes and API paths

## API Endpoints Tested

The tests verify integration with these backend endpoints:

- `/api/status` - Pipeline status and queue statistics
- `/api/pointing/history` - Pointing history for summary card
- `/api/dlq` - Dead Letter Queue statistics
- `/api/health` - Health check summary
- `/api/circuit-breakers` - Circuit breaker status
- `/api/ese/candidates` - ESE candidates for QA snapshot
- `/api/pipeline/metrics` - Pipeline metrics summary
- `/api/pipeline/executions` - Active pipeline executions

## Expected Behavior

### Dashboard Diagnostics Section

- Should be visible and expanded by default
- All cards should load their respective data
- Navigation buttons should route to correct pages
- Should handle API errors gracefully (show loading/error states)

### Control Page Live Operations

- Should appear in the right column (or stack on mobile)
- Should display current pipeline metrics
- Should show active executions or empty state message
- Should navigate to pipeline monitor when button clicked

### Data Browser QA Snapshot

- Should only appear in Published tab
- Should display ESE candidate counts and top candidates
- Should show empty state if no candidates exist
- Should refresh data when refresh button clicked
- Should navigate to QA page when button clicked

## Troubleshooting

### Tests fail with "No tests found"

- Verify Playwright config points to correct test directory
- Check that test files have `.spec.ts` extension
- Ensure test files are in `tests/e2e/` directory

### Tests fail with API errors

- Verify backend API is running on port 8000
- Check API endpoints are accessible
- Verify CORS is configured correctly

### Tests fail with navigation errors

- Verify frontend dev server is running on port 3210
- Check that routes are configured correctly
- Ensure React Router is set up properly

### Tests timeout

- Increase timeout in test file: `{ timeout: 30000 }`
- Check network connectivity
- Verify API responses are fast enough

## Test Coverage

These tests provide coverage for:

- ✅ Component rendering
- ✅ API integration
- ✅ User interactions (button clicks, navigation)
- ✅ Loading and error states
- ✅ Responsive layout
- ✅ Data display and formatting
- ✅ Navigation flows

## Maintenance

When updating components:

1. Update corresponding test file
2. Verify tests still pass
3. Add new test cases for new features
4. Update this README if test structure changes
