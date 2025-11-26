"""Transient detection API routes.

Provides endpoints for querying and managing transient candidates and alerts.
Supports user intervention operations: acknowledge, classify, update status, add notes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter()


# Request models
class AcknowledgeRequest(BaseModel):
    """Request model for acknowledging alerts."""

    acknowledged_by: str = Field(..., description="Username/identifier of person acknowledging")
    notes: Optional[str] = Field(None, description="Optional notes about the acknowledgment")


class ClassifyRequest(BaseModel):
    """Request model for classifying candidates."""

    classification: str = Field(
        ..., description="Classification: real, artifact, variable, or uncertain"
    )
    classified_by: str = Field(..., description="Username/identifier of person classifying")
    notes: Optional[str] = Field(None, description="Optional notes about the classification")


class FollowUpRequest(BaseModel):
    """Request model for updating follow-up status."""

    status: str = Field(
        ..., description="Follow-up status: pending, scheduled, completed, or declined"
    )
    notes: Optional[str] = Field(None, description="Optional notes about the status update")


class NotesRequest(BaseModel):
    """Request model for adding notes."""

    notes: str = Field(..., description="Notes text to add")
    username: str = Field(..., description="Username/identifier of person adding notes")
    append: bool = Field(True, description="If True, append to existing notes; if False, replace")


# Response models
class TransientAlertResponse(BaseModel):
    """Response model for transient alert."""

    id: int
    candidate_id: int
    alert_level: str
    alert_message: str
    created_at: float
    acknowledged: bool
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[float] = None
    follow_up_status: Optional[str] = None
    notes: Optional[str] = None


class TransientCandidateResponse(BaseModel):
    """Response model for transient candidate."""

    id: int
    source_name: str
    ra_deg: float
    dec_deg: float
    detection_type: str
    flux_obs_mjy: float
    flux_baseline_mjy: Optional[float] = None
    flux_ratio: Optional[float] = None
    significance_sigma: float
    baseline_catalog: Optional[str] = None
    detected_at: float
    mosaic_id: Optional[int] = None
    classification: Optional[str] = None
    classified_by: Optional[str] = None
    classified_at: Optional[float] = None
    variability_index: Optional[float] = None
    last_updated: float
    follow_up_status: Optional[str] = None
    notes: Optional[str] = None


# Query endpoints
@router.get("/alerts", response_model=list[TransientAlertResponse])
def list_alerts(
    alert_level: Optional[str] = Query(
        None, description="Filter by alert level (CRITICAL, HIGH, MEDIUM)"
    ),
    acknowledged: bool = Query(
        False, description="Show acknowledged (True) or unacknowledged (False)"
    ),
    limit: int = Query(50, description="Maximum number of alerts to return", ge=1, le=500),
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """List transient alerts with optional filtering."""
    from dsa110_contimg.catalog.transient_detection import get_transient_alerts

    try:
        df = get_transient_alerts(
            alert_level=alert_level, acknowledged=acknowledged, limit=limit, db_path=db_path
        )
        alerts = df.to_dict("records")
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query alerts: {str(e)}") from e


@router.get("/alerts/{alert_id}", response_model=TransientAlertResponse)
def get_alert(
    alert_id: int,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Get details for a specific alert."""
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM transient_alerts WHERE id = ?", (alert_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")

        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alert: {str(e)}") from e


@router.get("/candidates", response_model=list[TransientCandidateResponse])
def list_candidates(
    min_significance: float = Query(5.0, description="Minimum significance threshold (sigma)"),
    detection_type: Optional[str] = Query(
        None, description="Filter by detection type (new_source, brightening, fading, variable)"
    ),
    limit: int = Query(50, description="Maximum number of candidates to return", ge=1, le=500),
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """List transient candidates with optional filtering."""
    from dsa110_contimg.catalog.transient_detection import get_transient_candidates

    try:
        # Build detection_types list if provided
        detection_types = [detection_type] if detection_type else None

        df = get_transient_candidates(
            min_significance=min_significance,
            detection_types=detection_types,
            limit=limit,
            db_path=db_path,
        )
        candidates = df.to_dict("records")
        return candidates
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query candidates: {str(e)}") from e


@router.get("/candidates/{candidate_id}", response_model=TransientCandidateResponse)
def get_candidate(
    candidate_id: int,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Get details for a specific candidate."""
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM transient_candidates WHERE id = ?", (candidate_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Candidate {candidate_id} not found")

        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get candidate: {str(e)}") from e


# Modification endpoints
@router.put("/alerts/{alert_id}/acknowledge")
def acknowledge_alert_endpoint(
    alert_id: int,
    request: AcknowledgeRequest,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Acknowledge an alert."""
    from dsa110_contimg.catalog.transient_detection import acknowledge_alert

    try:
        result = acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by=request.acknowledged_by,
            notes=request.notes,
            db_path=db_path,
        )
        return {"success": result, "alert_id": alert_id, "acknowledged_by": request.acknowledged_by}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}") from e


@router.put("/candidates/{candidate_id}/classify")
def classify_candidate_endpoint(
    candidate_id: int,
    request: ClassifyRequest,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Classify a transient candidate."""
    from dsa110_contimg.catalog.transient_detection import classify_candidate

    try:
        result = classify_candidate(
            candidate_id=candidate_id,
            classification=request.classification,
            classified_by=request.classified_by,
            notes=request.notes,
            db_path=db_path,
        )
        return {
            "success": result,
            "candidate_id": candidate_id,
            "classification": request.classification,
            "classified_by": request.classified_by,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to classify candidate: {str(e)}"
        ) from e


@router.put("/alerts/{alert_id}/follow-up")
def update_alert_follow_up(
    alert_id: int,
    request: FollowUpRequest,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Update follow-up status for an alert."""
    from dsa110_contimg.catalog.transient_detection import update_follow_up_status

    try:
        result = update_follow_up_status(
            item_id=alert_id,
            item_type="alert",
            status=request.status,
            notes=request.notes,
            db_path=db_path,
        )
        return {"success": result, "alert_id": alert_id, "status": request.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update follow-up status: {str(e)}"
        ) from e


@router.put("/candidates/{candidate_id}/follow-up")
def update_candidate_follow_up(
    candidate_id: int,
    request: FollowUpRequest,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Update follow-up status for a candidate."""
    from dsa110_contimg.catalog.transient_detection import update_follow_up_status

    try:
        result = update_follow_up_status(
            item_id=candidate_id,
            item_type="candidate",
            status=request.status,
            notes=request.notes,
            db_path=db_path,
        )
        return {"success": result, "candidate_id": candidate_id, "status": request.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update follow-up status: {str(e)}"
        ) from e


@router.put("/alerts/{alert_id}/notes")
def add_alert_notes(
    alert_id: int,
    request: NotesRequest,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Add or update notes for an alert."""
    from dsa110_contimg.catalog.transient_detection import add_notes

    try:
        result = add_notes(
            item_id=alert_id,
            item_type="alert",
            notes=request.notes,
            username=request.username,
            append=request.append,
            db_path=db_path,
        )
        return {
            "success": result,
            "alert_id": alert_id,
            "username": request.username,
            "append": request.append,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add notes: {str(e)}") from e


@router.put("/candidates/{candidate_id}/notes")
def add_candidate_notes(
    candidate_id: int,
    request: NotesRequest,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Add or update notes for a candidate."""
    from dsa110_contimg.catalog.transient_detection import add_notes

    try:
        result = add_notes(
            item_id=candidate_id,
            item_type="candidate",
            notes=request.notes,
            username=request.username,
            append=request.append,
            db_path=db_path,
        )
        return {
            "success": result,
            "candidate_id": candidate_id,
            "username": request.username,
            "append": request.append,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add notes: {str(e)}") from e


# Bulk operations
@router.post("/alerts/bulk-acknowledge")
def bulk_acknowledge_alerts(
    alert_ids: list[int],
    acknowledged_by: str,
    notes: Optional[str] = None,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Acknowledge multiple alerts at once."""
    from dsa110_contimg.catalog.transient_detection import acknowledge_alert

    results = {"success": [], "failed": []}

    for alert_id in alert_ids:
        try:
            acknowledge_alert(
                alert_id=alert_id, acknowledged_by=acknowledged_by, notes=notes, db_path=db_path
            )
            results["success"].append(alert_id)
        except Exception as e:
            results["failed"].append({"alert_id": alert_id, "error": str(e)})

    return {
        "total": len(alert_ids),
        "succeeded": len(results["success"]),
        "failed": len(results["failed"]),
        "results": results,
    }


@router.post("/candidates/bulk-classify")
def bulk_classify_candidates(
    candidate_ids: list[int],
    classification: str,
    classified_by: str,
    notes: Optional[str] = None,
    db_path: str = Query(
        "/data/dsa110-contimg/state/db/products.sqlite3", description="Path to products database"
    ),
):
    """Classify multiple candidates at once."""
    from dsa110_contimg.catalog.transient_detection import classify_candidate

    results = {"success": [], "failed": []}

    for candidate_id in candidate_ids:
        try:
            classify_candidate(
                candidate_id=candidate_id,
                classification=classification,
                classified_by=classified_by,
                notes=notes,
                db_path=db_path,
            )
            results["success"].append(candidate_id)
        except Exception as e:
            results["failed"].append({"candidate_id": candidate_id, "error": str(e)})

    return {
        "total": len(candidate_ids),
        "succeeded": len(results["success"]),
        "failed": len(results["failed"]),
        "results": results,
    }
