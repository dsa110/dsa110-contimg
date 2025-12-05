"""
Comments API routes.

Provides endpoints for user comments on sources, images, observations, jobs, and MS.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..dependencies import get_pipeline_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/comments", tags=["comments"])


# ============================================================================
# Pydantic Models
# ============================================================================

CommentTarget = Literal["source", "image", "observation", "job", "ms"]


class Comment(BaseModel):
    """A comment record."""

    id: str
    target_type: CommentTarget
    target_id: str
    user_id: str
    username: str
    content: str
    is_pinned: bool = False
    is_resolved: bool = False
    parent_id: Optional[str] = None
    reply_count: int = 0
    created_at: str
    updated_at: str


class CreateCommentRequest(BaseModel):
    """Input for creating a comment."""

    target_type: CommentTarget
    target_id: str
    content: str = Field(..., min_length=1, max_length=10000)
    parent_id: Optional[str] = None


class UpdateCommentRequest(BaseModel):
    """Input for updating a comment."""

    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    is_pinned: Optional[bool] = None
    is_resolved: Optional[bool] = None


class CommentThread(BaseModel):
    """A comment with its replies."""

    comment: Comment
    replies: List[Comment]


class CommentStats(BaseModel):
    """Comment statistics."""

    total_comments: int
    pinned_comments: int
    resolved_comments: int
    active_threads: int
    comments_today: int
    comments_this_week: int
    top_commenters: List[Dict[str, Any]]
    target_distribution: Dict[str, int]


class MentionableUser(BaseModel):
    """User that can be mentioned."""

    user_id: str
    username: str
    email: Optional[str] = None


class CommentListResponse(BaseModel):
    """Response for listing comments."""

    comments: List[Comment]
    total: int


# ============================================================================
# Database Schema
# ============================================================================

COMMENTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_comments (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL CHECK (target_type IN ('source', 'image', 'observation', 'job', 'ms')),
    target_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    content TEXT NOT NULL,
    is_pinned INTEGER DEFAULT 0,
    is_resolved INTEGER DEFAULT 0,
    parent_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (parent_id) REFERENCES user_comments(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_comments_target ON user_comments(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_comments_user ON user_comments(user_id);
CREATE INDEX IF NOT EXISTS idx_comments_parent ON user_comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_comments_pinned ON user_comments(is_pinned);
"""


def _ensure_schema(db: sqlite3.Connection):
    """Ensure comment tables exist."""
    db.executescript(COMMENTS_SCHEMA)
    db.commit()


def _row_to_comment(row: sqlite3.Row, reply_count: int = 0) -> Comment:
    """Convert database row to Comment model."""
    return Comment(
        id=row["id"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        user_id=row["user_id"],
        username=row["username"],
        content=row["content"],
        is_pinned=bool(row["is_pinned"]),
        is_resolved=bool(row["is_resolved"]),
        parent_id=row["parent_id"],
        reply_count=reply_count,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_current_user() -> tuple[str, str]:
    """Get current user ID and username. Placeholder for auth integration."""
    return ("default_user", "Default User")


def _get_reply_counts(db: sqlite3.Connection, comment_ids: List[str]) -> Dict[str, int]:
    """Get reply counts for a list of comments."""
    if not comment_ids:
        return {}

    placeholders = ",".join("?" * len(comment_ids))
    cursor = db.execute(
        f"""
        SELECT parent_id, COUNT(*) as count
        FROM user_comments
        WHERE parent_id IN ({placeholders})
        GROUP BY parent_id
        """,
        comment_ids,
    )
    return {row[0]: row[1] for row in cursor.fetchall()}


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/stats", response_model=CommentStats)
async def get_comment_stats(
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get comment statistics."""
    _ensure_schema(db)

    total = db.execute("SELECT COUNT(*) FROM user_comments").fetchone()[0]
    pinned = db.execute("SELECT COUNT(*) FROM user_comments WHERE is_pinned = 1").fetchone()[0]
    resolved = db.execute("SELECT COUNT(*) FROM user_comments WHERE is_resolved = 1").fetchone()[0]

    # Active threads (top-level comments with replies)
    active = db.execute("""
        SELECT COUNT(DISTINCT parent_id)
        FROM user_comments
        WHERE parent_id IS NOT NULL
    """).fetchone()[0]

    # Today and this week
    today = datetime.utcnow().date().isoformat()
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

    today_count = db.execute(
        "SELECT COUNT(*) FROM user_comments WHERE created_at >= ?", (today,)
    ).fetchone()[0]

    week_count = db.execute(
        "SELECT COUNT(*) FROM user_comments WHERE created_at >= ?", (week_ago,)
    ).fetchone()[0]

    # Top commenters
    cursor = db.execute("""
        SELECT user_id, username, COUNT(*) as comment_count
        FROM user_comments
        GROUP BY user_id, username
        ORDER BY comment_count DESC
        LIMIT 10
    """)
    top_commenters = [
        {"user_id": row[0], "username": row[1], "comment_count": row[2]}
        for row in cursor.fetchall()
    ]

    # Target distribution
    cursor = db.execute("""
        SELECT target_type, COUNT(*) as count
        FROM user_comments
        GROUP BY target_type
    """)
    target_dist = {row[0]: row[1] for row in cursor.fetchall()}

    return CommentStats(
        total_comments=total,
        pinned_comments=pinned,
        resolved_comments=resolved,
        active_threads=active,
        comments_today=today_count,
        comments_this_week=week_count,
        top_commenters=top_commenters,
        target_distribution=target_dist,
    )


@router.get("/users", response_model=List[MentionableUser])
async def get_mentionable_users(
    search: Optional[str] = Query(None, description="Search by username"),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get users that can be mentioned in comments."""
    _ensure_schema(db)

    # Get unique users from comments
    if search:
        cursor = db.execute(
            """
            SELECT DISTINCT user_id, username
            FROM user_comments
            WHERE username LIKE ?
            ORDER BY username
            LIMIT 20
            """,
            (f"%{search}%",),
        )
    else:
        cursor = db.execute(
            """
            SELECT DISTINCT user_id, username
            FROM user_comments
            ORDER BY username
            LIMIT 50
            """
        )

    return [MentionableUser(user_id=row[0], username=row[1]) for row in cursor.fetchall()]


@router.get("", response_model=CommentListResponse)
async def list_comments(
    target_type: Optional[CommentTarget] = Query(None),
    target_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    is_pinned: Optional[bool] = Query(None),
    is_resolved: Optional[bool] = Query(None),
    parent_id: Optional[str] = Query(
        None, description="Filter by parent (use 'null' for top-level)"
    ),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """List comments with filtering and pagination."""
    _ensure_schema(db)

    conditions = []
    params: List[Any] = []

    if target_type:
        conditions.append("target_type = ?")
        params.append(target_type)

    if target_id:
        conditions.append("target_id = ?")
        params.append(target_id)

    if user_id:
        conditions.append("user_id = ?")
        params.append(user_id)

    if search:
        conditions.append("content LIKE ?")
        params.append(f"%{search}%")

    if is_pinned is not None:
        conditions.append("is_pinned = ?")
        params.append(1 if is_pinned else 0)

    if is_resolved is not None:
        conditions.append("is_resolved = ?")
        params.append(1 if is_resolved else 0)

    if parent_id == "null":
        conditions.append("parent_id IS NULL")
    elif parent_id:
        conditions.append("parent_id = ?")
        params.append(parent_id)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    # Validate sort
    valid_sorts = {"created_at", "updated_at"}
    if sort_by not in valid_sorts:
        sort_by = "created_at"
    order = "DESC" if sort_order.lower() == "desc" else "ASC"

    sql = f"""
        SELECT * FROM user_comments
        WHERE {where_clause}
        ORDER BY {sort_by} {order}
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    cursor = db.execute(sql, params)
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()

    # Get reply counts
    comment_ids = [row["id"] for row in rows]
    reply_counts = _get_reply_counts(db, comment_ids)

    comments = [_row_to_comment(row, reply_counts.get(row["id"], 0)) for row in rows]

    # Get total count
    count_sql = f"SELECT COUNT(*) FROM user_comments WHERE {where_clause}"
    total = db.execute(count_sql, params[:-2]).fetchone()[0]

    return CommentListResponse(comments=comments, total=total)


@router.get("/{comment_id}", response_model=Comment)
async def get_comment(
    comment_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get a specific comment."""
    _ensure_schema(db)

    cursor = db.execute(
        "SELECT * FROM user_comments WHERE id = ?",
        (comment_id,),
    )
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Comment not found")

    reply_count = db.execute(
        "SELECT COUNT(*) FROM user_comments WHERE parent_id = ?", (comment_id,)
    ).fetchone()[0]

    return _row_to_comment(row, reply_count)


@router.get("/{comment_id}/thread", response_model=CommentThread)
async def get_comment_thread(
    comment_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get a comment with all its replies."""
    _ensure_schema(db)

    # Get parent comment
    cursor = db.execute(
        "SELECT * FROM user_comments WHERE id = ?",
        (comment_id,),
    )
    cursor.row_factory = sqlite3.Row
    parent_row = cursor.fetchone()

    if not parent_row:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Get replies
    cursor = db.execute(
        """
        SELECT * FROM user_comments
        WHERE parent_id = ?
        ORDER BY created_at ASC
        """,
        (comment_id,),
    )
    cursor.row_factory = sqlite3.Row
    reply_rows = cursor.fetchall()

    replies = [_row_to_comment(row, 0) for row in reply_rows]
    parent = _row_to_comment(parent_row, len(replies))

    return CommentThread(comment=parent, replies=replies)


@router.post("", response_model=Comment, status_code=201)
async def create_comment(
    data: CreateCommentRequest,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Create a new comment."""
    _ensure_schema(db)

    user_id, username = _get_current_user()
    comment_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Verify parent exists if provided
    if data.parent_id:
        cursor = db.execute(
            "SELECT id FROM user_comments WHERE id = ?",
            (data.parent_id,),
        )
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Parent comment not found")

    db.execute(
        """
        INSERT INTO user_comments (id, target_type, target_id, user_id, username, content, parent_id, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            comment_id,
            data.target_type,
            data.target_id,
            user_id,
            username,
            data.content,
            data.parent_id,
            now,
            now,
        ),
    )
    db.commit()

    return Comment(
        id=comment_id,
        target_type=data.target_type,
        target_id=data.target_id,
        user_id=user_id,
        username=username,
        content=data.content,
        is_pinned=False,
        is_resolved=False,
        parent_id=data.parent_id,
        reply_count=0,
        created_at=now,
        updated_at=now,
    )


@router.patch("/{comment_id}", response_model=Comment)
async def update_comment(
    comment_id: str,
    data: UpdateCommentRequest,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Update a comment."""
    _ensure_schema(db)

    user_id, _ = _get_current_user()

    # Get existing comment
    cursor = db.execute(
        "SELECT * FROM user_comments WHERE id = ?",
        (comment_id,),
    )
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Only owner can update content
    if data.content is not None and row["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Cannot update another user's comment")

    # Build update
    updates = []
    params: List[Any] = []

    if data.content is not None:
        updates.append("content = ?")
        params.append(data.content)

    if data.is_pinned is not None:
        updates.append("is_pinned = ?")
        params.append(1 if data.is_pinned else 0)

    if data.is_resolved is not None:
        updates.append("is_resolved = ?")
        params.append(1 if data.is_resolved else 0)

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    updates.append("updated_at = ?")
    params.append(datetime.utcnow().isoformat())
    params.append(comment_id)

    db.execute(
        f"UPDATE user_comments SET {', '.join(updates)} WHERE id = ?",
        params,
    )
    db.commit()

    # Fetch updated
    cursor = db.execute(
        "SELECT * FROM user_comments WHERE id = ?",
        (comment_id,),
    )
    cursor.row_factory = sqlite3.Row
    updated_row = cursor.fetchone()

    reply_count = db.execute(
        "SELECT COUNT(*) FROM user_comments WHERE parent_id = ?", (comment_id,)
    ).fetchone()[0]

    return _row_to_comment(updated_row, reply_count)


@router.post("/{comment_id}/pin", response_model=Comment)
async def pin_comment(
    comment_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Pin a comment."""
    _ensure_schema(db)

    db.execute(
        "UPDATE user_comments SET is_pinned = 1, updated_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), comment_id),
    )
    db.commit()

    return await get_comment(comment_id, db)


@router.delete("/{comment_id}/pin", response_model=Comment)
async def unpin_comment(
    comment_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Unpin a comment."""
    _ensure_schema(db)

    db.execute(
        "UPDATE user_comments SET is_pinned = 0, updated_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), comment_id),
    )
    db.commit()

    return await get_comment(comment_id, db)


@router.post("/{comment_id}/resolve", response_model=Comment)
async def resolve_comment(
    comment_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Mark a comment as resolved."""
    _ensure_schema(db)

    db.execute(
        "UPDATE user_comments SET is_resolved = 1, updated_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), comment_id),
    )
    db.commit()

    return await get_comment(comment_id, db)


@router.delete("/{comment_id}/resolve", response_model=Comment)
async def unresolve_comment(
    comment_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Mark a comment as unresolved."""
    _ensure_schema(db)

    db.execute(
        "UPDATE user_comments SET is_resolved = 0, updated_at = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), comment_id),
    )
    db.commit()

    return await get_comment(comment_id, db)


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Delete a comment (owner only). Replies are also deleted."""
    _ensure_schema(db)

    user_id, _ = _get_current_user()

    cursor = db.execute(
        "SELECT user_id FROM user_comments WHERE id = ?",
        (comment_id,),
    )
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Comment not found")

    if row[0] != user_id:
        raise HTTPException(status_code=403, detail="Cannot delete another user's comment")

    # Delete comment and replies (CASCADE should handle this)
    db.execute("DELETE FROM user_comments WHERE id = ? OR parent_id = ?", (comment_id, comment_id))
    db.commit()
