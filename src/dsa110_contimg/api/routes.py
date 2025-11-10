"""FastAPI routing for the pipeline monitoring API."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    FastAPI,
    HTTPException,
    Query,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles

from dsa110_contimg.api.config import ApiConfig
from dsa110_contimg.api.data_access import (
    _connect,
    fetch_alert_history,
    fetch_calibration_sets,
    fetch_ese_candidates,
    fetch_mosaic_by_id,
    fetch_mosaics,
    fetch_pointing_history,
    fetch_queue_stats,
    fetch_recent_calibrator_matches,
    fetch_recent_products,
    fetch_recent_queue_groups,
    fetch_source_timeseries,
)
from dsa110_contimg.api.image_utils import (
    convert_casa_to_fits,
    get_fits_path,
    resolve_image_path,
)
from dsa110_contimg.api.models import (
    AlertHistory,
    AntennaInfo,
    BatchApplyParams,
    BatchCalibrateParams,
    BatchImageParams,
    BatchJob,
    BatchJobCreateRequest,
    BatchJobList,
    BatchJobStatus,
    CalibrateJobParams,
    CalibrationQA,
    CalibratorMatchList,
    CalTableCompatibility,
    CalTableInfo,
    CalTableList,
    ConversionJobCreateRequest,
    ConversionJobParams,
    ESECandidate,
    ESECandidatesResponse,
    ExistingCalTable,
    ExistingCalTables,
    FieldInfo,
    FlaggingStats,
    GroupDetail,
    ImageInfo,
    ImageList,
    ImageQA,
    Job,
    JobCreateRequest,
    JobList,
    Mosaic,
    MosaicQueryResponse,
    MSCalibratorMatch,
    MSCalibratorMatchList,
    MsIndexEntry,
    MsIndexList,
    MSList,
    MSListEntry,
    MSMetadata,
    PipelineStatus,
    PointingHistoryList,
    ProductList,
    QAArtifact,
    QAList,
    QAMetrics,
    SourceSearchResponse,
    SourceTimeseries,
    StreamingConfigRequest,
    StreamingControlResponse,
    StreamingHealthResponse,
    StreamingStatusResponse,
    SystemMetrics,
    UVH5FileEntry,
    UVH5FileList,
    WorkflowJobCreateRequest,
)
from dsa110_contimg.api.streaming_service import (
    StreamingConfig,
    StreamingServiceManager,
)

logger = logging.getLogger(__name__)


def create_app(config: ApiConfig | None = None) -> FastAPI:
    """Factory for the monitoring API application."""

    cfg = config or ApiConfig.from_env()
    app = FastAPI(title="DSA-110 Continuum Pipeline API", version="0.1.0")

    # Background task to broadcast status updates
    @app.on_event("startup")
    async def start_status_broadcaster():
        """Start background task to broadcast status updates."""
        from dsa110_contimg.api.websocket_manager import create_status_update, manager

        async def broadcast_status():
            """Periodically fetch and broadcast status updates."""
            while True:
                try:
                    await asyncio.sleep(10)  # Broadcast every 10 seconds

                    # Fetch current status
                    pipeline_status = None
                    metrics = None
                    ese_candidates = None

                    try:
                        queue_stats = fetch_queue_stats(cfg.queue_db)
                        recent_groups = fetch_recent_queue_groups(
                            cfg.queue_db, cfg, limit=20
                        )
                        cal_sets = fetch_calibration_sets(cfg.registry_db)
                        matched_recent = sum(
                            1
                            for g in recent_groups
                            if getattr(g, "has_calibrator", False)
                        )
                        pipeline_status = {
                            "queue": (
                                queue_stats.dict()
                                if hasattr(queue_stats, "dict")
                                else queue_stats
                            ),
                            "recent_groups": [
                                g.dict() if hasattr(g, "dict") else g
                                for g in recent_groups
                            ],
                            "calibration_sets": [
                                cs.dict() if hasattr(cs, "dict") else cs
                                for cs in cal_sets
                            ],
                            "matched_recent": matched_recent,
                        }
                    except Exception as e:
                        logger.warning(f"Failed to fetch pipeline status: {e}")

                    try:
                        # Calculate system metrics inline
                        import psutil

                        cpu_percent = psutil.cpu_percent(interval=0.1)
                        memory = psutil.virtual_memory()
                        disk = psutil.disk_usage("/")
                        load_avg = (
                            os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
                        )

                        metrics = {
                            "cpu_percent": cpu_percent,
                            "memory_percent": memory.percent,
                            "memory_used_gb": round(memory.used / (1024**3), 2),
                            "memory_total_gb": round(memory.total / (1024**3), 2),
                            "disk_percent": disk.percent,
                            "disk_free_gb": round(disk.free / (1024**3), 2),
                            "disk_total_gb": round(disk.total / (1024**3), 2),
                            "load_avg_1min": load_avg,
                            "timestamp": datetime.now().isoformat(),
                        }
                    except Exception as e:
                        logger.warning(f"Failed to fetch metrics: {e}")
                        metrics = None

                    try:
                        from dsa110_contimg.api.data_access import fetch_ese_candidates

                        ese_data = fetch_ese_candidates(cfg.products_db, limit=50)
                        ese_candidates = {
                            "candidates": [
                                c.dict() if hasattr(c, "dict") else c for c in ese_data
                            ],
                        }
                    except Exception as e:
                        logger.warning(f"Failed to fetch ESE candidates: {e}")

                    # Broadcast update
                    if pipeline_status or metrics or ese_candidates:
                        update = create_status_update(
                            pipeline_status, metrics, ese_candidates
                        )
                        await manager.broadcast(update)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in status broadcaster: {e}")
                    await asyncio.sleep(10)

        # Start background task
        asyncio.create_task(broadcast_status())

    # Add CORS middleware to allow frontend access (support dev and served static ports)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://10.42.0.148:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            # Common static serve ports we use
            "http://localhost:3000",
            "http://localhost:3001",
            "http://localhost:3002",
            "http://localhost:3210",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:3001",
            "http://127.0.0.1:3002",
            "http://127.0.0.1:3210",
            "http://lxd110h17:3000",
            "http://lxd110h17:3001",
            "http://lxd110h17:3002",
            "http://lxd110h17:3210",
        ],
        allow_origin_regex=r"http://(localhost|127\\.0\\.0\\.1|lxd110h17)(:\\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Optionally serve built frontend under the same origin to avoid CORS in production/dev
    try:
        project_root = Path(__file__).resolve().parents[3]
        frontend_dist = project_root / "frontend" / "dist"
        if frontend_dist.exists():
            # Serve JS9 files from paths JS9 requests (without /js9/ prefix)
            # JS9 requests these from /ui/ instead of /ui/js9/, so we serve them from both locations
            js9_files_map = {
                "js9Prefs.json": frontend_dist / "js9" / "js9Prefs.json",
                "js9worker.js": frontend_dist / "js9" / "js9worker.js",
                "astroemw.wasm": frontend_dist / "js9" / "astroemw.wasm",
                "astroemw.js": frontend_dist / "js9" / "astroemw.js",
            }

            # Add specific routes for JS9 files that JS9 requests without /js9/ prefix
            @app.get("/ui/js9Prefs.json")
            def serve_js9_prefs():
                file_path = js9_files_map["js9Prefs.json"]
                if file_path.exists():
                    return FileResponse(str(file_path), media_type="application/json")
                raise HTTPException(status_code=404, detail="js9Prefs.json not found")

            @app.get("/ui/js9worker.js")
            def serve_js9_worker():
                file_path = js9_files_map["js9worker.js"]
                if file_path.exists():
                    return FileResponse(
                        str(file_path), media_type="application/javascript"
                    )
                raise HTTPException(status_code=404, detail="js9worker.js not found")

            @app.get("/ui/astroemw.wasm")
            def serve_astroemw_wasm():
                file_path = js9_files_map["astroemw.wasm"]
                if file_path.exists():
                    return FileResponse(str(file_path), media_type="application/wasm")
                raise HTTPException(status_code=404, detail="astroemw.wasm not found")

            @app.get("/ui/astroemw.js")
            def serve_astroemw_js():
                file_path = js9_files_map["astroemw.js"]
                if file_path.exists():
                    return FileResponse(
                        str(file_path), media_type="application/javascript"
                    )
                raise HTTPException(status_code=404, detail="astroemw.js not found")

            # Catch-all for client-side routing - serve index.html for any /ui/* path
            # This must come BEFORE mounts to handle client-side routes
            @app.get("/ui/{path:path}")
            def serve_frontend_app(path: str):
                """Serve frontend index.html for client-side routing."""
                # Handle specific static file requests
                if path == "index.html" or path == "":
                    index_path = frontend_dist / "index.html"
                    if index_path.exists():
                        return FileResponse(str(index_path), media_type="text/html")

                # Check if it's a static asset (has file extension)
                path_parts = path.split("/")
                last_part = path_parts[-1] if path_parts else ""

                # If it looks like a file (has extension), try to serve it
                if "." in last_part:
                    file_path = frontend_dist / path
                    if file_path.exists() and file_path.is_file():
                        return FileResponse(str(file_path))

                # Otherwise serve index.html for client-side routing
                index_path = frontend_dist / "index.html"
                if index_path.exists():
                    return FileResponse(str(index_path), media_type="text/html")
                raise HTTPException(status_code=404, detail="Frontend not found")

            # Mount static files for assets and JS9 (these will only match exact paths)
            app.mount(
                "/ui/assets",
                StaticFiles(directory=str(frontend_dist / "assets")),
                name="ui-assets",
            )
            app.mount(
                "/ui/js9",
                StaticFiles(directory=str(frontend_dist / "js9")),
                name="ui-js9",
            )

            # Redirect root path to UI if frontend is available
            @app.get("/", response_class=HTMLResponse)
            def root():
                return RedirectResponse(url="/ui/")

    except Exception:
        pass

    router = APIRouter(prefix="/api")

    # Test endpoints (dev only)
    import os

    if os.getenv("ENVIRONMENT") != "production":

        @router.post("/test/streaming/broadcast")
        async def test_streaming_broadcast(message: Optional[dict] = None):
            """Test endpoint to trigger WebSocket broadcast (dev only).

            Used for testing real-time status updates (STREAM-020).
            """
            import time

            from dsa110_contimg.api.websocket_manager import manager

            test_message = message or {
                "type": "streaming_status_update",
                "status": "running",
                "timestamp": time.time(),
                "test": True,
            }
            await manager.broadcast(test_message)
            return {"success": True, "message": "Broadcast sent", "data": test_message}

    @router.get("/health")
    def health():
        """Health check endpoint for monitoring and load balancers."""
        import os

        from dsa110_contimg.api.data_access import _connect

        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "databases": {},
            "version": "0.1.0",
        }

        # Check database accessibility
        databases = {
            "queue": cfg.queue_db,
            "products": cfg.products_db,
            "registry": cfg.registry_db,
        }

        all_healthy = True
        for db_name, db_path in databases.items():
            try:
                if db_path.exists():
                    # Try to connect and execute a simple query
                    with _connect(db_path) as conn:
                        conn.execute("SELECT 1").fetchone()
                    health_status["databases"][db_name] = "accessible"
                else:
                    health_status["databases"][db_name] = "not_found"
                    all_healthy = False
            except Exception as e:
                health_status["databases"][db_name] = f"error: {str(e)}"
                all_healthy = False

        # Check disk space (basic check)
        try:
            import shutil

            disk_usage = shutil.disk_usage(
                cfg.queue_db.parent if cfg.queue_db.parent.exists() else Path(".")
            )
            health_status["disk"] = {
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "total_gb": round(disk_usage.total / (1024**3), 2),
            }
        except Exception:
            pass

        if not all_healthy:
            health_status["status"] = "degraded"
            return health_status, 503

        return health_status

    @router.websocket("/ws/status")
    async def websocket_status(websocket: WebSocket):
        """WebSocket endpoint for real-time status updates."""
        from dsa110_contimg.api.websocket_manager import manager

        await manager.connect(websocket)
        try:
            while True:
                # Wait for client messages (ping/pong)
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            await manager.disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            await manager.disconnect(websocket)

    @router.get("/sse/status")
    async def sse_status():
        """Server-Sent Events endpoint for real-time status updates."""
        from dsa110_contimg.api.websocket_manager import event_generator

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @router.get("/status", response_model=PipelineStatus)
    def status(
        limit: int = 20,
    ) -> PipelineStatus:  # noqa: WPS430 (fastapi handles context)
        queue_stats = fetch_queue_stats(cfg.queue_db)
        recent_groups = fetch_recent_queue_groups(cfg.queue_db, cfg, limit=limit)
        cal_sets = fetch_calibration_sets(cfg.registry_db)
        matched_recent = sum(
            1 for g in recent_groups if getattr(g, "has_calibrator", False)
        )
        return PipelineStatus(
            queue=queue_stats,
            recent_groups=recent_groups,
            calibration_sets=cal_sets,
            matched_recent=matched_recent,
        )

    @router.get("/products", response_model=ProductList)
    def products(limit: int = 50) -> ProductList:
        items = fetch_recent_products(cfg.products_db, limit=limit)
        return ProductList(items=items)

    @router.get("/images", response_model=ImageList)
    def images(
        limit: int = 100,
        offset: int = 0,
        ms_path: str | None = None,
        image_type: str | None = None,
        pbcor: bool | None = None,
    ) -> ImageList:
        """List available images for SkyView.

        Args:
            limit: Maximum number of images to return (1-1000, default: 100)
            offset: Offset for pagination (>= 0, default: 0)
            ms_path: Filter by MS path (partial match)
            image_type: Filter by image type (image, pbcor, residual, psf, pb)
            pbcor: Filter by primary beam correction status
        """
        # Validate and clamp parameters
        limit = max(1, min(limit, 1000)) if limit > 0 else 100
        offset = max(0, offset) if offset >= 0 else 0

        db_path = cfg.products_db
        items: list[ImageInfo] = []
        total = 0

        if not db_path.exists():
            return ImageList(items=items, total=0)

        with _connect(db_path) as conn:
            # Build query
            where_clauses = []
            params: list[object] = []

            if ms_path:
                where_clauses.append("ms_path LIKE ?")
                params.append(f"%{ms_path}%")

            if image_type:
                where_clauses.append("type = ?")
                params.append(image_type)

            if pbcor is not None:
                where_clauses.append("pbcor = ?")
                params.append(1 if pbcor else 0)

            where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM images{where_sql}"
            total_row = conn.execute(count_query, params).fetchone()
            total = total_row["total"] if total_row else 0

            # Get images
            query = f"""
                SELECT id, path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor
                FROM images
                {where_sql}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()

            for r in rows:
                # For now, we'll use the basic fields. WCS and additional metadata
                # can be extracted from FITS headers in a future enhancement
                items.append(
                    ImageInfo(
                        id=r["id"],
                        path=r["path"],
                        ms_path=r["ms_path"],
                        created_at=(
                            datetime.fromtimestamp(r["created_at"])
                            if r["created_at"]
                            else None
                        ),
                        type=r["type"],
                        beam_major_arcsec=r["beam_major_arcsec"],
                        beam_minor_arcsec=None,  # Not in current schema
                        beam_pa_deg=None,  # Not in current schema
                        noise_jy=r["noise_jy"],
                        peak_flux_jy=None,  # Not in current schema
                        pbcor=bool(r["pbcor"]),
                        center_ra_deg=None,  # Will extract from FITS in future
                        center_dec_deg=None,  # Will extract from FITS in future
                        image_size_deg=None,  # Will extract from FITS in future
                        pixel_size_arcsec=None,  # Will extract from FITS in future
                    )
                )

        return ImageList(items=items, total=total)

    @router.get("/images/{image_id}/fits")
    def get_image_fits(image_id: int):
        """Serve FITS file for an image.

        Converts CASA images to FITS on-demand if needed.
        """
        db_path = cfg.products_db

        if not db_path.exists():
            return HTMLResponse(status_code=404, content="Database not found")

        with _connect(db_path) as conn:
            row = conn.execute(
                "SELECT path FROM images WHERE id = ?", (image_id,)
            ).fetchone()

            if not row:
                return HTMLResponse(status_code=404, content="Image not found")

            image_path = row["path"]

        # Get FITS file path (convert if needed)
        fits_path = get_fits_path(image_path)

        if not fits_path or not Path(fits_path).exists():
            return HTMLResponse(
                status_code=404,
                content=f"FITS file not found for image {image_id}. Conversion may have failed.",
            )

        # Serve FITS file
        return FileResponse(
            fits_path,
            media_type="application/fits",
            filename=Path(fits_path).name,
        )

    @router.get("/images/{image_id}/profile")
    def get_image_profile(
        image_id: int,
        profile_type: str = Query(
            ..., description="Profile type: line, polyline, or point"
        ),
        coordinates: str = Query(..., description="JSON array of coordinate pairs"),
        coordinate_system: str = Query(
            "wcs", description="Coordinate system: wcs or pixel"
        ),
        width: int = Query(1, description="Width of profile extraction in pixels"),
        radius: float = Query(
            10.0, description="Radius in arcseconds for point profile"
        ),
        fit_model: Optional[str] = Query(
            None, description="Fit model: gaussian, moffat, or none"
        ),
    ):
        """Extract a spatial profile from an image.

        Supports line, polyline, and point (radial) profiles.
        Optionally fits Gaussian or Moffat models to the profile.
        """
        import json

        from dsa110_contimg.utils.profiling import (
            extract_line_profile,
            extract_point_profile,
            extract_polyline_profile,
            fit_gaussian_profile,
            fit_moffat_profile,
        )

        db_path = cfg.products_db
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        with _connect(db_path) as conn:
            row = conn.execute(
                "SELECT path FROM images WHERE id = ?", (image_id,)
            ).fetchone()

            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Image {image_id} not found"
                )

            image_path = row["path"]

        # Get FITS file path
        fits_path = get_fits_path(image_path)
        if not fits_path or not Path(fits_path).exists():
            raise HTTPException(
                status_code=404, detail=f"FITS file not found for image {image_id}"
            )

        # Validate profile type first
        if profile_type not in ["line", "polyline", "point"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid profile_type: {profile_type}. Must be 'line', 'polyline', or 'point'",
            )

        # Parse coordinates
        try:
            coords_list = json.loads(coordinates)
            if not isinstance(coords_list, list):
                raise ValueError("Coordinates must be a JSON array")

            # Validate coordinate count based on profile type
            if profile_type == "point":
                if len(coords_list) < 1:
                    raise ValueError("Point profile requires at least 1 coordinate")
            else:
                if len(coords_list) < 2:
                    raise ValueError(
                        f"{profile_type} profile requires at least 2 coordinates"
                    )
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, detail="Invalid JSON in coordinates parameter"
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Validate coordinate system
        if coordinate_system not in ["wcs", "pixel"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid coordinate_system: {coordinate_system}. Must be 'wcs' or 'pixel'",
            )

        try:
            # Extract profile based on type
            if profile_type == "line":
                if len(coords_list) != 2:
                    raise HTTPException(
                        status_code=400,
                        detail="Line profile requires exactly 2 coordinates",
                    )
                profile_data = extract_line_profile(
                    fits_path,
                    tuple(coords_list[0]),
                    tuple(coords_list[1]),
                    coordinate_system,
                    width,
                )
            elif profile_type == "polyline":
                if len(coords_list) < 2:
                    raise HTTPException(
                        status_code=400,
                        detail="Polyline profile requires at least 2 coordinates",
                    )
                coord_tuples = [tuple(c) for c in coords_list]
                profile_data = extract_polyline_profile(
                    fits_path,
                    coord_tuples,
                    coordinate_system,
                    width,
                )
            else:  # point profile
                if len(coords_list) != 1:
                    raise HTTPException(
                        status_code=400,
                        detail="Point profile requires exactly 1 coordinate",
                    )

                profile_data = extract_point_profile(
                    fits_path,
                    tuple(coords_list[0]),
                    radius,
                    coordinate_system,
                )

            # Perform fitting if requested
            if fit_model and fit_model != "none":
                import numpy as np

                distance = np.array(profile_data["distance"])
                flux = np.array(profile_data["flux"])
                error = (
                    np.array(profile_data["error"]) if profile_data["error"] else None
                )

                if fit_model == "gaussian":
                    fit_result = fit_gaussian_profile(distance, flux, error)
                elif fit_model == "moffat":
                    fit_result = fit_moffat_profile(distance, flux, error)
                else:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid fit_model: {fit_model}. Must be 'gaussian' or 'moffat'",
                    )

                profile_data["fit"] = fit_result

            return profile_data

        except Exception as e:
            logger.error(f"Error extracting profile from image {image_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to extract profile: {str(e)}"
            )

    @router.post("/images/{image_id}/fit")
    def fit_image(
        image_id: int,
        model: str = Body(..., description="Fit model: gaussian or moffat"),
        region_id: Optional[int] = Body(
            None, description="Optional region ID to fit within"
        ),
        initial_guess: Optional[str] = Body(
            None, description="Optional JSON with initial parameters"
        ),
        fit_background: bool = Body(
            True, description="Whether to fit background level"
        ),
    ):
        """Fit a 2D model (Gaussian or Moffat) to a source in an image.

        Optionally fits within a region constraint.
        """
        import json

        import numpy as np
        from astropy.io import fits
        from astropy.wcs import WCS

        from dsa110_contimg.utils.fitting import fit_2d_gaussian, fit_2d_moffat
        from dsa110_contimg.utils.regions import create_region_mask, json_to_region

        db_path = cfg.products_db
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        with _connect(db_path) as conn:
            row = conn.execute(
                "SELECT path FROM images WHERE id = ?", (image_id,)
            ).fetchone()

            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Image {image_id} not found"
                )

            image_path = row["path"]

        # Get FITS file path
        fits_path = get_fits_path(image_path)
        if not fits_path or not Path(fits_path).exists():
            raise HTTPException(
                status_code=404, detail=f"FITS file not found for image {image_id}"
            )

        # Validate model
        if model not in ["gaussian", "moffat"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model: {model}. Must be 'gaussian' or 'moffat'",
            )

        # Parse initial guess if provided
        initial_guess_dict = None
        if initial_guess:
            try:
                initial_guess_dict = json.loads(initial_guess)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400, detail="Invalid JSON in initial_guess parameter"
                )

        # Load FITS file to get header, data shape, and WCS
        region_mask = None
        wcs = None
        try:
            with fits.open(fits_path) as hdul:
                header = hdul[0].header
                data = hdul[0].data

                # Handle multi-dimensional data
                if data.ndim > 2:
                    data = data.squeeze()
                    if data.ndim > 2:
                        data = data[0, 0] if data.ndim == 4 else data[0]

                data_shape = data.shape[:2]  # Get 2D shape (ny, nx)

                # Get WCS from header
                try:
                    wcs = WCS(header)
                except Exception as e:
                    logger.warning(f"Could not load WCS: {e}")
                    wcs = None

                # Get region mask if region_id provided
                if region_id:
                    with _connect(db_path) as conn:
                        region_row = conn.execute(
                            "SELECT * FROM regions WHERE id = ?", (region_id,)
                        ).fetchone()

                        if not region_row:
                            raise HTTPException(
                                status_code=404, detail=f"Region {region_id} not found"
                            )

                        region = json_to_region(
                            {
                                "name": region_row["name"],
                                "type": region_row["type"],
                                "coordinates": json.loads(region_row["coordinates"]),
                                "image_path": region_row["image_path"],
                            }
                        )

                        # Create mask from region
                        region_mask = create_region_mask(
                            shape=data_shape, region=region, wcs=wcs, header=header
                        )

                        # Verify mask has valid pixels
                        if not np.any(region_mask):
                            logger.warning(
                                f"Region {region_id} contains no valid pixels - fitting entire image"
                            )
                            region_mask = None
        except Exception as e:
            logger.error(f"Error loading FITS file or creating region mask: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to process image: {str(e)}"
            )

        try:
            # Perform fitting
            if model == "gaussian":
                fit_result = fit_2d_gaussian(
                    fits_path,
                    region_mask=region_mask,
                    initial_guess=initial_guess_dict,
                    fit_background=fit_background,
                    wcs=wcs,
                )
            else:  # moffat
                fit_result = fit_2d_moffat(
                    fits_path,
                    region_mask=region_mask,
                    initial_guess=initial_guess_dict,
                    fit_background=fit_background,
                    wcs=wcs,
                )

            return fit_result

        except Exception as e:
            logger.error(f"Error fitting {model} to image {image_id}: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to fit {model}: {str(e)}"
            )

    @router.get("/catalog/overlay")
    def get_catalog_overlay(
        ra: float = Query(..., description="RA center in degrees"),
        dec: float = Query(..., description="Dec center in degrees"),
        radius: float = Query(..., description="Search radius in degrees"),
        catalog: str = Query(
            "all", description="Catalog type: nvss, vlass, first, or all"
        ),
    ):
        """Get catalog sources for overlay on images.

        Returns sources within the specified field of view from the master catalog.
        """
        from dsa110_contimg.catalog.query import query_sources

        try:
            # Query sources from catalog
            if catalog == "all":
                # Query master catalog (includes NVSS, VLASS, FIRST)
                df = query_sources(
                    catalog_type="master",
                    ra_center=ra,
                    dec_center=dec,
                    radius_deg=radius,
                )
            else:
                df = query_sources(
                    catalog_type=catalog.lower(),
                    ra_center=ra,
                    dec_center=dec,
                    radius_deg=radius,
                )

            # Convert to list of dictionaries
            sources = []
            for _, row in df.iterrows():
                source = {
                    "ra_deg": float(row.get("ra_deg", 0)),
                    "dec_deg": float(row.get("dec_deg", 0)),
                    "flux_mjy": (
                        float(row.get("flux_mjy", 0)) if "flux_mjy" in row else None
                    ),
                    "source_id": (
                        str(row.get("source_id", "")) if "source_id" in row else None
                    ),
                    "catalog_type": (
                        str(row.get("catalog_type", catalog))
                        if "catalog_type" in row
                        else catalog
                    ),
                }
                sources.append(source)

            return {
                "sources": sources,
                "count": len(sources),
                "ra_center": ra,
                "dec_center": dec,
                "radius_deg": radius,
            }
        except Exception as e:
            logger.error(f"Error querying catalog overlay: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to query catalog: {str(e)}"
            )

    @router.get("/regions")
    def get_regions(
        image_path: Optional[str] = Query(None, description="Filter by image path"),
        region_type: Optional[str] = Query(None, description="Filter by region type"),
    ):
        """Get regions for images.

        Returns list of regions, optionally filtered by image_path or type.
        """
        from dsa110_contimg.utils.regions import json_to_region, region_to_json

        db_path = cfg.products_db
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        with _connect(db_path) as conn:
            query = "SELECT * FROM regions WHERE 1=1"
            params = []

            if image_path:
                query += " AND image_path = ?"
                params.append(image_path)

            if region_type:
                query += " AND type = ?"
                params.append(region_type)

            query += " ORDER BY created_at DESC"

            rows = conn.execute(query, params).fetchall()

            regions = []
            for row in rows:
                region_data = {
                    "id": row["id"],
                    "name": row["name"],
                    "type": row["type"],
                    "coordinates": json.loads(row["coordinates"]),
                    "image_path": row["image_path"],
                    "created_at": row["created_at"],
                    "created_by": row.get("created_by"),
                    "updated_at": row.get("updated_at"),
                }
                regions.append(region_data)

            return {"regions": regions, "count": len(regions)}

    @router.post("/regions")
    def create_region(region_data: Dict[str, Any]):
        """Create a new region.

        Expected fields:
        - name: Region name
        - type: Region type (circle, rectangle, polygon)
        - coordinates: JSON object with coordinates
        - image_path: Path to image
        """
        import time

        from dsa110_contimg.utils.regions import RegionData, region_to_json

        db_path = cfg.products_db
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        # Validate region data
        required_fields = ["name", "type", "coordinates", "image_path"]
        for field in required_fields:
            if field not in region_data:
                raise HTTPException(
                    status_code=400, detail=f"Missing required field: {field}"
                )

        # Create region object
        region = RegionData(
            name=region_data["name"],
            type=region_data["type"],
            coordinates=region_data["coordinates"],
            image_path=region_data["image_path"],
            created_at=time.time(),
            created_by=region_data.get("created_by"),
        )

        # Insert into database
        with _connect(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO regions (name, type, coordinates, image_path, created_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    region.name,
                    region.type,
                    json.dumps(region.coordinates),
                    region.image_path,
                    region.created_at,
                    region.created_by,
                ),
            )
            region_id = cursor.lastrowid
            conn.commit()

        return {"id": region_id, "region": region_to_json(region)}

    @router.get("/regions/{region_id}")
    def get_region(region_id: int):
        """Get a specific region by ID."""
        from dsa110_contimg.utils.regions import json_to_region, region_to_json

        db_path = cfg.products_db
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        with _connect(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM regions WHERE id = ?", (region_id,)
            ).fetchone()

            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Region {region_id} not found"
                )

            region_data = {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "coordinates": json.loads(row["coordinates"]),
                "image_path": row["image_path"],
                "created_at": row["created_at"],
                "created_by": row.get("created_by"),
                "updated_at": row.get("updated_at"),
            }

            return region_data

    @router.put("/regions/{region_id}")
    def update_region(region_id: int, region_data: Dict[str, Any]):
        """Update an existing region."""
        import time

        db_path = cfg.products_db
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        with _connect(db_path) as conn:
            # Check if region exists
            row = conn.execute(
                "SELECT id FROM regions WHERE id = ?", (region_id,)
            ).fetchone()

            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Region {region_id} not found"
                )

            # Update region
            update_fields = []
            params = []

            if "name" in region_data:
                update_fields.append("name = ?")
                params.append(region_data["name"])

            if "coordinates" in region_data:
                update_fields.append("coordinates = ?")
                params.append(json.dumps(region_data["coordinates"]))

            update_fields.append("updated_at = ?")
            params.append(time.time())
            params.append(region_id)

            conn.execute(
                f"UPDATE regions SET {', '.join(update_fields)} WHERE id = ?", params
            )
            conn.commit()

        return {"id": region_id, "updated": True}

    @router.delete("/regions/{region_id}")
    def delete_region(region_id: int):
        """Delete a region."""
        db_path = cfg.products_db
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        with _connect(db_path) as conn:
            cursor = conn.execute("DELETE FROM regions WHERE id = ?", (region_id,))

            if cursor.rowcount == 0:
                raise HTTPException(
                    status_code=404, detail=f"Region {region_id} not found"
                )

            conn.commit()

        return {"id": region_id, "deleted": True}

    @router.get("/regions/{region_id}/statistics")
    def get_region_statistics(region_id: int):
        """Get statistics for pixels within a region."""
        from dsa110_contimg.api.image_utils import get_fits_path
        from dsa110_contimg.utils.regions import (
            calculate_region_statistics,
            json_to_region,
        )

        db_path = cfg.products_db
        if not db_path.exists():
            raise HTTPException(status_code=404, detail="Database not found")

        with _connect(db_path) as conn:
            row = conn.execute(
                "SELECT * FROM regions WHERE id = ?", (region_id,)
            ).fetchone()

            if not row:
                raise HTTPException(
                    status_code=404, detail=f"Region {region_id} not found"
                )

            region = json_to_region(
                {
                    "name": row["name"],
                    "type": row["type"],
                    "coordinates": json.loads(row["coordinates"]),
                    "image_path": row["image_path"],
                }
            )

            # Get FITS path for image
            fits_path = get_fits_path(region.image_path)
            if not fits_path:
                raise HTTPException(
                    status_code=404,
                    detail=f"FITS file not found for image: {region.image_path}",
                )

            # Calculate statistics
            stats = calculate_region_statistics(fits_path, region)

            return {"region_id": region_id, "statistics": stats}

    @router.get("/calibrator_matches", response_model=CalibratorMatchList)
    def calibrator_matches(
        limit: int = 50, matched_only: bool = False
    ) -> CalibratorMatchList:
        items = fetch_recent_calibrator_matches(
            cfg.queue_db, limit=limit, matched_only=matched_only
        )
        return CalibratorMatchList(items=items)

    @router.get("/pointing_history", response_model=PointingHistoryList)
    def pointing_history(start_mjd: float, end_mjd: float) -> PointingHistoryList:
        items = fetch_pointing_history(cfg.products_db, start_mjd, end_mjd)
        return PointingHistoryList(items=items)

    @router.get("/qa", response_model=QAList)
    def qa(limit: int = 100) -> QAList:
        # Prefer DB-backed artifacts if available
        artifacts: list[QAArtifact] = []
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        try:
            if db_path.exists():
                with _connect(db_path) as conn:
                    rows = conn.execute(
                        "SELECT group_id, name, path, created_at FROM qa_artifacts ORDER BY created_at DESC LIMIT ?",
                        (limit,),
                    ).fetchall()
                    for r in rows:
                        ts = (
                            datetime.fromtimestamp(r["created_at"])
                            if r["created_at"]
                            else None
                        )
                        artifacts.append(
                            QAArtifact(
                                group_id=r["group_id"],
                                name=r["name"],
                                path=r["path"],
                                created_at=ts,
                            )
                        )
        except Exception:
            artifacts = []
        if artifacts:
            return QAList(items=artifacts)
        # Fallback to filesystem scan
        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        qa_dir = base_state / "qa"
        if qa_dir.exists():
            for group_subdir in sorted(qa_dir.iterdir()):
                if not group_subdir.is_dir():
                    continue
                group_id = group_subdir.name
                try:
                    for f in group_subdir.iterdir():
                        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg"):
                            try:
                                ts = datetime.fromtimestamp(f.stat().st_mtime)
                            except Exception:
                                ts = None
                            artifacts.append(
                                QAArtifact(
                                    group_id=group_id,
                                    name=f.name,
                                    path=str(f),
                                    created_at=ts,
                                )
                            )
                except Exception:
                    continue
        artifacts.sort(
            key=lambda a: a.created_at or datetime.fromtimestamp(0), reverse=True
        )
        return QAList(items=artifacts[:limit])

    @router.get("/qa/file/{group}/{name}")
    def qa_file(group: str, name: str):
        """Serve QA files with path traversal protection.

        CRITICAL: Validates input to prevent path traversal attacks.
        Only allows files within the QA directory structure.
        """
        # CRITICAL: Validate input doesn't contain path separators or traversal sequences
        if "/" in group or "\\" in group or ".." in group:
            return HTMLResponse(status_code=400, content="Invalid group name")
        if "/" in name or "\\" in name or ".." in name:
            return HTMLResponse(status_code=400, content="Invalid file name")

        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        base = (base_state / "qa").resolve()

        # CRITICAL: Use joinpath to safely construct path (prevents double slashes, etc.)
        # Then resolve to handle any symlinks and get absolute path
        fpath = base.joinpath(group, name).resolve()

        # CRITICAL: Verify resolved path is still within base directory
        # This handles symlink attacks and ensures we don't escape the base directory
        try:
            # Python 3.9+: safe containment check that handles symlinks
            fpath.relative_to(base.resolve())
        except (ValueError, AttributeError):
            # Path is outside base directory or Python < 3.9 fallback
            # For Python < 3.9, use string comparison as fallback
            # Note: This is less secure against symlinks but better than nothing
            base_str = str(base.resolve()) + os.sep
            fpath_str = str(fpath)
            if not fpath_str.startswith(base_str):
                return HTMLResponse(status_code=403, content="Forbidden")

        if not fpath.exists() or not fpath.is_file():
            return HTMLResponse(status_code=404, content="Not found")

        return FileResponse(str(fpath))

    # System metrics helper and history buffer
    _METRICS_HISTORY: deque[SystemMetrics] = deque(maxlen=200)

    def _get_system_metrics() -> SystemMetrics:
        ts = datetime.utcnow()
        cpu = mem_pct = mem_total = mem_used = disk_total = disk_used = None
        load1 = load5 = load15 = None
        try:
            import psutil  # type: ignore

            cpu = float(psutil.cpu_percent(interval=0.0))
            vm = psutil.virtual_memory()
            mem_pct = float(vm.percent)
            mem_total = int(vm.total)
            mem_used = int(vm.used)
        except Exception:
            pass
        try:
            du = shutil.disk_usage("/")
            disk_total = int(du.total)
            disk_used = int(du.used)
        except Exception:
            pass
        try:
            load1, load5, load15 = os.getloadavg()
        except Exception:
            pass
        return SystemMetrics(
            ts=ts,
            cpu_percent=cpu,
            mem_percent=mem_pct,
            mem_total=mem_total,
            mem_used=mem_used,
            disk_total=disk_total,
            disk_used=disk_used,
            load_1=load1,
            load_5=load5,
            load_15=load15,
        )

    @router.get("/metrics/system", response_model=SystemMetrics)
    def metrics_system() -> SystemMetrics:
        m = _get_system_metrics()
        _METRICS_HISTORY.append(m)
        return m

    @router.get("/metrics/system/history", response_model=List[SystemMetrics])
    def metrics_history(limit: int = 60) -> List[SystemMetrics]:
        m = _get_system_metrics()
        _METRICS_HISTORY.append(m)
        n = max(1, min(limit, len(_METRICS_HISTORY)))
        return list(_METRICS_HISTORY)[-n:]

    @router.get("/qa/thumbs", response_model=QAList)
    def qa_thumbs(limit: int = 100) -> QAList:
        artifacts: list[QAArtifact] = []
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        try:
            if db_path.exists():
                with _connect(db_path) as conn:
                    rows = conn.execute(
                        """
                        SELECT qa.group_id, qa.name, qa.path, qa.created_at
                          FROM qa_artifacts qa
                          JOIN (
                            SELECT group_id, MAX(created_at) AS mc
                              FROM qa_artifacts
                          GROUP BY group_id
                          ) q ON qa.group_id = q.group_id AND qa.created_at = q.mc
                         ORDER BY qa.created_at DESC
                         LIMIT ?
                        """,
                        (limit,),
                    ).fetchall()
                    for r in rows:
                        ts = (
                            datetime.fromtimestamp(r["created_at"])
                            if r["created_at"]
                            else None
                        )
                        artifacts.append(
                            QAArtifact(
                                group_id=r["group_id"],
                                name=r["name"],
                                path=r["path"],
                                created_at=ts,
                            )
                        )
                    return QAList(items=artifacts)
        except Exception:
            artifacts = []
        # FS fallback: use latest image per group
        base = Path(os.getenv("PIPELINE_STATE_DIR", "state")) / "qa"
        if base.exists():
            for sub in sorted(base.iterdir()):
                if not sub.is_dir():
                    continue
                latest = None
                for f in sorted(
                    sub.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True
                ):
                    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg"):
                        latest = f
                        break
                if latest:
                    ts = datetime.fromtimestamp(latest.stat().st_mtime)
                    artifacts.append(
                        QAArtifact(
                            group_id=sub.name,
                            name=latest.name,
                            path=str(latest),
                            created_at=ts,
                        )
                    )
        return QAList(items=artifacts[:limit])

    @router.get("/groups/{group_id}", response_model=GroupDetail)
    def group_detail(group_id: str) -> GroupDetail:
        # Fetch queue group details, including state and counts
        with _connect(cfg.queue_db) as conn:
            row = conn.execute(
                """
                SELECT iq.group_id, iq.state, iq.received_at, iq.last_update,
                       iq.expected_subbands, iq.has_calibrator, iq.calibrators,
                       COUNT(sf.subband_idx) AS subbands
                  FROM ingest_queue iq
             LEFT JOIN subband_files sf ON iq.group_id = sf.group_id
                 WHERE iq.group_id = ?
              GROUP BY iq.group_id
                """,
                (group_id,),
            ).fetchone()
            if row is None:
                return HTMLResponse(status_code=404, content="Not found")
            # Try performance metrics
            perf = conn.execute(
                "SELECT total_time FROM performance_metrics WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            perf_total = float(perf[0]) if perf and perf[0] is not None else None

        # Parse matches JSON
        import json as _json

        matches_list = []
        cal_json = row["calibrators"] or "[]"
        try:
            parsed_list = _json.loads(cal_json)
        except Exception:
            parsed_list = []
        from dsa110_contimg.api.models import CalibratorMatch

        for m in parsed_list if isinstance(parsed_list, list) else []:
            try:
                matches_list.append(
                    CalibratorMatch(
                        name=str(m.get("name", "")),
                        ra_deg=float(m.get("ra_deg", 0.0)),
                        dec_deg=float(m.get("dec_deg", 0.0)),
                        sep_deg=float(m.get("sep_deg", 0.0)),
                        weighted_flux=(
                            float(m.get("weighted_flux"))
                            if m.get("weighted_flux") is not None
                            else None
                        ),
                    )
                )
            except Exception:
                continue

        # Collect QA artifacts from DB (with filesystem fallback)
        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        qa_dir = base_state / "qa" / group_id
        qa_items: list[QAArtifact] = []
        # DB first
        try:
            pdb = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
            if pdb.exists():
                with _connect(pdb) as conn:
                    rows = conn.execute(
                        "SELECT name, path, created_at FROM qa_artifacts WHERE group_id = ? ORDER BY created_at DESC",
                        (group_id,),
                    ).fetchall()
                    for r in rows:
                        ts = (
                            datetime.fromtimestamp(r["created_at"])
                            if r["created_at"]
                            else None
                        )
                        qa_items.append(
                            QAArtifact(
                                group_id=group_id,
                                name=r["name"],
                                path=r["path"],
                                created_at=ts,
                            )
                        )
        except Exception:
            qa_items = []
        # FS fallback
        if not qa_items and qa_dir.exists():
            for f in qa_dir.iterdir():
                if (
                    f.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg", ".html")
                    and f.is_file()
                ):
                    try:
                        ts = datetime.fromtimestamp(f.stat().st_mtime)
                    except Exception:
                        ts = None
                    qa_items.append(
                        QAArtifact(
                            group_id=group_id, name=f.name, path=str(f), created_at=ts
                        )
                    )

        # Fetch writer type from performance_metrics
        writer_type = None
        try:
            pdb = _connect(cfg.queue_db)
            with pdb:
                w = pdb.execute(
                    "SELECT writer_type FROM performance_metrics WHERE group_id = ?",
                    (group_id,),
                ).fetchone()
                if w is not None:
                    writer_type = w[0]
        except Exception:
            writer_type = None

        return GroupDetail(
            group_id=row["group_id"],
            state=row["state"],
            received_at=datetime.fromtimestamp(row["received_at"]),
            last_update=datetime.fromtimestamp(row["last_update"]),
            subbands_present=row["subbands"] or 0,
            expected_subbands=row["expected_subbands"] or 16,
            has_calibrator=(
                bool(row["has_calibrator"])
                if row["has_calibrator"] is not None
                else None
            ),
            matches=matches_list or None,
            qa=qa_items,
            perf_total_time=perf_total,
            writer_type=writer_type,
        )

    @router.get("/ui/calibrators", response_class=HTMLResponse)
    def ui_calibrators(limit: int = 50) -> HTMLResponse:
        items = fetch_recent_calibrator_matches(cfg.queue_db, limit=limit)
        rows = []
        for g in items:
            if g.matched and g.matches:
                match_html = (
                    "<ul>"
                    + "".join(
                        f"<li>{m.name} (sep {m.sep_deg:.2f}°; RA {m.ra_deg:.4f}°, Dec {m.dec_deg:.4f}°; wflux {'' if m.weighted_flux is None else f'{m.weighted_flux:.2f} Jy' })</li>"
                        for m in g.matches
                    )
                    + "</ul>"
                )
            else:
                match_html = "<em>none</em>"
            rows.append(
                f"<tr><td>{g.group_id}</td><td>{g.matched}</td><td>{g.received_at}</td><td>{g.last_update}</td><td>{match_html}</td></tr>"
            )
        html = f"""
        <html><head><title>Calibrator Matches</title>
        <style>
          body {{ font-family: sans-serif; }}
          table, th, td {{ border: 1px solid #ddd; border-collapse: collapse; padding: 6px; }}
          th {{ background: #f0f0f0; }}
        </style>
        </head><body>
        <h2>Recent Calibrator Matches</h2>
        <table>
          <tr><th>Group</th><th>Matched</th><th>Received</th><th>Last Update</th><th>Matches</th></tr>
          {''.join(rows)}
        </table>
        </body></html>
        """
        return HTMLResponse(content=html, status_code=200)

    # NOTE:
    # Include the API router after ALL route declarations.
    # Previously this was called before several endpoints (e.g., /ms_index,
    # /reprocess, /ese/candidates, /mosaics, /sources, /alerts/history)
    # were attached to `router`, which meant those routes were missing from
    # the running application. Moving the include to the end ensures every
    # route registered on `router` is exposed.

    # Additional endpoints: ms_index querying and reprocess trigger
    @router.get("/ms_index", response_model=MsIndexList)
    def ms_index(
        stage: str | None = None, status: str | None = None, limit: int = 100
    ) -> MsIndexList:
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        items: list[MsIndexEntry] = []
        if not db_path.exists():
            return MsIndexList(items=items)
        with _connect(db_path) as conn:
            q = "SELECT path, start_mjd, end_mjd, mid_mjd, processed_at, status, stage, stage_updated_at, cal_applied, imagename FROM ms_index"
            where = []
            params: list[object] = []
            if stage:
                where.append("stage = ?")
                params.append(stage)
            if status:
                where.append("status = ?")
                params.append(status)
            if where:
                q += " WHERE " + " AND ".join(where)
            # SQLite does not support NULLS LAST; DESC naturally places NULLs last for numeric values.
            q += " ORDER BY COALESCE(stage_updated_at, processed_at) DESC LIMIT ?"
            params.append(int(limit))
            rows = conn.execute(q, params).fetchall()
            for r in rows:
                items.append(
                    MsIndexEntry(
                        path=r["path"],
                        start_mjd=r["start_mjd"],
                        end_mjd=r["end_mjd"],
                        mid_mjd=r["mid_mjd"],
                        processed_at=(
                            datetime.fromtimestamp(r["processed_at"])
                            if r["processed_at"]
                            else None
                        ),
                        status=r["status"],
                        stage=r["stage"],
                        stage_updated_at=(
                            datetime.fromtimestamp(r["stage_updated_at"])
                            if r["stage_updated_at"]
                            else None
                        ),
                        cal_applied=r["cal_applied"],
                        imagename=r["imagename"],
                    )
                )
        return MsIndexList(items=items)

    @router.post("/reprocess/{group_id}")
    def reprocess_group(group_id: str):
        # Nudge the ingest_queue row back to 'pending' to trigger reprocessing
        qdb = Path(
            os.getenv(
                "PIPELINE_QUEUE_DB",
                os.getenv("PIPELINE_QUEUE_DB", "state/ingest.sqlite3"),
            )
        )
        if not qdb.exists():
            return {"ok": False, "error": "queue_db not found"}
        with _connect(qdb) as conn:
            now = datetime.utcnow().timestamp()
            row = conn.execute(
                "SELECT state, retry_count FROM ingest_queue WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            if row is None:
                return {"ok": False, "error": "group not found"}
            new_retry = (row["retry_count"] or 0) + 1
            conn.execute(
                "UPDATE ingest_queue SET state='pending', last_update=?, retry_count=? WHERE group_id = ?",
                (now, new_retry, group_id),
            )
            conn.commit()
        return {"ok": True}

    # Enhanced API endpoints for new dashboard features

    @router.get("/ese/candidates", response_model=ESECandidatesResponse)
    def ese_candidates(limit: int = 50, min_sigma: float = 5.0):
        """Get ESE candidate sources from database."""
        candidates_data = fetch_ese_candidates(
            cfg.products_db, limit=limit, min_sigma=min_sigma
        )
        candidates = [ESECandidate(**c) for c in candidates_data]
        return ESECandidatesResponse(
            candidates=candidates,
            total=len(candidates),
        )

    @router.post("/mosaics/query", response_model=MosaicQueryResponse)
    def mosaics_query(request: dict):
        """Query mosaics by time range from database."""
        start_time = request.get("start_time", "")
        end_time = request.get("end_time", "")

        if not start_time or not end_time:
            return MosaicQueryResponse(mosaics=[], total=0)

        mosaics_data = fetch_mosaics(cfg.products_db, start_time, end_time)
        mosaics = [Mosaic(**m) for m in mosaics_data]
        return MosaicQueryResponse(
            mosaics=mosaics,
            total=len(mosaics),
        )

    @router.post("/mosaics/create")
    def mosaics_create(request: dict):
        """Create a new mosaic (queue mosaic generation job).

        Note: This is a placeholder for future mosaic generation pipeline integration.
        For now, returns a response indicating the feature is not yet implemented.
        """
        return {
            "status": "not_implemented",
            "message": "Mosaic creation via API is not yet implemented. Use the mosaic CLI tools.",
            "mosaic_id": None,
        }

    @router.get("/mosaics/{mosaic_id}", response_model=Mosaic)
    def get_mosaic(mosaic_id: int):
        """Get a single mosaic by ID."""
        mosaic_data = fetch_mosaic_by_id(cfg.products_db, mosaic_id)
        if not mosaic_data:
            raise HTTPException(status_code=404, detail=f"Mosaic {mosaic_id} not found")
        return Mosaic(**mosaic_data)

    @router.get("/mosaics/{mosaic_id}/fits")
    def get_mosaic_fits(mosaic_id: int):
        """Serve FITS file for a mosaic."""
        mosaic_data = fetch_mosaic_by_id(cfg.products_db, mosaic_id)
        if not mosaic_data:
            raise HTTPException(status_code=404, detail=f"Mosaic {mosaic_id} not found")

        mosaic_path = mosaic_data["path"]

        # Check if path exists
        if not Path(mosaic_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"FITS file not found for mosaic {mosaic_id}: {mosaic_path}",
            )

        # Serve FITS file
        return FileResponse(
            mosaic_path,
            media_type="application/fits",
            filename=Path(mosaic_path).name,
        )

    @router.post("/sources/search", response_model=SourceSearchResponse)
    def sources_search(request: dict):
        """Search for sources and return flux timeseries from photometry database."""
        source_id = request.get("source_id", "")

        if not source_id:
            return SourceSearchResponse(sources=[], total=0)

        source_data = fetch_source_timeseries(cfg.products_db, source_id)

        if source_data is None:
            return SourceSearchResponse(sources=[], total=0)

        # Convert flux points to SourceFluxPoint models
        from dsa110_contimg.api.models import SourceFluxPoint

        flux_points = [SourceFluxPoint(**fp) for fp in source_data["flux_points"]]

        source = SourceTimeseries(
            source_id=source_data["source_id"],
            ra_deg=source_data["ra_deg"],
            dec_deg=source_data["dec_deg"],
            catalog=source_data["catalog"],
            flux_points=flux_points,
            mean_flux_jy=source_data["mean_flux_jy"],
            std_flux_jy=source_data["std_flux_jy"],
            chi_sq_nu=source_data["chi_sq_nu"],
            is_variable=source_data["is_variable"],
        )

        return SourceSearchResponse(
            sources=[source],
            total=1,
        )

    @router.get("/alerts/history", response_model=List[AlertHistory])
    def alerts_history(limit: int = 50):
        """Get alert history from database."""
        alerts_data = fetch_alert_history(cfg.products_db, limit=limit)
        alerts = [AlertHistory(**a) for a in alerts_data]
        return alerts

    # Control panel routes
    @router.get("/ms", response_model=MSList)
    def list_ms(
        search: str | None = None,
        has_calibrator: bool | None = None,
        is_calibrated: bool | None = None,
        is_imaged: bool | None = None,
        calibrator_quality: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        sort_by: str = "time_desc",
        limit: int = 100,
        offset: int = 0,
        scan: bool = False,
        scan_dir: str | None = None,
    ) -> MSList:
        """List available Measurement Sets with filtering and sorting.

        Args:
            scan: If True, scan filesystem for MS files before listing
            scan_dir: Directory to scan (defaults to CONTIMG_OUTPUT_DIR or /stage/dsa110-contimg/ms)
            limit: Maximum number of results (1-1000, default: 100)
            offset: Offset for pagination (>= 0, default: 0)
        """
        # Validate and clamp parameters
        limit = max(1, min(limit, 1000)) if limit > 0 else 100
        offset = max(0, offset) if offset >= 0 else 0

        import astropy.units as u
        from astropy.time import Time

        from dsa110_contimg.database.products import (
            discover_ms_files,
            ensure_products_db,
        )

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))

        # Optionally scan filesystem for MS files
        if scan:
            if scan_dir is None:
                scan_dir = os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/ms")
            try:
                discovered = discover_ms_files(db_path, scan_dir, recursive=True)
                logger.info(f"Discovered {len(discovered)} MS files from {scan_dir}")
            except Exception as e:
                logger.warning(f"Failed to scan for MS files: {e}")

        entries: list[MSListEntry] = []

        try:
            conn = ensure_products_db(db_path)

            # Build query with filters
            where_clauses = []
            params: list[object] = []

            if search:
                where_clauses.append(
                    "(m.path LIKE ? OR COALESCE(cm.calibrator_name, '') LIKE ?)"
                )
                params.extend([f"%{search}%", f"%{search}%"])

            if has_calibrator is not None:
                if has_calibrator:
                    where_clauses.append("cm.has_calibrator = 1")
                else:
                    where_clauses.append(
                        "(cm.has_calibrator = 0 OR cm.has_calibrator IS NULL)"
                    )

            if is_calibrated is not None:
                if is_calibrated:
                    where_clauses.append("m.cal_applied = 1")
                else:
                    where_clauses.append("(m.cal_applied = 0 OR m.cal_applied IS NULL)")

            if is_imaged is not None:
                if is_imaged:
                    where_clauses.append(
                        "m.imagename IS NOT NULL AND m.imagename != ''"
                    )
                else:
                    where_clauses.append("(m.imagename IS NULL OR m.imagename = '')")

            if calibrator_quality:
                where_clauses.append("cm.calibrator_quality = ?")
                params.append(calibrator_quality)

            if start_date:
                try:
                    start_mjd = Time(start_date).mjd
                    where_clauses.append("m.mid_mjd >= ?")
                    params.append(start_mjd)
                except Exception:
                    pass

            if end_date:
                try:
                    end_mjd = Time(end_date).mjd
                    where_clauses.append("m.mid_mjd <= ?")
                    params.append(end_mjd)
                except Exception:
                    pass

            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

            # Determine sort order
            sort_mapping = {
                "time_desc": "m.mid_mjd DESC",
                "time_asc": "m.mid_mjd ASC",
                "name_asc": "m.path ASC",
                "name_desc": "m.path DESC",
                "size_desc": "m.path DESC",  # Size not in DB yet, use path
                "size_asc": "m.path ASC",
            }
            order_by = sort_mapping.get(sort_by, "m.mid_mjd DESC")

            # Get total count (before pagination)
            # Simplified query - pointing_history doesn't have ms_path or calibrator columns
            count_query = f"""
                SELECT COUNT(*) FROM ms_index m
                WHERE {where_sql}
            """
            total_count = conn.execute(count_query, params).fetchone()[0]

            # Main query with joins (simplified - no calibrator info from pointing_history)
            query = f"""
                SELECT 
                    m.path,
                    m.mid_mjd,
                    m.status,
                    m.cal_applied,
                    0 as has_calibrator,
                    NULL as calibrator_name,
                    NULL as calibrator_quality,
                    CASE WHEN m.cal_applied = 1 THEN 1 ELSE 0 END as is_calibrated,
                    CASE WHEN m.imagename IS NOT NULL AND m.imagename != '' THEN 1 ELSE 0 END as is_imaged,
                    cq.overall_quality as calibration_quality,
                    iq.overall_quality as image_quality,
                    m.start_mjd,
                    m.end_mjd
                FROM ms_index m
                LEFT JOIN (
                    SELECT ms_path, overall_quality
                    FROM calibration_qa
                    WHERE id IN (SELECT MAX(id) FROM calibration_qa GROUP BY ms_path)
                ) cq ON m.path = cq.ms_path
                LEFT JOIN (
                    SELECT ms_path, overall_quality
                    FROM image_qa
                    WHERE id IN (SELECT MAX(id) FROM image_qa GROUP BY ms_path)
                ) iq ON m.path = iq.ms_path
                WHERE {where_sql}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])

            rows = conn.execute(query, params).fetchall()
            conn.close()

            for row in rows:
                # Convert MJD to datetime string if available
                start_time = None
                if row[11]:  # start_mjd
                    try:
                        start_time = Time(row[11], format="mjd").iso
                    except Exception:
                        pass

                # Calculate size (placeholder - would need actual file size)
                size_gb = None
                try:
                    ms_path = Path(row[0])
                    if ms_path.exists():
                        total_size = sum(
                            f.stat().st_size for f in ms_path.rglob("*") if f.is_file()
                        )
                        size_gb = total_size / (1024**3)
                except Exception:
                    pass

                entries.append(
                    MSListEntry(
                        path=row[0],
                        mid_mjd=row[1],
                        status=row[2],
                        cal_applied=row[3],
                        has_calibrator=bool(row[4]),
                        calibrator_name=row[5],
                        calibrator_quality=row[6],
                        is_calibrated=bool(row[7]),
                        is_imaged=bool(row[8]),
                        calibration_quality=row[9],
                        image_quality=row[10],
                        size_gb=size_gb,
                        start_time=start_time,
                    )
                )
        except Exception as e:
            logger.error(f"Failed to list MS: {e}")
            return MSList(items=[], total=0, filtered=0)

        return MSList(items=entries, total=total_count, filtered=len(entries))

    @router.post("/ms/discover")
    def discover_ms(request: dict | None = None) -> dict:
        """Scan filesystem for MS files and register them in the database.

        Request body (optional):
            scan_dir: Directory to scan (defaults to CONTIMG_OUTPUT_DIR or /stage/dsa110-contimg/ms)
            recursive: If True, scan subdirectories recursively (default: True)

        Returns:
            Dictionary with count of discovered MS files and list of paths
        """
        from dsa110_contimg.database.products import (
            discover_ms_files,
            ensure_products_db,
        )

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))

        if request is None:
            request = {}

        scan_dir = request.get("scan_dir")
        recursive = request.get("recursive", True)

        if scan_dir is None:
            scan_dir = os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/ms")

        try:
            discovered = discover_ms_files(db_path, scan_dir, recursive=recursive)
            return {
                "success": True,
                "count": len(discovered),
                "scan_dir": scan_dir,
                "discovered": discovered,
            }
        except Exception as e:
            logger.error(f"Failed to discover MS files: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Discovery failed: {str(e)}")

    @router.get("/jobs", response_model=JobList)
    def list_jobs(limit: int = 50, status: str | None = None) -> JobList:
        """List recent jobs."""
        from dsa110_contimg.api.models import JobParams
        from dsa110_contimg.database.jobs import list_jobs as db_list_jobs
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)
        jobs_data = db_list_jobs(conn, limit=limit, status=status)
        conn.close()

        jobs = []
        for jd in jobs_data:
            jobs.append(
                Job(
                    id=jd["id"],
                    type=jd["type"],
                    status=jd["status"],
                    ms_path=jd["ms_path"],
                    params=JobParams(**jd["params"]),
                    logs=jd["logs"],
                    artifacts=jd["artifacts"],
                    created_at=datetime.fromtimestamp(jd["created_at"]),
                    started_at=(
                        datetime.fromtimestamp(jd["started_at"])
                        if jd["started_at"]
                        else None
                    ),
                    finished_at=(
                        datetime.fromtimestamp(jd["finished_at"])
                        if jd["finished_at"]
                        else None
                    ),
                )
            )

        return JobList(items=jobs)

    @router.get("/jobs/id/{job_id}", response_model=Job)
    def get_job(job_id: int) -> Job:
        """Get job details by ID."""
        from dsa110_contimg.api.models import JobParams
        from dsa110_contimg.database.jobs import get_job as db_get_job
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)
        jd = db_get_job(conn, job_id)
        conn.close()

        if not jd:
            raise HTTPException(status_code=404, detail="Job not found")

        return Job(
            id=jd["id"],
            type=jd["type"],
            status=jd["status"],
            ms_path=jd["ms_path"],
            params=JobParams(**jd["params"]),
            logs=jd["logs"],
            artifacts=jd["artifacts"],
            created_at=datetime.fromtimestamp(jd["created_at"]),
            started_at=(
                datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None
            ),
            finished_at=(
                datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None
            ),
        )

    @router.get("/jobs/id/{job_id}/logs")
    def stream_job_logs(job_id: int):
        """Stream job logs via SSE."""
        from dsa110_contimg.database.jobs import get_job as db_get_job
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))

        async def event_stream():
            last_pos = 0
            conn = ensure_products_db(db_path)

            while True:
                jd = db_get_job(conn, job_id)
                if not jd:
                    yield f'event: error\ndata: {{"message": "Job not found"}}\n\n'
                    break

                logs = jd.get("logs", "")
                if len(logs) > last_pos:
                    new_content = logs[last_pos:]
                    yield f"data: {json.dumps({'logs': new_content})}\n\n"
                    last_pos = len(logs)

                # Check if job is done
                if jd["status"] in ["done", "failed"]:
                    yield f"event: complete\ndata: {{\"status\": \"{jd['status']}\"}}\n\n"
                    break

                await asyncio.sleep(1)

            conn.close()

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    @router.post("/jobs/calibrate", response_model=Job)
    def create_calibrate_job(
        request: JobCreateRequest, background_tasks: BackgroundTasks
    ) -> Job:
        """Create and run a calibration job."""
        from dsa110_contimg.api.job_runner import run_calibrate_job
        from dsa110_contimg.api.models import JobParams
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        job_id = create_job(
            conn, "calibrate", request.ms_path, request.params.model_dump()
        )
        conn.close()

        # Start job in background
        background_tasks.add_task(
            run_calibrate_job,
            job_id,
            request.ms_path,
            request.params.model_dump(),
            db_path,
        )

        # Return initial job state
        conn = ensure_products_db(db_path)
        from dsa110_contimg.database.jobs import get_job as db_get_job

        jd = db_get_job(conn, job_id)
        conn.close()

        return Job(
            id=jd["id"],
            type=jd["type"],
            status=jd["status"],
            ms_path=jd["ms_path"],
            params=JobParams(**jd["params"]),
            logs=jd["logs"],
            artifacts=jd["artifacts"],
            created_at=datetime.fromtimestamp(jd["created_at"]),
            started_at=(
                datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None
            ),
            finished_at=(
                datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None
            ),
        )

    @router.post("/jobs/apply", response_model=Job)
    def create_apply_job(
        request: JobCreateRequest, background_tasks: BackgroundTasks
    ) -> Job:
        """Create and run an apply calibration job."""
        from dsa110_contimg.api.job_runner import run_apply_job
        from dsa110_contimg.api.models import JobParams
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        job_id = create_job(conn, "apply", request.ms_path, request.params.model_dump())
        conn.close()

        # Start job in background
        background_tasks.add_task(
            run_apply_job, job_id, request.ms_path, request.params.model_dump(), db_path
        )

        # Return initial job state
        conn = ensure_products_db(db_path)
        from dsa110_contimg.database.jobs import get_job as db_get_job

        jd = db_get_job(conn, job_id)
        conn.close()

        return Job(
            id=jd["id"],
            type=jd["type"],
            status=jd["status"],
            ms_path=jd["ms_path"],
            params=JobParams(**jd["params"]),
            logs=jd["logs"],
            artifacts=jd["artifacts"],
            created_at=datetime.fromtimestamp(jd["created_at"]),
            started_at=(
                datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None
            ),
            finished_at=(
                datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None
            ),
        )

    @router.post("/jobs/image", response_model=Job)
    def create_image_job(
        request: JobCreateRequest, background_tasks: BackgroundTasks
    ) -> Job:
        """Create and run an imaging job."""
        from dsa110_contimg.api.job_runner import run_image_job
        from dsa110_contimg.api.models import JobParams
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        job_id = create_job(conn, "image", request.ms_path, request.params.model_dump())
        conn.close()

        # Start job in background
        background_tasks.add_task(
            run_image_job, job_id, request.ms_path, request.params.model_dump(), db_path
        )

        # Return initial job state
        conn = ensure_products_db(db_path)
        from dsa110_contimg.database.jobs import get_job as db_get_job

        jd = db_get_job(conn, job_id)
        conn.close()

        return Job(
            id=jd["id"],
            type=jd["type"],
            status=jd["status"],
            ms_path=jd["ms_path"],
            params=JobParams(**jd["params"]),
            logs=jd["logs"],
            artifacts=jd["artifacts"],
            created_at=datetime.fromtimestamp(jd["created_at"]),
            started_at=(
                datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None
            ),
            finished_at=(
                datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None
            ),
        )

    @router.get("/uvh5", response_model=UVH5FileList)
    def list_uvh5_files(input_dir: str | None = None, limit: int = 100) -> UVH5FileList:
        """List available UVH5 files for conversion."""
        import glob as _glob
        import re

        from dsa110_contimg.api.models import UVH5FileEntry, UVH5FileList

        if input_dir is None:
            input_dir = os.getenv("CONTIMG_INPUT_DIR", "/data/incoming")

        entries: list[UVH5FileEntry] = []

        try:
            search_path = Path(input_dir)
            if not search_path.exists():
                return UVH5FileList(items=[])

            # Find all .hdf5 files
            pattern = str(search_path / "**/*.hdf5")
            files = sorted(_glob.glob(pattern, recursive=True), reverse=True)[:limit]

            for fpath in files:
                fname = os.path.basename(fpath)
                size_mb = os.path.getsize(fpath) / (1024 * 1024)

                # Extract timestamp and subband from filename
                # Expected format: YYYY-MM-DDTHH:MM:SS_sbXX.hdf5
                timestamp = None
                subband = None
                match = re.match(r"(.+)_sb(\d+)\.hdf5$", fname)
                if match:
                    timestamp = match.group(1)
                    subband = f"sb{match.group(2)}"

                entries.append(
                    UVH5FileEntry(
                        path=fpath,
                        timestamp=timestamp,
                        subband=subband,
                        size_mb=round(size_mb, 2),
                    )
                )
        except Exception:
            pass

        return UVH5FileList(items=entries)

    @router.post("/jobs/convert", response_model=Job)
    def create_convert_job(
        request: ConversionJobCreateRequest, background_tasks: BackgroundTasks
    ) -> Job:
        """Create and run a UVH5 → MS conversion job."""
        from dsa110_contimg.api.job_runner import run_convert_job
        from dsa110_contimg.api.models import ConversionJobParams, JobParams
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        # Create job with conversion params (ms_path is empty for conversion jobs)
        job_id = create_job(conn, "convert", "", request.params.model_dump())
        conn.close()

        # Start job in background
        background_tasks.add_task(
            run_convert_job, job_id, request.params.model_dump(), db_path
        )

        # Return initial job state
        conn = ensure_products_db(db_path)
        from dsa110_contimg.database.jobs import get_job as db_get_job

        jd = db_get_job(conn, job_id)
        conn.close()

        # For conversion jobs, use ConversionJobParams instead of JobParams
        return Job(
            id=jd["id"],
            type=jd["type"],
            status=jd["status"],
            ms_path=jd["ms_path"],
            params=(
                JobParams(**jd["params"]) if jd["type"] != "convert" else JobParams()
            ),  # Placeholder
            logs=jd["logs"],
            artifacts=jd["artifacts"],
            created_at=datetime.fromtimestamp(jd["created_at"]),
            started_at=(
                datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None
            ),
            finished_at=(
                datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None
            ),
        )

    @router.get("/caltables", response_model=CalTableList)
    def list_caltables(cal_dir: str | None = None) -> CalTableList:
        """List available calibration tables."""
        import glob as _glob
        import re

        from dsa110_contimg.api.models import CalTableInfo, CalTableList

        if cal_dir is None:
            cal_dir = os.getenv("CONTIMG_CAL_DIR", "/stage/dsa110-contimg/caltables")

        entries: list[CalTableInfo] = []

        try:
            search_path = Path(cal_dir)
            if not search_path.exists():
                return CalTableList(items=[])

            # Find all .cal files (K, BP, G tables)
            patterns = ["**/*.kcal", "**/*.bpcal", "**/*.gpcal", "**/*.fcal"]
            files = []
            for pattern in patterns:
                files.extend(_glob.glob(str(search_path / pattern), recursive=True))

            files = sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)

            for fpath in files:
                fname = os.path.basename(fpath)
                size_mb = (
                    sum(
                        os.path.getsize(os.path.join(dirpath, filename))
                        for dirpath, _, filenames in os.walk(fpath)
                        for filename in filenames
                    )
                    / (1024 * 1024)
                    if os.path.isdir(fpath)
                    else os.path.getsize(fpath) / (1024 * 1024)
                )

                # Determine table type from extension
                if fname.endswith(".kcal"):
                    table_type = "K"
                elif fname.endswith(".bpcal"):
                    table_type = "BP"
                elif fname.endswith(".gpcal"):
                    table_type = "G"
                elif fname.endswith(".fcal"):
                    table_type = "F"
                else:
                    table_type = "unknown"

                modified_time = datetime.fromtimestamp(os.path.getmtime(fpath))

                entries.append(
                    CalTableInfo(
                        path=fpath,
                        filename=fname,
                        table_type=table_type,
                        size_mb=round(size_mb, 2),
                        modified_time=modified_time,
                    )
                )
        except Exception:
            pass

        return CalTableList(items=entries)

    @router.get("/ms/{ms_path:path}/metadata", response_model=MSMetadata)
    def get_ms_metadata(ms_path: str) -> MSMetadata:
        """Get metadata for an MS file."""
        import numpy as np
        from casatools import ms as casams
        from casatools import table

        from dsa110_contimg.api.models import (
            AntennaInfo,
            FieldInfo,
            FlaggingStats,
            MSMetadata,
        )

        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith("/") else ms_path

        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")

        metadata = MSMetadata(path=ms_full_path)

        try:
            # Get basic info from MAIN table
            tb = table()
            tb.open(ms_full_path, nomodify=True)

            # Extract time range using standardized utility (handles format detection)
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            start_mjd, end_mjd, _ = extract_ms_time_range(str(ms_path))
            if start_mjd is not None and end_mjd is not None:
                from astropy.time import Time

                start_time_obj = Time(start_mjd, format="mjd")
                end_time_obj = Time(end_mjd, format="mjd")
                metadata.start_time = start_time_obj.isot
                metadata.end_time = end_time_obj.isot
                metadata.duration_sec = (end_mjd - start_mjd) * 86400.0

            # Get available data columns
            colnames = tb.colnames()
            data_cols = [col for col in colnames if "DATA" in col]
            metadata.data_columns = data_cols
            metadata.calibrated = "CORRECTED_DATA" in data_cols

            # Get flagging statistics
            try:
                flags = tb.getcol("FLAG")
                if flags.size > 0:
                    total_flagged = np.sum(flags)
                    total_data = flags.size
                    flag_fraction = (
                        float(total_flagged / total_data) if total_data > 0 else 0.0
                    )

                    # Per-antenna flagging
                    ant1 = tb.getcol("ANTENNA1")
                    ant2 = tb.getcol("ANTENNA2")
                    per_antenna = {}
                    unique_ants = np.unique(np.concatenate([ant1, ant2]))
                    for ant_id in unique_ants:
                        ant_mask = (ant1 == ant_id) | (ant2 == ant_id)
                        if np.any(ant_mask):
                            ant_flags = flags[ant_mask]
                            ant_frac = (
                                float(np.sum(ant_flags) / ant_flags.size)
                                if ant_flags.size > 0
                                else 0.0
                            )
                            per_antenna[str(int(ant_id))] = ant_frac

                    # Per-field flagging
                    field_ids = tb.getcol("FIELD_ID")
                    per_field = {}
                    unique_fields = np.unique(field_ids)
                    for field_id in unique_fields:
                        field_mask = field_ids == field_id
                        if np.any(field_mask):
                            field_flags = flags[field_mask]
                            field_frac = (
                                float(np.sum(field_flags) / field_flags.size)
                                if field_flags.size > 0
                                else 0.0
                            )
                            per_field[str(int(field_id))] = field_frac

                    metadata.flagging_stats = FlaggingStats(
                        total_fraction=flag_fraction,
                        per_antenna=per_antenna if per_antenna else None,
                        per_field=per_field if per_field else None,
                    )
            except Exception as e:
                logger.warning(f"Could not extract flagging stats: {e}")

            tb.close()

            # Get field info with coordinates
            tb.open(f"{ms_full_path}/FIELD", nomodify=True)
            field_names = tb.getcol("NAME").tolist()
            phase_dir = tb.getcol("PHASE_DIR")

            fields = []
            for i, name in enumerate(field_names):
                # Extract RA/Dec from PHASE_DIR (handles various shapes)
                pd = np.asarray(phase_dir[i])
                if pd.ndim == 3 and pd.shape[-1] == 2:
                    ra_rad = float(pd[0, 0, 0])
                    dec_rad = float(pd[0, 0, 1])
                elif pd.ndim == 2 and pd.shape[-1] == 2:
                    ra_rad = float(pd[0, 0])
                    dec_rad = float(pd[0, 1])
                elif pd.ndim == 1 and pd.shape[0] == 2:
                    ra_rad = float(pd[0])
                    dec_rad = float(pd[1])
                else:
                    ra_rad = float(pd.ravel()[-2])
                    dec_rad = float(pd.ravel()[-1])

                # Convert radians to degrees
                ra_deg = np.degrees(ra_rad)
                dec_deg = np.degrees(dec_rad)

                fields.append(
                    FieldInfo(
                        field_id=i, name=str(name), ra_deg=ra_deg, dec_deg=dec_deg
                    )
                )

            metadata.num_fields = len(field_names)
            metadata.field_names = field_names
            metadata.fields = fields
            tb.close()

            # Get spectral window info
            tb.open(f"{ms_full_path}/SPECTRAL_WINDOW", nomodify=True)
            chan_freqs = tb.getcol("CHAN_FREQ")
            if len(chan_freqs) > 0:
                metadata.freq_min_ghz = float(chan_freqs.min() / 1e9)
                metadata.freq_max_ghz = float(chan_freqs.max() / 1e9)
                metadata.num_channels = int(chan_freqs.shape[0])
            tb.close()

            # Get antenna info with names
            tb.open(f"{ms_full_path}/ANTENNA", nomodify=True)
            antenna_names = tb.getcol("NAME").tolist()
            antennas = []
            for i, name in enumerate(antenna_names):
                antennas.append(AntennaInfo(antenna_id=i, name=str(name)))
            metadata.num_antennas = len(antennas)
            metadata.antennas = antennas
            tb.close()

            # Get size
            size_bytes = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(ms_full_path)
                for filename in filenames
            )
            metadata.size_gb = round(size_bytes / (1024**3), 2)

        except Exception as e:
            logger.error(f"Error extracting MS metadata: {e}")
            # Return partial metadata if some operations fail
            pass

        return metadata

    @router.get(
        "/ms/{ms_path:path}/calibrator-matches", response_model=MSCalibratorMatchList
    )
    def get_ms_calibrator_matches(
        ms_path: str, catalog: str = "vla", radius_deg: float = 1.5, top_n: int = 5
    ) -> MSCalibratorMatchList:
        """Find calibrator candidates for an MS."""
        import astropy.units as u
        import numpy as np
        from astropy.time import Time
        from casatools import table

        from dsa110_contimg.calibration.catalogs import (
            airy_primary_beam_response,
            calibrator_match,
            read_vla_parsed_catalog_csv,
        )
        from dsa110_contimg.pointing.utils import load_pointing

        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith("/") else ms_path

        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")

        try:
            # Get pointing declination
            pointing_info = load_pointing(ms_full_path)
            pt_dec = pointing_info["dec_deg"] * u.deg

            # Get mid MJD from MS using standardized utility function
            # This handles both TIME formats (seconds since MJD 0 vs MJD 51544.0)
            from dsa110_contimg.utils.time_utils import extract_ms_time_range

            start_mjd, end_mjd, mid_mjd = extract_ms_time_range(ms_full_path)

            if mid_mjd is None:
                raise HTTPException(status_code=400, detail="MS has no valid time data")

            # Load catalog
            if catalog == "vla":
                from dsa110_contimg.calibration.catalogs import load_vla_catalog

                try:
                    df = load_vla_catalog()
                except FileNotFoundError as e:
                    raise HTTPException(
                        status_code=500, detail=f"VLA catalog not found: {e}"
                    )
            else:
                raise HTTPException(status_code=400, detail="Unknown catalog")

            # Get top matches
            matches_raw = calibrator_match(
                df, pt_dec, mid_mjd, radius_deg=radius_deg, freq_ghz=1.4, top_n=top_n
            )

            # Determine PB response reference point
            # For phased MS files, if a calibrator is found, assume MS is phased to it
            # Otherwise use telescope pointing (meridian)
            use_calibrator_as_phase_center = False
            phase_center_ra_deg = None
            phase_center_dec_deg = None

            # Check if MS filename suggests it's phased (heuristic)
            ms_basename = os.path.basename(ms_full_path).lower()
            ms_dirname = os.path.basename(os.path.dirname(ms_full_path)).lower()
            is_phased_ms = "phased" in ms_basename

            # If MS appears phased and we have matches, check if calibrator name matches directory
            # or if calibrator is reasonably close (< 0.2 deg for phased MS)
            if is_phased_ms and matches_raw:
                best_match = matches_raw[0]  # Already sorted by weighted_flux
                calibrator_name = best_match["name"].lower()
                # Check if calibrator name appears in directory name (e.g., "0834_transit" contains "0834")
                # Clean calibrator name: remove + and -, split by spaces
                calibrator_clean = calibrator_name.replace("+", "").replace("-", "")
                # Extract numeric part (e.g., "0834" from "0834555")
                calibrator_parts = [p for p in calibrator_clean.split() if len(p) >= 4]
                if not calibrator_parts:
                    # Try to extract first 4 digits
                    import re

                    digits = re.findall(r"\d{4,}", calibrator_clean)
                    # Use first 4+ digit sequence
                    calibrator_parts = digits[:1]
                name_in_dir = any(part in ms_dirname for part in calibrator_parts)

                # For phased MS, use calibrator coordinates if:
                # 1. Calibrator name matches directory, OR
                # 2. Separation is small (< 0.2 deg = 12 arcmin)
                if name_in_dir or best_match.get("sep_deg", 999) < 0.2:
                    use_calibrator_as_phase_center = True
                    phase_center_ra_deg = best_match["ra_deg"]
                    phase_center_dec_deg = best_match["dec_deg"]

            # Convert to MSCalibratorMatch with quality assessment
            matches = []
            for m in matches_raw:
                # Get flux from catalog - use flux_jy column (already in Jy)
                flux_jy = df.loc[m["name"], "flux_jy"] if m["name"] in df.index else 0.0

                # Compute PB response
                # For phased MS files phased to a calibrator, use calibrator coordinates
                # Otherwise use telescope pointing (meridian)
                if use_calibrator_as_phase_center and phase_center_ra_deg is not None:
                    # Use calibrator coordinates (MS is phased to this calibrator)
                    pb_response = airy_primary_beam_response(
                        np.deg2rad(phase_center_ra_deg),
                        np.deg2rad(phase_center_dec_deg),
                        np.deg2rad(m["ra_deg"]),
                        np.deg2rad(m["dec_deg"]),
                        1.4,
                    )
                else:
                    # Use telescope pointing (meridian) for unphased MS files
                    from astropy.coordinates import Angle

                    t = Time(mid_mjd, format="mjd", scale="utc")
                    from dsa110_contimg.utils.constants import DSA110_LOCATION

                    t.location = DSA110_LOCATION
                    ra_meridian = t.sidereal_time("apparent").to_value(u.deg)
                    dec_meridian = float(pt_dec.to_value(u.deg))

                    pb_response = airy_primary_beam_response(
                        np.deg2rad(ra_meridian),
                        np.deg2rad(dec_meridian),
                        np.deg2rad(m["ra_deg"]),
                        np.deg2rad(m["dec_deg"]),
                        1.4,
                    )

                # Determine quality
                if pb_response >= 0.8:
                    quality = "excellent"
                elif pb_response >= 0.5:
                    quality = "good"
                elif pb_response >= 0.3:
                    quality = "marginal"
                else:
                    quality = "poor"

                matches.append(
                    MSCalibratorMatch(
                        name=m["name"],
                        ra_deg=m["ra_deg"],
                        dec_deg=m["dec_deg"],
                        flux_jy=float(flux_jy),
                        sep_deg=m["sep_deg"],
                        pb_response=float(pb_response),
                        weighted_flux=m.get("weighted_flux", 0.0),
                        quality=quality,
                        recommended_fields=None,  # Could add field detection here
                    )
                )

            has_calibrator = len(matches) > 0 and matches[0].pb_response > 0.3

            return MSCalibratorMatchList(
                ms_path=ms_full_path,
                pointing_dec=float(pt_dec.to_value(u.deg)),
                mid_mjd=float(mid_mjd),
                matches=matches,
                has_calibrator=has_calibrator,
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error finding calibrators: {str(e)}"
            )

    @router.get(
        "/ms/{ms_path:path}/existing-caltables", response_model=ExistingCalTables
    )
    def get_existing_caltables(ms_path: str) -> ExistingCalTables:
        """Discover existing calibration tables for an MS."""
        import glob
        import time

        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith("/") else ms_path

        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")

        # Get MS directory and base name
        ms_dir = os.path.dirname(ms_full_path)
        ms_base = os.path.basename(ms_full_path).replace(".ms", "")

        # Search patterns for cal tables
        k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
        bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
        # Matches gpcal and gacal
        g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")

        def make_table_info(path: str) -> ExistingCalTable:
            """Create ExistingCalTable from path."""
            stat = os.stat(path)
            size_mb = stat.st_size / (1024 * 1024)
            modified_time = datetime.fromtimestamp(stat.st_mtime)
            age_hours = (time.time() - stat.st_mtime) / 3600.0
            return ExistingCalTable(
                path=path,
                filename=os.path.basename(path),
                size_mb=round(size_mb, 2),
                modified_time=modified_time,
                age_hours=round(age_hours, 2),
            )

        # Find tables
        k_tables = [
            make_table_info(p) for p in glob.glob(k_pattern) if os.path.isdir(p)
        ]
        bp_tables = [
            make_table_info(p) for p in glob.glob(bp_pattern) if os.path.isdir(p)
        ]
        g_tables = [
            make_table_info(p) for p in glob.glob(g_pattern) if os.path.isdir(p)
        ]

        # Sort by modified time (newest first)
        k_tables.sort(key=lambda t: t.modified_time, reverse=True)
        bp_tables.sort(key=lambda t: t.modified_time, reverse=True)
        g_tables.sort(key=lambda t: t.modified_time, reverse=True)

        return ExistingCalTables(
            ms_path=ms_full_path,
            k_tables=k_tables,
            bp_tables=bp_tables,
            g_tables=g_tables,
            has_k=len(k_tables) > 0,
            has_bp=len(bp_tables) > 0,
            has_g=len(g_tables) > 0,
        )

    @router.post(
        "/ms/{ms_path:path}/validate-caltable", response_model=CalTableCompatibility
    )
    def validate_caltable_compatibility(
        ms_path: str, caltable_path: str = Body(..., embed=True)
    ) -> CalTableCompatibility:
        """Validate that a calibration table is compatible with an MS file.

        Checks:
        - Antennas match
        - Frequency ranges overlap
        - Table structure is valid
        """
        import numpy as np
        from casatools import table

        # Decode paths
        ms_full_path = f"/{ms_path}" if not ms_path.startswith("/") else ms_path
        cal_full_path = (
            f"/{caltable_path}" if not caltable_path.startswith("/") else caltable_path
        )

        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")
        if not os.path.exists(cal_full_path):
            raise HTTPException(status_code=404, detail="Calibration table not found")

        issues = []
        warnings = []
        is_compatible = True

        ms_antennas = []
        caltable_antennas = []
        ms_freq_min_ghz = None
        ms_freq_max_ghz = None
        caltable_freq_min_ghz = None
        caltable_freq_max_ghz = None

        try:
            # Get MS antennas
            tb = table()
            tb.open(f"{ms_full_path}/ANTENNA", nomodify=True)
            ms_antennas = list(range(tb.nrows()))
            tb.close()

            # Get MS frequency range
            tb.open(f"{ms_full_path}/SPECTRAL_WINDOW", nomodify=True)
            chan_freqs = tb.getcol("CHAN_FREQ")
            if len(chan_freqs) > 0:
                ms_freq_min_ghz = float(chan_freqs.min() / 1e9)
                ms_freq_max_ghz = float(chan_freqs.max() / 1e9)
            tb.close()

            # Get calibration table antennas and frequencies
            tb.open(cal_full_path, nomodify=True)
            if tb.nrows() == 0:
                issues.append("Calibration table has no solutions")
                is_compatible = False
            else:
                # Get antennas from cal table
                if "ANTENNA1" in tb.colnames():
                    cal_ant1 = tb.getcol("ANTENNA1")
                    caltable_antennas = sorted(list(set(cal_ant1.tolist())))

                # Get spectral window from cal table
                if "SPECTRAL_WINDOW_ID" in tb.colnames():
                    spw_ids = tb.getcol("SPECTRAL_WINDOW_ID")
                    unique_spws = np.unique(spw_ids)

                    # Try to get frequency info from cal table's SPECTRAL_WINDOW subtable
                    try:
                        tb_spw = table()
                        tb_spw.open(f"{cal_full_path}/SPECTRAL_WINDOW", nomodify=True)
                        if tb_spw.nrows() > 0:
                            cal_chan_freqs = tb_spw.getcol("CHAN_FREQ")
                            if len(cal_chan_freqs) > 0:
                                caltable_freq_min_ghz = float(
                                    cal_chan_freqs.min() / 1e9
                                )
                                caltable_freq_max_ghz = float(
                                    cal_chan_freqs.max() / 1e9
                                )
                        tb_spw.close()
                    except Exception:
                        warnings.append(
                            "Could not extract frequency range from calibration table"
                        )
            tb.close()

            # Validate antenna compatibility
            if caltable_antennas:
                missing_ants = set(caltable_antennas) - set(ms_antennas)
                if missing_ants:
                    issues.append(
                        f"Calibration table contains antennas not in MS: {sorted(missing_ants)}"
                    )
                    is_compatible = False

                extra_ants = set(ms_antennas) - set(caltable_antennas)
                if extra_ants:
                    warnings.append(
                        f"MS contains antennas not in calibration table: {sorted(extra_ants)}"
                    )

            # Validate frequency compatibility
            if (
                ms_freq_min_ghz
                and ms_freq_max_ghz
                and caltable_freq_min_ghz
                and caltable_freq_max_ghz
            ):
                # Check if frequency ranges overlap
                freq_overlap = not (
                    ms_freq_max_ghz < caltable_freq_min_ghz
                    or caltable_freq_max_ghz < ms_freq_min_ghz
                )
                if not freq_overlap:
                    issues.append(
                        f"Frequency ranges do not overlap: "
                        f"MS={ms_freq_min_ghz:.3f}-{ms_freq_max_ghz:.3f} GHz, "
                        f"Cal={caltable_freq_min_ghz:.3f}-{caltable_freq_max_ghz:.3f} GHz"
                    )
                    is_compatible = False
                else:
                    # Check if ranges are significantly different
                    ms_range = ms_freq_max_ghz - ms_freq_min_ghz
                    cal_range = caltable_freq_max_ghz - caltable_freq_min_ghz
                    if abs(ms_range - cal_range) / max(ms_range, cal_range) > 0.2:
                        warnings.append(
                            "Frequency ranges have different widths (may indicate different observations)"
                        )

        except Exception as e:
            logger.error(f"Error validating calibration table compatibility: {e}")
            issues.append(f"Validation error: {e}")
            is_compatible = False

        return CalTableCompatibility(
            is_compatible=is_compatible,
            caltable_path=caltable_path,
            ms_path=ms_path,
            issues=issues,
            warnings=warnings,
            ms_antennas=ms_antennas,
            caltable_antennas=caltable_antennas,
            ms_freq_min_ghz=ms_freq_min_ghz,
            ms_freq_max_ghz=ms_freq_max_ghz,
            caltable_freq_min_ghz=caltable_freq_min_ghz,
            caltable_freq_max_ghz=caltable_freq_max_ghz,
        )

    @router.get("/qa/calibration/{ms_path:path}/bandpass-plots")
    def list_bandpass_plots(ms_path: str):
        """List available bandpass plots for an MS."""
        import glob
        import urllib.parse

        from dsa110_contimg.calibration.caltables import discover_caltables

        # FastAPI automatically URL-decodes path parameters, but we need to handle
        # cases where the path might not start with / and ensure proper decoding
        # Handle URL-encoded colons and other special characters
        decoded_path = urllib.parse.unquote(ms_path)
        ms_full_path = (
            f"/{decoded_path}" if not decoded_path.startswith("/") else decoded_path
        )

        # Log for debugging
        logger.debug(
            f"Bandpass plots request - received: {ms_path}, decoded: {decoded_path}, full: {ms_full_path}"
        )

        if not os.path.exists(ms_full_path):
            logger.warning(
                f"MS not found at path: {ms_full_path} (received: {ms_path}, decoded: {decoded_path})"
            )
            # Try alternative path constructions
            alt_paths = [
                ms_full_path,
                decoded_path,
                f"/{decoded_path}",
                ms_path if ms_path.startswith("/") else f"/{ms_path}",
            ]
            logger.debug(f"Tried paths: {alt_paths}")
            for alt in alt_paths:
                if os.path.exists(alt):
                    logger.info(f"Found MS at alternative path: {alt}")
                    ms_full_path = alt
                    break
            else:
                # Return detailed error with all attempted paths for debugging
                error_detail = (
                    f"MS not found. Received: '{ms_path}', "
                    f"Decoded: '{decoded_path}', "
                    f"Full path: '{ms_full_path}'. "
                    f"Tried: {alt_paths}"
                )
                logger.error(error_detail)
                raise HTTPException(status_code=404, detail=error_detail)

        # Find bandpass table
        caltables = discover_caltables(ms_full_path)
        if "bp" not in caltables or not caltables["bp"]:
            return {"plots": [], "message": "No bandpass calibration table found"}

        # Determine plot directory
        ms_dir = os.path.dirname(ms_full_path)
        plot_dir = os.path.join(ms_dir, "calibration_plots", "bandpass")

        if not os.path.exists(plot_dir):
            return {"plots": [], "message": "No bandpass plots directory found"}

        # Find all plot files
        bp_table_name = os.path.basename(caltables["bp"].rstrip("/"))
        plot_pattern = os.path.join(plot_dir, f"{bp_table_name}_plot_*.png")
        plot_files = sorted(glob.glob(plot_pattern))

        # Organize by type and SPW
        plots = []
        for plot_file in plot_files:
            filename = os.path.basename(plot_file)
            # Parse filename: {table}_plot_{type}.spw{XX}.t{YY}.png
            if "_plot_amp." in filename:
                plot_type = "amplitude"
            elif "_plot_phase." in filename:
                plot_type = "phase"
            else:
                plot_type = "unknown"

            # Extract SPW number
            spw_match = None
            if ".spw" in filename:
                try:
                    spw_part = filename.split(".spw")[1].split(".")[0]
                    spw_match = int(spw_part)
                except (ValueError, IndexError):
                    pass

            plots.append(
                {
                    "filename": filename,
                    "path": plot_file,
                    "type": plot_type,
                    "spw": spw_match,
                    "url": f"/api/qa/calibration/{ms_path}/bandpass-plots/{os.path.basename(plot_file)}",
                }
            )

        return {
            "ms_path": ms_full_path,
            "plot_dir": plot_dir,
            "plots": plots,
            "count": len(plots),
        }

    @router.get("/qa/calibration/{ms_path:path}/bandpass-plots/{filename}")
    def get_bandpass_plot(ms_path: str, filename: str):
        """Serve a specific bandpass plot file."""
        import urllib.parse

        # FastAPI automatically URL-decodes path parameters, but we need to handle
        # cases where the path might not start with / and ensure proper decoding
        decoded_path = urllib.parse.unquote(ms_path)
        ms_full_path = (
            f"/{decoded_path}" if not decoded_path.startswith("/") else decoded_path
        )

        if not os.path.exists(ms_full_path):
            # Try alternative path constructions
            alt_paths = [
                ms_full_path,
                decoded_path,
                f"/{decoded_path}",
                ms_path if ms_path.startswith("/") else f"/{ms_path}",
            ]
            for alt in alt_paths:
                if os.path.exists(alt):
                    ms_full_path = alt
                    break
            else:
                raise HTTPException(
                    status_code=404, detail=f"MS not found: {ms_full_path}"
                )

        # Determine plot directory
        ms_dir = os.path.dirname(ms_full_path)
        plot_dir = os.path.join(ms_dir, "calibration_plots", "bandpass")
        plot_path = os.path.join(plot_dir, filename)

        if not os.path.exists(plot_path):
            raise HTTPException(status_code=404, detail="Plot file not found")

        # Security: ensure filename doesn't contain path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        from fastapi.responses import FileResponse

        return FileResponse(plot_path, media_type="image/png", filename=filename)

    @router.get("/qa/calibration/{ms_path:path}/spw-plot")
    def get_calibration_spw_plot(ms_path: str):
        """Generate and return per-SPW flagging visualization for an MS."""
        import tempfile

        from dsa110_contimg.qa.calibration_quality import (
            analyze_per_spw_flagging,
            plot_per_spw_flagging,
        )

        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith("/") else ms_path

        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")

        try:
            # Find the bandpass table for this MS
            from dsa110_contimg.calibration.caltables import discover_caltables

            caltables = discover_caltables(ms_full_path)

            if (
                "bp" not in caltables
                or not caltables["bp"]
                or not Path(caltables["bp"]).exists()
            ):
                raise HTTPException(
                    status_code=404,
                    detail="No bandpass calibration table found for this MS",
                )

            # Generate per-SPW statistics
            spw_stats = analyze_per_spw_flagging(caltables["bp"])

            if not spw_stats:
                raise HTTPException(
                    status_code=404,
                    detail="No SPW statistics found in calibration table",
                )

            # Generate plot in temporary file
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                plot_path = tmp.name

            try:
                plot_file = plot_per_spw_flagging(
                    spw_stats,
                    plot_path,
                    title=f"Bandpass Calibration - Per-SPW Flagging Analysis\n{os.path.basename(ms_full_path)}",
                )

                # Return the plot file
                from fastapi.responses import FileResponse

                return FileResponse(
                    plot_file,
                    media_type="image/png",
                    filename=f"spw_flagging_{os.path.basename(ms_full_path)}.png",
                )
            except Exception as e:
                # Clean up temp file on error
                if os.path.exists(plot_path):
                    try:
                        os.unlink(plot_path)
                    except Exception:
                        pass
                raise
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating per-SPW plot: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error generating per-SPW plot: {str(e)}"
            )

    @router.get("/qa/calibration/{ms_path:path}/caltable-completeness")
    async def get_caltable_completeness(ms_path: str):
        """
        Check calibration table completeness for an MS.

        Returns:
            Dict with:
            - expected_tables: List of expected table paths
            - existing_tables: List of existing table paths
            - missing_tables: List of missing table paths
            - completeness: Fraction of expected tables that exist
            - has_issues: bool (True if any tables missing)
        """
        from dsa110_contimg.qa.calibration_quality import check_caltable_completeness

        result = check_caltable_completeness(ms_path)
        return result

    @router.get("/qa/calibration/{ms_path:path}", response_model=CalibrationQA)
    def get_calibration_qa(ms_path: str) -> CalibrationQA:
        """Get calibration QA metrics for an MS."""
        import json

        from dsa110_contimg.database.products import ensure_products_db

        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith("/") else ms_path

        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            # Get latest calibration QA for this MS
            cursor = conn.execute(
                """
                SELECT id, ms_path, job_id, k_metrics, bp_metrics, g_metrics, 
                       overall_quality, flags_total, per_spw_stats, timestamp
                FROM calibration_qa
                WHERE ms_path = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (ms_full_path,),
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404, detail="No calibration QA found for this MS"
                )

            # Parse JSON metrics
            k_metrics = json.loads(row[3]) if row[3] else None
            bp_metrics = json.loads(row[4]) if row[4] else None
            g_metrics = json.loads(row[5]) if row[5] else None
            per_spw_stats_json = json.loads(row[8]) if row[8] else None

            # Convert per-SPW stats to Pydantic models
            per_spw_stats = None
            if per_spw_stats_json:
                from dsa110_contimg.api.models import PerSPWStats

                per_spw_stats = [PerSPWStats(**s) for s in per_spw_stats_json]

            return CalibrationQA(
                ms_path=row[1],
                job_id=row[2],
                k_metrics=k_metrics,
                bp_metrics=bp_metrics,
                g_metrics=g_metrics,
                overall_quality=row[6] or "unknown",
                flags_total=row[7],
                per_spw_stats=per_spw_stats,
                timestamp=datetime.fromtimestamp(row[9]),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching calibration QA: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching calibration QA: {str(e)}"
            )
        finally:
            conn.close()

    @router.get("/qa/images/{image_id}/catalog-overlay")
    async def get_catalog_overlay(
        image_id: str,
        catalog: str = "nvss",
        search_radius_arcsec: float = 60.0,
        min_flux_jy: Optional[float] = None,
    ):
        """
        Get catalog sources for overlay on an image.

        Args:
            image_id: Image ID (integer) or image path (string)
            catalog: Reference catalog ("nvss" or "vlass")
            search_radius_arcsec: Search radius in arcseconds (for catalog query)
            min_flux_jy: Minimum flux in Jy (optional)

        Returns:
            Dict with:
            - sources: List of catalog sources with pixel coordinates
            - image_info: Image metadata (center, size, pixel scale)
            - catalog_used: Which catalog was queried
        """
        from astropy.io import fits
        from astropy.wcs import WCS

        from dsa110_contimg.catalog.query import query_sources
        from dsa110_contimg.qa.catalog_validation import get_catalog_overlay_pixels

        # Resolve image ID to path (handles both integer IDs and string paths)
        try:
            # Try as integer first
            image_id_int = int(image_id)
            image_path = resolve_image_path(image_id_int)
        except ValueError:
            # Not an integer, treat as path
            image_path = resolve_image_path(image_id)

        # Get image metadata
        with fits.open(image_path) as hdul:
            header = hdul[0].header
            wcs = WCS(header)

            nx = header.get("NAXIS1", 0)
            ny = header.get("NAXIS2", 0)
            center_x = nx / 2
            center_y = ny / 2
            center_ra, center_dec = wcs.wcs_pix2world(center_x, center_y, 0)

            # Estimate field size
            cdelt1 = abs(header.get("CDELT1", 0.001))
            cdelt2 = abs(header.get("CDELT2", 0.001))
            width_deg = nx * cdelt1
            height_deg = ny * cdelt2
            radius_deg = max(width_deg, height_deg) / 2 + 0.01

        # Query catalog
        min_flux_mjy = min_flux_jy * 1000.0 if min_flux_jy else None
        catalog_sources = query_sources(
            catalog_type=catalog,
            ra_center=center_ra,
            dec_center=center_dec,
            radius_deg=radius_deg,
            min_flux_mjy=min_flux_mjy,
        )

        # Convert to pixel coordinates
        sources_pixels = get_catalog_overlay_pixels(image_path, catalog_sources)

        return {
            "sources": sources_pixels,
            "image_info": {
                "center_ra": float(center_ra),
                "center_dec": float(center_dec),
                "width_deg": float(width_deg),
                "height_deg": float(height_deg),
                "nx": int(nx),
                "ny": int(ny),
                "pixel_scale_arcsec": float(cdelt1 * 3600.0),
            },
            "catalog_used": catalog,
        }

    @router.get("/qa/images/{image_id}/catalog-validation")
    async def get_catalog_validation(
        image_id: str,
        catalog: str = "nvss",
        validation_type: str = "all",  # "astrometry", "flux_scale", "source_counts", "all"
    ):
        """
        Get catalog validation results for an image.

        Args:
            image_id: Image ID (integer) or image path (string)
            catalog: Reference catalog ("nvss" or "vlass")
            validation_type: Type of validation to return

        Returns:
            Dict with validation results
        """
        from dsa110_contimg.qa.catalog_validation import (
            validate_astrometry,
            validate_flux_scale,
            validate_source_counts,
        )

        # Resolve image ID to path (handles both integer IDs and string paths)
        try:
            # Try as integer first
            image_id_int = int(image_id)
            image_path = resolve_image_path(image_id_int)
        except ValueError:
            # Not an integer, treat as path
            image_path = resolve_image_path(image_id)

        results = {}

        if validation_type in ("all", "astrometry"):
            results["astrometry"] = validate_astrometry(image_path, catalog=catalog)

        if validation_type in ("all", "flux_scale"):
            results["flux_scale"] = validate_flux_scale(image_path, catalog=catalog)

        if validation_type in ("all", "source_counts"):
            results["source_counts"] = validate_source_counts(
                image_path, catalog=catalog
            )

        return results

    @router.post("/qa/images/{image_id}/catalog-validation/run")
    async def run_catalog_validation(
        image_id: str,
        catalog: str = "nvss",
        validation_types: List[str] = ["astrometry", "flux_scale", "source_counts"],
    ):
        """
        Run catalog validation for an image and return results.

        Args:
            image_id: Image ID (integer) or image path (string)
            catalog: Reference catalog ("nvss" or "vlass")
            validation_types: List of validation types to run

        Returns:
            Dict with validation results
        """
        from dsa110_contimg.qa.catalog_validation import (
            validate_astrometry,
            validate_flux_scale,
            validate_source_counts,
        )

        # Resolve image ID to path (handles both integer IDs and string paths)
        try:
            # Try as integer first
            image_id_int = int(image_id)
            image_path = resolve_image_path(image_id_int)
        except ValueError:
            # Not an integer, treat as path
            image_path = resolve_image_path(image_id)

        results = {}

        if "astrometry" in validation_types:
            results["astrometry"] = validate_astrometry(image_path, catalog=catalog)

        if "flux_scale" in validation_types:
            results["flux_scale"] = validate_flux_scale(image_path, catalog=catalog)

        if "source_counts" in validation_types:
            results["source_counts"] = validate_source_counts(
                image_path, catalog=catalog
            )

        # TODO: Store results in database for future retrieval

        return results

    @router.get("/qa/images/{image_id}/validation-report.html")
    async def get_validation_html_report(
        image_id: str,
        catalog: str = "nvss",
        validation_types: List[str] = Query(
            default=["astrometry", "flux_scale", "source_counts"],
            description="Validation types to include",
        ),
        save_to_file: bool = Query(
            default=False, description="Save HTML report to file in QA directory"
        ),
    ):
        """
        Generate and return HTML validation report for an image.

        Args:
            image_id: Image ID (integer) or image path (string)
            catalog: Reference catalog ("nvss" or "vlass")
            validation_types: List of validation types to include
            save_to_file: Whether to save HTML report to file

        Returns:
            HTMLResponse with validation report
        """
        import os

        from fastapi.responses import HTMLResponse

        from dsa110_contimg.qa.catalog_validation import run_full_validation
        from dsa110_contimg.qa.html_reports import (
            ValidationReport,
            generate_validation_report,
        )

        # Resolve image ID to path
        try:
            image_id_int = int(image_id)
            image_path = resolve_image_path(image_id_int)
        except ValueError:
            image_path = resolve_image_path(image_id)

        # Run validations
        astrometry_result, flux_scale_result, source_counts_result = (
            run_full_validation(
                image_path=image_path,
                catalog=catalog,
                validation_types=validation_types,
                generate_html=False,  # We'll generate HTML ourselves
            )
        )

        # Create validation report
        report = ValidationReport(
            image_path=image_path,
            image_name=os.path.basename(image_path),
            astrometry=astrometry_result,
            flux_scale=flux_scale_result,
            source_counts=source_counts_result,
            catalog_used=catalog,
        )

        # Determine output path if saving to file
        html_output_path = None
        if save_to_file:
            # Save to QA directory
            qa_dir = os.path.join(
                os.getenv("PIPELINE_STATE_DIR", "state"), "qa", "reports"
            )
            os.makedirs(qa_dir, exist_ok=True)
            image_basename = os.path.splitext(os.path.basename(image_path))[0]
            html_output_path = os.path.join(
                qa_dir, f"{image_basename}_validation_report.html"
            )

        # Generate HTML
        html_content = generate_html_report(report, output_path=html_output_path)

        return HTMLResponse(content=html_content, status_code=200)

    @router.post("/qa/images/{image_id}/validation-report/generate")
    async def generate_validation_html_report(
        image_id: str,
        catalog: str = "nvss",
        validation_types: List[str] = ["astrometry", "flux_scale", "source_counts"],
        output_path: Optional[str] = None,
    ):
        """
        Generate HTML validation report and save to file.

        Args:
            image_id: Image ID (integer) or image path (string)
            catalog: Reference catalog ("nvss" or "vlass")
            validation_types: List of validation types to include
            output_path: Optional custom output path. If None, saves to QA directory.

        Returns:
            Dict with report path and status
        """
        import os

        from dsa110_contimg.qa.catalog_validation import run_full_validation

        # Resolve image ID to path
        try:
            image_id_int = int(image_id)
            image_path = resolve_image_path(image_id_int)
        except ValueError:
            image_path = resolve_image_path(image_id)

        # Use default validation types if not provided
        if validation_types is None:
            validation_types = ["astrometry", "flux_scale", "source_counts"]

        # Determine output path
        if output_path is None:
            qa_dir = os.path.join(
                os.getenv("PIPELINE_STATE_DIR", "state"), "qa", "reports"
            )
            os.makedirs(qa_dir, exist_ok=True)
            image_basename = os.path.splitext(os.path.basename(image_path))[0]
            output_path = os.path.join(
                qa_dir, f"{image_basename}_validation_report.html"
            )

        # Run validations and generate HTML
        run_full_validation(
            image_path=image_path,
            catalog=catalog,
            validation_types=validation_types,
            generate_html=True,
            html_output_path=output_path,
        )

        return {
            "status": "success",
            "report_path": output_path,
            "image_path": image_path,
            "catalog": catalog,
            "validation_types": validation_types,
        }

    @router.get("/qa/image/{ms_path:path}", response_model=ImageQA)
    def get_image_qa(ms_path: str) -> ImageQA:
        """Get image QA metrics for an MS."""
        from dsa110_contimg.database.products import ensure_products_db

        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith("/") else ms_path

        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            # Get latest image QA for this MS
            cursor = conn.execute(
                """
                SELECT id, ms_path, job_id, image_path, rms_noise, peak_flux, dynamic_range,
                       beam_major, beam_minor, beam_pa, num_sources, thumbnail_path,
                       overall_quality, timestamp
                FROM image_qa
                WHERE ms_path = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (ms_full_path,),
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404, detail="No image QA found for this MS"
                )

            return ImageQA(
                ms_path=row[1],
                job_id=row[2],
                image_path=row[3],
                rms_noise=row[4],
                peak_flux=row[5],
                dynamic_range=row[6],
                beam_major=row[7],
                beam_minor=row[8],
                beam_pa=row[9],
                num_sources=row[10],
                thumbnail_path=row[11],
                overall_quality=row[12] or "unknown",
                timestamp=datetime.fromtimestamp(row[13]),
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching image QA: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching image QA: {str(e)}"
            )
        finally:
            conn.close()

    @router.get("/qa/{ms_path:path}", response_model=QAMetrics)
    def get_qa_metrics(ms_path: str) -> QAMetrics:
        """Get combined QA metrics (calibration + image) for an MS."""
        import json

        from dsa110_contimg.database.products import ensure_products_db

        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith("/") else ms_path

        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            # Get calibration QA
            cal_qa = None
            try:
                cursor = conn.execute(
                    """
                    SELECT id, ms_path, job_id, k_metrics, bp_metrics, g_metrics,
                           overall_quality, flags_total, timestamp
                    FROM calibration_qa
                    WHERE ms_path = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (ms_full_path,),
                )
                row = cursor.fetchone()
                if row:
                    k_metrics = json.loads(row[3]) if row[3] else None
                    bp_metrics = json.loads(row[4]) if row[4] else None
                    g_metrics = json.loads(row[5]) if row[5] else None
                    cal_qa = CalibrationQA(
                        ms_path=row[1],
                        job_id=row[2],
                        k_metrics=k_metrics,
                        bp_metrics=bp_metrics,
                        g_metrics=g_metrics,
                        overall_quality=row[6] or "unknown",
                        flags_total=row[7],
                        timestamp=datetime.fromtimestamp(row[8]),
                    )
            except Exception as e:
                logger.warning(f"Could not fetch calibration QA: {e}")

            # Get image QA
            img_qa = None
            try:
                cursor = conn.execute(
                    """
                    SELECT id, ms_path, job_id, image_path, rms_noise, peak_flux, dynamic_range,
                           beam_major, beam_minor, beam_pa, num_sources, thumbnail_path,
                           overall_quality, timestamp
                    FROM image_qa
                    WHERE ms_path = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (ms_full_path,),
                )
                row = cursor.fetchone()
                if row:
                    img_qa = ImageQA(
                        ms_path=row[1],
                        job_id=row[2],
                        image_path=row[3],
                        rms_noise=row[4],
                        peak_flux=row[5],
                        dynamic_range=row[6],
                        beam_major=row[7],
                        beam_minor=row[8],
                        beam_pa=row[9],
                        num_sources=row[10],
                        thumbnail_path=row[11],
                        overall_quality=row[12] or "unknown",
                        timestamp=datetime.fromtimestamp(row[13]),
                    )
            except Exception as e:
                logger.warning(f"Could not fetch image QA: {e}")

            return QAMetrics(
                ms_path=ms_full_path, calibration_qa=cal_qa, image_qa=img_qa
            )
        except Exception as e:
            logger.error(f"Error fetching QA metrics: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error fetching QA metrics: {str(e)}"
            )
        finally:
            conn.close()

    @router.get("/thumbnails/{ms_path:path}.png")
    def get_image_thumbnail(ms_path: str):
        """Serve image thumbnail for an MS."""
        from dsa110_contimg.database.products import ensure_products_db

        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith("/") else ms_path

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            # Get thumbnail path from image_qa
            cursor = conn.execute(
                """
                SELECT thumbnail_path FROM image_qa
                WHERE ms_path = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (ms_full_path,),
            )
            row = cursor.fetchone()

            if not row or not row[0]:
                raise HTTPException(
                    status_code=404, detail="No thumbnail found for this MS"
                )

            thumbnail_path = Path(row[0])
            if not thumbnail_path.exists():
                raise HTTPException(status_code=404, detail="Thumbnail file not found")

            return FileResponse(
                str(thumbnail_path),
                media_type="image/png",
                filename=f"{os.path.basename(ms_full_path)}.thumb.png",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error serving thumbnail: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error serving thumbnail: {str(e)}"
            )
        finally:
            conn.close()

    @router.get("/plots/caltable/{caltable_path:path}")
    def get_caltable_plot(
        caltable_path: str,
        plot_type: str = "amp_vs_freq",  # amp_vs_freq, phase_vs_time, phase_vs_freq
        antenna: int | None = None,
    ):
        """Generate and serve a calibration solution plot for a calibration table.

        Plot types:
        - amp_vs_freq: Amplitude vs frequency (for bandpass tables)
        - phase_vs_time: Phase vs time (for gain tables)
        - phase_vs_freq: Phase vs frequency (for bandpass tables)
        """
        import matplotlib
        import numpy as np
        from casatools import table

        matplotlib.use("Agg")
        from io import BytesIO

        import matplotlib.pyplot as plt

        # Decode path
        cal_full_path = (
            f"/{caltable_path}" if not caltable_path.startswith("/") else caltable_path
        )

        if not os.path.exists(cal_full_path):
            raise HTTPException(status_code=404, detail="Calibration table not found")

        try:
            tb = table()
            tb.open(cal_full_path, nomodify=True)

            if tb.nrows() == 0:
                raise HTTPException(
                    status_code=400, detail="Calibration table has no solutions"
                )

            # Get data columns
            antenna_ids = tb.getcol("ANTENNA1") if "ANTENNA1" in tb.colnames() else None
            spw_ids = (
                tb.getcol("SPECTRAL_WINDOW_ID")
                if "SPECTRAL_WINDOW_ID" in tb.colnames()
                else None
            )
            times = tb.getcol("TIME") if "TIME" in tb.colnames() else None
            gains = tb.getcol("CPARAM") if "CPARAM" in tb.colnames() else None
            flags = tb.getcol("FLAG") if "FLAG" in tb.colnames() else None

            if gains is None:
                raise HTTPException(
                    status_code=400,
                    detail="Calibration table does not contain CPARAM column",
                )

            # Convert to numpy arrays
            antenna_ids = np.asarray(antenna_ids) if antenna_ids is not None else None
            spw_ids = np.asarray(spw_ids) if spw_ids is not None else None
            times = np.asarray(times) if times is not None else None
            gains = np.asarray(gains)
            flags = (
                np.asarray(flags)
                if flags is not None
                else np.zeros(gains.shape, dtype=bool)
            )

            # Mask flagged values
            gains_masked = np.where(flags, np.nan + 0j, gains)

            # Filter by antenna if specified
            if antenna is not None and antenna_ids is not None:
                ant_mask = antenna_ids == antenna
                if not np.any(ant_mask):
                    raise HTTPException(
                        status_code=404,
                        detail=f"Antenna {antenna} not found in calibration table",
                    )
                gains_masked = gains_masked[ant_mask]
                if spw_ids is not None:
                    spw_ids = spw_ids[ant_mask]
                if times is not None:
                    times = times[ant_mask]

            # Generate plot based on type
            fig, ax = plt.subplots(figsize=(10, 6))

            if plot_type == "amp_vs_freq":
                # For bandpass: amplitude vs frequency
                if spw_ids is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot plot amplitude vs frequency: no SPW information",
                    )

                # Get frequencies from SPW subtable
                try:
                    tb_spw = table()
                    tb_spw.open(f"{cal_full_path}/SPECTRAL_WINDOW", nomodify=True)
                    chan_freqs = tb_spw.getcol("CHAN_FREQ")
                    tb_spw.close()

                    # Flatten gains and create frequency array
                    amplitudes = np.abs(gains_masked)
                    if amplitudes.ndim > 1:
                        # Average over polarization if needed
                        amplitudes = (
                            np.nanmean(amplitudes, axis=-1)
                            if amplitudes.ndim > 1
                            else amplitudes
                        )

                    # Create frequency array matching the data
                    unique_spws = np.unique(spw_ids)
                    freq_data = []
                    amp_data = []

                    for spw in unique_spws:
                        spw_mask = spw_ids == spw
                        if np.any(spw_mask):
                            # Convert to GHz
                            spw_freqs = chan_freqs[int(spw)] / 1e9
                            spw_amps = amplitudes[spw_mask]
                            if spw_amps.ndim > 1:
                                spw_amps = np.nanmean(spw_amps, axis=-1)
                            freq_data.extend(spw_freqs.tolist())
                            amp_data.extend(spw_amps.tolist())

                    ax.plot(freq_data, amp_data, "b-", alpha=0.7, linewidth=0.5)
                    ax.set_xlabel("Frequency (GHz)")
                    ax.set_ylabel("Amplitude")
                    ax.set_title(
                        f'Bandpass Amplitude vs Frequency{(" (Antenna " + str(antenna) + ")") if antenna is not None else ""}'
                    )
                    ax.grid(True, alpha=0.3)

                except Exception as e:
                    logger.error(f"Error plotting amplitude vs frequency: {e}")
                    raise HTTPException(
                        status_code=500, detail=f"Error generating plot: {e}"
                    )

            elif plot_type == "phase_vs_time":
                # For gain: phase vs time
                if times is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot plot phase vs time: no TIME column",
                    )

                phases = np.angle(gains_masked)
                if phases.ndim > 1:
                    phases = np.nanmean(phases, axis=-1)

                # Convert CASA time to hours since start
                time_hours = (times - times.min()) / 3600.0
                from dsa110_contimg.utils.angles import wrap_phase_deg

                phases_deg = wrap_phase_deg(np.degrees(phases))

                ax.plot(time_hours, phases_deg, "b-", alpha=0.7, linewidth=0.5)
                ax.set_xlabel("Time (hours since start)")
                ax.set_ylabel("Phase (degrees)")
                ax.set_title(
                    f'Gain Phase vs Time{(" (Antenna " + str(antenna) + ")") if antenna is not None else ""}'
                )
                ax.grid(True, alpha=0.3)

            elif plot_type == "phase_vs_freq":
                # For bandpass: phase vs frequency
                if spw_ids is None:
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot plot phase vs frequency: no SPW information",
                    )

                try:
                    tb_spw = table()
                    tb_spw.open(f"{cal_full_path}/SPECTRAL_WINDOW", nomodify=True)
                    chan_freqs = tb_spw.getcol("CHAN_FREQ")
                    tb_spw.close()

                    phases = np.angle(gains_masked)
                    if phases.ndim > 1:
                        phases = np.nanmean(phases, axis=-1)

                    unique_spws = np.unique(spw_ids)
                    freq_data = []
                    phase_data = []

                    for spw in unique_spws:
                        spw_mask = spw_ids == spw
                        if np.any(spw_mask):
                            # Convert to GHz
                            spw_freqs = chan_freqs[int(spw)] / 1e9
                            spw_phases = phases[spw_mask]
                            if spw_phases.ndim > 1:
                                spw_phases = np.nanmean(spw_phases, axis=-1)
                            from dsa110_contimg.utils.angles import wrap_phase_deg

                            freq_data.extend(spw_freqs.tolist())
                            phase_data.extend(
                                wrap_phase_deg(np.degrees(spw_phases)).tolist()
                            )

                    ax.plot(freq_data, phase_data, "b-", alpha=0.7, linewidth=0.5)
                    ax.set_xlabel("Frequency (GHz)")
                    ax.set_ylabel("Phase (degrees)")
                    ax.set_title(
                        f'Bandpass Phase vs Frequency{(" (Antenna " + str(antenna) + ")") if antenna is not None else ""}'
                    )
                    ax.grid(True, alpha=0.3)

                except Exception as e:
                    logger.error(f"Error plotting phase vs frequency: {e}")
                    raise HTTPException(
                        status_code=500, detail=f"Error generating plot: {e}"
                    )
            else:
                raise HTTPException(
                    status_code=400, detail=f"Unknown plot type: {plot_type}"
                )

            tb.close()

            # Save plot to BytesIO
            buf = BytesIO()
            plt.savefig(buf, format="png", dpi=100, bbox_inches="tight")
            plt.close(fig)
            buf.seek(0)

            return FileResponse(
                buf,
                media_type="image/png",
                filename=f"{os.path.basename(cal_full_path)}_{plot_type}.png",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error generating calibration plot: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error generating plot: {str(e)}"
            )
        finally:
            try:
                tb.close()
            except Exception:
                pass  # Ignore errors during cleanup

    @router.post("/jobs/workflow", response_model=Job)
    def create_workflow_job(
        request: WorkflowJobCreateRequest, background_tasks: BackgroundTasks
    ) -> Job:
        """Create and run a full pipeline workflow (Convert → Calibrate → Image)."""
        from dsa110_contimg.api.job_runner import run_workflow_job
        from dsa110_contimg.api.models import JobParams
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        # Create workflow job
        job_id = create_job(conn, "workflow", "", request.params.model_dump())
        conn.close()

        # Start workflow in background
        background_tasks.add_task(
            run_workflow_job, job_id, request.params.model_dump(), db_path
        )

        # Return initial job state
        conn = ensure_products_db(db_path)
        from dsa110_contimg.database.jobs import get_job as db_get_job

        jd = db_get_job(conn, job_id)
        conn.close()

        return Job(
            id=jd["id"],
            type=jd["type"],
            status=jd["status"],
            ms_path=jd["ms_path"],
            params=JobParams(**jd["params"]) if jd["params"] else JobParams(),
            logs=jd["logs"],
            artifacts=jd["artifacts"],
            created_at=datetime.fromtimestamp(jd["created_at"]),
            started_at=(
                datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None
            ),
            finished_at=(
                datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None
            ),
        )

    # Batch job endpoints
    @router.post("/batch/calibrate", response_model=BatchJob)
    def create_batch_calibrate_job(
        request: BatchJobCreateRequest, background_tasks: BackgroundTasks
    ) -> BatchJob:
        """Create a batch calibration job for multiple MS files."""
        from dsa110_contimg.api.batch_jobs import create_batch_job
        from dsa110_contimg.api.job_runner import run_batch_calibrate_job
        from dsa110_contimg.database.products import ensure_products_db

        if request.job_type != "calibrate":
            raise HTTPException(status_code=400, detail="Job type must be 'calibrate'")

        if not isinstance(request.params, BatchCalibrateParams):
            raise HTTPException(
                status_code=400, detail="Invalid params type for batch calibrate"
            )

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            batch_id = create_batch_job(
                conn,
                "batch_calibrate",
                request.params.ms_paths,
                request.params.params.model_dump(),
            )

            # Start batch processing in background
            background_tasks.add_task(
                run_batch_calibrate_job,
                batch_id,
                request.params.ms_paths,
                request.params.params.model_dump(),
                db_path,
            )

            # Get batch job details
            cursor = conn.execute(
                """
                SELECT id, type, created_at, status, total_items, completed_items, failed_items, params
                FROM batch_jobs WHERE id = ?
                """,
                (batch_id,),
            )
            row = cursor.fetchone()

            # Get batch items
            items_cursor = conn.execute(
                """
                SELECT ms_path, job_id, status, error, started_at, completed_at
                FROM batch_job_items WHERE batch_id = ?
                """,
                (batch_id,),
            )
            items = []
            for item_row in items_cursor.fetchall():
                items.append(
                    BatchJobStatus(
                        ms_path=item_row[0],
                        job_id=item_row[1],
                        status=item_row[2],
                        error=item_row[3],
                        started_at=(
                            datetime.fromtimestamp(item_row[4]) if item_row[4] else None
                        ),
                        completed_at=(
                            datetime.fromtimestamp(item_row[5]) if item_row[5] else None
                        ),
                    )
                )

            return BatchJob(
                id=row[0],
                type=row[1],
                created_at=datetime.fromtimestamp(row[2]),
                status=row[3],
                total_items=row[4],
                completed_items=row[5],
                failed_items=row[6],
                params=json.loads(row[7]) if row[7] else {},
                items=items,
            )
        finally:
            conn.close()

    @router.post("/batch/apply", response_model=BatchJob)
    def create_batch_apply_job(
        request: BatchJobCreateRequest, background_tasks: BackgroundTasks
    ) -> BatchJob:
        """Create a batch apply job for multiple MS files."""
        from dsa110_contimg.api.batch_jobs import create_batch_job
        from dsa110_contimg.api.job_runner import run_batch_apply_job
        from dsa110_contimg.database.products import ensure_products_db

        if request.job_type != "apply":
            raise HTTPException(status_code=400, detail="Job type must be 'apply'")

        if not isinstance(request.params, BatchApplyParams):
            raise HTTPException(
                status_code=400, detail="Invalid params type for batch apply"
            )

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            batch_id = create_batch_job(
                conn,
                "batch_apply",
                request.params.ms_paths,
                request.params.params.model_dump(),
            )

            background_tasks.add_task(
                run_batch_apply_job,
                batch_id,
                request.params.ms_paths,
                request.params.params.model_dump(),
                db_path,
            )

            # Get batch job details (same as calibrate)
            cursor = conn.execute(
                """
                SELECT id, type, created_at, status, total_items, completed_items, failed_items, params
                FROM batch_jobs WHERE id = ?
                """,
                (batch_id,),
            )
            row = cursor.fetchone()

            items_cursor = conn.execute(
                """
                SELECT ms_path, job_id, status, error, started_at, completed_at
                FROM batch_job_items WHERE batch_id = ?
                """,
                (batch_id,),
            )
            items = []
            for item_row in items_cursor.fetchall():
                items.append(
                    BatchJobStatus(
                        ms_path=item_row[0],
                        job_id=item_row[1],
                        status=item_row[2],
                        error=item_row[3],
                        started_at=(
                            datetime.fromtimestamp(item_row[4]) if item_row[4] else None
                        ),
                        completed_at=(
                            datetime.fromtimestamp(item_row[5]) if item_row[5] else None
                        ),
                    )
                )

            return BatchJob(
                id=row[0],
                type=row[1],
                created_at=datetime.fromtimestamp(row[2]),
                status=row[3],
                total_items=row[4],
                completed_items=row[5],
                failed_items=row[6],
                params=json.loads(row[7]) if row[7] else {},
                items=items,
            )
        finally:
            conn.close()

    @router.post("/batch/image", response_model=BatchJob)
    def create_batch_image_job(
        request: BatchJobCreateRequest, background_tasks: BackgroundTasks
    ) -> BatchJob:
        """Create a batch imaging job for multiple MS files."""
        from dsa110_contimg.api.batch_jobs import create_batch_job
        from dsa110_contimg.api.job_runner import run_batch_image_job
        from dsa110_contimg.database.products import ensure_products_db

        if request.job_type != "image":
            raise HTTPException(status_code=400, detail="Job type must be 'image'")

        if not isinstance(request.params, BatchImageParams):
            raise HTTPException(
                status_code=400, detail="Invalid params type for batch image"
            )

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            batch_id = create_batch_job(
                conn,
                "batch_image",
                request.params.ms_paths,
                request.params.params.model_dump(),
            )

            background_tasks.add_task(
                run_batch_image_job,
                batch_id,
                request.params.ms_paths,
                request.params.params.model_dump(),
                db_path,
            )

            # Get batch job details (same as calibrate)
            cursor = conn.execute(
                """
                SELECT id, type, created_at, status, total_items, completed_items, failed_items, params
                FROM batch_jobs WHERE id = ?
                """,
                (batch_id,),
            )
            row = cursor.fetchone()

            items_cursor = conn.execute(
                """
                SELECT ms_path, job_id, status, error, started_at, completed_at
                FROM batch_job_items WHERE batch_id = ?
                """,
                (batch_id,),
            )
            items = []
            for item_row in items_cursor.fetchall():
                items.append(
                    BatchJobStatus(
                        ms_path=item_row[0],
                        job_id=item_row[1],
                        status=item_row[2],
                        error=item_row[3],
                        started_at=(
                            datetime.fromtimestamp(item_row[4]) if item_row[4] else None
                        ),
                        completed_at=(
                            datetime.fromtimestamp(item_row[5]) if item_row[5] else None
                        ),
                    )
                )

            return BatchJob(
                id=row[0],
                type=row[1],
                created_at=datetime.fromtimestamp(row[2]),
                status=row[3],
                total_items=row[4],
                completed_items=row[5],
                failed_items=row[6],
                params=json.loads(row[7]) if row[7] else {},
                items=items,
            )
        finally:
            conn.close()

    @router.get("/batch", response_model=BatchJobList)
    def list_batch_jobs(limit: int = 50, status: str | None = None) -> BatchJobList:
        """List batch jobs with optional status filter."""
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            query = """
                SELECT id, type, created_at, status, total_items, completed_items, failed_items, params
                FROM batch_jobs
            """
            params: list[object] = []

            if status:
                query += " WHERE status = ?"
                params.append(status)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            batches = []

            for row in cursor.fetchall():
                batch_id = row[0]

                # Get items for this batch
                items_cursor = conn.execute(
                    """
                    SELECT ms_path, job_id, status, error, started_at, completed_at
                    FROM batch_job_items WHERE batch_id = ?
                    """,
                    (batch_id,),
                )
                items = []
                for item_row in items_cursor.fetchall():
                    items.append(
                        BatchJobStatus(
                            ms_path=item_row[0],
                            job_id=item_row[1],
                            status=item_row[2],
                            error=item_row[3],
                            started_at=(
                                datetime.fromtimestamp(item_row[4])
                                if item_row[4]
                                else None
                            ),
                            completed_at=(
                                datetime.fromtimestamp(item_row[5])
                                if item_row[5]
                                else None
                            ),
                        )
                    )

                batches.append(
                    BatchJob(
                        id=row[0],
                        type=row[1],
                        created_at=datetime.fromtimestamp(row[2]),
                        status=row[3],
                        total_items=row[4],
                        completed_items=row[5],
                        failed_items=row[6],
                        params=json.loads(row[7]) if row[7] else {},
                        items=items,
                    )
                )

            return BatchJobList(items=batches)
        finally:
            conn.close()

    @router.get("/batch/{batch_id}", response_model=BatchJob)
    def get_batch_job(batch_id: int) -> BatchJob:
        """Get batch job details by ID."""
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            cursor = conn.execute(
                """
                SELECT id, type, created_at, status, total_items, completed_items, failed_items, params
                FROM batch_jobs WHERE id = ?
                """,
                (batch_id,),
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Batch job not found")

            # Get items
            items_cursor = conn.execute(
                """
                SELECT ms_path, job_id, status, error, started_at, completed_at
                FROM batch_job_items WHERE batch_id = ?
                ORDER BY id
                """,
                (batch_id,),
            )
            items = []
            for item_row in items_cursor.fetchall():
                items.append(
                    BatchJobStatus(
                        ms_path=item_row[0],
                        job_id=item_row[1],
                        status=item_row[2],
                        error=item_row[3],
                        started_at=(
                            datetime.fromtimestamp(item_row[4]) if item_row[4] else None
                        ),
                        completed_at=(
                            datetime.fromtimestamp(item_row[5]) if item_row[5] else None
                        ),
                    )
                )

            return BatchJob(
                id=row[0],
                type=row[1],
                created_at=datetime.fromtimestamp(row[2]),
                status=row[3],
                total_items=row[4],
                completed_items=row[5],
                failed_items=row[6],
                params=json.loads(row[7]) if row[7] else {},
                items=items,
            )
        finally:
            conn.close()

    @router.post("/batch/{batch_id}/cancel")
    def cancel_batch_job(batch_id: int):
        """Cancel a running batch job."""
        from dsa110_contimg.database.products import ensure_products_db

        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)

        try:
            # Check if batch exists
            cursor = conn.execute(
                "SELECT status FROM batch_jobs WHERE id = ?", (batch_id,)
            )
            row = cursor.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="Batch job not found")

            if row[0] not in ("pending", "running"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot cancel batch job in status: {row[0]}",
                )

            # Update batch status to cancelled
            conn.execute(
                "UPDATE batch_jobs SET status = 'cancelled' WHERE id = ?", (batch_id,)
            )

            # Update pending/running items to cancelled
            conn.execute(
                """
                UPDATE batch_job_items
                SET status = 'cancelled'
                WHERE batch_id = ? AND status IN ('pending', 'running')
                """,
                (batch_id,),
            )

            conn.commit()

            return {"message": f"Batch job {batch_id} cancelled", "batch_id": batch_id}
        finally:
            conn.close()

    # Streaming Service Control Endpoints
    _streaming_manager = StreamingServiceManager()

    @router.get("/streaming/status", response_model=StreamingStatusResponse)
    def get_streaming_status(
        test_mode: str | None = Query(default=None),
        test_delay: int | None = Query(default=None),
        test_error: int | None = Query(default=None),
    ) -> StreamingStatusResponse:
        """Get current status of the streaming service.

        Test mode parameters (dev only):
        - test_mode: 'delay' or 'error'
        - test_delay: Delay in milliseconds (for loading state testing)
        - test_error: HTTP error code to return (for error handling testing)
        """
        # Test mode support (dev only)
        import os

        if os.getenv("ENVIRONMENT") != "production" and test_mode:
            if test_mode == "delay" and test_delay:
                import time

                time.sleep(test_delay / 1000.0)  # Convert ms to seconds
            elif test_mode == "error" and test_error:
                from fastapi import HTTPException

                raise HTTPException(
                    status_code=test_error, detail="Test error simulation"
                )

        status = _streaming_manager.get_status()
        return StreamingStatusResponse(**status.to_dict())

    @router.get("/streaming/health", response_model=StreamingHealthResponse)
    def get_streaming_health() -> StreamingHealthResponse:
        """Get health check information for the streaming service."""
        health = _streaming_manager.get_health()
        return StreamingHealthResponse(**health)

    @router.get("/pointing-monitor/status")
    def get_pointing_monitor_status() -> dict:
        """Get status of the pointing monitor service.

        Reads status from the JSON file written by the pointing monitor.
        Returns status information including health, metrics, and issues.
        """
        state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "/data/dsa110-contimg/state"))
        status_file = state_dir / "pointing-monitor-status.json"

        if not status_file.exists():
            return {
                "running": False,
                "healthy": False,
                "error": "Status file not found - monitor may not be running",
                "status_file": str(status_file),
            }

        try:
            with open(status_file, "r") as f:
                status = json.load(f)

            # Add age of status file
            file_age = time.time() - status_file.stat().st_mtime
            status["status_file_age_seconds"] = round(file_age, 1)

            # Consider stale if older than 2 minutes (monitor writes every 30s)
            if file_age > 120:
                status["stale"] = True
                status["healthy"] = False
                if "issues" not in status:
                    status["issues"] = []
                status["issues"].append(f"Status file is stale (age: {file_age:.0f}s)")
            else:
                status["stale"] = False

            return status
        except json.JSONDecodeError as e:
            return {
                "running": False,
                "healthy": False,
                "error": f"Failed to parse status file: {e}",
                "status_file": str(status_file),
            }
        except Exception as e:
            return {
                "running": False,
                "healthy": False,
                "error": f"Failed to read status file: {e}",
                "status_file": str(status_file),
            }

    @router.get("/streaming/config", response_model=StreamingConfigRequest)
    def get_streaming_config() -> StreamingConfigRequest:
        """Get current streaming service configuration."""
        status = _streaming_manager.get_status()
        if status.config:
            return StreamingConfigRequest(**status.config.to_dict())
        else:
            # Return defaults
            return StreamingConfigRequest(
                input_dir=os.getenv("CONTIMG_INPUT_DIR", "/data/incoming"),
                output_dir=os.getenv("CONTIMG_OUTPUT_DIR", "/stage/dsa110-contimg/ms"),
                queue_db=os.getenv("CONTIMG_QUEUE_DB", "state/ingest.sqlite3"),
                registry_db=os.getenv(
                    "CONTIMG_REGISTRY_DB", "state/cal_registry.sqlite3"
                ),
                scratch_dir=os.getenv("CONTIMG_SCRATCH_DIR", "/stage/dsa110-contimg"),
            )

    @router.post("/streaming/config", response_model=StreamingControlResponse)
    def update_streaming_config(
        request: StreamingConfigRequest,
        test_validation_error: bool | None = Query(default=None),
    ) -> StreamingControlResponse:
        """Update streaming service configuration.

        Test mode parameters (dev only):
        - test_validation_error: If True, return validation error (for validation testing)
        """
        # Test mode support (dev only)
        import os

        if os.getenv("ENVIRONMENT") != "production" and test_validation_error:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=422,
                detail={
                    "errors": [
                        {
                            "field": "input_dir",
                            "message": "Input directory is required",
                        },
                        {
                            "field": "max_workers",
                            "message": "Max workers must be between 1 and 32",
                        },
                    ]
                },
            )
        config = StreamingConfig(
            input_dir=request.input_dir,
            output_dir=request.output_dir,
            queue_db=request.queue_db
            or os.getenv("CONTIMG_QUEUE_DB", "state/ingest.sqlite3"),
            registry_db=request.registry_db
            or os.getenv("CONTIMG_REGISTRY_DB", "state/cal_registry.sqlite3"),
            scratch_dir=request.scratch_dir
            or os.getenv("CONTIMG_SCRATCH_DIR", "/stage/dsa110-contimg"),
            expected_subbands=request.expected_subbands,
            chunk_duration=request.chunk_duration,
            log_level=request.log_level,
            use_subprocess=request.use_subprocess,
            monitoring=request.monitoring,
            monitor_interval=request.monitor_interval,
            poll_interval=request.poll_interval,
            worker_poll_interval=request.worker_poll_interval,
            max_workers=request.max_workers,
            stage_to_tmpfs=request.stage_to_tmpfs,
            tmpfs_path=request.tmpfs_path,
        )
        result = _streaming_manager.update_config(config)
        return StreamingControlResponse(**result)

    @router.post("/streaming/start", response_model=StreamingControlResponse)
    def start_streaming_service(
        request: Optional[StreamingConfigRequest] = None,
        test_delay: int | None = Query(default=None),
    ) -> StreamingControlResponse:
        """Start the streaming service.

        Test mode parameters (dev only):
        - test_delay: Delay in milliseconds before response (for loading state testing)
        """
        # Test mode support (dev only)
        import os

        if os.getenv("ENVIRONMENT") != "production" and test_delay:
            import time

            time.sleep(test_delay / 1000.0)  # Convert ms to seconds
        config = None
        if request:
            config = StreamingConfig(
                input_dir=request.input_dir,
                output_dir=request.output_dir,
                queue_db=request.queue_db
                or os.getenv("CONTIMG_QUEUE_DB", "state/ingest.sqlite3"),
                registry_db=request.registry_db
                or os.getenv("CONTIMG_REGISTRY_DB", "state/cal_registry.sqlite3"),
                scratch_dir=request.scratch_dir
                or os.getenv("CONTIMG_SCRATCH_DIR", "/stage/dsa110-contimg"),
                expected_subbands=request.expected_subbands,
                chunk_duration=request.chunk_duration,
                log_level=request.log_level,
                use_subprocess=request.use_subprocess,
                monitoring=request.monitoring,
                monitor_interval=request.monitor_interval,
                poll_interval=request.poll_interval,
                worker_poll_interval=request.worker_poll_interval,
                max_workers=request.max_workers,
                stage_to_tmpfs=request.stage_to_tmpfs,
                tmpfs_path=request.tmpfs_path,
            )
        result = _streaming_manager.start(config)
        return StreamingControlResponse(**result)

    @router.post("/streaming/stop", response_model=StreamingControlResponse)
    def stop_streaming_service() -> StreamingControlResponse:
        """Stop the streaming service."""
        result = _streaming_manager.stop()
        return StreamingControlResponse(**result)

    @router.post("/streaming/restart", response_model=StreamingControlResponse)
    def restart_streaming_service(
        request: Optional[StreamingConfigRequest] = None,
    ) -> StreamingControlResponse:
        """Restart the streaming service."""
        config = None
        if request:
            config = StreamingConfig(
                input_dir=request.input_dir,
                output_dir=request.output_dir,
                queue_db=request.queue_db
                or os.getenv("CONTIMG_QUEUE_DB", "state/ingest.sqlite3"),
                registry_db=request.registry_db
                or os.getenv("CONTIMG_REGISTRY_DB", "state/cal_registry.sqlite3"),
                scratch_dir=request.scratch_dir
                or os.getenv("CONTIMG_SCRATCH_DIR", "/stage/dsa110-contimg"),
                expected_subbands=request.expected_subbands,
                chunk_duration=request.chunk_duration,
                log_level=request.log_level,
                use_subprocess=request.use_subprocess,
                monitoring=request.monitoring,
                monitor_interval=request.monitor_interval,
                poll_interval=request.poll_interval,
                worker_poll_interval=request.worker_poll_interval,
                max_workers=request.max_workers,
                stage_to_tmpfs=request.stage_to_tmpfs,
                tmpfs_path=request.tmpfs_path,
            )
        result = _streaming_manager.restart(config)
        return StreamingControlResponse(**result)

    @router.get("/streaming/metrics")
    def get_streaming_metrics():
        """Get processing metrics for the streaming service."""
        import time

        from dsa110_contimg.api.config import ApiConfig
        from dsa110_contimg.api.data_access import _connect

        cfg = ApiConfig.from_env()
        status = _streaming_manager.get_status()

        metrics = {
            "service_running": status.running,
            "uptime_seconds": status.uptime_seconds,
            "cpu_percent": status.cpu_percent,
            "memory_mb": status.memory_mb,
        }

        # Get queue statistics
        if cfg.queue_db and Path(cfg.queue_db).exists():
            try:
                with _connect(Path(cfg.queue_db)) as conn:
                    # Count by state
                    queue_stats = conn.execute(
                        """
                        SELECT state, COUNT(*) as count
                        FROM ingest_queue
                        GROUP BY state
                        """
                    ).fetchall()

                    metrics["queue_stats"] = {
                        row["state"]: row["count"] for row in queue_stats
                    }

                    # Get processing rate (groups processed in last hour)
                    one_hour_ago = time.time() - 3600
                    recent_completed = conn.execute(
                        """
                        SELECT COUNT(*) as count
                        FROM ingest_queue
                        WHERE state = 'completed' AND last_update > ?
                        """,
                        (one_hour_ago,),
                    ).fetchone()

                    metrics["processing_rate_per_hour"] = (
                        recent_completed["count"] if recent_completed else 0
                    )
            except Exception as e:
                log.warning(f"Failed to get queue metrics: {e}")
                metrics["queue_error"] = str(e)

        return metrics

    @router.get("/jobs/healthz")
    def jobs_health():
        """Health check for job execution environment.

        Returns booleans and environment info indicating whether background job
        execution is likely to succeed (Python subprocess spawn, CASA import,
        dsa110_contimg import resolution, DB readability, disk space).
        """
        import shutil as _shutil
        import subprocess as _subprocess

        from dsa110_contimg.api.job_runner import (
            _python_cmd_for_jobs,
            _src_path_for_env,
        )
        from dsa110_contimg.database.products import (
            ensure_products_db as _ensure_products_db,
        )

        # Prepare environment for child process imports
        child_env = os.environ.copy()
        src_path = _src_path_for_env()
        if src_path:
            child_env["PYTHONPATH"] = src_path

        py = _python_cmd_for_jobs()

        def _run_py(code: str, timeout: float = 3.0):
            try:
                r = _subprocess.run(
                    py + ["-c", code],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=child_env,
                )
                return (
                    r.returncode == 0,
                    (r.stdout or "").strip(),
                    (r.stderr or "").strip(),
                )
            except Exception as e:  # pragma: no cover - defensive
                return (False, "", str(e))

        # 1) Basic subprocess and interpreter info
        sp_ok, sp_out, sp_err = _run_py(
            "import sys, json; print(json.dumps({'executable': sys.executable, 'version': sys.version}))"
        )
        interp = {}
        try:
            if sp_out:
                import json as _json

                interp = _json.loads(sp_out)
        except Exception:
            interp = {"raw": sp_out}

        # 2) CASA availability in job env
        casa_code = (
            "import json\n"
            "try:\n"
            "    import casatasks\n"
            "    print(json.dumps({'ok': True}))\n"
            "except Exception as e:\n"
            "    print(json.dumps({'ok': False, 'error': str(e)}))\n"
        )
        casa_ok, casa_out, casa_err = _run_py(casa_code, timeout=8.0)
        try:
            import json as _json

            casa_json = _json.loads(casa_out) if casa_out else {"ok": False}
        except Exception:
            casa_json = {"ok": False, "error": casa_err}

        # 3) Import dsa110_contimg in job env
        src_code = (
            "import json\n"
            "try:\n"
            "    import dsa110_contimg.imaging.cli  # noqa\n"
            "    print(json.dumps({'ok': True}))\n"
            "except Exception as e:\n"
            "    print(json.dumps({'ok': False, 'error': str(e)}))\n"
        )
        src_ok, src_out, src_err = _run_py(src_code)
        try:
            import json as _json

            src_json = _json.loads(src_out) if src_out else {"ok": False}
        except Exception:
            src_json = {"ok": False, "error": src_err}

        # 4) Products DB readability
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        db_ok = False
        db_exists = db_path.exists()
        db_error = None
        try:
            conn = _ensure_products_db(db_path)
            conn.execute("SELECT 1")
            conn.close()
            db_ok = True
        except Exception as e:  # pragma: no cover - environment dependent
            db_ok = False
            db_error = str(e)

        # 5) Disk space on state dir
        state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        try:
            du = _shutil.disk_usage(state_dir)
            disk = {"total": du.total, "used": du.used, "free": du.free}
            disk_ok = du.free > 200 * 1024 * 1024  # >200MB free
        except Exception:
            disk = None
            disk_ok = False

        ok = bool(
            sp_ok
            and casa_json.get("ok", False)
            and src_json.get("ok", False)
            and db_ok
            and disk_ok
        )

        return {
            "ok": ok,
            "subprocess_ok": sp_ok,
            "casa_ok": casa_json.get("ok", False),
            "casa_error": (None if casa_json.get("ok") else casa_json.get("error")),
            "src_ok": src_json.get("ok", False),
            "src_error": (None if src_json.get("ok") else src_json.get("error")),
            "db_ok": db_ok,
            "db_exists": db_exists,
            "db_error": db_error,
            "disk_ok": disk_ok,
            "disk": disk,
        }

    # Include router after all routes are defined
    @router.get("/data")
    async def list_data_instances(
        data_type: str | None = None,
        status: str | None = None,
    ):
        """List data instances with optional filters."""
        from pathlib import Path

        from dsa110_contimg.database.data_registry import (
            DataRecord,
            ensure_data_registry_db,
            list_data,
        )

        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
        conn = ensure_data_registry_db(db_path)

        records = list_data(conn, data_type=data_type, status=status)

        return [
            {
                "id": r.data_id,
                "data_type": r.data_type,
                "status": r.status,
                "stage_path": r.stage_path,
                "published_path": r.published_path,
                "created_at": r.created_at,
                "published_at": r.published_at,
                "publish_mode": r.publish_mode,
                "qa_status": r.qa_status,
                "validation_status": r.validation_status,
                "finalization_status": r.finalization_status,
                "auto_publish_enabled": r.auto_publish_enabled,
                "metadata": json.loads(r.metadata_json) if r.metadata_json else None,
            }
            for r in records
        ]

    @router.get("/data/{data_id:path}")
    async def get_data_instance(data_id: str) -> dict:
        """Get a specific data instance."""
        from pathlib import Path

        from dsa110_contimg.database.data_registry import (
            ensure_data_registry_db,
            get_data,
        )

        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
        conn = ensure_data_registry_db(db_path)

        record = get_data(conn, data_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Data {data_id} not found")

        return {
            "id": record.data_id,
            "data_type": record.data_type,
            "status": record.status,
            "stage_path": record.stage_path,
            "published_path": record.published_path,
            "created_at": record.created_at,
            "staged_at": record.staged_at,
            "published_at": record.published_at,
            "publish_mode": record.publish_mode,
            "qa_status": record.qa_status,
            "validation_status": record.validation_status,
            "finalization_status": record.finalization_status,
            "auto_publish_enabled": record.auto_publish_enabled,
            "metadata": (
                json.loads(record.metadata_json) if record.metadata_json else None
            ),
        }

    @router.post("/data/{data_id:path}/finalize")
    async def finalize_data_instance(
        data_id: str,
        qa_status: Optional[str] = None,
        validation_status: Optional[str] = None,
    ):
        """Finalize a data instance and trigger auto-publish if enabled."""
        from pathlib import Path

        from dsa110_contimg.database.data_registry import (
            ensure_data_registry_db,
            finalize_data,
            get_data,
        )

        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
        conn = ensure_data_registry_db(db_path)

        record = get_data(conn, data_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Data {data_id} not found")

        finalized = finalize_data(
            conn, data_id, qa_status=qa_status, validation_status=validation_status
        )

        # Check if auto-published
        updated_record = get_data(conn, data_id)
        auto_published = (
            updated_record.status == "published" if updated_record else False
        )

        return {
            "finalized": finalized,
            "auto_published": auto_published,
            "status": updated_record.status if updated_record else record.status,
        }

    @router.post("/data/{data_id:path}/publish")
    async def publish_data_instance_manual(data_id: str):
        """Manually publish a data instance."""
        from pathlib import Path

        from dsa110_contimg.database.data_registry import (
            ensure_data_registry_db,
            get_data,
            publish_data_manual,
        )

        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
        conn = ensure_data_registry_db(db_path)

        record = get_data(conn, data_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Data {data_id} not found")

        if record.status == "published":
            raise HTTPException(
                status_code=400, detail=f"Data {data_id} is already published"
            )

        success = publish_data_manual(conn, data_id)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to publish {data_id}")

        updated_record = get_data(conn, data_id)
        return {
            "published": True,
            "status": updated_record.status if updated_record else record.status,
            "published_path": updated_record.published_path if updated_record else None,
        }

    @router.post("/data/{data_id:path}/auto-publish/enable")
    async def enable_auto_publish(data_id: str):
        """Enable auto-publish for a data instance."""
        from pathlib import Path

        from dsa110_contimg.database.data_registry import (
            enable_auto_publish as enable_ap,
        )
        from dsa110_contimg.database.data_registry import (
            ensure_data_registry_db,
        )

        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
        conn = ensure_data_registry_db(db_path)

        success = enable_ap(conn, data_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Data {data_id} not found")

        return {"enabled": True}

    @router.post("/data/{data_id:path}/auto-publish/disable")
    async def disable_auto_publish(data_id: str):
        """Disable auto-publish for a data instance."""
        from pathlib import Path

        from dsa110_contimg.database.data_registry import (
            disable_auto_publish as disable_ap,
        )
        from dsa110_contimg.database.data_registry import (
            ensure_data_registry_db,
        )

        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
        conn = ensure_data_registry_db(db_path)

        success = disable_ap(conn, data_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Data {data_id} not found")

        return {"enabled": False}

    @router.get("/data/{data_id:path}/auto-publish/status")
    async def get_auto_publish_status(data_id: str):
        """Get auto-publish status and criteria for a data instance."""
        from pathlib import Path

        from dsa110_contimg.database.data_registry import (
            check_auto_publish_criteria,
            ensure_data_registry_db,
        )

        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
        conn = ensure_data_registry_db(db_path)

        status = check_auto_publish_criteria(conn, data_id)
        return status

    @router.get("/data/{data_id:path}/lineage")
    async def get_data_lineage(data_id: str):
        """Get lineage (parents and children) for a data instance."""
        from pathlib import Path

        from dsa110_contimg.database.data_registry import (
            ensure_data_registry_db,
            get_data,
            get_data_lineage,
        )

        db_path = Path("/data/dsa110-contimg/state/products.sqlite3")
        conn = ensure_data_registry_db(db_path)

        record = get_data(conn, data_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Data {data_id} not found")

        lineage = get_data_lineage(conn, data_id)
        return lineage

    # Include router after all routes are defined
    app.include_router(router)

    # Include visualization routes
    from dsa110_contimg.api.visualization_routes import router as visualization_router

    app.include_router(visualization_router)

    return app
