# Database Reference: data_registry.sqlite3

**Location**: `/data/dsa110-contimg/state/data_registry.sqlite3`  
**Purpose**: Data product publishing and QA status tracking  
**Size**: ~64 KB (typical)

---

## Overview

The `data_registry.sqlite3` database tracks the lifecycle of data products from
staging through QA validation to final publishing. It implements the
auto-publish workflow ensuring only validated products reach the published
directory.

---

## Tables

### 1. `data_registry` - Product Publishing Registry

**Purpose**: Track data products through staging, QA, and publishing

**Schema**:

```sql
CREATE TABLE data_registry (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_type TEXT NOT NULL,             -- 'mosaic', 'image', 'ms', etc.
    data_id TEXT NOT NULL UNIQUE,        -- Unique identifier
    base_path TEXT NOT NULL,             -- Base directory path
    status TEXT NOT NULL DEFAULT 'staging',  -- Current status
    stage_path TEXT NOT NULL,            -- Path in staging area
    published_path TEXT,                 -- Path in published area
    created_at REAL NOT NULL,            -- Creation timestamp
    staged_at REAL NOT NULL,             -- Staging timestamp
    published_at REAL,                   -- Publishing timestamp
    publish_mode TEXT,                   -- 'copy' or 'move'
    metadata_json TEXT,                  -- JSON metadata
    qa_status TEXT,                      -- QA result
    validation_status TEXT,              -- Validation result
    finalization_status TEXT DEFAULT 'pending',  -- Finalization status
    auto_publish_enabled INTEGER DEFAULT 1,      -- Auto-publish flag
    publish_attempts INTEGER DEFAULT 0,  -- Number of publish attempts
    publish_error TEXT,                  -- Last publish error
    photometry_status TEXT DEFAULT NULL, -- Photometry status
    photometry_job_id TEXT DEFAULT NULL, -- Photometry job ID
    UNIQUE(data_type, data_id)
);

CREATE INDEX idx_data_registry_type_status ON data_registry(data_type, status);
CREATE INDEX idx_data_registry_status ON data_registry(status);
CREATE INDEX idx_data_registry_published_at ON data_registry(published_at);
CREATE INDEX idx_data_registry_finalization ON data_registry(finalization_status);
```

---

## Status Values

| Status       | Description                          |
| ------------ | ------------------------------------ |
| `staging`    | Product in staging area, awaiting QA |
| `validated`  | QA passed, ready for publishing      |
| `publishing` | Publishing in progress               |
| `published`  | Successfully published               |
| `failed`     | Publishing failed                    |
| `retracted`  | Published then removed               |

---

## QA Status Values

| QA Status | Description             |
| --------- | ----------------------- |
| `pending` | QA not yet run          |
| `running` | QA in progress          |
| `passed`  | QA checks passed        |
| `failed`  | QA checks failed        |
| `warning` | QA passed with warnings |

---

## Validation Status Values

| Validation Status | Description        |
| ----------------- | ------------------ |
| `pending`         | Validation not run |
| `validated`       | Product validated  |
| `invalid`         | Validation failed  |

---

## Finalization Status Values

| Finalization Status | Description            |
| ------------------- | ---------------------- |
| `pending`           | Not yet finalized      |
| `finalized`         | Ready for auto-publish |
| `rejected`          | Finalization rejected  |

---

## Auto-Publish Criteria

A product is auto-published when **ALL** of the following are true:

1. `status='staging'`
2. `auto_publish_enabled=1`
3. `qa_status='passed'`
4. `validation_status='validated'`
5. `finalization_status='finalized'`
6. `photometry_status='completed'` (if photometry enabled)

---

## Common Queries

### Products Ready for Publishing

```sql
-- Find products that meet auto-publish criteria
SELECT data_id, data_type, stage_path
FROM data_registry
WHERE status='staging'
  AND auto_publish_enabled=1
  AND qa_status='passed'
  AND validation_status='validated'
  AND finalization_status='finalized'
  AND (photometry_status='completed' OR photometry_status IS NULL);
```

### Publishing Status

```sql
-- Get publishing status for a product
SELECT data_id, status, published_at, published_path
FROM data_registry
WHERE data_id='mosaic_2025-11-18_12-00-00';

-- List published products
SELECT data_id, data_type, published_at
FROM data_registry
WHERE status='published'
ORDER BY published_at DESC;
```

### Failed Publishing

```sql
-- Find failed publishing attempts
SELECT data_id, publish_attempts, publish_error
FROM data_registry
WHERE status='failed'
ORDER BY publish_attempts DESC;

-- Products with multiple failed attempts
SELECT data_id, publish_attempts, publish_error
FROM data_registry
WHERE publish_attempts > 3;
```

### QA and Validation Status

```sql
-- Products awaiting QA
SELECT data_id, data_type, staged_at
FROM data_registry
WHERE qa_status='pending';

-- QA failures
SELECT data_id, qa_status, validation_status, metadata_json
FROM data_registry
WHERE qa_status='failed';

-- Products with warnings
SELECT data_id, data_type, qa_status
FROM data_registry
WHERE qa_status='warning';
```

### Photometry Status

```sql
-- Products awaiting photometry
SELECT data_id, photometry_status, photometry_job_id
FROM data_registry
WHERE photometry_status IN ('pending', 'running');

-- Products with completed photometry
SELECT data_id, photometry_status
FROM data_registry
WHERE photometry_status='completed';
```

### Staging Area Overview

```sql
-- Count products by status
SELECT status, COUNT(*) as n_products
FROM data_registry
GROUP BY status;

-- Count by data type
SELECT data_type, status, COUNT(*)
FROM data_registry
GROUP BY data_type, status;

-- Age of staging products
SELECT data_id,
       (strftime('%s','now') - staged_at) / 3600.0 as age_hours
FROM data_registry
WHERE status='staging'
ORDER BY age_hours DESC;
```

---

## Python Access Examples

### Register New Product

```python
from pathlib import Path
from dsa110_contimg.database.data_registry import (
    ensure_data_registry_db,
    register_data_instance
)

# Open database
conn = ensure_data_registry_db(Path("state/data_registry.sqlite3"))

# Register mosaic in staging
register_data_instance(
    conn,
    data_type="mosaic",
    data_id="mosaic_2025-11-18_12-00-00",
    stage_path="/stage/dsa110-contimg/mosaics/mosaic_2025-11-18_12-00-00.fits",
    auto_publish=True
)

conn.close()
```

### Update QA Status

```python
from dsa110_contimg.database.data_registration import update_qa_status

# Mark QA as passed
update_qa_status(
    conn,
    data_id="mosaic_2025-11-18_12-00-00",
    qa_status="passed",
    validation_status="validated"
)
```

### Finalize Product

```python
from dsa110_contimg.database.data_registration import finalize_data

# Finalize product (triggers auto-publish if criteria met)
finalize_data(
    conn,
    data_id="mosaic_2025-11-18_12-00-00",
    qa_status="passed",
    validation_status="validated"
)
```

### Publish Product

```python
from dsa110_contimg.database.data_registration import publish_data_instance

# Manually publish
success = publish_data_instance(
    conn,
    data_id="mosaic_2025-11-18_12-00-00",
    published_dir="/data/dsa110-contimg/products/mosaics",
    mode="move"  # or "copy"
)
```

### Query Ready Products

```python
import sqlite3

conn = sqlite3.connect("state/data_registry.sqlite3")
conn.row_factory = sqlite3.Row

# Get products ready for publishing
cursor = conn.cursor()
cursor.execute("""
    SELECT data_id, stage_path
    FROM data_registry
    WHERE status='staging'
      AND auto_publish_enabled=1
      AND qa_status='passed'
      AND validation_status='validated'
      AND finalization_status='finalized'
""")

for row in cursor.fetchall():
    print(f"Ready: {row['data_id']}")

conn.close()
```

---

## Publishing Workflow

### 1. Registration

```python
# Product created in staging
register_data_instance(
    conn,
    data_type="mosaic",
    data_id=mosaic_id,
    stage_path=stage_path,
    auto_publish=True
)
# Status: staging, qa_status=NULL, finalization_status=pending
```

### 2. QA Execution

```python
# Run QA checks
qa_result = run_qa_checks(stage_path)

# Update status
update_qa_status(
    conn,
    data_id=mosaic_id,
    qa_status="passed" if qa_result.passed else "failed",
    validation_status="validated" if qa_result.valid else "invalid"
)
```

### 3. Photometry (if enabled)

```python
# Submit photometry job
job_id = submit_photometry_job(mosaic_id)

# Update status
conn.execute("""
    UPDATE data_registry
    SET photometry_status='running', photometry_job_id=?
    WHERE data_id=?
""", (job_id, mosaic_id))

# ... photometry completes ...

conn.execute("""
    UPDATE data_registry
    SET photometry_status='completed'
    WHERE data_id=?
""", (mosaic_id,))
```

### 4. Finalization

```python
# Finalize (triggers auto-publish check)
finalize_data(
    conn,
    data_id=mosaic_id,
    qa_status="passed",
    validation_status="validated"
)
# If all criteria met, triggers auto-publish
```

### 5. Publishing

```python
# Auto-publish moves file and updates registry
# Status: publishing -> published
# published_path and published_at are set
```

---

## Error Handling

### Retry Failed Publishing

```python
# Retry publishing for failed products
cursor.execute("""
    SELECT data_id, stage_path
    FROM data_registry
    WHERE status='failed'
      AND publish_attempts < 3
""")

for row in cursor.fetchall():
    try:
        publish_data_instance(conn, row['data_id'], published_dir)
    except Exception as e:
        # Log error, increment attempts
        pass
```

### Manual Publishing

```bash
# Use CLI to manually publish
python -m dsa110_contimg.database.cli publish \
  --db state/data_registry.sqlite3 \
  --data-id mosaic_2025-11-18_12-00-00
```

---

## Maintenance Queries

### Reset Failed Product

```sql
-- Reset to staging for retry
UPDATE data_registry
SET status='staging',
    publish_attempts=0,
    publish_error=NULL
WHERE data_id='mosaic_2025-11-18_12-00-00';
```

### Disable Auto-Publish

```sql
-- Disable auto-publish for specific product
UPDATE data_registry
SET auto_publish_enabled=0
WHERE data_id='mosaic_2025-11-18_12-00-00';
```

### Clean Up Old Staging Products

```sql
-- List old staging products (>7 days)
SELECT data_id, stage_path,
       (strftime('%s','now') - staged_at) / 86400.0 as age_days
FROM data_registry
WHERE status='staging'
  AND age_days > 7;
```

### Database Statistics

```sql
-- Publishing statistics
SELECT
    COUNT(*) as total_products,
    SUM(CASE WHEN status='published' THEN 1 ELSE 0 END) as published,
    SUM(CASE WHEN status='staging' THEN 1 ELSE 0 END) as staging,
    SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
    AVG(publish_attempts) as avg_attempts
FROM data_registry;

-- Success rate
SELECT
    ROUND(100.0 * SUM(CASE WHEN status='published' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_pct
FROM data_registry
WHERE status IN ('published', 'failed');
```

---

## CLI Commands

### List Staging Products

```bash
sqlite3 state/data_registry.sqlite3 \
  "SELECT data_id, status, qa_status FROM data_registry
   WHERE status='staging'"
```

### Check Publish Status

```bash
python -m dsa110_contimg.database.cli status \
  --db state/data_registry.sqlite3 \
  --data-id mosaic_2025-11-18_12-00-00
```

### Manual Publish

```bash
python -m dsa110_contimg.database.cli publish \
  --db state/data_registry.sqlite3 \
  --data-id mosaic_2025-11-18_12-00-00 \
  --products-base /data/dsa110-contimg/products
```

### Retry Failed

```bash
python -m dsa110_contimg.database.cli retry \
  --db state/data_registry.sqlite3 \
  --data-id mosaic_2025-11-18_12-00-00
```

---

## Related Tables

### 2. `data_relationships` - Product Dependencies

**Purpose**: Track relationships between data products

```sql
CREATE TABLE data_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    created_at REAL NOT NULL
);
```

### 3. `data_tags` - Product Tags

**Purpose**: Tag products for organization and search

```sql
CREATE TABLE data_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at REAL NOT NULL
);
```

---

## Performance Notes

- **Indexes**: Optimized for status and finalization queries
- **Typical Size**: <100 KB with hundreds of products
- **Query Speed**: <10ms for publish-ready queries
- **Concurrency**: Not critical (staging/publishing is serialized)

---

## Related Files

- **Code**: `dsa110_contimg/database/data_registry.py`, `data_registration.py`
- **CLI**: `dsa110_contimg/database/cli.py`
- **Documentation**: `dsa110_contimg/README_PIPELINE_DOCUMENTATION.md`

---

## See Also

- **Products Database**: `docs/reference/database_products_sqlite3.md`
- **Publishing Guide**: `docs/how-to/publishing_workflow.md`
- **Pipeline Documentation**: `dsa110_contimg/FINAL_WORKFLOW_VERIFICATION.md`
