"""
Calibration routes.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException

from ..errors import db_unavailable, internal_error
from ..repositories import safe_row_get

router = APIRouter(prefix="/cal", tags=["calibration"])


# TODO: Move to config
CAL_REGISTRY_DB_PATH = os.getenv(
    "DSA110_CAL_REGISTRY_DB_PATH",
    "/data/dsa110-contimg/state/cal_registry.sqlite3"
)


@router.get("/{encoded_path:path}")
async def get_cal_table_detail(encoded_path: str):
    """Get calibration table details."""
    cal_path = unquote(encoded_path)
    
    try:
        if not os.path.exists(CAL_REGISTRY_DB_PATH):
            raise HTTPException(
                status_code=503,
                detail=db_unavailable("cal_registry").to_dict(),
            )
        
        conn = sqlite3.connect(CAL_REGISTRY_DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM caltables WHERE path = ?",
            (cal_path,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=internal_error(f"Calibration table not found: {cal_path}").to_dict(),
            )
        
        return {
            "path": row["path"],
            "table_type": row["table_type"],
            "set_name": safe_row_get(row, "set_name"),
            "cal_field": safe_row_get(row, "cal_field"),
            "refant": safe_row_get(row, "refant"),
            "created_at": (
                datetime.fromtimestamp(row["created_at"])
                if safe_row_get(row, "created_at") else None
            ),
            "source_ms_path": safe_row_get(row, "source_ms_path"),
            "status": safe_row_get(row, "status"),
            "notes": safe_row_get(row, "notes"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=internal_error(f"Failed to retrieve cal table: {str(e)}").to_dict(),
        )
