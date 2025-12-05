"""
QA Ratings API routes.

Provides endpoints for rating sources and images with star ratings and quality flags.
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

router = APIRouter(prefix="/ratings", tags=["ratings"])


# ============================================================================
# Pydantic Models
# ============================================================================

RatingTarget = Literal["source", "image"]
RatingCategory = Literal["overall", "flux", "morphology", "position", "calibration"]
QualityFlag = Literal["good", "uncertain", "bad", "needs_review"]


class Rating(BaseModel):
    """A rating record."""

    id: str
    target_type: RatingTarget
    target_id: str
    user_id: str
    username: str
    category: RatingCategory
    value: int = Field(..., ge=1, le=5)
    flag: QualityFlag
    comment: Optional[str] = None
    created_at: str
    updated_at: str


class RatingSubmission(BaseModel):
    """Input for submitting a rating."""

    target_type: RatingTarget
    target_id: str
    category: RatingCategory = "overall"
    value: int = Field(..., ge=1, le=5)
    flag: QualityFlag = "good"
    comment: Optional[str] = None


class RatingSummary(BaseModel):
    """Summary of ratings for a target."""

    target_type: RatingTarget
    target_id: str
    category: RatingCategory
    average_rating: float
    rating_count: int
    flag_distribution: Dict[str, int]
    recent_ratings: List[Rating]


class TargetRatingSummary(BaseModel):
    """Complete rating summary for a target across all categories."""

    target_type: RatingTarget
    target_id: str
    overall_average: float
    total_ratings: int
    categories: Dict[str, Dict[str, Any]]
    primary_flag: QualityFlag
    needs_attention: bool


class RatingStats(BaseModel):
    """Global rating statistics."""

    total_ratings: int
    sources_rated: int
    images_rated: int
    average_rating: float
    ratings_today: int
    ratings_this_week: int
    top_raters: List[Dict[str, Any]]
    flag_distribution: Dict[str, int]


class QueueItem(BaseModel):
    """Item in the rating queue."""

    target_type: RatingTarget
    target_id: str
    name: str
    priority: Literal["high", "medium", "low"]
    reason: str
    created_at: str


class QueueListResponse(BaseModel):
    """Response for rating queue."""

    items: List[QueueItem]
    total: int


# ============================================================================
# Database Schema
# ============================================================================

RATINGS_SCHEMA = """
CREATE TABLE IF NOT EXISTS qa_ratings (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL CHECK (target_type IN ('source', 'image')),
    target_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'overall',
    value INTEGER NOT NULL CHECK (value >= 1 AND value <= 5),
    flag TEXT NOT NULL DEFAULT 'good',
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(target_type, target_id, user_id, category)
);

CREATE TABLE IF NOT EXISTS rating_queue (
    id TEXT PRIMARY KEY,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    name TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'medium',
    reason TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(target_type, target_id)
);

CREATE INDEX IF NOT EXISTS idx_ratings_target ON qa_ratings(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_ratings_user ON qa_ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_ratings_created ON qa_ratings(created_at);
"""


def _ensure_schema(db: sqlite3.Connection):
    """Ensure rating tables exist."""
    db.executescript(RATINGS_SCHEMA)
    db.commit()


def _row_to_rating(row: sqlite3.Row) -> Rating:
    """Convert database row to Rating model."""
    return Rating(
        id=row["id"],
        target_type=row["target_type"],
        target_id=row["target_id"],
        user_id=row["user_id"],
        username=row["username"],
        category=row["category"],
        value=row["value"],
        flag=row["flag"],
        comment=row["comment"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _get_current_user() -> tuple[str, str]:
    """Get current user ID and username. Placeholder for auth integration."""
    return ("default_user", "Default User")


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/stats", response_model=RatingStats)
async def get_rating_stats(
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get global rating statistics."""
    _ensure_schema(db)

    # Total ratings
    total = db.execute("SELECT COUNT(*) FROM qa_ratings").fetchone()[0]

    # Sources and images rated
    sources = db.execute(
        "SELECT COUNT(DISTINCT target_id) FROM qa_ratings WHERE target_type = 'source'"
    ).fetchone()[0]
    images = db.execute(
        "SELECT COUNT(DISTINCT target_id) FROM qa_ratings WHERE target_type = 'image'"
    ).fetchone()[0]

    # Average rating
    avg_result = db.execute("SELECT AVG(value) FROM qa_ratings").fetchone()[0]
    avg_rating = float(avg_result) if avg_result else 0.0

    # Today and this week
    today = datetime.utcnow().date().isoformat()
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()

    today_count = db.execute(
        "SELECT COUNT(*) FROM qa_ratings WHERE created_at >= ?", (today,)
    ).fetchone()[0]

    week_count = db.execute(
        "SELECT COUNT(*) FROM qa_ratings WHERE created_at >= ?", (week_ago,)
    ).fetchone()[0]

    # Top raters
    cursor = db.execute("""
        SELECT user_id, username, COUNT(*) as rating_count
        FROM qa_ratings
        GROUP BY user_id, username
        ORDER BY rating_count DESC
        LIMIT 10
    """)
    top_raters = [
        {"user_id": row[0], "username": row[1], "rating_count": row[2]} for row in cursor.fetchall()
    ]

    # Flag distribution
    cursor = db.execute("""
        SELECT flag, COUNT(*) as count
        FROM qa_ratings
        GROUP BY flag
    """)
    flag_dist = {row[0]: row[1] for row in cursor.fetchall()}

    return RatingStats(
        total_ratings=total,
        sources_rated=sources,
        images_rated=images,
        average_rating=round(avg_rating, 2),
        ratings_today=today_count,
        ratings_this_week=week_count,
        top_raters=top_raters,
        flag_distribution=flag_dist,
    )


@router.get("/queue", response_model=QueueListResponse)
async def get_rating_queue(
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(50, le=200),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get items in the rating queue."""
    _ensure_schema(db)

    sql = "SELECT * FROM rating_queue"
    params: List[Any] = []

    if priority:
        sql += " WHERE priority = ?"
        params.append(priority)

    sql += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC"
    sql += " LIMIT ?"
    params.append(limit)

    cursor = db.execute(sql, params)
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()

    items = [
        QueueItem(
            target_type=row["target_type"],
            target_id=row["target_id"],
            name=row["name"],
            priority=row["priority"],
            reason=row["reason"] or "",
            created_at=row["created_at"],
        )
        for row in rows
    ]

    return QueueListResponse(items=items, total=len(items))


@router.post("/queue/{target_type}/{target_id}", status_code=204)
async def remove_from_queue(
    target_type: RatingTarget,
    target_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Remove an item from the rating queue (after rating)."""
    _ensure_schema(db)

    db.execute(
        "DELETE FROM rating_queue WHERE target_type = ? AND target_id = ?",
        (target_type, target_id),
    )
    db.commit()


@router.get("/user", response_model=List[Rating])
async def get_user_ratings(
    user_id: Optional[str] = Query(None, description="User ID (defaults to current user)"),
    limit: int = Query(50, le=200),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get ratings by a specific user."""
    _ensure_schema(db)

    current_user_id, _ = _get_current_user()
    target_user = user_id or current_user_id

    cursor = db.execute(
        """
        SELECT * FROM qa_ratings
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (target_user, limit),
    )
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()

    return [_row_to_rating(row) for row in rows]


@router.get("/{target_type}/{target_id}", response_model=List[Rating])
async def get_ratings(
    target_type: RatingTarget,
    target_id: str,
    category: Optional[RatingCategory] = Query(None),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get all ratings for a specific target."""
    _ensure_schema(db)

    sql = "SELECT * FROM qa_ratings WHERE target_type = ? AND target_id = ?"
    params: List[Any] = [target_type, target_id]

    if category:
        sql += " AND category = ?"
        params.append(category)

    sql += " ORDER BY created_at DESC"

    cursor = db.execute(sql, params)
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()

    return [_row_to_rating(row) for row in rows]


@router.get("/{target_type}/{target_id}/summary", response_model=RatingSummary)
async def get_rating_summary(
    target_type: RatingTarget,
    target_id: str,
    category: RatingCategory = Query("overall"),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get rating summary for a target in a specific category."""
    _ensure_schema(db)

    # Get ratings for this category
    cursor = db.execute(
        """
        SELECT * FROM qa_ratings
        WHERE target_type = ? AND target_id = ? AND category = ?
        ORDER BY created_at DESC
        """,
        (target_type, target_id, category),
    )
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()

    ratings = [_row_to_rating(row) for row in rows]

    # Calculate stats
    if ratings:
        avg = sum(r.value for r in ratings) / len(ratings)
        flag_dist = {}
        for r in ratings:
            flag_dist[r.flag] = flag_dist.get(r.flag, 0) + 1
    else:
        avg = 0.0
        flag_dist = {}

    return RatingSummary(
        target_type=target_type,
        target_id=target_id,
        category=category,
        average_rating=round(avg, 2),
        rating_count=len(ratings),
        flag_distribution=flag_dist,
        recent_ratings=ratings[:5],
    )


@router.get("/{target_type}/{target_id}/complete-summary", response_model=TargetRatingSummary)
async def get_complete_summary(
    target_type: RatingTarget,
    target_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get complete rating summary across all categories."""
    _ensure_schema(db)

    cursor = db.execute(
        """
        SELECT category, AVG(value) as avg, COUNT(*) as count
        FROM qa_ratings
        WHERE target_type = ? AND target_id = ?
        GROUP BY category
        """,
        (target_type, target_id),
    )

    categories = {}
    total_count = 0
    total_sum = 0.0

    for row in cursor.fetchall():
        categories[row[0]] = {"average": round(row[1], 2), "count": row[2]}
        total_count += row[2]
        total_sum += row[1] * row[2]

    overall_avg = round(total_sum / total_count, 2) if total_count > 0 else 0.0

    # Get primary flag (most common)
    cursor = db.execute(
        """
        SELECT flag, COUNT(*) as count
        FROM qa_ratings
        WHERE target_type = ? AND target_id = ?
        GROUP BY flag
        ORDER BY count DESC
        LIMIT 1
        """,
        (target_type, target_id),
    )
    row = cursor.fetchone()
    primary_flag = row[0] if row else "good"

    # Needs attention if any bad/needs_review flags or low ratings
    needs_attention = primary_flag in ("bad", "needs_review") or overall_avg < 2.5

    return TargetRatingSummary(
        target_type=target_type,
        target_id=target_id,
        overall_average=overall_avg,
        total_ratings=total_count,
        categories=categories,
        primary_flag=primary_flag,
        needs_attention=needs_attention,
    )


@router.post("", response_model=Rating, status_code=201)
async def submit_rating(
    data: RatingSubmission,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Submit or update a rating."""
    _ensure_schema(db)

    user_id, username = _get_current_user()
    now = datetime.utcnow().isoformat()

    # Check if rating exists (upsert)
    cursor = db.execute(
        """
        SELECT id FROM qa_ratings
        WHERE target_type = ? AND target_id = ? AND user_id = ? AND category = ?
        """,
        (data.target_type, data.target_id, user_id, data.category),
    )
    existing = cursor.fetchone()

    if existing:
        # Update
        rating_id = existing[0]
        db.execute(
            """
            UPDATE qa_ratings
            SET value = ?, flag = ?, comment = ?, updated_at = ?
            WHERE id = ?
            """,
            (data.value, data.flag, data.comment, now, rating_id),
        )
    else:
        # Insert
        rating_id = str(uuid.uuid4())
        db.execute(
            """
            INSERT INTO qa_ratings (id, target_type, target_id, user_id, username, category, value, flag, comment, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rating_id,
                data.target_type,
                data.target_id,
                user_id,
                username,
                data.category,
                data.value,
                data.flag,
                data.comment,
                now,
                now,
            ),
        )

    db.commit()

    # Remove from queue if present
    db.execute(
        "DELETE FROM rating_queue WHERE target_type = ? AND target_id = ?",
        (data.target_type, data.target_id),
    )
    db.commit()

    # Fetch and return
    cursor = db.execute("SELECT * FROM qa_ratings WHERE id = ?", (rating_id,))
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()

    return _row_to_rating(row)


@router.delete("/{rating_id}", status_code=204)
async def delete_rating(
    rating_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Delete a rating (owner only)."""
    _ensure_schema(db)

    user_id, _ = _get_current_user()

    # Check ownership
    cursor = db.execute(
        "SELECT user_id FROM qa_ratings WHERE id = ?",
        (rating_id,),
    )
    row = cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Rating not found")

    if row[0] != user_id:
        raise HTTPException(status_code=403, detail="Cannot delete another user's rating")

    db.execute("DELETE FROM qa_ratings WHERE id = ?", (rating_id,))
    db.commit()
