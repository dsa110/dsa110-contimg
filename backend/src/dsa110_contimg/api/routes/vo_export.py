"""
VO Export API routes.

Manage export jobs to Virtual Observatory formats (VOTable, FITS, CSV).
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ..dependencies import get_pipeline_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vo", tags=["vo-export"])

# Configuration
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "/stage/dsa110-contimg/exports"))


# ============================================================================
# Pydantic Models
# ============================================================================


class ExportRequest(BaseModel):
    """Request to create an export job."""

    export_type: str = Field(..., pattern="^(votable|csv|fits|tar)$")
    target_type: str = Field(..., pattern="^(sources|images|ms|catalog)$")
    query_params: Optional[Dict[str, Any]] = None  # Filters, IDs, etc.
    include_metadata: bool = True
    compress: bool = False


class ExportJob(BaseModel):
    """Export job information."""

    id: str
    export_type: str
    target_type: str
    query_params: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None
    status: str  # pending, running, completed, failed, cancelled
    progress_pct: int = 0
    total_items: Optional[int] = None
    processed_items: int = 0
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    download_url: Optional[str] = None


class ExportJobListResponse(BaseModel):
    """Response for listing export jobs."""

    jobs: List[ExportJob]
    total: int


class ExportProgress(BaseModel):
    """Progress update for an export job."""

    id: str
    status: str
    progress_pct: int
    processed_items: int
    total_items: Optional[int] = None
    eta_seconds: Optional[int] = None


# ============================================================================
# Helpers
# ============================================================================


def _row_to_job(row: sqlite3.Row) -> ExportJob:
    """Convert database row to ExportJob model."""
    query_params = None
    if row["query_params"]:
        try:
            query_params = json.loads(row["query_params"])
        except json.JSONDecodeError:
            pass
    
    download_url = None
    if row["status"] == "completed" and row["output_path"]:
        download_url = f"/api/vo-export/{row['id']}/download"
    
    return ExportJob(
        id=row["id"],
        export_type=row["export_type"],
        target_type=row["target_type"],
        query_params=query_params,
        output_path=row["output_path"],
        status=row["status"],
        progress_pct=row["progress_pct"] or 0,
        total_items=row["total_items"],
        processed_items=row["processed_items"] or 0,
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        error_message=row["error_message"],
        download_url=download_url,
    )


def _get_current_user() -> str:
    """Get current user. Placeholder for auth integration."""
    return "default_user"


# ============================================================================
# Background Export Tasks
# ============================================================================


def _run_export(job_id: str, export_type: str, target_type: str, query_params: Optional[Dict], db_path: Path):
    """Execute export job in background."""
    import time
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    try:
        # Update status to running
        now = datetime.utcnow().isoformat()
        conn.execute(
            "UPDATE export_jobs SET status = 'running', started_at = ? WHERE id = ?",
            (now, job_id),
        )
        conn.commit()
        
        # Determine output path
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        ext_map = {"votable": "xml", "csv": "csv", "fits": "fits", "tar": "tar.gz"}
        ext = ext_map.get(export_type, "dat")
        output_path = EXPORT_DIR / f"{target_type}_{timestamp}_{job_id[:8]}.{ext}"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get items to export
        if target_type == "sources":
            items = _export_sources(conn, query_params, export_type, output_path)
        elif target_type == "images":
            items = _export_images(conn, query_params, export_type, output_path)
        elif target_type == "catalog":
            items = _export_catalog(conn, query_params, export_type, output_path)
        else:
            items = 0
        
        # Mark completed
        conn.execute(
            """
            UPDATE export_jobs 
            SET status = 'completed', completed_at = ?, output_path = ?,
                progress_pct = 100, processed_items = ?, total_items = ?
            WHERE id = ?
            """,
            (datetime.utcnow().isoformat(), str(output_path), items, items, job_id),
        )
        conn.commit()
        logger.info(f"Export job {job_id} completed: {items} items")
        
    except Exception as e:
        logger.error(f"Export job {job_id} failed: {e}")
        conn.execute(
            "UPDATE export_jobs SET status = 'failed', error_message = ? WHERE id = ?",
            (str(e), job_id),
        )
        conn.commit()
    finally:
        conn.close()


def _export_sources(conn: sqlite3.Connection, query_params: Optional[Dict], export_type: str, output_path: Path) -> int:
    """Export sources to specified format."""
    # Query sources
    sql = "SELECT * FROM sources"
    params = []
    
    if query_params:
        conditions = []
        if "min_flux" in query_params:
            conditions.append("flux_mjy >= ?")
            params.append(query_params["min_flux"])
        if "max_flux" in query_params:
            conditions.append("flux_mjy <= ?")
            params.append(query_params["max_flux"])
        if "dec_min" in query_params:
            conditions.append("dec_deg >= ?")
            params.append(query_params["dec_min"])
        if "dec_max" in query_params:
            conditions.append("dec_deg <= ?")
            params.append(query_params["dec_max"])
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
    
    cursor = conn.execute(sql, params)
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    if export_type == "votable":
        _write_votable(rows, output_path, "sources")
    elif export_type == "csv":
        _write_csv(rows, output_path)
    elif export_type == "fits":
        _write_fits_table(rows, output_path)
    
    return len(rows)


def _export_images(conn: sqlite3.Connection, query_params: Optional[Dict], export_type: str, output_path: Path) -> int:
    """Export image metadata to specified format."""
    sql = "SELECT * FROM images"
    params = []
    
    if query_params:
        conditions = []
        if "image_type" in query_params:
            conditions.append("type = ?")
            params.append(query_params["image_type"])
        if "date_start" in query_params:
            conditions.append("created_at >= ?")
            params.append(query_params["date_start"])
        if "date_end" in query_params:
            conditions.append("created_at <= ?")
            params.append(query_params["date_end"])
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
    
    cursor = conn.execute(sql, params)
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    if export_type == "votable":
        _write_votable(rows, output_path, "images")
    elif export_type == "csv":
        _write_csv(rows, output_path)
    
    return len(rows)


def _export_catalog(conn: sqlite3.Connection, query_params: Optional[Dict], export_type: str, output_path: Path) -> int:
    """Export full catalog with cross-matches."""
    # Join sources with photometry and cross-matches
    sql = """
        SELECT s.*, p.flux_peak, p.flux_int, p.rms_local
        FROM sources s
        LEFT JOIN photometry_results p ON s.id = p.source_id
    """
    
    cursor = conn.execute(sql)
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    if export_type == "votable":
        _write_votable(rows, output_path, "dsa110_catalog")
    elif export_type == "csv":
        _write_csv(rows, output_path)
    elif export_type == "fits":
        _write_fits_table(rows, output_path)
    
    return len(rows)


def _write_votable(rows: List[sqlite3.Row], output_path: Path, table_name: str):
    """Write rows to VOTable format."""
    # Simple VOTable XML output
    with open(output_path, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<VOTABLE version="1.4" xmlns="http://www.ivoa.net/xml/VOTable/v1.4">\n')
        f.write(f'  <RESOURCE name="{table_name}">\n')
        f.write(f'    <TABLE name="{table_name}">\n')
        
        if rows:
            # Write fields
            keys = rows[0].keys()
            for key in keys:
                f.write(f'      <FIELD name="{key}" datatype="char" arraysize="*"/>\n')
            
            # Write data
            f.write('      <DATA>\n')
            f.write('        <TABLEDATA>\n')
            for row in rows:
                f.write('          <TR>\n')
                for key in keys:
                    val = row[key] if row[key] is not None else ""
                    f.write(f'            <TD>{val}</TD>\n')
                f.write('          </TR>\n')
            f.write('        </TABLEDATA>\n')
            f.write('      </DATA>\n')
        
        f.write('    </TABLE>\n')
        f.write('  </RESOURCE>\n')
        f.write('</VOTABLE>\n')


def _write_csv(rows: List[sqlite3.Row], output_path: Path):
    """Write rows to CSV format."""
    import csv
    
    with open(output_path, "w", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))


def _write_fits_table(rows: List[sqlite3.Row], output_path: Path):
    """Write rows to FITS table format."""
    try:
        from astropy.io import fits
        from astropy.table import Table
        
        if rows:
            data = {key: [row[key] for row in rows] for key in rows[0].keys()}
            table = Table(data)
            table.write(output_path, format="fits", overwrite=True)
        else:
            # Empty FITS file
            hdu = fits.PrimaryHDU()
            hdu.writeto(output_path, overwrite=True)
    except ImportError:
        # Fallback if astropy not available
        with open(output_path, "wb") as f:
            f.write(b"FITS format requires astropy")


# ============================================================================
# Endpoints
# ============================================================================


class ExportJobList(BaseModel):
    """List of export jobs response."""
    jobs: List[ExportJob]
    total: int


@router.get("/exports", response_model=ExportJobList)
async def list_exports(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """List export jobs."""
    if status:
        cursor = db.execute(
            "SELECT * FROM export_jobs WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        )
    else:
        cursor = db.execute(
            "SELECT * FROM export_jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    jobs = [_row_to_job(row) for row in rows]
    
    # Get total count
    count_cursor = db.execute("SELECT COUNT(*) FROM export_jobs")
    total = count_cursor.fetchone()[0]
    
    return ExportJobList(jobs=jobs, total=total)


@router.post("/exports", response_model=ExportJob, status_code=201)
async def create_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Create a new export job."""
    current_user = _get_current_user()
    job_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    query_params_json = json.dumps(request.query_params) if request.query_params else None
    
    db.execute(
        """
        INSERT INTO export_jobs (id, export_type, target_type, query_params, status, created_at, created_by)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
        """,
        (job_id, request.export_type, request.target_type, query_params_json, now, current_user),
    )
    db.commit()
    
    # Get DB path for background task
    db_path = Path(os.getenv("PIPELINE_DB", "/data/dsa110-contimg/state/db/pipeline.sqlite3"))
    
    # Schedule background export
    background_tasks.add_task(
        _run_export,
        job_id,
        request.export_type,
        request.target_type,
        request.query_params,
        db_path,
    )
    
    return ExportJob(
        id=job_id,
        export_type=request.export_type,
        target_type=request.target_type,
        query_params=request.query_params,
        status="pending",
        created_at=now,
    )


@router.get("/exports/{job_id}", response_model=ExportJob)
async def get_export_status(
    job_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get status of an export job."""
    cursor = db.execute("SELECT * FROM export_jobs WHERE id = ?", (job_id,))
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
    
    return _row_to_job(row)


@router.get("/progress/{job_id}", response_model=ExportProgress)
async def get_export_progress(
    job_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Get progress of an export job (for polling)."""
    cursor = db.execute(
        "SELECT id, status, progress_pct, processed_items, total_items FROM export_jobs WHERE id = ?",
        (job_id,),
    )
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
    
    return ExportProgress(
        id=row["id"],
        status=row["status"],
        progress_pct=row["progress_pct"] or 0,
        processed_items=row["processed_items"] or 0,
        total_items=row["total_items"],
    )


@router.get("/{job_id}/download")
async def download_export(
    job_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Download completed export file."""
    cursor = db.execute(
        "SELECT output_path, status, export_type FROM export_jobs WHERE id = ?",
        (job_id,),
    )
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
    
    if row[1] != "completed":
        raise HTTPException(status_code=400, detail="Export not yet completed")
    
    output_path = Path(row[0])
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # Determine media type
    media_types = {
        "votable": "application/xml",
        "csv": "text/csv",
        "fits": "application/fits",
        "tar": "application/gzip",
    }
    media_type = media_types.get(row[2], "application/octet-stream")
    
    return FileResponse(
        path=output_path,
        filename=output_path.name,
        media_type=media_type,
    )


@router.get("/jobs", response_model=ExportJobListResponse)
async def list_export_jobs(
    status: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """List export jobs."""
    conditions = []
    params = []
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    if target_type:
        conditions.append("target_type = ?")
        params.append(target_type)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    params.append(limit)
    
    cursor = db.execute(
        f"""
        SELECT * FROM export_jobs
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        params,
    )
    cursor.row_factory = sqlite3.Row
    rows = cursor.fetchall()
    
    jobs = [_row_to_job(row) for row in rows]
    return ExportJobListResponse(jobs=jobs, total=len(jobs))


@router.post("/{job_id}/cancel", response_model=ExportJob)
async def cancel_export(
    job_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Cancel a pending or running export job."""
    cursor = db.execute("SELECT status FROM export_jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
    
    if row[0] not in ("pending", "running"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel job with status '{row[0]}'")
    
    db.execute(
        "UPDATE export_jobs SET status = 'cancelled' WHERE id = ?",
        (job_id,),
    )
    db.commit()
    
    cursor = db.execute("SELECT * FROM export_jobs WHERE id = ?", (job_id,))
    cursor.row_factory = sqlite3.Row
    row = cursor.fetchone()
    
    return _row_to_job(row)


@router.delete("/{job_id}", status_code=204)
async def delete_export(
    job_id: str,
    db: sqlite3.Connection = Depends(get_pipeline_db),
):
    """Delete an export job and its output file."""
    cursor = db.execute("SELECT output_path FROM export_jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail=f"Export job {job_id} not found")
    
    # Delete output file if exists
    if row[0]:
        output_path = Path(row[0])
        if output_path.exists():
            output_path.unlink()
    
    db.execute("DELETE FROM export_jobs WHERE id = ?", (job_id,))
    db.commit()
    
    return None
