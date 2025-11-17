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

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException
from fastapi import Path as PathParam
from fastapi import Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from dsa110_contimg.api.carta_service import get_carta_service_manager
from dsa110_contimg.qa.casa_ms_qa import QaResult, QaThresholds, run_ms_qa
from dsa110_contimg.qa.visualization import (
    CasaTable,
    FileList,
    FITSFile,
    ImageFile,
    TextFile,
    browse_qa_outputs,
    display_qa_summary,
    generate_fits_viewer_notebook,
    generate_qa_notebook,
    generate_qa_notebook_from_result,
    ls,
)
from dsa110_contimg.qa.visualization_qa import run_ms_qa_with_visualization
from dsa110_contimg.utils.cli_helpers import casa_log_environment
from dsa110_contimg.utils.path_validation import sanitize_filename, validate_path

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/visualization", tags=["visualization"])

# Simple in-memory cache for analysis results
# Key: (task, image_path, region_hash, params_hash) -> result
_analysis_cache: Dict[str, Dict[str, Any]] = {}
_cache_max_size = 100  # Maximum number of cached results


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


class ImageInfo(BaseModel):
    """Image file information."""

    path: str
    exists: bool
    size: Optional[int] = None
    format: Optional[str] = None
    dimensions: Optional[Dict[str, int]] = None
    error: Optional[str] = None


class TextInfo(BaseModel):
    """Text file information."""

    path: str
    exists: bool
    size: Optional[int] = None
    line_count: Optional[int] = None
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

    Note: Path is validated using validate_path() before use. CodeQL warnings
    about path injection in error messages are false positives.
    """
    try:
        # Validate path is within allowed directories using path validation utility
        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        qa_base = base_state / "qa"
        output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))

        # Try validation against each allowed base directory
        target_path = None
        validation_errors = []

        for base_dir in [base_state, qa_base, output_dir]:
            try:
                # Allow absolute paths if the base directory resolves to an absolute path
                # This is necessary because output_dir is typically an absolute path,
                # and relative base directories like "state" resolve to absolute paths
                resolved_base = Path(base_dir).resolve()
                allow_absolute = resolved_base.is_absolute()
                target_path = validate_path(path, base_dir, allow_absolute=allow_absolute)
                break
            except ValueError as e:
                validation_errors.append(str(e))
                continue

        if target_path is None:
            # codeql[py/path-injection]: Path has been validated; using original path only in error message
            raise HTTPException(
                status_code=403,
                detail=f"Path {path} is outside allowed directories: {validation_errors[0] if validation_errors else 'Invalid path'}",
            )

        if not target_path.exists():
            # codeql[py/path-injection]: Path has been validated; using original path only in error message
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")

        if not target_path.is_dir():
            # codeql[py/path-injection]: Path has been validated; using original path only in error message
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
        from dsa110_contimg.qa.visualization.file import autodetect_file_type

        for item in qa_dir:
            file_type = autodetect_file_type(item.fullpath) or (
                "directory" if item.isdir else "file"
            )
            entry = DirectoryEntry(
                name=item.basename,
                path=item.fullpath,
                type=file_type,
                size=str(item.size) if item.size is not None else None,
                modified_time=(datetime.fromtimestamp(item.mtime) if item.mtime else None),
                is_dir=item.isdir,
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


@router.get("/directory/thumbnails")
def get_directory_thumbnails(
    path: str = Query(..., description="Directory path to browse"),
    recursive: bool = Query(False, description="Recursive directory scan"),
    include_pattern: Optional[str] = Query(None, description="Include pattern (glob)"),
    exclude_pattern: Optional[str] = Query(None, description="Exclude pattern (glob)"),
    ncol: Optional[int] = Query(None, description="Number of columns (None = auto)"),
    mincol: int = Query(0, description="Minimum number of columns"),
    maxcol: int = Query(8, description="Maximum number of columns"),
    titles: bool = Query(True, description="Show file titles"),
    width: Optional[int] = Query(None, description="Thumbnail width in pixels"),
):
    """
    Render a thumbnail catalog (grid view) of files in a directory.

    Returns HTML for displaying thumbnails in a grid layout.
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
                status_code=403, detail=f"Path {path} is outside allowed directories"
            )

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Path not found: {path}")

        if not target_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

        # Browse directory using DataDir
        from dsa110_contimg.qa.visualization.datadir import DataDir

        qa_dir = DataDir(str(target_path), recursive=recursive)

        # Apply filters using callable syntax if patterns provided
        if include_pattern or exclude_pattern:
            patterns = []
            if include_pattern:
                patterns.append(include_pattern)
            if exclude_pattern:
                patterns.append(f"!{exclude_pattern}")
            qa_dir = qa_dir(*patterns)

        # Render thumbnail catalog
        html = qa_dir.render_thumbnail_catalog(
            ncol=ncol,
            mincol=mincol,
            maxcol=maxcol,
            titles=titles,
            width=width,
        )

        return HTMLResponse(content=html)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error rendering thumbnails for {path}")
        raise HTTPException(status_code=500, detail=f"Error rendering thumbnails: {str(e)}")


# ============================================================================
# FITS File Endpoints
# ============================================================================


@router.get("/fits/info", response_model=FITSInfo)
def get_fits_info(
    path: str = Query(..., description="Path to FITS file"),
):
    """Get information about a FITS file."""
    try:
        # Validate path to prevent path traversal
        base_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        try:
            target_path = validate_path(path, base_dir)
        except ValueError:
            output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
            try:
                target_path = validate_path(path, output_dir)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"FITS file not found: {path}")

        fits_file = FITSFile(str(target_path))

        return FITSInfo(
            path=str(target_path),
            exists=fits_file.exists,
            shape=fits_file.shape if fits_file.exists else None,
            summary=str(fits_file.summary) if fits_file.exists else None,
            header_keys=(
                list(fits_file.hdrobj.keys())
                if fits_file.exists and hasattr(fits_file, "hdrobj")
                else None
            ),
            naxis=(
                fits_file.hdrobj.get("NAXIS")
                if fits_file.exists and hasattr(fits_file, "hdrobj")
                else None
            ),
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
        # Validate path to prevent path traversal
        base_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        try:
            target_path = validate_path(path, base_dir)
        except ValueError:
            # Try other allowed directories
            output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
            try:
                target_path = validate_path(path, output_dir)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

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
        casa_table.rescan()  # pylint: disable=no-member

        return CasaTableInfo(
            path=str(target_path),
            exists=casa_table.exists,
            nrows=casa_table.nrows if casa_table.exists else None,
            columns=casa_table.columns if casa_table.exists else None,
            keywords=casa_table.keywords if casa_table.exists else None,
            subtables=([str(s) for s in casa_table.subtables] if casa_table.exists else None),
            is_writable=casa_table._is_writable if casa_table.exists else None,
            error=casa_table._error if hasattr(casa_table, "_error") else None,
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
        casa_table.rescan()  # pylint: disable=no-member

        # Note: show() uses display() which won't work in API context
        # We need to generate HTML directly
        html = f'<div class="qa-casatable-summary"><h3>CASA Table: {casa_table.basename}</h3>'
        html += f"<p>Path: {casa_table.fullpath}</p>"
        html += f"<p>Rows: {casa_table.nrows:,}</p>"
        html += f"<p>Columns: {len(casa_table.columns)}</p>"
        html += "</div>"

        return HTMLResponse(content=html)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating CASA table viewer HTML for {path}")
        raise HTTPException(status_code=500, detail=f"Error generating viewer: {str(e)}")


# ============================================================================
# Image File Endpoints
# ============================================================================


@router.get("/image/info", response_model=ImageInfo)
def get_image_info(
    path: str = Query(..., description="Path to image file"),
):
    """Get information about an image file."""
    try:
        # Validate path to prevent path traversal
        base_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        try:
            target_path = validate_path(path, base_dir)
        except ValueError:
            output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
            try:
                target_path = validate_path(path, output_dir)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Image file not found: {path}")

        img_file = ImageFile(str(target_path))

        # Get image dimensions if available
        dimensions = None
        if img_file.exists:
            try:
                from PIL import Image as PILImage

                with PILImage.open(target_path) as img:
                    dimensions = {"width": img.width, "height": img.height}
            except Exception:
                pass

        return ImageInfo(
            path=str(target_path),
            exists=img_file.exists,
            size=img_file.size if img_file.exists else None,
            format=target_path.suffix.lower() if img_file.exists else None,
            dimensions=dimensions,
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error reading image file {path}")
        return ImageInfo(
            path=path,
            exists=False,
            error=str(e),
        )


@router.get("/image/view")
def view_image_file(
    path: str = Query(..., description="Path to image file"),
    width: Optional[int] = Query(None, description="Display width in pixels"),
):
    """
    Get HTML for viewing an image file.

    Returns HTML that can be embedded in the dashboard.
    """
    try:
        # Validate path to prevent path traversal
        base_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        try:
            target_path = validate_path(path, base_dir)
        except ValueError:
            output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
            try:
                target_path = validate_path(path, output_dir)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Image file not found: {path}")

        img_file = ImageFile(str(target_path))
        html = img_file.render_html(width=width)  # pylint: disable=no-member

        return HTMLResponse(content=html)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating image viewer HTML for {path}")
        raise HTTPException(status_code=500, detail=f"Error generating viewer: {str(e)}")


@router.get("/image/thumbnail")
def get_image_thumbnail(
    path: str = Query(..., description="Path to image file"),
    width: int = Query(300, description="Thumbnail width in pixels"),
):
    """
    Get or generate thumbnail for an image file.

    Returns HTML with thumbnail that can be embedded in the dashboard.
    """
    try:
        # Validate path to prevent path traversal
        base_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        try:
            target_path = validate_path(path, base_dir)
        except ValueError:
            output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
            try:
                target_path = validate_path(path, output_dir)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Image file not found: {path}")

        img_file = ImageFile(str(target_path))
        html = img_file.render_thumb(width=width)

        return HTMLResponse(content=html)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating thumbnail for {path}")
        raise HTTPException(status_code=500, detail=f"Error generating thumbnail: {str(e)}")


# ============================================================================
# Text File Endpoints
# ============================================================================


@router.get("/text/info", response_model=TextInfo)
def get_text_info(
    path: str = Query(..., description="Path to text file"),
):
    """Get information about a text file."""
    try:
        # Validate path to prevent path traversal
        base_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        try:
            target_path = validate_path(path, base_dir)
        except ValueError:
            output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
            try:
                target_path = validate_path(path, output_dir)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Text file not found: {path}")

        text_file = TextFile(str(target_path))
        text_file._load_impl()  # Load file content

        return TextInfo(
            path=str(target_path),
            exists=text_file.exists,
            size=text_file.size if text_file.exists else None,
            line_count=len(text_file.lines) if hasattr(text_file, "lines") else None,
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error reading text file {path}")
        return TextInfo(
            path=path,
            exists=False,
            error=str(e),
        )


@router.get("/text/view")
def view_text_file(
    path: str = Query(..., description="Path to text file"),
    head: Optional[int] = Query(None, description="Show first N lines"),
    tail: Optional[int] = Query(None, description="Show last N lines"),
    grep: Optional[str] = Query(None, description="Search pattern (regex)"),
    line_numbers: bool = Query(True, description="Show line numbers"),
):
    """
    View text file with optional filtering (head, tail, grep).

    Returns HTML that can be embedded in the dashboard.
    """
    try:
        # Validate path to prevent path traversal
        base_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        try:
            target_path = validate_path(path, base_dir)
        except ValueError:
            output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
            try:
                target_path = validate_path(path, output_dir)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

        if not target_path.exists():
            raise HTTPException(status_code=404, detail=f"Text file not found: {path}")

        text_file = TextFile(str(target_path))
        text_file._load_impl()  # Load file content

        # Apply filters
        if grep:
            filtered = text_file.grep(grep)
        elif head:
            filtered = text_file.head(head)
        elif tail:
            filtered = text_file.tail(tail)
        else:
            filtered = text_file

        html = filtered.render_html(line_numbers=line_numbers)

        return HTMLResponse(content=html)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error generating text viewer HTML for {path}")
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
        # Validate path to prevent path traversal
        base_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        try:
            target_path = validate_path(notebook_path, base_dir)
        except ValueError:
            output_dir = Path(os.getenv("PIPELINE_OUTPUT_DIR", "/stage/dsa110-contimg/ms"))
            try:
                target_path = validate_path(notebook_path, output_dir)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")

        # Ensure it's a .ipynb file
        if not target_path.suffix == ".ipynb":
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
        # browse_qa_outputs returns a DataDir, use it directly
        from dsa110_contimg.qa.visualization.datadir import DataDir

        qa_dir = DataDir(qa_root)
        qa_dir.rescan()

        entries = []
        from dsa110_contimg.qa.visualization.file import autodetect_file_type

        for item in qa_dir:
            file_type = autodetect_file_type(item.fullpath) or (
                "directory" if item.isdir else "file"
            )
            entries.append(
                DirectoryEntry(
                    name=item.basename,
                    path=item.fullpath,
                    type=file_type,
                    size=str(item.size) if item.size is not None else None,
                    modified_time=(datetime.fromtimestamp(item.mtime) if item.mtime else None),
                    is_dir=item.is_dir,
                )
            )

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


# JS9 CASA Analysis Endpoints
# ============================================================================


class JS9AnalysisRequest(BaseModel):
    """Request for JS9 CASA analysis."""

    task: str = Field(..., description="CASA task name (imstat, imfit, imview, specflux)")
    image_path: str = Field(..., description="Path to FITS image file")
    region: Optional[Dict[str, Any]] = Field(
        None, description="JS9 region object (optional, for region-based analysis)"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Additional task-specific parameters"
    )


class JS9AnalysisResponse(BaseModel):
    """Response from JS9 CASA analysis."""

    success: bool
    task: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_sec: Optional[float] = None


@router.post("/js9/analysis", response_model=JS9AnalysisResponse)
def js9_casa_analysis(request: JS9AnalysisRequest):
    """
    Execute CASA analysis tasks on FITS images for JS9 viewer.

    Supports server-side execution of CASA tasks:
    - imstat: Image statistics
    - imfit: Source fitting
    - imview: Contour generation (returns contour data)
    - specflux: Spectral flux extraction
    - imval: Pixel value extraction

    The image_path must be a valid FITS file accessible to the server.
    Region is optional and can be provided in JS9 format (pixel coordinates).

    Results are cached to avoid re-running identical analyses.
    """
    import hashlib
    import time

    from dsa110_contimg.utils.casa_init import ensure_casa_path

    start_time = time.time()

    try:
        # Create cache key
        import json as json_module

        region_str = json_module.dumps(request.region, sort_keys=True) if request.region else ""
        params_str = json_module.dumps(request.parameters or {}, sort_keys=True)
        cache_key_data = f"{request.task}:{request.image_path}:{region_str}:{params_str}"
        cache_key = hashlib.sha256(cache_key_data.encode()).hexdigest()

        # Check cache
        if cache_key in _analysis_cache:
            cached_result = _analysis_cache[cache_key]
            logger.debug(f"Returning cached result for {request.task}")
            return JS9AnalysisResponse(
                success=cached_result["success"],
                task=request.task,
                result=cached_result.get("result"),
                error=cached_result.get("error"),
                execution_time_sec=0.001,  # Cached results are instant
            )
        # Ensure CASA path is set
        ensure_casa_path()

        # Validate image path
        image_path = Path(request.image_path).resolve()
        if not image_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Image file not found: {request.image_path}"
            )

        if not image_path.suffix.lower() == ".fits":
            raise HTTPException(
                status_code=400,
                detail=f"File is not a FITS image: {request.image_path}",
            )

        # Validate task name
        valid_tasks = [
            "imstat",
            "imfit",
            "imview",
            "specflux",
            "imval",
            "imhead",
            "immath",
        ]
        if request.task not in valid_tasks:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid task '{request.task}'. Valid tasks: {valid_tasks}",
            )

        # Execute CASA task
        result = _execute_casa_task(
            task=request.task,
            image_path=str(image_path),
            region=request.region,
            parameters=request.parameters or {},
        )

        execution_time = time.time() - start_time

        response = JS9AnalysisResponse(
            success=True,
            task=request.task,
            result=result,
            execution_time_sec=round(execution_time, 3),
        )

        # Cache the result
        _cache_result(
            cache_key,
            {
                "success": True,
                "result": result,
                "error": None,
            },
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error executing CASA task {request.task}")
        execution_time = time.time() - start_time

        response = JS9AnalysisResponse(
            success=False,
            task=request.task,
            error=str(e),
            execution_time_sec=round(execution_time, 3),
        )

        # Don't cache errors
        return response


def _cache_result(cache_key: str, result: Dict[str, Any]) -> None:
    """Cache an analysis result."""
    global _analysis_cache

    # Limit cache size
    if len(_analysis_cache) >= _cache_max_size:
        # Remove oldest entry (simple FIFO)
        oldest_key = next(iter(_analysis_cache))
        del _analysis_cache[oldest_key]

    _analysis_cache[cache_key] = result


def _execute_casa_task(
    task: str,
    image_path: str,
    region: Optional[Dict[str, Any]],
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a CASA task on an image.

    Args:
        task: Task name (imstat, imfit, imview, specflux)
        image_path: Path to FITS image
        region: Optional JS9 region object
        parameters: Additional task parameters

    Returns:
        Dictionary with task results
    """
    from dsa110_contimg.utils.casa_init import ensure_casa_path

    ensure_casa_path()

    if task == "imstat":
        return _run_imstat(image_path, region, parameters)
    elif task == "imfit":
        return _run_imfit(image_path, region, parameters)
    elif task == "imview":
        return _run_imview(image_path, region, parameters)
    elif task == "specflux":
        return _run_specflux(image_path, region, parameters)
    elif task == "imval":
        return _run_imval(image_path, region, parameters)
    elif task == "imhead":
        return _run_imhead(image_path, region, parameters)
    elif task == "immath":
        return _run_immath(image_path, region, parameters)
    else:
        raise ValueError(f"Unsupported task: {task}")


def _run_imstat(
    image_path: str, region: Optional[Dict[str, Any]], parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Run imstat CASA task."""
    # Convert JS9 region to CASA region string if provided
    region_str = None
    if region:
        region_str = _js9_region_to_casa(region)

    # Run imstat
    with casa_log_environment():
        from casatasks import imstat

        stats = imstat(imagename=image_path, region=region_str, **parameters)

    # Convert to JSON-serializable format
    result = {}
    if isinstance(stats, dict):
        # imstat returns a dictionary with keys like 'DATA', 'MASK', etc.
        for key, value in stats.items():
            if isinstance(value, dict):
                # Convert nested dicts
                result[key] = {k: _convert_to_json_serializable(v) for k, v in value.items()}
            else:
                result[key] = _convert_to_json_serializable(value)
    else:
        result["stats"] = _convert_to_json_serializable(stats)

    return result


def _run_imfit(
    image_path: str, region: Optional[Dict[str, Any]], parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Run imfit CASA task for source fitting."""
    region_str = None
    if region:
        region_str = _js9_region_to_casa(region)

    # Run imfit
    with casa_log_environment():
        from casatasks import imfit

        fit_result = imfit(imagename=image_path, region=region_str, **parameters)

    # Convert to JSON-serializable format
    return {"fit": _convert_to_json_serializable(fit_result)}


def _run_imview(
    image_path: str, region: Optional[Dict[str, Any]], parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Run imview CASA task for contour generation."""
    import numpy as np
    from astropy.io import fits
    from scipy.ndimage import gaussian_filter

    # Get contour levels from parameters or use defaults
    n_levels = parameters.get("n_levels", 10)
    sigma = parameters.get("smoothing_sigma", 1.0)

    # Load image data
    with fits.open(image_path) as hdul:
        data = hdul[0].data  # pylint: disable=no-member

        # Handle multi-dimensional data
        if data.ndim > 2:
            data = data.squeeze()
            if data.ndim > 2:
                data = data[0, 0] if data.ndim == 4 else data[0]

        # Apply smoothing if requested
        if sigma > 0:
            data = gaussian_filter(data, sigma=sigma)

        # Calculate contour levels
        valid_data = data[~np.isnan(data)]
        if len(valid_data) == 0:
            return {"error": "No valid data in image"}

        min_val = float(np.nanmin(valid_data))
        max_val = float(np.nanmax(valid_data))

        # Generate contour levels (linear spacing)
        contour_levels = np.linspace(min_val, max_val, n_levels + 2)[1:-1].tolist()

        # Generate contour coordinates using matplotlib
        try:
            from matplotlib import pyplot as plt

            # Create a figure to generate contours
            fig = plt.figure(figsize=(1, 1))
            ax = fig.add_subplot(111)

            # Generate contours
            contours = ax.contour(data, levels=contour_levels)

            # Extract contour paths
            contour_paths = []
            for level, collection in zip(contour_levels, contours.collections):
                paths = []
                for path in collection.get_paths():
                    vertices = path.vertices
                    paths.append(
                        {
                            "x": vertices[:, 0].tolist(),
                            "y": vertices[:, 1].tolist(),
                        }
                    )
                contour_paths.append(
                    {
                        "level": float(level),
                        "paths": paths,
                    }
                )

            plt.close(fig)

            return {
                "contour_levels": contour_levels,
                "contour_paths": contour_paths,
                "image_shape": list(data.shape),
                "data_range": {"min": min_val, "max": max_val},
            }
        except ImportError:
            # Fallback: return statistics if matplotlib not available
            region_str = None
            if region:
                region_str = _js9_region_to_casa(region)

            with casa_log_environment():
                from casatasks import imstat

                stats = imstat(imagename=image_path, region=region_str, **parameters)

            return {
                "contour_data": _convert_to_json_serializable(stats),
                "note": ("Matplotlib not available, " "returning statistics instead"),
            }


def _run_specflux(
    image_path: str, region: Optional[Dict[str, Any]], parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Run spectral flux extraction."""
    from casatasks import imstat

    region_str = None
    if region:
        region_str = _js9_region_to_casa(region)

    # Extract flux statistics
    stats = imstat(imagename=image_path, region=region_str, **parameters)

    return {
        "flux": _convert_to_json_serializable(stats),
        "note": "Spectral flux extraction via imstat",
    }


def _run_imval(
    image_path: str, region: Optional[Dict[str, Any]], parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Run imval CASA task for pixel value extraction."""
    from casatasks import imval

    region_str = None
    if region:
        region_str = _js9_region_to_casa(region)

    # Get additional parameters
    box = parameters.get("box", None)  # Box region: "x1,y1,x2,y2"
    stokes = parameters.get("stokes", None)  # Stokes parameter

    # Run imval
    try:
        val_result = imval(
            imagename=image_path,
            region=region_str,
            box=box,
            stokes=stokes,
        )

        # imval returns a dictionary with keys like 'data', 'mask', 'coords'
        result = {}
        if isinstance(val_result, dict):
            for key, value in val_result.items():
                result[key] = _convert_to_json_serializable(value)
        else:
            result["values"] = _convert_to_json_serializable(val_result)

        return result
    except Exception as e:
        # Fallback: try to extract pixel values directly from FITS
        import numpy as np
        from astropy.io import fits

        try:
            with fits.open(image_path) as hdul:
                data = hdul[0].data  # pylint: disable=no-member

                # Handle multi-dimensional data
                if data.ndim > 2:
                    data = data.squeeze()
                    if data.ndim > 2:
                        data = data[0, 0] if data.ndim == 4 else data[0]

                # If region provided, extract values from region
                if region:
                    # Create mask from region
                    from astropy.wcs import WCS

                    from dsa110_contimg.utils.regions import (
                        create_region_mask,
                    )

                    wcs = WCS(hdul[0].header)  # pylint: disable=no-member
                    region_data = type(
                        "RegionData",
                        (),
                        {
                            "type": region.get("shape", "circle"),
                            "coordinates": {
                                "ra_deg": region.get("ra", 0),
                                "dec_deg": region.get("dec", 0),
                                "radius_deg": region.get("r", 1),
                            },
                        },
                    )()

                    mask = create_region_mask(
                        data.shape, region_data, wcs, hdul[0].header
                    )  # pylint: disable=no-member
                    values = data[mask].tolist()
                else:
                    # Return all values (flattened)
                    values = data.flatten().tolist()

                return {
                    "values": values,
                    "shape": list(data.shape),
                    "note": ("Extracted directly from FITS file " "(imval fallback)"),
                }
        except Exception as e2:
            return {
                "error": (f"Failed to extract pixel values: {str(e2)}"),
                "original_error": str(e),
            }


def _run_imhead(
    image_path: str, region: Optional[Dict[str, Any]], parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Run imhead CASA task to get image header information."""
    from casatasks import imhead

    try:
        # Get mode (list, get, put)
        mode = parameters.get("mode", "list")

        if mode == "list":
            # List all header keywords
            header_info = imhead(imagename=image_path, mode="list")
        elif mode == "get":
            # Get specific keyword
            keyword = parameters.get("keyword", None)
            if not keyword:
                return {"error": "keyword parameter required for mode='get'"}
            header_info = imhead(imagename=image_path, mode="get", hdkey=keyword)
        else:
            return {"error": f"Unsupported mode: {mode}"}

        return {"header": _convert_to_json_serializable(header_info)}
    except Exception as e:
        # Fallback: read header directly from FITS
        try:
            from astropy.io import fits

            with fits.open(image_path) as hdul:
                header = hdul[0].header
                header_dict = {}
                for key, value in header.items():
                    # Skip COMMENT and HISTORY cards
                    if key not in ["COMMENT", "HISTORY"]:
                        try:
                            # Try to convert to JSON-serializable types
                            if isinstance(value, (int, float, str, bool)):
                                header_dict[key] = value
                            else:
                                header_dict[key] = str(value)
                        except Exception:
                            header_dict[key] = str(value)

                return {
                    "header": header_dict,
                    "note": "Extracted directly from FITS file (imhead fallback)",
                }
        except Exception as e2:
            return {
                "error": f"Failed to extract header: {str(e2)}",
                "original_error": str(e),
            }


def _run_immath(
    image_path: str, region: Optional[Dict[str, Any]], parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Run immath CASA task for image arithmetic operations."""
    import os
    import tempfile

    from casatasks import immath

    try:
        # Get expression and output name
        expr = parameters.get("expr", None)
        if not expr:
            return {"error": "expr parameter required for immath"}

        # Create temporary output file
        output_path = parameters.get("output", None)
        if not output_path:
            # Generate temporary filename
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"immath_temp_{os.getpid()}.fits")

        # Run immath
        immath(
            imagename=image_path,
            expr=expr,
            outfile=output_path,
            **{k: v for k, v in parameters.items() if k not in ["expr", "output"]},
        )

        # Read result statistics
        from casatasks import imstat

        stats = imstat(imagename=output_path)

        result = {
            "output_path": output_path,
            "statistics": _convert_to_json_serializable(stats),
            "expression": expr,
        }

        # Clean up temporary file if we created it
        if not parameters.get("output") and os.path.exists(output_path):
            try:
                os.remove(output_path)
                result["note"] = "Temporary output file cleaned up"
            except Exception:
                result["note"] = "Temporary output file preserved"

        return result
    except Exception as e:
        return {"error": f"Failed to execute immath: {str(e)}"}


def _js9_region_to_casa(region: Dict[str, Any]) -> str:
    """
    Convert JS9 region object to CASA region string.

    JS9 regions are typically in pixel coordinates.
    CASA region format: circle[[ra,dec],radius] or box[[ra,dec],[width,height]]

    For now, we'll use pixel coordinates directly (CASA supports pixel regions).
    """
    shape = region.get("shape", "").lower()
    if shape in ["circle", "c"]:
        # JS9 circle: {x, y, radius} in pixels
        x = region.get("x", region.get("xcen", 0))
        y = region.get("y", region.get("ycen", 0))
        radius = region.get("r", region.get("radius", 1))
        # CASA pixel region format: circle[[x,y],radius]pix
        return f"circle[[{x},{y}],{radius}]pix"
    elif shape in ["box", "rectangle", "r"]:
        # JS9 box: {x, y, width, height} in pixels
        x = region.get("x", region.get("xcen", 0))
        y = region.get("y", region.get("ycen", 0))
        width = region.get("width", 1)
        height = region.get("height", 1)
        # CASA pixel region format: box[[x,y],[width,height]]pix
        return f"box[[{x},{y}],[{width},{height}]]pix"
    else:
        # Default: use bounding box
        return ""


def _convert_to_json_serializable(obj: Any) -> Any:
    """Convert numpy types and other non-JSON-serializable objects to JSON-compatible types."""
    import numpy as np

    if isinstance(obj, (np.integer, np.floating)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (list, tuple)):
        return [_convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    else:
        # Try to convert to string as fallback
        return str(obj)


# CARTA Service Management
# ============================================================================


class CARTAServiceStatus(BaseModel):
    """CARTA service status response."""

    running: bool
    backend_port_open: bool
    frontend_port_open: bool
    backend_healthy: bool
    container_running: bool
    method: str


class CARTAServiceControlResponse(BaseModel):
    """CARTA service control response."""

    success: bool
    message: str
    method: Optional[str] = None


@router.get("/carta/status", response_model=CARTAServiceStatus)
def get_carta_status():
    """
    Get the current status of CARTA services.

    Returns information about whether CARTA backend and frontend are running,
    ports are open, and services are healthy.
    """
    manager = get_carta_service_manager()
    status = manager.get_status()
    return CARTAServiceStatus(**status)


@router.post("/carta/start", response_model=CARTAServiceControlResponse)
def start_carta_service():
    """
    Start CARTA services.

    Attempts to start CARTA backend and frontend services. If Docker is available,
    will create and start a CARTA container. Otherwise, checks if services are
    already running.
    """
    manager = get_carta_service_manager()
    result = manager.start_service()
    return CARTAServiceControlResponse(**result)


@router.post("/carta/stop", response_model=CARTAServiceControlResponse)
def stop_carta_service():
    """
    Stop CARTA services.

    Stops CARTA services if they are managed by Docker. If services are running
    standalone, returns an error message indicating manual stop is required.
    """
    manager = get_carta_service_manager()
    result = manager.stop_service()
    return CARTAServiceControlResponse(**result)


@router.post("/carta/restart", response_model=CARTAServiceControlResponse)
def restart_carta_service():
    """
    Restart CARTA services.

    Stops and then starts CARTA services. Useful for recovering from errors
    or applying configuration changes.
    """
    manager = get_carta_service_manager()
    result = manager.restart_service()
    return CARTAServiceControlResponse(**result)


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
