import argparse
from typing import List

from .flagging import reset_flags, flag_zeros, flag_rfi
from .calibration import solve_delay, solve_bandpass, solve_gains
from .applycal import apply_to_target
from .selection import select_bandpass_fields, select_bandpass_from_catalog
from .msfix import fix_field_num_poly, fix_spw_resolution, fix_main_sigma_weight


def run_calibrator(ms: str, cal_field: str, refant: str, *, do_flagging: bool = True) -> List[str]:
    # Normalize FIELD::NUM_POLY to avoid casacore interpolateDirMeas crashes
    try:
        changed = False
        if fix_field_num_poly(ms):
            print("Patched FIELD::NUM_POLY -> 0 for constant DIR")
            changed = True
        if fix_spw_resolution(ms):
            print("Filled SPW::RESOLUTION/EFFECTIVE_BW from CHAN_WIDTH")
            changed = True
        if fix_main_sigma_weight(ms):
            print("Filled MAIN::SIGMA/WEIGHT for missing rows")
            changed = True
    except Exception:
        pass
    if do_flagging:
        reset_flags(ms)
        flag_zeros(ms)
        flag_rfi(ms)
    ktabs = solve_delay(ms, cal_field, refant)
    bptabs = solve_bandpass(ms, cal_field, refant, ktabs[0])
    gtabs = solve_gains(ms, cal_field, refant, ktabs[0], bptabs)
    return ktabs[:1] + bptabs + gtabs


def main():
    p = argparse.ArgumentParser(description="CASA 6.7 calibration runner (no dsacalib)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("calibrate", help="Calibrate a calibrator MS")
    pc.add_argument("--ms", required=True)
    pc.add_argument("--field", required=False, default=None, help="Calibrator field name/index or range (e.g. 10~12)")
    pc.add_argument("--refant", required=False, default=None)
    pc.add_argument("--refant-ranking", help="Path to refant_ranking.json for auto selection")
    pc.add_argument("--auto-fields", action="store_true", help="Automatically select bandpass fields using calibrator info")
    pc.add_argument("--cal-ra-deg", type=float, help="Calibrator RA (deg) for auto field selection")
    pc.add_argument("--cal-dec-deg", type=float, help="Calibrator Dec (deg) for auto field selection")
    pc.add_argument("--cal-flux-jy", type=float, help="Calibrator flux (Jy) for weighting in auto selection")
    pc.add_argument("--cal-catalog", help="Path to VLA calibrator catalog for auto field selection")
    pc.add_argument("--cal-search-radius-deg", type=float, default=1.0, help="Search radius (deg) around catalog entries")
    pc.add_argument("--pt-dec-deg", type=float, help="Pointing declination (deg) for catalog weighting")
    pc.add_argument("--bp-window", type=int, default=3, help="Number of fields (approx) around peak to include")
    pc.add_argument("--no-flagging", action="store_true", help="Disable pre-solve flagging to avoid crashes on nonstandard polarizations")

    pt = sub.add_parser("apply", help="Apply calibration to target MS")
    pt.add_argument("--ms", required=True)
    pt.add_argument("--field", required=True)
    pt.add_argument("--tables", nargs="+", required=True, help="Calibration tables in order")

    args = p.parse_args()

    if args.cmd == "calibrate":
        field_sel = args.field
        if args.auto_fields:
            try:
                if args.cal_catalog:
                    if args.pt_dec_deg is None:
                        p.error("--auto-fields with --cal-catalog requires --pt-dec-deg")
                    sel, idxs, wflux, calinfo = select_bandpass_from_catalog(
                        args.ms,
                        args.cal_catalog,
                        search_radius_deg=float(args.cal_search_radius_deg or 1.0),
                        window=max(1, int(args.bp_window)),
                    )
                    name, ra_deg, dec_deg, flux_jy = calinfo
                    print(f"Catalog calibrator: {name} (RA {ra_deg:.4f} deg, Dec {dec_deg:.4f} deg, flux {flux_jy:.2f} Jy)")
                    print(f"Auto-selected bandpass fields: {sel} (indices: {idxs})")
                    field_sel = sel
                else:
                    if args.cal_ra_deg is None or args.cal_dec_deg is None or args.cal_flux_jy is None:
                        p.error("--auto-fields requires --cal-ra-deg/--cal-dec-deg/--cal-flux-jy or --cal-catalog")
                    sel, idxs, wflux = select_bandpass_fields(
                        args.ms,
                        args.cal_ra_deg,
                        args.cal_dec_deg,
                        args.cal_flux_jy,
                        window=max(1, int(args.bp_window)),
                    )
                    print(f"Auto-selected bandpass fields: {sel} (indices: {idxs})")
                    field_sel = sel
            except Exception as e:
                print(f"Auto field selection failed ({e}); falling back to --field")
                if field_sel is None:
                    p.error("No --field provided and auto selection failed")
        if field_sel is None:
            p.error("--field is required when --auto-fields is not used")

        # Determine reference antenna
        refant = args.refant
        if args.refant_ranking:
            import json
            try:
                with open(args.refant_ranking, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                rec = data.get('recommended') if isinstance(data, dict) else None
                if rec and rec.get('antenna_id') is not None:
                    refant = str(rec['antenna_id'])
                    print(f"Reference antenna (from ranking): {refant}")
            except Exception as e:
                print(f"Failed to read refant ranking ({e}); falling back to --refant")
        if refant is None:
            p.error("Provide --refant or --refant-ranking")

        tabs = run_calibrator(args.ms, field_sel, refant, do_flagging=(not args.no_flagging))
        print("Generated tables:\n" + "\n".join(tabs))
    elif args.cmd == "apply":
        apply_to_target(args.ms, args.field, args.tables)
        print("Applied calibration to target")


if __name__ == "__main__":
    main()
