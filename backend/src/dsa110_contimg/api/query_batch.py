"""
Query batching utilities for optimized multi-record database access.

This module provides batch query capabilities that work with both
SQLite (aiosqlite) and PostgreSQL (asyncpg) backends.

The key optimization patterns are:
1. Batch fetching: Fetch multiple records by IDs in a single query
2. Chunked processing: Process large ID sets in configurable chunks
3. Prefetching: Load related records in parallel where possible

Example:
    # Instead of N+1 queries:
    for id in ids:
        record = await repo.get_by_id(id)  # BAD: N queries
    
    # Use batch fetch:
    records = await repo.get_many(ids)  # GOOD: 1-2 queries
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine, List, Optional, TypeVar, Dict, Sequence

T = TypeVar("T")

logger = logging.getLogger(__name__)

# Default batch size for chunked operations
DEFAULT_BATCH_SIZE = 100

# Maximum parameters for SQLite (SQLITE_MAX_VARIABLE_NUMBER is typically 999)
SQLITE_MAX_PARAMS = 900

# Maximum parameters for PostgreSQL (effectively unlimited, but 1000 is practical)
POSTGRES_MAX_PARAMS = 1000


def chunk_list(items: Sequence[T], chunk_size: int) -> List[List[T]]:
    """Split a list into chunks of specified size.
    
    Args:
        items: List to split
        chunk_size: Maximum size of each chunk
        
    Returns:
        List of chunks
        
    Example:
        >>> chunk_list([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    return [list(items[i:i + chunk_size]) for i in range(0, len(items), chunk_size)]


def build_in_clause(column: str, count: int, placeholder: str = "?") -> str:
    """Build an IN clause for batch queries.
    
    Args:
        column: Column name
        count: Number of parameters
        placeholder: Parameter placeholder (? for SQLite, $N for PostgreSQL)
        
    Returns:
        SQL IN clause string
        
    Example:
        >>> build_in_clause("id", 3)
        "id IN (?, ?, ?)"
        >>> build_in_clause("id", 3, "$")
        "id IN ($1, $2, $3)"
    """
    if placeholder == "$":
        # PostgreSQL-style numbered placeholders
        placeholders = ", ".join(f"${i}" for i in range(1, count + 1))
    else:
        # SQLite-style ? placeholders
        placeholders = ", ".join(placeholder for _ in range(count))
    return f"{column} IN ({placeholders})"


def build_batch_query(
    base_query: str,
    id_column: str,
    id_count: int,
    placeholder: str = "?",
) -> str:
    """Build a batch query with IN clause.
    
    Args:
        base_query: Base SQL query (without WHERE clause)
        id_column: Column name for ID filtering
        id_count: Number of IDs to filter by
        placeholder: Parameter placeholder style
        
    Returns:
        Complete SQL query with IN clause
        
    Example:
        >>> build_batch_query("SELECT * FROM images", "id", 3)
        "SELECT * FROM images WHERE id IN (?, ?, ?)"
    """
    in_clause = build_in_clause(id_column, id_count, placeholder)
    return f"{base_query} WHERE {in_clause}"


async def batch_fetch(
    fetch_func: Callable[[List[T]], Coroutine[Any, Any, List[Any]]],
    ids: Sequence[T],
    batch_size: int = DEFAULT_BATCH_SIZE,
    preserve_order: bool = True,
    id_key: str = "id",
) -> List[Any]:
    """Fetch records in batches and combine results.
    
    This is a generic batch fetcher that can work with any async fetch function.
    It handles chunking, parallel fetching, and result ordering.
    
    Args:
        fetch_func: Async function that takes a list of IDs and returns records
        ids: List of IDs to fetch
        batch_size: Maximum IDs per batch
        preserve_order: If True, return results in same order as input IDs
        id_key: Key/attribute to use for matching results to input IDs
        
    Returns:
        List of fetched records (may be shorter if some IDs not found)
        
    Example:
        async def fetch_images(image_ids):
            # Implementation
            pass
            
        images = await batch_fetch(fetch_images, [1, 2, 3, 4, 5], batch_size=2)
    """
    if not ids:
        return []
    
    # Deduplicate while preserving order for result mapping
    seen = set()
    unique_ids = []
    for id_ in ids:
        if id_ not in seen:
            seen.add(id_)
            unique_ids.append(id_)
    
    # Fetch in batches
    chunks = chunk_list(unique_ids, batch_size)
    all_results: List[Any] = []
    
    for chunk in chunks:
        try:
            results = await fetch_func(chunk)
            all_results.extend(results)
        except Exception as e:
            logger.error(f"Batch fetch error for chunk of {len(chunk)} IDs: {e}")
            raise
    
    if not preserve_order:
        return all_results
    
    # Reorder to match input order
    result_map: Dict[Any, Any] = {}
    for record in all_results:
        # Handle both dict and object records
        if isinstance(record, dict):
            key = record.get(id_key)
        else:
            key = getattr(record, id_key, None)
        if key is not None:
            result_map[key] = record
    
    # Return in original order (skipping missing IDs)
    ordered_results = []
    for id_ in ids:
        if id_ in result_map:
            ordered_results.append(result_map[id_])
    
    return ordered_results


async def prefetch_related(
    records: List[Any],
    foreign_key: str,
    fetch_func: Callable[[List[Any]], Coroutine[Any, Any, Dict[Any, Any]]],
    target_attr: str,
) -> List[Any]:
    """Prefetch related records and attach to parent records.
    
    This is useful for avoiding N+1 queries when fetching related data.
    
    Args:
        records: List of parent records
        foreign_key: Attribute/key on parent that references related record
        fetch_func: Async function that fetches related records by IDs,
                    returns dict mapping ID to related record
        target_attr: Attribute name to set on parent with related record
        
    Returns:
        Same records list with related data attached
        
    Example:
        async def fetch_ms_by_paths(paths):
            # Returns {path: MSRecord}
            pass
            
        images = await prefetch_related(
            images,
            foreign_key="ms_path",
            fetch_func=fetch_ms_by_paths,
            target_attr="ms_record"
        )
    """
    if not records:
        return records
    
    # Collect unique foreign keys
    fk_values = set()
    for record in records:
        if isinstance(record, dict):
            fk = record.get(foreign_key)
        else:
            fk = getattr(record, foreign_key, None)
        if fk is not None:
            fk_values.add(fk)
    
    if not fk_values:
        return records
    
    # Fetch related records
    related_map = await fetch_func(list(fk_values))
    
    # Attach to parent records
    for record in records:
        if isinstance(record, dict):
            fk = record.get(foreign_key)
            if fk in related_map:
                record[target_attr] = related_map[fk]
        else:
            fk = getattr(record, foreign_key, None)
            if fk in related_map:
                setattr(record, target_attr, related_map[fk])
    
    return records


class BatchQueryBuilder:
    """Builder for constructing batch queries with proper placeholder handling.
    
    This class helps build queries that work with both SQLite and PostgreSQL
    by handling placeholder differences.
    
    Example:
        builder = BatchQueryBuilder(use_postgres=True)
        query, params = builder.build_select(
            table="images",
            columns=["id", "path", "ms_path"],
            id_column="id",
            ids=[1, 2, 3]
        )
        # query: "SELECT id, path, ms_path FROM images WHERE id IN ($1, $2, $3)"
        # params: [1, 2, 3]
    """
    
    def __init__(self, use_postgres: bool = False, max_params: Optional[int] = None):
        """Initialize the batch query builder.
        
        Args:
            use_postgres: If True, use PostgreSQL $N placeholders
            max_params: Maximum parameters per query (default: backend-specific)
        """
        self.use_postgres = use_postgres
        self.max_params = max_params or (
            POSTGRES_MAX_PARAMS if use_postgres else SQLITE_MAX_PARAMS
        )
    
    def build_select(
        self,
        table: str,
        columns: List[str],
        id_column: str,
        ids: Sequence[Any],
        order_by: Optional[str] = None,
    ) -> tuple[str, List[Any]]:
        """Build a SELECT query with IN clause.
        
        Args:
            table: Table name
            columns: Columns to select (use ["*"] for all)
            id_column: Column for IN clause filtering
            ids: Values for IN clause
            order_by: Optional ORDER BY clause
            
        Returns:
            Tuple of (query_string, parameters)
        """
        if not ids:
            cols = ", ".join(columns)
            return f"SELECT {cols} FROM {table} WHERE 1=0", []
        
        cols = ", ".join(columns)
        in_clause = self._build_in_clause(id_column, len(ids))
        
        query = f"SELECT {cols} FROM {table} WHERE {in_clause}"
        if order_by:
            query += f" ORDER BY {order_by}"
        
        return query, list(ids)
    
    def build_count(
        self,
        table: str,
        id_column: str,
        ids: Sequence[Any],
    ) -> tuple[str, List[Any]]:
        """Build a COUNT query with IN clause.
        
        Args:
            table: Table name
            id_column: Column for IN clause filtering
            ids: Values for IN clause
            
        Returns:
            Tuple of (query_string, parameters)
        """
        if not ids:
            return f"SELECT COUNT(*) FROM {table} WHERE 1=0", []
        
        in_clause = self._build_in_clause(id_column, len(ids))
        return f"SELECT COUNT(*) FROM {table} WHERE {in_clause}", list(ids)
    
    def _build_in_clause(self, column: str, count: int) -> str:
        """Build an IN clause with proper placeholders."""
        if self.use_postgres:
            placeholders = ", ".join(f"${i}" for i in range(1, count + 1))
        else:
            placeholders = ", ".join("?" for _ in range(count))
        return f"{column} IN ({placeholders})"
    
    def get_batch_size(self) -> int:
        """Get recommended batch size for this backend."""
        return min(DEFAULT_BATCH_SIZE, self.max_params)
