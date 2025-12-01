# Backend Architecture

## Overview

The DSA-110 Continuum Imaging Pipeline backend is a FastAPI-based REST API that
provides access to radio telescope data, pipeline job status, and analysis
results.

**Key Technologies:**

- **FastAPI** - Modern async Python web framework
- **aiosqlite** - Async SQLite database access
- **Pydantic** - Data validation and serialization
- **SQLAlchemy-style patterns** - Repository pattern for data access

---

## Package Structure

```
src/dsa110_contimg/api/
├── __init__.py
├── app.py                    # FastAPI application factory
├── config.py                 # Centralized configuration (TimeoutConfig, APIConfig)
├── database.py               # Database connection pooling
├── dependencies.py           # FastAPI dependency injection
├── exceptions.py             # Custom exception hierarchy
├── interfaces.py             # Repository Protocol interfaces
├── repositories.py           # Sync data access layer
├── async_repositories.py     # Async data access layer
├── schemas.py                # Pydantic request/response models
├── security.py               # Authentication/authorization
├── validation.py             # Input validation utilities
├── websocket.py              # WebSocket handlers
├── services_monitor.py       # External service health monitoring
├── job_queue.py              # Background job processing (RQ)
├── rate_limit.py             # Rate limiting configuration
├── metrics.py                # Prometheus metrics
├── cache.py                  # Redis cache integration
│
├── batch/                    # Batch job processing
│   ├── jobs.py               # Job creation and management
│   ├── qa.py                 # QA metric extraction
│   └── thumbnails.py         # Thumbnail generation
│
├── db_adapters/              # Multi-backend database support
│   ├── backend.py            # DatabaseAdapter Protocol
│   ├── query_builder.py      # Cross-database query utilities
│   └── adapters/
│       ├── sqlite_adapter.py
│       └── postgresql_adapter.py
│
├── middleware/               # HTTP middleware
│   └── exception_handler.py  # Global exception handling
│
├── routes/                   # API endpoint handlers
│   ├── images.py             # /api/v1/images/*
│   ├── sources.py            # /api/v1/sources/*
│   ├── jobs.py               # /api/v1/jobs/*
│   ├── ms.py                 # /api/v1/ms/*
│   ├── qa.py                 # /api/v1/qa/*
│   ├── cal.py                # /api/v1/cal/*
│   ├── stats.py              # /api/v1/stats/*
│   ├── logs.py               # /api/v1/logs/*
│   ├── queue.py              # /api/v1/queue/*
│   ├── cache.py              # /api/v1/cache/*
│   └── services.py           # /api/v1/services/*
│
└── services/                 # Business logic layer
    ├── async_services.py     # Async service implementations
    ├── fits_service.py       # FITS file parsing
    ├── qa_service.py         # QA calculations
    └── stats_service.py      # Statistics computation

src/dsa110_contimg/absurd/    # ABSURD Task Queue System
├── __init__.py               # Package exports
├── __main__.py               # Worker entry point
├── client.py                 # Database operations, task spawning
├── worker.py                 # Task execution loop
├── config.py                 # Environment configuration
├── adapter.py                # Pipeline task executors
├── dependencies.py           # DAG dependency management
├── scheduling.py             # Cron-like scheduling
├── monitoring.py             # Health checks and metrics
├── schema.sql                # PostgreSQL schema
├── setup.py                  # Database initialization
└── scheduler_main.py         # Scheduler daemon entry point
```

---

## Layered Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Routes Layer                      │
│   (routes/*.py - HTTP handlers, request/response mapping)   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Services Layer                            │
│   (services/*.py - Business logic, orchestration)           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Repositories Layer                          │
│   (async_repositories.py - Data access, aiosqlite)          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│               Database Abstraction Layer                     │
│   (db_adapters/ - SQLite/PostgreSQL adapters)               │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Design Patterns

### 1. Protocol-Based Interfaces

Repository interfaces use Python `Protocol` for structural subtyping:

```python
from typing import Protocol

class ImageRepositoryProtocol(Protocol):
    async def get_by_id(self, image_id: str) -> Optional[ImageRecord]: ...
    async def list_all(self, limit: int, offset: int) -> List[ImageRecord]: ...
```

This enables duck typing - any class implementing these methods is compatible.

### 2. Dependency Injection

FastAPI's `Depends()` provides clean dependency injection:

```python
from fastapi import Depends

async def get_async_image_service(
    repo: AsyncImageRepository = Depends(get_async_image_repository)
) -> AsyncImageService:
    return AsyncImageService(repo)

@router.get("/{image_id}")
async def get_image(
    image_id: str,
    service: AsyncImageService = Depends(get_async_image_service),
):
    return await service.get_image(image_id)
```

### 3. Custom Exception Hierarchy

All API errors extend `DSA110APIError` with consistent JSON responses:

```python
class DSA110APIError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def to_dict(self) -> dict:
        return {
            "error": self.error_code,
            "message": str(self),
            "details": self.details,
        }

# Specific exceptions
class RecordNotFoundError(DSA110APIError):
    status_code = 404
    error_code = "NOT_FOUND"

class ValidationError(DSA110APIError):
    status_code = 400
    error_code = "VALIDATION_ERROR"
```

### 4. Lazy Configuration Loading

Configuration is loaded lazily to respect environment variables in tests:

```python
def _get_default_db_path() -> str:
    """Get default database path (lazy-loaded)."""
    return str(get_config().database.products_path)
```

### 5. Centralized Timeout Configuration

All timeouts are configured in one place:

```python
@dataclass
class TimeoutConfig:
    db_connection: float = 30.0
    websocket_ping: float = 30.0
    health_check: float = 2.0
    redis_socket: float = 2.0
```

---

## Async Architecture

The API is fully async using:

- **aiosqlite** for non-blocking SQLite access
- **httpx** for async HTTP client requests
- **asyncio** for TCP/Redis health checks
- **RQ (Redis Queue)** for background job processing

### Benefits

1. **Non-blocking I/O** - Event loop handles concurrent requests efficiently
2. **Better tail latencies** - P99 reduced by 10-33%
3. **Resource efficiency** - Thousands of connections on single event loop
4. **WebSocket ready** - Native async WebSocket support

### Performance Characteristics

| Endpoint Type  | Throughput | Notes                           |
| -------------- | ---------- | ------------------------------- |
| CPU-bound      | +26%       | Health checks, pure computation |
| Database-heavy | -5-11%     | aiosqlite overhead (expected)   |
| P99 Latencies  | +10-33%    | More consistent under load      |

See [ASYNC_PERFORMANCE_REPORT.md](./ASYNC_PERFORMANCE_REPORT.md) for detailed
benchmarks.

---

## ABSURD Task Queue

ABSURD (Asynchronous Background Service for Unified Resource Distribution) is
the durable task queue for pipeline processing.

### Architecture

```
┌──────────────────┐     ┌────────────────────────┐     ┌──────────────────┐
│   API / Client   │────▶│   PostgreSQL (absurd)  │◀────│  AbsurdWorker    │
│  spawn_task()    │     │   - tasks table        │     │  claim_task()    │
└──────────────────┘     │   - SKIP LOCKED        │     │  execute()       │
                         └────────────────────────┘     │  complete/fail() │
                                                        └──────────────────┘
```

### Key Features

- **Durable persistence** - Tasks survive crashes in PostgreSQL
- **Atomic claims** - `FOR UPDATE SKIP LOCKED` ensures exactly-once
- **DAG dependencies** - Tasks can depend on parent completion
- **Dead letter queue** - Failed tasks moved to DLQ after retries
- **Cron scheduling** - Time-based task triggers

### Usage

```python
from dsa110_contimg.absurd import AbsurdClient

async def main():
    client = AbsurdClient.from_env()
    await client.connect()

    # Spawn task
    task_id = await client.spawn("convert_uvh5", {"ms_path": "/path/to.ms"})

    # Check status
    stats = await client.get_queue_stats("dsa110-pipeline")
    await client.close()
```

See [ABSURD README](../src/dsa110_contimg/absurd/README.md) and
[Activation Guide](./ops/absurd-service-activation.md) for full documentation.

---

## Database Layer

### Current: SQLite (aiosqlite)

```python
async with get_async_connection(db_path) as conn:
    cursor = await conn.execute("SELECT * FROM images WHERE id = ?", (id,))
    row = await cursor.fetchone()
```

### Future: PostgreSQL (asyncpg)

The `db_adapters/` package provides a unified interface:

```python
from dsa110_contimg.api.db_adapters import create_adapter

adapter = create_adapter()  # Uses DSA110_DB_BACKEND env var
await adapter.connect()
rows = await adapter.fetch_all("SELECT * FROM images")
```

See [database-adapters.md](./database-adapters.md) for full documentation.

---

## Error Handling

### Exception Middleware

All exceptions are caught and converted to consistent JSON responses:

```python
@app.exception_handler(RecordNotFoundError)
async def record_not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content=exc.to_dict(),
    )
```

### Narrow Exception Handling

Specific exception types are caught where possible:

```python
# Good: Specific exceptions
try:
    async with get_async_connection(db_path) as conn:
        cursor = await conn.execute(query)
except aiosqlite.OperationalError as e:
    raise DatabaseConnectionError(f"Database error: {e}")

# Avoid: Overly broad handlers
except Exception:
    pass  # Hides bugs!
```

---

## Testing

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (mocked dependencies)
│   ├── test_routes.py
│   ├── test_services.py
│   ├── test_repositories_orm.py
│   └── ...
├── integration/             # Integration tests (real database)
│   └── test_api.py
└── fixtures/                # Test data factories
    └── writers.py
```

### Running Tests

```bash
# All unit tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=src/dsa110_contimg/api --cov-report=term-missing

# Specific test file
pytest tests/unit/test_routes.py -v
```

### Current Coverage

- **782 tests passing**
- **72% coverage** on API package
- Key modules at 90%+ coverage

---

## Configuration

### Environment Variables

| Variable            | Default                                     | Description       |
| ------------------- | ------------------------------------------- | ----------------- |
| `DSA110_DB_BACKEND` | `sqlite`                                    | Database backend  |
| `PRODUCTS_DB_PATH`  | `/data/dsa110-contimg/.../products.sqlite3` | Products database |
| `REDIS_URL`         | `redis://localhost:6379/0`                  | Redis connection  |
| `DSA110_QUEUE_NAME` | `dsa110-pipeline`                           | RQ queue name     |
| `DSA110_LOG_LEVEL`  | `INFO`                                      | Logging level     |

### TimeoutConfig

```python
from dsa110_contimg.api.config import get_config

config = get_config()
timeout = config.timeouts.db_connection  # 30.0 seconds
```

---

## Security

- **IP-based access control** - Only private networks by default
- **Rate limiting** - Per-IP request limits via slowapi
- **CORS** - Configurable origins

See the [Security Guide](../../docs/reference/security.md) for details.
