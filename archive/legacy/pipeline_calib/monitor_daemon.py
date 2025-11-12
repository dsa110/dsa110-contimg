#!/usr/bin/env python3
"""
Calibrator monitor daemon (skeleton).

Responsibilities:
- Build a declination-specific calibrator list from VLA catalog.
- Compute transit times for candidates and pick the best observation windows.
- When a calibrator pass is available (or a calibrator MS is provided),
  run K/B/G solves using CASA and register the resulting tables in the
  calibration registry with a validity window.

Two modes:
  1) one-shot `solve-and-register` for a given calibrator MS
  2) `monitor-loop` that polls on a cadence and triggers solves near transit

Note: CASA must be available in the Python environment for solving.
"""

import argparse
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

# Heavy CASA/astropy imports are made inside command handlers so that --help
# works even outside the CASA environment.
from dsa110_contimg.database.registry import ensure_db, register_set_from_prefix
from dsa110_contimg.calibration.calibration import solve_delay, solve_bandpass, solve_gains
from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.calibration.imaging import quick_image


logger = logging.getLogger("cal_monitor")


@dataclass
class SolveContext:
    ms_cal: str
    cal_field: str
    refant: str
    set_name: str
    registry_db: Path
    valid_window_min: float


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _solve_and_register(ctx: SolveContext) -> None:
    ms = ctx.ms_cal
    cal_field = ctx.cal_field
    refant = ctx.refant

    # Solve tables using CASA tasks
    ktabs = solve_delay(ms, cal_field, refant)
    bptabs = solve_bandpass(ms, cal_field, refant, ktabs[0])
    gtabs = solve_gains(ms, cal_field, refant, ktabs[0], bptabs)

    prefix = f"{ms.rstrip('.ms')}_{cal_field}"
    # Compute default validity window around now; can be overridden via CLI
    # Here we do not compute transit, since this is a one-shot; monitor-loop computes it.
    # Use obs mid-time as a proxy if available later.
    valid_min = ctx.valid_window_min
    valid_days = valid_min / (24 * 60)
    mid_mjd = None  # Unknown without MS inspection; registry will accept None

    register_set_from_prefix(
        ctx.registry_db,
        ctx.set_name,
        prefix=Path(prefix),
        cal_field=cal_field,
        refant=refant,
        valid_start_mjd=(mid_mjd - valid_days) if mid_mjd else None,
        valid_end_mjd=(mid_mjd + valid_days) if mid_mjd else None,
        status="active",
    )
    logger.info("Registered calibration set '%s' from prefix %s", ctx.set_name, prefix)


def cmd_solve_and_register(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    ctx = SolveContext(
        ms_cal=args.ms,
        cal_field=args.field,
        refant=args.refant,
        set_name=args.set_name or Path(args.ms).stem,
        registry_db=Path(args.registry_db),
        valid_window_min=float(args.valid_window),
    )
    ensure_db(ctx.registry_db)
    _solve_and_register(ctx)
    return 0


def cmd_monitor_loop(args: argparse.Namespace) -> int:
    setup_logging(args.log_level)
    registry_db = Path(args.registry_db)
    ensure_db(registry_db)

    import astropy.units as u
    from astropy.time import Time
    from dsa110_contimg.calibration.catalogs import read_vla_calibrator_catalog, update_caltable
    from dsa110_contimg.calibration.schedule import next_transit_time

    vla_df = read_vla_calibrator_catalog(args.vla_catalog)
    pt_dec = float(args.pt_dec_deg) * u.deg
    cal_csv = update_caltable(vla_df, pt_dec)
    logger.info("Prepared declination-specific calibrator CSV: %s", cal_csv)

    # In a full implementation we'd also monitor data arrival and pick files near transit.
    # For now, this loop sleeps and logs the next transit time of a named calibrator.
    while True:
        try:
            t0 = Time.now()
            ttran = next_transit_time(args.cal_ra_deg, t0.mjd)
            logger.info(
                "Next transit for RA=%.3f deg at %s (MJD %.5f)",
                args.cal_ra_deg,
                ttran.isot,
                ttran.mjd,
            )
        except Exception as e:
            logger.warning("Failed transit computation: %s", e)
        time.sleep(float(args.poll_interval))

    # Unreachable
    # return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Calibrator monitor daemon (skeleton)")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("solve-and-register", help="Run solves on a calibrator MS and register tables")
    sp.add_argument("--ms", required=True, help="Path to calibrator MS")
    sp.add_argument("--field", required=True, help="Calibrator field name/index")
    sp.add_argument("--refant", required=True, help="Reference antenna (e.g., '23')")
    sp.add_argument("--set-name", help="Logical set name for the registry (default: MS basename)")
    sp.add_argument("--registry-db", required=True, help="Path to registry SQLite DB")
    sp.add_argument("--valid-window", type=float, default=120.0, help="Validity window in minutes")
    sp.add_argument("--log-level", default="INFO")
    sp.set_defaults(func=cmd_solve_and_register)

    sp = sub.add_parser("monitor-loop", help="Log next transit times; future: trigger solves near transit")
    sp.add_argument("--vla-catalog", required=True, help="Path to VLA calibrator text file")
    sp.add_argument("--pt-dec-deg", type=float, required=True, help="Pointing declination (deg)")
    sp.add_argument("--cal-ra-deg", type=float, required=True, help="RA of chosen calibrator (deg)")
    sp.add_argument("--registry-db", required=True)
    sp.add_argument("--poll-interval", type=float, default=300.0)
    sp.add_argument("--log-level", default="INFO")
    sp.set_defaults(func=cmd_monitor_loop)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    p = build_parser()
    args = p.parse_args(argv)
    if not hasattr(args, 'func'):
        p.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
