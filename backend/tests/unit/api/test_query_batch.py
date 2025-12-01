"""
Unit tests for query_batch module.

Tests the batch query utilities including:
- chunk_list: Splitting lists into chunks
- build_in_clause: Building SQL IN clauses
- BatchQueryBuilder: Query construction
- batch_fetch: Async batch fetching
"""

import pytest
from typing import List, Dict, Any

from dsa110_contimg.api.query_batch import (
    chunk_list,
    build_in_clause,
    build_batch_query,
    BatchQueryBuilder,
    batch_fetch,
    prefetch_related,
    SQLITE_MAX_PARAMS,
    POSTGRES_MAX_PARAMS,
    DEFAULT_BATCH_SIZE,
)


# =============================================================================
# chunk_list tests
# =============================================================================

class TestChunkList:
    """Tests for the chunk_list function."""
    
    def test_empty_list(self):
        """Empty list returns empty list of chunks."""
        assert chunk_list([], 10) == []
    
    def test_single_element(self):
        """Single element returns one chunk."""
        assert chunk_list([1], 10) == [[1]]
    
    def test_exact_chunk_size(self):
        """List exactly divisible by chunk size."""
        assert chunk_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]
    
    def test_remainder_chunk(self):
        """List with remainder creates partial final chunk."""
        assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    
    def test_chunk_larger_than_list(self):
        """Chunk size larger than list returns single chunk."""
        assert chunk_list([1, 2, 3], 10) == [[1, 2, 3]]
    
    def test_chunk_size_one(self):
        """Chunk size of 1 creates individual chunks."""
        assert chunk_list([1, 2, 3], 1) == [[1], [2], [3]]
    
    def test_tuple_input(self):
        """Tuple input is handled correctly."""
        result = chunk_list((1, 2, 3, 4, 5), 2)
        assert result == [[1, 2], [3, 4], [5]]


# =============================================================================
# build_in_clause tests
# =============================================================================

class TestBuildInClause:
    """Tests for the build_in_clause function."""
    
    def test_sqlite_placeholders(self):
        """SQLite-style ? placeholders."""
        result = build_in_clause("id", 3)
        assert result == "id IN (?, ?, ?)"
    
    def test_postgres_placeholders(self):
        """PostgreSQL-style $N placeholders."""
        result = build_in_clause("id", 3, "$")
        assert result == "id IN ($1, $2, $3)"
    
    def test_single_value(self):
        """Single value IN clause."""
        assert build_in_clause("col", 1) == "col IN (?)"
    
    def test_column_names_preserved(self):
        """Column names with special chars preserved."""
        result = build_in_clause("table.column_name", 2)
        assert result == "table.column_name IN (?, ?)"


# =============================================================================
# build_batch_query tests
# =============================================================================

class TestBuildBatchQuery:
    """Tests for the build_batch_query function."""
    
    def test_basic_select(self):
        """Basic SELECT with IN clause."""
        result = build_batch_query(
            "SELECT * FROM images",
            "id",
            3
        )
        assert result == "SELECT * FROM images WHERE id IN (?, ?, ?)"
    
    def test_postgres_style(self):
        """PostgreSQL placeholder style."""
        result = build_batch_query(
            "SELECT id, name FROM users",
            "id",
            2,
            "$"
        )
        assert result == "SELECT id, name FROM users WHERE id IN ($1, $2)"


# =============================================================================
# BatchQueryBuilder tests
# =============================================================================

class TestBatchQueryBuilder:
    """Tests for the BatchQueryBuilder class."""
    
    def test_sqlite_builder(self):
        """SQLite query builder."""
        builder = BatchQueryBuilder(use_postgres=False)
        query, params = builder.build_select(
            table="images",
            columns=["id", "path"],
            id_column="id",
            ids=[1, 2, 3]
        )
        assert "?" in query
        assert "$" not in query
        assert params == [1, 2, 3]
        assert "id IN" in query
    
    def test_postgres_builder(self):
        """PostgreSQL query builder."""
        builder = BatchQueryBuilder(use_postgres=True)
        query, params = builder.build_select(
            table="images",
            columns=["id", "path"],
            id_column="id",
            ids=[1, 2, 3]
        )
        assert "$1" in query
        assert "$2" in query
        assert "$3" in query
        assert "?" not in query
        assert params == [1, 2, 3]
    
    def test_empty_ids(self):
        """Empty ID list returns no-match query."""
        builder = BatchQueryBuilder()
        query, params = builder.build_select(
            table="test",
            columns=["*"],
            id_column="id",
            ids=[]
        )
        assert "1=0" in query  # Always false condition
        assert params == []
    
    def test_order_by(self):
        """ORDER BY clause is added."""
        builder = BatchQueryBuilder()
        query, params = builder.build_select(
            table="test",
            columns=["*"],
            id_column="id",
            ids=[1],
            order_by="created_at DESC"
        )
        assert "ORDER BY created_at DESC" in query
    
    def test_build_count(self):
        """COUNT query builder."""
        builder = BatchQueryBuilder()
        query, params = builder.build_count(
            table="images",
            id_column="id",
            ids=[1, 2]
        )
        assert "COUNT(*)" in query
        assert "id IN" in query
        assert params == [1, 2]
    
    def test_get_batch_size(self):
        """Batch size respects max params."""
        sqlite_builder = BatchQueryBuilder(use_postgres=False)
        assert sqlite_builder.get_batch_size() <= SQLITE_MAX_PARAMS
        
        pg_builder = BatchQueryBuilder(use_postgres=True)
        assert pg_builder.get_batch_size() <= POSTGRES_MAX_PARAMS
    
    def test_custom_max_params(self):
        """Custom max params limit."""
        builder = BatchQueryBuilder(max_params=50)
        assert builder.get_batch_size() == min(DEFAULT_BATCH_SIZE, 50)


# =============================================================================
# batch_fetch tests (async)
# =============================================================================

@pytest.mark.asyncio
class TestBatchFetch:
    """Tests for the async batch_fetch function."""
    
    async def test_empty_ids(self):
        """Empty IDs returns empty list."""
        async def fetch_func(ids):
            return []
        
        result = await batch_fetch(fetch_func, [])
        assert result == []
    
    async def test_single_batch(self):
        """Single batch fetch."""
        async def fetch_func(ids):
            return [{"id": id_, "name": f"item-{id_}"} for id_ in ids]
        
        result = await batch_fetch(fetch_func, [1, 2, 3], batch_size=10)
        assert len(result) == 3
        assert result[0]["id"] == 1
    
    async def test_multiple_batches(self):
        """Multiple batch fetches are combined."""
        call_count = 0
        
        async def fetch_func(ids):
            nonlocal call_count
            call_count += 1
            return [{"id": id_, "value": id_ * 10} for id_ in ids]
        
        result = await batch_fetch(
            fetch_func,
            [1, 2, 3, 4, 5],
            batch_size=2
        )
        
        assert call_count == 3  # 3 batches: [1,2], [3,4], [5]
        assert len(result) == 5
    
    async def test_preserve_order(self):
        """Results are returned in input order."""
        async def fetch_func(ids):
            # Return in reverse order
            return [{"id": id_} for id_ in reversed(ids)]
        
        result = await batch_fetch(
            fetch_func,
            [3, 1, 2],
            batch_size=10,
            preserve_order=True
        )
        
        # Should be reordered to match input
        assert [r["id"] for r in result] == [3, 1, 2]
    
    async def test_no_preserve_order(self):
        """Results not reordered when preserve_order=False."""
        async def fetch_func(ids):
            return [{"id": id_} for id_ in ids]
        
        result = await batch_fetch(
            fetch_func,
            [1, 2, 3],
            batch_size=10,
            preserve_order=False
        )
        
        # Just check all are present
        assert len(result) == 3
    
    async def test_deduplication(self):
        """Duplicate IDs are deduplicated before fetching."""
        fetched_ids = []
        
        async def fetch_func(ids):
            fetched_ids.extend(ids)
            return [{"id": id_} for id_ in ids]
        
        result = await batch_fetch(
            fetch_func,
            [1, 2, 1, 3, 2],
            batch_size=10
        )
        
        # Should only fetch unique IDs
        assert sorted(fetched_ids) == [1, 2, 3]
        # But result should have all requested (5 items)
        assert len(result) == 5
    
    async def test_missing_ids(self):
        """Missing IDs result in fewer returned records."""
        async def fetch_func(ids):
            # Only return even IDs
            return [{"id": id_} for id_ in ids if id_ % 2 == 0]
        
        result = await batch_fetch(
            fetch_func,
            [1, 2, 3, 4, 5],
            batch_size=10
        )
        
        # Only 2 and 4 found
        assert len(result) == 2
        assert all(r["id"] % 2 == 0 for r in result)


# =============================================================================
# prefetch_related tests (async)
# =============================================================================

@pytest.mark.asyncio
class TestPrefetchRelated:
    """Tests for the async prefetch_related function."""
    
    async def test_empty_records(self):
        """Empty records returns empty list."""
        async def fetch_func(ids):
            return {}
        
        result = await prefetch_related([], "fk", fetch_func, "related")
        assert result == []
    
    async def test_attach_related_dict(self):
        """Related records attached to dict records."""
        records = [
            {"id": 1, "ms_path": "/path/a"},
            {"id": 2, "ms_path": "/path/b"},
        ]
        
        async def fetch_ms(paths):
            return {
                "/path/a": {"path": "/path/a", "status": "done"},
                "/path/b": {"path": "/path/b", "status": "pending"},
            }
        
        result = await prefetch_related(
            records,
            foreign_key="ms_path",
            fetch_func=fetch_ms,
            target_attr="ms_record"
        )
        
        assert result[0]["ms_record"]["status"] == "done"
        assert result[1]["ms_record"]["status"] == "pending"
    
    async def test_missing_related(self):
        """Missing related records don't raise errors."""
        records = [
            {"id": 1, "ms_path": "/path/a"},
            {"id": 2, "ms_path": "/path/missing"},
        ]
        
        async def fetch_ms(paths):
            return {"/path/a": {"status": "done"}}
        
        result = await prefetch_related(
            records,
            foreign_key="ms_path",
            fetch_func=fetch_ms,
            target_attr="ms_record"
        )
        
        assert "ms_record" in result[0]
        assert "ms_record" not in result[1]


# =============================================================================
# Constants tests
# =============================================================================

class TestConstants:
    """Tests for module constants."""
    
    def test_sqlite_max_params(self):
        """SQLite max params is reasonable."""
        assert 500 <= SQLITE_MAX_PARAMS <= 999
    
    def test_postgres_max_params(self):
        """PostgreSQL max params is reasonable."""
        assert POSTGRES_MAX_PARAMS >= 1000
    
    def test_default_batch_size(self):
        """Default batch size is reasonable."""
        assert 50 <= DEFAULT_BATCH_SIZE <= 200
