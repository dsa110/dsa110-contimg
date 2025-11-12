#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

from casatools import ms as ms_tool_mod, table as table_tool_mod
from casatasks import gaincal, bandpass, applycal, ft, clearcal

from dsa110.calibration.calibrator_finder import CalibratorFinder
from dsa110.calibration.skymodel_builder import SkyModelBuilder
from dsa110.calibration.provenance import write_provenance
from dsa110.utils.casa_logging import ensure_casa_log_directory, force_casa_logging_to_directory


def read_field_center(ms_path: str) -> Optional[Dict[str, float]]:
    tb = table_tool_mod()
    try:
        tb.open(f"{ms_path}/FIELD")
        phase_dir = tb.getcol('PHASE_DIR')
        # shape (nrows, 2) or (2, nrows); normalize to [ra, dec]
        if phase_dir is None:
            return None
        if len(phase_dir.shape) == 2:
            ra_rad, dec_rad = float(phase_dir[0][0]), float(phase_dir[1][0])
        elif len(phase_dir.shape) == 1:
            ra_rad, dec_rad = float(phase_dir[0]), float(phase_dir[1])
        else:
            return None
        return {"ra_deg": ra_rad * 180.0 / 3.141592653589793, "dec_deg": dec_rad * 180.0 / 3.141592653589793}
    finally:
        try:
            tb.close()
        except Exception:
            pass


def mk_cal_table_name(ms_path: str, kind: str) -> str:
    base = os.path.splitext(os.path.basename(ms_path.rstrip('/')))[0]
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    return f"{base}_{kind}_{ts}.table"


def make_symlink(target_path: str, link_path: str):
    try:
        if os.path.islink(link_path) or os.path.exists(link_path):
            os.remove(link_path)
        os.symlink(os.path.basename(target_path), link_path)
    except Exception:
        pass


def choose_calibrator(ra_deg: float, dec_deg: float, radius_deg: float, min_flux_jy: float) -> Optional[Dict[str, Any]]:
    finder = CalibratorFinder(use_cache=True, allow_online_fallback=True)
    cands = finder.find_nearby(ra_deg, dec_deg, radius_deg=radius_deg, min_flux_jy=min_flux_jy)
    if not cands:
        return None
    c = cands[0]
    return {
        "name": c.name,
        "ra_deg": c.ra_deg,
        "dec_deg": c.dec_deg,
        "flux_jy_ref": c.flux_jy_ref,
        "ref_freq_hz": c.ref_freq_hz,
        "spectral_index": c.spectral_index,
        "separation_deg": c.separation_deg,
        "provenance": c.provenance,
    }


def build_component_list(cal: Dict[str, Any], out_dir: str) -> str:
    builder = SkyModelBuilder(output_dir=out_dir)
    sm = builder.build_point_sources(
        names=[cal["name"]],
        ras_deg=[cal["ra_deg"]],
        decs_deg=[cal["dec_deg"]],
        fluxes_jy=[float(cal["flux_jy_ref"]) if cal["flux_jy_ref"] is not None else 1.0],
        ref_freq_hz=float(cal["ref_freq_hz"]) if cal["ref_freq_hz"] is not None else 1.4e9,
    )
    return builder.write_casa_component_list(sm, out_name=f"cal_{cal['name']}")


def run(args: argparse.Namespace) -> int:
    # Force CASA logs into logs/casa
    log_dir = 'logs/casa'
    ensure_casa_log_directory({'paths': {'casa_log_dir': log_dir}})
    force_casa_logging_to_directory(log_dir)

    ms_path = args.ms
    cal_dir = args.cal_tables
    os.makedirs(cal_dir, exist_ok=True)

    # Determine field center
    center = read_field_center(ms_path) or {"ra_deg": args.ra, "dec_deg": args.dec}
    if center is None:
        print("ERROR: Could not determine field center and no RA/Dec provided")
        return 2

    # Choose calibrator
    cal = choose_calibrator(center["ra_deg"], center["dec_deg"], args.radius_deg, args.min_flux_jy)
    if cal is None:
        print("ERROR: No suitable calibrator found")
        return 3

    # Build and inject model
    cl_dir = args.skymodels
    os.makedirs(cl_dir, exist_ok=True)
    cl_path = build_component_list(cal, cl_dir)
    clearcal(vis=ms_path, addmodel=False)
    ft(vis=ms_path, complist=cl_path, usescratch=True)

    # Delay (approximate, phase-only if K not available)
    g0_name = mk_cal_table_name(ms_path, "G0")
    g0_path = os.path.join(cal_dir, g0_name)
    gaincal(
        vis=ms_path,
        caltable=g0_path,
        field=args.field,
        refant=args.refant,
        solint=args.delay_solint,
        calmode='p',
        minsnr=0.5,
        combine=args.combine,
    )

    # Bandpass
    b0_name = mk_cal_table_name(ms_path, "B0")
    b0_path = os.path.join(cal_dir, b0_name)
    bandpass(
        vis=ms_path,
        caltable=b0_path,
        field=args.field,
        refant=args.refant,
        solint=args.bp_solint,
        combine=args.combine,
        minsnr=0.5,
        solnorm=True,
        gaintable=[g0_path],
    )

    # Final gains (amplitude+phase)
    g1_name = mk_cal_table_name(ms_path, "G1")
    g1_path = os.path.join(cal_dir, g1_name)
    gaincal(
        vis=ms_path,
        caltable=g1_path,
        field=args.field,
        refant=args.refant,
        solint=args.g_solint,
        calmode='ap',
        minsnr=0.5,
        combine=args.combine,
        gaintable=[b0_path, g0_path],
    )

    # Apply
    applycal(
        vis=ms_path,
        field=args.field,
        gaintable=[b0_path, g0_path, g1_path],
        calwt=True,
        applymode='calonly',
    )

    # Symlinks (.bcal/.gcal)
    make_symlink(b0_path, os.path.join(cal_dir, 'latest.bcal'))
    make_symlink(g1_path, os.path.join(cal_dir, 'latest.gcal'))

    # Provenance JSON
    prov = {
        "ms": ms_path,
        "field_center": center,
        "calibrator": cal,
        "component_list": cl_path,
        "refant": args.refant,
        "solints": {"delay": args.delay_solint, "bandpass": args.bp_solint, "gain": args.g_solint},
        "combine": args.combine,
        "tables": {"G0": g0_path, "B0": b0_path, "G1": g1_path},
        "timestamp_utc": datetime.utcnow().isoformat() + 'Z',
    }
    write_provenance(prov, output_dir=cal_dir, basename='calibration_provenance')

    print(json.dumps({"success": True, "bcal": b0_path, "gcal": g1_path, "component_list": cl_path}, indent=2))
    return 0


def main():
    p = argparse.ArgumentParser(description="Run K→B→G calibration with calibrator selection and provenance")
    p.add_argument('--ms', required=True, help='Path to MS')
    p.add_argument('--field', default='0', help='Field selection (default 0)')
    p.add_argument('--cal-tables', default='data/cal_tables', help='Calibration tables directory')
    p.add_argument('--skymodels', default='data/sky_models', help='Component lists directory')
    p.add_argument('--radius-deg', type=float, default=3.0, help='Search radius for calibrators')
    p.add_argument('--min-flux-jy', type=float, default=0.2, help='Minimum flux density for calibrators')
    p.add_argument('--refant', default='0', help='Reference antenna')
    p.add_argument('--delay-solint', default='inf', help='Delay solve solint')
    p.add_argument('--bp-solint', default='inf', help='Bandpass solve solint')
    p.add_argument('--g-solint', default='inf', help='Gain solve solint')
    p.add_argument('--combine', default='scan', help='CASA combine parameter (e.g., scan,spw)')
    p.add_argument('--ra', type=float, default=None, help='Fallback RA deg for field center')
    p.add_argument('--dec', type=float, default=None, help='Fallback Dec deg for field center')
    args = p.parse_args()
    raise SystemExit(run(args))


if __name__ == '__main__':
    main()


