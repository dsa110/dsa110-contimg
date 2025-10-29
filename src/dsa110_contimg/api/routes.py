"""FastAPI routing for the pipeline monitoring API."""

from __future__ import annotations

import os
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from typing import List
from collections import deque
import shutil
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

from dsa110_contimg.api.config import ApiConfig
from dsa110_contimg.api.data_access import (
    fetch_calibration_sets,
    fetch_queue_stats,
    fetch_recent_products,
    fetch_recent_queue_groups,
    fetch_recent_calibrator_matches,
    fetch_pointing_history,
)
from dsa110_contimg.api.models import (
    PipelineStatus,
    ProductList,
    CalTableList,
    CalTableInfo,
    ExistingCalTables,
    ExistingCalTable,
    MSMetadata,
    MSCalibratorMatchList,
    MSCalibratorMatch,
    WorkflowJobCreateRequest,
    CalibratorMatchList,
    QAList,
    QAArtifact,
    GroupDetail,
    SystemMetrics,
    MsIndexList,
    MsIndexEntry,
    PointingHistoryList,
    Job,
    JobList,
    JobCreateRequest,
    MSList,
    MSListEntry,
    UVH5FileList,
    UVH5FileEntry,
    ConversionJobCreateRequest,
    ConversionJobParams,
    CalibrateJobParams,
    CalibrationQA,
    ImageQA,
    QAMetrics,
)
from dsa110_contimg.api.data_access import _connect
from dsa110_contimg.api.mock_data import (
    generate_mock_ese_candidates,
    generate_mock_mosaics,
    generate_mock_source_timeseries,
    generate_mock_alert_history,
)


def create_app(config: ApiConfig | None = None) -> FastAPI:
    """Factory for the monitoring API application."""

    cfg = config or ApiConfig.from_env()
    app = FastAPI(title="DSA-110 Continuum Pipeline API", version="0.1.0")

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
            app.mount("/ui", StaticFiles(directory=str(frontend_dist), html=True), name="ui")
    except Exception:
        pass

    router = APIRouter(prefix="/api")

    @router.get("/status", response_model=PipelineStatus)
    def status(limit: int = 20) -> PipelineStatus:  # noqa: WPS430 (fastapi handles context)
        queue_stats = fetch_queue_stats(cfg.queue_db)
        recent_groups = fetch_recent_queue_groups(cfg.queue_db, cfg, limit=limit)
        cal_sets = fetch_calibration_sets(cfg.registry_db)
        matched_recent = sum(1 for g in recent_groups if getattr(g, 'has_calibrator', False))
        return PipelineStatus(queue=queue_stats, recent_groups=recent_groups, calibration_sets=cal_sets, matched_recent=matched_recent)

    @router.get("/products", response_model=ProductList)
    def products(limit: int = 50) -> ProductList:
        items = fetch_recent_products(cfg.products_db, limit=limit)
        return ProductList(items=items)

    @router.get("/calibrator_matches", response_model=CalibratorMatchList)
    def calibrator_matches(limit: int = 50, matched_only: bool = False) -> CalibratorMatchList:
        items = fetch_recent_calibrator_matches(cfg.queue_db, limit=limit, matched_only=matched_only)
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
                        ts = datetime.fromtimestamp(r["created_at"]) if r["created_at"] else None
                        artifacts.append(QAArtifact(group_id=r["group_id"], name=r["name"], path=r["path"], created_at=ts))
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
                            artifacts.append(QAArtifact(group_id=group_id, name=f.name, path=str(f), created_at=ts))
                except Exception:
                    continue
        artifacts.sort(key=lambda a: a.created_at or datetime.fromtimestamp(0), reverse=True)
        return QAList(items=artifacts[:limit])

    @router.get("/qa/file/{group}/{name}")
    def qa_file(group: str, name: str):
        base_state = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
        base = (base_state / "qa").resolve()
        fpath = (base / group / name).resolve()
        try:
            # Python 3.9+: safe containment check
            if not fpath.is_relative_to(base):
                return HTMLResponse(status_code=403, content="Forbidden")
        except AttributeError:  # pragma: no cover - fallback for very old Python
            base_str = str(base) + os.sep
            if not str(fpath).startswith(base_str):
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
            du = shutil.disk_usage('/')
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
                        ts = datetime.fromtimestamp(r["created_at"]) if r["created_at"] else None
                        artifacts.append(QAArtifact(group_id=r["group_id"], name=r["name"], path=r["path"], created_at=ts))
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
                for f in sorted(sub.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
                    if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg"):
                        latest = f
                        break
                if latest:
                    ts = datetime.fromtimestamp(latest.stat().st_mtime)
                    artifacts.append(QAArtifact(group_id=sub.name, name=latest.name, path=str(latest), created_at=ts))
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
                        weighted_flux=float(m.get("weighted_flux")) if m.get("weighted_flux") is not None else None,
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
                        ts = datetime.fromtimestamp(r["created_at"]) if r["created_at"] else None
                        qa_items.append(QAArtifact(group_id=group_id, name=r["name"], path=r["path"], created_at=ts))
        except Exception:
            qa_items = []
        # FS fallback
        if not qa_items and qa_dir.exists():
            for f in qa_dir.iterdir():
                if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".svg", ".html") and f.is_file():
                    try:
                        ts = datetime.fromtimestamp(f.stat().st_mtime)
                    except Exception:
                        ts = None
                    qa_items.append(QAArtifact(group_id=group_id, name=f.name, path=str(f), created_at=ts))

        # Fetch writer type from performance_metrics
        writer_type = None
        try:
            pdb = _connect(cfg.queue_db)
            with pdb:
                w = pdb.execute("SELECT writer_type FROM performance_metrics WHERE group_id = ?", (group_id,)).fetchone()
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
            has_calibrator=bool(row["has_calibrator"]) if row["has_calibrator"] is not None else None,
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
                match_html = "<ul>" + "".join(
                    f"<li>{m.name} (sep {m.sep_deg:.2f}°; RA {m.ra_deg:.4f}°, Dec {m.dec_deg:.4f}°; wflux {'' if m.weighted_flux is None else f'{m.weighted_flux:.2f} Jy' })</li>"
                    for m in g.matches
                ) + "</ul>"
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
    def ms_index(stage: str | None = None, status: str | None = None, limit: int = 100) -> MsIndexList:
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
                items.append(MsIndexEntry(
                    path=r["path"],
                    start_mjd=r["start_mjd"], end_mjd=r["end_mjd"], mid_mjd=r["mid_mjd"],
                    processed_at=(datetime.fromtimestamp(r["processed_at"]) if r["processed_at"] else None),
                    status=r["status"], stage=r["stage"],
                    stage_updated_at=(datetime.fromtimestamp(r["stage_updated_at"]) if r["stage_updated_at"] else None),
                    cal_applied=r["cal_applied"], imagename=r["imagename"],
                ))
        return MsIndexList(items=items)

    @router.post("/reprocess/{group_id}")
    def reprocess_group(group_id: str):
        # Nudge the ingest_queue row back to 'pending' to trigger reprocessing
        qdb = Path(os.getenv("PIPELINE_QUEUE_DB", os.getenv("PIPELINE_QUEUE_DB", "state/ingest.sqlite3")))
        if not qdb.exists():
            return {"ok": False, "error": "queue_db not found"}
        with _connect(qdb) as conn:
            now = datetime.utcnow().timestamp()
            row = conn.execute("SELECT state, retry_count FROM ingest_queue WHERE group_id = ?", (group_id,)).fetchone()
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
    @router.get("/ese/candidates")
    def ese_candidates():
        """Get ESE candidate sources (mock data)."""
        return {
            'candidates': generate_mock_ese_candidates(5),
            'total': 5,
        }

    @router.post("/mosaics/query")
    def mosaics_query(request: dict):
        """Query mosaics by time range (mock data)."""
        start_time = request.get('start_time', '')
        end_time = request.get('end_time', '')
        mosaics = generate_mock_mosaics(start_time, end_time)
        return {
            'mosaics': mosaics,
            'total': len(mosaics),
        }

    @router.post("/mosaics/create")
    def mosaics_create(request: dict):
        """Create a new mosaic (mock response)."""
        return {
            'status': 'pending',
            'message': 'Mosaic generation queued',
            'mosaic_id': 'mosaic_new_001',
        }

    @router.post("/sources/search")
    def sources_search(request: dict):
        """Search for sources (mock data)."""
        source_id = request.get('source_id', 'NVSS J123456+420312')
        source = generate_mock_source_timeseries(source_id)
        return {
            'sources': [source],
            'total': 1,
        }

    @router.get("/alerts/history")
    def alerts_history(limit: int = 50):
        """Get alert history (mock data)."""
        return generate_mock_alert_history(limit)

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
    ) -> MSList:
        """List available Measurement Sets with filtering and sorting."""
        from dsa110_contimg.database.products import ensure_products_db
        from astropy.time import Time
        import astropy.units as u
        
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        entries: list[MSListEntry] = []
        
        try:
            conn = ensure_products_db(db_path)
            
            # Build query with filters
            where_clauses = []
            params: list[object] = []
            
            if search:
                where_clauses.append("(m.path LIKE ? OR COALESCE(cm.calibrator_name, '') LIKE ?)")
                params.extend([f"%{search}%", f"%{search}%"])
            
            if has_calibrator is not None:
                if has_calibrator:
                    where_clauses.append("cm.has_calibrator = 1")
                else:
                    where_clauses.append("(cm.has_calibrator = 0 OR cm.has_calibrator IS NULL)")
            
            if is_calibrated is not None:
                if is_calibrated:
                    where_clauses.append("m.cal_applied = 1")
                else:
                    where_clauses.append("(m.cal_applied = 0 OR m.cal_applied IS NULL)")
            
            if is_imaged is not None:
                if is_imaged:
                    where_clauses.append("m.imagename IS NOT NULL AND m.imagename != ''")
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
            count_query = f"""
                SELECT COUNT(*) FROM ms_index m
                LEFT JOIN (
                    SELECT ms_path, 
                           MAX(CASE WHEN has_calibrator = 1 THEN 1 ELSE 0 END) as has_calibrator,
                           MAX(calibrator_name) as calibrator_name,
                           MAX(calibrator_quality) as calibrator_quality
                    FROM (
                        SELECT ms_path, 1 as has_calibrator, name as calibrator_name, quality as calibrator_quality
                        FROM pointing_history
                        WHERE calibrator_name IS NOT NULL
                    )
                    GROUP BY ms_path
                ) cm ON m.path = cm.ms_path
                WHERE {where_sql}
            """
            total_count = conn.execute(count_query, params).fetchone()[0]
            
            # Main query with joins
            query = f"""
                SELECT 
                    m.path,
                    m.mid_mjd,
                    m.status,
                    m.cal_applied,
                    COALESCE(cm.has_calibrator, 0) as has_calibrator,
                    cm.calibrator_name,
                    cm.calibrator_quality,
                    CASE WHEN m.cal_applied = 1 THEN 1 ELSE 0 END as is_calibrated,
                    CASE WHEN m.imagename IS NOT NULL AND m.imagename != '' THEN 1 ELSE 0 END as is_imaged,
                    cq.overall_quality as calibration_quality,
                    iq.overall_quality as image_quality,
                    m.start_mjd,
                    m.end_mjd
                FROM ms_index m
                LEFT JOIN (
                    SELECT ms_path, 
                           MAX(CASE WHEN has_calibrator = 1 THEN 1 ELSE 0 END) as has_calibrator,
                           MAX(calibrator_name) as calibrator_name,
                           MAX(calibrator_quality) as calibrator_quality
                    FROM (
                        SELECT ms_path, 1 as has_calibrator, name as calibrator_name, quality as calibrator_quality
                        FROM pointing_history
                        WHERE calibrator_name IS NOT NULL
                    )
                    GROUP BY ms_path
                ) cm ON m.path = cm.ms_path
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
                        start_time = Time(row[11], format='mjd').iso
                    except Exception:
                        pass
                
                # Calculate size (placeholder - would need actual file size)
                size_gb = None
                try:
                    ms_path = Path(row[0])
                    if ms_path.exists():
                        total_size = sum(f.stat().st_size for f in ms_path.rglob('*') if f.is_file())
                        size_gb = total_size / (1024**3)
                except Exception:
                    pass
                
                entries.append(MSListEntry(
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
                ))
        except Exception as e:
            logger.error(f"Failed to list MS: {e}")
            return MSList(items=[], total=0, filtered=0)
        
        return MSList(items=entries, total=total_count, filtered=len(entries))

    @router.get("/jobs", response_model=JobList)
    def list_jobs(limit: int = 50, status: str | None = None) -> JobList:
        """List recent jobs."""
        from dsa110_contimg.database.jobs import list_jobs as db_list_jobs
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.api.models import JobParams
        
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)
        jobs_data = db_list_jobs(conn, limit=limit, status=status)
        conn.close()
        
        jobs = []
        for jd in jobs_data:
            jobs.append(Job(
                id=jd["id"],
                type=jd["type"],
                status=jd["status"],
                ms_path=jd["ms_path"],
                params=JobParams(**jd["params"]),
                logs=jd["logs"],
                artifacts=jd["artifacts"],
                created_at=datetime.fromtimestamp(jd["created_at"]),
                started_at=datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None,
                finished_at=datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None,
            ))
        
        return JobList(items=jobs)

    

    @router.get("/jobs/id/{job_id}", response_model=Job)
    def get_job(job_id: int) -> Job:
        """Get job details by ID."""
        from dsa110_contimg.database.jobs import get_job as db_get_job
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.api.models import JobParams
        
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
            started_at=datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None,
            finished_at=datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None,
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
                    yield f"event: error\ndata: {{\"message\": \"Job not found\"}}\n\n"
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
    def create_calibrate_job(request: JobCreateRequest, background_tasks: BackgroundTasks) -> Job:
        """Create and run a calibration job."""
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.api.job_runner import run_calibrate_job
        from dsa110_contimg.api.models import JobParams
        
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)
        
        job_id = create_job(conn, "calibrate", request.ms_path, request.params.model_dump())
        conn.close()
        
        # Start job in background
        background_tasks.add_task(run_calibrate_job, job_id, request.ms_path, request.params.model_dump(), db_path)
        
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
            started_at=datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None,
            finished_at=datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None,
        )

    @router.post("/jobs/apply", response_model=Job)
    def create_apply_job(request: JobCreateRequest, background_tasks: BackgroundTasks) -> Job:
        """Create and run an apply calibration job."""
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.api.job_runner import run_apply_job
        from dsa110_contimg.api.models import JobParams
        
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)
        
        job_id = create_job(conn, "apply", request.ms_path, request.params.model_dump())
        conn.close()
        
        # Start job in background
        background_tasks.add_task(run_apply_job, job_id, request.ms_path, request.params.model_dump(), db_path)
        
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
            started_at=datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None,
            finished_at=datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None,
        )

    @router.post("/jobs/image", response_model=Job)
    def create_image_job(request: JobCreateRequest, background_tasks: BackgroundTasks) -> Job:
        """Create and run an imaging job."""
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.api.job_runner import run_image_job
        from dsa110_contimg.api.models import JobParams
        
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)
        
        job_id = create_job(conn, "image", request.ms_path, request.params.model_dump())
        conn.close()
        
        # Start job in background
        background_tasks.add_task(run_image_job, job_id, request.ms_path, request.params.model_dump(), db_path)
        
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
            started_at=datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None,
            finished_at=datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None,
        )

    @router.get("/uvh5", response_model=UVH5FileList)
    def list_uvh5_files(input_dir: str | None = None, limit: int = 100) -> UVH5FileList:
        """List available UVH5 files for conversion."""
        from dsa110_contimg.api.models import UVH5FileEntry, UVH5FileList
        import re
        import glob as _glob
        
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
                match = re.match(r'(.+)_sb(\d+)\.hdf5$', fname)
                if match:
                    timestamp = match.group(1)
                    subband = f"sb{match.group(2)}"
                
                entries.append(UVH5FileEntry(
                    path=fpath,
                    timestamp=timestamp,
                    subband=subband,
                    size_mb=round(size_mb, 2),
                ))
        except Exception:
            pass
        
        return UVH5FileList(items=entries)

    @router.post("/jobs/convert", response_model=Job)
    def create_convert_job(request: ConversionJobCreateRequest, background_tasks: BackgroundTasks) -> Job:
        """Create and run a UVH5 → MS conversion job."""
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.api.job_runner import run_convert_job
        from dsa110_contimg.api.models import JobParams, ConversionJobParams
        
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)
        
        # Create job with conversion params (ms_path is empty for conversion jobs)
        job_id = create_job(conn, "convert", "", request.params.model_dump())
        conn.close()
        
        # Start job in background
        background_tasks.add_task(run_convert_job, job_id, request.params.model_dump(), db_path)
        
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
            params=JobParams(**jd["params"]) if jd["type"] != "convert" else JobParams(),  # Placeholder
            logs=jd["logs"],
            artifacts=jd["artifacts"],
            created_at=datetime.fromtimestamp(jd["created_at"]),
            started_at=datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None,
            finished_at=datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None,
        )

    @router.get("/caltables", response_model=CalTableList)
    def list_caltables(cal_dir: str | None = None) -> CalTableList:
        """List available calibration tables."""
        from dsa110_contimg.api.models import CalTableInfo, CalTableList
        import re
        import glob as _glob
        
        if cal_dir is None:
            cal_dir = os.getenv("CONTIMG_CAL_DIR", "/scratch/dsa110-contimg/cal")
        
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
                size_mb = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, _, filenames in os.walk(fpath)
                    for filename in filenames
                ) / (1024 * 1024) if os.path.isdir(fpath) else os.path.getsize(fpath) / (1024 * 1024)
                
                # Determine table type from extension
                if fname.endswith('.kcal'):
                    table_type = 'K'
                elif fname.endswith('.bpcal'):
                    table_type = 'BP'
                elif fname.endswith('.gpcal'):
                    table_type = 'G'
                elif fname.endswith('.fcal'):
                    table_type = 'F'
                else:
                    table_type = 'unknown'
                
                modified_time = datetime.fromtimestamp(os.path.getmtime(fpath))
                
                entries.append(CalTableInfo(
                    path=fpath,
                    filename=fname,
                    table_type=table_type,
                    size_mb=round(size_mb, 2),
                    modified_time=modified_time,
                ))
        except Exception:
            pass
        
        return CalTableList(items=entries)

    @router.get("/ms/{ms_path:path}/metadata", response_model=MSMetadata)
    def get_ms_metadata(ms_path: str) -> MSMetadata:
        """Get metadata for an MS file."""
        from dsa110_contimg.api.models import MSMetadata
        from casatools import table, ms as casams
        
        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith('/') else ms_path
        
        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")
        
        metadata = MSMetadata(path=ms_full_path)
        
        try:
            # Get basic info from MAIN table
            tb = table()
            tb.open(ms_full_path, nomodify=True)
            
            times = tb.getcol("TIME")
            if len(times) > 0:
                start_time = datetime.fromtimestamp(times.min()).isoformat()
                end_time = datetime.fromtimestamp(times.max()).isoformat()
                metadata.start_time = start_time
                metadata.end_time = end_time
                metadata.duration_sec = float(times.max() - times.min())
            
            # Get available data columns
            colnames = tb.colnames()
            data_cols = [col for col in colnames if 'DATA' in col]
            metadata.data_columns = data_cols
            metadata.calibrated = 'CORRECTED_DATA' in data_cols
            
            tb.close()
            
            # Get field info
            tb.open(f"{ms_full_path}/FIELD", nomodify=True)
            field_names = tb.getcol("NAME").tolist()
            metadata.num_fields = len(field_names)
            metadata.field_names = field_names
            tb.close()
            
            # Get spectral window info
            tb.open(f"{ms_full_path}/SPECTRAL_WINDOW", nomodify=True)
            chan_freqs = tb.getcol("CHAN_FREQ")
            if len(chan_freqs) > 0:
                metadata.freq_min_ghz = float(chan_freqs.min() / 1e9)
                metadata.freq_max_ghz = float(chan_freqs.max() / 1e9)
                metadata.num_channels = int(chan_freqs.shape[0])
            tb.close()
            
            # Get antenna info
            tb.open(f"{ms_full_path}/ANTENNA", nomodify=True)
            metadata.num_antennas = tb.nrows()
            tb.close()
            
            # Get size
            size_bytes = sum(
                os.path.getsize(os.path.join(dirpath, filename))
                for dirpath, _, filenames in os.walk(ms_full_path)
                for filename in filenames
            )
            metadata.size_gb = round(size_bytes / (1024**3), 2)
            
        except Exception as e:
            # Return partial metadata if some operations fail
            pass
        
        return metadata

    @router.get("/ms/{ms_path:path}/calibrator-matches", response_model=MSCalibratorMatchList)
    def get_ms_calibrator_matches(ms_path: str, catalog: str = "vla", radius_deg: float = 1.5, top_n: int = 5) -> MSCalibratorMatchList:
        """Find calibrator candidates for an MS."""
        from dsa110_contimg.calibration.catalogs import (
            calibrator_match, 
            read_vla_parsed_catalog_csv,
            airy_primary_beam_response
        )
        from dsa110_contimg.pointing import read_pointing_from_ms
        from casatools import table
        import numpy as np
        import astropy.units as u
        from astropy.time import Time
        
        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith('/') else ms_path
        
        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")
        
        try:
            # Get pointing declination
            pt_dec = read_pointing_from_ms(ms_full_path)
            
            # Get mid MJD from MS
            tb = table()
            tb.open(ms_full_path, nomodify=True)
            times = tb.getcol("TIME")
            tb.close()
            
            if len(times) == 0:
                raise HTTPException(status_code=400, detail="MS has no data")
            
            mid_time = (times.min() + times.max()) / 2.0
            # CASA times are in seconds since MJD 0
            mid_mjd = mid_time / 86400.0
            
            # Load catalog
            if catalog == "vla":
                cat_path = os.getenv("VLA_CATALOG", "/data/dsa110-contimg/data/catalogs/VLA_calibrators_parsed.csv")
                if not os.path.exists(cat_path):
                    raise HTTPException(status_code=500, detail=f"Catalog not found: {cat_path}")
                df = read_vla_parsed_catalog_csv(cat_path)
            else:
                raise HTTPException(status_code=400, detail="Unknown catalog")
            
            # Get top matches
            matches_raw = calibrator_match(df, pt_dec, mid_mjd, radius_deg=radius_deg, freq_ghz=1.4, top_n=top_n)
            
            # Convert to MSCalibratorMatch with quality assessment
            matches = []
            for m in matches_raw:
                # Get flux from catalog
                flux_jy = df.loc[m['name'], 'flux_20_cm'] / 1000.0 if m['name'] in df.index else 0.0
                
                # Compute PB response
                from astropy.coordinates import Angle
                t = Time(mid_mjd, format='mjd', scale='utc')
                from dsa110_contimg.pointing import OVRO
                t.location = OVRO
                ra_meridian = t.sidereal_time('apparent').to_value(u.deg)
                dec_meridian = float(pt_dec.to_value(u.deg))
                
                pb_response = airy_primary_beam_response(
                    np.deg2rad(ra_meridian), 
                    np.deg2rad(dec_meridian),
                    np.deg2rad(m['ra_deg']), 
                    np.deg2rad(m['dec_deg']),
                    1.4
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
                
                matches.append(MSCalibratorMatch(
                    name=m['name'],
                    ra_deg=m['ra_deg'],
                    dec_deg=m['dec_deg'],
                    flux_jy=float(flux_jy),
                    sep_deg=m['sep_deg'],
                    pb_response=float(pb_response),
                    weighted_flux=m.get('weighted_flux', 0.0),
                    quality=quality,
                    recommended_fields=None  # Could add field detection here
                ))
            
            has_calibrator = len(matches) > 0 and matches[0].pb_response > 0.3
            
            return MSCalibratorMatchList(
                ms_path=ms_full_path,
                pointing_dec=float(pt_dec.to_value(u.deg)),
                mid_mjd=float(mid_mjd),
                matches=matches,
                has_calibrator=has_calibrator
            )
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error finding calibrators: {str(e)}")

    @router.get("/ms/{ms_path:path}/existing-caltables", response_model=ExistingCalTables)
    def get_existing_caltables(ms_path: str) -> ExistingCalTables:
        """Discover existing calibration tables for an MS."""
        import glob
        import time
        
        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith('/') else ms_path
        
        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")
        
        # Get MS directory and base name
        ms_dir = os.path.dirname(ms_full_path)
        ms_base = os.path.basename(ms_full_path).replace('.ms', '')
        
        # Search patterns for cal tables
        k_pattern = os.path.join(ms_dir, f"{ms_base}*kcal")
        bp_pattern = os.path.join(ms_dir, f"{ms_base}*bpcal")
        g_pattern = os.path.join(ms_dir, f"{ms_base}*g*cal")  # Matches gpcal and gacal
        
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
                age_hours=round(age_hours, 2)
            )
        
        # Find tables
        k_tables = [make_table_info(p) for p in glob.glob(k_pattern) if os.path.isdir(p)]
        bp_tables = [make_table_info(p) for p in glob.glob(bp_pattern) if os.path.isdir(p)]
        g_tables = [make_table_info(p) for p in glob.glob(g_pattern) if os.path.isdir(p)]
        
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
            has_g=len(g_tables) > 0
        )

    @router.get("/qa/calibration/{ms_path:path}", response_model=CalibrationQA)
    def get_calibration_qa(ms_path: str) -> CalibrationQA:
        """Get calibration QA metrics for an MS."""
        from dsa110_contimg.database.products import ensure_products_db
        import json
        
        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith('/') else ms_path
        
        if not os.path.exists(ms_full_path):
            raise HTTPException(status_code=404, detail="MS not found")
        
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)
        
        try:
            # Get latest calibration QA for this MS
            cursor = conn.execute(
                """
                SELECT id, ms_path, job_id, k_metrics, bp_metrics, g_metrics, 
                       overall_quality, flags_total, timestamp
                FROM calibration_qa
                WHERE ms_path = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (ms_full_path,)
            )
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="No calibration QA found for this MS")
            
            # Parse JSON metrics
            k_metrics = json.loads(row[3]) if row[3] else None
            bp_metrics = json.loads(row[4]) if row[4] else None
            g_metrics = json.loads(row[5]) if row[5] else None
            
            return CalibrationQA(
                ms_path=row[1],
                job_id=row[2],
                k_metrics=k_metrics,
                bp_metrics=bp_metrics,
                g_metrics=g_metrics,
                overall_quality=row[6] or "unknown",
                flags_total=row[7],
                timestamp=datetime.fromtimestamp(row[8])
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching calibration QA: {e}")
            raise HTTPException(status_code=500, detail=f"Error fetching calibration QA: {str(e)}")
        finally:
            conn.close()

    @router.get("/qa/image/{ms_path:path}", response_model=ImageQA)
    def get_image_qa(ms_path: str) -> ImageQA:
        """Get image QA metrics for an MS."""
        from dsa110_contimg.database.products import ensure_products_db
        
        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith('/') else ms_path
        
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
                (ms_full_path,)
            )
            row = cursor.fetchone()
            
            if not row:
                raise HTTPException(status_code=404, detail="No image QA found for this MS")
            
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
                timestamp=datetime.fromtimestamp(row[13])
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching image QA: {e}")
            raise HTTPException(status_code=500, detail=f"Error fetching image QA: {str(e)}")
        finally:
            conn.close()

    @router.get("/qa/{ms_path:path}", response_model=QAMetrics)
    def get_qa_metrics(ms_path: str) -> QAMetrics:
        """Get combined QA metrics (calibration + image) for an MS."""
        from dsa110_contimg.database.products import ensure_products_db
        import json
        
        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith('/') else ms_path
        
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
                    (ms_full_path,)
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
                        timestamp=datetime.fromtimestamp(row[8])
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
                    (ms_full_path,)
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
                        timestamp=datetime.fromtimestamp(row[13])
                    )
            except Exception as e:
                logger.warning(f"Could not fetch image QA: {e}")
            
            return QAMetrics(
                ms_path=ms_full_path,
                calibration_qa=cal_qa,
                image_qa=img_qa
            )
        except Exception as e:
            logger.error(f"Error fetching QA metrics: {e}")
            raise HTTPException(status_code=500, detail=f"Error fetching QA metrics: {str(e)}")
        finally:
            conn.close()

    @router.get("/thumbnails/{ms_path:path}.png")
    def get_image_thumbnail(ms_path: str):
        """Serve image thumbnail for an MS."""
        from dsa110_contimg.database.products import ensure_products_db
        
        # Decode path
        ms_full_path = f"/{ms_path}" if not ms_path.startswith('/') else ms_path
        
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
                (ms_full_path,)
            )
            row = cursor.fetchone()
            
            if not row or not row[0]:
                raise HTTPException(status_code=404, detail="No thumbnail found for this MS")
            
            thumbnail_path = Path(row[0])
            if not thumbnail_path.exists():
                raise HTTPException(status_code=404, detail="Thumbnail file not found")
            
            return FileResponse(
                str(thumbnail_path),
                media_type="image/png",
                filename=f"{os.path.basename(ms_full_path)}.thumb.png"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error serving thumbnail: {e}")
            raise HTTPException(status_code=500, detail=f"Error serving thumbnail: {str(e)}")
        finally:
            conn.close()

    @router.post("/jobs/workflow", response_model=Job)
    def create_workflow_job(request: WorkflowJobCreateRequest, background_tasks: BackgroundTasks) -> Job:
        """Create and run a full pipeline workflow (Convert → Calibrate → Image)."""
        from dsa110_contimg.database.jobs import create_job
        from dsa110_contimg.database.products import ensure_products_db
        from dsa110_contimg.api.job_runner import run_workflow_job
        from dsa110_contimg.api.models import JobParams
        
        db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))
        conn = ensure_products_db(db_path)
        
        # Create workflow job
        job_id = create_job(conn, "workflow", "", request.params.model_dump())
        conn.close()
        
        # Start workflow in background
        background_tasks.add_task(run_workflow_job, job_id, request.params.model_dump(), db_path)
        
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
            started_at=datetime.fromtimestamp(jd["started_at"]) if jd["started_at"] else None,
            finished_at=datetime.fromtimestamp(jd["finished_at"]) if jd["finished_at"] else None,
        )

    @router.get("/jobs/healthz")
    def jobs_health():
        """Health check for job execution environment.

        Returns booleans and environment info indicating whether background job
        execution is likely to succeed (Python subprocess spawn, CASA import,
        dsa110_contimg import resolution, DB readability, disk space).
        """
        import subprocess as _subprocess
        import shutil as _shutil
        from dsa110_contimg.api.job_runner import _python_cmd_for_jobs, _src_path_for_env
        from dsa110_contimg.database.products import ensure_products_db as _ensure_products_db

        # Prepare environment for child process imports
        child_env = os.environ.copy()
        src_path = _src_path_for_env()
        if src_path:
            child_env["PYTHONPATH"] = src_path

        py = _python_cmd_for_jobs()

        def _run_py(code: str, timeout: float = 3.0):
            try:
                r = _subprocess.run(py + ["-c", code], capture_output=True, text=True, timeout=timeout, env=child_env)
                return (r.returncode == 0, (r.stdout or "").strip(), (r.stderr or "").strip())
            except Exception as e:  # pragma: no cover - defensive
                return (False, "", str(e))

        # 1) Basic subprocess and interpreter info
        sp_ok, sp_out, sp_err = _run_py("import sys, json; print(json.dumps({'executable': sys.executable, 'version': sys.version}))")
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

        ok = bool(sp_ok and casa_json.get("ok", False) and src_json.get("ok", False) and db_ok and disk_ok)

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