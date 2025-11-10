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
import numpy as np

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
    include_pattern: Optional[str] = Query(
        None, description="Include pattern (glob)"),
    exclude_pattern: Optional[str] = Query(
        None, description="Exclude pattern (glob)"),
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
        # Include both relative and absolute paths for flexibility
        allowed_bases = [
            base_state.resolve(),
            qa_base.resolve(),
            Path(os.getenv("PIPELINE_OUTPUT_DIR",
                 "/stage/dsa110-contimg/ms")).resolve(),
        ]

        # Also allow browsing within /data/dsa110-contimg (common deployment path)
        # This allows users to browse from /data down to the project directory
        data_base = Path("/data/dsa110-contimg")
        if data_base.exists():
            allowed_bases.append(data_base.resolve())

        # Allow browsing /data itself (parent directory) for navigation purposes
        # This enables users to navigate from /data to /data/dsa110-contimg
        data_root = Path("/data")
        if data_root.exists():
            allowed_bases.append(data_root.resolve())

        # Allow browsing root directory (/) for full system navigation
        # Note: This enables browsing from root, but users can still only access
        # paths within the allowed bases listed above
        root_path = Path("/")
        if root_path.exists():
            allowed_bases.append(root_path.resolve())

        # Check if path is within any allowed base
        path_allowed = False
        for base in allowed_bases:
            try:
                # Use relative_to to properly handle path containment (handles symlinks)
                target_path.relative_to(base.resolve())
                path_allowed = True
                break
            except ValueError:
                # Path is not within this base, try next
                continue

        if not path_allowed:
            raise HTTPException(
                status_code=403,
                detail=f"Path {path} is outside allowed directories. Allowed: {[str(b) for b in allowed_bases]}"
            )

        if not target_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Path not found: {path}")

        if not target_path.is_dir():
            raise HTTPException(
                status_code=400, detail=f"Path is not a directory: {path}")

        # Browse directory using DataDir
        from dsa110_contimg.qa.visualization.datadir import DataDir
        try:
            qa_dir = DataDir(str(target_path), recursive=recursive)

            # Apply filters
            if include_pattern:
                qa_dir = qa_dir.include(include_pattern)
            if exclude_pattern:
                qa_dir = qa_dir.exclude(exclude_pattern)

            # Convert to API response
            entries = []
            for item in qa_dir:
                # Determine file type - FileBase uses isdir (not is_dir)
                is_directory = getattr(item, 'isdir', False) or getattr(
                    item, 'is_dir', False)
                file_type = "directory" if is_directory else "file"
                if not is_directory:
                    # Use autodetect_file_type for file type detection
                    from dsa110_contimg.qa.visualization.file import autodetect_file_type
                    detected_type = autodetect_file_type(item.fullpath)
                    if detected_type == "fits":
                        file_type = "fits"
                    elif detected_type == "casatable":
                        file_type = "casatable"

                # Format size as human-readable string
                size_bytes = getattr(item, 'size', 0)
                if isinstance(size_bytes, int):
                    if size_bytes == 0:
                        size_str = "0 B"
                    elif size_bytes < 1024:
                        size_str = f"{size_bytes} B"
                    elif size_bytes < 1024 * 1024:
                        size_str = f"{size_bytes / 1024:.1f} KB"
                    elif size_bytes < 1024 * 1024 * 1024:
                        size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                    else:
                        size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
                else:
                    size_str = str(size_bytes) if size_bytes else "0 B"

                entry = DirectoryEntry(
                    name=item.basename,
                    path=item.fullpath,
                    type=file_type,
                    size=size_str,
                    modified_time=datetime.fromtimestamp(
                        item.mtime) if item.mtime else None,
                    is_dir=is_directory,
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
        except (PermissionError, OSError) as e:
            # Handle permission errors gracefully when browsing root or system directories
            # Return empty listing with error message in detail
            logger.warning(f"Permission error browsing {path}: {e}")
            return DirectoryListing(
                path=str(target_path),
                entries=[],
                total_files=0,
                total_dirs=0,
                fits_count=0,
                casatable_count=0,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error browsing directory {path}")
        raise HTTPException(
            status_code=500, detail=f"Error browsing directory: {str(e)}")


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
            raise HTTPException(
                status_code=404, detail=f"FITS file not found: {path}")

        fits_file = FITSFile(str(target_path))

        return FITSInfo(
            path=str(target_path),
            exists=fits_file.exists,
            shape=fits_file.shape if fits_file.exists else None,
            summary=str(fits_file.summary) if fits_file.exists else None,
            header_keys=list(fits_file.hdrobj.keys()) if fits_file.exists and hasattr(
                fits_file, 'hdrobj') else None,
            naxis=fits_file.hdrobj.get('NAXIS') if fits_file.exists and hasattr(
                fits_file, 'hdrobj') else None,
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
            raise HTTPException(
                status_code=404, detail=f"FITS file not found: {path}")

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
        raise HTTPException(
            status_code=500, detail=f"Error generating viewer: {str(e)}")


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
            raise HTTPException(
                status_code=404, detail=f"CASA table not found: {path}")

        if not target_path.is_dir():
            raise HTTPException(
                status_code=400, detail=f"Path is not a directory: {path}")

        casa_table = CasaTable(str(target_path))
        # CasaTable scans automatically in __init__ if path exists
        # Access properties to ensure scanning is complete
        _ = casa_table.nrows  # This triggers scanning if needed

        return CasaTableInfo(
            path=str(target_path),
            exists=casa_table.exists,
            nrows=casa_table.nrows if casa_table.exists else None,
            columns=casa_table.columns if casa_table.exists else None,
            keywords=casa_table.keywords if casa_table.exists else None,
            subtables=[
                str(s) for s in casa_table.subtables] if casa_table.exists else None,
            is_writable=casa_table._writeable if casa_table.exists else None,
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
            raise HTTPException(
                status_code=404, detail=f"CASA table not found: {path}")

        casa_table = CasaTable(str(target_path))
        # CasaTable scans automatically in __init__ if path exists
        # Access properties to ensure scanning is complete
        _ = casa_table.nrows  # This triggers scanning if needed

        # Generate HTML summary directly (show() uses display() which won't work in API context)
        html = f'<div class="qa-casatable-summary"><h3>CASA Table: {casa_table.basename}</h3>'
        html += f'<p>Path: {casa_table.fullpath}</p>'
        html += f'<p>Rows: {casa_table.nrows:,}</p>'
        html += f'<p>Columns: {len(casa_table.columns)}</p>'

        # Display sample rows if available
        if casa_table.nrows > 0 and casa_table.columns:
            html += '<div class="qa-casatable-sample"><h4>Sample Rows:</h4>'
            sample_cols = casa_table.columns[:max_cols]
            html += '<table><tr><th>Row</th>'
            for col in sample_cols:
                html += f'<th>{col}</th>'
            html += '</tr>'

            try:
                for i in range(min(max_rows, casa_table.nrows)):
                    html += f'<tr><td>{i}</td>'
                    for col in sample_cols:
                        val = casa_table.getcol(col, start=i, nrow=1)
                        if isinstance(val, np.ndarray) and val.size > 1:
                            html += f'<td>Array({val.shape})</td>'
                        elif isinstance(val, np.ndarray) and val.size == 1:
                            html += f'<td>{val.item()}</td>'
                        else:
                            html += f'<td>{val}</td>'
                    html += '</tr>'
            except Exception as e:
                html += f'<tr><td colspan="{len(sample_cols)+1}">Error reading sample data: {e}</td></tr>'

            html += '</table></div>'

        html += '</div>'

        return HTMLResponse(content=html)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating CASA table viewer HTML for {path}")
        raise HTTPException(
            status_code=500, detail=f"Error generating viewer: {str(e)}")


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
        raise HTTPException(
            status_code=500, detail=f"Error generating notebook: {str(e)}")


@router.post("/notebook/qa", response_model=NotebookGenerateResponse)
def generate_qa_notebook_endpoint(request: QANotebookRequest):
    """
    Run MS QA and generate an interactive notebook from the results.

    This combines QA execution with notebook generation.
    """
    try:
        # Run QA
        thresholds = QaThresholds(
            **(request.thresholds or {})) if request.thresholds else None

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
        raise HTTPException(
            status_code=500, detail=f"Error generating QA notebook: {str(e)}")


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
        raise HTTPException(
            status_code=500, detail=f"Error serving notebook: {str(e)}")


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
        # browse_qa_outputs returns a DataDir, use it directly
        from dsa110_contimg.qa.visualization.datadir import DataDir
        qa_dir = DataDir(qa_root)
        qa_dir.rescan()

        entries = []
        for item in qa_dir:
            # Determine file type - FileBase uses isdir (not is_dir)
            is_directory = getattr(item, 'isdir', False) or getattr(
                item, 'is_dir', False)
            file_type = "directory" if is_directory else "file"
            if not is_directory:
                from dsa110_contimg.qa.visualization.file import autodetect_file_type
                detected_type = autodetect_file_type(item.fullpath)
                if detected_type == "fits":
                    file_type = "fits"
                elif detected_type == "casatable":
                    file_type = "casatable"

            # Format size as human-readable string
            size_bytes = getattr(item, 'size', 0)
            if isinstance(size_bytes, int):
                if size_bytes == 0:
                    size_str = "0 B"
                elif size_bytes < 1024:
                    size_str = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            else:
                size_str = str(size_bytes) if size_bytes else "0 B"

            entries.append(DirectoryEntry(
                name=item.basename,
                path=item.fullpath,
                type=file_type,
                size=size_str,
                modified_time=datetime.fromtimestamp(
                    item.mtime) if item.mtime else None,
                is_dir=is_directory,
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
        raise HTTPException(
            status_code=500, detail=f"Error browsing QA directory: {str(e)}")


# ============================================================================
# Demo/Viewer Page
# ============================================================================

@router.get("/viewer", response_class=HTMLResponse)
def visualization_viewer():
    """
    Serve a formatted HTML viewer page for testing visualization endpoints.

    This page provides a user-friendly interface to browse and view QA data.
    """
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DSA-110 QA Visualization Viewer</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 {
            font-size: 2em;
            margin-bottom: 10px;
        }
        .subtitle {
            opacity: 0.9;
            font-size: 1.1em;
        }
        .section {
            background: white;
            border-radius: 8px;
            padding: 25px;
            margin-bottom: 25px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555;
        }
        input[type="text"], input[type="number"] {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus, input[type="number"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            transition: background 0.3s;
            margin-right: 10px;
            margin-top: 10px;
        }
        button:hover {
            background: #5568d3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 5px;
            background: #f9f9f9;
            border-left: 4px solid #667eea;
            display: none;
        }
        .result.show {
            display: block;
        }
        .result.error {
            border-left-color: #e74c3c;
            background: #fee;
        }
        .result.success {
            border-left-color: #27ae60;
            background: #efe;
        }
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            font-size: 13px;
            line-height: 1.5;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .file-list {
            list-style: none;
            padding: 0;
        }
        .file-item {
            padding: 12px;
            border-bottom: 1px solid #eee;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .file-item:hover {
            background: #f5f5f5;
        }
        .file-item:last-child {
            border-bottom: none;
        }
        .file-name {
            font-weight: 600;
            color: #333;
        }
        .file-meta {
            font-size: 0.9em;
            color: #666;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: 600;
            margin-left: 10px;
        }
        .badge.directory {
            background: #e3f2fd;
            color: #1976d2;
        }
        .badge.fits {
            background: #fff3e0;
            color: #f57c00;
        }
        .badge.casatable {
            background: #f3e5f5;
            color: #7b1fa2;
        }
        .badge.file {
            background: #e8f5e9;
            color: #388e3c;
        }
        .stats {
            display: flex;
            gap: 20px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        .stat {
            background: #f0f0f0;
            padding: 10px 15px;
            border-radius: 5px;
            text-align: center;
        }
        .stat-value {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>DSA-110 QA Visualization Viewer</h1>
            <p class="subtitle">Interactive interface for exploring QA data, FITS files, and Measurement Sets</p>
        </header>

        <div class="section">
            <h2>Browse Directory</h2>
            <div class="form-group">
                <label for="browse-path">Directory Path:</label>
                <input type="text" id="browse-path" placeholder="/data/dsa110-contimg/state/qa" value="/data/dsa110-contimg/state/qa">
            </div>
            <div class="form-group">
                <label>
                    <input type="checkbox" id="browse-recursive"> Recursive
                </label>
            </div>
            <button onclick="browseDirectory()">Browse Directory</button>
            <div id="browse-result" class="result"></div>
        </div>

        <div class="section">
            <h2>View FITS File</h2>
            <div class="form-group">
                <label for="fits-path">FITS File Path:</label>
                <input type="text" id="fits-path" placeholder="/data/dsa110-contimg/state/images/example.fits">
            </div>
            <button onclick="getFITSInfo()">Get FITS Info</button>
            <button onclick="viewFITS()">View FITS File</button>
            <div id="fits-result" class="result"></div>
        </div>

        <div class="section">
            <h2>View CASA Table</h2>
            <div class="form-group">
                <label for="casatable-path">CASA Table Path (MS directory):</label>
                <input type="text" id="casatable-path" placeholder="/data/dsa110-contimg/state/ms/science/2025-10-28/2025-10-28T13:55:53.ms" value="/data/dsa110-contimg/state/ms/science/2025-10-28/2025-10-28T13:55:53.ms">
            </div>
            <button onclick="getCasaTableInfo()">Get Table Info</button>
            <button onclick="viewCasaTable()">View Table</button>
            <div id="casatable-result" class="result"></div>
        </div>
    </div>

    <script>
        const API_BASE = '/api/visualization';

        function showResult(elementId, content, isError = false) {
            const element = document.getElementById(elementId);
            element.className = 'result show ' + (isError ? 'error' : 'success');
            element.innerHTML = content;
        }

        function formatJSON(obj) {
            return '<pre>' + JSON.stringify(obj, null, 2) + '</pre>';
        }

        function formatDirectoryListing(data) {
            let html = '<div class="stats">';
            html += `<div class="stat"><div class="stat-value">${data.total_files}</div><div class="stat-label">Files</div></div>`;
            html += `<div class="stat"><div class="stat-value">${data.total_dirs}</div><div class="stat-label">Directories</div></div>`;
            html += `<div class="stat"><div class="stat-value">${data.fits_count}</div><div class="stat-label">FITS Files</div></div>`;
            html += `<div class="stat"><div class="stat-value">${data.casatable_count}</div><div class="stat-label">CASA Tables</div></div>`;
            html += '</div>';
            html += '<ul class="file-list">';
            data.entries.forEach(entry => {
                const badgeClass = entry.type === 'directory' ? 'directory' : 
                                 entry.type === 'fits' ? 'fits' : 
                                 entry.type === 'casatable' ? 'casatable' : 'file';
                html += `<li class="file-item">
                    <div>
                        <span class="file-name">${entry.name}</span>
                        <span class="badge ${badgeClass}">${entry.type}</span>
                    </div>
                    <div class="file-meta">
                        ${entry.size || 'N/A'} | ${entry.modified_time ? new Date(entry.modified_time).toLocaleString() : 'N/A'}
                    </div>
                </li>`;
            });
            html += '</ul>';
            return html;
        }

        async function browseDirectory() {
            const path = document.getElementById('browse-path').value;
            const recursive = document.getElementById('browse-recursive').checked;
            const resultDiv = document.getElementById('browse-result');
            
            resultDiv.innerHTML = '<div class="loading"></div> Loading...';
            resultDiv.className = 'result show';

            try {
                const url = `${API_BASE}/browse?path=${encodeURIComponent(path)}&recursive=${recursive}`;
                const response = await fetch(url);
                const data = await response.json();
                
                if (response.ok) {
                    showResult('browse-result', formatDirectoryListing(data));
                } else {
                    showResult('browse-result', `<strong>Error:</strong> ${data.detail || 'Unknown error'}`, true);
                }
            } catch (error) {
                showResult('browse-result', `<strong>Error:</strong> ${error.message}`, true);
            }
        }

        async function getFITSInfo() {
            const path = document.getElementById('fits-path').value;
            const resultDiv = document.getElementById('fits-result');
            
            resultDiv.innerHTML = '<div class="loading"></div> Loading...';
            resultDiv.className = 'result show';

            try {
                const url = `${API_BASE}/fits/info?path=${encodeURIComponent(path)}`;
                const response = await fetch(url);
                const data = await response.json();
                
                if (response.ok) {
                    showResult('fits-result', formatJSON(data));
                } else {
                    showResult('fits-result', `<strong>Error:</strong> ${data.detail || 'Unknown error'}`, true);
                }
            } catch (error) {
                showResult('fits-result', `<strong>Error:</strong> ${error.message}`, true);
            }
        }

        async function viewFITS() {
            const path = document.getElementById('fits-path').value;
            const resultDiv = document.getElementById('fits-result');
            
            resultDiv.innerHTML = '<div class="loading"></div> Loading...';
            resultDiv.className = 'result show';

            try {
                const url = `${API_BASE}/fits/view?path=${encodeURIComponent(path)}&width=800&height=600`;
                const response = await fetch(url);
                const html = await response.text();
                
                if (response.ok) {
                    resultDiv.innerHTML = html;
                    resultDiv.className = 'result show';
                } else {
                    const data = await response.json();
                    showResult('fits-result', `<strong>Error:</strong> ${data.detail || 'Unknown error'}`, true);
                }
            } catch (error) {
                showResult('fits-result', `<strong>Error:</strong> ${error.message}`, true);
            }
        }

        async function getCasaTableInfo() {
            const path = document.getElementById('casatable-path').value;
            const resultDiv = document.getElementById('casatable-result');
            
            resultDiv.innerHTML = '<div class="loading"></div> Loading...';
            resultDiv.className = 'result show';

            try {
                const url = `${API_BASE}/casatable/info?path=${encodeURIComponent(path)}`;
                const response = await fetch(url);
                const data = await response.json();
                
                if (response.ok) {
                    showResult('casatable-result', formatJSON(data));
                } else {
                    showResult('casatable-result', `<strong>Error:</strong> ${data.detail || 'Unknown error'}`, true);
                }
            } catch (error) {
                showResult('casatable-result', `<strong>Error:</strong> ${error.message}`, true);
            }
        }

        async function viewCasaTable() {
            const path = document.getElementById('casatable-path').value;
            const resultDiv = document.getElementById('casatable-result');
            
            resultDiv.innerHTML = '<div class="loading"></div> Loading...';
            resultDiv.className = 'result show';

            try {
                const url = `${API_BASE}/casatable/view?path=${encodeURIComponent(path)}&max_rows=10&max_cols=10`;
                const response = await fetch(url);
                const html = await response.text();
                
                if (response.ok) {
                    resultDiv.innerHTML = html;
                    resultDiv.className = 'result show';
                } else {
                    const data = await response.json();
                    showResult('casatable-result', `<strong>Error:</strong> ${data.detail || 'Unknown error'}`, true);
                }
            } catch (error) {
                showResult('casatable-result', `<strong>Error:</strong> ${error.message}`, true);
            }
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
