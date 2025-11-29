# Database ORM Layer

The DSA-110 Continuum Imaging Pipeline uses SQLAlchemy 2.0 ORM for database
access, providing type-safe queries, better concurrency handling, and structured
schema management via Alembic migrations.

## Quick Start

```python
from dsa110_contimg.database import get_session, Image, MSIndex

# Query with context manager (auto-commit/rollback)
with get_session("products") as session:
    images = session.query(Image).filter_by(type="dirty").all()
    for img in images:
        print(f"{img.path}: {img.noise_jy} Jy/beam")
```

## Database Configuration

All databases use SQLite with:

- **WAL mode** - Concurrent read/write access
- **30 second timeout** - Handles lock contention gracefully
- **Foreign keys enabled** - Referential integrity

| Database        | Path                                               | Description            |
| --------------- | -------------------------------------------------- | ---------------------- |
| `products`      | `/data/dsa110-contimg/state/products.sqlite3`      | MS, images, photometry |
| `cal_registry`  | `/data/dsa110-contimg/state/cal_registry.sqlite3`  | Calibration tables     |
| `hdf5`          | `/data/dsa110-contimg/state/hdf5.sqlite3`          | HDF5 file index        |
| `ingest`        | `/data/dsa110-contimg/state/ingest.sqlite3`        | Streaming queue        |
| `data_registry` | `/data/dsa110-contimg/state/data_registry.sqlite3` | Data products          |

Paths can be overridden via environment variables (e.g.,
`PIPELINE_PRODUCTS_DB`).

## Session Management

### Basic Usage

```python
from dsa110_contimg.database.session import get_session

# Read-write session (default)
with get_session("products") as session:
    new_image = Image(path="/path/to/image.fits", ...)
    session.add(new_image)
    session.commit()

# Read-only session
with get_session("products", read_only=True) as session:
    images = session.query(Image).all()
```

### Multi-threaded Contexts (Streaming Converter)

For thread-safety, use scoped sessions:

```python
from dsa110_contimg.database.session import get_scoped_session

# Get a thread-local session factory
Session = get_scoped_session("products")

def worker_thread():
    session = Session()
    try:
        # Do work
        session.commit()
    finally:
        Session.remove()  # Clean up thread-local session
```

### Direct Engine Access

For table creation or direct SQL:

```python
from dsa110_contimg.database.session import get_engine
from dsa110_contimg.database.models import ProductsBase

engine = get_engine("products")
ProductsBase.metadata.create_all(engine)
```

## ORM Models

### Products Database

```python
from dsa110_contimg.database.models import (
    MSIndex,          # Measurement Set metadata
    Image,            # FITS image records
    Photometry,       # Source flux measurements
    TransientCandidate,  # Transient detections
    MonitoringSource, # Sources under monitoring
)

# Query MS by stage
with get_session("products") as session:
    pending = session.query(MSIndex).filter_by(stage="pending").all()

# Query images by type
with get_session("products") as session:
    dirty_images = session.query(Image).filter_by(type="dirty").all()
```

### Calibration Registry

```python
from dsa110_contimg.database.models import Caltable

# Find valid calibration table for a given MJD
with get_session("cal_registry") as session:
    valid_cals = session.query(Caltable).filter(
        Caltable.valid_from_mjd <= target_mjd,
        Caltable.valid_until_mjd >= target_mjd
    ).all()
```

### HDF5 File Index

```python
from dsa110_contimg.database.models import HDF5FileIndex

# Query by group ID
with get_session("hdf5") as session:
    files = session.query(HDF5FileIndex).filter_by(
        group_id="2025-01-15T12:30:00"
    ).all()
```

## Repositories

Repository classes provide high-level query methods:

```python
from dsa110_contimg.database.repositories import (
    ImageRepository,
    MSRepository,
    PhotometryRepository,
    CaltableRepository,
)

# List all dirty images
images = ImageRepository.list_all(session, type_filter="dirty")

# Get MS files at a specific stage
pending_ms = MSRepository.list_all(session, stage="pending")

# Get lightcurve for a source
lightcurve = PhotometryRepository.get_lightcurve(session, source_id="J1234+5678")

# Find valid calibration tables
caltables = CaltableRepository.find_valid_for_mjd(session, mjd=60000.5)
```

## Schema Migrations with Alembic

### Running Migrations

```bash
# Set database and run migrations
cd backend/src/dsa110_contimg
DATABASE=products alembic upgrade head

# Check current version
DATABASE=products alembic current

# Generate new migration from model changes
DATABASE=products alembic revision --autogenerate -m "Add new column"
```

### Creating Migrations

1. Modify ORM models in `database/models.py`
2. Generate migration:
   ```bash
   DATABASE=products alembic revision --autogenerate -m "Description"
   ```
3. Review generated migration in `migrations/versions/`
4. Apply migration:
   ```bash
   DATABASE=products alembic upgrade head
   ```

### Multi-Database Support

Set `DATABASE` environment variable to target different databases:

```bash
DATABASE=products alembic upgrade head
DATABASE=cal_registry alembic upgrade head
DATABASE=hdf5 alembic upgrade head
```

## Testing with In-Memory Databases

Unit tests use in-memory SQLite databases:

```python
from dsa110_contimg.database.session import get_engine, get_session
from dsa110_contimg.database.models import ProductsBase, Image

def test_image_creation():
    # Create in-memory engine
    engine = get_engine("products", in_memory=True)
    ProductsBase.metadata.create_all(engine)

    with get_session("products", in_memory=True) as session:
        image = Image(path="/test.fits", ms_path="/test.ms", ...)
        session.add(image)
        session.commit()

        result = session.query(Image).first()
        assert result.path == "/test.fits"
```

## Best Practices

1. **Always use context managers** for sessions to ensure proper cleanup
2. **Use scoped sessions** in multi-threaded code (streaming converter)
3. **Prefer repositories** for common query patterns
4. **Test with in-memory databases** to avoid touching production data
5. **Review autogenerated migrations** before applying - Alembic may detect
   false positives due to SQLite type affinity

## Module Structure

```
backend/src/dsa110_contimg/database/
├── __init__.py          # Public exports
├── models.py            # ORM model definitions
├── session.py           # Engine/session management
├── repositories.py      # Query repositories
└── migrations/
    ├── env.py           # Alembic configuration
    └── versions/        # Migration scripts
```
