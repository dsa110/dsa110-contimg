"""Data registry database module.

Provides data registry tables and functions for tracking all data instances
through their lifecycle from staging to published.
"""

import os
import sqlite3
import json
import time
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class DataRecord:
    """Data registry record."""

    id: int
    data_type: str
    data_id: str
    base_path: str
    status: str  # 'staging' or 'published'
    stage_path: str
    published_path: Optional[str]
    created_at: float
    staged_at: float
    published_at: Optional[float]
    publish_mode: Optional[str]  # 'auto' or 'manual'
    metadata_json: Optional[str]
    qa_status: Optional[str]
    validation_status: Optional[str]
    finalization_status: str  # 'pending', 'finalized', 'failed'
    auto_publish_enabled: bool


def ensure_data_registry_db(path: Path) -> sqlite3.Connection:
    """Open or create the data registry SQLite DB and ensure schema exists.

    Tables:
      - data_registry: Central registry of all data instances
      - data_relationships: Relationships between data instances
      - data_tags: Tags for organization/search
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(os.fspath(path))

    # Data registry table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS data_registry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_type TEXT NOT NULL,
            data_id TEXT NOT NULL UNIQUE,
            base_path TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'staging',
            stage_path TEXT NOT NULL,
            published_path TEXT,
            created_at REAL NOT NULL,
            staged_at REAL NOT NULL,
            published_at REAL,
            publish_mode TEXT,
            metadata_json TEXT,
            qa_status TEXT,
            validation_status TEXT,
            finalization_status TEXT DEFAULT 'pending',
            auto_publish_enabled INTEGER DEFAULT 1,
            UNIQUE(data_type, data_id)
        )
        """
    )

    # Data relationships table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS data_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_data_id TEXT NOT NULL,
            child_data_id TEXT NOT NULL,
            relationship_type TEXT NOT NULL,
            FOREIGN KEY (parent_data_id) REFERENCES data_registry(data_id),
            FOREIGN KEY (child_data_id) REFERENCES data_registry(data_id),
            UNIQUE(parent_data_id, child_data_id, relationship_type)
        )
        """
    )

    # Data tags table
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS data_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_id TEXT NOT NULL,
            tag TEXT NOT NULL,
            FOREIGN KEY (data_id) REFERENCES data_registry(data_id),
            UNIQUE(data_id, tag)
        )
        """
    )

    # Indexes
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_data_registry_type_status ON data_registry(data_type, status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_data_registry_status ON data_registry(status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_data_registry_published_at ON data_registry(published_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_data_registry_finalization ON data_registry(finalization_status)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_data_relationships_parent ON data_relationships(parent_data_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_data_relationships_child ON data_relationships(child_data_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_data_tags_data_id ON data_tags(data_id)"
        )
    except Exception as e:
        logger.warning(f"Failed to create indexes: {e}")

    conn.commit()
    return conn


def register_data(
    conn: sqlite3.Connection,
    data_type: str,
    data_id: str,
    stage_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    auto_publish: bool = True,
) -> str:
    """Register a new data instance in the registry.

    Args:
        conn: Database connection
        data_type: Type of data ('ms', 'calib_ms', 'image', 'mosaic', etc.)
        data_id: Unique identifier for this data instance
        stage_path: Path in /stage/dsa110-contimg/
        metadata: Optional metadata dictionary (will be JSON-encoded)
        auto_publish: Whether auto-publish is enabled for this instance

    Returns:
        data_id (same as input)
    """
    now = time.time()
    metadata_json = json.dumps(metadata) if metadata else None

    conn.execute(
        """
        INSERT OR REPLACE INTO data_registry
        (data_type, data_id, base_path, status, stage_path, created_at, staged_at,
         metadata_json, auto_publish_enabled, finalization_status)
        VALUES (?, ?, ?, 'staging', ?, ?, ?, ?, ?, 'pending')
        """,
        (
            data_type,
            data_id,
            str(Path(stage_path).parent),  # base_path is parent directory
            stage_path,
            now,
            now,
            metadata_json,
            1 if auto_publish else 0,
        ),
    )
    conn.commit()
    return data_id


def finalize_data(
    conn: sqlite3.Connection,
    data_id: str,
    qa_status: Optional[str] = None,
    validation_status: Optional[str] = None,
) -> bool:
    """Mark data as finalized and trigger auto-publish if enabled and criteria met.

    Args:
        conn: Database connection
        data_id: Data instance ID
        qa_status: QA status ('pending', 'passed', 'failed', 'warning')
        validation_status: Validation status ('pending', 'validated', 'invalid')

    Returns:
        True if finalized (and possibly auto-published), False otherwise
    """
    cur = conn.cursor()

    # CRITICAL: Whitelist allowed column names to prevent SQL injection
    # Even though values are parameterized, column names must be whitelisted
    ALLOWED_UPDATE_COLUMNS = {
        "finalization_status",
        "qa_status",
        "validation_status",
    }

    # Update finalization status and QA/validation if provided
    updates = []
    params = []

    # Always set finalization_status
    updates.append("finalization_status = ?")
    params.append("finalized")

    # Add optional updates only if column is whitelisted
    if qa_status and "qa_status" in ALLOWED_UPDATE_COLUMNS:
        updates.append("qa_status = ?")
        params.append(qa_status)

    if validation_status and "validation_status" in ALLOWED_UPDATE_COLUMNS:
        updates.append("validation_status = ?")
        params.append(validation_status)

    # Add data_id for WHERE clause
    params.append(data_id)

    if updates:
        cur.execute(
            f"UPDATE data_registry SET {', '.join(updates)} WHERE data_id = ?",
            tuple(params),
        )

    # Check if auto-publish should be triggered
    cur.execute(
        """
        SELECT auto_publish_enabled, qa_status, validation_status, data_type, stage_path
        FROM data_registry
        WHERE data_id = ?
        """,
        (data_id,),
    )
    row = cur.fetchone()

    if not row:
        conn.commit()
        return False

    auto_enabled, qa, validation, dtype, stage_path = row

    if auto_enabled:
        # Check criteria (simplified - will be enhanced with config)
        should_publish = True
        if validation != "validated":
            should_publish = False

        # For science data types, require QA passed
        if dtype in ("image", "mosaic", "calib_ms", "caltable"):
            if qa != "passed":
                should_publish = False

        if should_publish:
            # Trigger auto-publish
            trigger_auto_publish(conn, data_id)
            conn.commit()
            return True

    conn.commit()
    return True


def trigger_auto_publish(
    conn: sqlite3.Connection,
    data_id: str,
    products_base: Optional[Path] = None,
) -> bool:
    """Trigger auto-publish for a data instance.

    Moves data from /stage/ (SSD) to /data/dsa110-contimg/products/ (HDD).

    Args:
        conn: Database connection
        data_id: Data instance ID
        products_base: Base path for published products (defaults to /data/dsa110-contimg/products)

    Returns:
        True if successful, False otherwise
    """
    if products_base is None:
        products_base = Path("/data/dsa110-contimg/products")

    cur = conn.cursor()
    cur.execute(
        """
        SELECT data_type, stage_path, base_path
        FROM data_registry
        WHERE data_id = ? AND status = 'staging'
        """,
        (data_id,),
    )
    row = cur.fetchone()

    if not row:
        logger.warning(f"Data {data_id} not found or already published")
        return False

    data_type, stage_path, base_path = row

    # Determine published path based on data type
    type_to_dir = {
        "ms": "ms",
        "calib_ms": "calib_ms",
        "caltable": "caltables",
        "image": "images",
        "mosaic": "mosaics",
        "catalog": "catalogs",
        "qa": "qa",
        "metadata": "metadata",
    }

    type_dir = type_to_dir.get(data_type, "misc")
    published_dir = products_base / type_dir
    published_dir.mkdir(parents=True, exist_ok=True)

    # Move data (preserve directory structure)
    stage_path_obj = Path(stage_path)
    if not stage_path_obj.exists():
        logger.error(f"Stage path does not exist: {stage_path}")
        return False

    # Published path maintains same structure
    published_path = published_dir / stage_path_obj.name

    try:
        # Move directory/file
        if stage_path_obj.is_dir():
            shutil.move(str(stage_path_obj), str(published_path))
        else:
            published_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(stage_path_obj), str(published_path))

        # Update database
        now = time.time()
        cur.execute(
            """
            UPDATE data_registry
            SET status = 'published',
                published_path = ?,
                published_at = ?,
                publish_mode = 'auto'
            WHERE data_id = ?
            """,
            (str(published_path), now, data_id),
        )
        conn.commit()

        logger.info(f"Auto-published {data_id} from {stage_path} to {published_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to auto-publish {data_id}: {e}")
        conn.rollback()
        return False


def publish_data_manual(
    conn: sqlite3.Connection,
    data_id: str,
    products_base: Optional[Path] = None,
) -> bool:
    """Manually publish data (user-initiated).

    Args:
        conn: Database connection
        data_id: Data instance ID
        products_base: Base path for published products

    Returns:
        True if successful, False otherwise
    """
    if products_base is None:
        products_base = Path("/data/dsa110-contimg/products")

    cur = conn.cursor()
    cur.execute(
        """
        SELECT data_type, stage_path
        FROM data_registry
        WHERE data_id = ? AND status = 'staging'
        """,
        (data_id,),
    )
    row = cur.fetchone()

    if not row:
        logger.warning(f"Data {data_id} not found or already published")
        return False

    data_type, stage_path = row

    # Use same logic as auto-publish for path determination
    type_to_dir = {
        "ms": "ms",
        "calib_ms": "calib_ms",
        "caltable": "caltables",
        "image": "images",
        "mosaic": "mosaics",
        "catalog": "catalogs",
        "qa": "qa",
        "metadata": "metadata",
    }

    type_dir = type_to_dir.get(data_type, "misc")
    published_dir = products_base / type_dir
    published_dir.mkdir(parents=True, exist_ok=True)

    stage_path_obj = Path(stage_path)
    if not stage_path_obj.exists():
        logger.error(f"Stage path does not exist: {stage_path}")
        return False

    published_path = published_dir / stage_path_obj.name

    try:
        if stage_path_obj.is_dir():
            shutil.move(str(stage_path_obj), str(published_path))
        else:
            published_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(stage_path_obj), str(published_path))

        now = time.time()
        cur.execute(
            """
            UPDATE data_registry
            SET status = 'published',
                published_path = ?,
                published_at = ?,
                publish_mode = 'manual'
            WHERE data_id = ?
            """,
            (str(published_path), now, data_id),
        )
        conn.commit()

        logger.info(
            f"Manually published {data_id} from {stage_path} to {published_path}"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to manually publish {data_id}: {e}")
        conn.rollback()
        return False


def get_data(conn: sqlite3.Connection, data_id: str) -> Optional[DataRecord]:
    """Get a data record by ID."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, data_type, data_id, base_path, status, stage_path, published_path,
               created_at, staged_at, published_at, publish_mode, metadata_json,
               qa_status, validation_status, finalization_status, auto_publish_enabled
        FROM data_registry
        WHERE data_id = ?
        """,
        (data_id,),
    )
    row = cur.fetchone()

    if not row:
        return None

    return DataRecord(
        id=row[0],
        data_type=row[1],
        data_id=row[2],
        base_path=row[3],
        status=row[4],
        stage_path=row[5],
        published_path=row[6],
        created_at=row[7],
        staged_at=row[8],
        published_at=row[9],
        publish_mode=row[10],
        metadata_json=row[11],
        qa_status=row[12],
        validation_status=row[13],
        finalization_status=row[14],
        auto_publish_enabled=bool(row[15]),
    )


def list_data(
    conn: sqlite3.Connection,
    data_type: Optional[str] = None,
    status: Optional[str] = None,
) -> List[DataRecord]:
    """List data records with optional filters."""
    cur = conn.cursor()

    query = """
        SELECT id, data_type, data_id, base_path, status, stage_path, published_path,
               created_at, staged_at, published_at, publish_mode, metadata_json,
               qa_status, validation_status, finalization_status, auto_publish_enabled
        FROM data_registry
        WHERE 1=1
    """
    params = []

    if data_type:
        query += " AND data_type = ?"
        params.append(data_type)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC"

    cur.execute(query, params)
    rows = cur.fetchall()

    return [
        DataRecord(
            id=row[0],
            data_type=row[1],
            data_id=row[2],
            base_path=row[3],
            status=row[4],
            stage_path=row[5],
            published_path=row[6],
            created_at=row[7],
            staged_at=row[8],
            published_at=row[9],
            publish_mode=row[10],
            metadata_json=row[11],
            qa_status=row[12],
            validation_status=row[13],
            finalization_status=row[14],
            auto_publish_enabled=bool(row[15]),
        )
        for row in rows
    ]


def link_data(
    conn: sqlite3.Connection,
    parent_id: str,
    child_id: str,
    relationship_type: str,
) -> bool:
    """Link two data instances with a relationship."""
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO data_relationships
            (parent_data_id, child_data_id, relationship_type)
            VALUES (?, ?, ?)
            """,
            (parent_id, child_id, relationship_type),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to link data {parent_id} -> {child_id}: {e}")
        return False


def get_data_lineage(conn: sqlite3.Connection, data_id: str) -> Dict[str, List[str]]:
    """Get lineage (parents and children) for a data instance."""
    cur = conn.cursor()

    # Get parents (what this data was derived from)
    cur.execute(
        """
        SELECT parent_data_id, relationship_type
        FROM data_relationships
        WHERE child_data_id = ?
        """,
        (data_id,),
    )
    parents = {}
    for parent_id, rel_type in cur.fetchall():
        if rel_type not in parents:
            parents[rel_type] = []
        parents[rel_type].append(parent_id)

    # Get children (what was produced from this data)
    cur.execute(
        """
        SELECT child_data_id, relationship_type
        FROM data_relationships
        WHERE parent_data_id = ?
        """,
        (data_id,),
    )
    children = {}
    for child_id, rel_type in cur.fetchall():
        if rel_type not in children:
            children[rel_type] = []
        children[rel_type].append(child_id)

    return {
        "parents": parents,
        "children": children,
    }


def enable_auto_publish(conn: sqlite3.Connection, data_id: str) -> bool:
    """Enable auto-publish for a data instance."""
    try:
        conn.execute(
            "UPDATE data_registry SET auto_publish_enabled = 1 WHERE data_id = ?",
            (data_id,),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to enable auto-publish for {data_id}: {e}")
        return False


def disable_auto_publish(conn: sqlite3.Connection, data_id: str) -> bool:
    """Disable auto-publish for a data instance."""
    try:
        conn.execute(
            "UPDATE data_registry SET auto_publish_enabled = 0 WHERE data_id = ?",
            (data_id,),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to disable auto-publish for {data_id}: {e}")
        return False


def check_auto_publish_criteria(
    conn: sqlite3.Connection,
    data_id: str,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Check if auto-publish criteria are met for a data instance."""
    cur = conn.cursor()
    cur.execute(
        """
        SELECT data_type, qa_status, validation_status, finalization_status, auto_publish_enabled
        FROM data_registry
        WHERE data_id = ?
        """,
        (data_id,),
    )
    row = cur.fetchone()

    if not row:
        return {"enabled": False, "criteria_met": False, "reason": "not_found"}

    dtype, qa_status, validation_status, finalization_status, auto_enabled = row

    if not auto_enabled:
        return {"enabled": False, "criteria_met": False, "reason": "disabled"}

    criteria_met = True
    reasons = []

    # Check finalization
    if finalization_status != "finalized":
        criteria_met = False
        reasons.append("not_finalized")

    # Check validation
    if validation_status != "validated":
        criteria_met = False
        reasons.append("not_validated")

    # Check QA for science data
    if dtype in ("image", "mosaic", "calib_ms", "caltable"):
        if qa_status != "passed":
            criteria_met = False
            reasons.append("qa_not_passed")

    return {
        "enabled": True,
        "criteria_met": criteria_met,
        "reasons": reasons,
        "qa_status": qa_status,
        "validation_status": validation_status,
        "finalization_status": finalization_status,
    }
