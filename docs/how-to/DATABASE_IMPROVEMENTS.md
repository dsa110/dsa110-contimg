# Database Interaction Improvements

This document describes the improvements made to database interactions for
better reliability, performance, and monitoring.

## Overview

Three major improvements have been implemented:

1. **Retry Logic**: Automatic retry with exponential backoff for database
   locking errors
2. **Performance Monitoring**: Real-time tracking of database operation metrics
3. **Connection Pooling**: Reusable database connections to reduce overhead

## 1. Retry Logic

### Implementation

- **Location**: `src/dsa110_contimg/api/db_utils.py`
- **Function**: `retry_db_operation()`

### Features

- Automatically retries database operations on locking errors
- Exponential backoff (0.1s, 0.2s, 0.4s by default)
- Configurable retry attempts (default: 3)
- Only retries on locking errors, fails fast on other errors
- Integrated with performance monitoring

### Usage

```python
from dsa110_contimg.api.db_utils import retry_db_operation

def fetch_data():
    with db_operation(db_path, "fetch_data") as conn:
        return conn.execute("SELECT * FROM table").fetchall()

# Wrap with retry logic
result = retry_db_operation(fetch_data, operation_name="fetch_data")
```

### Applied To

- `fetch_queue_stats()` - Critical for dashboard status
- `fetch_recent_queue_groups()` - Used frequently by frontend

## 2. Performance Monitoring

### Implementation

- **Location**: `src/dsa110_contimg/api/db_utils.py`
- **Class**: `DatabasePerformanceMonitor`

### Metrics Tracked

- Total operations count
- Error count and error rate
- Operation duration (min, max, average)
- Percentiles (P50, P95, P99)
- Per-operation tracking

### API Endpoint

**GET** `/api/metrics/database`

Returns:

```json
{
  "total_operations": 1234,
  "error_count": 5,
  "error_rate": 0.004,
  "avg_duration": 0.012,
  "min_duration": 0.001,
  "max_duration": 0.234,
  "p50_duration": 0.008,
  "p95_duration": 0.045,
  "p99_duration": 0.123
}
```

### Usage

All database operations using `db_operation()` context manager are automatically
monitored.

## 3. Connection Pooling

### Implementation

- **Location**: `src/dsa110_contimg/api/db_utils.py`
- **Class**: `DatabaseConnectionPool`

### Features

- Maintains a pool of connections per database path
- Reuses connections to reduce overhead
- Maximum 5 connections per database (configurable)
- Automatic connection validation
- Thread-safe (uses locks for pool access)

### Benefits

- **Reduced Connection Overhead**: Reusing connections avoids the cost of
  creating new ones
- **Better Resource Management**: Limits concurrent connections
- **Automatic Cleanup**: Invalid connections are detected and replaced

### Usage

```python
from dsa110_contimg.api.db_utils import db_operation

# Automatically uses connection pool
with db_operation(db_path, "my_operation", use_pool=True) as conn:
    cursor = conn.execute("SELECT * FROM table")
    results = cursor.fetchall()
```

## Database Configuration

### WAL Mode

All database connections now use **WAL (Write-Ahead Logging) mode**:

- **Benefits**:
  - Multiple readers can access database simultaneously
  - Readers don't block writers
  - Writers don't block readers
  - Better performance under concurrent access

- **Status**: Enabled automatically for all connections

### Timeout Settings

- **Connection Timeout**: 30 seconds
- **Busy Timeout**: 30 seconds (30000ms)
- **Retry Delays**: 0.1s, 0.2s, 0.4s (exponential backoff)

## Testing

### Verify WAL Mode

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('/data/dsa110-contimg/state/products.sqlite3', timeout=30)
print('Journal mode:', conn.execute('PRAGMA journal_mode').fetchone()[0])
print('Busy timeout:', conn.execute('PRAGMA busy_timeout').fetchone()[0])
conn.close()
"
```

Expected output:

```
Journal mode: wal
Busy timeout: 30000
```

### Check Database Metrics

```bash
curl http://localhost:8000/api/metrics/database | python3 -m json.tool
```

### Test Retry Logic

Restart the pointing monitor service while the API is handling requests:

```bash
sudo systemctl restart contimg-pointing-monitor.service
```

The API should continue operating smoothly without disconnections.

## Performance Tuning

### Adjusting Connection Pool Size

Edit `src/dsa110_contimg/api/db_utils.py`:

```python
_connection_pool = DatabaseConnectionPool(max_connections=10, timeout=30.0)
```

### Adjusting Retry Parameters

When calling `retry_db_operation()`:

```python
retry_db_operation(
    func,
    max_retries=5,        # Increase retries
    initial_delay=0.2,    # Start with longer delay
    operation_name="my_op"
)
```

### Monitoring Performance

Check the `/api/metrics/database` endpoint regularly to:

- Identify slow operations (high P95/P99)
- Monitor error rates
- Track operation counts

If error rates are high or operations are slow, consider:

- Increasing connection pool size
- Adjusting timeout values
- Optimizing slow queries

## Files Modified

1. **`src/dsa110_contimg/api/db_utils.py`** (NEW)
   - Connection pooling implementation
   - Performance monitoring
   - Retry logic

2. **`src/dsa110_contimg/api/data_access.py`**
   - Updated `_connect()` to enable WAL mode
   - Added retry logic to critical functions
   - Integrated with connection pooling

3. **`src/dsa110_contimg/database/products.py`**
   - Updated `ensure_products_db()` to enable WAL mode

4. **`src/dsa110_contimg/api/routes.py`**
   - Added `/api/metrics/database` endpoint

## Benefits

1. **Reliability**: Automatic retry prevents transient failures
2. **Performance**: Connection pooling reduces overhead
3. **Observability**: Performance metrics enable proactive monitoring
4. **Concurrency**: WAL mode allows better concurrent access
5. **Resilience**: System continues operating during service restarts

## Future Enhancements

- [ ] Add connection pool metrics to monitoring endpoint
- [ ] Implement query result caching for frequently accessed data
- [ ] Add database query optimization recommendations
- [ ] Create alerts for high error rates or slow operations
- [ ] Add per-operation performance dashboards
