# Database Abstraction Layer

## Overview

The `db_adapters` package provides a unified async interface for database
operations using SQLite. This provides a clean abstraction for database access
with consistent patterns across the codebase.

> **Note:** PostgreSQL support was removed in the complexity reduction refactor.
> The pipeline exclusively uses SQLite for data storage. The ABSURD workflow
> manager uses its own separate PostgreSQL database.

## Package Structure

```
src/dsa110_contimg/api/db_adapters/
├── __init__.py              # Public API exports
├── backend.py               # DatabaseAdapter ABC, DatabaseConfig, factory
├── query_builder.py         # Query building utilities
└── adapters/
    ├── __init__.py
    └── sqlite_adapter.py    # SQLite implementation (aiosqlite)
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
from dsa110_contimg.api.db_adapters import create_adapter, DatabaseConfig

config = DatabaseConfig(
    sqlite_path="/path/to/database.db",
    sqlite_timeout=30.0,
)

adapter = create_adapter(config)
await adapter.connect()
```

## Environment Variables

Configure the database via environment variables:

| Variable                   | Default                               | Description               |
| -------------------------- | ------------------------------------- | ------------------------- |
| `DSA110_DB_SQLITE_PATH`    | `/data/.../state/db/products.sqlite3` | Path to SQLite database   |
| `DSA110_DB_SQLITE_TIMEOUT` | `30.0`                                | SQLite connection timeout |

Alternative legacy variable:

- `PIPELINE_PRODUCTS_DB` - Also recognized for backward compatibility

## Query Builder

The `QueryBuilder` class generates SQL queries:

```python
from dsa110_contimg.api.db_adapters import QueryBuilder

qb = QueryBuilder()

# Build queries
select = qb.select("products", columns=["id", "name"], where="status = ?")
insert = qb.insert("products", columns=["name", "status"])
update = qb.update("products", columns=["name"], where="id = ?")
delete = qb.delete("products", where="id = ?")
upsert = qb.upsert("products", columns=["id", "name"], conflict_columns=["id"])

# Generate placeholders
qb.placeholders(3)  # "?, ?, ?"
```

## DatabaseAdapter Interface

The adapter implements these async methods:

| Method                             | Description                                     |
| ---------------------------------- | ----------------------------------------------- |
| `connect()`                        | Initialize connection                           |
| `disconnect()`                     | Close connection                                |
| `acquire()`                        | Context manager to acquire connection           |
| `execute(query, params)`           | Execute query, return cursor                    |
| `fetch_one(query, params)`         | Execute query, return single row as dict        |
| `fetch_all(query, params)`         | Execute query, return all rows as list of dicts |
| `fetch_val(query, params)`         | Execute query, return single scalar value       |
| `execute_many(query, params_list)` | Execute query with multiple param sets          |
| `commit()`                         | Commit current transaction                      |
| `rollback()`                       | Rollback current transaction                    |

## Usage Example

```python
from dsa110_contimg.api.db_adapters import create_adapter, QueryBuilder

async def main():
    adapter = create_adapter()
    await adapter.connect()

    qb = QueryBuilder()

    # Insert
    insert_sql = qb.insert("products", ["name", "status"])
    await adapter.execute(insert_sql, ("My Product", "active"))
    await adapter.commit()

    # Select
    rows = await adapter.fetch_all("SELECT * FROM products WHERE status = ?", ("active",))
    for row in rows:
        print(row["name"])

    await adapter.disconnect()
```

## Testing

Run database adapter tests:

```bash
pytest tests/unit/test_database_adapters.py -v
```

## Dependencies

- **SQLite**: `aiosqlite` (included in requirements)

## Notes

1. **Placeholder Style**: SQLite uses `?` placeholders
2. **Connection**: Single connection per adapter (SQLite limitation)
3. **Transactions**: Use `commit()` and `rollback()` for transaction control
4. **WAL Mode**: Recommended for concurrent read access
