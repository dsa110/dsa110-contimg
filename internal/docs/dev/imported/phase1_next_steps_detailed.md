# Phase 1 Next Steps - Detailed Guide

## 1. Test the Endpoints with Real Data

### Backend API Testing

#### Step 1.1: Start the Backend Server

```bash
# Activate casa6 environment
source /opt/miniforge/bin/activate casa6

# Navigate to project directory
cd /data/dsa110-contimg

# Start the FastAPI server (if not already running)
# Check if server is running on port 8000
curl http://localhost:8000/health/liveness

# If not running, start it (adjust command based on your setup)
# Example: uvicorn src.dsa110_contimg.api.routes:app --host 0.0.0.0 --port 8000
```

#### Step 1.2: Test Health Summary Endpoint

```bash
# Test the comprehensive health summary
curl http://localhost:8000/api/health/summary | jq

# Expected response structure:
# {
#   "status": "healthy" | "degraded" | "unhealthy",
#   "timestamp": 1234567890.123,
#   "checks": { ... },
#   "circuit_breakers": [ ... ],
#   "dlq_stats": { ... }
# }
```

#### Step 1.3: Test Dead Letter Queue Endpoints

**Get DLQ Statistics:**

```bash
curl http://localhost:8000/api/operations/dlq/stats | jq

# Expected:
# {
#   "total": 0,
#   "pending": 0,
#   "retrying": 0,
#   "resolved": 0,
#   "failed": 0
# }
```

**Get DLQ Items:**

```bash
# Get all pending items
curl "http://localhost:8000/api/operations/dlq/items?status=pending&limit=10" | jq

# Filter by component
curl "http://localhost:8000/api/operations/dlq/items?component=ese_detection&status=pending" | jq
```

**Create Test DLQ Item (if needed):**

```python
# Create a test script: test_dlq.py
from pathlib import Path
from dsa110_contimg.pipeline.dead_letter_queue import get_dlq

dlq = get_dlq()
item_id = dlq.add(
    component="ese_detection",
    operation="detect_candidates",
    error=RuntimeError("Test error for DLQ"),
    context={"min_sigma": 5.0, "source_id": "test_source"}
)
print(f"Created DLQ item: {item_id}")
```

Run it:

```bash
/opt/miniforge/envs/casa6/bin/python test_dlq.py
```

**Test Retry Action:**

```bash
# Replace {item_id} with actual ID from previous step
curl -X POST "http://localhost:8000/api/operations/dlq/items/1/retry" \
  -H "Content-Type: application/json" \
  -d '{"note": "Manual retry test"}' | jq
```

**Test Resolve Action:**

```bash
curl -X POST "http://localhost:8000/api/operations/dlq/items/1/resolve" \
  -H "Content-Type: application/json" \
  -d '{"note": "Manually resolved"}' | jq
```

#### Step 1.4: Test Circuit Breaker Endpoints

**Get All Circuit Breakers:**

```bash
curl http://localhost:8000/api/operations/circuit-breakers | jq

# Expected:
# {
#   "circuit_breakers": [
#     {
#       "name": "ese_detection",
#       "state": "closed",
#       "failure_count": 0,
#       "recovery_timeout": 60.0
#     },
#     ...
#   ]
# }
```

**Get Specific Circuit Breaker:**

```bash
curl http://localhost:8000/api/operations/circuit-breakers/ese_detection | jq
```

**Test Reset (if circuit is open):**

```bash
curl -X POST "http://localhost:8000/api/operations/circuit-breakers/ese_detection/reset" | jq
```

#### Step 1.5: Test Error Handling

**Test Invalid Endpoints:**

```bash
# Should return 404
curl http://localhost:8000/api/operations/dlq/items/99999 | jq

# Should return 404
curl http://localhost:8000/api/operations/circuit-breakers/invalid_name | jq
```

### Frontend Testing

#### Step 1.6: Start Frontend Development Server

```bash
cd /data/dsa110-contimg/frontend

# Install dependencies if needed
npm install

# Start dev server
npm run dev

# Frontend should be available at http://localhost:5173 (or configured port)
```

#### Step 1.7: Test Operations Page

1. Navigate to `http://localhost:5173/operations`
2. Verify DLQ table loads (may be empty initially)
3. Verify Circuit Breaker status displays
4. Test filtering dropdowns
5. Test tab switching

#### Step 1.8: Test Health Page Enhancement

1. Navigate to `http://localhost:5173/health`
2. Click on "Operations Health" tab
3. Verify:
   - Overall status displays
   - Health checks list shows
   - DLQ stats card displays
   - Circuit breaker status displays

### Test Checklist

- [ ] Health summary endpoint returns valid JSON
- [ ] DLQ stats endpoint returns correct structure
- [ ] DLQ items endpoint returns list (empty or with items)
- [ ] DLQ retry action works
- [ ] DLQ resolve action works
- [ ] Circuit breaker list endpoint works
- [ ] Circuit breaker reset works (if applicable)
- [ ] Frontend Operations page loads
- [ ] Frontend Health page Operations tab loads
- [ ] Error handling works (404s, invalid data)

---

## 2. Fix Any TypeScript/Linting Errors

### Step 2.1: Check TypeScript Errors

**Run TypeScript Compiler:**

```bash
cd /data/dsa110-contimg/frontend

# Check for TypeScript errors
npm run type-check
# OR
npx tsc --noEmit
```

**Common Issues to Look For:**

- Missing type imports
- Type mismatches
- Undefined properties
- Missing optional chaining

### Step 2.2: Check Linting Errors

**Run ESLint:**

```bash
cd /data/dsa110-contimg/frontend

# Run linter
npm run lint
# OR
npx eslint src --ext .ts,.tsx
```

**Common Issues:**

- Unused imports
- Missing dependencies in useEffect
- Console.log statements (if linting rules disallow)
- Missing prop types

### Step 2.3: Fix Common TypeScript Issues

**Issue: Missing Import**

```typescript
// Error: Cannot find name 'DLQItem'
// Fix: Add import
import type { DLQItem } from "../api/types";
```

**Issue: Type Mismatch**

```typescript
// Error: Type 'string' is not assignable to type 'DLQItem'
// Fix: Ensure correct type casting
const item: DLQItem = response.data;
```

**Issue: Optional Property Access**

```typescript
// Error: Object is possibly 'undefined'
// Fix: Add optional chaining
const status = healthSummary?.status ?? "unknown";
```

### Step 2.4: Fix Common Linting Issues

**Issue: Unused Variable**

```typescript
// Error: 'variable' is assigned a value but never used
// Fix: Remove or prefix with underscore
const _unusedVariable = value;
```

**Issue: Missing Dependency**

```typescript
// Error: React Hook useEffect has missing dependency
// Fix: Add to dependency array or use useCallback
useEffect(() => {
  refetch();
}, [refetch]); // Add missing dependency
```

### Step 2.5: Verify Fixes

**Run All Checks:**

```bash
cd /data/dsa110-contimg/frontend

# Type check
npm run type-check

# Lint check
npm run lint

# Build check (if applicable)
npm run build
```

### Fix Checklist

- [ ] No TypeScript errors
- [ ] No ESLint errors
- [ ] No ESLint warnings (or acceptable warnings)
- [ ] Build succeeds (if applicable)
- [ ] All imports are correct
- [ ] All types are properly defined

---

## 3. Add Navigation Links to the Operations Page

### Step 3.1: Find Navigation Component

**Locate Navigation/Sidebar:**

```bash
# Search for navigation components
cd /data/dsa110-contimg/frontend
find src -name "*nav*" -o -name "*menu*" -o -name "*sidebar*" | head -10

# Check App.tsx for navigation structure
grep -n "nav\|menu\|sidebar" src/App.tsx
```

### Step 3.2: Identify Navigation Pattern

**Common Patterns:**

1. **Sidebar Navigation** - Usually in a separate component
2. **Top Navigation Bar** - Header component
3. **Drawer Menu** - Material-UI Drawer component
4. **Breadcrumbs** - For hierarchical navigation

**Check Existing Routes:**

```typescript
// Look for existing navigation items in App.tsx or navigation component
// Example patterns:
- Dashboard
- Control
- Health
- QA
- Data Browser
```

### Step 3.3: Add Operations Link

**Exact Code for Navigation.tsx:**

1. **Add Icon Import** (if not already imported):

```typescript
// In frontend/src/components/Navigation.tsx
import {
  Dashboard,
  Image,
  TableChart,
  Public,
  ShowChart,
  Settings,
  PlayArrow,
  Storage,
  Assessment,
  Build, // ADD THIS - or use Settings if already imported
} from "@mui/icons-material";
```

2. **Add to navItems Array:**

```typescript
// Find the navItems array (around line 20-30)
const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: Dashboard },
  { path: "/control", label: "Control", icon: Settings },
  { path: "/streaming", label: "Streaming", icon: PlayArrow },
  { path: "/data", label: "Data", icon: Storage },
  { path: "/qa", label: "QA Visualization", icon: Assessment },
  { path: "/mosaics", label: "Mosaics", icon: Image },
  { path: "/sources", label: "Sources", icon: TableChart },
  { path: "/sky", label: "Sky View", icon: Public },
  { path: "/observing", label: "Observing", icon: Public },
  { path: "/health", label: "Health", icon: Assessment },
  // ADD THIS LINE:
  { path: "/operations", label: "Operations", icon: Build },
];
```

**File Location:** `frontend/src/components/Navigation.tsx`

**If Using Top Navigation:**

```typescript
// Find the navigation menu items
<MenuItem component={Link} to="/dashboard">Dashboard</MenuItem>
<MenuItem component={Link} to="/control">Control</MenuItem>
<MenuItem component={Link} to="/health">Health</MenuItem>
{/* ADD THIS: */}
<MenuItem component={Link} to="/operations">Operations</MenuItem>
```

**If Using Material-UI List:**

```typescript
<ListItem button component={Link} to="/dashboard">
  <ListItemIcon><DashboardIcon /></ListItemIcon>
  <ListItemText primary="Dashboard" />
</ListItemItem>
{/* ADD THIS: */}
<ListItem button component={Link} to="/operations">
  <ListItemIcon><SettingsIcon /></ListItemIcon>
  <ListItemText primary="Operations" />
</ListItemItem>
```

### Step 3.4: Add Icon (if needed)

**Import Material-UI Icon:**

```typescript
import {
  Settings as SettingsIcon,
  // OR
  Build as BuildIcon,
  // OR
  Engineering as EngineeringIcon,
} from "@mui/icons-material";
```

### Step 3.5: Verify Navigation

**Test Steps:**

1. Start frontend dev server
2. Check navigation menu/sidebar
3. Click "Operations" link
4. Verify it navigates to `/operations`
5. Verify Operations page loads correctly
6. Check that active route is highlighted (if applicable)

### Step 3.6: Add to Health Page (Optional)

**Add Quick Link in Health Page:**

```typescript
// In HealthPage.tsx, add a link to Operations page
import { Link } from 'react-router-dom';

// In OperationsHealthTab component:
<Alert severity="info">
  For detailed operations management, visit the{' '}
  <Link to="/operations">Operations Page</Link>
</Alert>
```

### Navigation Checklist

- [ ] Found navigation component/structure
- [ ] Added Operations link to navigation
- [ ] Added appropriate icon
- [ ] Verified link works
- [ ] Verified active state (if applicable)
- [ ] Tested navigation from different pages
- [ ] Added to breadcrumbs (if applicable)

---

## 4. Test Real-Time Updates

### Step 4.1: Verify Auto-Refresh Configuration

**Check Query Refresh Intervals:**

```typescript
// In frontend/src/api/queries.ts, verify:
useDLQStats() {
  refetchInterval: 10000, // 10 seconds
}

useCircuitBreakers() {
  refetchInterval: 5000, // 5 seconds
}

useHealthSummary() {
  refetchInterval: 10000, // 10 seconds
}
```

### Step 4.2: Test DLQ Stats Auto-Refresh

**Test Steps:**

1. Open Operations page (`/operations`)
2. Note current DLQ stats values
3. Create a new DLQ item (using test script from Step 1.3)
4. Wait 10-15 seconds
5. Verify stats update automatically without page refresh

**Expected Behavior:**

- Stats card updates automatically
- No page reload required
- Smooth transition (no flicker)

### Step 4.3: Test Circuit Breaker Auto-Refresh

**Test Steps:**

1. Open Operations page, Circuit Breakers tab
2. Note current circuit breaker states
3. Manually trigger a circuit breaker failure (if possible) OR
4. Wait and observe refresh (should refresh every 5 seconds)
5. Verify states update automatically

**Expected Behavior:**

- Circuit breaker cards update every 5 seconds
- State changes are reflected immediately
- Failure counts update correctly

### Step 4.4: Test DLQ Table Auto-Refresh

**Test Steps:**

1. Open Operations page, Dead Letter Queue tab
2. Note current items in table
3. Create a new DLQ item
4. Wait 30 seconds (refresh interval)
5. Verify new item appears in table automatically

**Expected Behavior:**

- Table updates every 30 seconds
- New items appear automatically
- Status changes are reflected

### Step 4.5: Test Health Summary Auto-Refresh

**Test Steps:**

1. Open Health page, Operations Health tab
2. Note current health status
3. Create a DLQ item or open a circuit breaker
4. Wait 10-15 seconds
5. Verify health summary updates automatically

**Expected Behavior:**

- Overall status updates
- DLQ stats update
- Circuit breaker status updates
- Health checks remain current

### Step 4.6: Test WebSocket Integration (if applicable)

**Check WebSocket Usage:**

```typescript
// Some queries may use WebSocket for real-time updates
// Check if useRealtimeQuery is used for operations endpoints
```

**If WebSocket is Used:**

1. Open browser DevTools → Network → WS tab
2. Verify WebSocket connection is established
3. Trigger an event (create DLQ item, open circuit breaker)
4. Verify WebSocket message is received
5. Verify UI updates immediately

### Step 4.7: Test Manual Refresh

**Test Refresh Buttons:**

1. Click refresh icon on Circuit Breaker Status component
2. Verify data refreshes immediately
3. Click refresh on DLQ Stats (if available)
4. Verify manual refresh works

### Step 4.8: Test Multiple Tabs

**Test Concurrent Updates:**

1. Open Operations page in Tab 1
2. Open Health page Operations Health tab in Tab 2
3. Create a DLQ item
4. Verify both tabs update independently
5. Verify no conflicts or race conditions

### Step 4.9: Test Error Handling During Refresh

**Test Network Errors:**

1. Stop backend server
2. Wait for refresh interval
3. Verify error handling (should show error state, not crash)
4. Restart backend server
5. Verify recovery (should resume updates)

### Real-Time Updates Checklist

- [ ] DLQ stats auto-refresh works (10s interval)
- [ ] Circuit breaker status auto-refresh works (5s interval)
- [ ] DLQ table auto-refresh works (30s interval)
- [ ] Health summary auto-refresh works (10s interval)
- [ ] Manual refresh buttons work
- [ ] Multiple tabs update independently
- [ ] Network errors handled gracefully
- [ ] No memory leaks from intervals
- [ ] Updates are smooth (no flicker)
- [ ] WebSocket integration works (if applicable)

---

## Additional Testing Considerations

### Performance Testing

- [ ] Page load time is acceptable (< 2 seconds)
- [ ] Auto-refresh doesn't cause performance issues
- [ ] Large DLQ tables render efficiently
- [ ] No unnecessary re-renders

### Browser Compatibility

- [ ] Works in Chrome
- [ ] Works in Firefox
- [ ] Works in Safari (if applicable)
- [ ] Mobile responsive (if applicable)

### Accessibility

- [ ] Keyboard navigation works
- [ ] Screen reader compatible (if applicable)
- [ ] Color contrast meets standards
- [ ] Focus indicators visible

---

## Troubleshooting Guide

### Issue: Endpoints Return 404

**Solution:** Verify router is included in `routes.py`:

```python
app.include_router(operations_router, prefix="/api")
```

### Issue: TypeScript Errors

**Solution:** Check imports and type definitions match backend response
structure

### Issue: Auto-Refresh Not Working

**Solution:**

1. Check `refetchInterval` values
2. Verify React Query is configured correctly
3. Check browser console for errors
4. Verify backend is responding

### Issue: Navigation Link Not Working

**Solution:**

1. Verify route is defined in `App.tsx`
2. Check Link component import
3. Verify path matches route definition

---

**Status**: Ready for Testing **Estimated Time**: 2-4 hours for complete testing
