"""
FITS file parsing service.

This module provides a dedicated service for parsing FITS file metadata,
extracting header information, and handling FITS-specific operations.

This separates FITS parsing logic from repositories, following the
Single Responsibility Principle.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from ..exceptions import FileNotAccessibleError, FITSParsingError

logger = logging.getLogger(__name__)


@dataclass
class FITSMetadata:
    """Extracted FITS file metadata."""

    # File info
    path: str
    exists: bool = True
    size_bytes: int = 0

    # Observation info
    object_name: Optional[str] = None
    observer: Optional[str] = None
    telescope: Optional[str] = None
    instrument: Optional[str] = None
    date_obs: Optional[str] = None

    # Spatial info
    ra_deg: Optional[float] = None
    dec_deg: Optional[float] = None
    naxis1: Optional[int] = None
    naxis2: Optional[int] = None
    cdelt1: Optional[float] = None  # degrees/pixel
    cdelt2: Optional[float] = None
    crpix1: Optional[float] = None
    crpix2: Optional[float] = None
    crval1: Optional[float] = None
    crval2: Optional[float] = None
    ctype1: Optional[str] = None
    ctype2: Optional[str] = None

    # Frequency info
    freq_hz: Optional[float] = None
    bandwidth_hz: Optional[float] = None
    restfreq: Optional[float] = None

    # Beam info
    bmaj: Optional[float] = None  # degrees
    bmin: Optional[float] = None  # degrees
    bpa: Optional[float] = None  # degrees

    # Data info
    bunit: Optional[str] = None
    btype: Optional[str] = None

    # Statistics (optional, computed if requested)
    data_min: Optional[float] = None
    data_max: Optional[float] = None
    data_mean: Optional[float] = None
    data_rms: Optional[float] = None

    @property
    def cellsize_arcsec(self) -> Optional[float]:
        """Get cell size in arcseconds (from cdelt)."""
        if self.cdelt1:
            return abs(self.cdelt1) * 3600.0
        return None

    @property
    def beam_major_arcsec(self) -> Optional[float]:
        """Get beam major axis in arcseconds."""
        if self.bmaj:
            return self.bmaj * 3600.0
        return None

    @property
    def beam_minor_arcsec(self) -> Optional[float]:
        """Get beam minor axis in arcseconds."""
        if self.bmin:
            return self.bmin * 3600.0
        return None

    @property
    def freq_ghz(self) -> Optional[float]:
        """Get frequency in GHz."""
        if self.freq_hz:
            return self.freq_hz / 1e9
        return None

    @property
    def bandwidth_mhz(self) -> Optional[float]:
        """Get bandwidth in MHz."""
        if self.bandwidth_hz:
            return self.bandwidth_hz / 1e6
        return None


class FITSParsingService:
    """
    Service for parsing FITS files and extracting metadata.

    This service encapsulates all FITS-related operations, providing
    a clean interface for the rest of the application.
    """

    # Standard FITS header keywords to extract
    HEADER_KEYS = {
        # Observation
        "OBJECT": "object_name",
        "OBSERVER": "observer",
        "TELESCOP": "telescope",
        "INSTRUME": "instrument",
        "DATE-OBS": "date_obs",
        # Spatial
        "NAXIS1": "naxis1",
        "NAXIS2": "naxis2",
        "CDELT1": "cdelt1",
        "CDELT2": "cdelt2",
        "CRPIX1": "crpix1",
        "CRPIX2": "crpix2",
        "CRVAL1": "crval1",
        "CRVAL2": "crval2",
        "CTYPE1": "ctype1",
        "CTYPE2": "ctype2",
        # Frequency
        "RESTFREQ": "restfreq",
        "CRVAL3": "freq_hz",  # Often frequency axis
        # Beam
        "BMAJ": "bmaj",
        "BMIN": "bmin",
        "BPA": "bpa",
        # Data
        "BUNIT": "bunit",
        "BTYPE": "btype",
    }

    def __init__(self):
        """Initialize the FITS parsing service."""
        self._fits = None

    def _get_fits_module(self):
        """Lazy-load astropy.io.fits module."""
        if self._fits is None:
            try:
                from astropy.io import fits

                self._fits = fits
            except ImportError as e:
                raise FITSParsingError("unknown", f"astropy not available: {e}")
        return self._fits

    def parse_header(self, fits_path: str) -> FITSMetadata:
        """
        Parse FITS file header and extract metadata.

        Args:
            fits_path: Path to the FITS file

        Returns:
            FITSMetadata with extracted information

        Raises:
            FileNotAccessibleError: If file doesn't exist or can't be read
            FITSParsingError: If FITS parsing fails
        """
        path = Path(fits_path)

        # Check file exists
        if not path.exists():
            raise FileNotAccessibleError(fits_path, "read")

        metadata = FITSMetadata(
            path=fits_path,
            exists=True,
            size_bytes=path.stat().st_size,
        )

        try:
            fits = self._get_fits_module()

            with fits.open(fits_path, memmap=True) as hdul:
                header = hdul[0].header

                # Extract standard keywords
                for fits_key, attr_name in self.HEADER_KEYS.items():
                    if fits_key in header:
                        setattr(metadata, attr_name, header[fits_key])

                # Try to get RA/Dec from header
                metadata.ra_deg, metadata.dec_deg = self._extract_coordinates(header)

                # Try to get frequency from various sources
                if metadata.freq_hz is None:
                    metadata.freq_hz = self._extract_frequency(header)

                # Try to get bandwidth
                metadata.bandwidth_hz = self._extract_bandwidth(header)

            return metadata

        except FileNotAccessibleError:
            raise
        except (OSError, ValueError, KeyError) as e:
            raise FITSParsingError(fits_path, str(e))

    def parse_with_stats(self, fits_path: str) -> FITSMetadata:
        """
        Parse FITS file and compute data statistics.

        This is slower than parse_header as it reads the data.

        Args:
            fits_path: Path to the FITS file

        Returns:
            FITSMetadata with header info and data statistics
        """
        metadata = self.parse_header(fits_path)

        try:
            import numpy as np

            fits = self._get_fits_module()

            with fits.open(fits_path, memmap=True) as hdul:
                data = hdul[0].data
                if data is not None:
                    # Flatten and remove NaNs
                    valid_data = data[np.isfinite(data)]
                    if valid_data.size > 0:
                        metadata.data_min = float(np.min(valid_data))
                        metadata.data_max = float(np.max(valid_data))
                        metadata.data_mean = float(np.mean(valid_data))
                        metadata.data_rms = float(np.std(valid_data))

            return metadata

        except (OSError, ValueError) as e:
            logger.warning(f"Failed to compute stats for {fits_path}: {e}")
            return metadata

    def _extract_coordinates(self, header) -> Tuple[Optional[float], Optional[float]]:
        """Extract RA/Dec from FITS header."""
        ra = None
        dec = None

        # Try various coordinate keywords
        for ra_key in ["CRVAL1", "RA", "OBSRA"]:
            if ra_key in header and header[ra_key] is not None:
                ra = float(header[ra_key])
                break

        for dec_key in ["CRVAL2", "DEC", "OBSDEC"]:
            if dec_key in header and header[dec_key] is not None:
                dec = float(header[dec_key])
                break

        # Check if CRVAL1/2 are actually RA/Dec by checking CTYPE
        if "CTYPE1" in header:
            ctype1 = str(header["CTYPE1"]).upper()
            if "RA" not in ctype1 and "GLON" not in ctype1:
                ra = None

        if "CTYPE2" in header:
            ctype2 = str(header["CTYPE2"]).upper()
            if "DEC" not in ctype2 and "GLAT" not in ctype2:
                dec = None

        return ra, dec

    def _extract_frequency(self, header) -> Optional[float]:
        """Extract frequency from FITS header."""
        # Try various frequency keywords
        for freq_key in ["CRVAL3", "FREQ", "RESTFREQ", "OBSFREQ"]:
            if freq_key in header and header[freq_key] is not None:
                try:
                    return float(header[freq_key])
                except (ValueError, TypeError):
                    continue

        return None

    def _extract_bandwidth(self, header) -> Optional[float]:
        """Extract bandwidth from FITS header."""
        for bw_key in ["CDELT3", "BANDWIDTH", "BANDWID"]:
            if bw_key in header and header[bw_key] is not None:
                try:
                    return abs(float(header[bw_key]))
                except (ValueError, TypeError):
                    continue

        return None

    def get_data_slice(self, fits_path: str, channel: int = 0, stokes: int = 0):
        """
        Get a 2D slice of FITS data.

        Args:
            fits_path: Path to FITS file
            channel: Channel index (for 3D+ data)
            stokes: Stokes index (for 4D data)

        Returns:
            2D numpy array, or None if extraction fails
        """
        try:
            fits = self._get_fits_module()

            with fits.open(fits_path, memmap=True) as hdul:
                data = hdul[0].data
                if data is None:
                    return None

                # Handle different dimensionalities
                if data.ndim == 2:
                    return data
                elif data.ndim == 3:
                    return data[channel, :, :]
                elif data.ndim == 4:
                    return data[stokes, channel, :, :]
                else:
                    # Just take first 2D slice
                    while data.ndim > 2:
                        data = data[0]
                    return data

        except (OSError, IndexError, ValueError) as e:
            logger.error(f"Failed to extract data slice from {fits_path}: {e}")
            return None

    def validate_fits(self, fits_path: str) -> Dict[str, Any]:
        """
        Validate a FITS file and return any issues found.

        Args:
            fits_path: Path to FITS file

        Returns:
            Dictionary with validation results:
            - valid: bool
            - errors: List of error messages
            - warnings: List of warning messages
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }

        path = Path(fits_path)

        # Check existence
        if not path.exists():
            result["valid"] = False
            result["errors"].append(f"File does not exist: {fits_path}")
            return result

        # Check readability
        if not path.is_file():
            result["valid"] = False
            result["errors"].append(f"Not a file: {fits_path}")
            return result

        try:
            fits = self._get_fits_module()

            with fits.open(fits_path, memmap=True) as hdul:
                # Check for primary HDU
                if len(hdul) == 0:
                    result["valid"] = False
                    result["errors"].append("No HDUs in FITS file")
                    return result

                header = hdul[0].header
                data = hdul[0].data

                # Check for data
                if data is None:
                    result["warnings"].append("No data in primary HDU")

                # Check for WCS keywords
                has_wcs = "CRVAL1" in header and "CRVAL2" in header
                if not has_wcs:
                    result["warnings"].append("Missing WCS coordinates (CRVAL1/CRVAL2)")

                # Check for beam
                has_beam = "BMAJ" in header and "BMIN" in header
                if not has_beam:
                    result["warnings"].append("Missing beam information (BMAJ/BMIN)")

                # Verify with astropy's verification
                hdul.verify("silentfix")

        except (OSError, ValueError) as e:
            result["valid"] = False
            result["errors"].append(f"FITS parsing error: {str(e)}")

        return result


# =============================================================================
# Module-level convenience functions
# =============================================================================

_fits_service: Optional[FITSParsingService] = None


def get_fits_service() -> FITSParsingService:
    """Get the global FITS parsing service instance."""
    global _fits_service
    if _fits_service is None:
        _fits_service = FITSParsingService()
    return _fits_service


def parse_fits_header(fits_path: str) -> FITSMetadata:
    """
    Convenience function to parse FITS header.

    Args:
        fits_path: Path to FITS file

    Returns:
        FITSMetadata with extracted information
    """
    return get_fits_service().parse_header(fits_path)


def validate_fits_file(fits_path: str) -> Dict[str, Any]:
    """
    Convenience function to validate a FITS file.

    Args:
        fits_path: Path to FITS file

    Returns:
        Validation result dictionary
    """
    return get_fits_service().validate_fits(fits_path)
