"""MODEL_DATA validation utilities.

Provides comprehensive validation of MODEL_DATA column to ensure calibration correctness.
Validates MODEL_DATA against catalog information, checks consistency, and verifies
that MODEL_DATA matches the expected calibrator position and flux.
"""

import logging
from typing import Dict, List, Optional, Tuple

import astropy.units as u
import numpy as np

# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path

ensure_casa_path()

from astropy.coordinates import Angle, SkyCoord
import casacore.tables as casatables

table = casatables.table  # noqa: N816

logger = logging.getLogger(__name__)


def validate_model_data_exists(ms_path: str) -> bool:
    """Check if MODEL_DATA column exists in MS.

    Args:
        ms_path: Path to Measurement Set

    Returns:
        True if MODEL_DATA exists, False otherwise
    """
    try:
        with table(ms_path, readonly=True, ack=False) as tb:
            return "MODEL_DATA" in tb.colnames()
    except Exception as e:
        logger.error(f"Error checking MODEL_DATA existence: {e}")
        return False


def validate_model_data_populated(
    ms_path: str, min_fraction: float = 0.01, sample_size: int = 1000
) -> Tuple[bool, Dict]:
    """Validate that MODEL_DATA is populated (not all zeros).

    Args:
        ms_path: Path to Measurement Set
        min_fraction: Minimum fraction of non-zero values required (default: 0.01)
        sample_size: Number of rows to sample for validation (default: 1000)

    Returns:
        Tuple of (is_populated, statistics_dict)
        statistics_dict contains:
            - fraction_nonzero: Fraction of non-zero values
            - max_value: Maximum absolute value
            - mean_value: Mean absolute value
            - n_rows_checked: Number of rows checked
    """
    stats = {
        "fraction_nonzero": 0.0,
        "max_value": 0.0,
        "mean_value": 0.0,
        "n_rows_checked": 0,
    }

    try:
        with table(ms_path, readonly=True, ack=False) as tb:
            n_rows = tb.nrows()
            if n_rows == 0:
                logger.warning("MS has zero rows")
                return False, stats

            # Sample rows for validation (check more than just first 100)
            n_sample = min(sample_size, n_rows)
            start_row = 0
            model_sample = tb.getcol("MODEL_DATA", startrow=start_row, nrow=n_sample)

            # Check if all values are near zero
            abs_values = np.abs(model_sample)
            nonzero_mask = abs_values > 1e-10
            fraction_nonzero = float(np.sum(nonzero_mask) / abs_values.size)

            stats.update(
                {
                    "fraction_nonzero": fraction_nonzero,
                    "max_value": float(np.max(abs_values)),
                    "mean_value": (
                        float(np.mean(abs_values[nonzero_mask]))
                        if np.any(nonzero_mask)
                        else 0.0
                    ),
                    "n_rows_checked": n_sample,
                }
            )

            is_populated = fraction_nonzero >= min_fraction

            if not is_populated:
                logger.warning(
                    f"MODEL_DATA appears unpopulated: {fraction_nonzero:.1%} non-zero values "
                    f"(threshold: {min_fraction:.1%})"
                )

            return is_populated, stats

    except Exception as e:
        logger.error(f"Error validating MODEL_DATA population: {e}")
        return False, stats


def validate_model_data_against_catalog(
    ms_path: str,
    catalog_ra_deg: float,
    catalog_dec_deg: float,
    catalog_flux_jy: float,
    tolerance_arcmin: float = 1.0,
    flux_tolerance_factor: float = 0.5,
) -> Tuple[bool, Dict]:
    """Validate MODEL_DATA against catalog calibrator information.

    Checks that MODEL_DATA phase center matches catalog position and that
    MODEL_DATA flux is consistent with catalog flux.

    Args:
        ms_path: Path to Measurement Set
        catalog_ra_deg: Catalog RA in degrees
        catalog_dec_deg: Catalog Dec in degrees
        catalog_flux_jy: Catalog flux in Jy
        tolerance_arcmin: Position tolerance in arcminutes (default: 1.0)
        flux_tolerance_factor: Flux tolerance factor (default: 0.5 = 50% variation allowed)

    Returns:
        Tuple of (is_valid, validation_dict)
        validation_dict contains:
            - position_match: Whether phase center matches catalog position
            - flux_match: Whether flux is consistent with catalog
            - phase_center_ra_deg: Phase center RA in degrees
            - phase_center_dec_deg: Phase center Dec in degrees
            - separation_arcmin: Separation between phase center and catalog position
            - estimated_flux_jy: Estimated flux from MODEL_DATA
            - flux_ratio: Ratio of estimated flux to catalog flux
    """
    validation = {
        "position_match": False,
        "flux_match": False,
        "phase_center_ra_deg": None,
        "phase_center_dec_deg": None,
        "separation_arcmin": None,
        "estimated_flux_jy": None,
        "flux_ratio": None,
    }

    try:
        # Get phase center from MS
        from dsa110_contimg.calibration.uvw_verification import get_phase_center_from_ms

        phase_center = get_phase_center_from_ms(ms_path, field=0)
        if phase_center is None:
            logger.warning("Could not extract phase center from MS")
            return False, validation

        ms_ra_deg, ms_dec_deg = phase_center
        validation["phase_center_ra_deg"] = ms_ra_deg
        validation["phase_center_dec_deg"] = ms_dec_deg

        # Calculate separation
        catalog_coord = SkyCoord(
            catalog_ra_deg * u.deg, catalog_dec_deg * u.deg, frame="icrs"
        )
        ms_coord = SkyCoord(ms_ra_deg * u.deg, ms_dec_deg * u.deg, frame="icrs")
        separation = catalog_coord.separation(ms_coord)
        separation_arcmin = separation.to(u.arcmin).value
        validation["separation_arcmin"] = separation_arcmin

        # Check position match
        validation["position_match"] = separation_arcmin <= tolerance_arcmin

        if not validation["position_match"]:
            logger.warning(
                f"Phase center offset from catalog: {separation_arcmin:.2f} arcmin "
                f"(tolerance: {tolerance_arcmin} arcmin)"
            )

        # Estimate flux from MODEL_DATA
        # This is approximate - MODEL_DATA contains visibility amplitudes, not flux directly
        # For a point source at phase center, flux ≈ mean(MODEL_DATA amplitude)
        try:
            with table(ms_path, readonly=True, ack=False) as tb:
                # Sample MODEL_DATA
                n_sample = min(1000, tb.nrows())
                model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=n_sample)

                # Get unflagged data
                flags = tb.getcol("FLAG", startrow=0, nrow=n_sample)
                unflagged_model = model_sample[~flags]

                if len(unflagged_model) > 0:
                    # Estimate flux as mean amplitude (for point source at phase center)
                    estimated_flux = float(np.mean(np.abs(unflagged_model)))
                    validation["estimated_flux_jy"] = estimated_flux

                    if catalog_flux_jy > 0:
                        flux_ratio = estimated_flux / catalog_flux_jy
                        validation["flux_ratio"] = flux_ratio

                        # Check if flux is within tolerance
                        # Allow significant variation due to primary beam, frequency, etc.
                        validation["flux_match"] = flux_ratio >= (
                            1.0 - flux_tolerance_factor
                        ) and flux_ratio <= (1.0 + flux_tolerance_factor)

                        if not validation["flux_match"]:
                            logger.warning(
                                f"MODEL_DATA flux ({estimated_flux:.2f} Jy) differs from catalog "
                                f"({catalog_flux_jy:.2f} Jy), ratio: {flux_ratio:.2f}"
                            )
        except Exception as e:
            logger.warning(f"Could not estimate flux from MODEL_DATA: {e}")

        is_valid = validation["position_match"] and validation["flux_match"]

        return is_valid, validation

    except Exception as e:
        logger.error(f"Error validating MODEL_DATA against catalog: {e}")
        return False, validation


def validate_model_data_consistency(
    ms_path: str, fields: Optional[List[int]] = None
) -> Tuple[bool, Dict]:
    """Validate MODEL_DATA consistency across fields.

    For drift-scan instruments, all fields should have MODEL_DATA at the same
    phase center after rephasing.

    Args:
        ms_path: Path to Measurement Set
        fields: List of field IDs to check (None = check all fields)

    Returns:
        Tuple of (is_consistent, consistency_dict)
        consistency_dict contains:
            - n_fields_checked: Number of fields checked
            - phase_centers: Dict mapping field_id -> (ra_deg, dec_deg)
            - max_separation_arcmin: Maximum separation between field phase centers
            - all_match: Whether all phase centers match within tolerance
    """
    consistency = {
        "n_fields_checked": 0,
        "phase_centers": {},
        "max_separation_arcmin": 0.0,
        "all_match": False,
    }

    try:
        from dsa110_contimg.calibration.uvw_verification import get_phase_center_from_ms

        with table(f"{ms_path}::FIELD", readonly=True, ack=False) as field_tb:
            n_fields = field_tb.nrows()

            if fields is None:
                fields = list(range(n_fields))

            phase_centers = {}
            for field_id in fields:
                if field_id >= n_fields:
                    continue

                phase_center = get_phase_center_from_ms(ms_path, field=field_id)
                if phase_center is not None:
                    phase_centers[field_id] = phase_center

            consistency["n_fields_checked"] = len(phase_centers)
            consistency["phase_centers"] = phase_centers

            if len(phase_centers) < 2:
                consistency["all_match"] = True
                return True, consistency

            # Check separations between all field pairs
            max_separation = 0.0
            coords = [
                SkyCoord(ra * u.deg, dec * u.deg, frame="icrs")
                for ra, dec in phase_centers.values()
            ]

            for i, coord1 in enumerate(coords):
                for coord2 in coords[i + 1 :]:
                    separation = coord1.separation(coord2)
                    separation_arcmin = separation.to(u.arcmin).value
                    max_separation = max(max_separation, separation_arcmin)

            consistency["max_separation_arcmin"] = max_separation

            # Fields are consistent if all phase centers are within 1 arcmin
            tolerance_arcmin = 1.0
            consistency["all_match"] = max_separation <= tolerance_arcmin

            if not consistency["all_match"]:
                logger.warning(
                    f"MODEL_DATA phase centers inconsistent across fields: "
                    f"max separation {max_separation:.2f} arcmin"
                )

            return consistency["all_match"], consistency

    except Exception as e:
        logger.error(f"Error validating MODEL_DATA consistency: {e}")
        return False, consistency


def comprehensive_model_data_validation(
    ms_path: str,
    catalog_ra_deg: Optional[float] = None,
    catalog_dec_deg: Optional[float] = None,
    catalog_flux_jy: Optional[float] = None,
) -> Dict:
    """Perform comprehensive MODEL_DATA validation.

    Validates MODEL_DATA existence, population, catalog match, and consistency.

    Args:
        ms_path: Path to Measurement Set
        catalog_ra_deg: Optional catalog RA in degrees
        catalog_dec_deg: Optional catalog Dec in degrees
        catalog_flux_jy: Optional catalog flux in Jy

    Returns:
        Dictionary with validation results:
            - exists: MODEL_DATA column exists
            - populated: MODEL_DATA is populated
            - catalog_match: MODEL_DATA matches catalog (if catalog info provided)
            - consistent: MODEL_DATA is consistent across fields
            - all_valid: All validations passed
            - details: Detailed validation results
    """
    results = {
        "exists": False,
        "populated": False,
        "catalog_match": None,  # None if catalog info not provided
        "consistent": False,
        "all_valid": False,
        "details": {},
    }

    # Check existence
    results["exists"] = validate_model_data_exists(ms_path)
    if not results["exists"]:
        logger.error("MODEL_DATA column does not exist")
        return results

    # Check population
    is_populated, pop_stats = validate_model_data_populated(ms_path)
    results["populated"] = is_populated
    results["details"]["population"] = pop_stats

    if not is_populated:
        logger.error("MODEL_DATA is not populated")
        return results

    # Check catalog match (if catalog info provided)
    if catalog_ra_deg is not None and catalog_dec_deg is not None:
        catalog_match, catalog_validation = validate_model_data_against_catalog(
            ms_path,
            catalog_ra_deg,
            catalog_dec_deg,
            catalog_flux_jy or 0.0,
        )
        results["catalog_match"] = catalog_match
        results["details"]["catalog"] = catalog_validation

    # Check consistency
    is_consistent, consistency_info = validate_model_data_consistency(ms_path)
    results["consistent"] = is_consistent
    results["details"]["consistency"] = consistency_info

    # Overall validation
    results["all_valid"] = (
        results["exists"]
        and results["populated"]
        and (results["catalog_match"] is None or results["catalog_match"])
        and results["consistent"]
    )

    return results
