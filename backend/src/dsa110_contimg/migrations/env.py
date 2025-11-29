"""
Alembic Environment Configuration for DSA-110 Continuum Imaging Pipeline.

This module configures Alembic to work with our multi-database SQLite setup.
Each database (products, cal_registry, hdf5, ingest, data_registry) has its
own schema and migrations should be run per-database.

Usage:
    # Set DATABASE env var to specify which database to migrate
    DATABASE=products alembic upgrade head
    DATABASE=cal_registry alembic upgrade head
    
    # Or use the CLI wrapper
    python -m dsa110_contimg.database.migrations --database products upgrade head
"""
import os
from logging.config import fileConfig

from sqlalchemy import pool, create_engine, text

from alembic import context

from dsa110_contimg.database.models import (
    ProductsBase,
    CalRegistryBase,
    HDF5Base,
    IngestBase,
    DataRegistryBase,
)
from dsa110_contimg.database.session import DATABASE_PATHS

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Database name to metadata mapping
DATABASE_METADATA = {
    "products": ProductsBase.metadata,
    "cal_registry": CalRegistryBase.metadata,
    "hdf5": HDF5Base.metadata,
    "ingest": IngestBase.metadata,
    "data_registry": DataRegistryBase.metadata,
}

# Get the database name from environment or command line
database_name = os.environ.get("DATABASE", "products")

if database_name not in DATABASE_METADATA:
    raise ValueError(
        f"Unknown database: {database_name}. "
        f"Valid options: {list(DATABASE_METADATA.keys())}"
    )

target_metadata = DATABASE_METADATA[database_name]


def get_url() -> str:
    """Get the database URL for the current database."""
    # Get path from our database paths
    if database_name in DATABASE_PATHS:
        db_path = DATABASE_PATHS[database_name]
    else:
        # For custom paths, use environment variable
        db_path = os.environ.get("DATABASE_PATH", f"/data/dsa110-contimg/state/{database_name}.sqlite3")
    
    return f"sqlite:///{db_path}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    which is useful for generating SQL scripts without connecting
    to the database.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,  # SQLite needs batch mode for ALTER TABLE
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an Engine and associates it with the context.
    Uses SQLite-specific settings for safety.
    """
    connectable = create_engine(
        get_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Enable foreign keys for SQLite
        connection.execute(text("PRAGMA foreign_keys=ON"))
        
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite needs batch mode for ALTER TABLE
            compare_type=True,  # Detect column type changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
