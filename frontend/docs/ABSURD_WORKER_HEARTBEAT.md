# ABSURD Worker Heartbeat System

## Overview

The ABSURD (Asynchronous Backend Service Using Redis Durably) task queue includes an **API heartbeat mechanism** that allows workers to automatically register and maintain their presence in the API's in-memory worker registry. This enables real-time monitoring of worker health and status through the frontend Pipeline Status panel.

## Architecture

### Two Heartbeat Systems

ABSURD workers maintain two independent heartbeat systems:

1. **Database Heartbeat** (existing)

   - Purpose: Track task execution progress
   - Destination: PostgreSQL database
   - Timing: Only sent while actively processing tasks
   - Used by: Task coordination and recovery logic

2. **API Heartbeat** (new)
   - Purpose: Worker presence and health monitoring
   - Destination: FastAPI `/absurd/workers/{worker_id}/heartbeat` endpoint
   - Timing: Continuous background loop (every 10 seconds by default)
   - Used by: Frontend monitoring, operational dashboards

### Why API Heartbeats?

The API monitor (`AbsurdMonitor`) maintains an **in-memory registry** of active workers:

```python
# backend/src/dsa110_contimg/api/v1/absurd/monitor.py
class AbsurdMonitor:
    def __init__(self):
        self.workers: dict[str, WorkerInfo] = {}  # In-memory only!
```

**Problem**: This registry is empty after API restart, and database heartbeats only occur during task processing.

**Solution**: Workers continuously send API heartbeats to maintain their registration, independent of task execution.

## Configuration

### Environment Variables

Configure worker API heartbeats in `backend/.env`:

```bash
# Required: API base URL for heartbeat endpoint
ABSURD_API_BASE_URL=http://localhost:8000

# Optional: Heartbeat interval (default: 10.0 seconds)
ABSURD_API_HEARTBEAT_INTERVAL=10.0

# Required for JWT authentication
DSA110_JWT_SECRET=your-secret-key-here

# Development: Disable auth for local testing
DSA110_AUTH_DISABLED=true
DSA110_ENV=development
```

### Worker Configuration

Workers read these settings via `AbsurdConfig`:

```python
# backend/src/dsa110_contimg/absurd/config.py
@dataclass
class AbsurdConfig:
    api_base_url: str = ""  # Empty string disables API heartbeats
    api_heartbeat_interval_sec: float = 10.0
    # ... other config fields
```

**Note**: If `api_base_url` is empty or not set, API heartbeats are **disabled** and workers operate in database-only mode.

## Implementation

### Worker Heartbeat Loop

Each worker runs a continuous background task alongside task polling:

```python
# backend/src/dsa110_contimg/absurd/worker.py
async def _api_heartbeat_loop(self):
    """Send continuous heartbeats to API monitor."""
    if not self.config.api_base_url:
        return  # API heartbeats disabled

    session = aiohttp.ClientSession()
    token = self._create_jwt_token()

    while True:
        try:
            await session.post(
                f"{self.config.api_base_url}/absurd/workers/{self.worker_id}/heartbeat",
                headers={"Authorization": f"Bearer {token}"},
                json={"state": self.state}
            )
        except Exception as e:
            logger.warning(f"API heartbeat failed: {e}")

        await asyncio.sleep(self.config.api_heartbeat_interval_sec)
```

### JWT Token Generation

Workers authenticate using JWT tokens with `["write"]` scope:

```python
def _create_jwt_token(self, secret: str, worker_id: str) -> str:
    """Generate JWT token for worker authentication."""
    payload = {
        "sub": f"worker:{worker_id}",
        "scope": ["write"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, secret, algorithm="HS256")
```

Tokens are refreshed every 50 minutes to prevent expiration.

## API Endpoints

### Worker Heartbeat

**POST** `/absurd/workers/{worker_id}/heartbeat`

Registers or updates worker in the API monitor's in-memory registry.

**Request:**

```json
{
  "state": "active" // or "idle", "stopped"
}
```

**Headers:**

```
Authorization: Bearer <jwt_token>
```

**Response:**

```json
{
  "status": "ok"
}
```

### List Workers

**GET** `/absurd/workers`

Returns all registered workers and counts.

**Response:**

```json
{
  "workers": [
    {
      "worker_id": "lxd110h17-fa9d2dff",
      "state": "active",
      "last_heartbeat": "2024-12-03T10:30:00Z"
    }
  ],
  "total": 1,
  "active": 1,
  "idle": 0,
  "stopped": 0
}
```

## Frontend Integration

### Pipeline Status Panel

The `PipelineStatusPanel` component displays worker status:

```tsx
// frontend/src/components/pipeline/PipelineStatusPanel.tsx
const { data: workersRes } = useQuery({
  queryKey: ["absurd-workers"],
  queryFn: () => client.get("/absurd/workers").then((r) => r.data),
});

const workerCount =
  workersRes?.total ??
  (Array.isArray(workersRes?.workers) ? workersRes.workers.length : 0);
```

**Display:**

- Status: "Healthy" (when workers > 0) or "No Workers" (when workers = 0)
- Worker Count: Total number of registered workers
- Color: Green for healthy, red for no workers

## Deployment

### Systemd Service

Workers are deployed as systemd services with environment file:

```ini
# /etc/systemd/system/dsa110-absurd-worker@.service
[Unit]
Description=DSA-110 ABSURD Worker %i
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/data/dsa110-contimg/backend
EnvironmentFile=/data/dsa110-contimg/backend/.env
Environment="PYTHONPATH=/data/dsa110-contimg/backend/src"
ExecStart=/opt/miniforge/envs/casa6/bin/python -m dsa110_contimg.absurd
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
# Start worker instance
sudo systemctl start dsa110-absurd-worker@1

# Check status
sudo systemctl status dsa110-absurd-worker@1

# View logs
sudo journalctl -u dsa110-absurd-worker@1 -f

# Restart all workers
sudo systemctl restart dsa110-absurd-worker@*
```

## Monitoring

### Check Worker Registration

```bash
# Query workers endpoint
curl http://localhost:8000/absurd/workers | jq

# Expected output:
{
  "workers": [
    {
      "worker_id": "lxd110h17-fa9d2dff",
      "state": "active",
      "last_heartbeat": "2024-12-03T10:30:00Z"
    }
  ],
  "total": 1,
  "active": 1
}
```

### Check Worker Logs

```bash
# View heartbeat activity
sudo journalctl -u dsa110-absurd-worker@1 | grep heartbeat

# Expected output:
Dec 03 10:30:00 lxd110h17 python[12345]: INFO: Sent API heartbeat
Dec 03 10:30:10 lxd110h17 python[12345]: INFO: Sent API heartbeat
```

## Troubleshooting

### Workers Show 0 in Pipeline Status

**Symptom**: Frontend shows "No Workers" even when workers are running.

**Check:**

1. Verify `ABSURD_API_BASE_URL` is set in `backend/.env`
2. Check worker logs for heartbeat errors:
   ```bash
   sudo journalctl -u dsa110-absurd-worker@1 | grep -i "heartbeat\|error"
   ```
3. Test API endpoint directly:
   ```bash
   curl http://localhost:8000/absurd/workers
   ```

**Common causes:**

- `ABSURD_API_BASE_URL` not set (heartbeats disabled)
- API not running or wrong port
- Authentication failures (missing `DSA110_JWT_SECRET`)
- Network connectivity issues

### Authentication Errors

**Symptom**: Worker logs show "401 Unauthorized" on heartbeat.

**Fix:**

1. Ensure `DSA110_JWT_SECRET` is set in `.env`
2. For development, disable auth:
   ```bash
   DSA110_AUTH_DISABLED=true
   DSA110_ENV=development
   ```
3. Restart workers after `.env` changes:
   ```bash
   sudo systemctl restart dsa110-absurd-worker@*
   ```

### Heartbeat Failures

**Symptom**: Worker logs show connection errors on heartbeat.

**Check:**

1. API is running:
   ```bash
   curl http://localhost:8000/api/v1/health
   ```
2. Port 8000 is accessible from worker process
3. Correct base URL (no trailing slash):
   ```bash
   ABSURD_API_BASE_URL=http://localhost:8000  # Correct
   ABSURD_API_BASE_URL=http://localhost:8000/ # Wrong
   ```

### Workers Disappear After API Restart

**Expected behavior**: Worker registry is in-memory only and clears on API restart.

**Resolution**: Workers will re-register automatically within 10 seconds (default heartbeat interval). If workers don't reappear:

1. Verify workers are still running:
   ```bash
   sudo systemctl status dsa110-absurd-worker@*
   ```
2. Check worker logs for heartbeat activity
3. Restart workers if needed

## Testing

### Unit Test

Test worker heartbeat loop in isolation:

```python
# backend/tests/test_worker_heartbeat.py
async def test_api_heartbeat_loop():
    config = AbsurdConfig(
        api_base_url="http://localhost:8000",
        api_heartbeat_interval_sec=5.0
    )
    worker = AbsurdWorker(config)

    # Should send heartbeats every 5 seconds
    await asyncio.sleep(12)  # Allow 2 heartbeats

    # Verify API received heartbeats
    response = await client.get("/absurd/workers")
    assert response.json()["total"] == 1
```

### Integration Test

Test complete flow from worker to frontend:

```javascript
// frontend/scripts/test-pipeline-status.mjs
const response = await fetch("http://localhost:8000/absurd/workers");
const data = await response.json();

console.log("Worker Count:", data.total);
console.log("Active Workers:", data.active);

// Verify frontend displays correctly
await page.goto("http://localhost:3000");
const workerCount = await page
  .locator('[data-testid="worker-count"]')
  .textContent();
console.log("Frontend Worker Count:", workerCount);
```

## Performance Considerations

### Heartbeat Frequency

Default interval: **10 seconds**

**Tradeoffs:**

- **Shorter interval** (5s):
  - Pros: Faster detection of worker failures
  - Cons: More network traffic, more API load
- **Longer interval** (30s):
  - Pros: Lower overhead
  - Cons: Slower failure detection

**Recommendation**: 10 seconds provides good balance for most deployments. Adjust via `ABSURD_API_HEARTBEAT_INTERVAL` if needed.

### Scaling Considerations

**Impact per worker:**

- Network: ~200 bytes per heartbeat (every 10s = 20 bytes/sec)
- API: Single POST request (minimal CPU)
- Memory: ~1KB per worker in registry

**Example scaling:**

- 10 workers: 200 bytes/sec network, 10KB memory
- 100 workers: 2KB/sec network, 100KB memory
- 1000 workers: 20KB/sec network, 1MB memory

**Verdict**: Heartbeat overhead is negligible even at 1000+ workers.

## Future Enhancements

### Planned Features

1. **Worker Metadata**: Include worker hostname, version, capabilities in heartbeat
2. **Health Metrics**: Send CPU/memory usage with heartbeat
3. **Graceful Shutdown**: Worker sends "stopped" state before exit
4. **Heartbeat History**: Store recent heartbeats for debugging
5. **Alert Thresholds**: Notify when worker count drops below threshold

### Potential Improvements

- Add exponential backoff for failed heartbeats
- Support multiple API endpoints for HA
- Add worker registration callback for custom logic
- Implement worker health checks beyond heartbeats

## References

- **Worker Implementation**: `backend/src/dsa110_contimg/absurd/worker.py`
- **Configuration**: `backend/src/dsa110_contimg/absurd/config.py`
- **API Monitor**: `backend/src/dsa110_contimg/api/v1/absurd/monitor.py`
- **Frontend Panel**: `frontend/src/components/pipeline/PipelineStatusPanel.tsx`
- **Systemd Service**: `/etc/systemd/system/dsa110-absurd-worker@.service`

## Change Log

### 2024-12-03 - Initial Implementation

- Added API heartbeat loop to worker
- Implemented JWT token generation
- Added environment variable configuration
- Fixed systemd service for proper `.env` loading
- Updated frontend to parse worker response correctly
- Added comprehensive documentation

---

**Summary**: The ABSURD worker API heartbeat system provides continuous, automatic worker registration for real-time monitoring. Workers independently maintain their presence in the API monitor, enabling accurate health dashboards and operational visibility.
