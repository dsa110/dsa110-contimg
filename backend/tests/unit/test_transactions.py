"""
Tests for database transaction context managers.
"""

import sqlite3
import tempfile
from pathlib import Path

import pytest

from dsa110_contimg.api.database import (
    transaction,
    async_transaction,
    transactional_connection,
    async_transactional_connection,
)


class TestSyncTransaction:
    """Tests for the synchronous transaction context manager."""
    
    @pytest.fixture
    def db_path(self, tmp_path):
        """Create a temporary database."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        return str(db_file)
    
    def test_transaction_commits_on_success(self, db_path):
        """Test that transaction commits when no error occurs."""
        conn = sqlite3.connect(db_path)
        
        with transaction(conn):
            conn.execute("INSERT INTO items (name) VALUES ('test1')")
            conn.execute("INSERT INTO items (name) VALUES ('test2')")
        
        # Verify data was committed
        cursor = conn.execute("SELECT COUNT(*) FROM items")
        assert cursor.fetchone()[0] == 2
        conn.close()
    
    def test_transaction_rollback_on_error(self, db_path):
        """Test that transaction rolls back on error."""
        conn = sqlite3.connect(db_path)
        
        try:
            with transaction(conn):
                conn.execute("INSERT INTO items (name) VALUES ('test1')")
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        # Verify data was rolled back
        cursor = conn.execute("SELECT COUNT(*) FROM items")
        assert cursor.fetchone()[0] == 0
        conn.close()
    
    def test_transaction_nested_operations(self, db_path):
        """Test multiple operations in a transaction."""
        conn = sqlite3.connect(db_path)
        
        with transaction(conn):
            conn.execute("INSERT INTO items (name) VALUES ('item1')")
            conn.execute("INSERT INTO items (name) VALUES ('item2')")
            conn.execute("UPDATE items SET name = 'updated' WHERE name = 'item1'")
        
        cursor = conn.execute("SELECT name FROM items ORDER BY id")
        names = [row[0] for row in cursor.fetchall()]
        assert names == ['updated', 'item2']
        conn.close()
    
    def test_transaction_preserves_exception_type(self, db_path):
        """Test that the original exception is re-raised."""
        conn = sqlite3.connect(db_path)
        
        with pytest.raises(KeyError):
            with transaction(conn):
                conn.execute("INSERT INTO items (name) VALUES ('test')")
                raise KeyError("test key")
        
        conn.close()


class TestTransactionalConnection:
    """Tests for the transactional_connection context manager."""
    
    @pytest.fixture
    def db_path(self, tmp_path):
        """Create a temporary database."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        return str(db_file)
    
    def test_connection_commits_and_closes(self, db_path):
        """Test that connection commits and closes properly."""
        with transactional_connection(db_path) as conn:
            conn.execute("INSERT INTO items (name) VALUES ('test')")
        
        # Verify using a new connection
        verify_conn = sqlite3.connect(db_path)
        cursor = verify_conn.execute("SELECT COUNT(*) FROM items")
        assert cursor.fetchone()[0] == 1
        verify_conn.close()
    
    def test_connection_rolls_back_on_error(self, db_path):
        """Test that connection rolls back on error."""
        try:
            with transactional_connection(db_path) as conn:
                conn.execute("INSERT INTO items (name) VALUES ('test')")
                raise RuntimeError("Simulated error")
        except RuntimeError:
            pass
        
        # Verify data was not committed
        verify_conn = sqlite3.connect(db_path)
        cursor = verify_conn.execute("SELECT COUNT(*) FROM items")
        assert cursor.fetchone()[0] == 0
        verify_conn.close()
    
    def test_connection_with_row_factory(self, db_path):
        """Test that row factory is configured."""
        with transactional_connection(db_path, row_factory=True) as conn:
            conn.execute("INSERT INTO items (name) VALUES ('test')")
            cursor = conn.execute("SELECT * FROM items")
            row = cursor.fetchone()
            # Row factory should allow dict-like access
            assert row['name'] == 'test'
    
    def test_connection_without_row_factory(self, db_path):
        """Test connection without row factory."""
        with transactional_connection(db_path, row_factory=False) as conn:
            conn.execute("INSERT INTO items (name) VALUES ('test')")
            cursor = conn.execute("SELECT * FROM items")
            row = cursor.fetchone()
            # Should be a plain tuple
            assert row == (1, 'test')


@pytest.mark.asyncio
class TestAsyncTransaction:
    """Tests for the async transaction context manager."""
    
    @pytest.fixture
    def db_path(self, tmp_path):
        """Create a temporary database."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        return str(db_file)
    
    async def test_async_transaction_commits(self, db_path):
        """Test that async transaction commits on success."""
        import aiosqlite
        
        conn = await aiosqlite.connect(db_path)
        
        async with async_transaction(conn):
            await conn.execute("INSERT INTO items (name) VALUES ('test1')")
            await conn.execute("INSERT INTO items (name) VALUES ('test2')")
        
        cursor = await conn.execute("SELECT COUNT(*) FROM items")
        row = await cursor.fetchone()
        assert row[0] == 2
        
        await conn.close()
    
    async def test_async_transaction_rollback(self, db_path):
        """Test that async transaction rolls back on error."""
        import aiosqlite
        
        conn = await aiosqlite.connect(db_path)
        
        try:
            async with async_transaction(conn):
                await conn.execute("INSERT INTO items (name) VALUES ('test')")
                raise ValueError("Simulated error")
        except ValueError:
            pass
        
        cursor = await conn.execute("SELECT COUNT(*) FROM items")
        row = await cursor.fetchone()
        assert row[0] == 0
        
        await conn.close()


@pytest.mark.asyncio
class TestAsyncTransactionalConnection:
    """Tests for the async_transactional_connection context manager."""
    
    @pytest.fixture
    def db_path(self, tmp_path):
        """Create a temporary database."""
        db_file = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_file))
        conn.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)")
        conn.commit()
        conn.close()
        return str(db_file)
    
    async def test_async_connection_commits_and_closes(self, db_path):
        """Test that async connection commits and closes properly."""
        async with async_transactional_connection(db_path) as conn:
            await conn.execute("INSERT INTO items (name) VALUES ('test')")
        
        # Verify using a sync connection
        verify_conn = sqlite3.connect(db_path)
        cursor = verify_conn.execute("SELECT COUNT(*) FROM items")
        assert cursor.fetchone()[0] == 1
        verify_conn.close()
    
    async def test_async_connection_rollback(self, db_path):
        """Test that async connection rolls back on error."""
        try:
            async with async_transactional_connection(db_path) as conn:
                await conn.execute("INSERT INTO items (name) VALUES ('test')")
                raise RuntimeError("Simulated error")
        except RuntimeError:
            pass
        
        # Verify data was not committed
        verify_conn = sqlite3.connect(db_path)
        cursor = verify_conn.execute("SELECT COUNT(*) FROM items")
        assert cursor.fetchone()[0] == 0
        verify_conn.close()
