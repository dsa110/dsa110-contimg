"""
Saved Queries API routes.

CRUD operations for saved filter configurations with visibility controls.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from ..dependencies import get_pipeline_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/saved-queries", tags=["saved-queries"])


# ============================================================================
# Pydantic Models
# ============================================================================


class SavedQueryInput(BaseModel):
    """Input for creating/updating a saved query."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    filters: str  # JSON string of FilterState
    target_type: str = Field(..., pattern="^(images|sources|jobs|ms)$")
    visibility: str = Field(default="private", pattern="^(private|team|public)$")


class SavedQuery(BaseModel):
    """Full saved query with metadata."""

    id: str
    name: str
    description: Optional[str] = None
    filters: str
    target_type: str
    visibility: str
    created_by: str
    created_at: str
    updated_at: str


class SavedQueryListResponse(BaseModel):
    """Response for listing saved queries."""

    queries: List[SavedQuery]
    total: int


# ============================================================================
# Database Helpers
# ============================================================================


def _row_to_query(row: sqlite3.Row) -> SavedQuery:
    """Convert database row to SavedQuery model."""
    return SavedQuery(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        filters=row["filters"],
        target_type=row["target_type"],
        visibility=row["visibility"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_current_user() -> str:
    """Get current user. Placeholder for auth integration."""
    # TODO: Integrate with actual auth system
    return "default_user"


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=SavedQueryListResponse)
async def list_saved_queries(
    target_type: Optional[str] = Query(None, description="Filter by target type"),
    visibility: Optional[str] = Query(None, description="Filter by visibility"),
    include_public: bool = Query(True, description="Include public queries"),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """List saved queries visible to the current user."""
    current_user = _get_current_user()
    
    conditions = []
    params = []
    
    # Visibility filter: own queries + public (optionally)
    if include_public:
        conditions.append("(created_by = ? OR visibility = 'public' OR visibility = 'team')")
        params.append(current_user)
    else:
        conditions.append("created_by = ?")
        params.append(current_user)
    
    if target_type:
        conditions.append("target_type = ?")
        params.append(target_type)
    
    if visibility:
        conditions.append("visibility = ?")
        params.append(visibility)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    cursor = db.execute(
        f"""
        SELECT * FROM saved_queries
        WHERE {where_clause}
        ORDER BY updated_at DESC
        """,
        params,
    )
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    queries = [_row_to_query(row) for row in rows]
    return SavedQueryListResponse(queries=queries, total=len(queries))


@router.get("/{query_id}", response_model=SavedQuery)
async def get_saved_query(
    query_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get a single saved query by ID."""
    current_user = _get_current_user()
    
    cursor = db.execute(
        """
        SELECT * FROM saved_queries
        WHERE id = ? AND (created_by = ? OR visibility IN ('public', 'team'))
        """,
        (query_id, current_user),
    )
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    
    return _row_to_query(row)


@router.post("", response_model=SavedQuery, status_code=201)
async def create_saved_query(
    data: SavedQueryInput,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Create a new saved query."""
    current_user = _get_current_user()
    query_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    try:
        db.execute(
            """
            INSERT INTO saved_queries (id, name, description, filters, target_type, visibility, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query_id,
                data.name,
                data.description,
                data.filters,
                data.target_type,
                data.visibility,
                current_user,
                now,
                now,
            ),
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Failed to create query: {e}")
    
    return SavedQuery(
        id=query_id,
        name=data.name,
        description=data.description,
        filters=data.filters,
        target_type=data.target_type,
        visibility=data.visibility,
        created_by=current_user,
        created_at=now,
        updated_at=now,
    )


@router.put("/{query_id}", response_model=SavedQuery)
async def update_saved_query(
    query_id: str,
    data: SavedQueryInput,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Update an existing saved query. Only owner can update."""
    current_user = _get_current_user()
    
    # Check ownership
    cursor = db.execute(
        "SELECT created_by FROM saved_queries WHERE id = ?",
        (query_id,),
    )
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    
    if row[0] != current_user:
        raise HTTPException(status_code=403, detail="Cannot update another user's query")
    
    db.execute(
        """
        UPDATE saved_queries
        SET name = ?, description = ?, filters = ?, target_type = ?, visibility = ?
        WHERE id = ?
        """,
        (data.name, data.description, data.filters, data.target_type, data.visibility, query_id),
    )
    db.commit()
    
    # Fetch updated record
    cursor = db.execute("SELECT * FROM saved_queries WHERE id = ?", (query_id,))
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    return _row_to_query(row)


@router.delete("/{query_id}", status_code=204)
async def delete_saved_query(
    query_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Delete a saved query. Only owner can delete."""
    current_user = _get_current_user()
    
    # Check ownership
    cursor = db.execute(
        "SELECT created_by FROM saved_queries WHERE id = ?",
        (query_id,),
    )
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    
    if row[0] != current_user:
        raise HTTPException(status_code=403, detail="Cannot delete another user's query")
    
    db.execute("DELETE FROM saved_queries WHERE id = ?", (query_id,))
    db.commit()
    
    return None


@router.post("/{query_id}/fork", response_model=SavedQuery, status_code=201)
async def fork_saved_query(
    query_id: str,
    name: Optional[str] = Query(None, description="New name for forked query"),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Fork a public/team query to create a personal copy."""
    current_user = _get_current_user()
    
    # Get original query (must be accessible)
    cursor = db.execute(
        """
        SELECT * FROM saved_queries
        WHERE id = ? AND (created_by = ? OR visibility IN ('public', 'team'))
        """,
        (query_id, current_user),
    )
    cursor.row_factory = sqlite3.Row
    original = cursor.fetchone()
    
    if not original:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found or not accessible")
    
    # Create fork
    fork_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    fork_name = name or f"{original['name']} (copy)"
    
    db.execute(
        """
        INSERT INTO saved_queries (id, name, description, filters, target_type, visibility, created_by, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, 'private', ?, ?, ?)
        """,
        (
            fork_id,
            fork_name,
            original["description"],
            original["filters"],
            original["target_type"],
            current_user,
            now,
            now,
        ),
    )
    db.commit()
    
    return SavedQuery(
        id=fork_id,
        name=fork_name,
        description=original["description"],
        filters=original["filters"],
        target_type=original["target_type"],
        visibility="private",
        created_by=current_user,
        created_at=now,
        updated_at=now,
    )
