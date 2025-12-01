"""
SQLAlchemy database session management for DSA-110 Continuum Imaging Pipeline.

This module provides:
- Database engine factory with proper SQLite configuration (WAL mode, 30s timeout)
- Session factories for each database
- Scoped sessions for multi-threaded contexts (streaming converter)
- Context managers for safe session handling

Usage:
    # Simple session usage with context manager
    from dsa110_contimg.database.session import get_session
    
    with get_session("products") as session:
        images = session.query(Image).filter_by(type="dirty").all()
        session.add(new_image)
        session.commit()
    
    # Scoped sessions for multi-threaded contexts
    from dsa110_contimg.database.session import get_scoped_session
    
    Session = get_scoped_session("products")
    session = Session()
    try:
        # do work
        session.commit()
    finally:
        Session.remove()
    
    # Direct engine access for migrations
    from dsa110_contimg.database.session import get_engine
    
    engine = get_engine("products")
    Base.metadata.create_all(engine)

Configuration:
    Database paths are read from environment variables with fallbacks:
    - PIPELINE_PRODUCTS_DB -> /data/dsa110-contimg/state/products.sqlite3
    - PIPELINE_CAL_REGISTRY_DB -> /data/dsa110-contimg/state/cal_registry.sqlite3
    - PIPELINE_HDF5_DB -> /data/dsa110-contimg/state/hdf5.sqlite3
    - PIPELINE_INGEST_DB -> /data/dsa110-contimg/state/ingest.sqlite3
    - PIPELINE_DATA_REGISTRY_DB -> /data/dsa110-contimg/state/data_registry.sqlite3
"""

from __future__ import annotations

import os
import logging
from contextlib import contextmanager
from threading import RLock
from typing import Optional, Generator, Dict, Literal, TYPE_CHECKING

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.pool import StaticPool

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

logger = logging.getLogger(__name__)

# =============================================================================
# Database Path Configuration
# =============================================================================

# Default database paths (can be overridden via environment variables)
DEFAULT_DB_PATHS = {
    "products": "/data/dsa110-contimg/state/db/products.sqlite3",
    "cal_registry": "/data/dsa110-contimg/state/db/cal_registry.sqlite3",
    "hdf5": "/data/dsa110-contimg/state/db/hdf5.sqlite3",
    "ingest": "/data/dsa110-contimg/state/db/ingest.sqlite3",
    "data_registry": "/data/dsa110-contimg/state/db/data_registry.sqlite3",
    "docsearch": "/data/dsa110-contimg/state/docsearch.sqlite3",
    "embedding_cache": "/data/dsa110-contimg/state/embedding_cache.sqlite3",
}

# Alias for Alembic migrations
DATABASE_PATHS = DEFAULT_DB_PATHS

# Environment variable names for database paths
DB_ENV_VARS = {
    "products": "PIPELINE_PRODUCTS_DB",
    "cal_registry": "PIPELINE_CAL_REGISTRY_DB",
    "hdf5": "PIPELINE_HDF5_DB",
    "ingest": "PIPELINE_INGEST_DB",
    "data_registry": "PIPELINE_DATA_REGISTRY_DB",
    "docsearch": "PIPELINE_DOCSEARCH_DB",
    "embedding_cache": "PIPELINE_EMBEDDING_CACHE_DB",
}

# Database name type for type hints
DatabaseName = Literal[
    "products", "cal_registry", "hdf5", "ingest", 
    "data_registry", "docsearch", "embedding_cache"
]

# =============================================================================
# Engine and Session Caching
# =============================================================================

# Global caches for engines and session factories
_engines: Dict[str, Engine] = {}
_session_factories: Dict[str, sessionmaker] = {}
_scoped_sessions: Dict[str, scoped_session] = {}
_lock = RLock()  # Use RLock for reentrant locking (get_session_factory calls get_engine)

# SQLite connection settings
SQLITE_TIMEOUT = 30  # seconds
SQLITE_CHECK_SAME_THREAD = False  # Allow multi-threaded access


def get_db_path(db_name: DatabaseName) -> str:
    """
    Get the database file path for a named database.
    
    Checks environment variable first, then falls back to default path.
    
    Args:
        db_name: Name of the database ('products', 'cal_registry', etc.)
        
    Returns:
        Absolute path to the SQLite database file
        
    Raises:
        ValueError: If db_name is not recognized
    """
    if db_name not in DEFAULT_DB_PATHS:
        raise ValueError(
            f"Unknown database name: {db_name}. "
            f"Valid names: {list(DEFAULT_DB_PATHS.keys())}"
        )
    
    env_var = DB_ENV_VARS.get(db_name)
    if env_var:
        return os.environ.get(env_var, DEFAULT_DB_PATHS[db_name])
    return DEFAULT_DB_PATHS[db_name]


def get_db_url(db_name: DatabaseName, in_memory: bool = False) -> str:
    """
    Get SQLAlchemy database URL for a named database.
    
    Args:
        db_name: Name of the database
        in_memory: If True, use in-memory SQLite for testing
        
    Returns:
        SQLAlchemy connection URL
    """
    if in_memory:
        return "sqlite:///:memory:"
    
    db_path = get_db_path(db_name)
    return f"sqlite:///{db_path}"


def _setup_sqlite_wal_mode(dbapi_connection, connection_record):
    """
    Set up SQLite WAL mode and other pragmas on connection.
    
    This is called for every new connection to ensure proper configuration.
    """
    cursor = dbapi_connection.cursor()
    
    # Enable WAL mode for concurrent reads/writes
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # Enable foreign key constraints
    cursor.execute("PRAGMA foreign_keys=ON")
    
    # Synchronous mode NORMAL is faster while still safe with WAL
    cursor.execute("PRAGMA synchronous=NORMAL")
    
    # Increase cache size for better performance (64MB)
    cursor.execute("PRAGMA cache_size=-65536")
    
    # Memory-mapped I/O size (256MB)
    cursor.execute("PRAGMA mmap_size=268435456")
    
    cursor.close()


def get_engine(
    db_name: DatabaseName,
    in_memory: bool = False,
    echo: bool = False,
) -> Engine:
    """
    Get or create a SQLAlchemy engine for a database.
    
    Engines are cached and reused. Each engine is configured with:
    - WAL journal mode for concurrent access
    - 30 second timeout for lock contention
    - Foreign key enforcement
    - Optimized cache and mmap settings
    
    Args:
        db_name: Name of the database
        in_memory: If True, create an in-memory database (for testing)
        echo: If True, log all SQL statements
        
    Returns:
        SQLAlchemy Engine instance
        
    Example:
        engine = get_engine("products")
        Base.metadata.create_all(engine)
    """
    cache_key = f"{db_name}:{'memory' if in_memory else 'file'}"
    
    with _lock:
        if cache_key in _engines:
            return _engines[cache_key]
        
        db_url = get_db_url(db_name, in_memory=in_memory)
        
        # Configure engine
        if in_memory:
            # In-memory databases need special pooling to persist
            engine = create_engine(
                db_url,
                echo=echo,
                poolclass=StaticPool,
                connect_args={
                    "check_same_thread": SQLITE_CHECK_SAME_THREAD,
                },
            )
        else:
            engine = create_engine(
                db_url,
                echo=echo,
                connect_args={
                    "timeout": SQLITE_TIMEOUT,
                    "check_same_thread": SQLITE_CHECK_SAME_THREAD,
                },
                pool_pre_ping=True,  # Check connection health before use
            )
        
        # Set up WAL mode and other pragmas for new connections
        event.listen(engine, "connect", _setup_sqlite_wal_mode)
        
        _engines[cache_key] = engine
        logger.debug(f"Created engine for database '{db_name}' at {db_url}")
        
        return engine


def get_session_factory(
    db_name: DatabaseName,
    in_memory: bool = False,
) -> sessionmaker:
    """
    Get or create a session factory for a database.
    
    Session factories are cached and reused.
    
    Args:
        db_name: Name of the database
        in_memory: If True, use in-memory database
        
    Returns:
        SQLAlchemy sessionmaker instance
        
    Example:
        Session = get_session_factory("products")
        session = Session()
        try:
            # do work
            session.commit()
        finally:
            session.close()
    """
    cache_key = f"{db_name}:{'memory' if in_memory else 'file'}"
    
    with _lock:
        if cache_key in _session_factories:
            return _session_factories[cache_key]
        
        engine = get_engine(db_name, in_memory=in_memory)
        factory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=True,
            expire_on_commit=True,
        )
        
        _session_factories[cache_key] = factory
        return factory


def get_scoped_session(
    db_name: DatabaseName,
    in_memory: bool = False,
) -> scoped_session:
    """
    Get or create a thread-local scoped session for a database.
    
    Scoped sessions provide thread-safe session management, ideal for
    multi-threaded contexts like the streaming converter.
    
    Args:
        db_name: Name of the database
        in_memory: If True, use in-memory database
        
    Returns:
        SQLAlchemy scoped_session instance
        
    Example:
        Session = get_scoped_session("products")
        
        def worker_thread():
            session = Session()
            try:
                # do work
                session.commit()
            finally:
                Session.remove()  # Clean up thread-local session
    """
    cache_key = f"{db_name}:{'memory' if in_memory else 'file'}"
    
    with _lock:
        if cache_key in _scoped_sessions:
            return _scoped_sessions[cache_key]
        
        factory = get_session_factory(db_name, in_memory=in_memory)
        scoped = scoped_session(factory)
        
        _scoped_sessions[cache_key] = scoped
        return scoped


@contextmanager
def get_session(
    db_name: DatabaseName,
    in_memory: bool = False,
) -> Generator[Session, None, None]:
    """
    Context manager for safe session handling.
    
    Automatically commits on success and rolls back on exception.
    Session is closed after the context exits.
    
    Args:
        db_name: Name of the database
        in_memory: If True, use in-memory database
        
    Yields:
        SQLAlchemy Session instance
        
    Example:
        with get_session("products") as session:
            images = session.query(Image).filter_by(type="dirty").all()
            new_image = Image(path="/path/to/image.fits", ...)
            session.add(new_image)
            # Commits automatically on successful exit
    """
    factory = get_session_factory(db_name, in_memory=in_memory)
    session = factory()
    
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_readonly_session(
    db_name: DatabaseName,
    in_memory: bool = False,
) -> Generator[Session, None, None]:
    """
    Context manager for read-only session handling.
    
    Does not commit - use for queries only.
    
    Args:
        db_name: Name of the database
        in_memory: If True, use in-memory database
        
    Yields:
        SQLAlchemy Session instance
        
    Example:
        with get_readonly_session("products") as session:
            images = session.query(Image).all()
            # No commit needed, session closes cleanly
    """
    factory = get_session_factory(db_name, in_memory=in_memory)
    session = factory()
    
    try:
        yield session
    finally:
        session.close()


# =============================================================================
# Database Initialization
# =============================================================================

def init_database(
    db_name: DatabaseName,
    in_memory: bool = False,
) -> None:
    """
    Initialize database tables if they don't exist.
    
    Creates all tables defined in the appropriate Base for the database.
    Safe to call multiple times - existing tables are not modified.
    
    Args:
        db_name: Name of the database to initialize
        in_memory: If True, use in-memory database
        
    Example:
        init_database("products")  # Creates all products.sqlite3 tables
    """
    from .models import (
        ProductsBase, CalRegistryBase, HDF5Base,
        IngestBase, DataRegistryBase,
    )
    
    engine = get_engine(db_name, in_memory=in_memory)
    
    # Map database names to their declarative bases
    base_map = {
        "products": ProductsBase,
        "cal_registry": CalRegistryBase,
        "hdf5": HDF5Base,
        "ingest": IngestBase,
        "data_registry": DataRegistryBase,
    }
    
    base = base_map.get(db_name)
    if base:
        base.metadata.create_all(engine)
        logger.info(f"Initialized database: {db_name}")
    else:
        logger.warning(f"No model base defined for database: {db_name}")


def reset_engines() -> None:
    """
    Reset all cached engines and session factories.
    
    Useful for testing or when database files are replaced.
    """
    global _engines, _session_factories, _scoped_sessions
    
    with _lock:
        # Dispose all engines
        for engine in _engines.values():
            engine.dispose()
        
        # Remove scoped sessions
        for scoped in _scoped_sessions.values():
            scoped.remove()
        
        _engines.clear()
        _session_factories.clear()
        _scoped_sessions.clear()
        
    logger.debug("Reset all database engines and session factories")


# =============================================================================
# Compatibility layer for gradual migration
# =============================================================================

def get_raw_connection(db_name: DatabaseName) -> "Connection":
    """
    Get a raw SQLAlchemy connection for legacy code migration.
    
    This provides a connection that can be used with raw SQL while
    still benefiting from proper connection management.
    
    Args:
        db_name: Name of the database
        
    Returns:
        SQLAlchemy Connection object
        
    Example:
        # For gradual migration of raw SQL code
        conn = get_raw_connection("products")
        result = conn.execute(text("SELECT * FROM images LIMIT 10"))
        rows = result.fetchall()
        conn.close()
    """
    engine = get_engine(db_name)
    return engine.connect()
