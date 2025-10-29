import argparse
import time
from typing import List

from .flagging import reset_flags, flag_zeros, flag_rfi
from .calibration import solve_delay, solve_bandpass, solve_gains
from .applycal import apply_to_target
from .selection import select_bandpass_fields, select_bandpass_from_catalog
try:
    # Ensure casacore temp files go to scratch, not the repo root
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment
except Exception:  # pragma: no cover
    prepare_temp_environment = None  # type: ignore


def run_calibrator(ms: str, cal_field: str, refant: str, *,
                   do_flagging: bool = True) -> List[str]:
    """Run K, BP and G solves on a calibrator MS.

    Note: On-the-fly MS metadata repair has been removed. If a dataset is
    malformed, prefer reconversion with the current writer.
    """
    if do_flagging:
        reset_flags(ms)
        flag_zeros(ms)
        flag_rfi(ms)
    ktabs = solve_delay(ms, cal_field, refant)
    bptabs = solve_bandpass(ms, cal_field, refant, ktabs[0])
    gtabs = solve_gains(ms, cal_field, refant, ktabs[0], bptabs)
    return ktabs[:1] + bptabs + gtabs


def main():
    # Best-effort: route TempLattice and similar to scratch
    try:
        if prepare_temp_environment is not None:
            prepare_temp_environment(os.getenv('CONTIMG_SCRATCH_DIR') or '/scratch/dsa110-contimg')
    except Exception:
        pass
    p = argparse.ArgumentParser(
        description="CASA 6.7 calibration runner (no dsacalib)")
    sub = p.add_subparsers(dest="cmd", required=True)

    pc = sub.add_parser("calibrate", help="Calibrate a calibrator MS")
    pc.add_argument("--ms", required=True)
    pc.add_argument("--field", required=False, default=None,
                    help="Calibrator field name/index or range (e.g. 10~12)")
    pc.add_argument("--refant", required=False, default=None)
    pc.add_argument(
        "--refant-ranking",
        help="Path to refant_ranking.json for auto selection")
    pc.add_argument(
        "--auto-fields",
        action="store_true",
        help="Automatically select bandpass fields using calibrator info")
    pc.add_argument(
        "--cal-ra-deg",
        type=float,
        help="Calibrator RA (deg) for auto field selection")
    pc.add_argument(
        "--cal-dec-deg",
        type=float,
        help="Calibrator Dec (deg) for auto field selection")
    pc.add_argument(
        "--cal-flux-jy",
        type=float,
        help="Calibrator flux (Jy) for weighting in auto selection")
    pc.add_argument(
        "--cal-catalog",
        help="Path to VLA calibrator catalog for auto field selection")
    pc.add_argument(
        "--cal-search-radius-deg",
        type=float,
        default=1.0,
        help="Search radius (deg) around catalog entries")
    pc.add_argument(
        "--pt-dec-deg",
        type=float,
        help="Pointing declination (deg) for catalog weighting")
    pc.add_argument(
        "--bp-window",
        type=int,
        default=3,
        help="Number of fields (approx) around peak to include")
    pc.add_argument(
        "--bp-min-pb",
        type=float,
        default=None,
        help=(
            "Primary-beam gain threshold [0-1] to auto-size field window "
            "around peak"
        ),
    )
    pc.add_argument(
        "--bp-combine-field",
        action="store_true",
        help="Combine across selected fields when solving bandpass/gains")
    pc.add_argument(
        "--fast",
        action="store_true",
        help=(
            "Enable fast path: subset MS (time/channel avg), "
            "phase-only gains, uvrange cuts"
        ),
    )
    pc.add_argument(
        "--skip-k",
        action="store_true",
        help="Skip delay (K) solve; solve only BP/GP",
    )
    pc.add_argument(
        "--skip-bp",
        action="store_true",
        help="Skip bandpass (BP) solve",
    )
    pc.add_argument(
        "--skip-g",
        action="store_true",
        help="Skip gain (G) solve",
    )
    pc.add_argument(
        "--gain-solint",
        default="inf",
        help="Gain solution interval (e.g., 'inf', '60s', '10min')",
    )
    pc.add_argument(
        "--gain-calmode",
        default="ap",
        choices=["ap", "p", "a"],
        help="Gain calibration mode: ap (amp+phase), p (phase-only), a (amp-only)",
    )
    pc.add_argument(
        "--timebin",
        default=None,
        help="Time averaging for fast subset, e.g. '30s'",
    )
    pc.add_argument(
        "--chanbin",
        type=int,
        default=None,
        help="Channel binning factor for fast subset (>=2)",
    )
    pc.add_argument(
        "--uvrange",
        default="",
        help="uvrange selection (e.g. '>1klambda') for fast solves",
    )
    pc.add_argument(
        "--no-flagging",
        action="store_true",
        help=(
            "Disable pre-solve flagging to avoid crashes on nonstandard "
            "polarizations"
        ),
    )
    pc.add_argument(
        "--model-source",
        choices=["catalog", "setjy", "component", "image"],
        help=(
            "Populate MODEL_DATA before bandpass using the specified strategy"
        ),
    )
    pc.add_argument(
        "--model-component",
        help=(
            "Path to CASA component list (.cl) when --model-source=component"
        ),
    )
    pc.add_argument(
        "--model-image",
        help="Path to CASA image when --model-source=image")
    pc.add_argument(
        "--model-field",
        help="Field name/index for setjy when --model-source=setjy",
    )
    pc.add_argument(
        "--model-setjy-standard",
        default="Perley-Butler 2017",
        help=(
            "Flux standard for setjy (default: Perley-Butler 2017)"
        ),
    )
    pc.add_argument(
        "--model-setjy-spw",
        default="",
        help="Spectral window selection for setjy")
    # On-the-fly MS repair has been removed; prefer reconversion if needed.

    pt = sub.add_parser("apply", help="Apply calibration to target MS")
    pt.add_argument("--ms", required=True)
    pt.add_argument("--field", required=True)
    pt.add_argument("--tables", nargs="+", required=True,
                    help="Calibration tables in order")

    args = p.parse_args()

    if args.cmd == "calibrate":
        field_sel = args.field
        # Defaults to ensure variables exist for later logic
        idxs = []  # type: ignore[assignment]
        wflux = []  # type: ignore[assignment]
        if args.auto_fields:
            try:
                if args.cal_catalog:
                    sel, idxs, wflux, calinfo = select_bandpass_from_catalog(
                        args.ms,
                        args.cal_catalog,
                        search_radius_deg=float(
                            args.cal_search_radius_deg or 1.0
                        ),
                        window=max(1, int(args.bp_window)),
                        min_pb=(
                            float(args.bp_min_pb)
                            if args.bp_min_pb is not None
                            else None
                        ),
                    )
                    name, ra_deg, dec_deg, flux_jy = calinfo
                    print(
                        (
                            "Catalog calibrator: {name} (RA {ra_deg:.4f} deg, "
                            "Dec {dec_deg:.4f} deg, flux {flux_jy:.2f} Jy)"
                        ).format(
                            name=name,
                            ra_deg=ra_deg,
                            dec_deg=dec_deg,
                            flux_jy=flux_jy,
                        )
                    )
                    print(
                        "Auto-selected bandpass fields: {} (indices: {})"
                        .format(sel, idxs)
                    )
                    field_sel = sel
                else:
                    if (
                        args.cal_ra_deg is None
                        or args.cal_dec_deg is None
                        or args.cal_flux_jy is None
                    ):
                        p.error(
                            (
                                "--auto-fields requires --cal-ra-deg/"
                                "--cal-dec-deg/--cal-flux-jy or --cal-catalog"
                            )
                        )
                    sel, idxs, wflux = select_bandpass_fields(
                        args.ms,
                        args.cal_ra_deg,
                        args.cal_dec_deg,
                        args.cal_flux_jy,
                        window=max(1, int(args.bp_window)),
                        min_pb=(
                            float(args.bp_min_pb)
                            if args.bp_min_pb is not None
                            else None
                        ),
                    )
                    print(
                        "Auto-selected bandpass fields: {} (indices: {})"
                        .format(sel, idxs)
                    )
                    field_sel = sel
            except Exception as e:
                print(
                    (
                        "Auto field selection failed ({}); falling back to "
                        "--field"
                    ).format(e)
                )
                if field_sel is None:
                    p.error(
                        "No --field provided and auto selection failed"
                    )
        if field_sel is None:
            p.error("--field is required when --auto-fields is not used")

        # Determine reference antenna
        refant = args.refant
        if args.refant_ranking:
            import json
            try:
                with open(args.refant_ranking, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                rec = data.get('recommended') if isinstance(
                    data, dict) else None
                if rec and rec.get('antenna_id') is not None:
                    refant = str(rec['antenna_id'])
                    print(f"Reference antenna (from ranking): {refant}")
            except Exception as e:
                print(
                    (
                        "Failed to read refant ranking ({}); "
                        "falling back to --refant"
                    ).format(e)
                )
        if refant is None:
            p.error("Provide --refant or --refant-ranking")

        # MS repair flags removed.
        # Optionally create a fast subset MS
        ms_in = args.ms
        if args.fast and (args.timebin or args.chanbin):
            from .subset import make_subset
            base = ms_in.rstrip('/').rstrip('.ms')
            ms_fast = f"{base}.fast.ms"
            print(
                (
                    "Creating fast subset: timebin={tb} chanbin={cb} -> {out}"
                ).format(tb=args.timebin, cb=args.chanbin, out=ms_fast)
            )
            make_subset(
                ms_in,
                ms_fast,
                timebin=args.timebin,
                chanbin=args.chanbin,
                combinespws=False,
            )
            ms_in = ms_fast

        # Execute solves with a robust K step on the peak field only, then BP/G
        # across the selected window

        if not args.no_flagging:
            reset_flags(ms_in)
            flag_zeros(ms_in)
            flag_rfi(ms_in)

        # Determine a peak field for K (if auto-selected, we have idxs/wflux)
        k_field_sel = field_sel
        try:
            # Available only in this scope if auto-fields branch set these
            # locals
            if (
                'idxs' in locals()
                and 'wflux' in locals()
                and idxs is not None
            ):
                import numpy as np
                k_idx = int(idxs[int(np.nanargmax(wflux))])
                k_field_sel = str(k_idx)
        except Exception:
            pass
        # As a fallback, if field_sel is a range like A~B, pick B
        if '~' in str(field_sel) and (k_field_sel == field_sel):
            try:
                _, b = str(field_sel).split('~')
                k_field_sel = str(int(b))
            except Exception:
                pass

        print(
            "Delay solve field (K): {}; BP/G fields: {}".format(
                k_field_sel, field_sel
            )
        )
        ktabs = []
        if not args.skip_k:
            t_k0 = time.perf_counter()
            ktabs = solve_delay(ms_in, k_field_sel, refant)
            print(
                "K (delay) solve completed in {:.2f}s".format(
                    time.perf_counter() - t_k0
                )
            )

        # Populate MODEL_DATA according to requested strategy.
        try:
            from . import model as model_helpers
            if args.model_source == "catalog":
                if (
                    args.auto_fields
                    and args.cal_catalog
                    and 'calinfo' in locals()
                    and isinstance(calinfo, (list, tuple))
                    and len(calinfo) >= 4
                ):
                    name, ra_deg, dec_deg, flux_jy = calinfo
                    print(
                        (
                            "Writing catalog point model: {n} @ ("
                            "{ra:.4f},{de:.4f}) deg, {fl:.2f} Jy"
                        ).format(n=name, ra=ra_deg, de=dec_deg, fl=flux_jy)
                    )
                    model_helpers.write_point_model_with_ft(
                        args.ms, float(ra_deg), float(dec_deg), float(flux_jy))
                else:
                    print(
                        (
                            "Catalog model requested but calibrator info "
                            "unavailable; skipping model write"
                        )
                    )
            elif args.model_source == "setjy":
                if not args.model_field:
                    p.error("--model-source=setjy requires --model-field")
                print(
                    (
                        "Running setjy on field {} (standard {})"
                    ).format(args.model_field, args.model_setjy_standard)
                )
                model_helpers.write_setjy_model(
                    args.ms,
                    field=args.model_field,
                    standard=args.model_setjy_standard,
                    spw=args.model_setjy_spw,
                )
            elif args.model_source == "component":
                if not args.model_component:
                    p.error(
                        "--model-source=component requires --model-component"
                    )
                print(
                    "Applying component list model: {}"
                    .format(args.model_component)
                )
                model_helpers.write_component_model_with_ft(
                    args.ms, args.model_component)
            elif args.model_source == "image":
                if not args.model_image:
                    p.error("--model-source=image requires --model-image")
                print(
                    "Applying image model: {}".format(args.model_image)
                )
                model_helpers.write_image_model_with_ft(
                    args.ms, args.model_image)
        except Exception as e:
            print(
                "MODEL_DATA population failed: {}".format(e)
            )

        bptabs = []
        if not args.skip_bp:
            t_bp0 = time.perf_counter()
            bptabs = solve_bandpass(
                ms_in,
                field_sel,
                refant,
                ktabs[0] if ktabs else None,
                combine_fields=bool(args.bp_combine_field),
                uvrange=(
                    (args.uvrange or "")
                    if args.fast
                    else ""
                ),
            )
            elapsed_bp = time.perf_counter() - t_bp0
            print("Bandpass solve completed in {:.2f}s".format(elapsed_bp))
        
        gtabs = []
        if not args.skip_g:
            t_g0 = time.perf_counter()
            # Determine phase_only based on gain_calmode
            phase_only = (args.gain_calmode == "p") or bool(args.fast)
            gtabs = solve_gains(
                ms_in,
                field_sel,
                refant,
                ktabs[0] if ktabs else None,
                bptabs,
                combine_fields=bool(args.bp_combine_field),
                phase_only=phase_only,
                uvrange=(
                    (args.uvrange or "")
                    if args.fast
                    else ""
                ),
                solint=args.gain_solint,
            )
            elapsed_g = time.perf_counter() - t_g0
            print("Gain solve completed in {:.2f}s".format(elapsed_g))

        tabs = (ktabs[:1] if ktabs else []) + bptabs + gtabs
        print("Generated tables:\n" + "\n".join(tabs))
    elif args.cmd == "apply":
        apply_to_target(args.ms, args.field, args.tables)
        print("Applied calibration to target")


if __name__ == "__main__":
    main()
