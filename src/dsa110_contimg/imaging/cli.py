"""
CLI to image a Measurement Set using CASA tclean.

Selects CORRECTED_DATA when present; otherwise falls back to DATA.
Performs primary-beam correction and exports FITS products.
"""

import argparse
import logging
import os
from typing import Optional
import time

import numpy as np
from casacore.tables import table
from casatasks import tclean, exportfits

LOG = logging.getLogger(__name__)


def _configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _detect_datacolumn(ms_path: str) -> str:
    """Choose datacolumn for tclean.

    Preference order:
    - Use CORRECTED_DATA if present and contains any non-zero values.
    - Otherwise fall back to DATA.
    This avoids the common pitfall where applycal didn't populate
    CORRECTED_DATA (all zeros) and tclean would produce blank images.
    """
    try:
        with table(ms_path, readonly=True) as t:
            cols = set(t.colnames())
            if "CORRECTED_DATA" in cols:
                try:
                    import numpy as _np
                    total = t.nrows()
                    if total <= 0:
                        return "data"
                    # Sample up to 8 evenly spaced windows of up to 2048 rows
                    windows = 8
                    block = 2048
                    indices = [max(0, int(i * total / max(1, windows)) - block // 2)
                               for i in range(windows)]
                    for start in indices:
                        n = min(block, total - start)
                        if n <= 0:
                            continue
                        cd = t.getcol("CORRECTED_DATA", start, n)
                        if _np.count_nonzero(_np.abs(cd) > 0) > 0:
                            return "corrected"
                except Exception:
                    pass
        return "data"
    except Exception:
        return "data"


def _default_cell_arcsec(ms_path: str) -> float:
    """Estimate cell size (arcsec) as a fraction of synthesized beam.

    Uses uv extents as proxy: theta ~ 0.5 * lambda / umax (radians).
    Returns 1/5 of theta in arcsec, clipped to [0.1, 60].
    """
    try:
        from daskms import xds_from_ms  # lazy import
        dsets = xds_from_ms(ms_path, columns=["UVW", "DATA"], chunks={})
        umax = 0.0
        freq = []
        for ds in dsets:
            uvw = np.asarray(ds.UVW.data.compute())
            umax = max(umax, float(np.nanmax(np.abs(uvw[:, 0]))))
            # derive mean freq per ddid
            from casacore.tables import table as ctab
            with ctab(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as dd:
                spw_map = dd.getcol("SPECTRAL_WINDOW_ID")
                spw_id = int(spw_map[ds.attrs["DATA_DESC_ID"]])
            with ctab(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
                chan = spw.getcol("CHAN_FREQ")[spw_id]
            freq.append(float(np.nanmean(chan)))
        if umax <= 0 or not freq:
            raise RuntimeError("bad umax or freq")
        c = 299_792_458.0
        lam = c / float(np.nanmean(freq))
        theta_rad = 0.5 * lam / umax
        cell = max(0.1, min(60.0, np.degrees(theta_rad) * 3600.0 / 5.0))
        return float(cell)
    except Exception:
        # CASA-only fallback using casacore tables if daskms missing
        try:
            from casacore.tables import table as ctab
            with ctab(f"{ms_path}::MAIN", readonly=True) as main:
                uvw0 = main.getcol("UVW", 0, min(10000, main.nrows()))
                umax = float(np.nanmax(np.abs(uvw0[:, 0])))
            with ctab(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
                chan = spw.getcol("CHAN_FREQ")
                freq = float(np.nanmean(chan))
            if umax <= 0 or not np.isfinite(freq):
                return 2.0
            c = 299_792_458.0
            lam = c / freq
            theta_rad = 0.5 * lam / umax
            cell = max(0.1, min(60.0, np.degrees(theta_rad) * 3600.0 / 5.0))
            return float(cell)
        except Exception:
            return 2.0


def image_ms(
    ms_path: str,
    *,
    imagename: str,
    field: str = "",
    spw: str = "",
    imsize: int = 1024,
    cell_arcsec: Optional[float] = None,
    weighting: str = "briggs",
    robust: float = 0.0,
    specmode: str = "mfs",
    deconvolver: str = "hogbom",
    nterms: int = 1,
    niter: int = 1000,
    threshold: str = "0.0Jy",
    pbcor: bool = True,
    phasecenter: Optional[str] = None,
    gridder: str = "standard",
    wprojplanes: int = 0,
    uvrange: str = "",
    pblimit: float = 0.2,
    psfcutoff: Optional[float] = None,
    quick: bool = False,
    skip_fits: bool = False,
) -> None:
    datacolumn = _detect_datacolumn(ms_path)
    if cell_arcsec is None:
        cell_arcsec = _default_cell_arcsec(ms_path)

    cell = f"{cell_arcsec:.3f}arcsec"
    if quick:
        # Conservative quick-look defaults
        imsize = min(imsize, 512)
        niter = min(niter, 300)
        threshold = threshold or "0.0Jy"
        weighting = weighting or "briggs"
        robust = robust if robust is not None else 0.0
    LOG.info("Imaging %s -> %s", ms_path, imagename)
    LOG.info(
        "datacolumn=%s cell=%s imsize=%d quick=%s",
        datacolumn,
        cell,
        imsize,
        quick,
    )

    # Build common kwargs for tclean, adding optional params only when needed
    kwargs = dict(
        vis=ms_path,
        imagename=imagename,
        datacolumn=datacolumn,
        field=field,
        spw=spw,
        imsize=[imsize, imsize],
        cell=[cell, cell],
        weighting=weighting,
        robust=robust,
        specmode=specmode,
        deconvolver=deconvolver,
        nterms=nterms,
        niter=niter,
        threshold=threshold,
        gridder=gridder,
        wprojplanes=wprojplanes,
        stokes="I",
        restoringbeam="",
        pbcor=pbcor,
        phasecenter=phasecenter if phasecenter else "",
        interactive=False,
    )
    if uvrange:
        kwargs["uvrange"] = uvrange
    if pblimit is not None:
        kwargs["pblimit"] = pblimit
    if psfcutoff is not None:
        kwargs["psfcutoff"] = psfcutoff

    t0 = time.perf_counter()
    tclean(**kwargs)
    LOG.info("tclean completed in %.2fs", time.perf_counter() - t0)

    # Export FITS products if present
    if skip_fits:
        return
    for suffix in (".image", ".pb", ".pbcor", ".residual", ".model"):
        img = imagename + suffix
        if os.path.isdir(img):
            fits = imagename + suffix + ".fits"
            try:
                exportfits(
                    imagename=img, fitsimage=fits, overwrite=True
                )
            except Exception as exc:
                LOG.debug("exportfits failed for %s: %s", img, exc)


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Image an MS with tclean"
    )
    parser.add_argument("--ms", required=True, help="Path to input MS")
    parser.add_argument(
        "--imagename", required=True, help="Output image name prefix"
    )
    parser.add_argument("--field", default="", help="Field selection")
    parser.add_argument("--spw", default="", help="SPW selection")
    parser.add_argument("--imsize", type=int, default=1024)
    parser.add_argument("--cell-arcsec", type=float, default=None)
    parser.add_argument("--weighting", default="briggs")
    parser.add_argument("--robust", type=float, default=0.0)
    # Friendly synonyms matching user vocabulary
    parser.add_argument(
        "--weighttype",
        dest="weighting_alias",
        default=None,
        help="Alias of --weighting")
    parser.add_argument(
        "--weight",
        dest="robust_alias",
        type=float,
        default=None,
        help="Alias of --robust (Briggs robust)")
    parser.add_argument("--specmode", default="mfs")
    parser.add_argument("--deconvolver", default="hogbom")
    parser.add_argument("--nterms", type=int, default=1)
    parser.add_argument("--niter", type=int, default=1000)
    parser.add_argument("--threshold", default="0.0Jy")
    parser.add_argument("--no-pbcor", action="store_true")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick-look imaging: smaller imsize and lower niter",
    )
    parser.add_argument(
        "--skip-fits",
        action="store_true",
        help="Do not export FITS products after tclean",
    )
    parser.add_argument(
        "--phasecenter",
        default=None,
        help="CASA phasecenter string (e.g., 'J2000 08h34m54.9 +55d34m21.1')")
    parser.add_argument(
        "--gridder",
        default="standard",
        help="tclean gridder (standard|wproject|mosaic)")
    parser.add_argument(
        "--wprojplanes",
        type=int,
        default=0,
        help=(
            "Number of w-projection planes when gridder=wproject "
            "(-1 for auto)"
        ),
    )
    parser.add_argument(
        "--uvrange",
        default="",
        help="uvrange selection, e.g. '>1klambda'")
    parser.add_argument("--pblimit", type=float, default=0.2)
    parser.add_argument("--psfcutoff", type=float, default=None)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
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
        quick=bool(args.quick),
        skip_fits=bool(args.skip_fits),
    )


if __name__ == "__main__":  # pragma: no cover
    main()
