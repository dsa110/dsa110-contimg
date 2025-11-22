import argparse
import sys
from pathlib import Path

from casatasks import imstat

# Add the source directory to Python path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from dsa110_contimg.calibration.applycal import apply_to_target
from dsa110_contimg.calibration.calibration import (
    solve_bandpass,
    solve_delay,
    solve_gains,
)
from dsa110_contimg.calibration.flagging import flag_rfi, flag_zeros, reset_flags
from dsa110_contimg.imaging.cli import (  # Replaces calibration.imaging.quick_image
    image_ms,
)


def main():
    p = argparse.ArgumentParser(
        description='Calibrate a VLA calibrator MS: K+B+G, apply to self, image at 3" pixels'
    )
    p.add_argument("--ms", required=True, help="Path to measurement set")
    p.add_argument(
        "--field",
        required=False,
        default="0",
        help="Calibrator field name or id (default 0)",
    )
    p.add_argument(
        "--refant",
        required=False,
        default="23",
        help="Reference antenna name/id (default 23)",
    )
    p.add_argument(
        "--imagename",
        required=False,
        default="cal_demo_image",
        help="Output image name (no extension)",
    )
    p.add_argument("--imsize", type=int, default=1024, help="Image size (pixels)")
    args = p.parse_args()

    ms = args.ms
    field = args.field
    refant = args.refant
    imagename = args.imagename

    print("Reset + flag RFI/zeros on {}".format(ms))
    reset_flags(ms)
    flag_zeros(ms)
    flag_rfi(ms)

    print("Solve delays (K)")
    ktabs = solve_delay(ms, field, refant, t_slow="inf", t_fast=None)
    ktab = ktabs[0]

    print("Solve bandpass (B)")
    bptabs = solve_bandpass(ms, field, refant, ktab)

    print("Solve gains (G)")
    gtabs = solve_gains(ms, field, refant, ktab, bptabs)

    tables = [ktab] + bptabs + gtabs
    print("Apply calibration to self")
    apply_to_target(ms, field, tables)

    print("Image calibrated data (3 arcsec pixels)")
    # Use image_ms with explicit parameters (replaces calibration.imaging.quick_image)
    image_ms(
        ms,
        imagename=imagename,
        field=field,
        niter=1000,
        threshold="0.1mJy",
        cell_arcsec=3.0,
        imsize=args.imsize,
        quick=False,
        skip_fits=True,
    )

    # Report peak and its world position
    stats = imstat(imagename + ".image")
    peak = float(stats["max"][0])
    maxpos_pix = stats["maxpos"]
    maxpos_world = stats.get("maxposf", None)
    print("Peak I: {:.4g} at pixel {}".format(peak, tuple(maxpos_pix)))
    if maxpos_world:
        print("Peak world: RA {}, Dec {}".format(maxpos_world[0], maxpos_world[1]))

    print("Done. Tables applied:")
    for t in tables:
        print("  ", t)


if __name__ == "__main__":
    main()
