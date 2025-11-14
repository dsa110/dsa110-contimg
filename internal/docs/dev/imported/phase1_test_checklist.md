# Phase 1 Testing Checklist

## Test Environment Setup

- [ ] Backend server running on port 8000
- [ ] Frontend dev server running (if testing UI)
- [ ] Database accessible (DLQ SQLite database)
- [ ] Required Python packages installed (casa6 environment)

## 1. Backend API Testing

### 1.1 Health Endpoints

- [ ] `GET /health/liveness` - Returns 200 OK
- [ ] `GET /health/readiness` - Returns 200 OK
- [ ] `GET /api/health/summary` - Returns comprehensive health summary
  - [ ] Contains `status` field (healthy/degraded/unhealthy)
  - [ ] Contains `checks` object
  - [ ] Contains `circuit_breakers` array
  - [ ] Contains `dlq_stats` object
  - [ ] Contains `timestamp` field

### 1.2 Dead Letter Queue Endpoints

#### Stats Endpoint

- [ ] `GET /api/operations/dlq/stats` - Returns DLQ statistics
  - [ ] Response contains: `total`, `pending`, `retrying`, `resolved`, `failed`
  - [ ] All fields are integers >= 0
  - [ ] `total = pending + retrying + resolved + failed`

#### List Items Endpoint

- [ ] `GET /api/operations/dlq/items` - Returns list of DLQ items
  - [ ] Returns array of items
  - [ ] Each item has required fields: `id`, `component`, `operation`,
        `error_type`, `error_message`, `context`, `created_at`, `retry_count`,
        `status`
  - [ ] Default limit is 100
  - [ ] `GET /api/operations/dlq/items?limit=10` - Respects limit parameter
  - [ ] `GET /api/operations/dlq/items?offset=5` - Respects offset parameter
  - [ ] `GET /api/operations/dlq/items?component=ese_detection` - Filters by
        component
  - [ ] `GET /api/operations/dlq/items?status=pending` - Filters by status
  - [ ] `GET /api/operations/dlq/items?component=ese_detection&status=pending&limit=5` -
        Multiple filters work together

#### Item Detail Endpoint

- [ ] `GET /api/operations/dlq/items/{item_id}` - Returns specific item
  - [ ] Returns complete item details
  - [ ] `GET /api/operations/dlq/items/99999` - Returns 404 for non-existent
        item

#### Item Actions

- [ ] `POST /api/operations/dlq/items/{item_id}/retry` - Marks item as retrying
  - [ ] Request body accepts optional `note` field
  - [ ] Returns success response
  - [ ] Item status changes to "retrying"
- [ ] `POST /api/operations/dlq/items/{item_id}/resolve` - Marks item as
      resolved
  - [ ] Request body accepts optional `note` field
  - [ ] Returns success response
  - [ ] Item status changes to "resolved"
  - [ ] `resolved_at` timestamp is set
- [ ] `POST /api/operations/dlq/items/{item_id}/fail` - Marks item as failed
  - [ ] Request body accepts optional `note` field
  - [ ] Returns success response
  - [ ] Item status changes to "failed"

### 1.3 Circuit Breaker Endpoints

#### List Circuit Breakers

- [ ] `GET /api/operations/circuit-breakers` - Returns all circuit breakers
  - [ ] Returns array with 3 circuit breakers: `ese_detection`,
        `calibration_solve`, `photometry`
  - [ ] Each breaker has: `name`, `state`, `failure_count`, `last_failure_time`,
        `recovery_timeout`
  - [ ] State values are: "closed", "open", or "half_open"

#### Individual Circuit Breaker

- [ ] `GET /api/operations/circuit-breakers/ese_detection` - Returns
      ese_detection breaker
- [ ] `GET /api/operations/circuit-breakers/calibration_solve` - Returns
      calibration_solve breaker
- [ ] `GET /api/operations/circuit-breakers/photometry` - Returns photometry
      breaker
- [ ] `GET /api/operations/circuit-breakers/invalid_name` - Returns 404

#### Reset Circuit Breaker

- [ ] `POST /api/operations/circuit-breakers/ese_detection/reset` - Resets
      circuit breaker
  - [ ] Returns success response
  - [ ] Circuit breaker state changes to "closed"
  - [ ] Failure count resets to 0
  - [ ] Last failure time is cleared

### 1.4 Error Handling

- [ ] Invalid endpoint returns 404
- [ ] Invalid DLQ item ID returns 404
- [ ] Invalid circuit breaker name returns 404
- [ ] Invalid query parameters (negative limit) returns 422 or 400
- [ ] Missing required fields in POST requests returns 422
- [ ] Invalid JSON in request body returns 422

## 2. Test Data Creation

### 2.1 Python Script Execution

- [ ] `scripts/test_dlq_endpoints.py` runs successfully
- [ ] Creates test DLQ items for:
  - [ ] `ese_detection.detect_candidates`
  - [ ] `calibration_solve.solve_gain`
  - [ ] `photometry.measure_flux`
- [ ] Script displays initial and final stats
- [ ] Created items have correct structure

### 2.2 Verify Test Data

- [ ] Test items appear in `GET /api/operations/dlq/items`
- [ ] Stats reflect new items (`total` increases)
- [ ] Items have correct `component` and `operation` fields
- [ ] Items have `error_message` and `error_type` fields
- [ ] Items have `context` dictionary with test data

## 3. Frontend Testing

### 3.1 Operations Page

- [ ] Page loads at `/operations`
- [ ] DLQ Table component displays
- [ ] Circuit Breaker Status component displays
- [ ] Tabs switch correctly
- [ ] No console errors

### 3.2 Dead Letter Queue Table

- [ ] Table displays DLQ items (if any exist)
- [ ] Filter dropdowns work (component, status)
- [ ] Pagination works (if > 10 items)
- [ ] Retry button works (if items exist)
- [ ] Resolve button works (if items exist)
- [ ] Table updates after actions

### 3.3 Dead Letter Queue Stats

- [ ] Stats card displays
- [ ] Shows: total, pending, retrying, resolved, failed
- [ ] Numbers match API response
- [ ] Updates automatically (every 10 seconds)

### 3.4 Circuit Breaker Status

- [ ] Displays all 3 circuit breakers
- [ ] Shows state (closed/open/half-open) with color coding
- [ ] Shows failure count
- [ ] Reset button works
- [ ] Updates automatically (every 5 seconds)

### 3.5 Health Page - Operations Health Tab

- [ ] Tab exists and is accessible
- [ ] Overall status displays correctly
- [ ] Health checks list displays
- [ ] DLQ stats card displays
- [ ] Circuit breaker status displays
- [ ] All components update automatically

## 4. Integration Testing

### 4.1 End-to-End Workflow

- [ ] Create DLQ item via Python script
- [ ] Item appears in frontend table
- [ ] Stats update in frontend
- [ ] Retry action works from frontend
- [ ] Status updates in table
- [ ] Resolve action works from frontend
- [ ] Item disappears from pending list

### 4.2 Circuit Breaker Workflow

- [ ] View circuit breaker state in frontend
- [ ] Reset circuit breaker via API
- [ ] State updates in frontend
- [ ] Reset circuit breaker via frontend button
- [ ] State updates correctly

## 5. Performance Testing

- [ ] API endpoints respond in < 500ms
- [ ] Frontend page loads in < 2 seconds
- [ ] Auto-refresh doesn't cause performance issues
- [ ] Large DLQ tables (100+ items) render efficiently
- [ ] No memory leaks from auto-refresh intervals

## 6. Error Scenarios

### 6.1 Backend Down

- [ ] Frontend handles backend unavailability gracefully
- [ ] Error messages display appropriately
- [ ] Auto-refresh resumes when backend comes back

### 6.2 Network Errors

- [ ] Failed API calls show error messages
- [ ] Retry mechanisms work
- [ ] No infinite retry loops

### 6.3 Invalid Data

- [ ] Frontend handles malformed API responses
- [ ] Missing fields don't crash components
- [ ] Type mismatches are handled gracefully

## 7. Browser Compatibility

- [ ] Works in Chrome
- [ ] Works in Firefox
- [ ] Works in Safari (if applicable)
- [ ] Mobile responsive (if applicable)

## 8. Accessibility

- [ ] Keyboard navigation works
- [ ] Screen reader compatible (if applicable)
- [ ] Color contrast meets standards
- [ ] Focus indicators visible

## Test Execution Log

### Date: \***\*\_\_\_\*\***

### Tester: \***\*\_\_\_\*\***

**Backend API Tests:**

- Passed: **_ / _**
- Failed: **_ / _**

**Frontend Tests:**

- Passed: **_ / _**
- Failed: **_ / _**

**Integration Tests:**

- Passed: **_ / _**
- Failed: **_ / _**

**Issues Found:**

1.
2.
3.

**Notes:**

-
