"""
CLI to image a Measurement Set using CASA tclean or WSClean.
WSClean is the default backend for faster imaging.

Selects CORRECTED_DATA when present; otherwise falls back to DATA.
Performs primary-beam correction and exports FITS products.

Supports hybrid workflow: CASA ft() for model seeding + WSClean for fast imaging.
"""

from dsa110_contimg.utils.validation import (
    validate_ms,
    validate_corrected_data_quality,
    ValidationError,
)
from dsa110_contimg.utils.cli_helpers import (
    setup_casa_environment,
    add_common_logging_args,
    configure_logging_from_args,
    ensure_scratch_dirs,
)
from .cli_imaging import image_ms, run_wsclean as _run_wsclean
from .cli_utils import (
    detect_datacolumn as _detect_datacolumn,
    default_cell_arcsec as _default_cell_arcsec,
)
from casatasks import tclean, exportfits  # type: ignore[import]
from casacore.tables import table  # type: ignore[import]
import numpy as np
import argparse
import logging
import os
import sys
from typing import Optional
import time
import subprocess
import shutil

logger = logging.getLogger(__name__)

# Use shared CLI utilities

# Set CASA log directory BEFORE any CASA imports - CASA writes logs to CWD
setup_casa_environment()

try:
    from casatools import vpmanager as _vpmanager  # type: ignore[import]
    from casatools import msmetadata as _msmd  # type: ignore[import]
except Exception:  # pragma: no cover
    _vpmanager = None
    _msmd = None

LOG = logging.getLogger(__name__)

try:
    # Ensure temp artifacts go to scratch and not the repo root
    from dsa110_contimg.utils.tempdirs import (
        prepare_temp_environment,
        derive_default_scratch_root,
    )
except Exception:  # pragma: no cover - defensive import
    prepare_temp_environment = None  # type: ignore
    derive_default_scratch_root = None  # type: ignore


# NOTE: _configure_logging() has been removed. Use configure_logging_from_args() instead.
# This function was deprecated and unused. All logging now uses the shared utility.


# Utility functions moved to cli_utils.py

# Core imaging functions moved to cli_imaging.py


def main(argv: Optional[list] = None) -> None:
    from dsa110_contimg.utils.runtime_safeguards import validate_image_shape

    parser = argparse.ArgumentParser(description="DSA-110 Imaging CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # image subcommand (main imaging functionality)
    img_parser = sub.add_parser(
        "image",
        help="Image an MS with tclean or WSClean (WSClean is default)",
        description=(
            "Create images from a Measurement Set using CASA tclean or WSClean. "
            "WSClean is the default backend for faster imaging. "
            "Automatically selects CORRECTED_DATA when present, otherwise uses DATA.\n\n"
            "Example:\n"
            "  python -m dsa110_contimg.imaging.cli image \\\n"
            "    --ms /data/ms/target.ms --imagename /data/images/target \\\n"
            "    --imsize 2048 --cell-arcsec 1.0 --quality-tier standard"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    img_parser.add_argument("--ms", required=True, help="Path to input MS")
    img_parser.add_argument(
        "--imagename", required=True, help="Output image name prefix"
    )
    img_parser.add_argument("--field", default="", help="Field selection")
    img_parser.add_argument("--spw", default="", help="SPW selection")
    img_parser.add_argument("--imsize", type=int, default=1024)
    img_parser.add_argument("--cell-arcsec", type=float, default=None)
    img_parser.add_argument("--weighting", default="briggs")
    img_parser.add_argument("--robust", type=float, default=0.0)
    # Friendly synonyms matching user vocabulary
    img_parser.add_argument(
        "--weighttype",
        dest="weighting_alias",
        default=None,
        help="Alias of --weighting",
    )
    img_parser.add_argument(
        "--weight",
        dest="robust_alias",
        type=float,
        default=None,
        help="Alias of --robust (Briggs robust)",
    )
    img_parser.add_argument("--specmode", default="mfs")
    img_parser.add_argument("--deconvolver", default="hogbom")
    img_parser.add_argument("--nterms", type=int, default=1)
    img_parser.add_argument("--niter", type=int, default=1000)
    img_parser.add_argument("--threshold", default="0.0Jy")
    img_parser.add_argument("--no-pbcor", action="store_true")
    img_parser.add_argument(
        "--quality-tier",
        choices=["development", "standard", "high_precision"],
        default="standard",
        help=(
            "Imaging quality tier with explicit trade-offs.\n"
            "  development: ⚠️  NON-SCIENCE - coarser resolution, fewer iterations\n"
            "  standard: Recommended for all science observations (full quality)\n"
            "  high_precision: Enhanced settings for maximum quality (slower)\n"
            "Default: standard"
        ),
    )
    img_parser.add_argument(
        "--skip-fits",
        action="store_true",
        help="Do not export FITS products after tclean",
    )
    img_parser.add_argument(
        "--phasecenter",
        default=None,
        help=("CASA phasecenter string (e.g., 'J2000 08h34m54.9 +55d34m21.1')"),
    )
    img_parser.add_argument(
        "--gridder",
        default="standard",
        help="tclean gridder (standard|wproject|mosaic|awproject)",
    )
    img_parser.add_argument(
        "--wprojplanes",
        type=int,
        default=0,
        help=("Number of w-projection planes when gridder=wproject " "(-1 for auto)"),
    )
    img_parser.add_argument(
        "--uvrange",
        default="",
        help="uvrange selection, e.g. '>1klambda'",
    )
    img_parser.add_argument("--pblimit", type=float, default=0.2)
    img_parser.add_argument("--psfcutoff", type=float, default=None)
    img_parser.add_argument("--verbose", action="store_true")
    # NVSS skymodel seeding
    img_parser.add_argument(
        "--nvss-min-mjy",
        type=float,
        default=None,
        help=(
            "If set, seed MODEL_DATA by ft() of NVSS point sources above this flux. "
            "In development quality tier, defaults to 10.0 mJy. "
            "In high_precision tier, defaults to 5.0 mJy."
        ),
    )
    img_parser.add_argument(
        "--export-model-image",
        action="store_true",
        help=(
            "Export MODEL_DATA as FITS image after NVSS seeding. "
            "Useful for visualizing the sky model used during imaging. "
            "Output will be saved as {imagename}.nvss_model.fits"
        ),
    )
    # Masking parameters
    img_parser.add_argument(
        "--no-nvss-mask",
        action="store_true",
        help="Disable NVSS-based masking (masking is enabled by default for 2-4x faster imaging)",
    )
    img_parser.add_argument(
        "--mask-radius-arcsec",
        type=float,
        default=60.0,
        help="Mask radius around NVSS sources in arcseconds (default: 60.0, ~2-3× beam)",
    )
    # A-Projection related options
    img_parser.add_argument(
        "--vptable",
        default=None,
        help="Path to CASA VP table (vpmanager.saveastable)",
    )
    img_parser.add_argument(
        "--wbawp",
        action="store_true",
        help="Enable wideband A-Projection approximation",
    )
    img_parser.add_argument(
        "--cfcache",
        default=None,
        help="Convolution function cache directory",
    )
    # Backend selection
    img_parser.add_argument(
        "--backend",
        choices=["tclean", "wsclean"],
        default="wsclean",
        help="Imaging backend: tclean (CASA) or wsclean (default: wsclean)",
    )
    img_parser.add_argument(
        "--wsclean-path",
        default=None,
        help="Path to WSClean executable (or 'docker' for Docker container). "
        "If not set, searches PATH or uses Docker if available.",
    )
    # Calibrator seeding
    img_parser.add_argument(
        "--calib-ra-deg",
        type=float,
        default=None,
        help="Calibrator RA (degrees) for single-component model seeding",
    )
    img_parser.add_argument(
        "--calib-dec-deg",
        type=float,
        default=None,
        help="Calibrator Dec (degrees) for single-component model seeding",
    )
    img_parser.add_argument(
        "--calib-flux-jy",
        type=float,
        default=None,
        help="Calibrator flux (Jy) for single-component model seeding",
    )

    # export subcommand
    exp_parser = sub.add_parser("export", help="Export CASA images to FITS and PNG")
    exp_parser.add_argument(
        "--source", required=True, help="Directory containing CASA images"
    )
    exp_parser.add_argument("--prefix", required=True, help="Prefix of image set")
    exp_parser.add_argument(
        "--make-fits", action="store_true", help="Export FITS from CASA images"
    )
    exp_parser.add_argument(
        "--make-png", action="store_true", help="Convert FITS to PNGs"
    )

    # create-nvss-mask subcommand
    mask_parser = sub.add_parser(
        "create-nvss-mask", help="Create CRTF mask around NVSS sources"
    )
    mask_parser.add_argument(
        "--image", required=True, help="CASA-exported FITS image path"
    )
    mask_parser.add_argument(
        "--min-mjy", type=float, default=1.0, help="Minimum NVSS flux (mJy)"
    )
    mask_parser.add_argument(
        "--radius-arcsec", type=float, default=6.0, help="Mask circle radius (arcsec)"
    )
    mask_parser.add_argument(
        "--out", help="Output CRTF path (defaults to <image>.nvss_mask.crtf)"
    )

    # create-nvss-overlay subcommand
    overlay_parser = sub.add_parser(
        "create-nvss-overlay", help="Overlay NVSS sources on FITS image"
    )
    overlay_parser.add_argument(
        "--image", required=True, help="Input FITS image (CASA export)"
    )
    overlay_parser.add_argument(
        "--pb", help="Primary beam FITS to mask detections (optional)"
    )
    overlay_parser.add_argument(
        "--pblimit", type=float, default=0.2, help="PB cutoff when --pb is provided"
    )
    overlay_parser.add_argument(
        "--min-mjy", type=float, default=10.0, help="Minimum NVSS flux (mJy) to plot"
    )
    overlay_parser.add_argument("--out", required=True, help="Output PNG path")

    args = parser.parse_args(argv)

    # Input validation
    if hasattr(args, "ms") and args.ms:
        if not os.path.exists(args.ms):
            raise FileNotFoundError(f"MS file not found: {args.ms}")
    if hasattr(args, "imagename") and args.imagename:
        output_dir = (
            os.path.dirname(args.imagename) if os.path.dirname(args.imagename) else "."
        )
        if not os.path.exists(output_dir):
            raise ValueError(f"Output directory does not exist: {output_dir}")

    # Configure logging using shared utility
    configure_logging_from_args(args)

    # Ensure scratch directory structure exists
    try:
        ensure_scratch_dirs()
    except Exception:
        pass  # Best-effort; continue if setup fails

    if args.cmd == "image":
        # Apply aliases if provided
        weighting = args.weighting_alias if args.weighting_alias else args.weighting
        robust = args.robust_alias if args.robust_alias is not None else args.robust

        image_ms(
            args.ms,
            imagename=args.imagename,
            field=args.field,
            spw=args.spw,
            imsize=args.imsize,
            cell_arcsec=args.cell_arcsec,
            weighting=weighting,
            robust=robust,
            specmode=args.specmode,
            deconvolver=args.deconvolver,
            nterms=args.nterms,
            niter=args.niter,
            threshold=args.threshold,
            pbcor=not args.no_pbcor,
            phasecenter=args.phasecenter,
            gridder=args.gridder,
            wprojplanes=args.wprojplanes,
            uvrange=args.uvrange,
            pblimit=args.pblimit,
            psfcutoff=args.psfcutoff,
            quality_tier=args.quality_tier,
            skip_fits=bool(args.skip_fits),
            vptable=args.vptable,
            wbawp=bool(args.wbawp),
            cfcache=args.cfcache,
            nvss_min_mjy=args.nvss_min_mjy,
            calib_ra_deg=args.calib_ra_deg,
            calib_dec_deg=args.calib_dec_deg,
            calib_flux_jy=args.calib_flux_jy,
            backend=args.backend,
            wsclean_path=args.wsclean_path,
            export_model_image=args.export_model_image,
            use_nvss_mask=not args.no_nvss_mask,
            mask_radius_arcsec=args.mask_radius_arcsec,
        )

    elif args.cmd == "export":
        from glob import glob
        from typing import List
        from dsa110_contimg.imaging.export import (
            export_fits,
            save_png_from_fits,
            _find_casa_images,
        )

        casa_images = _find_casa_images(args.source, args.prefix)
        if not casa_images:
            logger.warning(
                f"No CASA image directories found for prefix {args.prefix} under {args.source}"
            )
            print(
                "No CASA image directories found for prefix",
                args.prefix,
                "under",
                args.source,
            )
            return

        fits_paths: List[str] = []
        if args.make_fits:
            fits_paths = export_fits(casa_images)
            if not fits_paths:
                logger.warning("No FITS files exported (check casatasks and inputs)")
                print("No FITS files exported (check casatasks and inputs)")
        if args.make_png:
            # If FITS were not just created, try to discover existing ones
            if not fits_paths:
                patt = os.path.join(args.source, args.prefix + "*.fits")
                fits_paths = sorted(glob(patt))
            if not fits_paths:
                logger.warning(f"No FITS files found to convert for {args.prefix}")
                print("No FITS files found to convert for", args.prefix)
            else:
                save_png_from_fits(fits_paths)

    elif args.cmd == "create-nvss-mask":
        from dsa110_contimg.imaging.nvss_tools import create_nvss_mask

        out_path = (
            args.out
            or os.path.splitext(args.image)[0]
            + f".nvss_{args.min_mjy:g}mJy_{args.radius_arcsec:g}as_mask.crtf"
        )
        create_nvss_mask(args.image, args.min_mjy, args.radius_arcsec, out_path)
        print(f"Wrote mask: {out_path}")

    elif args.cmd == "create-nvss-overlay":
        from dsa110_contimg.imaging.nvss_tools import create_nvss_overlay

        create_nvss_overlay(args.image, args.out, args.pb, args.pblimit, args.min_mjy)
        print(f"Wrote overlay: {args.out}")


if __name__ == "__main__":  # pragma: no cover
    main()
