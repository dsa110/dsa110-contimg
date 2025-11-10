"""
CubiCal calibration functions.

This module provides CubiCal-based calibration functions that are
completely independent of the existing CASA-based pipeline.
"""

import logging
from typing import Optional

# These imports will only work when CubiCal is installed
try:
    from cubical import calibration_control, data_handling

    CUBICAL_AVAILABLE = True
except ImportError:
    CUBICAL_AVAILABLE = False
    logging.warning(
        "CubiCal not available. Install with: pip install 'cubical[lsm-support]@git+https://github.com/ratt-ru/CubiCal.git@1.4.0'"
    )


def solve_bandpass_cubical(
    ms_path: str,
    cal_field: str,
    refant: str,
    solint: str = "inf",
    combine: Optional[str] = None,
) -> "calibration_control.CalibrationControl":
    """
    Solve bandpass calibration using CubiCal.

    This is a standalone function that does NOT use CASA.
    It can be tested independently of the existing pipeline.

    Args:
        ms_path: Path to Measurement Set
        cal_field: Field ID or selection string
        refant: Reference antenna
        solint: Solution interval (CubiCal format)
        combine: Combine string (e.g., "scan,obs")

    Returns:
        CubiCal solution object
    """
    if not CUBICAL_AVAILABLE:
        raise ImportError("CubiCal is not installed")

    # Load data using CubiCal's data handler
    # This is different from CASA's approach
    data = data_handling.load_data(
        ms_path=ms_path,
        field_ids=[cal_field],  # CubiCal uses field IDs, not selection strings
    )

    # Create bandpass solver
    solver = calibration_control.CalibrationControl(
        data=data,
        model=data.model,  # CubiCal handles model differently
        solver_options={
            "type": "complex-2x2",  # CubiCal parameter
            "mode": "robust",
            "ref_ant": refant,  # Different parameter name than CASA
            "time_interval": solint,  # Different parameter name
            "freq_interval": "inf",  # Per-channel bandpass
        },
    )

    # Solve
    solution = solver.solve()

    return solution


def solve_gains_cubical(
    ms_path: str,
    cal_field: str,
    refant: str,
    bptable: str,
    solint: str = "60s",
    combine: Optional[str] = None,
) -> "calibration_control.CalibrationControl":
    """
    Solve gain calibration using CubiCal.

    This is a standalone function that does NOT use CASA.
    It can be tested independently of the existing pipeline.

    Args:
        ms_path: Path to Measurement Set
        cal_field: Field ID or selection string
        refant: Reference antenna
        bptable: Path to bandpass solution (CubiCal format)
        solint: Solution interval
        combine: Combine string

    Returns:
        CubiCal solution object
    """
    if not CUBICAL_AVAILABLE:
        raise ImportError("CubiCal is not installed")

    # Load data
    data = data_handling.load_data(
        ms_path=ms_path,
        field_ids=[cal_field],
    )

    # Load bandpass solution
    # (CubiCal format, not CASA table)
    bp_solution = calibration_control.load_solution(bptable)

    # Create gain solver with bandpass applied
    solver = calibration_control.CalibrationControl(
        data=data,
        model=data.model,
        gaintable=[bp_solution],  # Apply bandpass
        solver_options={
            "type": "complex-2x2",
            "mode": "robust",
            "ref_ant": refant,
            "time_interval": solint,
            "freq_interval": "inf",  # Average over frequency
        },
    )

    # Solve
    solution = solver.solve()

    return solution
