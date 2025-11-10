"""
API routes for QA visualization framework.

Provides endpoints for:
- Notebook generation
- Directory browsing
- FITS file viewing
- MS table browsing
- QA artifact exploration
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, Path as PathParam
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from dsa110_contimg.qa.visualization import (
    ls,
    FITSFile,
    CasaTable,
    generate_qa_notebook,
    generate_fits_viewer_notebook,
    generate_ms_explorer_notebook,
    browse_qa_outputs,
    display_qa_summary,
    generate_qa_notebook_from_result,
)
from dsa110_contimg.qa.casa_ms_qa import run_ms_qa, QaResult, QaThresholds
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visualization", tags=["visualization"])


# ============================================================================
# Request/Response Models
# ============================================================================

class DirectoryEntry(BaseModel):
    """Directory entry information."""
    name: str
    path: str
    type: str = Field(..., description="file, directory, fits, casatable")
    size: Optional[str] = None
    modified_time: Optional[datetime] = None
    is_dir: bool = False


class DirectoryListing(BaseModel):
    """Directory listing response."""
    path: str
    entries: List[DirectoryEntry]
    total_files: int = 0
    total_dirs: int = 0
    fits_count: int = 0
    casatable_count: int = 0


class FITSInfo(BaseModel):
    """FITS file information."""
    path: str
    exists: bool
    shape: Optional[List[int]] = None
    summary: Optional[str] = None
    header_keys: Optional[List[str]] = None
    naxis: Optional[int] = None
    error: Optional[str] = None


class CasaTableInfo(BaseModel):
    """CASA table information."""
    path: str
    exists: bool
    nrows: Optional[int] = None
    columns: Optional[List[str]] = None
    keywords: Optional[Dict[str, Any]] = None
    subtables: Optional[List[str]] = None
    is_writable: Optional[bool] = None
    error: Optional[str] = None


class NotebookGenerateRequest(BaseModel):
    """Request to generate a QA notebook."""
    ms_path: Optional[str] = None
    qa_root: Optional[str] = None
    artifacts: Optional[List[str]] = None
    title: Optional[str] = None
    output_path: Optional[str] = None


class NotebookGenerateResponse(BaseModel):
    """Response from notebook generation."""
    notebook_path: str
    success: bool
    message: Optional[str] = None


class QANotebookRequest(BaseModel):
    """Request to generate QA notebook from MS QA result."""
    ms_path: str
    qa_root: str
    thresholds: Optional[Dict[str, Any]] = None
    gaintables: Optional[List[str]] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    output_path: Optional[str] = None


# ============================================================================
# Directory Browsing Endpoints
# ============================================================================

@router.get("/browse", response_model=DirectoryListing)
def browse_directory(
    path: str = Query(..., description="Directory path to browse"),
    recursive: bool = Query(False, description="Recursive directory scan"),
    include_pattern: Optional[str] = Query(None, description="Include pattern (glob)"),
    exclude_pattern: Optional[str] = Query(None, description="Exclude pattern (glob)"),
):
    """
    Browse a directory and return file listing.
    
    Supports filtering by patterns and recursive scanning.
    """
    try:
        # Validate path is within allowed directories
        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        qa_base = base_state / "qa"
        
        # Resolve and validate path
        target_path = Path(path).resolve()
        
        # Ensure path is within allowed directories
        allowed_bases = [
            base_state.resolve(),
            qa_base.resolve(),
            Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms")).resolve(),
        ]
        
        if not any(str(target_path).startswith(str(base)) for base in allowed_bases):
            raise HTTPException(
                status_code=403,
                detail=f"Path {path} is outside allowed directories"
            )
        
        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")
        
        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
        
        # Browse directory using DataDir
        from dsa110_contimg.qa.visualization.datadir import DataDir
        qa_dir = DataDir(str(target_path), recursive=recursive)
        
        # Apply filters
        if include_pattern:
            qa_dir = qa_dir.include(include_pattern)
        if exclude_pattern:
            qa_dir = qa_dir.exclude(exclude_pattern)
        
        # Convert to API response
        entries = []
        for item in qa_dir:
            entry = DirectoryEntry(
                name=item.basename,
                path=item.fullpath,
                type=item.file_type,
                size=item.size,
                modified_time=datetime.fromtimestamp(item.mtime) if item.mtime else None,
                is_dir=item.is_dir,
            )
            entries.append(entry)
        
        return DirectoryListing(
            path=str(target_path),
            entries=entries,
            total_files=qa_dir.nfiles,
            total_dirs=qa_dir.ndirs,
            fits_count=len(qa_dir.fits),
            casatable_count=len(qa_dir.tables),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error browsing directory {path}")
        raise HTTPException(status_code=500, detail=f"Error browsing directory: {str(e)}")


# ============================================================================
# FITS File Endpoints
# ============================================================================

@router.get("/fits/info", response_model=FITSInfo)
def get_fits_info(
    path: str = Query(..., description="Path to FITS file"),
):
    """Get information about a FITS file."""
    try:
        # Validate path
        target_path = Path(path).resolve()
        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"FITS file not found: {path}")
        
        fits_file = FITSFile(str(target_path))
        
        return FITSInfo(
            path=str(target_path),
            exists=fits_file.exists,
            shape=fits_file.shape if fits_file.exists else None,
            summary=str(fits_file.summary) if fits_file.exists else None,
            header_keys=list(fits_file.hdrobj.keys()) if fits_file.exists and hasattr(fits_file, 'hdrobj') else None,
            naxis=fits_file.hdrobj.get('NAXIS') if fits_file.exists and hasattr(fits_file, 'hdrobj') else None,
            error=None,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error reading FITS file {path}")
        return FITSInfo(
            path=path,
            exists=False,
            error=str(e),
        )


@router.get("/fits/view")
def view_fits_file(
    path: str = Query(..., description="Path to FITS file"),
    width: int = Query(600, description="Display width in pixels"),
    height: int = Query(600, description="Display height in pixels"),
):
    """
    Get HTML for viewing a FITS file with JS9.
    
    Returns HTML that can be embedded in the dashboard.
    """
    try:
        target_path = Path(path).resolve()
        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"FITS file not found: {path}")
        
        fits_file = FITSFile(str(target_path))
        
        # Generate JS9 HTML
        fits_file._setup_summary()
        summary_html = fits_file._render_summary_html()
        js9_html = fits_file._render_js9_html(width=width, height=height)
        
        full_html = summary_html + js9_html
        
        return HTMLResponse(content=full_html)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating FITS viewer HTML for {path}")
        raise HTTPException(status_code=500, detail=f"Error generating viewer: {str(e)}")


# ============================================================================
# CASA Table Endpoints
# ============================================================================

@router.get("/casatable/info", response_model=CasaTableInfo)
def get_casatable_info(
    path: str = Query(..., description="Path to CASA table (MS directory)"),
):
    """Get information about a CASA Measurement Set table."""
    try:
        target_path = Path(path).resolve()
        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"CASA table not found: {path}")
        
        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
        
        casa_table = CasaTable(str(target_path))
        casa_table.rescan()
        
        return CasaTableInfo(
            path=str(target_path),
            exists=casa_table.exists,
            nrows=casa_table.nrows if casa_table.exists else None,
            columns=casa_table.columns if casa_table.exists else None,
            keywords=casa_table.keywords if casa_table.exists else None,
            subtables=[str(s) for s in casa_table.subtables] if casa_table.exists else None,
            is_writable=casa_table._is_writable if casa_table.exists else None,
            error=casa_table._error if hasattr(casa_table, '_error') else None,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error reading CASA table {path}")
        return CasaTableInfo(
            path=path,
            exists=False,
            error=str(e),
        )


@router.get("/casatable/view")
def view_casatable(
    path: str = Query(..., description="Path to CASA table"),
    max_rows: int = Query(10, description="Maximum rows to display"),
    max_cols: int = Query(5, description="Maximum columns to display"),
):
    """
    Get HTML for viewing a CASA table summary.
    
    Returns HTML that can be embedded in the dashboard.
    """
    try:
        target_path = Path(path).resolve()
        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"CASA table not found: {path}")
        
        casa_table = CasaTable(str(target_path))
        casa_table.rescan()
        
        # Generate HTML summary
        casa_table.show(max_rows=max_rows, max_cols=max_cols)
        
        # Note: show() uses display() which won't work in API context
        # We need to generate HTML directly
        html = f'<div class="qa-casatable-summary"><h3>CASA Table: {casa_table.basename}</h3>'
        html += f'<p>Path: {casa_table.fullpath}</p>'
        html += f'<p>Rows: {casa_table.nrows:,}</p>'
        html += f'<p>Columns: {len(casa_table.columns)}</p>'
        html += '</div>'
        
        return HTMLResponse(content=html)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating CASA table viewer HTML for {path}")
        raise HTTPException(status_code=500, detail=f"Error generating viewer: {str(e)}")


# ============================================================================
# Notebook Generation Endpoints
# ============================================================================

@router.post("/notebook/generate", response_model=NotebookGenerateResponse)
def generate_notebook(request: NotebookGenerateRequest):
    """
    Generate a QA notebook programmatically.
    
    Creates a Jupyter notebook for exploring QA results, FITS files, or MS tables.
    """
    try:
        notebook_path = generate_qa_notebook(
            ms_path=request.ms_path,
            qa_root=request.qa_root,
            artifacts=request.artifacts,
            output_path=request.output_path,
            title=request.title,
        )
        
        return NotebookGenerateResponse(
            notebook_path=notebook_path,
            success=True,
            message=f"Notebook generated successfully: {notebook_path}",
        )
    
    except Exception as e:
        logger.exception("Error generating notebook")
        raise HTTPException(status_code=500, detail=f"Error generating notebook: {str(e)}")


@router.post("/notebook/qa", response_model=NotebookGenerateResponse)
def generate_qa_notebook_endpoint(request: QANotebookRequest):
    """
    Run MS QA and generate an interactive notebook from the results.
    
    This combines QA execution with notebook generation.
    """
    try:
        # Run QA
        thresholds = QaThresholds(**(request.thresholds or {})) if request.thresholds else None
        
        qa_result = run_ms_qa(
            ms_path=request.ms_path,
            qa_root=request.qa_root,
            thresholds=thresholds,
            gaintables=request.gaintables,
            extra_metadata=request.extra_metadata,
        )
        
        # Generate notebook from result
        notebook_path = generate_qa_notebook_from_result(
            qa_result,
            output_path=request.output_path,
        )
        
        return NotebookGenerateResponse(
            notebook_path=notebook_path,
            success=True,
            message=f"QA notebook generated successfully: {notebook_path}",
        )
    
    except Exception as e:
        logger.exception("Error generating QA notebook")
        raise HTTPException(status_code=500, detail=f"Error generating QA notebook: {str(e)}")


@router.get("/notebook/{notebook_path:path}")
def serve_notebook(notebook_path: str):
    """
    Serve a generated notebook file.
    
    Returns the notebook file for download or viewing.
    """
    try:
        # Validate path
        target_path = Path(notebook_path).resolve()
        
        # Ensure it's a .ipynb file
        if not target_path.suffix == '.ipynb':
            raise HTTPException(status_code=400, detail="Not a notebook file")
        
        # Ensure it exists
        if not target_path.exists():
            raise HTTPException(status_code=404, detail="Notebook not found")
        
        return FileResponse(
            str(target_path),
            media_type="application/json",
            filename=target_path.name,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error serving notebook {notebook_path}")
        raise HTTPException(status_code=500, detail=f"Error serving notebook: {str(e)}")


# ============================================================================
# QA Integration Endpoints
# ============================================================================

@router.get("/qa/browse")
def browse_qa_directory(
    qa_root: str = Query(..., description="QA root directory"),
):
    """
    Browse QA output directory interactively.
    
    Returns directory listing with QA artifacts.
    """
    try:
        qa_dir = browse_qa_outputs(qa_root)
        qa_dir.rescan()
        
        entries = []
        for item in qa_dir:
            entries.append(DirectoryEntry(
                name=item.basename,
                path=item.fullpath,
                type=item.file_type,
                size=item.size,
                modified_time=datetime.fromtimestamp(item.mtime) if item.mtime else None,
                is_dir=item.is_dir,
            ))
        
        return DirectoryListing(
            path=qa_root,
            entries=entries,
            total_files=qa_dir.nfiles,
            total_dirs=qa_dir.ndirs,
            fits_count=len(qa_dir.fits),
            casatable_count=len(qa_dir.tables),
        )
    
    except Exception as e:
        logger.exception(f"Error browsing QA directory {qa_root}")
        raise HTTPException(status_code=500, detail=f"Error browsing QA directory: {str(e)}")

