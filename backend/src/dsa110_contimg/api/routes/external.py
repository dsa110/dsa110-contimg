"""
External service proxy routes.

Provides backend proxies for external astronomical services to avoid CORS issues
in the frontend. This includes:

- CDS Sesame name resolver (SIMBAD, NED, VizieR)
- Aladin HiPS tile services

These proxies allow the frontend to resolve object names and display sky images
without running into browser CORS restrictions.
"""

from __future__ import annotations

import logging
from typing import Literal, Optional
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/external", tags=["external"])

# =============================================================================
# Configuration
# =============================================================================

# CDS Sesame service URL
SESAME_BASE_URL = "https://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame"

# Timeouts for external requests (connect, read, write, pool)
EXTERNAL_TIMEOUT = httpx.Timeout(5.0, read=15.0)

# =============================================================================
# Pydantic Models
# =============================================================================


class SesameResult(BaseModel):
    """Result from Sesame name resolution."""

    object_name: str = Field(..., description="Original object name queried")
    ra: float = Field(..., description="Right Ascension in degrees")
    dec: float = Field(..., description="Declination in degrees")
    service: str = Field(..., description="Service that resolved the name (simbad, ned, vizier)")
    raw_response: Optional[str] = Field(None, description="Raw Sesame response for debugging")


class SesameError(BaseModel):
    """Error response from Sesame resolution."""

    error: str
    object_name: str
    service: str


# =============================================================================
# Sesame Name Resolver Proxy
# =============================================================================


@router.get("/sesame/resolve", response_model=SesameResult)
async def resolve_object_name(
    name: str = Query(..., min_length=1, description="Astronomical object name to resolve"),
    service: Literal["all", "simbad", "ned", "vizier"] = Query(
        "all", description="Name resolution service to use"
    ),
):
    """
    Resolve an astronomical object name to coordinates using CDS Sesame.

    This endpoint proxies requests to the CDS Sesame service to avoid CORS
    issues in the browser. Sesame queries SIMBAD, NED, and VizieR catalogs.

    Args:
        name: Object name (e.g., "M31", "3C286", "PSR J0534+2200")
        service: Service to query ("all", "simbad", "ned", "vizier")

    Returns:
        Resolved coordinates (RA, Dec in degrees) and service used

    Raises:
        HTTPException: If object cannot be resolved or service is unavailable
    """
    # Map service to Sesame code
    service_code = {
        "all": "A",
        "simbad": "S",
        "ned": "N",
        "vizier": "V",
    }.get(service, "A")

    # Build Sesame URL
    # Format: https://cdsweb.u-strasbg.fr/cgi-bin/nph-sesame/-oI/A?object_name
    url = f"{SESAME_BASE_URL}/-oI/{service_code}?{quote(name.strip())}"

    logger.debug(f"Sesame query: {url}")

    try:
        async with httpx.AsyncClient(timeout=EXTERNAL_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            text = response.text

    except httpx.TimeoutException:
        logger.warning(f"Sesame timeout resolving '{name}'")
        raise HTTPException(
            status_code=504,
            detail=f"Timeout connecting to CDS Sesame service. Please try again.",
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Sesame HTTP error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"CDS Sesame service returned error: {e.response.status_code}",
        )
    except httpx.RequestError as e:
        logger.error(f"Sesame request error: {e}")
        raise HTTPException(
            status_code=502,
            detail="Could not connect to CDS Sesame service. The service may be down.",
        )

    # Parse Sesame response
    # Format includes lines like:
    # %J 83.63308 +22.01450 = 05 34 31.94 +22 00 52.2
    # Also includes service info like:
    # #=S (SIMBAD resolved)
    ra, dec = None, None
    resolved_service = service

    for line in text.split("\n"):
        line = line.strip()

        # Check for resolved service indicator
        if line.startswith("#=S"):
            resolved_service = "simbad"
        elif line.startswith("#=N"):
            resolved_service = "ned"
        elif line.startswith("#=V"):
            resolved_service = "vizier"

        # Look for coordinate line
        if line.startswith("%J"):
            # Parse: %J RA DEC = HH MM SS.ss +DD MM SS.s
            parts = line.split()
            if len(parts) >= 3:
                try:
                    ra = float(parts[1])
                    dec = float(parts[2])
                except ValueError:
                    continue

    if ra is None or dec is None:
        # Check for specific error messages
        if "#!E" in text or "Nothing found" in text:
            raise HTTPException(
                status_code=404,
                detail=f"Object '{name}' not found. Please check the name and try again.",
            )
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse coordinates from Sesame response for '{name}'.",
        )

    return SesameResult(
        object_name=name,
        ra=ra,
        dec=dec,
        service=resolved_service,
        raw_response=text[:500] if len(text) < 1000 else None,  # Include raw for debugging
    )


# =============================================================================
# Aladin/HiPS Proxy (for future use)
# =============================================================================


@router.get("/aladin/status")
async def check_aladin_status():
    """
    Check if Aladin Lite CDN is accessible.

    Returns status of the CDS Aladin Lite resources.
    """
    try:
        async with httpx.AsyncClient(timeout=EXTERNAL_TIMEOUT) as client:
            # Check if Aladin Lite JS is accessible
            response = await client.head("https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.min.js")
            if response.status_code == 200:
                return {"status": "ok", "message": "Aladin Lite CDN is accessible"}
            return {"status": "degraded", "message": f"Aladin CDN returned {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"Cannot reach Aladin CDN: {str(e)}"}
