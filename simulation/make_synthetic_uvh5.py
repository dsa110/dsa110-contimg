#!/usr/bin/env python3
"""Generate synthetic DSA-110 UVH5 subband files for end-to-end testing."""

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import numpy as np
import yaml
import h5py
from astropy.coordinates import EarthLocation
from astropy.time import Time
import astropy.units as u
from pyuvdata import UVData

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from uvh5_to_ms_converter import calc_uvw_blt
from antpos_local import get_itrf
from uvh5_to_ms_converter import OVRO_LAT, OVRO_LON, OVRO_ALT

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
    if freq_template.size > 0 and norm_freq_order == "desc" and freq_template[0] < freq_template[-1]:
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


def build_time_arrays(config: TelescopeConfig, template: UVData, start_time: Time):
    nbls = template.Nbls
    ntimes = template.Ntimes
    dt_days = config.integration_time_sec / SECONDS_PER_DAY

    unique_times = start_time.mjd + dt_days * np.arange(ntimes)
    time_array = np.repeat(unique_times, nbls)

    lst = Time(unique_times, format="mjd", scale="utc", location=config.site_location)
    lst_array = np.repeat(lst.sidereal_time('apparent').rad, nbls)

    integration_time = np.full(time_array.shape, config.integration_time_sec, dtype=float)
    return unique_times, time_array, lst_array, integration_time


def build_uvw(template: UVData, config: TelescopeConfig, unique_times_mjd: np.ndarray) -> np.ndarray:
    nbls = template.Nbls
    ntimes = template.Ntimes

    ant_df = get_itrf(latlon_center=(OVRO_LAT * u.rad, OVRO_LON * u.rad, OVRO_ALT * u.m))
    ant_offsets = {}
    missing = []
    for ant in range(template.Nants_telescope):
        station = ant + 1
        if station in ant_df.index:
            row = ant_df.loc[station]
            ant_offsets[ant] = np.array([row['dx_m'], row['dy_m'], row['dz_m']], dtype=float)
        else:
            missing.append(station)
    if missing:
        raise ValueError(f"Missing antenna offsets for stations: {missing}")

    ant1 = template.ant_1_array[:nbls]
    ant2 = template.ant_2_array[:nbls]
    blen = np.zeros((nbls, 3))
    for idx, (a1, a2) in enumerate(zip(ant1, ant2)):
        blen[idx] = ant_offsets[int(a2)] - ant_offsets[int(a1)]

    uvw = np.zeros((nbls * ntimes, 3), dtype=float)
    for tidx, mjd in enumerate(unique_times_mjd):
        start = tidx * nbls
        stop = start + nbls
        time_vec = np.full(nbls, mjd)
        uvw[start:stop] = calc_uvw_blt(
            blen,
            time_vec,
            'J2000',
            np.full(nbls, config.phase_ra.to_value(u.rad)) * u.rad,
            np.full(nbls, config.phase_dec.to_value(u.rad)) * u.rad,
        )
    return uvw


def make_visibilities(template: UVData, amplitude_jy: float) -> np.ndarray:
    shape = (template.Nblts, template.Nspws, template.Nfreqs, template.Npols)
    value = amplitude_jy / 2.0  # split unpolarized flux equally between XX and YY
    vis = np.full(shape, value, dtype=np.complex64)
    return vis


def write_subband_uvh5(
    subband_index: int,
    template: UVData,
    config: TelescopeConfig,
    start_time: Time,
    times_mjd: np.ndarray,
    lst_array: np.ndarray,
    integration_time: np.ndarray,
    uvw_array: np.ndarray,
    amplitude_jy: float,
    output_dir: Path,
) -> Path:
    uv = template.copy()
    uv.history += f"\nSynthetic point-source dataset generated (subband {subband_index:02d})."

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
    uv.Nfreqs = nchan
    uv.Nspws = 1

    uv.time_array = times_mjd
    uv.lst_array = lst_array
    uv.integration_time = integration_time
    uv.uvw_array = uvw_array

    uv.data_array = make_visibilities(uv, amplitude_jy)
    uv.flag_array = np.zeros_like(uv.data_array, dtype=bool)
    uv.nsample_array = np.ones_like(uv.data_array, dtype=np.float32)

    uv.extra_keywords.update(config.extra_keywords)
    uv.extra_keywords['phase_center_dec'] = config.phase_dec.to_value(u.rad)
    uv.extra_keywords['ha_phase_center'] = 0.0
    uv.extra_keywords['phase_center_epoch'] = 'HADEC'

    uv.phase_center_ra = config.phase_ra.to_value(u.rad)
    uv.phase_center_dec = config.phase_dec.to_value(u.rad)
    uv.phase_center_frame = 'icrs'
    uv.phase_center_epoch = 2000.0

    anchor = start_time.iso.replace('-', '').replace(':', '')
    anchor_str = start_time.strftime('%Y-%m-%dT%H:%M:%S')
    filename = f"{anchor_str}_sb{subband_index:02d}.hdf5"
    output_path = output_dir / filename
    output_dir.mkdir(parents=True, exist_ok=True)
    uv.write_uvh5(output_path, run_check=False, clobber=True)

    with h5py.File(output_path, "r+") as handle:
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
        default=Path("output/ms/test_8subbands_concatenated.hdf5"),
        help="Reference UVH5 file for metadata scaffolding",
    )
    parser.add_argument(
        "--layout-meta",
        type=Path,
        default=Path("simulation/config/reference_layout.json"),
        help="JSON metadata produced by analyse_reference_uvh5.py",
    )
    parser.add_argument(
        "--telescope-config",
        type=Path,
        default=Path("simulation/pyuvsim/telescope.yaml"),
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    layout_meta = load_reference_layout(args.layout_meta)
    config = load_telescope_config(args.telescope_config, layout_meta, args.freq_order)

    if args.subbands != config.num_subbands:
        print(
            f"WARNING: Requested {args.subbands} subbands,"
            f" but configuration expects {config.num_subbands}."
        )

    uv_template = UVData()
    uv_template.read(
        args.template,
        file_type='uvh5',
        run_check=False,
        run_check_acceptability=False,
        strict_uvw_antpos_check=False,
    )

    start_time = Time(args.start_time, format='isot', scale='utc')
    unique_times, time_array, lst_array, integration_time = build_time_arrays(
        config, uv_template, start_time
    )
    uvw_array = build_uvw(uv_template, config, unique_times)

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
        )
        outputs.append(path)

    print("Generated synthetic subbands:")
    for path in outputs:
        print(f"  {path}")


if __name__ == "__main__":
    main()
