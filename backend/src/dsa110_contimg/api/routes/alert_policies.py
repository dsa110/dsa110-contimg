"""
Alert Policy Management API routes.

Provides CRUD operations, dry-run previews, and silence management
for configurable alert policies.
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

router = APIRouter(prefix="/alert-policies", tags=["alert-policies"])


# ============================================================================
# Pydantic Models
# ============================================================================


class AlertPolicyRule(BaseModel):
    """Individual rule within an alert policy."""

    metric: str
    labels: Optional[Dict[str, str]] = None
    operator: str  # >, >=, <, <=, ==, !=
    threshold: float
    for_seconds: Optional[int] = None


class AlertPolicyInput(BaseModel):
    """Input for creating/updating an alert policy."""

    name: str
    description: Optional[str] = None
    severity: str = "warning"  # info, warning, critical
    channels: List[str] = Field(default_factory=list)
    enabled: bool = True
    rules: List[AlertPolicyRule] = Field(default_factory=list)
    overrides: Optional[List[AlertPolicyRule]] = None
    repeat_interval_seconds: Optional[int] = None


class AlertPolicy(AlertPolicyInput):
    """Full alert policy with metadata."""

    id: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class AlertPolicyListResponse(BaseModel):
    """Response for listing alert policies."""

    policies: List[AlertPolicy]
    total: int


class AlertSilence(BaseModel):
    """A silence period for an alert policy."""

    id: str
    policy_id: str
    reason: str
    created_by: Optional[str] = None
    starts_at: str
    ends_at: str
    created_at: Optional[str] = None


class CreateSilenceInput(BaseModel):
    """Input for creating a silence."""

    reason: str
    created_by: Optional[str] = None
    starts_at: str
    ends_at: str


class DryRunSampleAlert(BaseModel):
    """A sample alert from dry run."""

    message: str
    severity: str
    labels: Optional[Dict[str, str]] = None


class DryRunAlert(BaseModel):
    """Result for a single policy in dry run."""

    policy_id: str
    policy_name: str
    would_fire: bool
    sample_alerts: List[DryRunSampleAlert] = Field(default_factory=list)


class AlertPolicyDryRunRequest(BaseModel):
    """Request for dry run."""

    policy: AlertPolicyInput


class AlertPolicyDryRunResponse(BaseModel):
    """Response from dry run."""

    results: List[DryRunAlert]
    evaluated_at: str


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
    """Ensure alert policy tables exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_policies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            severity TEXT DEFAULT 'warning',
            channels TEXT DEFAULT '[]',
            enabled INTEGER DEFAULT 1,
            rules TEXT DEFAULT '[]',
            overrides TEXT,
            repeat_interval_seconds INTEGER,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS alert_silences (
            id TEXT PRIMARY KEY,
            policy_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_by TEXT,
            starts_at TEXT NOT NULL,
            ends_at TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (policy_id) REFERENCES alert_policies (id)
        )
    """)
    conn.commit()


def policy_from_row(row: sqlite3.Row) -> AlertPolicy:
    """Convert a database row to an AlertPolicy."""
    import json

    return AlertPolicy(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        severity=row["severity"] or "warning",
        channels=json.loads(row["channels"] or "[]"),
        enabled=bool(row["enabled"]),
        rules=[AlertPolicyRule(**r) for r in json.loads(row["rules"] or "[]")],
        overrides=(
            [AlertPolicyRule(**r) for r in json.loads(row["overrides"])]
            if row["overrides"]
            else None
        ),
        repeat_interval_seconds=row["repeat_interval_seconds"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def silence_from_row(row: sqlite3.Row) -> AlertSilence:
    """Convert a database row to an AlertSilence."""
    return AlertSilence(
        id=row["id"],
        policy_id=row["policy_id"],
        reason=row["reason"],
        created_by=row["created_by"],
        starts_at=row["starts_at"],
        ends_at=row["ends_at"],
        created_at=row["created_at"],
    )


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("", response_model=AlertPolicyListResponse)
async def list_alert_policies(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    search: Optional[str] = Query(None, description="Search in name/description"),
) -> AlertPolicyListResponse:
    """
    List all alert policies with optional filtering.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    query = "SELECT * FROM alert_policies WHERE 1=1"
    params: List[Any] = []

    if severity:
        query += " AND severity = ?"
        params.append(severity)

    if enabled is not None:
        query += " AND enabled = ?"
        params.append(1 if enabled else 0)

    if search:
        query += " AND (name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY created_at DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    policies = [policy_from_row(row) for row in rows]
    return AlertPolicyListResponse(policies=policies, total=len(policies))


@router.get("/{policy_id}", response_model=AlertPolicy)
async def get_alert_policy(policy_id: str) -> AlertPolicy:
    """
    Get a specific alert policy by ID.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    row = conn.execute(
        "SELECT * FROM alert_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    return policy_from_row(row)


@router.post("", response_model=AlertPolicy)
async def create_alert_policy(input: AlertPolicyInput) -> AlertPolicy:
    """
    Create a new alert policy.
    """
    import json

    conn = get_db_connection()
    ensure_tables_exist(conn)

    policy_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    conn.execute(
        """
        INSERT INTO alert_policies
        (id, name, description, severity, channels, enabled, rules, overrides,
         repeat_interval_seconds, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            policy_id,
            input.name,
            input.description,
            input.severity,
            json.dumps(input.channels),
            1 if input.enabled else 0,
            json.dumps([r.model_dump() for r in input.rules]),
            json.dumps([r.model_dump() for r in input.overrides]) if input.overrides else None,
            input.repeat_interval_seconds,
            now,
            now,
        ),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM alert_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    conn.close()

    return policy_from_row(row)


@router.put("/{policy_id}", response_model=AlertPolicy)
async def update_alert_policy(policy_id: str, input: AlertPolicyInput) -> AlertPolicy:
    """
    Update an existing alert policy.
    """
    import json

    conn = get_db_connection()
    ensure_tables_exist(conn)

    # Check if exists
    existing = conn.execute(
        "SELECT id FROM alert_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    now = datetime.utcnow().isoformat() + "Z"

    conn.execute(
        """
        UPDATE alert_policies
        SET name = ?, description = ?, severity = ?, channels = ?, enabled = ?,
            rules = ?, overrides = ?, repeat_interval_seconds = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            input.name,
            input.description,
            input.severity,
            json.dumps(input.channels),
            1 if input.enabled else 0,
            json.dumps([r.model_dump() for r in input.rules]),
            json.dumps([r.model_dump() for r in input.overrides]) if input.overrides else None,
            input.repeat_interval_seconds,
            now,
            policy_id,
        ),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM alert_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    conn.close()

    return policy_from_row(row)


@router.delete("/{policy_id}")
async def delete_alert_policy(policy_id: str) -> Dict[str, Any]:
    """
    Delete an alert policy.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    # Check if exists
    existing = conn.execute(
        "SELECT id FROM alert_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    # Delete silences first
    conn.execute("DELETE FROM alert_silences WHERE policy_id = ?", (policy_id,))
    # Delete policy
    conn.execute("DELETE FROM alert_policies WHERE id = ?", (policy_id,))
    conn.commit()
    conn.close()

    return {"success": True, "deleted_id": policy_id}


@router.post("/{policy_id}/toggle", response_model=AlertPolicy)
async def toggle_alert_policy(
    policy_id: str,
    enabled: bool = Query(..., description="New enabled state"),
) -> AlertPolicy:
    """
    Toggle an alert policy's enabled state.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    # Check if exists
    existing = conn.execute(
        "SELECT id FROM alert_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    now = datetime.utcnow().isoformat() + "Z"

    conn.execute(
        "UPDATE alert_policies SET enabled = ?, updated_at = ? WHERE id = ?",
        (1 if enabled else 0, now, policy_id),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM alert_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    conn.close()

    return policy_from_row(row)


@router.post("/dry-run", response_model=AlertPolicyDryRunResponse)
async def dry_run_alert_policy(request: AlertPolicyDryRunRequest) -> AlertPolicyDryRunResponse:
    """
    Perform a dry run of an alert policy to see what alerts would fire.

    This evaluates the policy rules against current system state without
    actually creating any alerts.
    """
    policy = request.policy
    now = datetime.utcnow().isoformat() + "Z"

    # Simulate evaluation - in a real implementation, this would query
    # Prometheus or other metrics sources
    results = []

    # Generate sample result based on rules
    would_fire = False
    sample_alerts = []

    for rule in policy.rules:
        # Simulate checking the metric
        # In production, this would query Prometheus with the metric name
        sample_alerts.append(
            DryRunSampleAlert(
                message=f"[DRY RUN] {rule.metric} {rule.operator} {rule.threshold}",
                severity=policy.severity,
                labels=rule.labels,
            )
        )

    results.append(
        DryRunAlert(
            policy_id="dry-run",
            policy_name=policy.name,
            would_fire=would_fire,
            sample_alerts=sample_alerts,
        )
    )

    return AlertPolicyDryRunResponse(results=results, evaluated_at=now)


@router.get("/silences", response_model=List[AlertSilence])
async def list_all_silences() -> List[AlertSilence]:
    """
    List all alert silences across all policies.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    rows = conn.execute(
        "SELECT * FROM alert_silences ORDER BY created_at DESC"
    ).fetchall()
    conn.close()

    return [silence_from_row(row) for row in rows]


@router.get("/{policy_id}/silences", response_model=List[AlertSilence])
async def list_policy_silences(policy_id: str) -> List[AlertSilence]:
    """
    List silences for a specific alert policy.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    # Check if policy exists
    existing = conn.execute(
        "SELECT id FROM alert_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    rows = conn.execute(
        "SELECT * FROM alert_silences WHERE policy_id = ? ORDER BY created_at DESC",
        (policy_id,),
    ).fetchall()
    conn.close()

    return [silence_from_row(row) for row in rows]


@router.post("/{policy_id}/silences", response_model=AlertSilence)
async def create_alert_silence(
    policy_id: str, input: CreateSilenceInput
) -> AlertSilence:
    """
    Create a silence for an alert policy.

    During the silence period, the policy will not generate alerts.
    """
    conn = get_db_connection()
    ensure_tables_exist(conn)

    # Check if policy exists
    existing = conn.execute(
        "SELECT id FROM alert_policies WHERE id = ?", (policy_id,)
    ).fetchone()
    if not existing:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Policy {policy_id} not found")

    silence_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"

    conn.execute(
        """
        INSERT INTO alert_silences
        (id, policy_id, reason, created_by, starts_at, ends_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            silence_id,
            policy_id,
            input.reason,
            input.created_by,
            input.starts_at,
            input.ends_at,
            now,
        ),
    )
    conn.commit()

    row = conn.execute(
        "SELECT * FROM alert_silences WHERE id = ?", (silence_id,)
    ).fetchone()
    conn.close()

    return silence_from_row(row)
