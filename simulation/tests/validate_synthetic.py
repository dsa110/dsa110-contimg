#!/usr/bin/env python3
"""Validate synthetic UVH5 data products and run converter smoke test."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import h5py
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SYNTH_DIR = PROJECT_ROOT / "simulation/output"
DEFAULT_REFERENCE = PROJECT_ROOT / "output/ms/test_8subbands_concatenated.hdf5"
DEFAULT_LAYOUT = PROJECT_ROOT / "simulation/config/reference_layout.json"
DEFAULT_CONVERTER = PROJECT_ROOT / "uvh5_to_ms_converter.py"
DEFAULT_CONVERTER_OUTPUT = PROJECT_ROOT / "simulation/output/ms_validator"


def _load_layout(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _extract_header_metrics(path: Path) -> dict:
    with h5py.File(path, "r") as handle:
        hdr = handle["Header"]
        metrics = {
            "npol": int(hdr["Npols"][()]),
            "polarization_array": np.array(hdr["polarization_array"][()]),
            "nfreqs": int(hdr["Nfreqs"][()]),
            "channel_widths": np.abs(np.array(hdr["channel_width"][()]).reshape(-1)),
            "ntimes": int(hdr["Ntimes"][()]),
            "extra_keys": set(hdr["extra_keywords"].keys()),
        }
    return metrics


def _validate_schema(synth_files, reference_metrics, layout_meta):
    expected_npol = layout_meta.get("npol", reference_metrics["npol"])
    expected_pol_array = np.array(layout_meta.get("polarization_array", reference_metrics["polarization_array"]))
    expected_nfreqs = layout_meta.get("nfreqs", reference_metrics["nfreqs"])
    expected_width = abs(layout_meta.get("channel_width_hz", np.mean(reference_metrics["channel_widths"])) )
    expected_ntimes = reference_metrics["ntimes"]
    expected_extra = reference_metrics["extra_keys"]

    failures = []
    for path in synth_files:
        metrics = _extract_header_metrics(path)
        if metrics["npol"] != expected_npol:
            failures.append(f"{path.name}: Npols {metrics['npol']} != {expected_npol}")
        if not np.array_equal(metrics["polarization_array"], expected_pol_array):
            failures.append(f"{path.name}: polarization_array mismatch")
        if metrics["nfreqs"] != expected_nfreqs:
            failures.append(f"{path.name}: Nfreqs {metrics['nfreqs']} != {expected_nfreqs}")
        if not np.allclose(metrics["channel_widths"], expected_width, rtol=1e-6, atol=1e-3):
            failures.append(f"{path.name}: channel width deviation detected")
        if metrics["ntimes"] != expected_ntimes:
            failures.append(f"{path.name}: Ntimes {metrics['ntimes']} != {expected_ntimes}")
        missing_extra = expected_extra - metrics["extra_keys"]
        if missing_extra:
            failures.append(f"{path.name}: missing extra_keywords {sorted(missing_extra)}")
    if failures:
        raise AssertionError("Schema validation failed:\n" + "\n".join(failures))


def _derive_time_range(datasets):
    timestamps = []
    for path in datasets:
        stem = path.stem
        if "_sb" not in stem:
            continue
        ts = stem.split("_sb")[0]
        timestamps.append(datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S"))
    if not timestamps:
        raise ValueError("Unable to parse timestamps from synthetic filenames")
    start = min(timestamps) - timedelta(seconds=1)
    end = max(timestamps) + timedelta(seconds=1)
    return start, end


def _run_converter(converter, synthetic_dir, start, end, output_dir, log_level="DEBUG"):
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(converter),
        str(synthetic_dir),
        str(output_dir),
        start.strftime("%Y-%m-%d %H:%M:%S"),
        end.strftime("%Y-%m-%d %H:%M:%S"),
        "--log-level",
        log_level,
    ]
    subprocess.run(cmd, check=True)

    ms_dirs = list(output_dir.glob("*.ms"))
    if not ms_dirs:
        raise AssertionError(f"Converter produced no Measurement Sets in {output_dir}")
    return ms_dirs


def main():
    parser = argparse.ArgumentParser(description="Validate synthetic UVH5 dataset")
    parser.add_argument("--synthetic-dir", type=Path, default=DEFAULT_SYNTH_DIR,
                        help="Directory containing synthetic *_sb??.hdf5 files")
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE,
                        help="Reference UVH5 file for metadata comparison")
    parser.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT,
                        help="JSON layout metadata from analyse_reference_uvh5")
    parser.add_argument("--converter", type=Path, default=DEFAULT_CONVERTER,
                        help="Path to uvh5_to_ms_converter.py")
    parser.add_argument("--converter-output", type=Path, default=DEFAULT_CONVERTER_OUTPUT,
                        help="Directory to place converter Measurement Sets")
    parser.add_argument("--log-level", default="DEBUG",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Log level for converter execution")
    parser.add_argument("--max-subbands", type=int, default=None,
                        help="Limit number of synthetic subbands to validate (default all)")
    parser.add_argument("--skip-converter", action="store_true",
                        help="Validate UVH5 headers only, skip converter execution")
    args = parser.parse_args()

    synth_files = sorted(args.synthetic_dir.glob("*_sb??.hdf5"))
    if len(synth_files) != 16:
        raise AssertionError(f"Expected 16 synthetic subbands, found {len(synth_files)} in {args.synthetic_dir}")

    subset_dir = args.synthetic_dir
    temp_dir = None
    if args.max_subbands is not None:
        synth_files = synth_files[: args.max_subbands]
        if len(synth_files) < len(list(args.synthetic_dir.glob("*_sb??.hdf5"))):
            temp_dir = tempfile.TemporaryDirectory(prefix="synthetic_subset_")
            subset_dir = Path(temp_dir.name)
            subset_dir.mkdir(parents=True, exist_ok=True)
            for path in synth_files:
                shutil.copy2(path, subset_dir / path.name)

    reference_metrics = _extract_header_metrics(args.reference)
    layout_meta = _load_layout(args.layout)

    _validate_schema(synth_files, reference_metrics, layout_meta)

    if args.skip_converter:
        print("Schema validation complete (converter skipped)")
        print(f"Synthetic files checked: {len(synth_files)}")
        return

    start, end = _derive_time_range(synth_files)
    try:
        ms_dirs = _run_converter(args.converter, subset_dir, start, end, args.converter_output, args.log_level)
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()

    print("Validation complete")
    print(f"Synthetic files checked: {len(synth_files)}")
    print(f"Converter output MS directories: {len(ms_dirs)}")
    for ms in ms_dirs:
        print(f"  - {ms}")


if __name__ == "__main__":
    main()
