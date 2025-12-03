"""
Measurement Set routes.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import unquote

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..dependencies import get_async_ms_service
from ..exceptions import RecordNotFoundError
from ..schemas import (
    MSDetailResponse, 
    ProvenanceResponse,
    AntennaInfo,
    AntennaLayoutResponse,
)
from ..services.async_services import AsyncMSService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ms", tags=["measurement-sets"])


@router.get("/{encoded_path:path}/metadata", response_model=MSDetailResponse)
async def get_ms_metadata(
    encoded_path: str,
    service: AsyncMSService = Depends(get_async_ms_service),
):
    """
    Get metadata for a Measurement Set.
    
    The path should be URL-encoded.
    
    Raises:
        RecordNotFoundError: If MS is not found
    """
    ms_path = unquote(encoded_path)
    
    ms_meta = await service.get_ms_metadata(ms_path)
    if not ms_meta:
        raise RecordNotFoundError("MeasurementSet", ms_path)
    
    ra, dec = service.get_pointing(ms_meta)
    
    return MSDetailResponse(
        path=ms_meta.path,
        pointing_ra_deg=ra,
        pointing_dec_deg=dec,
        calibrator_matches=ms_meta.calibrator_tables,
        qa_grade=ms_meta.qa_grade,
        qa_summary=ms_meta.qa_summary,
        run_id=ms_meta.run_id,
        created_at=ms_meta.created_at,
    )


@router.get("/{encoded_path:path}/calibrator-matches")
async def get_ms_calibrator_matches(
    encoded_path: str,
    service: AsyncMSService = Depends(get_async_ms_service),
):
    """
    Get calibrator matches for a Measurement Set.
    
    Raises:
        RecordNotFoundError: If MS is not found
    """
    ms_path = unquote(encoded_path)
    
    ms_meta = await service.get_ms_metadata(ms_path)
    if not ms_meta:
        raise RecordNotFoundError("MeasurementSet", ms_path)
    
    return {
        "ms_path": ms_path,
        "matches": ms_meta.calibrator_tables or [],
    }


@router.get("/{encoded_path:path}/provenance", response_model=ProvenanceResponse)
async def get_ms_provenance(
    encoded_path: str,
    service: AsyncMSService = Depends(get_async_ms_service),
):
    """
    Get provenance information for a Measurement Set.
    
    Raises:
        RecordNotFoundError: If MS is not found
    """
    ms_path = unquote(encoded_path)
    
    ms_meta = await service.get_ms_metadata(ms_path)
    if not ms_meta:
        raise RecordNotFoundError("MeasurementSet", ms_path)
    
    ra, dec = service.get_pointing(ms_meta)
    cal_table = service.get_primary_cal_table(ms_meta)
    links = service.build_provenance_links(ms_meta)
    
    return ProvenanceResponse(
        run_id=ms_meta.run_id,
        ms_path=ms_path,
        cal_table=cal_table,
        pointing_ra_deg=ra,
        pointing_dec_deg=dec,
        qa_grade=ms_meta.qa_grade,
        qa_summary=ms_meta.qa_summary,
        logs_url=links["logs_url"],
        qa_url=links["qa_url"],
        ms_url=links["ms_url"],
        image_url=links["image_url"],
        created_at=ms_meta.created_at,
    )


# =============================================================================
# Visibility Raster Plot Endpoint (casangi integration)
# =============================================================================

def _is_casagui_available() -> bool:
    """Check if casagui is installed and importable."""
    try:
        import casagui  # noqa: F401
        return True
    except ImportError:
        return False


def _generate_raster_plot(
    ms_path: str,
    xaxis: str,
    yaxis: str,
    colormap: str,
    width: int,
    height: int,
    spw: Optional[int] = None,
    antenna: Optional[str] = None,
) -> bytes:
    """
    Generate a visibility raster plot as PNG bytes.
    
    Uses casagui.apps.MsRaster if available, otherwise falls back to
    matplotlib-based rendering.
    
    Args:
        ms_path: Path to the Measurement Set
        xaxis: X-axis dimension ('time', 'baseline', 'frequency')
        yaxis: Visibility component ('amp', 'phase', 'real', 'imag')
        colormap: Matplotlib/Bokeh colormap name
        width: Plot width in pixels
        height: Plot height in pixels
        spw: Spectral window to plot (None=all)
        antenna: Antenna selection string
        
    Returns:
        PNG image bytes
    """
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    from casacore.tables import table
    
    # Open MS and read data
    ms = table(ms_path, readonly=True)
    try:
        # Get time, antenna1, antenna2 for baseline info
        times = ms.getcol('TIME')
        ant1 = ms.getcol('ANTENNA1')
        ant2 = ms.getcol('ANTENNA2')
        
        # Try to read corrected data first, fall back to data
        try:
            data = ms.getcol('CORRECTED_DATA')
        except RuntimeError:
            data = ms.getcol('DATA')
        
        # Get flags
        try:
            flags = ms.getcol('FLAG')
        except RuntimeError:
            flags = np.zeros(data.shape, dtype=bool)
    finally:
        ms.close()
    
    # Apply flags
    data = np.ma.masked_array(data, mask=flags)
    
    # Calculate visibility component
    if yaxis == 'amp':
        vis = np.abs(data)
        ylabel = 'Amplitude'
    elif yaxis == 'phase':
        vis = np.angle(data, deg=True)
        ylabel = 'Phase (deg)'
    elif yaxis == 'real':
        vis = data.real
        ylabel = 'Real'
    elif yaxis == 'imag':
        vis = data.imag
        ylabel = 'Imaginary'
    else:
        vis = np.abs(data)
        ylabel = 'Amplitude'
    
    # Average over polarizations (assume last axis)
    vis_avg = np.ma.mean(vis, axis=-1)
    
    # Create figure
    dpi = 100
    fig, ax = plt.subplots(figsize=(width / dpi, height / dpi), dpi=dpi)
    
    if xaxis == 'time':
        # Average over frequency for time plot
        y_data = np.ma.mean(vis_avg, axis=1)
        unique_times = np.unique(times)
        
        # Create 2D array: time vs baseline
        n_baselines = len(np.unique(list(zip(ant1, ant2)), axis=0))
        n_times = len(unique_times)
        
        # Simple raster: just reshape if data is uniform
        if len(y_data) == n_times * n_baselines:
            raster = y_data.reshape(n_times, n_baselines)
            im = ax.imshow(
                raster.T, 
                aspect='auto', 
                cmap=colormap,
                origin='lower',
            )
            ax.set_xlabel('Time Index')
            ax.set_ylabel('Baseline Index')
        else:
            # Scatter plot fallback
            ax.scatter(range(len(y_data)), y_data, s=1, alpha=0.5)
            ax.set_xlabel('Sample Index')
            ax.set_ylabel(ylabel)
            
    elif xaxis == 'frequency':
        # Average over time/baseline for frequency plot
        y_data = np.ma.mean(vis_avg, axis=0)
        ax.plot(range(len(y_data)), y_data, '-', linewidth=0.5)
        ax.set_xlabel('Channel')
        ax.set_ylabel(ylabel)
        
    elif xaxis == 'baseline':
        # Average over time and frequency
        y_data = np.ma.mean(vis_avg, axis=1)
        baselines = ant1 * 1000 + ant2  # Simple baseline encoding
        unique_bl = np.unique(baselines)
        
        # Average per baseline
        bl_avg = []
        for bl in unique_bl:
            mask = baselines == bl
            bl_avg.append(np.ma.mean(y_data[mask]))
        
        ax.bar(range(len(bl_avg)), bl_avg, width=1.0)
        ax.set_xlabel('Baseline Index')
        ax.set_ylabel(ylabel)
    
    ax.set_title(f'{ylabel} vs {xaxis.capitalize()}')
    
    # Add colorbar if we have an image
    if xaxis == 'time' and 'im' in dir():
        plt.colorbar(im, ax=ax, label=ylabel)
    
    plt.tight_layout()
    
    # Save to bytes
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    return buf.getvalue()


@router.get("/{encoded_path:path}/raster")
async def get_ms_raster(
    encoded_path: str,
    xaxis: Literal["time", "baseline", "frequency"] = Query(
        "time", description="X-axis dimension"
    ),
    yaxis: Literal["amp", "phase", "real", "imag"] = Query(
        "amp", description="Visibility component to plot"
    ),
    colormap: str = Query("viridis", description="Colormap name"),
    width: int = Query(800, ge=200, le=2000, description="Width in pixels"),
    height: int = Query(600, ge=200, le=2000, description="Height in pixels"),
    spw: Optional[int] = Query(None, ge=0, description="Spectral window"),
    antenna: Optional[str] = Query(None, description="Antenna selection"),
    service: AsyncMSService = Depends(get_async_ms_service),
) -> StreamingResponse:
    """
    Generate a visibility raster plot for a Measurement Set.
    
    Returns a PNG image showing visibility data (amplitude, phase, real, or
    imaginary part) as a function of time, frequency, or baseline.
    
    This endpoint is useful for quick inspection of MS data quality and
    for identifying RFI, bad antennas, or calibration issues.
    
    Args:
        encoded_path: URL-encoded path to the MS
        xaxis: X-axis dimension (time, baseline, or frequency)
        yaxis: Visibility component (amp, phase, real, or imag)
        colormap: Matplotlib colormap name (default: viridis)
        width: Plot width in pixels (200-2000)
        height: Plot height in pixels (200-2000)
        spw: Spectral window to plot (None for all)
        antenna: Antenna selection string (e.g., '0~10')
        
    Returns:
        PNG image as streaming response
        
    Raises:
        404: MS file not found
        500: Error generating plot
    """
    ms_path = unquote(encoded_path)
    
    valid, error, resolved_path = service.validate_ms_path(ms_path)
    if not valid:
        status_code = 404 if error and "not found" in (error or "").lower() else 400
        raise HTTPException(status_code=status_code, detail=error or "Invalid MS path")
    
    try:
        png_bytes = _generate_raster_plot(
            ms_path=str(resolved_path),
            xaxis=xaxis,
            yaxis=yaxis,
            colormap=colormap,
            width=width,
            height=height,
            spw=spw,
            antenna=antenna,
        )
        
        return StreamingResponse(
            io.BytesIO(png_bytes),
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
                "Content-Disposition": f'inline; filename="raster_{xaxis}_{yaxis}.png"',
            },
        )
        
    except Exception as e:
        logger.exception(f"Error generating raster plot for {ms_path}")
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to generate raster plot: {str(e)}"
        )


# =============================================================================
# Antenna Layout Endpoint
# =============================================================================

def _get_antenna_info(ms_path: str) -> AntennaLayoutResponse:
    """
    Extract antenna positions and flagging statistics from an MS.
    
    Args:
        ms_path: Path to the Measurement Set
        
    Returns:
        AntennaLayoutResponse with positions and stats
    """
    from casacore.tables import table
    
    # Open ANTENNA subtable
    ant_table = table(f"{ms_path}/ANTENNA", readonly=True)
    try:
        names = ant_table.getcol('NAME')
        positions = ant_table.getcol('POSITION')  # ITRF XYZ in meters
    finally:
        ant_table.close()
    
    n_ants = len(names)
    
    # Convert ITRF to local ENU coordinates
    # DSA-110 array center (approximate)
    from dsa110_contimg.utils.constants import DSA110_LATITUDE, DSA110_LONGITUDE
    
    # Earth radius approximation
    R_EARTH = 6370000.0  # meters
    
    # Array center in ITRF (mean of all antenna positions)
    center_xyz = np.mean(positions, axis=0)
    
    # Convert to geodetic (approximate)
    center_lon = np.degrees(np.arctan2(center_xyz[1], center_xyz[0]))
    center_lat = np.degrees(np.arctan2(
        center_xyz[2], 
        np.sqrt(center_xyz[0]**2 + center_xyz[1]**2)
    ))
    
    # Convert each antenna to local ENU relative to center
    # Simplified conversion (accurate for small arrays)
    cos_lat = np.cos(np.radians(center_lat))
    cos_lon = np.cos(np.radians(center_lon))
    sin_lat = np.sin(np.radians(center_lat))
    sin_lon = np.sin(np.radians(center_lon))
    
    # Rotation matrix from ITRF to ENU
    R = np.array([
        [-sin_lon, cos_lon, 0],
        [-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat],
        [cos_lat * cos_lon, cos_lat * sin_lon, sin_lat]
    ])
    
    # Get flagging statistics from main table
    ms = table(ms_path, readonly=True)
    try:
        ant1 = ms.getcol('ANTENNA1')
        ant2 = ms.getcol('ANTENNA2')
        
        try:
            flags = ms.getcol('FLAG')
            # Calculate flagged fraction per antenna
            flagged_pct = np.zeros(n_ants)
            baseline_count = np.zeros(n_ants, dtype=int)
            
            for i in range(n_ants):
                # Find rows where this antenna is involved
                mask = (ant1 == i) | (ant2 == i)
                if np.any(mask):
                    # Fraction of flagged data for this antenna
                    ant_flags = flags[mask]
                    flagged_pct[i] = 100.0 * np.mean(ant_flags)
                    baseline_count[i] = np.sum(mask)
        except RuntimeError:
            # No FLAG column
            flagged_pct = np.zeros(n_ants)
            baseline_count = np.zeros(n_ants, dtype=int)
            for i in range(n_ants):
                mask = (ant1 == i) | (ant2 == i)
                baseline_count[i] = np.sum(mask)
    finally:
        ms.close()
    
    # Build antenna list
    antennas = []
    for i in range(n_ants):
        # Convert position to ENU
        dx = positions[i] - center_xyz
        enu = R @ dx
        
        antennas.append(AntennaInfo(
            id=i,
            name=str(names[i]),
            x_m=float(enu[0]),  # East
            y_m=float(enu[1]),  # North
            flagged_pct=float(flagged_pct[i]),
            baseline_count=int(baseline_count[i]),
        ))
    
    # Total baselines = n_ants * (n_ants - 1) / 2
    total_baselines = n_ants * (n_ants - 1) // 2
    
    return AntennaLayoutResponse(
        antennas=antennas,
        array_center_lon=float(center_lon),
        array_center_lat=float(center_lat),
        total_baselines=total_baselines,
    )


@router.get("/{encoded_path:path}/antennas", response_model=AntennaLayoutResponse)
async def get_antenna_layout(encoded_path: str) -> AntennaLayoutResponse:
    """
    Get antenna positions and flagging statistics for a Measurement Set.
    
    Returns antenna positions in local ENU coordinates (East-North-Up) relative
    to the array center, along with flagging statistics for each antenna.
    
    This is useful for:
    - Visualizing the array layout
    - Identifying antennas with high flagging rates
    - Debugging antenna-specific issues
    
    Args:
        encoded_path: URL-encoded path to the MS
        
    Returns:
        Antenna positions, names, flagging percentages, and baseline counts
        
    Raises:
        404: MS file not found
        500: Error reading antenna data
    """
    ms_path = unquote(encoded_path)
    
    # Validate MS exists
    if not Path(ms_path).exists():
        raise HTTPException(status_code=404, detail=f"MS not found: {ms_path}")
    
    # Check ANTENNA subtable exists
    if not Path(f"{ms_path}/ANTENNA").exists():
        raise HTTPException(
            status_code=404, 
            detail=f"ANTENNA subtable not found in {ms_path}"
        )
    
    try:
        return _get_antenna_info(ms_path)
    except Exception as e:
        logger.exception(f"Error reading antenna info from {ms_path}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to read antenna information: {str(e)}"
        )
