"""FastAPI routing for the pipeline monitoring API."""

from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from typing import List
from collections import deque
import shutil
from fastapi.staticfiles import StaticFiles

from dsa110_contimg.api.config import ApiConfig
from dsa110_contimg.api.data_access import (
    fetch_calibration_sets,
    fetch_queue_stats,
    fetch_recent_products,
    fetch_recent_queue_groups,
    fetch_recent_calibrator_matches,
)
from dsa110_contimg.api.models import PipelineStatus, ProductList, CalibratorMatchList, QAList, QAArtifact, GroupDetail, SystemMetrics, MsIndexList, MsIndexEntry
from dsa110_contimg.api.data_access import _connect


def create_app(config: ApiConfig | None = None) -> FastAPI:
    """Factory for the monitoring API application."""

    cfg = config or ApiConfig.from_env()
    app = FastAPI(title="DSA-110 Continuum Pipeline API", version="0.1.0")

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
        fpath = base_state / "qa" / group / name
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

    app.include_router(router)
    
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
            q += " ORDER BY COALESCE(stage_updated_at, processed_at) DESC NULLS LAST LIMIT ?"
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
    # Mount basic static dir for simple JS/HTML views (optional)
    static_dir = Path(__file__).resolve().parent / 'static'
    if static_dir.exists():
        app.mount('/ui/static', StaticFiles(directory=str(static_dir)), name='static')
        @app.get('/ui', response_class=HTMLResponse)
        def dashboard_root() -> HTMLResponse:  # noqa: WPS430
            index_path = static_dir / 'index.html'
            if index_path.exists():
                return HTMLResponse(content=index_path.read_text(encoding='utf-8'))
            # Fallback to calibrators view if index missing
            return HTMLResponse(content='<html><body><a href="/api/ui/calibrators">Calibrator Matches</a></body></html>')
    return app
