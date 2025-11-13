# Web Interface Analysis: Observability Modules

## Modules That Would Benefit from Web Interfaces

### 🔴 High Priority (Essential for Operations)

#### 1. **Dead Letter Queue** ⭐⭐⭐⭐⭐
**Priority: CRITICAL**

**Why:** Operators need to:
- View failed operations
- Retry failed items
- Mark items as resolved
- Investigate error context
- Monitor failure trends

**Web Interface Features:**
- Table view of pending/retrying/failed items
- Filter by component, operation, error type
- View full error context and stack traces
- One-click retry functionality
- Bulk operations (retry all, mark resolved)
- Statistics dashboard (failure rates by component)
- Search and pagination

**Current State:** Only SQLite database, no UI

**Integration:** Add to existing dashboard under `/health` or new `/operations` section

---

#### 2. **Health Checks Dashboard** ⭐⭐⭐⭐⭐
**Priority: HIGH**

**Why:** Real-time visibility into system health

**Web Interface Features:**
- Visual status indicators (green/yellow/red)
- Component health matrix
- Historical health trends
- Detailed check results
- Alert status

**Current State:** Endpoints exist (`/health/*`), but no visual dashboard

**Integration:** Add to existing dashboard, likely `/health` page

---

#### 3. **Metrics Dashboard** ⭐⭐⭐⭐⭐
**Priority: HIGH**

**Why:** Prometheus metrics need visualization

**Web Interface Features:**
- Grafana dashboards (standard Prometheus UI)
- Custom dashboards for:
  - ESE detection metrics
  - Calibration metrics
  - Photometry metrics
  - Pipeline stage metrics
  - System metrics
- Real-time graphs
- Alert visualization

**Current State:** Metrics endpoint exists (`/metrics`), but needs Grafana setup

**Integration:** External Grafana instance, or embed Grafana panels in dashboard

---

### 🟡 Medium Priority (Useful for Monitoring)

#### 4. **Circuit Breaker Status** ⭐⭐⭐⭐
**Priority: MEDIUM**

**Why:** Monitor circuit breaker states to identify failing services

**Web Interface Features:**
- Visual circuit state (CLOSED/OPEN/HALF_OPEN)
- Failure counts and thresholds
- Time until recovery
- Historical state changes
- Per-component circuit status

**Integration:** Add to health dashboard or new `/resilience` page

---

#### 5. **Event Bus Monitor** ⭐⭐⭐⭐
**Priority: MEDIUM**

**Why:** Monitor event stream and event history

**Web Interface Features:**
- Real-time event stream (WebSocket)
- Event history viewer
- Filter by event type
- Event statistics
- Event replay

**Integration:** New `/events` page or add to existing monitoring page

---

#### 6. **Cache Statistics** ⭐⭐⭐
**Priority: MEDIUM**

**Why:** Monitor cache performance and hit rates

**Web Interface Features:**
- Cache hit/miss rates
- Cache size and memory usage
- TTL statistics
- Cache key search
- Cache invalidation controls

**Integration:** Add to metrics dashboard or `/performance` page

---

### 🟢 Low Priority (Nice to Have)

#### 7. **Structured Logging Viewer** ⭐⭐⭐
**Priority: LOW**

**Why:** View and search structured logs

**Web Interface Features:**
- Log viewer with filtering
- Search by correlation ID
- Log level filtering
- Time range selection
- Export logs

**Note:** Better handled by dedicated log aggregation tools (Grafana Loki, ELK)

**Integration:** External tool or embed log viewer component

---

#### 8. **Retry Statistics** ⭐⭐
**Priority: LOW**

**Why:** Monitor retry patterns and success rates

**Web Interface Features:**
- Retry success/failure rates
- Retry attempt distributions
- Component-specific retry stats

**Integration:** Part of metrics dashboard

---

## Recommended Implementation Order

### Phase 1: Critical Operations (Week 1)
1. **Dead Letter Queue UI** - Essential for operations
2. **Health Checks Dashboard** - Real-time visibility

### Phase 2: Monitoring (Week 2)
3. **Metrics Dashboard** - Set up Grafana
4. **Circuit Breaker Status** - Resilience monitoring

### Phase 3: Advanced Monitoring (Week 3+)
5. **Event Bus Monitor** - Event stream visualization
6. **Cache Statistics** - Performance monitoring

---

## Integration with Existing Dashboard

Based on the existing React dashboard structure, these modules would fit into:

### Existing Pages to Enhance:
- **`/health`** - Add health checks dashboard, circuit breaker status
- **`/dashboard`** - Add metrics widgets, cache statistics
- **`/control`** - Add dead letter queue management

### New Pages to Create:
- **`/operations`** - Dead letter queue, retry management
- **`/events`** - Event bus monitor
- **`/metrics`** - Detailed metrics dashboard (or embed Grafana)

---

## API Endpoints Needed

### Dead Letter Queue
```
GET  /api/dlq/items              # List DLQ items
GET  /api/dlq/items/{id}         # Get DLQ item details
POST /api/dlq/items/{id}/retry   # Retry failed item
POST /api/dlq/items/{id}/resolve # Mark as resolved
GET  /api/dlq/stats              # DLQ statistics
```

### Circuit Breakers
```
GET  /api/circuit-breakers       # Get all circuit breaker states
GET  /api/circuit-breakers/{name} # Get specific circuit breaker state
POST /api/circuit-breakers/{name}/reset # Reset circuit breaker
```

### Event Bus
```
GET  /api/events                 # Get event history
GET  /api/events/stream          # WebSocket event stream
GET  /api/events/stats          # Event statistics
```

### Cache
```
GET  /api/cache/stats           # Cache statistics
GET  /api/cache/keys            # List cache keys (with pagination)
DELETE /api/cache/keys/{key}    # Invalidate cache key
POST /api/cache/clear           # Clear all cache
```

---

## Technology Stack

### Frontend (Existing)
- React 18 + TypeScript
- Material-UI v6
- React Query for API calls
- WebSocket client for real-time updates

### New Components Needed
- Data tables (for DLQ, events)
- Real-time charts (for metrics)
- Status indicators (for health, circuit breakers)
- WebSocket hooks (for event stream)

### Backend (New Endpoints)
- FastAPI endpoints for DLQ, circuit breakers, events, cache
- WebSocket support for event stream
- Pagination and filtering support

---

## Cost Analysis

**All web interfaces: $0**

- Use existing React dashboard infrastructure
- No new dependencies required
- Material-UI components already available
- WebSocket support already in place

---

## Summary

**Must Have:**
1. Dead Letter Queue UI (critical for operations)
2. Health Checks Dashboard (real-time visibility)
3. Metrics Dashboard (Grafana integration)

**Should Have:**
4. Circuit Breaker Status (resilience monitoring)
5. Event Bus Monitor (event stream visualization)

**Nice to Have:**
6. Cache Statistics (performance monitoring)
7. Log Viewer (better handled by external tools)

**Total Estimated Effort:**
- Phase 1: 1-2 weeks
- Phase 2: 1 week
- Phase 3: 1 week

**Total Cost: $0** (uses existing infrastructure)

