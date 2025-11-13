# Phase 3: Advanced Monitoring Implementation Plan

## Goal
Implement web-based interfaces for Event Bus Monitor and Cache Statistics to provide real-time visibility into system events and caching performance.

## Modules to Implement

### 1. Event Bus Monitor

**Backend API Endpoints (`src/dsa110_contimg/api/routers/events.py`)**:
- `GET /api/events/stream`: Get recent events (with filtering by event type, component, time range)
- `GET /api/events/stats`: Get event statistics (counts by type, rate over time)
- `GET /api/events/types`: Get list of available event types
- `POST /api/events/subscribe`: WebSocket endpoint for real-time event streaming (optional, future enhancement)

**Frontend Components (`frontend/src/components/Events/`)**:
- `EventStream.tsx`: Real-time event stream viewer with filtering
- `EventStats.tsx`: Event statistics dashboard
- `EventFilter.tsx`: Filtering controls (event type, time range, component)

**Frontend Page (`frontend/src/pages/EventsPage.tsx`)**:
- Main page integrating EventStream and EventStats components
- Real-time updates via polling (or WebSocket if implemented)

### 2. Cache Statistics Monitor

**Backend API Endpoints (`src/dsa110_contimg/api/routers/cache.py`)**:
- `GET /api/cache/stats`: Get cache statistics (hit rate, miss rate, size, TTL info)
- `GET /api/cache/keys`: List cache keys (with filtering, pagination)
- `GET /api/cache/keys/{key}`: Get details for a specific cache key
- `DELETE /api/cache/keys/{key}`: Delete a specific cache key
- `DELETE /api/cache/clear`: Clear all cache
- `GET /api/cache/performance`: Get cache performance metrics (hit/miss rates over time)

**Frontend Components (`frontend/src/components/Cache/`)**:
- `CacheStats.tsx`: Display cache statistics (hit rate, size, etc.)
- `CacheKeys.tsx`: Table of cache keys with search/filter
- `CachePerformance.tsx`: Performance charts (hit rate over time)

**Frontend Page (`frontend/src/pages/CachePage.tsx`)**:
- Main page integrating CacheStats, CacheKeys, and CachePerformance components

## Data Sources

### Event Bus
- `src/dsa110_contimg/pipeline/event_bus.py`: `EventBus` class with event history
- Need to add event history storage to EventBus for monitoring

### Cache
- `src/dsa110_contimg/pipeline/caching.py`: `CacheBackend` interface with `InMemoryCache` and `RedisCache` implementations
- Need to add statistics tracking to cache backends

## Implementation Details

### Backend Enhancements

1. **Event Bus History Storage**:
   - Add in-memory event history buffer (last N events)
   - Add event statistics tracking (counts by type, timestamps)
   - Consider SQLite storage for persistent event history (optional)

2. **Cache Statistics Tracking**:
   - Add hit/miss counters to cache backends
   - Track cache size and key counts
   - Track TTL information
   - Add performance metrics (hit rate over time)

### Frontend
- Use Material-UI for consistent styling
- Use React Query for data fetching and caching
- Implement auto-refresh for real-time updates
- Use charts library (e.g., recharts) for performance visualization

## Estimated Time
- Backend: 2-3 days
- Frontend: 2-3 days

**Total: 1 week**

## Success Criteria
- Users can view real-time event stream
- Event filtering and statistics are functional
- Cache statistics are displayed accurately
- Cache keys can be viewed and managed
- Performance metrics are visualized
- Real-time updates are functional

