#!/usr/bin/env python3
"""Extract layout parameters from a representative UVH5 capture."""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from pyuvdata import UVData

DEFAULT_OUTPUT = Path("simulation/config/reference_layout.json")


def _serialise_extra_keywords(extra_keywords: Dict[str, Any]) -> Dict[str, Any]:
    serialised: Dict[str, Any] = {}
    for key, value in extra_keywords.items():
        if isinstance(value, (np.floating, np.float64, np.float32)):
            serialised[key] = float(value)
        elif isinstance(value, (np.integer, np.int64, np.int32)):
            serialised[key] = int(value)
        elif isinstance(value, np.ndarray):
            serialised[key] = np.asarray(value).tolist()
        else:
            serialised[key] = value
    return serialised


def _float_list(array: np.ndarray) -> List[float]:
    return [float(x) for x in np.asarray(array).ravel()]


def analyse_uvh5(path: Path) -> Dict[str, Any]:
    uv = UVData()
    uv.read(path, file_type="uvh5", run_check=False, run_check_acceptability=False)

    info: Dict[str, Any] = {
        "filename": path.name,
        "npol": int(uv.Npols),
        "polarization_array": _float_list(uv.polarization_array),
        "nbls": int(uv.Nbls),
        "nblts": int(uv.Nblts),
        "nspws": int(uv.Nspws),
        "nfreqs": int(uv.Nfreqs),
        "freq_array_hz": _float_list(uv.freq_array.squeeze()),
        "channel_width_hz": float(np.mean(np.diff(uv.freq_array.squeeze()))),
        "integration_time_sec": float(np.mean(uv.integration_time)),
        "time_array_mjd": _float_list(uv.time_array),
        "time_span_sec": float(
            (uv.time_array.max() - uv.time_array.min()) * 86400.0
            if uv.time_array.size > 1
            else 0.0
        ),
        "uvw_order": "ij" if uv.uvplane_reference_time is None else "uvh5-default",
        "extra_keywords": _serialise_extra_keywords(uv.extra_keywords),
    }

    if uv.lst_array is not None and uv.lst_array.size:
        info["lst_array_rad"] = _float_list(uv.lst_array)
        if uv.lst_array.size > 1:
            lst_step = np.median(np.diff(np.unwrap(uv.lst_array)))
            info["lst_step_rad"] = float(lst_step)

    # Derive file naming hints, e.g. *_sbXX.hdf5
    if "_sb" in path.stem:
        prefix, suffix = path.stem.split("_sb", maxsplit=1)
        if suffix.isdigit():
            info["filename_prefix"] = prefix
            info["subband_digits"] = len(suffix)
            info["filename_pattern"] = f"{prefix}_sb{'#' * len(suffix)}.hdf5"

    # Convert polarization array to ints (pyuvdata stores as ints already but ensure JSON-safe)
    info["polarization_array"] = [int(x) for x in info["polarization_array"]]

    return info


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract UVH5 layout metadata for synthetic data generation"
    )
    parser.add_argument("uvh5", type=Path, help="Path to representative UVH5 file")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Where to write JSON metadata (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()

    info = analyse_uvh5(args.uvh5)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as fh:
        json.dump(info, fh, indent=2, sort_keys=True)
        fh.write("\n")

    print(f"Wrote layout metadata to {args.output}")


if __name__ == "__main__":
    main()
