# Browser Testing Guide for Phase 1

## Prerequisites

1. **Backend Server Running:**
   ```bash
   # Check if running
   curl http://localhost:8000/health/liveness
   
   # If not running, start it (adjust command based on your setup)
   ```

2. **Frontend Dev Server Running:**
   ```bash
   cd frontend
   npm run dev
   # Should be available at http://localhost:5173
   ```

3. **Browser Extension Connected:**
   - Click the Browser MCP extension icon in Chrome toolbar
   - Click "Connect" button
   - Extension should show "Connected" status

## Testing Steps

### 1. Navigate to Operations Page

**URL:** `http://localhost:5173/operations`

**Expected:**
- Page loads without errors
- Navigation bar shows "Operations" link (with Build icon)
- Operations page displays with tabs:
  - Dead Letter Queue tab
  - Circuit Breakers tab

### 2. Test Dead Letter Queue Tab

**What to Check:**
- DLQ Stats card displays at top
  - Shows: Total, Pending, Retrying, Resolved, Failed
  - Numbers match backend API (`/api/operations/dlq/stats`)
- DLQ Table displays items (if any exist)
  - Columns: ID, Component, Operation, Error Message, Status, Actions
  - Filter dropdowns work (Component, Status)
  - Retry button works (if items exist)
  - Resolve button works (if items exist)

**Test Actions:**
1. Create a test DLQ item:
   ```bash
   /opt/miniforge/envs/casa6/bin/python scripts/test_dlq_endpoints.py
   ```
2. Wait 10-30 seconds
3. Verify item appears in table automatically
4. Click "Retry" button
5. Verify status changes to "retrying"
6. Click "Resolve" button
7. Verify item moves to resolved state

### 3. Test Circuit Breakers Tab

**What to Check:**
- Circuit Breaker Status component displays
- Shows all 3 circuit breakers:
  - ese_detection
  - calibration_solve
  - photometry
- Each breaker shows:
  - Name
  - State (closed/open/half-open) with color coding
  - Failure count
  - Reset button

**Test Actions:**
1. Click "Reset" button on a circuit breaker
2. Verify state updates (should remain "closed" if already closed)
3. Verify failure count resets to 0

### 4. Test Real-Time Updates

**What to Check:**
- Open browser DevTools → Network tab
- Observe automatic API calls:
  - `/api/operations/dlq/stats` - Every 10 seconds
  - `/api/operations/circuit-breakers` - Every 5 seconds
  - `/api/operations/dlq/items` - Every 30 seconds

**Test Actions:**
1. Note current DLQ stats
2. Create new DLQ item via Python script
3. Wait 10-15 seconds
4. Verify stats update automatically (without page refresh)
5. Verify new item appears in table automatically

### 5. Test Navigation

**What to Check:**
- Navigation bar shows "Operations" link
- Link is clickable
- Active route is highlighted
- Mobile drawer menu includes Operations link

**Test Actions:**
1. Click "Operations" in navigation
2. Verify page navigates to `/operations`
3. Click other navigation links
4. Verify Operations link remains accessible

### 6. Test Health Page - Operations Health Tab

**URL:** `http://localhost:5173/health`

**What to Check:**
- Health page loads
- "Operations Health" tab exists
- Tab displays:
  - Overall status (healthy/degraded/unhealthy)
  - Health checks list
  - DLQ stats card
  - Circuit breaker status

**Test Actions:**
1. Navigate to `/health`
2. Click "Operations Health" tab
3. Verify all components display
4. Verify data matches `/api/health/summary` endpoint

## Expected Behaviors

### Auto-Refresh Intervals

| Component | Interval | Endpoint |
|-----------|----------|----------|
| DLQ Stats | 10 seconds | `/api/operations/dlq/stats` |
| Circuit Breakers | 5 seconds | `/api/operations/circuit-breakers` |
| Health Summary | 10 seconds | `/api/health/summary` |
| DLQ Items Table | 30 seconds | `/api/operations/dlq/items` |

### Color Coding

**Circuit Breaker States:**
- Closed (healthy): Green
- Open (unhealthy): Red
- Half-open (recovering): Yellow

**DLQ Item Status:**
- Pending: Default
- Retrying: Warning (yellow/orange)
- Resolved: Success (green)
- Failed: Error (red)

**Health Status:**
- Healthy: Green
- Degraded: Yellow/Warning
- Unhealthy: Red/Error

## Troubleshooting

### Page Not Loading
- Check if frontend dev server is running: `curl http://localhost:5173`
- Check browser console for errors
- Verify backend is running: `curl http://localhost:8000/health/liveness`

### Data Not Appearing
- Check browser console for API errors
- Verify backend API is responding: `curl http://localhost:8000/api/operations/dlq/stats`
- Check Network tab in DevTools for failed requests

### Auto-Refresh Not Working
- Check browser console for React Query errors
- Verify `refetchInterval` is configured in `queries.ts`
- Check Network tab to see if requests are being made
- Verify React Query is properly initialized

### Navigation Link Not Working
- Verify route is configured in `App.tsx`
- Check if link is in `Navigation.tsx` navItems array
- Verify React Router is working (check other routes)

## Test Checklist

- [ ] Operations page loads
- [ ] Navigation link appears
- [ ] DLQ Stats card displays
- [ ] DLQ Table displays (if items exist)
- [ ] Circuit Breaker status displays
- [ ] Retry action works
- [ ] Resolve action works
- [ ] Circuit breaker reset works
- [ ] Auto-refresh works (DLQ stats)
- [ ] Auto-refresh works (Circuit breakers)
- [ ] Auto-refresh works (DLQ items)
- [ ] Health page Operations Health tab works
- [ ] Mobile navigation includes Operations link
- [ ] No console errors
- [ ] No network errors

## Screenshots to Capture

1. Operations page - DLQ Tab
2. Operations page - Circuit Breakers Tab
3. Health page - Operations Health Tab
4. Browser DevTools - Network tab showing auto-refresh
5. Mobile navigation drawer with Operations link

## Notes

- All auto-refresh intervals are configured in `frontend/src/api/queries.ts`
- Backend endpoints are tested and working (see `docs/dev/phase1_backend_testing_complete.md`)
- Test data can be created using `scripts/test_dlq_endpoints.py`

