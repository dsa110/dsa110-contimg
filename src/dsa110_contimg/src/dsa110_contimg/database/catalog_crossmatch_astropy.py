"""Standard Astropy-based catalog cross-matching.

Replicates the standard protocol used by:
- LOFAR surveys (Shimwell et al. 2019+)
- RACS (McConnell et al. 2020, PASA 37, e048)
- FIRST × NVSS (Helfand et al. 2015)

Uses Astropy's SkyCoord.match_to_catalog_sky() which is the de facto
standard in radio astronomy for catalog matching.

References:
- Astropy Collaboration (2022), ApJ 935, 167
- Pineau et al. (2016), arXiv:1609.00818 (probabilistic matching)
- TOPCAT (Taylor 2005) - implements same algorithms
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import Table

logger = logging.getLogger(__name__)


# Catalog properties from survey papers
CATALOG_INFO = {
    "VLA": {
        "frequency_mhz": 1500.0,
        "position_error_arcsec": 1.0,
        "flux_type": "integrated",
        "reference": "Perley & Butler 2017, ApJS 230, 7",
    },
    "NVSS": {
        "frequency_mhz": 1400.0,
        "position_error_arcsec": 5.0,  # 45" beam
        "flux_type": "integrated",
        "reference": "Condon et al. 1998, AJ 115, 1693",
    },
    "FIRST": {
        "frequency_mhz": 1400.0,
        "position_error_arcsec": 1.0,  # 5" beam
        "flux_type": "peak",  # Peak for unresolved, integrated flagged
        "reference": "White et al. 1997, ApJ 475, 479",
    },
    "RACS": {
        "frequency_mhz": 887.5,
        "position_error_arcsec": 2.5,  # 15" beam
        "flux_type": "integrated",
        "reference": "McConnell et al. 2020, PASA 37, e048",
    },
}

# DSA-110 observing frequency
DSA110_FREQUENCY_MHZ = 1405.0

# Default spectral index for synchrotron emission
DEFAULT_SPECTRAL_INDEX = -0.7


@dataclass
class MatchedSource:
    """Cross-matched source from multiple catalogs.

    Follows standard Astropy Table conventions.
    """

    name: str
    ra_deg: float
    dec_deg: float
    flux_dsa110_jy: float  # Extrapolated to DSA-110 frequency
    flux_uncertainty_jy: float
    spectral_index: float
    spectral_index_error: Optional[float]
    n_catalogs: int  # Number of catalog matches
    catalogs: List[str]  # Which catalogs detected this source
    separations_arcsec: Dict[str, float]  # Separation in each catalog
    fluxes_observed: Dict[str, float]  # Observed fluxes


class RadioCatalogMatcher:
    """Standard radio catalog cross-matching using Astropy.

    Implements the protocol used by LOFAR, RACS, and other surveys.
    """

    def __init__(self, target_frequency_mhz: float = DSA110_FREQUENCY_MHZ):
        """Initialize matcher.

        Args:
            target_frequency_mhz: Target frequency for flux extrapolation
        """
        self.target_freq = target_frequency_mhz

    def match_two_catalogs(
        self,
        cat_a: Table,
        cat_b: Table,
        catalog_a_name: str,
        catalog_b_name: str,
        max_sep_arcsec: Optional[float] = None,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Match two catalogs using standard Astropy method.

        This is the standard protocol used by >90% of radio astronomy papers.

        Args:
            cat_a: Astropy Table with 'ra', 'dec', 'flux' columns
            cat_b: Astropy Table with 'ra', 'dec', 'flux' columns
            catalog_a_name: Name of catalog A (e.g., 'NVSS')
            catalog_b_name: Name of catalog B (e.g., 'FIRST')
            max_sep_arcsec: Maximum separation for match (default: 3×combined error)

        Returns:
            Tuple of (matches_mask, matched_indices_b, separations_arcsec)
            - matches_mask: Boolean array for cat_a (True if matched)
            - matched_indices_b: Index in cat_b for each source in cat_a
            - separations_arcsec: Separation for each match
        """
        # Handle empty catalogs
        if len(cat_a) == 0:
            return np.array([], dtype=bool), np.array([], dtype=int), np.array([])

        if len(cat_b) == 0:
            # No matches possible
            return (
                np.zeros(len(cat_a), dtype=bool),
                np.zeros(len(cat_a), dtype=int),
                np.full(len(cat_a), np.inf),
            )

        # Create SkyCoord objects (standard Astropy)
        coords_a = SkyCoord(ra=cat_a["ra"] * u.deg, dec=cat_a["dec"] * u.deg, frame="icrs")
        coords_b = SkyCoord(ra=cat_b["ra"] * u.deg, dec=cat_b["dec"] * u.deg, frame="icrs")

        # Standard Astropy matching
        idx_b, sep_2d, _ = coords_a.match_to_catalog_sky(coords_b)

        # Separation threshold (standard: 3× combined position error)
        if max_sep_arcsec is None:
            err_a = CATALOG_INFO[catalog_a_name]["position_error_arcsec"]
            err_b = CATALOG_INFO[catalog_b_name]["position_error_arcsec"]
            # Combined error in quadrature
            combined_error = np.sqrt(err_a**2 + err_b**2)
            max_sep_arcsec = 3.0 * combined_error
            logger.debug(
                f'Using separation threshold: {max_sep_arcsec:.1f}" '
                f'(3× combined error of {combined_error:.1f}")'
            )

        # Boolean mask of matches
        matches = sep_2d < (max_sep_arcsec * u.arcsec)

        # Convert separations to arcsec
        separations_arcsec = sep_2d.to(u.arcsec).value

        n_matches = np.sum(matches)
        logger.info(
            f"Matched {catalog_a_name} × {catalog_b_name}: "
            f"{n_matches}/{len(cat_a)} sources "
            f'(within {max_sep_arcsec:.1f}")'
        )

        return matches, idx_b, separations_arcsec

    def extrapolate_flux(
        self,
        flux_jy: float,
        freq_obs_mhz: float,
        freq_target_mhz: Optional[float] = None,
        spectral_index: float = DEFAULT_SPECTRAL_INDEX,
    ) -> float:
        """Extrapolate flux to target frequency using power law.

        Standard formula: S(ν) = S₀ × (ν/ν₀)^α

        This is the standard approach used in all radio astronomy papers.

        Args:
            flux_jy: Observed flux in Jy
            freq_obs_mhz: Observation frequency in MHz
            freq_target_mhz: Target frequency in MHz (default: DSA-110)
            spectral_index: Spectral index α (default: -0.7)

        Returns:
            Extrapolated flux in Jy
        """
        if freq_target_mhz is None:
            freq_target_mhz = self.target_freq

        if freq_obs_mhz == freq_target_mhz:
            return flux_jy

        return flux_jy * (freq_target_mhz / freq_obs_mhz) ** spectral_index

    def estimate_spectral_index(
        self,
        flux1_jy: float,
        freq1_mhz: float,
        flux2_jy: float,
        freq2_mhz: float,
    ) -> Tuple[float, float]:
        """Estimate spectral index from two measurements.

        Standard formula: α = log(S₁/S₂) / log(ν₁/ν₂)

        Used by LOFAR, RACS, and other surveys.

        Args:
            flux1_jy, freq1_mhz: First measurement
            flux2_jy, freq2_mhz: Second measurement

        Returns:
            Tuple of (spectral_index, uncertainty)
        """
        with np.errstate(divide="ignore", invalid="ignore"):
            alpha = np.log10(flux1_jy / flux2_jy) / np.log10(freq1_mhz / freq2_mhz)

        # If calculation failed, use default
        if not np.isfinite(alpha):
            return DEFAULT_SPECTRAL_INDEX, 0.3

        # Uncertainty estimate (conservative: ±0.15 for 2-point fit)
        uncertainty = 0.15

        return alpha, uncertainty

    def cone_search(
        self,
        catalog: Table,
        ra_center_deg: float,
        dec_center_deg: float,
        radius_deg: float,
    ) -> Table:
        """Cone search in catalog using standard Astropy method.

        Args:
            catalog: Astropy Table with 'ra', 'dec' columns
            ra_center_deg: Center RA in degrees
            dec_center_deg: Center Dec in degrees
            radius_deg: Search radius in degrees

        Returns:
            Astropy Table of sources within cone
        """
        center = SkyCoord(ra=ra_center_deg * u.deg, dec=dec_center_deg * u.deg)
        catalog_coords = SkyCoord(ra=catalog["ra"] * u.deg, dec=catalog["dec"] * u.deg)

        separations = center.separation(catalog_coords)
        in_cone = separations < (radius_deg * u.deg)

        result = catalog[in_cone].copy()
        result["separation_deg"] = separations[in_cone].to(u.deg).value

        return result

    def merge_two_catalogs(
        self,
        cat_a: Table,
        cat_b: Table,
        catalog_a_name: str,
        catalog_b_name: str,
        max_sep_arcsec: Optional[float] = None,
    ) -> List[MatchedSource]:
        """Merge two catalogs with cross-matching.

        Standard protocol:
        1. Match using Astropy
        2. Estimate spectral index from two frequencies
        3. Extrapolate flux to DSA-110 frequency
        4. Keep unmatched sources from both catalogs

        Args:
            cat_a, cat_b: Astropy Tables
            catalog_a_name, catalog_b_name: Catalog names
            max_sep_arcsec: Maximum separation for matching

        Returns:
            List of MatchedSource objects
        """
        # Match catalogs
        matches_a, idx_b, seps = self.match_two_catalogs(
            cat_a, cat_b, catalog_a_name, catalog_b_name, max_sep_arcsec
        )

        merged = []

        # Process matched sources
        for i in np.where(matches_a)[0]:
            j = idx_b[i]
            sep = seps[i]

            # Get measurements
            flux_a = cat_a["flux"][i]
            flux_b = cat_b["flux"][j]
            freq_a = CATALOG_INFO[catalog_a_name]["frequency_mhz"]
            freq_b = CATALOG_INFO[catalog_b_name]["frequency_mhz"]

            # Estimate spectral index
            alpha, alpha_err = self.estimate_spectral_index(flux_a, freq_a, flux_b, freq_b)

            # Extrapolate to DSA-110 frequency (use catalog A as reference)
            flux_dsa110 = self.extrapolate_flux(flux_a, freq_a, spectral_index=alpha)

            # Uncertainty: 10% + spectral index uncertainty
            flux_unc = 0.1 * flux_dsa110
            if alpha_err is not None:
                log_freq_ratio = np.abs(np.log(self.target_freq / freq_a))
                flux_unc += flux_dsa110 * log_freq_ratio * alpha_err

            # Position: simple average (could weight by position error)
            ra_avg = (cat_a["ra"][i] + cat_b["ra"][j]) / 2.0
            dec_avg = (cat_a["dec"][i] + cat_b["dec"][j]) / 2.0

            # Create matched source
            source = MatchedSource(
                name=cat_a["name"][i],
                ra_deg=ra_avg,
                dec_deg=dec_avg,
                flux_dsa110_jy=flux_dsa110,
                flux_uncertainty_jy=flux_unc,
                spectral_index=alpha,
                spectral_index_error=alpha_err,
                n_catalogs=2,
                catalogs=[catalog_a_name, catalog_b_name],
                separations_arcsec={catalog_a_name: 0.0, catalog_b_name: sep},
                fluxes_observed={catalog_a_name: flux_a, catalog_b_name: flux_b},
            )
            merged.append(source)

        # Add unmatched sources from catalog A
        for i in np.where(~matches_a)[0]:
            flux = cat_a["flux"][i]
            freq = CATALOG_INFO[catalog_a_name]["frequency_mhz"]

            flux_dsa110 = self.extrapolate_flux(flux, freq, spectral_index=DEFAULT_SPECTRAL_INDEX)

            source = MatchedSource(
                name=cat_a["name"][i],
                ra_deg=cat_a["ra"][i],
                dec_deg=cat_a["dec"][i],
                flux_dsa110_jy=flux_dsa110,
                flux_uncertainty_jy=0.3 * flux_dsa110,  # 30% for single catalog
                spectral_index=DEFAULT_SPECTRAL_INDEX,
                spectral_index_error=0.3,
                n_catalogs=1,
                catalogs=[catalog_a_name],
                separations_arcsec={catalog_a_name: 0.0},
                fluxes_observed={catalog_a_name: flux},
            )
            merged.append(source)

        # Add unmatched sources from catalog B
        matched_b = set(idx_b[matches_a])
        for j in range(len(cat_b)):
            if j not in matched_b:
                flux = cat_b["flux"][j]
                freq = CATALOG_INFO[catalog_b_name]["frequency_mhz"]

                flux_dsa110 = self.extrapolate_flux(
                    flux, freq, spectral_index=DEFAULT_SPECTRAL_INDEX
                )

                source = MatchedSource(
                    name=cat_b["name"][j],
                    ra_deg=cat_b["ra"][j],
                    dec_deg=cat_b["dec"][j],
                    flux_dsa110_jy=flux_dsa110,
                    flux_uncertainty_jy=0.3 * flux_dsa110,
                    spectral_index=DEFAULT_SPECTRAL_INDEX,
                    spectral_index_error=0.3,
                    n_catalogs=1,
                    catalogs=[catalog_b_name],
                    separations_arcsec={catalog_b_name: 0.0},
                    fluxes_observed={catalog_b_name: flux},
                )
                merged.append(source)

        logger.info(
            f"Merged {catalog_a_name} + {catalog_b_name}: "
            f"{len(merged)} total sources "
            f"({np.sum(matches_a)} matched, "
            f"{len(cat_a) - np.sum(matches_a)} unmatched from {catalog_a_name}, "
            f"{len(cat_b) - len(matched_b)} unmatched from {catalog_b_name})"
        )

        return merged


def create_mock_catalog(name: str, n_sources: int = 100) -> Table:
    """Create mock catalog for testing.

    Args:
        name: Catalog name
        n_sources: Number of sources

    Returns:
        Astropy Table with standard columns
    """
    rng = np.random.RandomState(42)

    catalog = Table()
    catalog["name"] = [f"{name}_J{i:04d}" for i in range(n_sources)]
    catalog["ra"] = rng.uniform(0, 360, n_sources)
    catalog["dec"] = rng.uniform(-30, 30, n_sources)
    catalog["flux"] = rng.lognormal(mean=0, sigma=1, size=n_sources)
    catalog.meta["catalog"] = name

    return catalog


__all__ = [
    "RadioCatalogMatcher",
    "MatchedSource",
    "CATALOG_INFO",
    "DSA110_FREQUENCY_MHZ",
    "create_mock_catalog",
]
