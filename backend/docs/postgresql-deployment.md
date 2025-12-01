# PostgreSQL Deployment Guide

This guide covers deploying PostgreSQL for the DSA-110 Continuum Imaging Pipeline.

## Overview

The pipeline supports two database backends:

- **SQLite** (default): Simple, file-based database for development and small deployments
- **PostgreSQL**: Scalable, production-grade database with connection pooling

## Quick Start

### 1. Start PostgreSQL Container

```bash
cd /data/dsa110-contimg/backend

# Start PostgreSQL
docker-compose -f docker-compose.postgresql.yml up -d postgres

# Verify it's running
docker ps | grep postgres
pg_isready -h localhost -p 5432 -U dsa110
```

### 2. Verify Schema Initialization

```bash
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 -c "\dt"
```

Expected output: 15 tables (images, photometry, jobs, ms_index, etc.)

### 3. Configure API to Use PostgreSQL

Set environment variables before starting the API:

```bash
export DSA110_DB_BACKEND=postgresql
export DSA110_DB_PG_HOST=localhost
export DSA110_DB_PG_PORT=5432
export DSA110_DB_PG_DATABASE=dsa110
export DSA110_DB_PG_USER=dsa110
export DSA110_DB_PG_PASSWORD=dsa110_dev_password
```

Or source the provided environment file:

```bash
source .env.postgresql
```

## Configuration Reference

### Environment Variables

| Variable                | Default   | Description                             |
| ----------------------- | --------- | --------------------------------------- |
| `DSA110_DB_BACKEND`     | sqlite    | Database backend (sqlite or postgresql) |
| `DSA110_DB_PG_HOST`     | localhost | PostgreSQL host                         |
| `DSA110_DB_PG_PORT`     | 5432      | PostgreSQL port                         |
| `DSA110_DB_PG_DATABASE` | dsa110    | Database name                           |
| `DSA110_DB_PG_USER`     | dsa110    | Database user                           |
| `DSA110_DB_PG_PASSWORD` | -         | Database password                       |
| `DSA110_DB_PG_POOL_MIN` | 1         | Minimum pool connections                |
| `DSA110_DB_PG_POOL_MAX` | 10        | Maximum pool connections                |
| `DSA110_DB_PG_SSL`      | false     | Enable SSL connection                   |

### Python API Usage

```python
from dsa110_contimg.api.db_adapters.backend import DatabaseConfig, create_adapter

# Auto-configure from environment
config = DatabaseConfig.from_env()
adapter = create_adapter(config)

# Connect and use
await adapter.connect()
result = await adapter.fetch_all("SELECT * FROM images LIMIT 10")
await adapter.disconnect()
```

## Data Migration

### Migrate from SQLite to PostgreSQL

Use the provided migration script:

```bash
cd /data/dsa110-contimg/backend

# Dry run (preview what would be migrated)
python scripts/postgres/migrate_sqlite_to_postgres.py --dry-run

# Run migration
python scripts/postgres/migrate_sqlite_to_postgres.py

# Migrate specific tables only
python scripts/postgres/migrate_sqlite_to_postgres.py --tables images photometry

# Save results to JSON
python scripts/postgres/migrate_sqlite_to_postgres.py --output migration_results.json
```

### Migration Script Options

| Option          | Description                                         |
| --------------- | --------------------------------------------------- |
| `--sqlite`      | Path to SQLite database (default: products.sqlite3) |
| `--pg-host`     | PostgreSQL host                                     |
| `--pg-port`     | PostgreSQL port                                     |
| `--pg-database` | PostgreSQL database                                 |
| `--pg-user`     | PostgreSQL user                                     |
| `--pg-password` | PostgreSQL password                                 |
| `--batch-size`  | Batch size for inserts (default: 1000)              |
| `--dry-run`     | Preview without making changes                      |
| `--tables`      | Specific tables to migrate                          |
| `--output`      | Save results to JSON file                           |

## Docker Configuration

### docker-compose.postgresql.yml

The compose file defines:

- `postgres`: PostgreSQL 16 Alpine container
- `api-pg`: API service configured for PostgreSQL

```yaml
services:
  postgres:
    image: postgres:16-alpine
    container_name: dsa110-postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/postgres/init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    environment:
      POSTGRES_DB: dsa110
      POSTGRES_USER: dsa110
      POSTGRES_PASSWORD: dsa110_dev_password
```

### Start Both Services

```bash
# Start PostgreSQL and API
docker-compose -f docker-compose.postgresql.yml up -d

# View logs
docker-compose -f docker-compose.postgresql.yml logs -f
```

## Connection Pooling

The PostgreSQL adapter uses asyncpg's connection pool:

- **Min connections**: 1-2 (idle connections maintained)
- **Max connections**: 10 (concurrent query limit)
- Automatic connection health checks
- Graceful reconnection on connection loss

### Tuning Pool Size

For high-load scenarios:

```bash
export DSA110_DB_PG_POOL_MIN=5
export DSA110_DB_PG_POOL_MAX=20
```

For memory-constrained environments:

```bash
export DSA110_DB_PG_POOL_MIN=1
export DSA110_DB_PG_POOL_MAX=5
```

## Troubleshooting

### Cannot Connect to PostgreSQL

```bash
# Check container is running
docker ps | grep postgres

# Check PostgreSQL is accepting connections
pg_isready -h localhost -p 5432 -U dsa110

# Check logs
docker logs dsa110-postgres
```

### Schema Not Initialized

```bash
# Manually run init script
PGPASSWORD=dsa110_dev_password psql -h localhost -U dsa110 -d dsa110 \
  -f scripts/postgres/init.sql
```

### Connection Pool Exhausted

Increase pool size or check for connection leaks:

```python
# Ensure connections are released
async with adapter.acquire() as conn:
    # Use connection
    pass
# Connection is automatically released
```

## Security Considerations

For production deployments:

1. **Change default password**: Update `POSTGRES_PASSWORD` in docker-compose
2. **Enable SSL**: Set `DSA110_DB_PG_SSL=true`
3. **Network isolation**: Use Docker networks or firewall rules
4. **Backup strategy**: Set up pg_dump cron jobs

## Performance Notes

PostgreSQL advantages over SQLite:

- Connection pooling for concurrent access
- Better handling of large datasets
- Built-in query optimization
- Support for complex queries and joins

Use batch operations (see [Query Batching](./query-batching.md)) for bulk data access.

