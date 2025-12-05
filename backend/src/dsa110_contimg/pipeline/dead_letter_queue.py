"""Dead letter queue for failed operations.

Stores failed operations for manual review and retry.
Uses SQLite for persistence (cost-free).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class DLQStatus(Enum):
    """Dead letter queue status."""

    PENDING = "pending"
    RETRYING = "retrying"
    RESOLVED = "resolved"
    FAILED = "failed"


@dataclass
class DeadLetterQueueItem:
    """Dead letter queue item."""

    id: Optional[int]
    component: str
    operation: str
    error_type: str
    error_message: str
    context: Dict[str, Any]
    created_at: float
    retry_count: int
    status: DLQStatus
    resolved_at: Optional[float] = None
    resolution_note: Optional[str] = None


class DeadLetterQueue:
    """Dead letter queue for failed operations."""

    def __init__(self, db_path: Path):
        """Initialize dead letter queue.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self):
        """Create dead letter queue table if it doesn't exist."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dead_letter_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                component TEXT NOT NULL,
                operation TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT,
                context_json TEXT,
                created_at REAL NOT NULL,
                retry_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                resolved_at REAL,
                resolution_note TEXT
            )
        """
        )
        conn.commit()
        conn.close()

    def add(
        self,
        component: str,
        operation: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add failed operation to dead letter queue.

        Args:
            component: Component name (e.g., 'ese_detection', 'photometry')
            operation: Operation name (e.g., 'detect_candidates', 'measure_flux')
            error: Exception that occurred
            context: Additional context dictionary

        Returns:
            DLQ item ID
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            """
            INSERT INTO dead_letter_queue
            (component, operation, error_type, error_message, context_json, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                component,
                operation,
                type(error).__name__,
                str(error),
                json.dumps(context or {}),
                datetime.now().timestamp(),
                DLQStatus.PENDING.value,
            ),
        )
        item_id = cursor.lastrowid
        conn.commit()
        conn.close()
        # lastrowid can be None if no row was inserted, but INSERT always inserts
        # so this is safe; cast to satisfy type checker
        return item_id if item_id is not None else 0

    def get_pending(
        self, component: Optional[str] = None, limit: int = 100
    ) -> List[DeadLetterQueueItem]:
        """Get pending items from dead letter queue.

        Args:
            component: Filter by component (None for all)
            limit: Maximum number of items to return

        Returns:
            List of DLQ items
        """
        conn = sqlite3.connect(str(self.db_path))

        if component:
            cursor = conn.execute(
                """
                SELECT id, component, operation, error_type, error_message,
                       context_json, created_at, retry_count, status,
                       resolved_at, resolution_note
                FROM dead_letter_queue
                WHERE status = ? AND component = ?
                ORDER BY created_at ASC
                LIMIT ?
            """,
                (DLQStatus.PENDING.value, component, limit),
            )
        else:
            cursor = conn.execute(
                """
                SELECT id, component, operation, error_type, error_message,
                       context_json, created_at, retry_count, status,
                       resolved_at, resolution_note
                FROM dead_letter_queue
                WHERE status = ?
                ORDER BY created_at ASC
                LIMIT ?
            """,
                (DLQStatus.PENDING.value, limit),
            )

        items = []
        for row in cursor.fetchall():
            items.append(
                DeadLetterQueueItem(
                    id=row[0],
                    component=row[1],
                    operation=row[2],
                    error_type=row[3],
                    error_message=row[4],
                    context=json.loads(row[5]) if row[5] else {},
                    created_at=row[6],
                    retry_count=row[7],
                    status=DLQStatus(row[8]),
                    resolved_at=row[9],
                    resolution_note=row[10],
                )
            )

        conn.close()
        return items

    def mark_retrying(self, item_id: int):
        """Mark item as retrying."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            """
            SELECT retry_count FROM dead_letter_queue WHERE id = ?
        """,
            (item_id,),
        )
        row = cursor.fetchone()
        retry_count = (row[0] or 0) + 1 if row else 1

        conn.execute(
            """
            UPDATE dead_letter_queue
            SET status = ?, retry_count = ?
            WHERE id = ?
        """,
            (DLQStatus.RETRYING.value, retry_count, item_id),
        )
        conn.commit()
        conn.close()

    def mark_resolved(self, item_id: int, note: Optional[str] = None):
        """Mark item as resolved."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """
            UPDATE dead_letter_queue
            SET status = ?, resolved_at = ?, resolution_note = ?
            WHERE id = ?
        """,
            (DLQStatus.RESOLVED.value, datetime.now().timestamp(), note, item_id),
        )
        conn.commit()
        conn.close()

    def resolve(self, item_id: int, note: Optional[str] = None):
        """Alias for mark_resolved for API compatibility."""
        self.mark_resolved(item_id, note)

    def mark_failed(self, item_id: int, note: Optional[str] = None):
        """Mark item as permanently failed."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            """
            UPDATE dead_letter_queue
            SET status = ?, resolved_at = ?, resolution_note = ?
            WHERE id = ?
        """,
            (DLQStatus.FAILED.value, datetime.now().timestamp(), note, item_id),
        )
        conn.commit()
        conn.close()

    def get_by_id(self, item_id: int) -> Optional[DeadLetterQueueItem]:
        """Get a specific DLQ item by ID.

        Args:
            item_id: The item ID

        Returns:
            DeadLetterQueueItem if found, None otherwise
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            """
            SELECT id, component, operation, error_type, error_message,
                   context_json, created_at, retry_count, status,
                   resolved_at, resolution_note
            FROM dead_letter_queue
            WHERE id = ?
        """,
            (item_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        return DeadLetterQueueItem(
            id=row[0],
            component=row[1],
            operation=row[2],
            error_type=row[3],
            error_message=row[4],
            context=json.loads(row[5]) if row[5] else {},
            created_at=row[6],
            retry_count=row[7],
            status=DLQStatus(row[8]),
            resolved_at=row[9],
            resolution_note=row[10],
        )

    def delete(self, item_id: int) -> bool:
        """Delete a DLQ item permanently.

        Args:
            item_id: The item ID

        Returns:
            True if item was deleted, False if not found
        """
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "DELETE FROM dead_letter_queue WHERE id = ?",
            (item_id,),
        )
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get dead letter queue statistics."""
        conn = sqlite3.connect(str(self.db_path))

        cursor = conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'retrying' THEN 1 ELSE 0 END) as retrying,
                SUM(CASE WHEN status = 'resolved' THEN 1 ELSE 0 END) as resolved,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM dead_letter_queue
        """
        )
        row = cursor.fetchone()

        stats = {
            "total": row[0] or 0,
            "pending": row[1] or 0,
            "retrying": row[2] or 0,
            "resolved": row[3] or 0,
            "failed": row[4] or 0,
        }

        # Get counts by component
        cursor = conn.execute(
            """
            SELECT component, COUNT(*) as count
            FROM dead_letter_queue
            WHERE status = 'pending'
            GROUP BY component
            """
        )
        stats["by_component"] = {row[0]: row[1] for row in cursor.fetchall()}

        # Get counts by error type
        cursor = conn.execute(
            """
            SELECT error_type, COUNT(*) as count
            FROM dead_letter_queue
            WHERE status = 'pending'
            GROUP BY error_type
            """
        )
        stats["by_error_type"] = {row[0]: row[1] for row in cursor.fetchall()}

        conn.close()
        return stats


def get_dlq(db_path: Optional[Path] = None) -> DeadLetterQueue:
    """Get dead letter queue instance.

    Args:
        db_path: Path to database (defaults to products database)

    Returns:
        DeadLetterQueue instance
    """
    if db_path is None:
        import os

        products_db = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/db/products.sqlite3"))
        db_path = products_db

    return DeadLetterQueue(db_path)
