# API Module

FastAPI-based REST API for the DSA-110 Continuum Imaging Pipeline.

## Quick Start

```bash
# Development server
python -m uvicorn dsa110_contimg.api.app:app --reload --port 8000

# View interactive docs
open http://localhost:8000/api/docs
```

## Architecture

```
Routes (routes/)      → Handle HTTP requests, validate input
    ↓
Services (services/)  → Business logic, orchestration
    ↓
Repositories          → Data access (async_repositories.py, repositories.py)
    ↓
Database Adapters     → SQLite or PostgreSQL (db_adapters/)
```

## Key Files

| File              | Purpose                                       |
| ----------------- | --------------------------------------------- |
| `app.py`          | FastAPI application factory, middleware setup |
| `routes/`         | Endpoint handlers organized by resource       |
| `schemas.py`      | Pydantic request/response models              |
| `repositories.py` | Sync data access layer                        |
| `interfaces.py`   | Repository Protocol definitions               |
| `query_batch.py`  | Batch query utilities for N+1 prevention      |
| `db_adapters/`    | Multi-database backend support                |
| `config.py`       | Centralized configuration                     |
| `security.py`     | IP-based access control                       |

## Endpoints

| Path               | Description                 |
| ------------------ | --------------------------- |
| `/api/v1/images/`  | Image products (FITS files) |
| `/api/v1/sources/` | Detected radio sources      |
| `/api/v1/ms/`      | Measurement Sets            |
| `/api/v1/jobs/`    | Pipeline job status         |
| `/api/v1/qa/`      | Quality assurance metrics   |
| `/api/v1/cal/`     | Calibration tables          |
| `/api/v1/stats/`   | Pipeline statistics         |

## Database Configuration

Set `DSA110_DB_BACKEND` environment variable:

- `sqlite` (default) - Single-file database
- `postgresql` - Production database with connection pooling

See `../docs/postgresql-deployment.md` for PostgreSQL setup.

## Adding a New Endpoint

1. Define Pydantic models in `schemas.py`
2. Create route handler in `routes/{resource}.py`
3. Add repository method if needed
4. Register router in `app.py`
5. Write tests in `tests/unit/api/`
