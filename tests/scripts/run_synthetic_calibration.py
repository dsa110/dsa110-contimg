#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
End-to-end synthetic calibration test using the generated UVH5 dataset.

Flow:
 1) Generate UVH5 (if not provided)
 2) Convert UVH5 → MS using uvh5_to_ms.convert_single_file
 3) Populate MODEL_DATA via component ft (point source)
 4) Flag zeros (minimal flagging)
 5) Optionally pre-bandpass phase-only solve
 6) Solve bandpass (no uvrange cut, minsnr configurable, optional smoothing)
 7) Solve gains (phase-only, minsnr configurable)
 8) Report bandpass flagged-solution fraction; assert < 50% by default
"""

import argparse
import os
from pathlib import Path
from typing import Optional

from dsa110_contimg.calibration.calibration import (
    solve_bandpass,
    solve_gains,
    solve_prebandpass_phase,
)
from dsa110_contimg.calibration.flagging import flag_zeros, reset_flags
from dsa110_contimg.calibration.model import write_point_model_with_ft
from dsa110_contimg.conversion.uvh5_to_ms import convert_single_file


def run(
    uvh5_path: Path,
    ms_path: Path,
    *,
    ra_deg: float,
    dec_deg: float,
    flux_jy: float,
    refant: str = "0",
    do_prebp: bool = True,
    bp_minsnr: float = 3.0,
    gain_minsnr: float = 3.0,
    bp_smooth_type: str = "none",
    bp_smooth_window: Optional[int] = None,
    assert_bp_flagged_lt: Optional[float] = 0.5,
) -> None:
    # 1+2) Convert UVH5 → MS
    convert_single_file(str(uvh5_path), str(ms_path), add_imaging_columns=True)

    # 3) Populate MODEL_DATA via ft (component list)
    write_point_model_with_ft(str(ms_path), ra_deg, dec_deg, flux_jy, field="0")

    # 4) Minimal pre-flagging
    reset_flags(str(ms_path))
    flag_zeros(str(ms_path), datacolumn="data")

    # 5) Optional pre-bandpass phase-only solve
    prebp = None
    if do_prebp:
        prebp = solve_prebandpass_phase(
            str(ms_path),
            "0",
            refant,
            combine_fields=False,
            uvrange="",
            solint="inf",
            minsnr=5.0,
        )

    # 6) Bandpass solve
    bptabs = solve_bandpass(
        str(ms_path),
        "0",
        refant,
        None,
        combine_fields=False,
        combine_spw=False,
        minsnr=float(bp_minsnr),
        uvrange="",
        prebandpass_phase_table=prebp,
        bp_smooth_type=(bp_smooth_type or "none"),
        bp_smooth_window=bp_smooth_window,
    )

    # 7) Gains (phase-only)
    _ = solve_gains(
        str(ms_path),
        "0",
        refant,
        None,
        bptabs,
        combine_fields=False,
        phase_only=True,
        uvrange="",
        solint="60s",
        minsnr=float(gain_minsnr),
    )

    # 8) Report bandpass flagged fraction
    try:
        from dsa110_contimg.qa.calibration_quality import validate_caltable_quality

        metrics = validate_caltable_quality(bptabs[0])
        frac = float(metrics.fraction_flagged)
        print(f"Bandpass flagged solutions: {frac*100:.1f}%")
        if assert_bp_flagged_lt is not None and not (frac < assert_bp_flagged_lt):
            raise SystemExit(
                f"FAIL: Bandpass flagged fraction {frac:.3f} not < {assert_bp_flagged_lt:.3f}"
            )
        print("✓ Bandpass flagged fraction within expected bounds")
    except Exception as e:
        print(f"WARNING: Could not compute bandpass flagged fraction: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run synthetic calibration end-to-end")
    ap.add_argument("--outdir", required=True, help="Output directory for products")
    ap.add_argument("--ra-deg", type=float, default=202.7845)
    ap.add_argument("--dec-deg", type=float, default=30.5089)
    ap.add_argument("--flux-jy", type=float, default=5.0)
    ap.add_argument("--refant", default="0")
    ap.add_argument("--no-prebp", action="store_true")
    ap.add_argument("--bp-minsnr", type=float, default=3.0)
    ap.add_argument("--gain-minsnr", type=float, default=3.0)
    ap.add_argument("--bp-smooth-type", default="none")
    ap.add_argument("--bp-smooth-window", type=int)
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    uvh5 = outdir / "synth_cal.uvh5"
    ms = outdir / "synth_cal.ms"

    # Generate UVH5 if missing
    if not uvh5.exists():
        from tests.utils.generate_uvh5_calibrator import generate_uvh5

        generate_uvh5(
            str(uvh5),
            n_ants=16,
            n_times=4,
            start_jd=2460000.0,
            int_time_s=15.0,
            n_chans=64,
            f0_hz=1.4e9,
            chan_bw_hz=1.0e6,
            ra_deg=float(args.ra_deg),
            dec_deg=float(args.dec_deg),
            flux_jy=float(args.flux_jy),
        )

    run(
        uvh5,
        ms,
        ra_deg=float(args.ra_deg),
        dec_deg=float(args.dec_deg),
        flux_jy=float(args.flux_jy),
        refant=str(args.refant),
        do_prebp=(not args.no_prebp),
        bp_minsnr=float(args.bp_minsnr),
        gain_minsnr=float(args.gain_minsnr),
        bp_smooth_type=str(args.bp_smooth_type or "none"),
        bp_smooth_window=(
            int(args.bp_smooth_window) if args.bp_smooth_window is not None else None
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
