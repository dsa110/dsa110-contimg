---
description: Canonical examples and templates for common tasks
applyTo: "**"
---

# Examples and Templates

## Quick metadata read (context manager)
```python
from pathlib import Path
import json

def read_metadata(path: Path) -> dict:
    with path.open() as f:
        return json.load(f)

source_path = Path("your_source_path")
meta = read_metadata(source_path)
```

## Group items by time tolerance
```python
from datetime import datetime, timedelta
from typing import List, Dict

def group_by_time(records: List[Dict], tolerance_seconds: float) -> List[List[Dict]]:
    records = sorted(records, key=lambda r: r["timestamp"])
    groups: List[List[Dict]] = []
    current: List[Dict] = []

    for record in records:
        if current and (record["timestamp"] - current[-1]["timestamp"]) > timedelta(seconds=tolerance_seconds):
            groups.append(current)
            current = []
        current.append(record)

    if current:
        groups.append(current)
    return groups
```

## Batch process with retries and logging
```python
import logging
from typing import Iterable, Callable, Any

logger = logging.getLogger(__name__)

def process_batch(items: Iterable[Any], handler: Callable[[Any], None]) -> None:
    for item in items:
        try:
            handler(item)
        except Exception as exc:  # replace with specific exceptions
            logger.error("item_failed", extra={"item": item, "error": str(exc)})
            # optional: enqueue for retry/dead-letter handling
```

## Structured logging with correlation ID
```python
import logging

logger = logging.getLogger(__name__)
correlation_id = "corr-123"

logger.info(
    "job_complete",
    extra={
        "component": "job_runner",
        "correlation_id": correlation_id,
        "output": "output_reference",
    },
)
```

## API test pattern
```python
import pytest
from fastapi.testclient import TestClient
from my_app import app  # replace with actual app

@pytest.fixture(scope="module")
def api_client():
    return TestClient(app)

def test_endpoint(api_client: TestClient):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").startswith("application/json")
```

## Frontend fetch hook pattern
```tsx
import { useQuery } from '@tanstack/react-query';

export function useItems() {
  return useQuery({
    queryKey: ['items'],
    queryFn: async () => {
      const res = await fetch('/api/items');
      if (!res.ok) throw new Error('Request failed');
      return res.json();
    },
  });
}
```
