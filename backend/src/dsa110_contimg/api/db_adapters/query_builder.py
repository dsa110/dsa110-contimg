"""
SQL Query Builder for SQLite.

This module provides utilities for building SQL queries for SQLite.

Note: PostgreSQL support was removed in the complexity reduction refactor.
The pipeline exclusively uses SQLite for data storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Sequence


class QueryBuilder:
    """Build SQL queries for SQLite.
    
    This class helps construct SQL queries with proper SQLite syntax.
    
    Example:
        qb = QueryBuilder()
        query = qb.select("products", columns=["id", "name"])
        # Returns: "SELECT id, name FROM products"
        
        query = qb.insert("products", columns=["name", "status"])
        # Returns: "INSERT INTO products (name, status) VALUES (?, ?)"
    """
    
    def __init__(self):
        pass
    
    def placeholder(self, index: int) -> str:
        """Get parameter placeholder for the given index (1-based).
        
        Args:
            index: 1-based parameter index
            
        Returns:
            "?" for SQLite
        """
        return "?"
    
    def placeholders(self, count: int) -> str:
        """Get comma-separated placeholders for N parameters.
        
        Args:
            count: Number of placeholders needed
            
        Returns:
            "?, ?, ?" for SQLite (3 params)
        """
        return ", ".join("?" for _ in range(count))
    
    def select(
        self,
        table: str,
        columns: Optional[Sequence[str]] = None,
        where: Optional[str] = None,
        order_by: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        """Build a SELECT query.
        
        Args:
            table: Table name
            columns: Columns to select (default: *)
            where: WHERE clause (without "WHERE" keyword)
            order_by: ORDER BY clause (without "ORDER BY" keywords)
            limit: LIMIT value
            offset: OFFSET value
            
        Returns:
            Complete SELECT query string
        """
        cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {cols} FROM {table}"
        
        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit is not None:
            query += f" LIMIT {limit}"
        if offset is not None:
            query += f" OFFSET {offset}"
        
        return query
    
    def insert(
        self,
        table: str,
        columns: Sequence[str],
        returning: Optional[Sequence[str]] = None,
    ) -> str:
        """Build an INSERT query.
        
        Args:
            table: Table name
            columns: Column names
            returning: Ignored (was PostgreSQL-only feature)
            
        Returns:
            INSERT query with placeholders
        """
        cols = ", ".join(columns)
        placeholders = self.placeholders(len(columns))
        query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        
        return query
    
    def update(
        self,
        table: str,
        columns: Sequence[str],
        where: str,
        where_param_offset: int = 0,
    ) -> str:
        """Build an UPDATE query.
        
        Args:
            table: Table name
            columns: Columns to update
            where: WHERE clause (with placeholders)
            where_param_offset: Ignored (was for PostgreSQL $N params)
            
        Returns:
            UPDATE query with placeholders
        """
        # Generate SET clause with ? placeholders
        set_parts = [f"{col} = ?" for col in columns]
        
        set_clause = ", ".join(set_parts)
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        return query
    
    def delete(self, table: str, where: str) -> str:
        """Build a DELETE query.
        
        Args:
            table: Table name
            where: WHERE clause
            
        Returns:
            DELETE query
        """
        return f"DELETE FROM {table} WHERE {where}"
    
    def upsert(
        self,
        table: str,
        columns: Sequence[str],
        conflict_columns: Sequence[str],
        update_columns: Optional[Sequence[str]] = None,
    ) -> str:
        """Build an UPSERT query (INSERT ... ON CONFLICT).
        
        Args:
            table: Table name
            columns: All columns to insert
            conflict_columns: Columns that define uniqueness
            update_columns: Columns to update on conflict (default: all non-conflict columns)
            
        Returns:
            UPSERT query (SQLite 3.24+ and PostgreSQL compatible)
        """
        # Build INSERT part
        cols = ", ".join(columns)
        placeholders = self.placeholders(len(columns))
        query = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        
        # Build ON CONFLICT part
        conflict_cols = ", ".join(conflict_columns)
        query += f" ON CONFLICT ({conflict_cols})"
        
        # Build UPDATE part
        if update_columns is None:
            update_columns = [c for c in columns if c not in conflict_columns]
        
        if update_columns:
            update_parts = [
                f"{col} = excluded.{col}" for col in update_columns
            ]
            query += f" DO UPDATE SET {', '.join(update_parts)}"
        else:
            query += " DO NOTHING"
        
        return query
    
    def count(self, table: str, where: Optional[str] = None) -> str:
        """Build a COUNT query.
        
        Args:
            table: Table name
            where: Optional WHERE clause
            
        Returns:
            COUNT query
        """
        query = f"SELECT COUNT(*) FROM {table}"
        if where:
            query += f" WHERE {where}"
        return query
    
    def exists(self, table: str, where: str) -> str:
        """Build an EXISTS check query.
        
        Args:
            table: Table name
            where: WHERE clause
            
        Returns:
            Query that returns 1 if exists, 0 otherwise
        """
        return f"SELECT EXISTS(SELECT 1 FROM {table} WHERE {where})"



