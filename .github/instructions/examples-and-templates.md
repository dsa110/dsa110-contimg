---
description: Canonical examples and templates for common tasks
applyTo: "**"
---

# Examples and Templates

## Fast UVH5 metadata read
```python
from dsa110_contimg.utils import FastMeta, get_uvh5_mid_mjd

mid_mjd = get_uvh5_mid_mjd("/data/incoming/2025-01-15T12:00:00_sb00.hdf5")
with FastMeta("/data/incoming/2025-01-15T12:00:00_sb00.hdf5") as meta:
    times = meta.time_array
    freqs = meta.freq_array
```

## Grouping subbands (legacy tolerance)
```python
from dsa110_contimg.database.hdf5_index import query_subband_groups

groups = query_subband_groups(
    hdf5_db="/data/dsa110-contimg/state/db/pipeline.sqlite3",
    start_time="2025-10-05T00:00:00",
    end_time="2025-10-05T01:00:00",
    tolerance_s=1.0,
    cluster_tolerance_s=60.0,
)
```

## Convert groups to MS (batch)
```python
from dsa110_contimg.conversion.strategies.hdf5_orchestrator import convert_subband_groups_to_ms

convert_subband_groups_to_ms(
    input_dir="/data/incoming",
    output_dir="/stage/dsa110-contimg/ms",
    start_time="2025-10-05T00:00:00",
    end_time="2025-10-05T01:00:00",
)
```

## Streaming converter launch
```bash
PIPELINE_DB=/data/dsa110-contimg/state/db/pipeline.sqlite3 \
python -m dsa110_contimg.conversion.streaming.streaming_converter \
  --input-dir /data/incoming \
  --output-dir /stage/dsa110-contimg/ms \
  --scratch-dir /stage/dsa110-contimg/scratch \
  --monitoring --monitor-interval 60
```

## Structured logging in pipeline components
```python
from dsa110_contimg.pipeline.structured_logging import get_logger, set_correlation_id

logger = get_logger(__name__)
set_correlation_id("corr-123")
logger.info(
    "conversion_complete",
    component="conversion",
    group_id="2025-01-15T12:00:00",
    output_ms="/stage/dsa110-contimg/ms/2025-01-15T12:00:00.ms",
)
```

## Fast API test pattern
```python
import pytest
from httpx import AsyncClient
from dsa110_contimg.api.app import app

@pytest.mark.asyncio
async def test_get_image(api_client: AsyncClient):
    resp = await api_client.get("/api/v1/images/123")
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
```

## Frontend fetch hook pattern
```tsx
import { useQuery } from '@tanstack/react-query';
import { api } from '@/api/client';

export function useImages() {
  return useQuery({
    queryKey: ['images'],
    queryFn: async () => (await api.get('/api/v1/images')).data,
  });
}
```

