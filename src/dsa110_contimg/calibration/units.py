"""Unit handling utilities for calibration calculations.

Provides explicit unit handling using astropy.units to prevent unit conversion errors
and ensure scientific correctness in calibration calculations.
"""

import logging
from typing import Optional, Tuple

import astropy.units as u
import numpy as np
from astropy.coordinates import Angle

logger = logging.getLogger(__name__)


def frequency_to_hz(freq_value: float, unit: str = "Hz") -> u.Quantity:
    """Convert frequency value to Quantity with explicit units.

    Args:
        freq_value: Frequency value
        unit: Unit string ("Hz", "MHz", "GHz", etc.)

    Returns:
        Frequency as Quantity with units

    Examples:
        >>> freq = frequency_to_hz(1400, "MHz")
        >>> freq.to(u.Hz)  # 1400000000.0 Hz
    """
    unit_map = {
        "Hz": u.Hz,
        "MHz": u.MHz,
        "GHz": u.GHz,
        "kHz": u.kHz,
    }

    if unit not in unit_map:
        raise ValueError(
            f"Unsupported frequency unit: {unit}. Use Hz, MHz, GHz, or kHz"
        )

    return freq_value * unit_map[unit]


def delay_from_phase(phase_rad: np.ndarray, frequency: u.Quantity) -> u.Quantity:
    """Convert phase to delay with explicit unit handling.

    Args:
        phase_rad: Phase in radians (numpy array)
        frequency: Frequency as Quantity (e.g., 1400 * u.MHz)

    Returns:
        Delay as Quantity (seconds, converted to nanoseconds)

    Examples:
        >>> phase = np.array([0.1, 0.2, 0.3])  # radians
        >>> freq = 1400 * u.MHz
        >>> delay = delay_from_phase(phase, freq)
        >>> delay.to(u.ns)  # Delay in nanoseconds
    """
    if not isinstance(frequency, u.Quantity):
        raise ValueError(f"Frequency must be Quantity, got {type(frequency)}")

    # Convert phase to delay: delay = phase / (2π × frequency)
    delay_sec = phase_rad / (2 * np.pi * frequency.to(u.Hz).value) * u.s

    return delay_sec


def phase_from_delay(delay: u.Quantity, frequency: u.Quantity) -> np.ndarray:
    """Convert delay to phase with explicit unit handling.

    Args:
        delay: Delay as Quantity (e.g., nanoseconds)
        frequency: Frequency as Quantity (e.g., MHz)

    Returns:
        Phase in radians (numpy array)
    """
    if not isinstance(delay, u.Quantity):
        raise ValueError(f"Delay must be Quantity, got {type(delay)}")
    if not isinstance(frequency, u.Quantity):
        raise ValueError(f"Frequency must be Quantity, got {type(frequency)}")

    # Convert delay to phase: phase = 2π × frequency × delay
    delay_sec = delay.to(u.s).value
    freq_hz = frequency.to(u.Hz).value
    phase_rad = 2 * np.pi * freq_hz * delay_sec

    return np.array(phase_rad)


def wrap_phase_deg(phase_deg: np.ndarray) -> np.ndarray:
    """Wrap phase to [-180, 180) degrees with proper handling.

    Args:
        phase_deg: Phase in degrees (numpy array)

    Returns:
        Wrapped phase in degrees, range [-180, 180)
    """
    # Wrap to [-180, 180)
    wrapped = np.mod(phase_deg + 180, 360) - 180
    return wrapped


def wrap_phase_rad(phase_rad: np.ndarray) -> np.ndarray:
    """Wrap phase to [-π, π) radians with proper handling.

    Args:
        phase_rad: Phase in radians (numpy array)

    Returns:
        Wrapped phase in radians, range [-π, π)
    """
    # Wrap to [-π, π)
    wrapped = np.mod(phase_rad + np.pi, 2 * np.pi) - np.pi
    return wrapped


def validate_units(
    value: u.Quantity,
    expected_unit: u.Unit,
    name: str = "value",
    tolerance: Optional[float] = None,
) -> None:
    """Validate that a Quantity has the expected units.

    Args:
        value: Quantity to validate
        expected_unit: Expected unit (e.g., u.Hz, u.deg)
        name: Name of value for error messages
        tolerance: Optional tolerance for unit conversion (e.g., 1e-6)

    Raises:
        ValueError: If units are incompatible
        UnitConversionError: If conversion fails

    Examples:
        >>> freq = 1400 * u.MHz
        >>> validate_units(freq, u.Hz)  # OK (MHz converts to Hz)
        >>> validate_units(freq, u.m)  # Raises ValueError
    """
    if not isinstance(value, u.Quantity):
        raise ValueError(f"{name} must be Quantity, got {type(value)}")

    try:
        converted = value.to(expected_unit)
        if tolerance is not None:
            # Check if conversion is exact (within tolerance)
            if abs(converted.value - value.to(expected_unit).value) > tolerance:
                logger.warning(
                    f"{name} unit conversion may have precision loss: "
                    f"{value} -> {converted}"
                )
    except u.UnitConversionError as e:
        raise ValueError(
            f"{name} has incompatible units: {value.unit} cannot be converted to {expected_unit}"
        ) from e


def get_reference_frequency_from_ms(ms_path: str) -> Optional[u.Quantity]:
    """Extract reference frequency from MS with explicit units.

    Args:
        ms_path: Path to Measurement Set

    Returns:
        Reference frequency as Quantity (Hz), or None if not found
    """
    # Ensure CASAPATH is set before importing CASA modules
    from dsa110_contimg.utils.casa_init import ensure_casa_path
    ensure_casa_path()

    try:
        import casacore.tables as casatables
        table = casatables.table

        with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True, ack=False) as spw_tb:
            ref_freqs = spw_tb.getcol("REF_FREQUENCY")
            if len(ref_freqs) > 0:
                # Use median reference frequency across SPWs
                ref_freq_hz = float(np.median(ref_freqs))
                return ref_freq_hz * u.Hz
    except Exception as e:
        logger.warning(f"Could not extract reference frequency from MS: {e}")

    return None


def calculate_phase_error_from_delay(
    delay: u.Quantity, bandwidth: u.Quantity
) -> u.Quantity:
    """Calculate phase error across bandwidth due to delay.

    Args:
        delay: Delay as Quantity (e.g., nanoseconds)
        bandwidth: Bandwidth as Quantity (e.g., MHz)

    Returns:
        Phase error as Quantity (degrees)

    Examples:
        >>> delay = 1.0 * u.ns
        >>> bandwidth = 200 * u.MHz
        >>> phase_error = calculate_phase_error_from_delay(delay, bandwidth)
        >>> phase_error.to(u.deg)  # Phase error in degrees
    """
    if not isinstance(delay, u.Quantity):
        raise ValueError(f"Delay must be Quantity, got {type(delay)}")
    if not isinstance(bandwidth, u.Quantity):
        raise ValueError(f"Bandwidth must be Quantity, got {type(bandwidth)}")

    # Phase error = 2π × delay × bandwidth
    delay_sec = delay.to(u.s).value
    bandwidth_hz = bandwidth.to(u.Hz).value
    phase_error_rad = 2 * np.pi * delay_sec * bandwidth_hz
    phase_error_deg = np.degrees(phase_error_rad) * u.deg

    return phase_error_deg


def calculate_coherence_loss(phase_error: u.Quantity) -> float:
    """Calculate coherence loss from phase error.

    Args:
        phase_error: Phase error as Quantity (degrees or radians)

    Returns:
        Coherence (0-1), where 1 is perfect coherence

    Examples:
        >>> phase_error = 10 * u.deg
        >>> coherence = calculate_coherence_loss(phase_error)
        >>> coherence_loss_percent = (1 - coherence) * 100
    """
    if not isinstance(phase_error, u.Quantity):
        raise ValueError(f"Phase error must be Quantity, got {type(phase_error)}")

    # Convert to radians
    phase_error_rad = phase_error.to(u.rad).value

    # Coherence = |sinc(phase_error / (2π))|
    coherence = np.abs(np.sinc(phase_error_rad / (2 * np.pi)))

    return float(coherence)
