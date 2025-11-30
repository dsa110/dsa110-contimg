"""
Calibration routes.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException

from ..exceptions import (
    RecordNotFoundError,
    DatabaseConnectionError,
    DatabaseQueryError,
)
from ..repositories import safe_row_get

router = APIRouter(prefix="/cal", tags=["calibration"])


# TODO: Move to config
CAL_REGISTRY_DB_PATH = os.getenv(
    "DSA110_CAL_REGISTRY_DB_PATH",
    "/data/dsa110-contimg/state/cal_registry.sqlite3"
)


@router.get("/{encoded_path:path}")
async def get_cal_table_detail(encoded_path: str):
    """
    Get calibration table details.
    
    Raises:
        DatabaseConnectionError: If cal registry database is unavailable
        RecordNotFoundError: If calibration table is not found
        DatabaseQueryError: If query fails
    """
    cal_path = unquote(encoded_path)
    
    if not os.path.exists(CAL_REGISTRY_DB_PATH):
        raise DatabaseConnectionError(
            "cal_registry",
            "Database file does not exist",
        )
    
    try:
        conn = sqlite3.connect(CAL_REGISTRY_DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM caltables WHERE path = ?",
            (cal_path,)
        )
        row = cursor.fetchone()
        conn.close()
    except sqlite3.Error as e:
        raise DatabaseQueryError("cal_table_lookup", str(e))
    
    if not row:
        raise RecordNotFoundError("CalibrationTable", cal_path)
    
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
