"""
Calibration routes.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from urllib.parse import unquote

from fastapi import APIRouter, Depends

from ..database import DatabasePool, get_db_pool
from ..exceptions import (
    RecordNotFoundError,
    DatabaseQueryError,
)
from ..repositories import safe_row_get

router = APIRouter(prefix="/cal", tags=["calibration"])


@router.get("/{encoded_path:path}")
async def get_cal_table_detail(
    encoded_path: str,
    db_pool: DatabasePool = Depends(get_db_pool),
):
    """
    Get calibration table details.
    
    Raises:
        RecordNotFoundError: If calibration table is not found
        DatabaseQueryError: If query fails
    """
    cal_path = unquote(encoded_path)
    
    try:
        async with db_pool.cal_registry_db() as conn:
            cursor = await conn.execute(
                "SELECT * FROM caltables WHERE path = ?",
                (cal_path,)
            )
            row = await cursor.fetchone()
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
