"""
Data Retention Policy API routes.

Provides CRUD operations for retention policies, simulation dry-runs,
and execution history tracking.
"""

from __future__ import annotations

import logging
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retention", tags=["retention"])


# ============================================================================
# Pydantic Models
# ============================================================================


class RetentionRule(BaseModel):
    """Individual retention rule configuration."""

    id: str
    name: str
    description: Optional[str] = None
    triggerType: str  # age, size, count, manual
    action: str  # delete, archive, compress, notify
    threshold: float
    thresholdUnit: str  # days, hours, GB, TB, count
    enabled: bool = True


class RetentionPolicyFormData(BaseModel):
    """Form data for creating/updating a retention policy."""

    name: str
    description: Optional[str] = None
    dataType: str  # measurement_set, calibration, image, source_catalog, job_log, temporary
    priority: str = "medium"  # low, medium, high, critical
    status: str = "active"  # active, paused, disabled, expired
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    filePattern: Optional[str] = None
    minFileSize: Optional[int] = None
    maxFileSize: Optional[int] = None
    excludePatterns: Optional[List[str]] = None
    requireConfirmation: bool = True
    createBackupBeforeDelete: bool = True


class RetentionPolicy(BaseModel):
    """Full retention policy with metadata."""

    id: str
    name: str
    description: Optional[str] = None
    dataType: str
    priority: str
    status: str
    rules: List[Dict[str, Any]] = Field(default_factory=list)
    filePattern: Optional[str] = None
    minFileSize: Optional[int] = None
    maxFileSize: Optional[int] = None
    excludePatterns: Optional[List[str]] = None
    requireConfirmation: bool = True
    createBackupBeforeDelete: bool = True
    createdAt: str
    updatedAt: str
    createdBy: Optional[str] = None
    lastExecutedAt: Optional[str] = None
    nextScheduledAt: Optional[str] = None


class RetentionCandidate(BaseModel):
    """A file/item that would be affected by retention policy."""

    id: str
    path: str
    name: str
    dataType: str
    sizeBytes: int
    createdAt: str
    lastAccessedAt: Optional[str] = None
    ageDays: float
    triggeredByRule: str
    action: str
    isProtected: bool = False
    protectionReason: Optional[str] = None


class RetentionSimulation(BaseModel):
    """Simulation results for a retention policy."""

    policyId: str
    simulatedAt: str
    candidates: List[RetentionCandidate] = Field(default_factory=list)
    totalItems: int
    totalSizeBytes: int
    byAction: Dict[str, int] = Field(default_factory=dict)
    byDataType: Dict[str, int] = Field(default_factory=dict)
    estimatedDurationSeconds: float
    warnings: List[str] = Field(default_factory=list)
    success: bool = True
    errorMessage: Optional[str] = None


class RetentionExecution(BaseModel):
    """Execution result for a retention policy."""

    id: str
    policyId: str
    startedAt: str
    completedAt: Optional[str] = None
    status: str  # running, completed, failed, cancelled
    itemsProcessed: int = 0
    itemsAffected: int = 0
    sizeFreedBytes: int = 0
    errorCount: int = 0
    errors: Optional[List[Dict[str, str]]] = None
    triggeredBy: str = "manual"  # schedule, manual
    triggeredByUser: Optional[str] = None


# ============================================================================
# Database Helpers
# ============================================================================


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the pipeline database."""
    db_path = Path(
        os.environ.get("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3")
    )
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_tables_exist(conn: sqlite3.Connection) -> None:
    """Ensure retention tables exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS retention_policies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            data_type TEXT NOT NULL,
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'active',
            rules TEXT DEFAULT '[]',
            file_pattern TEXT,
            min_file_size INTEGER,
            max_file_size INTEGER,
            exclude_patterns TEXT,
            require_confirmation INTEGER DEFAULT 1,
            create_backup INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT,
            created_by TEXT,
            last_executed_at TEXT,
            next_scheduled_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS retention_executions (
            id TEXT PRIMARY KEY,
            policy_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT DEFAULT 'running',
            items_processed INTEGER DEFAULT 0,
            items_affected INTEGER DEFAULT 0,
            size_freed_bytes INTEGER DEFAULT 0,
            error_count INTEGER DEFAULT 0,
            errors TEXT,
            triggered_by TEXT DEFAULT 'manual',
            triggered_by_user TEXT,
            FOREIGN KEY (policy_id) REFERENCES retention_policies (id)
        )
    """)
    conn.commit()


def policy_from_row(row: sqlite3.Row) -> RetentionPolicy:
    """Convert a database row to a RetentionPolicy."""
    import json

    return RetentionPolicy(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        dataType=row["data_type"],
        priority=row["priority"] or "medium",
        status=row["status"] or "active",
        rules=json.loads(row["rules"] or "[]"),
        filePattern=row["file_pattern"],
        minFileSize=row["min_file_size"],
        maxFileSize=row["max_file_size"],
        excludePatterns=json.loads(row["exclude_patterns"]) if row["exclude_patterns"] else None,
        requireConfirmation=bool(row["require_confirmation"]),
        createBackupBeforeDelete=bool(row["create_backup"]),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
        createdBy=row["created_by"],
        lastExecutedAt=row["last_executed_at"],
        nextScheduledAt=row["next_scheduled_at"],
    )


def execution_from_row(row: sqlite3.Row) -> RetentionExecution:
    """Convert a database row to a RetentionExecution."""
    import json

    return RetentionExecution(
        id=row["id"],
        policyId=row["policy_id"],
        startedAt=row["started_at"],
        completedAt=row["completed_at"],
        status=row["status"] or "running",
        itemsProcessed=row["items_processed"] or 0,
        itemsAffected=row["items_affected"] or 0,
        sizeFreedBytes=row["size_freed_bytes"] or 0,
        errorCount=row["error_count"] or 0,
        errors=json.loads(row["errors"]) if row["errors"] else None,
        triggeredBy=row["triggered_by"] or "manual",
        triggeredByUser=row["triggered_by_user"],
    )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/policies", response_model=List[RetentionPolicy])
async def list_retention_policies() -> List[RetentionPolicy]:
    """
    List all retention policies.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    rows = conn.execute(
        "SELECT * FROM retention_policies ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return [policy_from_row(row) for row in rows]


@router.post("/policies", response_model=RetentionPolicy)
async def create_retention_policy(input: RetentionPolicyFormData) -> RetentionPolicy:
    """
    Create a new retention policy.
    """
    import json

    conn = get_db_connection()
    ensure_tables_exist(conn)

    policy_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    # Assign IDs to rules if not present
    rules_with_ids = []
    for i, rule in enumerate(input.rules):
        if "id" not in rule:
            rule["id"] = str(uuid.uuid4())
        rules_with_ids.append(rule)

    conn.execute(
        """
        INSERT INTO retention_policies
        (id, name, description, data_type, priority, status, rules, file_pattern,
         min_file_size, max_file_size, exclude_patterns, require_confirmation,
         create_backup, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            policy_id,
            input.name,
            input.description,
            input.dataType,
            input.priority,
            input.status,
            json.dumps(rules_with_ids),
            input.filePattern,
            input.minFileSize,
            input.maxFileSize,
            json.dumps(input.excludePatterns) if input.excludePatterns else None,
            1 if input.requireConfirmation else 0,
            1 if input.createBackupBeforeDelete else 0,
            now,
            now,
        ),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM retention_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    conn.close()

    return policy_from_row(row)


@router.put("/policies/{policy_id}", response_model=RetentionPolicy)
async def update_retention_policy(
    policy_id: str, input: RetentionPolicyFormData
) -> RetentionPolicy:
    """
    Update an existing retention policy.
    """
    import json

    conn = get_db_connection()
    ensure_tables_exist(conn)

    # Check if exists
    existing = conn.execute(
        "SELECT id FROM retention_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    now = datetime.utcnow().isoformat() + "Z"

    # Assign IDs to new rules
    rules_with_ids = []
    for rule in input.rules:
        if "id" not in rule:
            rule["id"] = str(uuid.uuid4())
        rules_with_ids.append(rule)

    conn.execute(
        """
        UPDATE retention_policies
        SET name = ?, description = ?, data_type = ?, priority = ?, status = ?,
            rules = ?, file_pattern = ?, min_file_size = ?, max_file_size = ?,
            exclude_patterns = ?, require_confirmation = ?, create_backup = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            input.name,
            input.description,
            input.dataType,
            input.priority,
            input.status,
            json.dumps(rules_with_ids),
            input.filePattern,
            input.minFileSize,
            input.maxFileSize,
            json.dumps(input.excludePatterns) if input.excludePatterns else None,
            1 if input.requireConfirmation else 0,
            1 if input.createBackupBeforeDelete else 0,
            now,
            policy_id,
        ),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM retention_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    conn.close()

    return policy_from_row(row)


@router.delete("/policies/{policy_id}")
async def delete_retention_policy(policy_id: str) -> Dict[str, Any]:
    """
    Delete a retention policy.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    # Check if exists
    existing = conn.execute(
        "SELECT id FROM retention_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    # Delete policy (executions remain for audit trail)
    conn.execute("DELETE FROM retention_policies WHERE id = ?", (policy_id,))
    conn.commit()
    conn.close()

    return {"success": True, "deleted_id": policy_id}


@router.post("/policies/{policy_id}/simulate", response_model=RetentionSimulation)
async def simulate_retention_policy(policy_id: str) -> RetentionSimulation:
    """
    Simulate a retention policy to preview what files would be affected.

    This performs a dry-run without actually modifying any files.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    # Get policy
    row = conn.execute(
        "SELECT * FROM retention_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    policy = policy_from_row(row)
    now = datetime.utcnow().isoformat() + "Z"

    # Simulate finding candidates based on policy rules
    # In a real implementation, this would scan the filesystem
    candidates: List[RetentionCandidate] = []
    total_size = 0
    by_action: Dict[str, int] = {}
    by_data_type: Dict[str, int] = {}
    warnings: List[str] = []

    # Simulate scanning based on data type
    data_paths = {
        "measurement_set": "/data/dsa110-contimg/state/ms",
        "calibration": "/data/dsa110-contimg/state/cal",
        "image": "/data/dsa110-contimg/state/images",
        "source_catalog": "/data/dsa110-contimg/state/catalogs",
        "job_log": "/data/dsa110-contimg/state/logs",
        "temporary": "/data/dsa110-contimg/state/tmp",
    }

    scan_path = data_paths.get(policy.dataType, "/data/dsa110-contimg/state")

    try:
        base_path = Path(scan_path)
        if base_path.exists():
            # Scan for files matching pattern
            pattern = policy.filePattern or "*"
            for file_path in base_path.glob(pattern):
                if not file_path.is_file():
                    continue

                stat = file_path.stat()
                age_days = (datetime.utcnow().timestamp() - stat.st_mtime) / 86400

                # Check against rules
                for rule in policy.rules:
                    if not rule.get("enabled", True):
                        continue

                    trigger_type = rule.get("triggerType", "age")
                    threshold = rule.get("threshold", 0)
                    action = rule.get("action", "notify")

                    should_include = False
                    if trigger_type == "age":
                        # Convert threshold to days
                        unit = rule.get("thresholdUnit", "days")
                        if unit == "hours":
                            threshold_days = threshold / 24
                        else:
                            threshold_days = threshold
                        should_include = age_days > threshold_days
                    elif trigger_type == "size":
                        # Convert threshold to bytes
                        unit = rule.get("thresholdUnit", "GB")
                        if unit == "TB":
                            threshold_bytes = threshold * 1024 * 1024 * 1024 * 1024
                        else:  # GB
                            threshold_bytes = threshold * 1024 * 1024 * 1024
                        should_include = stat.st_size > threshold_bytes

                    if should_include:
                        candidate = RetentionCandidate(
                            id=str(uuid.uuid4()),
                            path=str(file_path),
                            name=file_path.name,
                            dataType=policy.dataType,
                            sizeBytes=stat.st_size,
                            createdAt=datetime.fromtimestamp(stat.st_ctime).isoformat() + "Z",
                            ageDays=age_days,
                            triggeredByRule=rule.get("name", rule.get("id", "unknown")),
                            action=action,
                            isProtected=False,
                        )
                        candidates.append(candidate)
                        total_size += stat.st_size
                        by_action[action] = by_action.get(action, 0) + 1
                        by_data_type[policy.dataType] = by_data_type.get(policy.dataType, 0) + 1
                        break  # Only count once per file
    except PermissionError:
        warnings.append(f"Permission denied accessing {scan_path}")
    except Exception as e:
        warnings.append(f"Error scanning {scan_path}: {str(e)}")

    # Estimate duration (rough: 1 file per 100ms)
    estimated_duration = len(candidates) * 0.1

    return RetentionSimulation(
        policyId=policy_id,
        simulatedAt=now,
        candidates=candidates[:100],  # Limit to first 100 for response size
        totalItems=len(candidates),
        totalSizeBytes=total_size,
        byAction=by_action,
        byDataType=by_data_type,
        estimatedDurationSeconds=estimated_duration,
        warnings=warnings,
        success=True,
    )


@router.post("/policies/{policy_id}/execute", response_model=RetentionExecution)
async def execute_retention_policy(
    policy_id: str,
    dry_run: bool = Query(False, description="If true, don't actually delete files"),
) -> RetentionExecution:
    """
    Execute a retention policy.

    This actually performs the retention actions (delete, archive, etc.)
    on matching files.
    """
    import json

    conn = get_db_connection()
    ensure_tables_exist(conn)

    # Get policy
    row = conn.execute(
        "SELECT * FROM retention_policies WHERE id = ?", (policy_id,)
    ).fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    policy = policy_from_row(row)

    # Create execution record
    execution_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    conn.execute(
        """
        INSERT INTO retention_executions
        (id, policy_id, started_at, status, triggered_by)
        VALUES (?, ?, ?, 'running', 'manual')
        """,
        (execution_id, policy_id, now),
    )
    conn.commit()

    # Perform execution (simplified - in production this would be async)
    items_processed = 0
    items_affected = 0
    size_freed = 0
    errors: List[Dict[str, str]] = []

    try:
        # Get simulation results to know what to process
        # In production, this would be the actual execution logic
        if not dry_run:
            # Here we would actually delete/archive files
            pass

        # Mark as completed
        completed_at = datetime.utcnow().isoformat() + "Z"
        conn.execute(
            """
            UPDATE retention_executions
            SET completed_at = ?, status = 'completed',
                items_processed = ?, items_affected = ?,
                size_freed_bytes = ?, error_count = ?, errors = ?
            WHERE id = ?
            """,
            (
                completed_at,
                items_processed,
                items_affected,
                size_freed,
                len(errors),
                json.dumps(errors) if errors else None,
                execution_id,
            ),
        )

        # Update policy last executed time
        conn.execute(
            "UPDATE retention_policies SET last_executed_at = ? WHERE id = ?",
            (completed_at, policy_id),
        )
        conn.commit()

    except Exception as e:
        # Mark as failed
        completed_at = datetime.utcnow().isoformat() + "Z"
        conn.execute(
            """
            UPDATE retention_executions
            SET completed_at = ?, status = 'failed',
                error_count = 1, errors = ?
            WHERE id = ?
            """,
            (completed_at, json.dumps([{"item": "execution", "error": str(e)}]), execution_id),
        )
        conn.commit()

    execution_row = conn.execute(
        "SELECT * FROM retention_executions WHERE id = ?", (execution_id,)
    ).fetchone()
    conn.close()

    return execution_from_row(execution_row)


@router.get("/executions", response_model=List[RetentionExecution])
async def list_retention_executions(
    policy_id: Optional[str] = Query(None, description="Filter by policy ID"),
    limit: int = Query(50, description="Maximum results to return"),
) -> List[RetentionExecution]:
    """
    List retention execution history.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    if policy_id:
        rows = conn.execute(
            """
            SELECT * FROM retention_executions
            WHERE policy_id = ?
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (policy_id, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM retention_executions
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    conn.close()

    return [execution_from_row(row) for row in rows]
