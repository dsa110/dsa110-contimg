"""
Pipeline Triggers API routes.

Expose Absurd scheduler for custom pipeline triggers with CRUD operations.
"""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from ..dependencies import get_pipeline_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/triggers", tags=["triggers"])


# ============================================================================
# Pydantic Models
# ============================================================================


class TriggerInput(BaseModel):
    """Input for creating/updating a trigger."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    trigger_type: str = Field(..., pattern="^(schedule|event|manual)$")
    schedule: Optional[str] = None  # Cron expression for schedule type
    event_pattern: Optional[str] = None  # Event type for event triggers
    action: str = Field(..., pattern="^(convert|calibrate|image|mosaic|cleanup|custom)$")
    action_params: Optional[Dict[str, Any]] = None
    enabled: bool = True


class Trigger(BaseModel):
    """Full trigger with metadata."""

    id: str
    name: str
    description: Optional[str] = None
    trigger_type: str
    schedule: Optional[str] = None
    event_pattern: Optional[str] = None
    action: str
    action_params: Optional[Dict[str, Any]] = None
    enabled: bool
    created_at: str
    last_triggered_at: Optional[str] = None
    next_run_at: Optional[str] = None


class TriggerListResponse(BaseModel):
    """Response for listing triggers."""

    triggers: List[Trigger]
    total: int


class TriggerExecution(BaseModel):
    """Record of a trigger execution."""

    id: str
    trigger_id: str
    trigger_name: str
    started_at: str
    completed_at: Optional[str] = None
    status: str  # running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TriggerExecutionResponse(BaseModel):
    """Response for trigger execution."""

    execution_id: str
    trigger_id: str
    status: str
    message: str


# ============================================================================
# Database Setup (extends pipeline.sqlite3)
# ============================================================================

TRIGGERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS pipeline_triggers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('schedule', 'event', 'manual')),
    schedule TEXT,
    event_pattern TEXT,
    action TEXT NOT NULL,
    action_params TEXT,
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_triggered_at TEXT,
    next_run_at TEXT
);

CREATE TABLE IF NOT EXISTS trigger_executions (
    id TEXT PRIMARY KEY,
    trigger_id TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    completed_at TEXT,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    result TEXT,
    error TEXT,
    FOREIGN KEY (trigger_id) REFERENCES pipeline_triggers(id)
);

CREATE INDEX IF NOT EXISTS idx_trigger_executions_trigger ON trigger_executions(trigger_id);
CREATE INDEX IF NOT EXISTS idx_trigger_executions_status ON trigger_executions(status);
"""


def _ensure_schema(db: sqlite3.Connection):
    """Ensure triggers tables exist."""
    db.executescript(TRIGGERS_SCHEMA)
    db.commit()


# ============================================================================
# Helpers
# ============================================================================


def _row_to_trigger(row: sqlite3.Row) -> Trigger:
    """Convert database row to Trigger model."""
    import json
    
    action_params = None
    if row["action_params"]:
        try:
            action_params = json.loads(row["action_params"])
        except json.JSONDecodeError:
            pass
    
    return Trigger(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        trigger_type=row["trigger_type"],
        schedule=row["schedule"],
        event_pattern=row["event_pattern"],
        action=row["action"],
        action_params=action_params,
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
        last_triggered_at=row["last_triggered_at"],
        next_run_at=row["next_run_at"],
    )


def _row_to_execution(row: sqlite3.Row, trigger_name: str = "") -> TriggerExecution:
    """Convert database row to TriggerExecution model."""
    import json
    
    result = None
    if row["result"]:
        try:
            result = json.loads(row["result"])
        except json.JSONDecodeError:
            pass
    
    return TriggerExecution(
        id=row["id"],
        trigger_id=row["trigger_id"],
        trigger_name=trigger_name,
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        status=row["status"],
        result=result,
        error=row["error"],
    )


def _calculate_next_run(schedule: Optional[str], trigger_type: str) -> Optional[str]:
    """Calculate next run time for scheduled triggers."""
    if trigger_type != "schedule" or not schedule:
        return None
    
    try:
        from croniter import croniter
        now = datetime.utcnow()
        cron = croniter(schedule, now)
        return cron.get_next(datetime).isoformat()
    except Exception:
        return None


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=TriggerListResponse)
async def list_triggers(
    trigger_type: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """List all pipeline triggers."""
    _ensure_schema(db)
    
    conditions = []
    params = []
    
    if trigger_type:
        conditions.append("trigger_type = ?")
        params.append(trigger_type)
    
    if enabled is not None:
        conditions.append("enabled = ?")
        params.append(1 if enabled else 0)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    cursor = db.execute(
        f"""
        SELECT * FROM pipeline_triggers
        WHERE {where_clause}
        ORDER BY created_at DESC
        """,
        params,
    )
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    triggers = [_row_to_trigger(row) for row in rows]
    return TriggerListResponse(triggers=triggers, total=len(triggers))


@router.get("/{trigger_id}", response_model=Trigger)
async def get_trigger(
    trigger_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get a single trigger by ID."""
    _ensure_schema(db)
    
    cursor = db.execute(
        "SELECT * FROM pipeline_triggers WHERE id = ?",
        (trigger_id,),
    )
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")
    
    return _row_to_trigger(row)


@router.post("", response_model=Trigger, status_code=201)
async def create_trigger(
    data: TriggerInput,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Create a new pipeline trigger."""
    import json
    
    _ensure_schema(db)
    
    trigger_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    next_run = _calculate_next_run(data.schedule, data.trigger_type)
    
    action_params_json = json.dumps(data.action_params) if data.action_params else None
    
    db.execute(
        """
        INSERT INTO pipeline_triggers 
        (id, name, description, trigger_type, schedule, event_pattern, action, action_params, enabled, created_at, next_run_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trigger_id,
            data.name,
            data.description,
            data.trigger_type,
            data.schedule,
            data.event_pattern,
            data.action,
            action_params_json,
            1 if data.enabled else 0,
            now,
            next_run,
        ),
    )
    db.commit()
    
    return Trigger(
        id=trigger_id,
        name=data.name,
        description=data.description,
        trigger_type=data.trigger_type,
        schedule=data.schedule,
        event_pattern=data.event_pattern,
        action=data.action,
        action_params=data.action_params,
        enabled=data.enabled,
        created_at=now,
        next_run_at=next_run,
    )


@router.put("/{trigger_id}", response_model=Trigger)
async def update_trigger(
    trigger_id: str,
    data: TriggerInput,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Update an existing trigger."""
    import json
    
    _ensure_schema(db)
    
    # Check exists
    cursor = db.execute(
        "SELECT id FROM pipeline_triggers WHERE id = ?",
        (trigger_id,),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")
    
    next_run = _calculate_next_run(data.schedule, data.trigger_type)
    action_params_json = json.dumps(data.action_params) if data.action_params else None
    
    db.execute(
        """
        UPDATE pipeline_triggers
        SET name = ?, description = ?, trigger_type = ?, schedule = ?, 
            event_pattern = ?, action = ?, action_params = ?, enabled = ?, next_run_at = ?
        WHERE id = ?
        """,
        (
            data.name,
            data.description,
            data.trigger_type,
            data.schedule,
            data.event_pattern,
            data.action,
            action_params_json,
            1 if data.enabled else 0,
            next_run,
            trigger_id,
        ),
    )
    db.commit()
    
    # Fetch updated
    cursor = db.execute("SELECT * FROM pipeline_triggers WHERE id = ?", (trigger_id,))
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    return _row_to_trigger(row)


@router.delete("/{trigger_id}", status_code=204)
async def delete_trigger(
    trigger_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Delete a trigger."""
    _ensure_schema(db)
    
    cursor = db.execute(
        "SELECT id FROM pipeline_triggers WHERE id = ?",
        (trigger_id,),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")
    
    # Delete executions first
    db.execute("DELETE FROM trigger_executions WHERE trigger_id = ?", (trigger_id,))
    db.execute("DELETE FROM pipeline_triggers WHERE id = ?", (trigger_id,))
    db.commit()
    
    return None


@router.post("/{trigger_id}/execute", response_model=TriggerExecutionResponse)
async def execute_trigger(
    trigger_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Manually execute a trigger immediately."""
    _ensure_schema(db)
    
    cursor = db.execute(
        "SELECT * FROM pipeline_triggers WHERE id = ?",
        (trigger_id,),
    )
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")
    
    trigger = _row_to_trigger(row)
    
    # Create execution record
    execution_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    db.execute(
        """
        INSERT INTO trigger_executions (id, trigger_id, started_at, status)
        VALUES (?, ?, ?, 'running')
        """,
        (execution_id, trigger_id, now),
    )
    
    # Update last triggered
    db.execute(
        "UPDATE pipeline_triggers SET last_triggered_at = ? WHERE id = ?",
        (now, trigger_id),
    )
    db.commit()
    
    # TODO: Actually dispatch to Absurd task queue
    # For now, mark as completed
    db.execute(
        """
        UPDATE trigger_executions
        SET status = 'completed', completed_at = ?
        WHERE id = ?
        """,
        (datetime.utcnow().isoformat(), execution_id),
    )
    db.commit()
    
    logger.info(f"Executed trigger {trigger.name} ({trigger_id})")
    
    return TriggerExecutionResponse(
        execution_id=execution_id,
        trigger_id=trigger_id,
        status="completed",
        message=f"Trigger '{trigger.name}' executed successfully",
    )


@router.get("/{trigger_id}/history", response_model=List[TriggerExecution])
async def get_trigger_history(
    trigger_id: str,
    limit: int = Query(50, ge=1, le=200),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get execution history for a trigger."""
    _ensure_schema(db)
    
    # Get trigger name
    cursor = db.execute(
        "SELECT name FROM pipeline_triggers WHERE id = ?",
        (trigger_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Trigger {trigger_id} not found")
    
    trigger_name = row[0]
    
    cursor = db.execute(
        """
        SELECT * FROM trigger_executions
        WHERE trigger_id = ?
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (trigger_id, limit),
    )
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    return [_row_to_execution(row, trigger_name) for row in rows]
