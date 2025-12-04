"""
Backup/Restore API routes.

Manage database and data backups with validation and restore capabilities.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import sqlite3
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ..dependencies import get_pipeline_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backups", tags=["backup"])

# Configuration
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", "/stage/backups"))
PIPELINE_DB = Path(os.getenv("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3"))
CALTABLES_DIR = Path(os.getenv("CALTABLES_DIR", "/products/caltables"))


# ============================================================================
# Pydantic Models
# ============================================================================


class BackupCreateInput(BaseModel):
    """Input for creating a backup."""

    backup_type: str = Field(
        default="database_only",
        pattern="^(full|incremental|database_only|caltables_only)$",
    )
    description: Optional[str] = None


class BackupInfo(BaseModel):
    """Backup information."""

    id: str
    backup_path: str
    backup_type: str
    size_bytes: Optional[int] = None
    checksum: Optional[str] = None
    created_at: str
    created_by: Optional[str] = None
    status: str
    validation_status: Optional[str] = None
    validated_at: Optional[str] = None
    error_message: Optional[str] = None


class BackupListResponse(BaseModel):
    """Response for listing backups."""

    backups: List[BackupInfo]
    total: int


class BackupValidationResult(BaseModel):
    """Result of backup validation."""

    id: str
    is_valid: bool
    expected_checksum: Optional[str] = None
    actual_checksum: Optional[str] = None
    error: Optional[str] = None


class RestoreResult(BaseModel):
    """Result of restore operation."""

    success: bool
    backup_id: str
    restored_at: str
    message: str


# ============================================================================
# Helpers
# ============================================================================


def _row_to_backup(row: sqlite3.Row) -> BackupInfo:
    """Convert database row to BackupInfo model."""
    return BackupInfo(
        id=row["id"],
        backup_path=row["backup_path"],
        backup_type=row["backup_type"],
        size_bytes=row["size_bytes"],
        checksum=row["checksum"],
        created_at=row["created_at"],
        created_by=row["created_by"],
        status=row["status"],
        validation_status=row["validation_status"],
        validated_at=row["validated_at"],
        error_message=row["error_message"],
    )


def _compute_checksum(filepath: Path) -> str:
    """Compute SHA256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def _get_current_user() -> str:
    """Get current user. Placeholder for auth integration."""
    return "default_user"


# ============================================================================
# Background Tasks
# ============================================================================


def _perform_backup(
    backup_id: str,
    backup_type: str,
    backup_path: Path,
    db_path: Path,
):
    """Perform the actual backup in background."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        
        if backup_type == "database_only":
            # SQLite backup
            dest_db = backup_path / "pipeline.sqlite3"
            dest_db.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["sqlite3", str(PIPELINE_DB), f".backup '{dest_db}'"],
                shell=True,
                check=True,
            )
            size = dest_db.stat().st_size
            checksum = _compute_checksum(dest_db)
            
        elif backup_type == "caltables_only":
            # Rsync caltables
            subprocess.run(
                ["rsync", "-a", str(CALTABLES_DIR) + "/", str(backup_path / "caltables") + "/"],
                check=True,
            )
            size = sum(f.stat().st_size for f in backup_path.rglob("*") if f.is_file())
            checksum = None  # Directory backup
            
        elif backup_type == "full":
            # Both database and caltables
            dest_db = backup_path / "pipeline.sqlite3"
            subprocess.run(
                ["sqlite3", str(PIPELINE_DB), f".backup '{dest_db}'"],
                shell=True,
                check=True,
            )
            subprocess.run(
                ["rsync", "-a", str(CALTABLES_DIR) + "/", str(backup_path / "caltables") + "/"],
                check=True,
            )
            size = sum(f.stat().st_size for f in backup_path.rglob("*") if f.is_file())
            checksum = _compute_checksum(dest_db) if dest_db.exists() else None
            
        else:
            raise ValueError(f"Unknown backup type: {backup_type}")
        
        # Update record
        conn.execute(
            """
            UPDATE backup_history
            SET status = 'completed', size_bytes = ?, checksum = ?
            WHERE id = ?
            """,
            (size, checksum, backup_id),
        )
        conn.commit()
        logger.info(f"Backup {backup_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Backup {backup_id} failed: {e}")
        conn.execute(
            """
            UPDATE backup_history
            SET status = 'failed', error_message = ?
            WHERE id = ?
            """,
            (str(e), backup_id),
        )
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/create", response_model=BackupInfo, status_code=201)
async def create_backup(
    data: BackupCreateInput,
    background_tasks: BackgroundTasks,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Create a new backup. Runs in background."""
    current_user = _get_current_user()
    backup_id = str(uuid.uuid4())
    now = datetime.utcnow()
    
    # Generate backup path
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / data.backup_type / f"{timestamp}_{backup_id[:8]}"
    
    # Create record
    db.execute(
        """
        INSERT INTO backup_history (id, backup_path, backup_type, created_at, created_by, status)
        VALUES (?, ?, ?, ?, ?, 'in_progress')
        """,
        (backup_id, str(backup_path), data.backup_type, now.isoformat(), current_user),
    )
    db.commit()
    
    # Schedule background task
    background_tasks.add_task(
        _perform_backup,
        backup_id,
        data.backup_type,
        backup_path,
        PIPELINE_DB,
    )
    
    return BackupInfo(
        id=backup_id,
        backup_path=str(backup_path),
        backup_type=data.backup_type,
        created_at=now.isoformat(),
        created_by=current_user,
        status="in_progress",
    )


@router.get("/status", response_model=BackupInfo)
async def get_latest_backup_status(
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get status of the most recent backup."""
    cursor = db.execute(
        "SELECT * FROM backup_history ORDER BY created_at DESC LIMIT 1"
    )
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="No backups found")
    
    return _row_to_backup(row)


@router.get("/history", response_model=BackupListResponse)
async def list_backups(
    backup_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """List backup history."""
    conditions = []
    params = []
    
    if backup_type:
        conditions.append("backup_type = ?")
        params.append(backup_type)
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)
    
    cursor = db.execute(
        f"""
        SELECT * FROM backup_history
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        params,
    )
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    backups = [_row_to_backup(row) for row in rows]
    return BackupListResponse(backups=backups, total=len(backups))


@router.post("/validate/{backup_id}", response_model=BackupValidationResult)
async def validate_backup(
    backup_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Validate backup integrity by checking checksum."""
    cursor = db.execute(
        "SELECT * FROM backup_history WHERE id = ?",
        (backup_id,),
    )
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found")
    
    backup_path = Path(row["backup_path"])
    expected_checksum = row["checksum"]
    
    # Find database file
    db_file = backup_path / "pipeline.sqlite3"
    if not db_file.exists():
        db_file = backup_path  # Might be direct file
    
    if not db_file.exists():
        return BackupValidationResult(
            id=backup_id,
            is_valid=False,
            error="Backup file not found",
        )
    
    try:
        actual_checksum = _compute_checksum(db_file)
        is_valid = expected_checksum is None or actual_checksum == expected_checksum
        
        # Update validation status
        now = datetime.utcnow().isoformat()
        db.execute(
            """
            UPDATE backup_history
            SET validation_status = ?, validated_at = ?
            WHERE id = ?
            """,
            ("valid" if is_valid else "invalid", now, backup_id),
        )
        db.commit()
        
        return BackupValidationResult(
            id=backup_id,
            is_valid=is_valid,
            expected_checksum=expected_checksum,
            actual_checksum=actual_checksum,
        )
        
    except Exception as e:
        return BackupValidationResult(
            id=backup_id,
            is_valid=False,
            error=str(e),
        )


@router.post("/restore/{backup_id}", response_model=RestoreResult)
async def restore_backup(
    backup_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Restore from a backup. Requires valid backup status."""
    cursor = db.execute(
        "SELECT * FROM backup_history WHERE id = ?",
        (backup_id,),
    )
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found")
    
    if row["status"] != "completed":
        raise HTTPException(status_code=400, detail="Cannot restore incomplete backup")
    
    backup_path = Path(row["backup_path"])
    backup_type = row["backup_type"]
    
    try:
        if backup_type in ("database_only", "full"):
            src_db = backup_path / "pipeline.sqlite3"
            if src_db.exists():
                # Close current connection and restore
                db.close()
                shutil.copy2(src_db, PIPELINE_DB)
        
        if backup_type in ("caltables_only", "full"):
            src_caltables = backup_path / "caltables"
            if src_caltables.exists():
                subprocess.run(
                    ["rsync", "-a", "--delete", str(src_caltables) + "/", str(CALTABLES_DIR) + "/"],
                    check=True,
                )
        
        return RestoreResult(
            success=True,
            backup_id=backup_id,
            restored_at=datetime.utcnow().isoformat(),
            message=f"Successfully restored {backup_type} backup",
        )
        
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        raise HTTPException(status_code=500, detail=f"Restore failed: {e}")


@router.delete("/{backup_id}", status_code=204)
async def delete_backup(
    backup_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Delete a backup and its files."""
    cursor = db.execute(
        "SELECT backup_path FROM backup_history WHERE id = ?",
        (backup_id,),
    )
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Backup {backup_id} not found")
    
    backup_path = Path(row[0])
    
    # Delete files
    if backup_path.exists():
        if backup_path.is_dir():
            shutil.rmtree(backup_path)
        else:
            backup_path.unlink()
    
    # Update status
    db.execute(
        "UPDATE backup_history SET status = 'deleted' WHERE id = ?",
        (backup_id,),
    )
    db.commit()
    
    return None
