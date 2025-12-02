#!/opt/miniforge/envs/casa6/bin/python
# pylint: disable=no-member  # astropy.units uses dynamic attributes (deg, arcsec, m, etc.)
"""Generate synthetic DSA-110 UVH5 subband files for end-to-end testing."""

import argparse
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import astropy.units as u  # pylint: disable=no-member
import numpy as np
import yaml
from astropy.coordinates import EarthLocation
from astropy.time import Time
from pyuvdata import UVData

from dsa110_contimg.utils.antpos_local import get_itrf
from dsa110_contimg.utils.constants import OVRO_ALT, OVRO_LAT, OVRO_LON
from dsa110_contimg.utils.fringestopping import calc_uvw_blt

PACKAGE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PACKAGE_ROOT / "config"
PYUVSIM_DIR = PACKAGE_ROOT / "pyuvsim"
DEFAULT_TEMPLATE = REPO_ROOT / "data-samples" / "ms" / "test_8subbands_concatenated.hdf5"

SECONDS_PER_DAY = 86400.0


@dataclass
class TelescopeConfig:
    layout_csv: Path
    polarizations: List[int]
    num_subbands: int
    channels_per_subband: int
    channel_width_hz: float
    freq_min_hz: float
    freq_max_hz: float
    reference_frequency_hz: float
    integration_time_sec: float
    total_duration_sec: float
    site_location: EarthLocation
    phase_ra: u.Quantity
    phase_dec: u.Quantity
    extra_keywords: Dict[str, str]
    freq_template: np.ndarray = field(default_factory=lambda: np.array([]))
    freq_order: str = "desc"


def load_reference_layout(path: Path) -> Dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_telescope_config(config_path: Path, layout_meta: Dict, freq_order: str) -> TelescopeConfig:
    with config_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)

    site = raw["site"]
    layout = raw["layout"]
    spectral = raw["spectral"]
    temporal = raw["temporal"]
    phase_center = raw["phase_center"]

    location = EarthLocation.from_geodetic(
        lon=site["longitude_deg"] * u.deg,
        lat=site["latitude_deg"] * u.deg,
        height=site["altitude_m"] * u.m,
    )

    polarizations = [int(pol) for pol in layout["polarization_array"]]
    extra_keywords = layout_meta.get("extra_keywords", {})

    # Derive frequency limits from reference layout when not stated explicitly.
    freq_array = layout_meta.get("freq_array_hz")
    freq_min = spectral.get("freq_min_hz")
    freq_max = spectral.get("freq_max_hz")
    freq_template = np.array(freq_array, dtype=float) if freq_array else np.array([])
    if freq_template.size > 0:
        if freq_min is None:
            freq_min = float(np.min(freq_template))
        if freq_max is None:
            freq_max = float(np.max(freq_template))
    if freq_min is None or freq_max is None:
        raise ValueError("Unable to derive frequency bounds from configuration or layout metadata")

    norm_freq_order = freq_order.lower()
    if norm_freq_order not in {"asc", "desc"}:
        raise ValueError(f"Unsupported frequency order '{freq_order}'")
    if freq_template.size > 0 and norm_freq_order == "asc" and freq_template[0] > freq_template[-1]:
        freq_template = freq_template[::-1]
    if (
        freq_template.size > 0
        and norm_freq_order == "desc"
        and freq_template[0] < freq_template[-1]
    ):
        freq_template = freq_template[::-1]

    return TelescopeConfig(
        layout_csv=config_path.parent / layout["csv"],
        polarizations=polarizations,
        num_subbands=int(spectral["num_subbands"]),
        channels_per_subband=int(spectral["channels_per_subband"]),
        channel_width_hz=float(spectral["channel_width_hz"]),
        freq_min_hz=float(freq_min),
        freq_max_hz=float(freq_max),
        reference_frequency_hz=float(spectral["reference_frequency_hz"]),
        integration_time_sec=float(temporal["integration_time_sec"]),
        total_duration_sec=float(temporal["total_duration_sec"]),
        site_location=location,
        phase_ra=float(phase_center["ra_deg"]) * u.deg,
        phase_dec=float(phase_center["dec_deg"]) * u.deg,
        extra_keywords=extra_keywords,
        freq_template=freq_template,
        freq_order=norm_freq_order,
    )


def build_time_arrays(config: TelescopeConfig, nbls: int, ntimes: int, start_time: Time):
    """Build time arrays for synthetic data generation.

    Args:
        config: Telescope configuration
        nbls: Number of baselines
        ntimes: Number of time integrations
        start_time: Observation start time

    Returns:
        Tuple of (unique_times, time_array, lst_array, integration_time)
    """
    dt_days = config.integration_time_sec / SECONDS_PER_DAY

    unique_times = start_time.mjd + dt_days * np.arange(ntimes)
    time_array = np.repeat(unique_times, nbls)

    lst = Time(unique_times, format="mjd", scale="utc", location=config.site_location)
    lst_array = np.repeat(lst.sidereal_time("apparent").rad, nbls)

    integration_time = np.full(time_array.shape, config.integration_time_sec, dtype=float)
    return unique_times, time_array, lst_array, integration_time


def build_uvw(
    config: TelescopeConfig,
    unique_times_mjd: np.ndarray,
    ant1_array: np.ndarray,
    ant2_array: np.ndarray,
    nants_telescope: int,
) -> np.ndarray:
    """Build UVW array for synthetic data generation.

    Args:
        config: Telescope configuration
        unique_times_mjd: Array of unique times in MJD
        ant1_array: Antenna 1 array for baselines
        ant2_array: Antenna 2 array for baselines
        nants_telescope: Number of antennas

    Returns:
        UVW array with shape (nbls * ntimes, 3)
    """
    nbls = len(ant1_array)
    ntimes = len(unique_times_mjd)

    ant_df = get_itrf(latlon_center=(OVRO_LAT * u.rad, OVRO_LON * u.rad, OVRO_ALT * u.m))
    ant_offsets = {}
    missing = []
    for ant in range(nants_telescope):
        station = ant + 1
        if station in ant_df.index:
            row = ant_df.loc[station]
            ant_offsets[ant] = np.array([row["dx_m"], row["dy_m"], row["dz_m"]], dtype=float)
        else:
            missing.append(station)
    if missing:
        raise ValueError(f"Missing antenna offsets for stations: {missing}")

    blen = np.zeros((nbls, 3))
    for idx, (a1, a2) in enumerate(zip(ant1_array, ant2_array)):
        blen[idx] = ant_offsets[int(a2)] - ant_offsets[int(a1)]

    uvw = np.zeros((nbls * ntimes, 3), dtype=float)
    for tidx, mjd in enumerate(unique_times_mjd):
        start = tidx * nbls
        stop = start + nbls
        time_vec = np.full(nbls, mjd)
        uvw[start:stop] = calc_uvw_blt(
            blen,
            time_vec,
            "J2000",
            np.full(nbls, config.phase_ra.to_value(u.rad)) * u.rad,
            np.full(nbls, config.phase_dec.to_value(u.rad)) * u.rad,
        )
    return uvw


def make_visibilities(
    nblts: int,
    nspws: int,
    nfreqs: int,
    npols: int,
    amplitude_jy: float,
    u_lambda: Optional[np.ndarray] = None,
    v_lambda: Optional[np.ndarray] = None,
    source_model: str = "point",
    source_size_arcsec: Optional[float] = None,
    source_pa_deg: float = 0.0,
) -> np.ndarray:
    """Create visibility array for synthetic data.

    Args:
        nblts: Number of baseline-time pairs
        nspws: Number of spectral windows
        nfreqs: Number of frequency channels
        npols: Number of polarizations
        amplitude_jy: Source flux density in Jy
        u_lambda: U coordinates in wavelengths (for extended sources)
        v_lambda: V coordinates in wavelengths (for extended sources)
        source_model: Source model type: "point", "gaussian", or "disk"
        source_size_arcsec: Source size in arcseconds (FWHM for Gaussian, radius for disk)
        source_pa_deg: Position angle in degrees (for Gaussian, default: 0)

    Returns:
        Visibility array with shape (nblts, nspws, nfreqs, npols)
    """
    from dsa110_contimg.simulation.visibility_models import (
        disk_source_visibility,
        gaussian_source_visibility,
    )

    shape = (nblts, nspws, nfreqs, npols)

    if source_model == "point" or source_size_arcsec is None or source_size_arcsec == 0:
        # Point source: constant visibility
        value = amplitude_jy / 2.0  # split unpolarized flux equally between XX and YY
        vis = np.full(shape, value, dtype=np.complex64)
    elif source_model == "gaussian":
        # Gaussian extended source
        if u_lambda is None or v_lambda is None:
            raise ValueError("u_lambda and v_lambda required for Gaussian source")
        # Use major_axis = minor_axis for circular Gaussian
        major_axis = source_size_arcsec
        minor_axis = source_size_arcsec
        vis_1d = gaussian_source_visibility(
            u_lambda, v_lambda, amplitude_jy, major_axis, minor_axis, source_pa_deg
        )
        # Expand to full shape: (nblts, nspws, nfreqs, npols)
        vis = np.zeros(shape, dtype=np.complex64)
        for spw in range(nspws):
            for freq in range(nfreqs):
                for pol in range(npols):
                    vis[:, spw, freq, pol] = (
                        vis_1d / 2.0
                    )  # Split unpolarized flux equally between XX and YY
    elif source_model == "disk":
        # Uniform disk source
        if u_lambda is None or v_lambda is None:
            raise ValueError("u_lambda and v_lambda required for disk source")
        vis_1d = disk_source_visibility(u_lambda, v_lambda, amplitude_jy, source_size_arcsec)
        # Expand to full shape
        vis = np.zeros(shape, dtype=np.complex64)
        for spw in range(nspws):
            for freq in range(nfreqs):
                for pol in range(npols):
                    vis[:, spw, freq, pol] = (
                        vis_1d / 2.0
                    )  # Split unpolarized flux equally between XX and YY
    else:
        raise ValueError(f"Unknown source model: {source_model}")

    return vis


def build_uvdata_from_scratch(
    config: TelescopeConfig,
    nants: int = 110,
    ntimes: int = 30,
    start_time: Time = None,
) -> UVData:
    """Build a minimal UVData object from scratch without requiring a template.

    This function creates a UVData object with realistic DSA-110 structure
    using only configuration files and antenna position data.

    Args:
        config: Telescope configuration
        nants: Number of antennas (default: 110 for DSA-110)
        ntimes: Number of time integrations (default: 30 for ~5 minutes)
        start_time: Observation start time (default: current time)

    Returns:
        UVData object with basic structure populated
    """
    if start_time is None:
        start_time = Time.now()

    # Get antenna positions
    ant_df = get_itrf(latlon_center=(OVRO_LAT * u.rad, OVRO_LON * u.rad, OVRO_ALT * u.m))

    # Select antennas (use first nants stations)
    available_stations = sorted(ant_df.index)[:nants]
    ant_offsets = {}
    for station in available_stations:
        ant_idx = station - 1  # Convert station number to antenna index
        row = ant_df.loc[station]
        ant_offsets[ant_idx] = np.array([row["dx_m"], row["dy_m"], row["dz_m"]], dtype=float)

    # Create baseline pairs
    ant_indices = sorted(ant_offsets.keys())
    baselines = [(i, j) for i in ant_indices for j in ant_indices if i < j]
    nbls = len(baselines)

    # Build antenna arrays
    ant1_list = [b[0] for b in baselines]
    ant2_list = [b[1] for b in baselines]

    # Build time arrays
    unique_times, time_array, lst_array, integration_time = build_time_arrays(
        config, nbls, ntimes, start_time
    )

    # Build UVW array
    uvw_array = build_uvw(
        config,
        unique_times,
        np.array(ant1_list),
        np.array(ant2_list),
        nants,
    )

    # Create UVData object
    uv = UVData()

    # Calculate dimensions - in pyuvdata 3.x these are computed properties
    # so we need to calculate them before creating arrays
    nblts = nbls * ntimes
    nspws = 1
    nfreqs = config.channels_per_subband
    npols = len(config.polarizations)

    # Set basic dimensions that can still be set
    uv.Nspws = nspws

    # Set antenna arrays (these define Nants_data and Nants_telescope)
    uv.ant_1_array = np.repeat(ant1_list, ntimes)
    uv.ant_2_array = np.repeat(ant2_list, ntimes)
    uv.antenna_numbers = np.array(ant_indices, dtype=int)
    uv.antenna_names = [str(i) for i in ant_indices]

    # Set time arrays
    uv.time_array = time_array
    uv.lst_array = lst_array
    uv.integration_time = integration_time

    # Set frequency array (will be set per subband)
    uv.freq_array = np.zeros((nspws, nfreqs), dtype=float)
    uv.channel_width = np.full(nfreqs, config.channel_width_hz, dtype=float)

    # Set phase center
    uv.phase_center_ra = config.phase_ra.to_value(u.rad)
    uv.phase_center_dec = config.phase_dec.to_value(u.rad)
    uv.phase_center_frame = "icrs"
    uv.phase_center_epoch = 2000.0

    # Set UVW
    uv.uvw_array = uvw_array

    # Set polarization
    uv.polarization_array = np.array(config.polarizations, dtype=int)

    # Set telescope metadata using the Telescope object (pyuvdata 3.x API)
    from pyuvdata import Telescope
    tel = Telescope()
    tel.name = "DSA-110"
    tel.location = config.site_location
    tel.Nants = len(uv.antenna_numbers)
    uv.telescope = tel

    # Set data arrays using calculated dimensions
    uv.data_array = np.zeros((nblts, nspws, nfreqs, npols), dtype=np.complex64)
    uv.flag_array = np.zeros((nblts, nspws, nfreqs, npols), dtype=bool)
    uv.nsample_array = np.ones((nblts, nspws, nfreqs, npols), dtype=np.float32)

    # Set units and metadata
    uv.vis_units = "Jy"
    uv.history = "Synthetic UVData created from scratch (template-free mode)"
    uv.object_name = "synthetic_calibrator"
    uv.extra_keywords = config.extra_keywords.copy()
    uv.extra_keywords["synthetic"] = True
    uv.extra_keywords["template_free"] = True

    return uv


def write_subband_uvh5(
    subband_index: int,
    uv_template: UVData,
    config: TelescopeConfig,
    start_time: Time,
    times_mjd: np.ndarray,
    lst_array: np.ndarray,
    integration_time: np.ndarray,
    uvw_array: np.ndarray,
    amplitude_jy: float,
    output_dir: Path,
    source_model: str = "point",
    source_size_arcsec: Optional[float] = None,
    source_pa_deg: float = 0.0,
    add_noise: bool = False,
    system_temperature_k: float = 50.0,
    add_cal_errors: bool = False,
    gain_std: float = 0.1,
    phase_std_deg: float = 10.0,
    rng: Optional[np.random.Generator] = None,
) -> Path:
    """Write a single subband UVH5 file.

    Args:
        subband_index: Subband index (0-based)
        uv_template: Template UVData object (or created from scratch)
        config: Telescope configuration
        start_time: Observation start time
        times_mjd: Time array in MJD
        lst_array: LST array in radians
        integration_time: Integration time array in seconds
        uvw_array: UVW array
        amplitude_jy: Source flux density in Jy
        output_dir: Output directory

    Returns:
        Path to created UVH5 file
    """
    uv = uv_template.copy()
    uv.history += f"\nSynthetic point-source dataset generated (subband {subband_index:02d})."

    # Mark as synthetic in extra_keywords
    uv.extra_keywords["synthetic"] = True
    uv.extra_keywords["synthetic_flux_jy"] = float(amplitude_jy)
    uv.extra_keywords["synthetic_source_model"] = source_model
    # Store source position for catalog generation
    uv.extra_keywords["synthetic_source_ra_deg"] = float(config.phase_ra.to_value(u.deg))
    uv.extra_keywords["synthetic_source_dec_deg"] = float(config.phase_dec.to_value(u.deg))
    if source_size_arcsec is not None:
        uv.extra_keywords["synthetic_source_size_arcsec"] = float(source_size_arcsec)
    if add_noise:
        uv.extra_keywords["synthetic_has_noise"] = True
        uv.extra_keywords["synthetic_system_temp_k"] = float(system_temperature_k)
    if add_cal_errors:
        uv.extra_keywords["synthetic_has_cal_errors"] = True
        uv.extra_keywords["synthetic_gain_std"] = float(gain_std)
        uv.extra_keywords["synthetic_phase_std_deg"] = float(phase_std_deg)

    delta_f = abs(config.channel_width_hz)
    nchan = config.channels_per_subband
    sign = -1.0 if config.freq_order == "desc" else 1.0

    if config.freq_template.size == nchan:
        base = config.freq_template.copy()
        freqs = base + sign * subband_index * nchan * delta_f
    else:
        if config.freq_order == "desc":
            start_freq = config.freq_max_hz
        else:
            start_freq = config.freq_min_hz
        freqs = start_freq + sign * delta_f * (np.arange(nchan) + subband_index * nchan)

    uv.freq_array = freqs.reshape(1, -1)
    uv.channel_width = np.full_like(uv.freq_array, sign * delta_f)
    uv.Nspws = 1

    uv.time_array = times_mjd
    uv.lst_array = lst_array
    uv.integration_time = integration_time
    uv.uvw_array = uvw_array

    # Calculate dimensions from arrays (pyuvdata 3.x compatibility)
    # Computed properties like Nblts, Nfreqs, Npols may be None
    nblts = len(times_mjd)
    nspws = 1
    nfreqs = nchan
    npols = len(uv.polarization_array)
    nants = len(uv.antenna_numbers)

    # Calculate u, v coordinates in wavelengths for extended sources
    u_lambda = None
    v_lambda = None
    if source_model != "point" and source_size_arcsec is not None:
        # Extract u, v from uvw_array (w is third column)
        # uvw_array shape: (Nblts, 3) where columns are [u, v, w] in meters
        # Convert to wavelengths using mean frequency
        mean_freq_hz = np.mean(uv.freq_array)
        wavelength_m = 299792458.0 / mean_freq_hz  # c / f
        u_lambda = uvw_array[:, 0] / wavelength_m
        v_lambda = uvw_array[:, 1] / wavelength_m

    # Generate visibilities
    uv.data_array = make_visibilities(
        nblts,
        nspws,
        nfreqs,
        npols,
        amplitude_jy,
        u_lambda=u_lambda,
        v_lambda=v_lambda,
        source_model=source_model,
        source_size_arcsec=source_size_arcsec,
        source_pa_deg=source_pa_deg,
    )

    # Add thermal noise if requested
    if add_noise:
        from dsa110_contimg.simulation.visibility_models import add_thermal_noise

        # Get integration time and channel width
        int_time = config.integration_time_sec
        chan_width = abs(config.channel_width_hz)

        # Get mean frequency for noise calculation (use center of frequency array)
        mean_freq_hz = (
            np.mean(uv.freq_array)
            if hasattr(uv, "freq_array") and uv.freq_array.size > 0
            else config.reference_frequency_hz
        )

        uv.data_array = add_thermal_noise(
            uv.data_array,
            int_time,
            chan_width,
            system_temperature_k=system_temperature_k,
            frequency_hz=mean_freq_hz,
            rng=rng,
        )

    # Add calibration errors if requested
    if add_cal_errors:
        from dsa110_contimg.simulation.visibility_models import (
            add_calibration_errors,
            apply_calibration_errors_to_visibilities,
        )

        _, complex_gains, _ = add_calibration_errors(
            uv.data_array,
            nants,  # Use calculated nants instead of uv.Nants_telescope
            gain_std=gain_std,
            phase_std_deg=phase_std_deg,
            rng=rng,
        )

        uv.data_array = apply_calibration_errors_to_visibilities(
            uv.data_array,
            uv.ant_1_array,
            uv.ant_2_array,
            complex_gains,
        )

    uv.flag_array = np.zeros_like(uv.data_array, dtype=bool)
    uv.nsample_array = np.ones_like(uv.data_array, dtype=np.float32)

    uv.extra_keywords.update(config.extra_keywords)
    uv.extra_keywords["phase_center_dec"] = config.phase_dec.to_value(u.rad)
    uv.extra_keywords["ha_phase_center"] = 0.0
    uv.extra_keywords["phase_center_epoch"] = "HADEC"

    uv.phase_center_ra = config.phase_ra.to_value(u.rad)
    uv.phase_center_dec = config.phase_dec.to_value(u.rad)
    uv.phase_center_frame = "icrs"
    uv.phase_center_epoch = 2000.0

    start_time.iso.replace("-", "").replace(":", "")
    anchor_str = start_time.strftime("%Y-%m-%dT%H:%M:%S")
    filename = f"{anchor_str}_sb{subband_index:02d}.hdf5"
    output_path = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)
    uv.write_uvh5(output_path, run_check=False, clobber=True)

    # Use optimized HDF5 access for post-write modifications
    from dsa110_contimg.utils.hdf5_io import open_uvh5

    with open_uvh5(output_path, "r+") as handle:
        hdr = handle["Header"]
        if "channel_width" in hdr:
            data = np.array([sign * delta_f], dtype=np.float64)
            del hdr["channel_width"]
            hdr.create_dataset("channel_width", data=data)
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Synthetic DSA-110 UVH5 generator")
    parser.add_argument(
        "--template",
        type=Path,
        default=DEFAULT_TEMPLATE,
        help="Reference UVH5 file for metadata scaffolding (optional if --template-free used)",
    )
    parser.add_argument(
        "--template-free",
        action="store_true",
        help="Generate synthetic data without requiring a template file",
    )
    parser.add_argument(
        "--nants",
        type=int,
        default=110,
        help="Number of antennas (only used in template-free mode, default: 110)",
    )
    parser.add_argument(
        "--ntimes",
        type=int,
        default=30,
        help="Number of time integrations (only used in template-free mode, default: 30)",
    )
    parser.add_argument(
        "--layout-meta",
        type=Path,
        default=CONFIG_DIR / "reference_layout.json",
        help="JSON metadata produced by analyse_reference_uvh5.py",
    )
    parser.add_argument(
        "--telescope-config",
        type=Path,
        default=PYUVSIM_DIR / "telescope.yaml",
        help="Telescope configuration YAML",
    )
    parser.add_argument(
        "--start-time",
        type=str,
        default="2025-01-01T00:00:00",
        help="Observation start time (UTC, ISO format)",
    )
    parser.add_argument(
        "--duration-minutes",
        type=float,
        default=5.0,
        help="Approximate observation duration in minutes",
    )
    parser.add_argument(
        "--flux-jy",
        type=float,
        default=25.0,
        help="Total Stokes I flux density of the calibrator",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("simulation/output"),
        help="Directory where UVH5 files will be written",
    )
    parser.add_argument(
        "--subbands",
        type=int,
        default=16,
        help="Number of subbands to synthesise",
    )
    parser.add_argument(
        "--freq-order",
        choices=["asc", "desc"],
        default="desc",
        help="Per-subband frequency ordering (default: desc)",
    )
    parser.add_argument(
        "--shuffle-subbands",
        action="store_true",
        help="Emit subband files in a shuffled order to exercise ingestion ordering",
    )
    parser.add_argument(
        "--source-model",
        choices=["point", "gaussian", "disk"],
        default="point",
        help="Source model type (default: point)",
    )
    parser.add_argument(
        "--source-size-arcsec",
        type=float,
        default=None,
        help="Source size in arcseconds (FWHM for Gaussian, radius for disk)",
    )
    parser.add_argument(
        "--source-pa-deg",
        type=float,
        default=0.0,
        help="Position angle in degrees for Gaussian sources (default: 0)",
    )
    parser.add_argument(
        "--add-noise",
        action="store_true",
        help="Add realistic thermal noise to visibilities",
    )
    parser.add_argument(
        "--system-temp-k",
        type=float,
        default=50.0,
        help="System temperature in Kelvin for noise calculation (default: 50K)",
    )
    parser.add_argument(
        "--add-cal-errors",
        action="store_true",
        help="Add realistic calibration errors (gain and phase)",
    )
    parser.add_argument(
        "--gain-std",
        type=float,
        default=0.1,
        help="Standard deviation of gain errors (default: 0.1 = 10%%)",
    )
    parser.add_argument(
        "--phase-std-deg",
        type=float,
        default=10.0,
        help="Standard deviation of phase errors in degrees (default: 10 deg)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility (for noise and cal errors)",
    )
    parser.add_argument(
        "--create-catalog",
        action="store_true",
        help="Create synthetic catalog database matching source positions",
    )
    parser.add_argument(
        "--catalog-type",
        type=str,
        choices=["nvss", "first", "rax", "vlass"],
        default="nvss",
        help="Catalog type for synthetic catalog (default: nvss)",
    )
    parser.add_argument(
        "--catalog-output",
        type=Path,
        default=None,
        help="Output path for synthetic catalog database (auto-generated if not specified)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.layout_meta.exists():
        raise FileNotFoundError(f"Layout metadata not found at {args.layout_meta}")
    if not args.telescope_config.exists():
        raise FileNotFoundError(f"Telescope configuration not found at {args.telescope_config}")

    layout_meta = load_reference_layout(args.layout_meta)
    config = load_telescope_config(args.telescope_config, layout_meta, args.freq_order)

    if args.subbands != config.num_subbands:
        print(
            f"WARNING: Requested {args.subbands} subbands,"
            f" but configuration expects {config.num_subbands}."
        )

    start_time = Time(args.start_time, format="isot", scale="utc")

    # Template-free mode: build UVData from scratch
    if args.template_free:
        print("Using template-free generation mode...")
        uv_template = build_uvdata_from_scratch(
            config, nants=args.nants, ntimes=args.ntimes, start_time=start_time
        )
        nbls = uv_template.Nbls
        ntimes = uv_template.Ntimes
        unique_times, time_array, lst_array, integration_time = build_time_arrays(
            config, nbls, ntimes, start_time
        )
        uvw_array = build_uvw(
            config,
            unique_times,
            uv_template.ant_1_array[:nbls],
            uv_template.ant_2_array[:nbls],
            uv_template.Nants_telescope,
        )
    # Template mode: use existing template file
    else:
        if not args.template.exists():
            raise FileNotFoundError(
                f"Template UVH5 not found at {args.template}. "
                f"Provide --template with a reference dataset or use --template-free."
            )
        print(f"Using template file: {args.template}")
        uv_template = UVData()
        uv_template.read(
            args.template,
            file_type="uvh5",
            run_check=False,
            run_check_acceptability=False,
            strict_uvw_antpos_check=False,
        )
        nbls = uv_template.Nbls
        ntimes = uv_template.Ntimes
        unique_times, time_array, lst_array, integration_time = build_time_arrays(
            config, nbls, ntimes, start_time
        )
        uvw_array = build_uvw(
            config,
            unique_times,
            uv_template.ant_1_array[:nbls],
            uv_template.ant_2_array[:nbls],
            uv_template.Nants_telescope,
        )

    # Set up random number generator for reproducibility
    if args.seed is not None:
        rng = np.random.default_rng(args.seed)
    else:
        rng = np.random.default_rng()

    outputs = []
    total_subbands = min(args.subbands, config.num_subbands)
    subband_indices = list(range(total_subbands))
    if args.shuffle_subbands:
        random.shuffle(subband_indices)

    for subband in subband_indices:
        path = write_subband_uvh5(
            subband,
            uv_template,
            config,
            start_time,
            time_array,
            lst_array,
            integration_time,
            uvw_array,
            args.flux_jy,
            args.output,
            source_model=args.source_model,
            source_size_arcsec=args.source_size_arcsec,
            source_pa_deg=args.source_pa_deg,
            add_noise=args.add_noise,
            system_temperature_k=args.system_temp_k,
            add_cal_errors=args.add_cal_errors,
            gain_std=args.gain_std,
            phase_std_deg=args.phase_std_deg,
            rng=rng,
        )
        outputs.append(path)

    print("Generated synthetic subbands:")
    for path in outputs:
        print(f"  {path}")

    # Create synthetic catalog if requested
    if args.create_catalog:
        from dsa110_contimg.simulation.synthetic_catalog import (
            create_synthetic_catalog_from_uvh5,
        )

        # Use first output file to extract source positions
        uvh5_path = outputs[0]

        # Determine catalog output path
        if args.catalog_output is None:
            # Auto-generate path based on declination strip
            dec_strip = round(float(uv_template.phase_center_dec_degrees), 1)
            catalog_name = f"{args.catalog_type}_dec{dec_strip:+.1f}.sqlite3"
            catalog_output = args.output.parent / "catalogs" / catalog_name
        else:
            catalog_output = args.catalog_output

        print(f"\nCreating synthetic {args.catalog_type.upper()} catalog...")
        catalog_path = create_synthetic_catalog_from_uvh5(
            uvh5_path=uvh5_path,
            catalog_output_path=catalog_output,
            catalog_type=args.catalog_type,
            add_noise=True,  # Add realistic catalog errors
            rng=rng,
        )
        print(f"  Created: {catalog_path}")
        print("\nTo use in pipeline testing, set environment variable:")
        print(f"  export {args.catalog_type.upper()}_CATALOG={catalog_path}")

    # Print summary of features used
    features = []
    if args.source_model != "point":
        features.append(f"Extended source ({args.source_model}, {args.source_size_arcsec} arcsec)")
    if args.add_noise:
        features.append(f"Thermal noise (T_sys={args.system_temp_k}K)")
    if args.add_cal_errors:
        features.append(
            f"Calibration errors (gain_std={args.gain_std}, phase_std={args.phase_std_deg}deg)"
        )

    if features:
        print("\nFeatures enabled:")
        for feature in features:
            print(f"  - {feature}")
    else:
        print("\nUsing basic point source model (no noise, no cal errors)")

    # Validate generated files if validation module is available
    try:
        from dsa110_contimg.simulation.validate_synthetic import validate_uvh5_file

        print("\nValidating generated files...")
        all_valid = True
        for path in outputs:
            is_valid, errors = validate_uvh5_file(path)
            if is_valid:
                print(f"  :check_mark: {path.name}: Valid")
            else:
                print(f"  :ballot_x: {path.name}: Invalid - {errors}")
                all_valid = False
        if all_valid:
            print("\n:check_mark: All generated files validated successfully")
        else:
            print("\n:warning_sign: Some generated files failed validation")
    except ImportError:
        print("\n:warning_sign: Validation module not available, skipping validation")


if __name__ == "__main__":
    main()
