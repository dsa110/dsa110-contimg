"""Catalog-related API routes extracted from routes.py."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


@router.get("/catalog/overlay")
def get_catalog_overlay(
    ra: float = Query(..., description="RA center in degrees"),
    dec: float = Query(..., description="Dec center in degrees"),
    radius: float = Query(..., description="Search radius in degrees"),
    catalog: str = Query("all", description="Catalog type: nvss, vlass, first, or all"),
):
    """Get catalog sources for overlay on images."""
    from dsa110_contimg.catalog.query import query_sources

    try:
        if catalog == "all":
            df = query_sources(catalog_type="master", ra_center=ra, dec_center=dec, radius_deg=radius)
        else:
            df = query_sources(catalog_type=catalog.lower(), ra_center=ra, dec_center=dec, radius_deg=radius)
        sources = []
        for _, row in df.iterrows():
            sources.append(
                {
                    "ra_deg": float(row.get("ra_deg", 0)),
                    "dec_deg": float(row.get("dec_deg", 0)),
                    "flux_mjy": float(row.get("flux_mjy", 0)) if "flux_mjy" in row else None,
                    "source_id": str(row.get("source_id", "")) if "source_id" in row else None,
                    "catalog_type": str(row.get("catalog_type", catalog)) if "catalog_type" in row else catalog,
                }
            )
        return {"sources": sources, "count": len(sources), "ra_center": ra, "dec_center": dec, "radius_deg": radius}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to query catalog: {str(e)}")

