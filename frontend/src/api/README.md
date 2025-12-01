# API Module

This module contains API client code and type alignment tests.

## Files

- `client.ts` - Axios-based API client with error handling and interceptors
- `client.test.ts` - Unit tests for the API client
- `health.ts` - Health monitoring API hooks (React Query)
- `absurd.ts` - ABSURD task queue API functions
- `alignment.test.ts` - **Type alignment tests** (critical for frontend/backend sync)
- `resilience/` - Network resilience utilities

## Type Alignment Tests

The `alignment.test.ts` file validates that frontend TypeScript types match
actual backend API responses. This prevents issues like:

- Field name mismatches (`timeline_start` vs `window_start_iso`)
- Type mismatches (array vs Record)
- Missing optional fields

### Running Alignment Tests

```bash
# Unit tests with fixture data (fast, no backend needed)
npm run test:alignment

# Integration tests against live backend (requires backend on :8000)
npm run test:alignment:live

# Quick structural check against live API
npm run test:alignment:check
npm run test:alignment:check:verbose
```

### Automation Strategy

The alignment tests are automated at multiple levels:

#### 1. Compile-Time Validation (TypeScript)

Fixtures use `satisfies` keyword to ensure they match TypeScript types:

```typescript
const FIXTURES = {
  systemHealth: {
    overall_status: "healthy",
    services: [{ name: "api", status: "running" }],
    summary: { total: 1, running: 1 },
  } satisfies SystemHealthReport, // ← Compile error if structure wrong
};
```

**When this catches issues:** Immediately when you change type definitions.

#### 2. Unit Tests (Vitest)

Run with `npm run test:alignment` - no backend needed:

- Validates fixtures have required keys
- Checks array vs Record patterns
- Documents expected field names
- Fast (~2 seconds)

**When this catches issues:** In CI on every PR, locally during development.

#### 3. Integration Tests (Live Backend)

Run with `npm run test:alignment:live`:

- Fetches real API responses
- Validates structure matches types
- Catches backend-only changes

**When this catches issues:** In CI with backend service, locally with backend running.

#### 4. Quick API Check (Node.js Script)

Run with `npm run test:alignment:check`:

- Lightweight structural validation
- No test framework overhead
- Exit code 0/1 for CI
- JSON output for parsing

**When this catches issues:** Pre-commit hooks, CI health checks.

### CI Integration

The `.github/workflows/api-alignment.yml` workflow:

1. **On PR** (paths: `frontend/src/types/**`, `frontend/src/api/**`):

   - Runs TypeScript type check
   - Runs alignment unit tests
   - Comments on PR if type files changed

2. **On Push** (master/master-dev):
   - Same as PR checks
   - Can trigger integration tests with backend service

### When to Update Fixtures

Update `alignment.test.ts` fixtures when:

1. **Backend API changes** - Capture new response, update fixture
2. **Frontend type changes** - Ensure fixtures still satisfy types
3. **New endpoints added** - Add corresponding fixture and tests

### Updating Fixtures from Live API

```bash
# Start backend
cd ../backend && uvicorn dsa110_contimg.api.main:app --port 8000

# Check current alignment
npm run test:alignment:check:verbose

# If changes needed, fetch live responses:
curl http://localhost:8000/api/v1/health/system | jq '.' > /tmp/system.json

# Update fixture in alignment.test.ts to match
```

### Test Structure

```
Health API Type Alignment
├── SystemHealthReport
│   ├── services should be an array, not a Record
│   ├── validates required fields
│   └── summary has correct structure
├── ValidityTimeline
│   ├── uses correct field names
│   └── windows array entries have correct field names
├── FluxMonitoringSummary
│   └── handles normal and empty responses
├── PointingStatus
└── AlertsResponse

Absurd API Type Alignment
├── Task
├── QueueStats
└── Worker

Core Data API Type Alignment
├── ImageSummary / ImageDetail
├── SourceSummary / SourceDetail
├── MSMetadata
└── JobSummary / JobDetail

Common API Response Patterns
├── arrays are arrays, not Records
├── optional message field for uninitialized states
└── ISO timestamps are strings, MJD values are numbers

Live API Integration Tests (run with INTEGRATION_TEST=true)
├── GET /api/v1/health/system
├── GET /api/v1/health/validity-windows/timeline
├── GET /api/v1/health/flux-monitoring
├── GET /api/v1/health/pointing
└── GET /api/v1/health/alerts
```

### Key Lessons Learned

1. **Arrays vs Records**: Backend often returns arrays with `name` or `id`
   properties, not `Record<string, T>`. Always check API response structure.

2. **Optional message fields**: Many endpoints return `{ data: [], message: "Not initialized" }`
   when database tables are empty. Types should have optional `message` field.

3. **Field naming conventions**: Backend uses `snake_case`, TypeScript types
   should match exactly. Don't assume camelCase transformation.
