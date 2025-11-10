# -*- coding: utf-8 -*-
"""Synthetic end-to-end smoke test (conversion → calibration).

Usage:
  python tests/scripts/synthetic_end_to_end.py /tmp/contimg_synth

Writes two UVH5 subbands, converts to MS via orchestrator (pyuvdata writer),
then runs calibration with permissive BP settings.
"""


import sys
from pathlib import Path
import subprocess


def run(cmd):
    print("$", " ".join(cmd))
    subprocess.check_call(cmd)


def main(out_dir):
    out = Path(out_dir)
    data_dir = out / "uvh5"
    ms_dir = out / "ms"
    ms_dir.mkdir(parents=True, exist_ok=True)

    # 1) Write two UVH5 subbands
    # Ensure 'tests' utils are on sys.path
    this_dir = Path(__file__).resolve().parent
    tests_dir = this_dir.parent
    if str(tests_dir) not in sys.path:
        sys.path.insert(0, str(tests_dir))
    from utils.synthetic_uvh5 import write_two_subbands

    write_two_subbands(data_dir, basename="synthetic")

    # 2) Convert to MS (use writer=pyuvdata for <=2 subbands)
    # Use the conversion CLI that discovers groups by time window; for synthetic,
    # we directly invoke the writer via orchestrator with a wide time window.
    start = "2020-01-01 00:00:00"
    end = "2030-01-01 00:00:00"
    run(
        [
            sys.executable,
            "-m",
            "dsa110_contimg.conversion.strategies.hdf5_orchestrator",
            str(data_dir),
            str(ms_dir),
            start,
            end,
            "--writer",
            "pyuvdata",
        ]
    )

    # Find produced MS
    mss = list(ms_dir.glob("*.ms"))
    assert mss, "No MS produced by conversion"
    ms_path = str(mss[0])

    # 3) Calibrate (zeros-only flagging, no UV cut, BP minsnr=3)
    run(
        [
            sys.executable,
            "-m",
            "dsa110_contimg.calibration.cli",
            "calibrate",
            "--ms",
            ms_path,
            "--field",
            "0",
            "--refant",
            "0",
            "--flagging-mode",
            "zeros",
            "--bp-minsnr",
            "3.0",
            "--bp-combine-field",
            "--model-source",
            "catalog",
            "--prebp-phase",
        ]
    )

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/contimg_synth"))
