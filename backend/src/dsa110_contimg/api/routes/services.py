"""
Services status routes.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/services", tags=["services"])


@router.get("/status")
async def get_services_status():
    """
    Get health status of all monitored services.

    Performs server-side health checks for all dependent services.
    """
    from ..services_monitor import check_all_services

    results = await check_all_services()

    running_count = sum(1 for r in results if r.status.value == "running")

    return {
        "services": [r.to_dict() for r in results],
        "summary": {
            "total": len(results),
            "running": running_count,
            "stopped": len(results) - running_count,
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/status/{port}")
async def get_service_status_by_port(port: int):
    """
    Get health status of a specific service by port number.
    """
    from ..services_monitor import MONITORED_SERVICES, check_service

    service = next((s for s in MONITORED_SERVICES if s.port == port), None)
    if not service:
        raise HTTPException(
            status_code=404,
            detail={"error": f"No monitored service on port {port}"},
        )

    result = await check_service(service)
    return result.to_dict()
