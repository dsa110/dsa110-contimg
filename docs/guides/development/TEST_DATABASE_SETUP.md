# Test Database Configuration Guide

## Overview

This guide explains how to set up test database configuration for unit and
integration tests.

## Current Status

**Status**: ✅ Configured for Unit Tests

The test database configuration is **already implemented** for unit tests. Tests
use SQLite databases configured via environment variables in
`tests/unit/api/conftest.py`:

- `PIPELINE_QUEUE_DB`: `/tmp/test_state/ingest.sqlite3`
- `PIPELINE_PRODUCTS_DB`: `/tmp/test_state/products.sqlite3`
- `CAL_REGISTRY_DB`: `/tmp/test_state/cal_registry.sqlite3`

These databases are automatically created in `/tmp/test_state/` during test
execution.

## When Test Database Configuration is Needed

Test database configuration is needed when:

1. **Integration tests** require a real database connection
2. **Database schema tests** need to validate migrations
3. **Data persistence tests** need to verify CRUD operations
4. **Transaction tests** need to test rollback behavior

## Options for Test Database Setup

### Option 1: SQLite In-Memory Database (Recommended for Unit Tests)

```python
# tests/unit/conftest.py
import sqlite3
import pytest
from pathlib import Path

@pytest.fixture
def test_db(tmp_path):
    """Create an in-memory SQLite database for testing."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    yield conn
    conn.close()
    db_path.unlink(missing_ok=True)
```

### Option 2: PostgreSQL Test Database (For Integration Tests)

```python
# tests/integration/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session")
def test_db_engine():
    """Create a test database engine."""
    # Use a separate test database
    engine = create_engine("postgresql://user:pass@localhost/test_db")
    yield engine
    engine.dispose()

@pytest.fixture
def test_session(test_db_engine):
    """Create a test database session."""
    Session = sessionmaker(bind=test_db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()
```

### Option 3: Docker Test Database (For CI/CD)

```yaml
# .github/workflows/pr-checks.yml (add to jobs)
services:
  postgres:
    image: postgres:15
    env:
      POSTGRES_PASSWORD: test
      POSTGRES_DB: test_db
    options: >-
      --health-cmd pg_isready --health-interval 10s --health-timeout 5s
      --health-retries 5
```

## Implementation Steps

### 1. Determine Database Requirements

Check what database operations your tests need:

```bash
# Search for database usage in tests
grep -r "database\|db\.\|sqlite\|postgres" tests/ --include="*.py"
```

### 2. Choose Appropriate Strategy

- **Unit tests**: Use in-memory SQLite or mocks
- **Integration tests**: Use separate test database
- **CI/CD**: Use Docker services or test database

### 3. Create Database Fixtures

Add fixtures to appropriate conftest.py files:

```python
# tests/unit/conftest.py - for unit tests
@pytest.fixture
def mock_db():
    """Mock database for unit tests."""
    return MagicMock()

# tests/integration/conftest.py - for integration tests
@pytest.fixture
def test_database():
    """Real test database for integration tests."""
    # Implementation here
    pass
```

### 4. Configure Test Database URL

Set test database URL via environment variable:

```python
# tests/conftest.py
import os

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "sqlite:///:memory:"  # Default to in-memory
)
```

### 5. Add Database Cleanup

Ensure test database is cleaned up after tests:

```python
@pytest.fixture(autouse=True)
def cleanup_db(test_db):
    """Clean up database after each test."""
    yield
    # Cleanup code here
    test_db.execute("DELETE FROM test_table")
    test_db.commit()
```

## Example: SQLite Test Database Setup

Here's a complete example for SQLite:

```python
# tests/unit/conftest.py
import sqlite3
import pytest
from pathlib import Path
from datetime import datetime, timezone

@pytest.fixture
def test_db_path(tmp_path):
    """Return path to temporary test database."""
    return tmp_path / "test.db"

@pytest.fixture
def test_db(test_db_path):
    """Create and return a test database connection."""
    conn = sqlite3.connect(str(test_db_path))

    # Create test tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ingest_queue (
            group_id TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            received_at REAL NOT NULL,
            last_update REAL NOT NULL
        )
    """)

    conn.commit()
    yield conn
    conn.close()
    test_db_path.unlink(missing_ok=True)

@pytest.fixture
def sample_queue_data(test_db):
    """Insert sample data into test database."""
    now = datetime.now(tz=timezone.utc).timestamp()
    test_db.execute(
        "INSERT INTO ingest_queue VALUES (?, ?, ?, ?)",
        ("test-group-1", "pending", now, now)
    )
    test_db.commit()
    yield
    test_db.execute("DELETE FROM ingest_queue")
    test_db.commit()
```

## Integration with Alembic

If using Alembic for migrations:

```python
# tests/conftest.py
from alembic import command
from alembic.config import Config

@pytest.fixture(scope="session")
def migrated_db(test_db_engine):
    """Run migrations on test database."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.attributes["connection"] = test_db_engine.connect()
    command.upgrade(alembic_cfg, "head")
    yield
    command.downgrade(alembic_cfg, "base")
```

## Environment Variables

Set these environment variables for test database:

```bash
# .env.test
TEST_DATABASE_URL=sqlite:///./tests/test.db
TEST_DATABASE_CLEANUP=true
```

## Best Practices

1. **Isolate test data**: Each test should start with a clean database
2. **Use transactions**: Rollback after each test to avoid side effects
3. **Use fixtures**: Centralize database setup in conftest.py
4. **Separate test DB**: Never use production database for tests
5. **Clean up**: Always clean up test data after tests complete

## Related Documentation

- [Environment Setup](ENVIRONMENT_SETUP.md)
- [Testing Guide](../qa/PIPELINE_TESTING_GUIDE.md)
- [CI/CD Setup](CI_CD_SETUP.md)

## Next Steps

1. **Assess requirements**: Determine what database operations tests need
2. **Choose strategy**: Select appropriate database setup (SQLite, PostgreSQL,
   etc.)
3. **Implement fixtures**: Add database fixtures to conftest.py
4. **Update tests**: Modify tests to use database fixtures
5. **CI integration**: Add database services to CI workflows if needed
