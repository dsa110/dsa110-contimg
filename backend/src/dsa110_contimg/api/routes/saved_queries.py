"""
Saved Queries API routes.

CRUD operations for saved filter configurations with visibility controls.
Includes query execution, favorites, cloning, and statistics.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from ..dependencies import get_pipeline_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queries", tags=["queries"])


# ============================================================================
# Pydantic Models
# ============================================================================


class QueryParameter(BaseModel):
    """Parameter definition for parameterized queries."""
    
    name: str
    type: str = "string"  # string, number, date, boolean
    default_value: Optional[str] = None
    description: Optional[str] = None
    required: bool = False


class SavedQueryInput(BaseModel):
    """Input for creating/updating a saved query."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    query_string: Optional[str] = None  # SQL-like query string
    filters: Optional[str] = None  # JSON string of FilterState (legacy)
    target_type: str = Field(..., pattern="^(images|sources|jobs|ms|source|image|job|observation)$")
    visibility: str = Field(default="private", pattern="^(private|team|public)$")
    tags: Optional[List[str]] = None
    parameters: Optional[List[QueryParameter]] = None


class SavedQuery(BaseModel):
    """Full saved query with metadata."""

    id: str
    name: str
    description: Optional[str] = None
    query_string: Optional[str] = None
    filters: Optional[str] = None
    target_type: str
    visibility: str
    owner_id: str
    owner_name: str
    is_favorite: bool = False
    run_count: int = 0
    last_run_at: Optional[str] = None
    created_at: str
    updated_at: str
    tags: List[str] = []
    parameters: List[QueryParameter] = []


class SavedQueryListResponse(BaseModel):
    """Response for listing saved queries."""

    queries: List[SavedQuery]
    total: int


class QueryResult(BaseModel):
    """Result from running a query."""
    
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    truncated: bool = False


class RunQueryRequest(BaseModel):
    """Request to run a query."""
    
    query_id: Optional[str] = None
    query_string: Optional[str] = None
    parameters: Optional[Dict[str, str]] = None
    limit: int = Field(default=100, le=1000)


class QueryStats(BaseModel):
    """Statistics about saved queries."""
    
    total_queries: int
    public_queries: int
    team_queries: int
    private_queries: int
    queries_run_today: int
    queries_run_this_week: int
    popular_tags: List[Dict[str, Any]]
    top_queries: List[Dict[str, Any]]


# ============================================================================
# Extended Database Schema
# ============================================================================

QUERIES_SCHEMA = """
-- Add new columns if they don't exist
ALTER TABLE saved_queries ADD COLUMN query_string TEXT;
ALTER TABLE saved_queries ADD COLUMN owner_name TEXT DEFAULT 'Default User';
ALTER TABLE saved_queries ADD COLUMN is_favorite INTEGER DEFAULT 0;
ALTER TABLE saved_queries ADD COLUMN run_count INTEGER DEFAULT 0;
ALTER TABLE saved_queries ADD COLUMN last_run_at TEXT;
ALTER TABLE saved_queries ADD COLUMN tags TEXT DEFAULT '[]';
ALTER TABLE saved_queries ADD COLUMN parameters TEXT DEFAULT '[]';

-- Create query history table
CREATE TABLE IF NOT EXISTS query_history (
    id TEXT PRIMARY KEY,
    query_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    run_at TEXT NOT NULL DEFAULT (datetime('now')),
    execution_time_ms REAL,
    row_count INTEGER,
    FOREIGN KEY (query_id) REFERENCES saved_queries(id)
);

CREATE INDEX IF NOT EXISTS idx_query_history_user ON query_history(user_id);
CREATE INDEX IF NOT EXISTS idx_query_history_query ON query_history(query_id);
"""


def _ensure_schema(db: sqlite3.Connection):
    """Ensure query tables have all columns."""
    try:
        # Try to add columns (ignore if they exist)
        for stmt in QUERIES_SCHEMA.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    db.execute(stmt)
                except sqlite3.OperationalError:
                    pass  # Column already exists or table exists
        db.commit()
    except Exception as e:
        logger.warning(f"Schema migration warning: {e}")


# ============================================================================
# Database Helpers
# ============================================================================


def _row_to_query(row: sqlite3.Row, is_favorite: bool = False) -> SavedQuery:
    """Convert database row to SavedQuery model."""
    tags = []
    parameters = []
    
    try:
        tags_val = row["tags"] if "tags" in row.keys() else None
        if tags_val:
            tags = json.loads(tags_val)
    except (json.JSONDecodeError, TypeError):
        pass
    
    try:
        params_val = row["parameters"] if "parameters" in row.keys() else None
        if params_val:
            parameters = [QueryParameter(**p) for p in json.loads(params_val)]
    except (json.JSONDecodeError, TypeError):
        pass
    
    # Handle both old (created_by) and new (owner_id) column names
    owner_id = row["owner_id"] if "owner_id" in row.keys() else row.get("created_by", "unknown")
    owner_name = row["owner_name"] if "owner_name" in row.keys() else "Default User"
    fav = row["is_favorite"] if "is_favorite" in row.keys() else 0
    run_count = row["run_count"] if "run_count" in row.keys() else 0
    last_run = row["last_run_at"] if "last_run_at" in row.keys() else None
    query_string = row["query_string"] if "query_string" in row.keys() else None
    
    return SavedQuery(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        query_string=query_string,
        filters=row["filters"],
        target_type=row["target_type"],
        visibility=row["visibility"],
        owner_id=owner_id,
        owner_name=owner_name,
        is_favorite=bool(fav) or is_favorite,
        run_count=run_count,
        last_run_at=last_run,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        tags=tags,
        parameters=parameters,
    )


def _get_current_user() -> tuple[str, str]:
    """Get current user ID and name. Placeholder for auth integration."""
    return ("default_user", "Default User")


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
    user_id, user_name = _get_current_user()
    
    # Get original query (must be accessible)
    cursor = db.execute(
        """
        SELECT * FROM saved_queries
        WHERE id = ? AND (created_by = ? OR visibility IN ('public', 'team'))
        """,
        (query_id, user_id),
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
            user_id,
            now,
            now,
        ),
    )
    db.commit()
    
    # Fetch and return
    cursor = db.execute("SELECT * FROM saved_queries WHERE id = ?", (fork_id,))
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    return _row_to_query(row)


# Alias for clone (same as fork)
@router.post("/{query_id}/clone", response_model=SavedQuery, status_code=201)
async def clone_saved_query(
    query_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Clone a query to create a personal copy (alias for fork)."""
    return await fork_saved_query(query_id, None, db)


@router.post("/{query_id}/favorite", response_model=SavedQuery)
async def favorite_query(
    query_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Mark a query as favorite."""
    _ensure_schema(db)
    
    db.execute(
        "UPDATE saved_queries SET is_favorite = 1 WHERE id = ?",
        (query_id,),
    )
    db.commit()
    
    cursor = db.execute("SELECT * FROM saved_queries WHERE id = ?", (query_id,))
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    
    return _row_to_query(row, is_favorite=True)


@router.delete("/{query_id}/favorite", response_model=SavedQuery)
async def unfavorite_query(
    query_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Remove a query from favorites."""
    _ensure_schema(db)
    
    db.execute(
        "UPDATE saved_queries SET is_favorite = 0 WHERE id = ?",
        (query_id,),
    )
    db.commit()
    
    cursor = db.execute("SELECT * FROM saved_queries WHERE id = ?", (query_id,))
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    
    return _row_to_query(row)


@router.get("/favorites", response_model=List[SavedQuery])
async def get_favorite_queries(
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get all favorite queries for the current user."""
    _ensure_schema(db)
    user_id, _ = _get_current_user()
    
    cursor = db.execute(
        """
        SELECT * FROM saved_queries
        WHERE is_favorite = 1 AND created_by = ?
        ORDER BY updated_at DESC
        """,
        (user_id,),
    )
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    return [_row_to_query(row) for row in rows]


@router.get("/stats", response_model=QueryStats)
async def get_query_stats(
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get query statistics."""
    _ensure_schema(db)
    
    total = db.execute("SELECT COUNT(*) FROM saved_queries").fetchone()[0]
    public = db.execute("SELECT COUNT(*) FROM saved_queries WHERE visibility = 'public'").fetchone()[0]
    team = db.execute("SELECT COUNT(*) FROM saved_queries WHERE visibility = 'team'").fetchone()[0]
    private = db.execute("SELECT COUNT(*) FROM saved_queries WHERE visibility = 'private'").fetchone()[0]
    
    # Queries run today/week
    today = datetime.utcnow().date().isoformat()
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    
    try:
        today_count = db.execute(
            "SELECT COUNT(*) FROM query_history WHERE run_at >= ?",
            (today,)
        ).fetchone()[0]
        
        week_count = db.execute(
            "SELECT COUNT(*) FROM query_history WHERE run_at >= ?",
            (week_ago,)
        ).fetchone()[0]
    except sqlite3.OperationalError:
        today_count = 0
        week_count = 0
    
    # Popular tags
    try:
        cursor = db.execute("SELECT tags FROM saved_queries WHERE tags IS NOT NULL AND tags != '[]'")
        tag_counts: Dict[str, int] = {}
        for row in cursor.fetchall():
            try:
                for tag in json.loads(row[0]):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except (json.JSONDecodeError, TypeError):
                pass
        popular_tags = sorted(
            [{"tag": k, "count": v} for k, v in tag_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]
    except sqlite3.OperationalError:
        popular_tags = []
    
    # Top queries by run count
    try:
        cursor = db.execute(
            """
            SELECT id, name, run_count, created_by as owner_name
            FROM saved_queries
            WHERE run_count > 0
            ORDER BY run_count DESC
            LIMIT 10
            """
        )
        top_queries = [
            {"id": row[0], "name": row[1], "run_count": row[2], "owner_name": row[3]}
            for row in cursor.fetchall()
        ]
    except sqlite3.OperationalError:
        top_queries = []
    
    return QueryStats(
        total_queries=total,
        public_queries=public,
        team_queries=team,
        private_queries=private,
        queries_run_today=today_count,
        queries_run_this_week=week_count,
        popular_tags=popular_tags,
        top_queries=top_queries,
    )


@router.get("/history")
async def get_query_history(
    limit: int = Query(20, le=100),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get recent query execution history."""
    _ensure_schema(db)
    user_id, _ = _get_current_user()
    
    try:
        cursor = db.execute(
            """
            SELECT qh.query_id, sq.name as query_name, qh.run_at
            FROM query_history qh
            JOIN saved_queries sq ON qh.query_id = sq.id
            WHERE qh.user_id = ?
            ORDER BY qh.run_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        return [
            {"query_id": row[0], "query_name": row[1], "run_at": row[2]}
            for row in cursor.fetchall()
        ]
    except sqlite3.OperationalError:
        return []


@router.post("/run", response_model=QueryResult)
async def run_query(
    data: RunQueryRequest,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Execute a saved or ad-hoc query."""
    _ensure_schema(db)
    user_id, _ = _get_current_user()
    
    query_string = data.query_string
    query_id = data.query_id
    
    # If query_id provided, fetch the query
    if query_id and not query_string:
        cursor = db.execute(
            "SELECT query_string, filters FROM saved_queries WHERE id = ?",
            (query_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
        query_string = row[0] or row[1]  # Use query_string or filters
    
    if not query_string:
        raise HTTPException(status_code=400, detail="No query string provided")
    
    # For safety, only allow SELECT queries
    query_lower = query_string.strip().lower()
    if not query_lower.startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed")
    
    # Add limit if not present
    if "limit" not in query_lower:
        query_string = f"{query_string} LIMIT {data.limit}"
    
    start_time = time.time()
    
    try:
        cursor = db.execute(query_string)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = []
        for row in cursor.fetchall():
            rows.append(dict(zip(columns, row)))
        
        execution_time = (time.time() - start_time) * 1000
        truncated = len(rows) >= data.limit
        
        # Record in history if saved query
        if query_id:
            history_id = str(uuid.uuid4())
            try:
                db.execute(
                    "INSERT INTO query_history (id, query_id, user_id, execution_time_ms, row_count) VALUES (?, ?, ?, ?, ?)",
                    (history_id, query_id, user_id, execution_time, len(rows)),
                )
                db.execute(
                    "UPDATE saved_queries SET run_count = run_count + 1, last_run_at = ? WHERE id = ?",
                    (datetime.utcnow().isoformat(), query_id),
                )
                db.commit()
            except sqlite3.OperationalError:
                pass  # History table may not exist
        
        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_time_ms=round(execution_time, 2),
            truncated=truncated,
        )
        
    except sqlite3.Error as e:
        raise HTTPException(status_code=400, detail=f"Query error: {e}")
