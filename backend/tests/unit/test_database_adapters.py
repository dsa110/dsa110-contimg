"""
Tests for database abstraction layer.

These tests verify the database adapters work correctly
for both SQLite and PostgreSQL backends.
"""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from dsa110_contimg.api.db_adapters import (
    create_adapter,
    DatabaseAdapter,
    DatabaseBackend,
    DatabaseConfig,
    QueryBuilder,
    convert_sqlite_to_postgresql,
    convert_postgresql_to_sqlite,
)
from dsa110_contimg.api.db_adapters.adapters.sqlite_adapter import SQLiteAdapter


# =============================================================================
# DatabaseConfig Tests
# =============================================================================


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = DatabaseConfig()
        assert config.backend == DatabaseBackend.SQLITE
        assert config.sqlite_timeout == 30.0
        assert config.pg_host == "localhost"
        assert config.pg_port == 5432
        assert config.pg_pool_min == 1
        assert config.pg_pool_max == 10
        assert config.pg_ssl is False
    
    def test_sqlite_connection_string(self):
        """Test SQLite connection string generation."""
        config = DatabaseConfig(
            backend=DatabaseBackend.SQLITE,
            sqlite_path="/tmp/test.db",
        )
        assert config.connection_string == "sqlite:////tmp/test.db"
    
    def test_postgresql_connection_string(self):
        """Test PostgreSQL connection string generation."""
        config = DatabaseConfig(
            backend=DatabaseBackend.POSTGRESQL,
            pg_host="dbserver",
            pg_port=5433,
            pg_database="testdb",
            pg_user="testuser",
            pg_password="testpass",
        )
        expected = "postgresql://testuser:testpass@dbserver:5433/testdb"
        assert config.connection_string == expected
    
    def test_postgresql_connection_string_with_ssl(self):
        """Test PostgreSQL connection string with SSL."""
        config = DatabaseConfig(
            backend=DatabaseBackend.POSTGRESQL,
            pg_host="secure.db",
            pg_database="proddb",
            pg_user="admin",
            pg_password="secret",
            pg_ssl=True,
        )
        assert "?sslmode=require" in config.connection_string
    
    def test_from_env_sqlite(self):
        """Test loading SQLite config from environment."""
        with patch.dict(os.environ, {
            "TEST_DB_BACKEND": "sqlite",
            "TEST_DB_SQLITE_PATH": "/data/test.db",
            "TEST_DB_SQLITE_TIMEOUT": "60.0",
        }):
            config = DatabaseConfig.from_env(prefix="TEST_DB")
            assert config.backend == DatabaseBackend.SQLITE
            assert config.sqlite_path == "/data/test.db"
            assert config.sqlite_timeout == 60.0
    
    def test_from_env_postgresql(self):
        """Test loading PostgreSQL config from environment."""
        with patch.dict(os.environ, {
            "TEST_DB_BACKEND": "postgresql",
            "TEST_DB_PG_HOST": "pg.example.com",
            "TEST_DB_PG_PORT": "5433",
            "TEST_DB_PG_DATABASE": "mydb",
            "TEST_DB_PG_USER": "dbuser",
            "TEST_DB_PG_PASSWORD": "dbpass",
            "TEST_DB_PG_POOL_MIN": "2",
            "TEST_DB_PG_POOL_MAX": "20",
            "TEST_DB_PG_SSL": "true",
        }):
            config = DatabaseConfig.from_env(prefix="TEST_DB")
            assert config.backend == DatabaseBackend.POSTGRESQL
            assert config.pg_host == "pg.example.com"
            assert config.pg_port == 5433
            assert config.pg_database == "mydb"
            assert config.pg_user == "dbuser"
            assert config.pg_password == "dbpass"
            assert config.pg_pool_min == 2
            assert config.pg_pool_max == 20
            assert config.pg_ssl is True


# =============================================================================
# SQLiteAdapter Tests
# =============================================================================


class TestSQLiteAdapter:
    """Tests for SQLiteAdapter."""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            yield f.name
        os.unlink(f.name)
    
    @pytest.fixture
    def config(self, temp_db):
        """Create SQLite config with temp database."""
        return DatabaseConfig(
            backend=DatabaseBackend.SQLITE,
            sqlite_path=temp_db,
        )
    
    @pytest_asyncio.fixture
    async def adapter(self, temp_db):
        """Create and connect SQLite adapter."""
        config = DatabaseConfig(
            backend=DatabaseBackend.SQLITE,
            sqlite_path=temp_db,
        )
        adapter = SQLiteAdapter(config)
        await adapter.connect()
        yield adapter
        await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self, config):
        """Test connection lifecycle."""
        adapter = SQLiteAdapter(config)
        assert adapter._connection is None
        
        await adapter.connect()
        assert adapter._connection is not None
        
        await adapter.disconnect()
        assert adapter._connection is None
    
    @pytest.mark.asyncio
    async def test_placeholder(self, adapter):
        """Test SQLite uses ? placeholder."""
        assert adapter.placeholder == "?"
    
    @pytest.mark.asyncio
    async def test_backend_property(self, adapter):
        """Test backend property returns SQLite."""
        assert adapter.backend == DatabaseBackend.SQLITE
    
    @pytest.mark.asyncio
    async def test_execute_create_table(self, adapter):
        """Test executing DDL statements."""
        await adapter.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            )
        """)
        # Verify table exists
        result = await adapter.fetch_val(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        )
        assert result == "test_table"
    
    @pytest.mark.asyncio
    async def test_execute_with_params(self, adapter):
        """Test executing with parameters."""
        await adapter.execute(
            "CREATE TABLE params_test (id INTEGER, value TEXT)"
        )
        await adapter.execute(
            "INSERT INTO params_test VALUES (?, ?)",
            (1, "hello"),
        )
        await adapter.commit()
        
        result = await adapter.fetch_one(
            "SELECT * FROM params_test WHERE id = ?",
            (1,),
        )
        assert result["id"] == 1
        assert result["value"] == "hello"
    
    @pytest.mark.asyncio
    async def test_fetch_one_returns_dict(self, adapter):
        """Test fetch_one returns dict-like result."""
        await adapter.execute(
            "CREATE TABLE dict_test (a INTEGER, b TEXT, c REAL)"
        )
        await adapter.execute(
            "INSERT INTO dict_test VALUES (?, ?, ?)",
            (42, "test", 3.14),
        )
        await adapter.commit()
        
        row = await adapter.fetch_one("SELECT * FROM dict_test")
        assert isinstance(row, dict)
        assert row["a"] == 42
        assert row["b"] == "test"
        assert row["c"] == 3.14
    
    @pytest.mark.asyncio
    async def test_fetch_one_no_results(self, adapter):
        """Test fetch_one returns None when no results."""
        await adapter.execute("CREATE TABLE empty_test (id INTEGER)")
        result = await adapter.fetch_one("SELECT * FROM empty_test")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_all_returns_list(self, adapter):
        """Test fetch_all returns list of dicts."""
        await adapter.execute(
            "CREATE TABLE list_test (id INTEGER, name TEXT)"
        )
        for i in range(5):
            await adapter.execute(
                "INSERT INTO list_test VALUES (?, ?)",
                (i, f"item_{i}"),
            )
        await adapter.commit()
        
        rows = await adapter.fetch_all("SELECT * FROM list_test ORDER BY id")
        assert len(rows) == 5
        assert all(isinstance(r, dict) for r in rows)
        assert [r["name"] for r in rows] == [f"item_{i}" for i in range(5)]
    
    @pytest.mark.asyncio
    async def test_fetch_all_empty(self, adapter):
        """Test fetch_all returns empty list when no results."""
        await adapter.execute("CREATE TABLE empty_list (id INTEGER)")
        rows = await adapter.fetch_all("SELECT * FROM empty_list")
        assert rows == []
    
    @pytest.mark.asyncio
    async def test_fetch_val_returns_scalar(self, adapter):
        """Test fetch_val returns single value."""
        await adapter.execute(
            "CREATE TABLE scalar_test (count INTEGER)"
        )
        await adapter.execute("INSERT INTO scalar_test VALUES (100)")
        await adapter.commit()
        
        result = await adapter.fetch_val("SELECT count FROM scalar_test")
        assert result == 100
    
    @pytest.mark.asyncio
    async def test_fetch_val_count(self, adapter):
        """Test fetch_val with COUNT aggregate."""
        await adapter.execute("CREATE TABLE count_test (id INTEGER)")
        for i in range(10):
            await adapter.execute(f"INSERT INTO count_test VALUES ({i})")
        await adapter.commit()
        
        count = await adapter.fetch_val("SELECT COUNT(*) FROM count_test")
        assert count == 10
    
    @pytest.mark.asyncio
    async def test_execute_many(self, adapter):
        """Test bulk insert with execute_many."""
        await adapter.execute(
            "CREATE TABLE bulk_test (id INTEGER, value TEXT)"
        )
        
        params = [(i, f"value_{i}") for i in range(100)]
        await adapter.execute_many(
            "INSERT INTO bulk_test VALUES (?, ?)",
            params,
        )
        
        count = await adapter.fetch_val("SELECT COUNT(*) FROM bulk_test")
        assert count == 100
    
    @pytest.mark.asyncio
    async def test_commit_and_rollback(self, adapter):
        """Test transaction commit and rollback."""
        await adapter.execute(
            "CREATE TABLE txn_test (id INTEGER)"
        )
        await adapter.commit()
        
        # Insert and rollback
        await adapter.execute("INSERT INTO txn_test VALUES (1)")
        await adapter.rollback()
        
        count = await adapter.fetch_val("SELECT COUNT(*) FROM txn_test")
        assert count == 0
        
        # Insert and commit
        await adapter.execute("INSERT INTO txn_test VALUES (2)")
        await adapter.commit()
        
        count = await adapter.fetch_val("SELECT COUNT(*) FROM txn_test")
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_acquire_reconnects_on_error(self, adapter):
        """Test acquire reconnects if connection lost."""
        # Close the underlying connection
        await adapter._connection.close()
        
        # acquire should reconnect
        async with adapter.acquire() as conn:
            result = await conn.execute("SELECT 1")
            row = await result.fetchone()
            assert row[0] == 1


# =============================================================================
# PostgreSQL Adapter Tests (Mocked)
# =============================================================================


class TestPostgreSQLAdapterMocked:
    """Tests for PostgreSQLAdapter using mocks.
    
    These tests verify the adapter behavior without requiring
    an actual PostgreSQL server.
    """
    
    @pytest.fixture
    def config(self):
        """Create PostgreSQL config."""
        return DatabaseConfig(
            backend=DatabaseBackend.POSTGRESQL,
            pg_host="localhost",
            pg_database="testdb",
            pg_user="testuser",
            pg_password="testpass",
        )
    
    @pytest.mark.asyncio
    async def test_postgresql_adapter_requires_asyncpg(self, config):
        """Test adapter raises ImportError if asyncpg not available."""
        with patch.dict("sys.modules", {"asyncpg": None}):
            # Re-import to trigger check
            import importlib
            from dsa110_contimg.api.db_adapters.adapters import postgresql_adapter
            
            # Temporarily set ASYNCPG_AVAILABLE to False
            original = postgresql_adapter.ASYNCPG_AVAILABLE
            postgresql_adapter.ASYNCPG_AVAILABLE = False
            
            try:
                with pytest.raises(ImportError, match="asyncpg is required"):
                    postgresql_adapter.PostgreSQLAdapter(config)
            finally:
                postgresql_adapter.ASYNCPG_AVAILABLE = original


# =============================================================================
# Factory Function Tests
# =============================================================================


class TestCreateAdapter:
    """Tests for create_adapter factory function."""
    
    def test_create_sqlite_adapter(self):
        """Test creating SQLite adapter."""
        config = DatabaseConfig(
            backend=DatabaseBackend.SQLITE,
            sqlite_path="/tmp/test.db",
        )
        adapter = create_adapter(config)
        assert isinstance(adapter, SQLiteAdapter)
        assert adapter.config == config
    
    def test_create_adapter_from_env(self):
        """Test creating adapter from environment variables."""
        with patch.dict(os.environ, {
            "DSA110_DB_BACKEND": "sqlite",
            "DSA110_DB_SQLITE_PATH": "/tmp/env_test.db",
        }):
            adapter = create_adapter()
            assert isinstance(adapter, SQLiteAdapter)
            assert adapter.config.sqlite_path == "/tmp/env_test.db"
    
    def test_create_postgresql_adapter(self):
        """Test creating PostgreSQL adapter (if asyncpg available)."""
        try:
            import asyncpg
        except ImportError:
            pytest.skip("asyncpg not installed")
        
        config = DatabaseConfig(
            backend=DatabaseBackend.POSTGRESQL,
            pg_host="localhost",
            pg_database="testdb",
        )
        adapter = create_adapter(config)
        from dsa110_contimg.api.db_adapters.adapters.postgresql_adapter import PostgreSQLAdapter
        assert isinstance(adapter, PostgreSQLAdapter)


# =============================================================================
# Placeholder Conversion Tests
# =============================================================================


class TestPlaceholderConversion:
    """Tests for SQLite to PostgreSQL placeholder conversion."""
    
    def test_convert_single_placeholder(self):
        """Test converting single ? to $1."""
        from dsa110_contimg.api.db_adapters.adapters.postgresql_adapter import convert_placeholders
        
        result = convert_placeholders("SELECT * FROM t WHERE id = ?")
        assert result == "SELECT * FROM t WHERE id = $1"
    
    def test_convert_multiple_placeholders(self):
        """Test converting multiple ? to $1, $2, etc."""
        from dsa110_contimg.api.db_adapters.adapters.postgresql_adapter import convert_placeholders
        
        result = convert_placeholders(
            "INSERT INTO t (a, b, c) VALUES (?, ?, ?)"
        )
        assert result == "INSERT INTO t (a, b, c) VALUES ($1, $2, $3)"
    
    def test_convert_no_placeholders(self):
        """Test query with no placeholders unchanged."""
        from dsa110_contimg.api.db_adapters.adapters.postgresql_adapter import convert_placeholders
        
        query = "SELECT * FROM products"
        result = convert_placeholders(query)
        assert result == query
    
    def test_convert_complex_query(self):
        """Test converting complex query with multiple placeholders."""
        from dsa110_contimg.api.db_adapters.adapters.postgresql_adapter import convert_placeholders
        
        query = """
            SELECT p.*, c.name as category
            FROM products p
            JOIN categories c ON p.category_id = c.id
            WHERE p.status = ? AND p.price > ?
            ORDER BY p.created_at DESC
            LIMIT ?
        """
        result = convert_placeholders(query)
        assert "$1" in result
        assert "$2" in result
        assert "$3" in result
        assert "?" not in result


# =============================================================================
# Integration Tests (SQLite only, no external dependencies)
# =============================================================================


class TestDatabaseIntegration:
    """Integration tests using SQLite adapter."""
    
    @pytest_asyncio.fixture
    async def db(self):
        """Create in-memory SQLite database."""
        config = DatabaseConfig(
            backend=DatabaseBackend.SQLITE,
            sqlite_path=":memory:",
        )
        adapter = SQLiteAdapter(config)
        await adapter.connect()
        
        # Create test schema
        await adapter.execute("""
            CREATE TABLE products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await adapter.commit()
        
        yield adapter
        await adapter.disconnect()
    
    @pytest.mark.asyncio
    async def test_crud_operations(self, db):
        """Test create, read, update, delete operations."""
        # Create
        await db.execute(
            "INSERT INTO products (name, status) VALUES (?, ?)",
            ("Test Product", "active"),
        )
        await db.commit()
        
        # Read
        product = await db.fetch_one(
            "SELECT * FROM products WHERE name = ?",
            ("Test Product",),
        )
        assert product is not None
        assert product["name"] == "Test Product"
        assert product["status"] == "active"
        product_id = product["id"]
        
        # Update
        await db.execute(
            "UPDATE products SET status = ? WHERE id = ?",
            ("completed", product_id),
        )
        await db.commit()
        
        updated = await db.fetch_one(
            "SELECT status FROM products WHERE id = ?",
            (product_id,),
        )
        assert updated["status"] == "completed"
        
        # Delete
        await db.execute(
            "DELETE FROM products WHERE id = ?",
            (product_id,),
        )
        await db.commit()
        
        deleted = await db.fetch_one(
            "SELECT * FROM products WHERE id = ?",
            (product_id,),
        )
        assert deleted is None
    
    @pytest.mark.asyncio
    async def test_batch_insert_and_query(self, db):
        """Test inserting multiple records and querying."""
        # Batch insert
        products = [(f"Product {i}", "active") for i in range(50)]
        await db.execute_many(
            "INSERT INTO products (name, status) VALUES (?, ?)",
            products,
        )
        
        # Verify count
        count = await db.fetch_val("SELECT COUNT(*) FROM products")
        assert count == 50
        
        # Verify all returned
        all_products = await db.fetch_all("SELECT * FROM products")
        assert len(all_products) == 50
    
    @pytest.mark.asyncio
    async def test_transaction_isolation(self, db):
        """Test transaction isolation."""
        # Start with clean state
        count_before = await db.fetch_val("SELECT COUNT(*) FROM products")
        assert count_before == 0
        
        # Insert but don't commit
        await db.execute(
            "INSERT INTO products (name) VALUES (?)",
            ("Uncommitted",),
        )
        
        # Rollback
        await db.rollback()
        
        # Verify not persisted
        count_after = await db.fetch_val("SELECT COUNT(*) FROM products")
        assert count_after == 0


# =============================================================================
# QueryBuilder Tests
# =============================================================================


class TestQueryBuilderSQLite:
    """Tests for QueryBuilder with SQLite backend."""
    
    @pytest.fixture
    def qb(self):
        """Create SQLite query builder."""
        return QueryBuilder(DatabaseBackend.SQLITE)
    
    def test_placeholder_sqlite(self, qb):
        """Test SQLite placeholder is ?."""
        assert qb.placeholder(1) == "?"
        assert qb.placeholder(5) == "?"
    
    def test_placeholders_multiple(self, qb):
        """Test multiple placeholders."""
        assert qb.placeholders(3) == "?, ?, ?"
        assert qb.placeholders(1) == "?"
    
    def test_select_all(self, qb):
        """Test basic SELECT *."""
        query = qb.select("products")
        assert query == "SELECT * FROM products"
    
    def test_select_columns(self, qb):
        """Test SELECT with specific columns."""
        query = qb.select("products", columns=["id", "name", "status"])
        assert query == "SELECT id, name, status FROM products"
    
    def test_select_with_where(self, qb):
        """Test SELECT with WHERE clause."""
        query = qb.select("products", where="status = ?")
        assert query == "SELECT * FROM products WHERE status = ?"
    
    def test_select_with_order_by(self, qb):
        """Test SELECT with ORDER BY."""
        query = qb.select("products", order_by="created_at DESC")
        assert query == "SELECT * FROM products ORDER BY created_at DESC"
    
    def test_select_with_limit_offset(self, qb):
        """Test SELECT with LIMIT and OFFSET."""
        query = qb.select("products", limit=10, offset=20)
        assert query == "SELECT * FROM products LIMIT 10 OFFSET 20"
    
    def test_select_full(self, qb):
        """Test SELECT with all options."""
        query = qb.select(
            "products",
            columns=["id", "name"],
            where="status = ?",
            order_by="name ASC",
            limit=50,
            offset=0,
        )
        expected = (
            "SELECT id, name FROM products "
            "WHERE status = ? ORDER BY name ASC LIMIT 50 OFFSET 0"
        )
        assert query == expected
    
    def test_insert(self, qb):
        """Test INSERT query."""
        query = qb.insert("products", columns=["name", "status"])
        assert query == "INSERT INTO products (name, status) VALUES (?, ?)"
    
    def test_insert_returning_ignored_sqlite(self, qb):
        """Test RETURNING is ignored for SQLite."""
        query = qb.insert(
            "products",
            columns=["name"],
            returning=["id"],
        )
        assert "RETURNING" not in query
        assert query == "INSERT INTO products (name) VALUES (?)"
    
    def test_update(self, qb):
        """Test UPDATE query."""
        query = qb.update(
            "products",
            columns=["name", "status"],
            where="id = ?",
        )
        assert query == "UPDATE products SET name = ?, status = ? WHERE id = ?"
    
    def test_delete(self, qb):
        """Test DELETE query."""
        query = qb.delete("products", where="id = ?")
        assert query == "DELETE FROM products WHERE id = ?"
    
    def test_upsert(self, qb):
        """Test UPSERT query."""
        query = qb.upsert(
            "products",
            columns=["id", "name", "status"],
            conflict_columns=["id"],
        )
        expected = (
            "INSERT INTO products (id, name, status) VALUES (?, ?, ?) "
            "ON CONFLICT (id) DO UPDATE SET name = excluded.name, status = excluded.status"
        )
        assert query == expected
    
    def test_upsert_do_nothing(self, qb):
        """Test UPSERT with DO NOTHING."""
        query = qb.upsert(
            "products",
            columns=["id"],
            conflict_columns=["id"],
            update_columns=[],
        )
        assert "DO NOTHING" in query
    
    def test_count(self, qb):
        """Test COUNT query."""
        query = qb.count("products")
        assert query == "SELECT COUNT(*) FROM products"
    
    def test_count_with_where(self, qb):
        """Test COUNT with WHERE."""
        query = qb.count("products", where="status = ?")
        assert query == "SELECT COUNT(*) FROM products WHERE status = ?"
    
    def test_exists(self, qb):
        """Test EXISTS query."""
        query = qb.exists("products", where="id = ?")
        assert query == "SELECT EXISTS(SELECT 1 FROM products WHERE id = ?)"


class TestQueryBuilderPostgreSQL:
    """Tests for QueryBuilder with PostgreSQL backend."""
    
    @pytest.fixture
    def qb(self):
        """Create PostgreSQL query builder."""
        return QueryBuilder(DatabaseBackend.POSTGRESQL)
    
    def test_placeholder_postgresql(self, qb):
        """Test PostgreSQL placeholder is $N."""
        assert qb.placeholder(1) == "$1"
        assert qb.placeholder(5) == "$5"
    
    def test_placeholders_multiple(self, qb):
        """Test multiple placeholders."""
        assert qb.placeholders(3) == "$1, $2, $3"
        assert qb.placeholders(1) == "$1"
    
    def test_insert(self, qb):
        """Test INSERT query."""
        query = qb.insert("products", columns=["name", "status"])
        assert query == "INSERT INTO products (name, status) VALUES ($1, $2)"
    
    def test_insert_returning(self, qb):
        """Test INSERT with RETURNING."""
        query = qb.insert(
            "products",
            columns=["name"],
            returning=["id", "created_at"],
        )
        assert query == "INSERT INTO products (name) VALUES ($1) RETURNING id, created_at"
    
    def test_update(self, qb):
        """Test UPDATE query."""
        query = qb.update(
            "products",
            columns=["name", "status"],
            where="id = $3",
        )
        assert query == "UPDATE products SET name = $1, status = $2 WHERE id = $3"


class TestQueryConversion:
    """Tests for query conversion functions."""
    
    def test_sqlite_to_postgresql_placeholders(self):
        """Test converting ? to $N."""
        query = "SELECT * FROM products WHERE a = ? AND b = ?"
        result = convert_sqlite_to_postgresql(query)
        assert result == "SELECT * FROM products WHERE a = $1 AND b = $2"
    
    def test_sqlite_to_postgresql_autoincrement(self):
        """Test converting AUTOINCREMENT to SERIAL."""
        query = "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT)"
        result = convert_sqlite_to_postgresql(query)
        assert "SERIAL PRIMARY KEY" in result
        assert "AUTOINCREMENT" not in result
    
    def test_postgresql_to_sqlite_placeholders(self):
        """Test converting $N to ?."""
        query = "SELECT * FROM products WHERE a = $1 AND b = $2"
        result = convert_postgresql_to_sqlite(query)
        assert result == "SELECT * FROM products WHERE a = ? AND b = ?"
    
    def test_postgresql_to_sqlite_serial(self):
        """Test converting SERIAL to AUTOINCREMENT."""
        query = "CREATE TABLE t (id SERIAL PRIMARY KEY)"
        result = convert_postgresql_to_sqlite(query)
        assert "INTEGER PRIMARY KEY AUTOINCREMENT" in result
        assert "SERIAL" not in result
    
    def test_roundtrip_conversion(self):
        """Test converting back and forth preserves structure."""
        original = "INSERT INTO t (a, b, c) VALUES (?, ?, ?)"
        pg = convert_sqlite_to_postgresql(original)
        back = convert_postgresql_to_sqlite(pg)
        assert back == original
