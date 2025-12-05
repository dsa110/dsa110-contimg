# Ingestion Architecture

**How UVH5 subband files flow from correlator to Measurement Sets.**

!!! note "Version"
Last updated: December 5, 2025

---

## Overview

The DSA-110 correlator produces **16 subband files per observation**, each ~5 minutes
of data. The ingestion system:

1. **Discovers** new files via scheduled polling
2. **Groups** subbands by timestamp (within tolerance)
3. **Normalizes** filenames to use sb00's timestamp
4. **Converts** complete groups to Measurement Sets

## Architecture

```
ABSURD Scheduler (every minute)
        │
        ▼
┌───────────────────────────────┐
│  scan-ingestion-directory     │  ← Checks /data/incoming for new files
└───────────────────────────────┘
        │
        ▼ (spawns one task per new file)
┌───────────────────────────────┐
│  ingest-subband               │  ← Records file, tracks group progress
└───────────────────────────────┘
        │
        ▼ (when 16/16 subbands collected)
┌───────────────────────────────┐
│  normalize-group              │  ← Renames files to sb00's timestamp
└───────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│  convert-group                │  ← Converts to Measurement Set
└───────────────────────────────┘
        │
        ▼
/stage/dsa110-contimg/ms/YYYY-MM-DDTHH:MM:SS.ms
```

## Components

### Scheduled Scanner

The `scan-ingestion-directory` task runs every minute via ABSURD scheduler:

- Polls `/data/incoming/` for `*_sb*.hdf5` files
- Compares against recorded files in PostgreSQL
- Spawns `ingest-subband` tasks for new files

### Subband Recording

Each `ingest-subband` task:

- Parses filename: `2025-01-15T12:00:00_sb05.hdf5` → group_id, subband_idx
- Reads metadata (dec_deg) from HDF5 header
- Records in `absurd.ingestion_subbands` table
- Updates group count in `absurd.ingestion_groups`
- When 16 subbands collected → spawns `normalize-group`

### Filename Normalization

The `normalize-group` task:

- Finds sb00's timestamp (canonical group_id)
- Renames all 16 files to use that timestamp
- Example: `2025-01-15T12:00:02_sb05.hdf5` → `2025-01-15T12:00:00_sb05.hdf5`
- Ensures consistent naming for downstream processing

### Conversion

The `convert-group` task:

- Loads all 16 subbands into pyuvdata
- Combines using `uvdata += subband` operator
- Writes Measurement Set via DirectSubbandWriter
- Updates antenna positions to DSA-110 coordinates
- Auto-detects and renames calibrator fields

## Database Schema

```sql
-- In absurd schema (PostgreSQL)

CREATE TABLE absurd.ingestion_groups (
    group_id TEXT PRIMARY KEY,          -- e.g., "2025-01-15T12:00:00"
    state TEXT DEFAULT 'collecting',    -- collecting, pending, converting, completed, failed
    subband_count INTEGER DEFAULT 0,
    expected_subbands INTEGER DEFAULT 16,
    dec_deg FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    ms_path TEXT,
    error TEXT
);

CREATE TABLE absurd.ingestion_subbands (
    group_id TEXT REFERENCES absurd.ingestion_groups(group_id),
    subband_idx INTEGER NOT NULL,       -- 0-15
    file_path TEXT NOT NULL,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (group_id, subband_idx)
);
```

## Configuration

### Enable Ingestion

```python
from dsa110_contimg.absurd import AbsurdClient, setup_ingestion_schedule
from dsa110_contimg.absurd.config import AbsurdConfig

async def main():
    config = AbsurdConfig.from_env()
    async with AbsurdClient(config.database_url) as client:
        result = await setup_ingestion_schedule(client)
        print(f"Ingestion schedule: {result}")

asyncio.run(main())
```

### Environment Variables

| Variable              | Default                    | Description                       |
| --------------------- | -------------------------- | --------------------------------- |
| `ABSURD_DATABASE_URL` | (required)                 | PostgreSQL connection URL         |
| `CONTIMG_INPUT_DIR`   | `/data/incoming`           | Directory to watch for HDF5 files |
| `CONTIMG_OUTPUT_DIR`  | `/stage/dsa110-contimg/ms` | Output directory for MS files     |

## Monitoring

### Check Schedule Status

```sql
SELECT name, cron_expression, last_run_at, next_run_at, state
FROM absurd.scheduled_tasks
WHERE name = 'ingestion_directory_scan';
```

### View Ingestion Stats

```python
from dsa110_contimg.absurd import get_ingestion_stats

stats = await get_ingestion_stats()
print(f"Collecting: {stats['collecting']}")
print(f"Pending: {stats['pending']}")
print(f"Converting: {stats['converting']}")
print(f"Completed: {stats['completed']}")
print(f"Failed: {stats['failed']}")
```

### Prometheus Metrics

The ABSURD worker exports metrics at `/metrics`:

- `absurd_tasks_total{queue="dsa110-ingestion", status="completed"}` - Completed tasks
- `absurd_tasks_duration_seconds` - Task duration histogram
- `absurd_queue_depth{queue="dsa110-ingestion"}` - Pending tasks

## Troubleshooting

### Files Not Being Ingested

1. Check scheduler is running:

   ```sql
   SELECT * FROM absurd.scheduled_tasks WHERE name = 'ingestion_directory_scan';
   ```

2. Check for files in incoming:

   ```bash
   ls -la /data/incoming/*.hdf5 | head
   ```

3. Check task failures:
   ```sql
   SELECT task_id, error, created_at
   FROM absurd.tasks
   WHERE queue_name = 'dsa110-ingestion' AND status = 'failed'
   ORDER BY created_at DESC LIMIT 10;
   ```

### Group Stuck in Collecting

Check which subbands are missing:

```sql
SELECT g.group_id, g.subband_count,
       array_agg(s.subband_idx ORDER BY s.subband_idx) as have_subbands
FROM absurd.ingestion_groups g
LEFT JOIN absurd.ingestion_subbands s ON g.group_id = s.group_id
WHERE g.state = 'collecting'
GROUP BY g.group_id, g.subband_count;
```

### Manual Retry

```python
from dsa110_contimg.absurd import AbsurdClient
from dsa110_contimg.absurd.config import AbsurdConfig

async def retry_failed_group(group_id: str):
    config = AbsurdConfig.from_env()
    async with AbsurdClient(config.database_url) as client:
        await client.spawn_task(
            queue_name="dsa110-ingestion",
            task_name="convert-group",
            params={"inputs": {"group_id": group_id}},
        )
```

## Migration from SQLite Streaming Converter

The old SQLite-based streaming converter has been archived. Key differences:

| Aspect  | Old (SQLite)              | New (ABSURD)                    |
| ------- | ------------------------- | ------------------------------- |
| Queue   | SQLite `processing_queue` | PostgreSQL `absurd.tasks`       |
| Watcher | watchdog inotify daemon   | Scheduled polling (1 min)       |
| Service | `contimg-stream.service`  | `contimg-absurd-worker.service` |
| Metrics | Custom logging            | Prometheus integration          |
| Retry   | Manual intervention       | Automatic with DLQ              |

The old code is archived in `scripts/archive/streaming-converter/`.
