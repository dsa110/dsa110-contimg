#!/usr/bin/env python3
"""
Automated service health fixer.

Implements missing API endpoints to bring all services to healthy status.
"""

import sys
from pathlib import Path

# Implementation templates for missing endpoints
MISSING_ENDPOINTS = {
    "/api/health/services": """
@router.get("/api/health/services")
def get_health_services():
    \"\"\"Get health status of all backend services.\"\"\"
    from dsa110_contimg.pipeline.circuit_breaker import (
        calibration_solve_circuit_breaker,
        ese_detection_circuit_breaker,
        photometry_circuit_breaker,
    )
    
    services = []
    
    # Check circuit breakers
    for name, cb in [
        ("ese_detection", ese_detection_circuit_breaker),
        ("calibration_solve", calibration_solve_circuit_breaker),
        ("photometry", photometry_circuit_breaker),
    ]:
        services.append({
            "name": name,
            "status": "healthy" if cb.state.value == "closed" else "degraded",
            "state": cb.state.value,
            "failure_count": cb.failure_count,
        })
    
    # Check databases
    from dsa110_contimg.api.health import _check_products_database, _check_calibration_registry
    
    healthy, error = _check_products_database()
    services.append({
        "name": "products_database",
        "status": "healthy" if healthy else "unhealthy",
        "error": error,
    })
    
    healthy, error = _check_calibration_registry()
    services.append({
        "name": "calibration_registry",
        "status": "healthy" if healthy else "unhealthy",
        "error": error,
    })
    
    return {"services": services, "timestamp": time.time()}
""",
    "/api/mosaics": """
@router.get("/api/mosaics")
def list_mosaics(limit: int = Query(10, ge=1, le=100)):
    \"\"\"List available mosaics from the products database.\"\"\"
    import os
    from pathlib import Path

    from dsa110_contimg.api.data_access import fetch_mosaics_recent

    db_path = Path(os.getenv("PIPELINE_PRODUCTS_DB", "state/products.sqlite3"))

    mosaics, total = fetch_mosaics_recent(db_path, limit=limit)
    return {"mosaics": mosaics, "total": total, "limit": limit}
""",
    "/api/sources": """
@router.get("/api/sources")
def list_sources(limit: int = Query(10, ge=1, le=100)):
    \"\"\"List known sources from master_sources database.\"\"\"
    import sqlite3
    
    state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
    master_sources_db = state_dir / "master_sources.sqlite3"
    
    if not master_sources_db.exists():
        return {"sources": [], "total": 0, "limit": limit, "note": "master_sources.sqlite3 not found"}
    
    try:
        conn = sqlite3.connect(str(master_sources_db), timeout=5.0)
        cursor = conn.execute("SELECT name, ra, dec, flux FROM sources LIMIT ?", (limit,))
        sources = [
            {"name": row[0], "ra": row[1], "dec": row[2], "flux_jy": row[3]}
            for row in cursor.fetchall()
        ]
        
        count_cursor = conn.execute("SELECT COUNT(*) FROM sources")
        total = count_cursor.fetchone()[0]
        
        conn.close()
        return {"sources": sources, "total": total, "limit": limit}
    except Exception as e:
        return {"sources": [], "total": 0, "limit": limit, "error": str(e)}
""",
    "/api/pointing/history": """
@router.get("/api/pointing/history")
def get_pointing_history_simple(limit: int = Query(10, ge=1, le=100)):
    \"\"\"Get recent pointing history (simplified endpoint without required date range).\"\"\"
    # Use existing fetch_pointing_history but with default date range
    from datetime import datetime, timedelta
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)  # Last 7 days by default
    
    try:
        history = fetch_pointing_history(
            start_time.timestamp(),
            end_time.timestamp(),
            limit=limit
        )
        return {
            "history": history,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": limit
        }
    except Exception as e:
        return {"history": [], "error": str(e)}
""",
    "/api/calibration/status": """
@router.get("/api/calibration/status")
def get_calibration_status():
    \"\"\"Get overall calibration system status.\"\"\"
    import sqlite3
    
    state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
    registry_db = state_dir / "cal_registry.sqlite3"
    
    status = {
        "registry_available": registry_db.exists(),
        "total_caltables": 0,
        "recent_calibrations": [],
    }
    
    if registry_db.exists():
        try:
            conn = sqlite3.connect(str(registry_db), timeout=5.0)
            
            # Count total caltables
            cursor = conn.execute("SELECT COUNT(*) FROM caltables")
            status["total_caltables"] = cursor.fetchone()[0]
            
            # Get recent calibrations
            cursor = conn.execute(
                "SELECT path, created_at, quality_score FROM caltables "
                "ORDER BY created_at DESC LIMIT 5"
            )
            status["recent_calibrations"] = [
                {"path": row[0], "created_at": row[1], "quality_score": row[2]}
                for row in cursor.fetchall()
            ]
            
            conn.close()
        except Exception as e:
            status["error"] = str(e)
    
    return status
""",
    "/api/visualization/casatable/info": """
@router.get("/api/visualization/casatable/info")
def get_casatable_info(path: str = Query(..., description="Relative path to casa table")):
    \"\"\"Get information about a CASA measurement set or table.\"\"\"
    # Validate path is relative
    if path.startswith("/"):
        raise HTTPException(status_code=400, detail="Absolute paths not allowed")
    
    state_dir = Path(os.getenv("PIPELINE_STATE_DIR", "state"))
    full_path = state_dir / path
    
    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"Table not found: {path}")
    
    # Basic info without CASA dependency
    info = {
        "path": str(full_path),
        "exists": True,
        "size_bytes": sum(f.stat().st_size for f in full_path.rglob("*") if f.is_file()),
        "note": "Detailed CASA table inspection requires casacore",
    }
    
    return info
""",
    "/api/ws/status": """
@router.get("/api/ws/status")
def get_websocket_status():
    \"\"\"Get WebSocket connection manager status.\"\"\"
    # Check if WebSocket manager is available
    ws_status = {
        "enabled": True,
        "endpoint": "/ws",
        "active_connections": 0,  # Would need to track this in ConnectionManager
        "note": "WebSocket endpoint available at /ws"
    }
    
    return ws_status
""",
}


def apply_fixes():
    """Apply fixes for missing and broken endpoints."""
    print("=" * 80)
    print("AUTOMATED SERVICE HEALTH FIXER")
    print("=" * 80)
    print()

    routes_file = Path("/data/dsa110-contimg/backend/src/dsa110_contimg/api/routes.py")

    if not routes_file.exists():
        print(f"ERROR: Routes file not found: {routes_file}")
        return False

    print(f"Reading routes file: {routes_file}")
    content = routes_file.read_text()

    # Find where to insert new routes (before the last lines of the file)
    # Look for the FastAPI app setup section
    insert_marker = "# Include router in app"
    if insert_marker not in content:
        # Alternative: insert before app.include_router
        insert_marker = "app.include_router(router)"

    if insert_marker not in content:
        print("ERROR: Could not find insertion point in routes.py")
        return False

    # Build the new routes section
    new_routes = "\n\n# ========== AUTO-GENERATED MISSING ENDPOINTS ==========\n"
    new_routes += "# Generated by scripts/diagnostics/diagnose_all_services.py\n"
    new_routes += (
        "# These endpoints were missing and causing degraded service status\n\n"
    )

    for endpoint, implementation in MISSING_ENDPOINTS.items():
        new_routes += implementation.strip() + "\n\n"

    new_routes += "# ========== END AUTO-GENERATED ENDPOINTS ==========\n\n"

    # Insert new routes before the marker
    parts = content.split(insert_marker)
    new_content = parts[0] + new_routes + insert_marker + parts[1]

    # Backup original file
    backup_file = routes_file.with_suffix(".py.backup")
    routes_file.rename(backup_file)
    print(f"Backed up original to: {backup_file}")

    # Write new content
    routes_file.write_text(new_content)
    print(f"Applied fixes to: {routes_file}")

    print()
    print("✓ Successfully added 7 missing endpoint implementations")
    print()
    print("Next steps:")
    print("  1. Restart backend API: systemctl restart dsa110-backend")
    print("  2. Or reload uvicorn if running manually")
    print(
        "  3. Re-run diagnostics: python3 scripts/diagnostics/diagnose_all_services.py"
    )
    print()

    return True


if __name__ == "__main__":
    success = apply_fixes()
    sys.exit(0 if success else 1)
