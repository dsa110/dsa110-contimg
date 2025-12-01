# Database Abstraction Layer

## Overview

The `db_adapters` package provides a unified async interface for database
operations, supporting both SQLite and PostgreSQL backends. This enables a
smooth migration path from SQLite to PostgreSQL without requiring changes to
application code.

## Package Structure

```
src/dsa110_contimg/api/db_adapters/
├── __init__.py              # Public API exports
├── backend.py               # DatabaseAdapter ABC, DatabaseConfig, factory
├── query_builder.py         # Cross-database query building utilities
└── adapters/
    ├── __init__.py
    ├── sqlite_adapter.py    # SQLite implementation (aiosqlite)
    └── postgresql_adapter.py # PostgreSQL implementation (asyncpg)
```

## Quick Start

### Basic Usage

```python
from dsa110_contimg.api.db_adapters import create_adapter, DatabaseConfig

# Create adapter from environment variables
adapter = create_adapter()
await adapter.connect()

# Execute queries
rows = await adapter.fetch_all("SELECT * FROM products")
single = await adapter.fetch_one("SELECT * FROM products WHERE id = ?", (1,))
count = await adapter.fetch_val("SELECT COUNT(*) FROM products")

# Clean up
await adapter.disconnect()
```

### With Explicit Configuration

```python
from dsa110_contimg.api.db_adapters import (
    create_adapter,
    DatabaseConfig,
    DatabaseBackend,
)

# SQLite configuration
sqlite_config = DatabaseConfig(
    backend=DatabaseBackend.SQLITE,
    sqlite_path="/path/to/database.db",
    sqlite_timeout=30.0,
)

# PostgreSQL configuration
pg_config = DatabaseConfig(
    backend=DatabaseBackend.POSTGRESQL,
    pg_host="localhost",
    pg_port=5432,
    pg_database="dsa110",
    pg_user="user",
    pg_password="password",
    pg_pool_min=1,
    pg_pool_max=10,
    pg_ssl=True,
)

# Create adapter for the configured backend
adapter = create_adapter(pg_config)
```

## Environment Variables

Configure the database backend via environment variables:

| Variable                   | Default                      | Description                                |
| -------------------------- | ---------------------------- | ------------------------------------------ |
| `DSA110_DB_BACKEND`        | `sqlite`                     | Database backend: `sqlite` or `postgresql` |
| `DSA110_DB_SQLITE_PATH`    | `/data/.../products.sqlite3` | Path to SQLite database                    |
| `DSA110_DB_SQLITE_TIMEOUT` | `30.0`                       | SQLite connection timeout                  |
| `DSA110_DB_PG_HOST`        | `localhost`                  | PostgreSQL host                            |
| `DSA110_DB_PG_PORT`        | `5432`                       | PostgreSQL port                            |
| `DSA110_DB_PG_DATABASE`    | `dsa110`                     | PostgreSQL database name                   |
| `DSA110_DB_PG_USER`        | ``                           | PostgreSQL username                        |
| `DSA110_DB_PG_PASSWORD`    | ``                           | PostgreSQL password                        |
| `DSA110_DB_PG_POOL_MIN`    | `1`                          | Minimum pool connections                   |
| `DSA110_DB_PG_POOL_MAX`    | `10`                         | Maximum pool connections                   |
| `DSA110_DB_PG_SSL`         | `false`                      | Enable SSL connection                      |

## Query Builder

The `QueryBuilder` class generates SQL queries compatible with both backends:

```python
from dsa110_contimg.api.db_adapters import QueryBuilder, DatabaseBackend

# Create builder for target backend
qb = QueryBuilder(DatabaseBackend.SQLITE)

# Build queries
select = qb.select("products", columns=["id", "name"], where="status = ?")
insert = qb.insert("products", columns=["name", "status"])
update = qb.update("products", columns=["name"], where="id = ?")
delete = qb.delete("products", where="id = ?")
upsert = qb.upsert("products", columns=["id", "name"], conflict_columns=["id"])

# Different placeholders per backend
sqlite_qb = QueryBuilder(DatabaseBackend.SQLITE)
pg_qb = QueryBuilder(DatabaseBackend.POSTGRESQL)

sqlite_qb.placeholders(3)  # "?, ?, ?"
pg_qb.placeholders(3)      # "$1, $2, $3"
```

## Query Conversion

Utility functions for converting queries between backends:

```python
from dsa110_contimg.api.db_adapters import (
    convert_sqlite_to_postgresql,
    convert_postgresql_to_sqlite,
)

# Convert SQLite query to PostgreSQL
sqlite_query = "SELECT * FROM products WHERE a = ? AND b = ?"
pg_query = convert_sqlite_to_postgresql(sqlite_query)
# Result: "SELECT * FROM products WHERE a = $1 AND b = $2"

# Convert PostgreSQL query to SQLite
pg_query = "SELECT * FROM t WHERE x = $1"
sqlite_query = convert_postgresql_to_sqlite(pg_query)
# Result: "SELECT * FROM t WHERE x = ?"
```

## DatabaseAdapter Interface

All adapters implement these async methods:

| Method                             | Description                                     |
| ---------------------------------- | ----------------------------------------------- |
| `connect()`                        | Initialize connection pool                      |
| `disconnect()`                     | Close all connections                           |
| `acquire()`                        | Context manager to acquire connection           |
| `execute(query, params)`           | Execute query, return cursor/status             |
| `fetch_one(query, params)`         | Execute query, return single row as dict        |
| `fetch_all(query, params)`         | Execute query, return all rows as list of dicts |
| `fetch_val(query, params)`         | Execute query, return single scalar value       |
| `execute_many(query, params_list)` | Execute query with multiple param sets          |
| `commit()`                         | Commit current transaction                      |
| `rollback()`                       | Rollback current transaction                    |

## PostgreSQL-Specific Features

The PostgreSQL adapter includes additional methods:

```python
# Bulk insert using COPY (much faster than INSERT)
await adapter.copy_records(
    "products",
    records=[(1, "a"), (2, "b")],
    columns=["id", "name"],
)

# INSERT ... RETURNING
qb = QueryBuilder(DatabaseBackend.POSTGRESQL)
query = qb.insert("products", ["name"], returning=["id"])
# Result: "INSERT INTO products (name) VALUES ($1) RETURNING id"
```

## Migration Path

### Step 1: Use the Abstraction Layer

Replace direct database calls with the adapter:

```python
# Before (direct aiosqlite)
async with aiosqlite.connect(db_path) as conn:
    cursor = await conn.execute("SELECT * FROM products")
    rows = await cursor.fetchall()

# After (using adapter)
adapter = create_adapter()
await adapter.connect()
rows = await adapter.fetch_all("SELECT * FROM products")
```

### Step 2: Use QueryBuilder for New Queries

Use `QueryBuilder` for all new queries to ensure compatibility:

```python
qb = QueryBuilder(adapter.backend)
query = qb.insert("products", ["name", "status"])
await adapter.execute(query, ("Product", "active"))
```

### Step 3: Switch Backend

When ready to migrate to PostgreSQL:

1. Set up PostgreSQL database with same schema
2. Migrate data using preferred tool (pg_dump, custom script, etc.)
3. Update environment variables:
   ```bash
   export DSA110_DB_BACKEND=postgresql
   export DSA110_DB_PG_HOST=your-pg-host
   export DSA110_DB_PG_DATABASE=dsa110
   export DSA110_DB_PG_USER=your-user
   export DSA110_DB_PG_PASSWORD=your-password
   ```
4. Restart application

## Testing

The package includes 58 unit tests covering:

- DatabaseConfig creation and environment loading
- SQLite adapter operations (CRUD, transactions)
- PostgreSQL adapter (mocked)
- QueryBuilder for both backends
- Query conversion utilities
- Integration tests with in-memory SQLite

Run tests:

```bash
pytest tests/unit/test_database_adapters.py -v
```

## Dependencies

- **SQLite**: `aiosqlite` (already installed)
- **PostgreSQL**: `asyncpg` (optional, install when needed)

Install PostgreSQL support:

```bash
pip install asyncpg
```

## Notes

1. **Placeholder Differences**: SQLite uses `?`, PostgreSQL uses `$1, $2, ...`

   - Use `QueryBuilder` to generate correct placeholders
   - Use `convert_*` functions for existing queries

2. **AUTOINCREMENT vs SERIAL**:

   - SQLite: `INTEGER PRIMARY KEY AUTOINCREMENT`
   - PostgreSQL: `SERIAL PRIMARY KEY`
   - Conversion functions handle this

3. **Connection Pooling**:

   - SQLite: Single connection (SQLite limitation)
   - PostgreSQL: asyncpg pool with configurable min/max

4. **Transactions**:
   - Both adapters support `commit()` and `rollback()`
   - Use `database.py` transaction context managers for atomic operations
