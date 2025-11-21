# Testing the Pointing History API Endpoint

This guide explains how to test the `/api/pointing_history` endpoint after
migrating the `pointing_history` table from `products.sqlite3` to
`ingest.sqlite3`.

## Quick Test (Manual)

### 1. Start the API Server

```bash
# From the project root
cd /data/dsa110-contimg
python -m dsa110_contimg.api.main
```

Or if running via systemd:

```bash
sudo systemctl status contimg-api.service
```

### 2. Test the Endpoint with curl

```bash
# Basic test - get pointing history for a time range
curl "http://localhost:8000/api/pointing_history?start_mjd=60300&end_mjd=60400" | jq

# Test with current time range (last 7 days)
python3 << 'EOF'
from astropy.time import Time
from datetime import datetime, timedelta

now = Time.now()
week_ago = Time(now.mjd - 7, format='mjd')

print(f"curl \"http://localhost:8000/api/pointing_history?start_mjd={week_ago.mjd:.2f}&end_mjd={now.mjd:.2f}\" | jq")
EOF
```

### 3. Expected Response Format

```json
{
  "items": [
    {
      "timestamp": 60300.123456,
      "ra_deg": 207.45,
      "dec_deg": 34.19
    },
    ...
  ]
}
```

### 4. Verify Data Sources

The endpoint queries three sources:

1. **`pointing_history` table** in `ingest.sqlite3` (monitoring data)
2. **`ms_index` table** in `products.sqlite3` (processed observations)
3. **Direct HDF5 file scan** from `/data/incoming/` (unprocessed files)

To verify each source:

```bash
# Check ingest database
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/data/dsa110-contimg/state/ingest.sqlite3')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM pointing_history")
print(f"Ingest DB records: {cursor.fetchone()[0]}")
conn.close()
EOF

# Check products database (ms_index)
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('/data/dsa110-contimg/state/products.sqlite3')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM ms_index WHERE ra_deg IS NOT NULL AND dec_deg IS NOT NULL")
print(f"Products DB MS records with pointing: {cursor.fetchone()[0]}")
conn.close()
EOF
```

## Automated Testing

### Unit Tests

Update the existing unit tests in `tests/unit/api/test_data_access.py`:

```python
def test_fetch_pointing_history_success(self, mock_ingest_db):
    """Test successful pointing history retrieval."""
    from astropy.time import Time

    now = datetime.now(tz=timezone.utc)
    now_mjd = Time(now).mjd

    history = fetch_pointing_history(
        str(mock_ingest_db),
        start_mjd=now_mjd - 1.0,
        end_mjd=now_mjd + 1.0
    )

    assert len(history) >= 0
    if len(history) > 0:
        assert hasattr(history[0], "ra_deg")
        assert hasattr(history[0], "dec_deg")
        assert hasattr(history[0], "timestamp")
```

### Integration Test Script

Create a test script:

```bash
#!/bin/bash
# test_pointing_history_api.sh

BASE_URL="http://localhost:8000/api"

echo "Testing /api/pointing_history endpoint..."
echo ""

# Test 1: Basic request
echo "Test 1: Basic request (last 7 days)"
python3 << 'PYEOF'
from astropy.time import Time
now = Time.now()
week_ago = Time(now.mjd - 7, format='mjd')
print(f"curl \"{BASE_URL}/pointing_history?start_mjd={week_ago.mjd:.2f}&end_mjd={now.mjd:.2f}\"")
PYEOF

response=$(curl -s "${BASE_URL}/pointing_history?start_mjd=60300&end_mjd=60400")
http_code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/pointing_history?start_mjd=60300&end_mjd=60400")

if [ "$http_code" = "200" ]; then
    echo "✓ HTTP 200 OK"
    item_count=$(echo "$response" | jq '.items | length' 2>/dev/null || echo "0")
    echo "  Found $item_count pointing records"
else
    echo "✗ HTTP $http_code"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
fi

# Test 2: Empty time range
echo ""
echo "Test 2: Empty time range (should return empty list)"
response=$(curl -s "${BASE_URL}/pointing_history?start_mjd=70000&end_mjd=70001")
item_count=$(echo "$response" | jq '.items | length' 2>/dev/null || echo "0")
if [ "$item_count" = "0" ]; then
    echo "✓ Returns empty list as expected"
else
    echo "⚠ Unexpected: Found $item_count items"
fi

# Test 3: Invalid parameters
echo ""
echo "Test 3: Missing parameters (should return 422)"
http_code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/pointing_history")
if [ "$http_code" = "422" ]; then
    echo "✓ Returns 422 validation error as expected"
else
    echo "⚠ Unexpected HTTP code: $http_code"
fi

echo ""
echo "Testing complete!"
```

## Troubleshooting

### Endpoint Returns Empty Results

1. **Check database locations:**

   ```bash
   ls -lh /data/dsa110-contimg/state/ingest.sqlite3
   ls -lh /data/dsa110-contimg/state/products.sqlite3
   ```

2. **Verify data exists:**

   ```bash
   python3 << 'EOF'
   import sqlite3
   # Check ingest DB
   conn = sqlite3.connect('/data/dsa110-contimg/state/ingest.sqlite3')
   cursor = conn.cursor()
   cursor.execute("SELECT COUNT(*) FROM pointing_history")
   print(f"Ingest DB: {cursor.fetchone()[0]} records")
   cursor.execute("SELECT MIN(timestamp), MAX(timestamp) FROM pointing_history")
   min_ts, max_ts = cursor.fetchone()
   print(f"  Timestamp range: {min_ts} to {max_ts}")
   conn.close()
   EOF
   ```

3. **Check API logs:**
   ```bash
   sudo journalctl -u contimg-api.service -f
   ```

### Endpoint Returns 500 Error

1. **Check API configuration:**

   ```bash
   # Verify environment variables
   echo $PIPELINE_QUEUE_DB
   echo $PIPELINE_PRODUCTS_DB
   ```

2. **Test database connections:**

   ```bash
   python3 << 'EOF'
   from pathlib import Path
   from dsa110_contimg.database.products import ensure_ingest_db, ensure_products_db

   try:
       ingest_db = Path('/data/dsa110-contimg/state/ingest.sqlite3')
       conn = ensure_ingest_db(ingest_db)
       conn.execute("SELECT 1").fetchone()
       conn.close()
       print("✓ Ingest DB connection OK")
   except Exception as e:
       print(f"✗ Ingest DB error: {e}")

   try:
       products_db = Path('/data/dsa110-contimg/state/products.sqlite3')
       conn = ensure_products_db(products_db)
       conn.execute("SELECT 1").fetchone()
       conn.close()
       print("✓ Products DB connection OK")
   except Exception as e:
       print(f"✗ Products DB error: {e}")
   EOF
   ```

## Frontend Testing

The frontend uses this endpoint via the `PointingVisualization` component. To
test:

1. **Open the dashboard:**

   ```bash
   # Start frontend (if not running)
   cd /data/dsa110-contimg/frontend
   npm run dev
   ```

2. **Check browser console:**
   - Open browser DevTools (F12)
   - Go to Network tab
   - Filter for `pointing_history`
   - Verify requests are successful (200 status)

3. **Verify visualization:**
   - The pointing visualization should display Dec vs time
   - Check that data points appear on the plot
   - Verify time range selector works

## Related Documentation

- API Endpoints: `docs/reference/api-endpoints.md`
- Pointing Visualization: `docs/how-to/pointing-visualization.md`
- API Testing: `docs/reference/API_TEST_COMMANDS.md`
