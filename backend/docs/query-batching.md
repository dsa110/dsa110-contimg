# Query Batching Guide

This guide covers the query batching utilities for optimized multi-record database access.

## Overview

Query batching helps avoid N+1 query problems by fetching multiple records in a single database round-trip. The `query_batch` module provides utilities that work with both SQLite and PostgreSQL backends.

## The N+1 Problem

```python
# BAD: N+1 queries (1 query per image)
for image_id in image_ids:
    image = await repo.get_by_id(image_id)  # N queries

# GOOD: Batch fetch (1-2 queries total)
images = await repo.get_many(image_ids)  # 1 query
```

## Available Batch Methods

All async repositories now have `get_many()` methods:

```python
from dsa110_contimg.api.repositories import (
    AsyncImageRepository,
    AsyncMSRepository,
    AsyncSourceRepository,
    AsyncJobRepository,
)

# Batch fetch images
image_repo = AsyncImageRepository()
images = await image_repo.get_many(["1", "2", "3"])

# Batch fetch MS records
ms_repo = AsyncMSRepository()
ms_records = await ms_repo.get_many(["/path/a.ms", "/path/b.ms"])

# Batch fetch sources
source_repo = AsyncSourceRepository()
sources = await source_repo.get_many(["src-001", "src-002"])

# Batch fetch jobs
job_repo = AsyncJobRepository()
jobs = await job_repo.get_many(["job-2025-01-01", "job-2025-01-02"])
```

## Query Batch Utilities

### chunk_list

Split a list into chunks for batched processing:

```python
from dsa110_contimg.api.query_batch import chunk_list

# Split 1000 IDs into chunks of 100
for chunk in chunk_list(ids, 100):
    results = await fetch_batch(chunk)
```

### BatchQueryBuilder

Build batch queries with proper placeholder handling:

```python
from dsa110_contimg.api.query_batch import BatchQueryBuilder

# SQLite style
builder = BatchQueryBuilder(use_postgres=False)
query, params = builder.build_select(
    table="images",
    columns=["id", "path", "ms_path"],
    id_column="id",
    ids=[1, 2, 3]
)
# query: "SELECT id, path, ms_path FROM images WHERE id IN (?, ?, ?)"

# PostgreSQL style
builder = BatchQueryBuilder(use_postgres=True)
query, params = builder.build_select(
    table="images",
    columns=["id", "path"],
    id_column="id",
    ids=[1, 2, 3]
)
# query: "SELECT id, path FROM images WHERE id IN ($1, $2, $3)"
```

### batch_fetch

Generic async batch fetcher:

```python
from dsa110_contimg.api.query_batch import batch_fetch

async def fetch_images(ids):
    # Your fetch implementation
    return [{"id": id_, "name": f"img-{id_}"} for id_ in ids]

# Fetch in batches of 100, preserve input order
results = await batch_fetch(
    fetch_images,
    [1, 2, 3, ..., 1000],
    batch_size=100,
    preserve_order=True
)
```

### prefetch_related

Prefetch related records to avoid N+1:

```python
from dsa110_contimg.api.query_batch import prefetch_related

images = await image_repo.list_all(limit=100)

# Prefetch MS metadata for all images in one batch
async def fetch_ms_by_paths(paths):
    return await ms_repo.get_many(paths)

images = await prefetch_related(
    images,
    foreign_key="ms_path",
    fetch_func=fetch_ms_by_paths,
    target_attr="ms_record"
)

# Now each image has ms_record attached
for img in images:
    print(f"{img.path}: {img.ms_record.status}")
```

## Constants

```python
from dsa110_contimg.api.query_batch import (
    SQLITE_MAX_PARAMS,  # 900 (SQLite limit is ~999)
    POSTGRES_MAX_PARAMS,  # 1000
    DEFAULT_BATCH_SIZE,  # 100
)
```

## Implementation Details

### Automatic Chunking

The `get_many()` methods automatically chunk large ID lists:

```python
# Even with 10,000 IDs, this works efficiently
images = await image_repo.get_many(ten_thousand_ids)
# Internally: ~100 queries of 100 IDs each
```

### Deduplication

Duplicate IDs are automatically deduplicated:

```python
# IDs with duplicates
ids = [1, 2, 1, 3, 2]

# Only queries for unique IDs
results = await batch_fetch(fetch_func, ids)

# Results mapped back to all requested positions
assert len(results) == 5
```

### Order Preservation

By default, results are returned in the same order as input IDs:

```python
images = await image_repo.get_many([3, 1, 2])
# Returns in order: [image-3, image-1, image-2]
```

## Performance Tips

1. **Use batch methods for lists**: Always prefer `get_many()` over loops with `get_by_id()`

2. **Prefetch related data**: Use `prefetch_related()` instead of fetching in loops

3. **Tune batch size**: Default is 100, adjust based on:

   - Network latency (higher batch size for high latency)
   - Memory constraints (lower batch size for large records)

4. **Use appropriate backend**: PostgreSQL handles larger batches better than SQLite

## Testing

Run the batch query tests:

```bash
cd /data/dsa110-contimg/backend
python -m pytest tests/unit/api/test_query_batch.py -v
```
