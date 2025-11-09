"""Telescope utility helper functions for conversion."""
import logging
from typing import Optional
from contextlib import contextmanager

import numpy as np
import astropy.units as u
from astropy.coordinates import EarthLocation

logger = logging.getLogger("dsa110_contimg.conversion.helpers")


def cleanup_casa_file_handles() -> None:
    """Force close any open CASA file handles to prevent locking issues.
    
    This is critical when running parallel MS operations or using tmpfs staging.
    CASA tools can hold file handles open even after operations complete,
    causing file locking errors in subsequent operations.
    """
    try:
        import casatools
        tool_names = ['ms', 'table', 'image', 'msmetadata', 'simulator']
        
        for tool_name in tool_names:
            try:
                tool_factory = getattr(casatools, tool_name, None)
                if tool_factory is not None:
                    tool_instance = tool_factory()
                    if hasattr(tool_instance, 'close'):
                        tool_instance.close()
                    if hasattr(tool_instance, 'done'):
                        tool_instance.done()
            except Exception:
                # Individual tool cleanup failures are non-fatal
                pass
                
        logger.debug("CASA file handles cleanup completed")
    except ImportError:
        # casatools not available - nothing to clean up
        pass
    except Exception as e:
        logger.debug(f"CASA cleanup failed (non-fatal): {e}")


@contextmanager
def casa_operation():
    """Context manager for CASA operations with automatic cleanup.
    
    Ensures CASA file handles are cleaned up after operations complete,
    even if exceptions occur. This prevents file locking issues in parallel
    operations and tmpfs staging scenarios.
    
    Example:
        with casa_operation():
            # CASA operations here
            ms.open("observation.ms")
            # ... do work ...
            ms.close()
        # cleanup_casa_file_handles() is automatically called here
    
    Note:
        This is a best-effort cleanup. Individual tool cleanup failures
        are logged but don't raise exceptions.
    """
    try:
        yield
    finally:
        cleanup_casa_file_handles()


def set_telescope_identity(
    uv,
    name: Optional[str] = None,
    lon_deg: Optional[float] = None,
    lat_deg: Optional[float] = None,
    alt_m: Optional[float] = None,
) -> None:
    """Set a consistent telescope identity and location on a UVData object.

    This writes both name and location metadata in places used by
    pyuvdata and downstream tools:
    - ``uv.telescope_name``
    - ``uv.telescope_location`` (ITRF meters)
    - ``uv.telescope_location_lat_lon_alt`` (radians + meters)
    - ``uv.telescope_location_lat_lon_alt_deg`` (degrees + meters, when present)
    - If a ``uv.telescope`` sub-object exists (pyuvdata>=3), mirror name and
      location fields there as well.

    Parameters
    ----------
    uv : UVData-like
        The in-memory UVData object.
    name : str, optional
        Telescope name. Defaults to ENV PIPELINE_TELESCOPE_NAME or 'DSA_110'.
    lon_deg, lat_deg, alt_m : float, optional
        Observatory geodetic coordinates (WGS84). If not provided, uses OVRO_LOCATION
        from constants.py (single source of truth for DSA-110 coordinates).
    """
    import os as _os

    # Use constants if coordinates not provided (single source of truth)
    if lon_deg is None or lat_deg is None or alt_m is None:
        from dsa110_contimg.utils.constants import OVRO_LOCATION
        if lon_deg is None:
            lon_deg = OVRO_LOCATION.lon.to(u.deg).value
        if lat_deg is None:
            lat_deg = OVRO_LOCATION.lat.to(u.deg).value
        if alt_m is None:
            alt_m = OVRO_LOCATION.height.to(u.m).value

    tel_name = name or _os.getenv("PIPELINE_TELESCOPE_NAME", "DSA_110")
    try:
        setattr(uv, "telescope_name", tel_name)
    except Exception:
        pass

    try:
        _loc = EarthLocation.from_geodetic(lon=lon_deg * u.deg, lat=lat_deg * u.deg, height=alt_m * u.m)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to construct EarthLocation: %s", exc)
        return

    # Populate top-level ITRF (meters)
    try:
        uv.telescope_location = np.array([
            _loc.x.to_value(u.m),
            _loc.y.to_value(u.m),
            _loc.z.to_value(u.m),
        ], dtype=float)
    except Exception:
        pass

    # Populate geodetic lat/lon/alt in radians/meters if available
    try:
        uv.telescope_location_lat_lon_alt = (
            float(_loc.lat.to_value(u.rad)),
            float(_loc.lon.to_value(u.rad)),
            float(_loc.height.to_value(u.m)),
        )
    except Exception:
        pass
    # And in degrees where convenient
    try:
        uv.telescope_location_lat_lon_alt_deg = (
            float(_loc.lat.to_value(u.deg)),
            float(_loc.lon.to_value(u.deg)),
            float(_loc.height.to_value(u.m)),
        )
    except Exception:
        pass

    # Mirror onto uv.telescope sub-object when present
    tel = getattr(uv, "telescope", None)
    if tel is not None:
        try:
            setattr(tel, "name", tel_name)
        except Exception:
            pass
        try:
            setattr(tel, "location", np.array([
                _loc.x.to_value(u.m),
                _loc.y.to_value(u.m),
                _loc.z.to_value(u.m),
            ], dtype=float))
        except Exception:
            pass
        try:
            setattr(tel, "location_lat_lon_alt", (
                float(_loc.lat.to_value(u.rad)),
                float(_loc.lon.to_value(u.rad)),
                float(_loc.height.to_value(u.m)),
            ))
        except Exception:
            pass
        try:
            setattr(tel, "location_lat_lon_alt_deg", (
                float(_loc.lat.to_value(u.deg)),
                float(_loc.lon.to_value(u.deg)),
                float(_loc.height.to_value(u.m)),
            ))
        except Exception:
            pass

    logger.debug(
        "Set telescope identity: %s @ (lon,lat,alt)=(%.4f, %.4f, %.1f)",
        tel_name, lon_deg, lat_deg, alt_m,
    )

