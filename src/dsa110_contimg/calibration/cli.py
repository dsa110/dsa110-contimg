import argparse
from typing import List

from .flagging import reset_flags, flag_zeros, flag_rfi
from .calibration import solve_delay, solve_bandpass, solve_gains
from .applycal import apply_to_target


def run_calibrator(ms: str, cal_field: str, refant: str) -> List[str]:
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
    pc.add_argument("--field", required=True, help="Calibrator field name/index")
    pc.add_argument("--refant", required=True)

    pt = sub.add_parser("apply", help="Apply calibration to target MS")
    pt.add_argument("--ms", required=True)
    pt.add_argument("--field", required=True)
    pt.add_argument("--tables", nargs="+", required=True, help="Calibration tables in order")

    args = p.parse_args()

    if args.cmd == "calibrate":
        tabs = run_calibrator(args.ms, args.field, args.refant)
        print("Generated tables:\n" + "\n".join(tabs))
    elif args.cmd == "apply":
        apply_to_target(args.ms, args.field, args.tables)
        print("Applied calibration to target")


if __name__ == "__main__":
    main()


