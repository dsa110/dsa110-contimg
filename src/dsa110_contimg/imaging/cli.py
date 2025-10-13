"""
CLI to image a Measurement Set using CASA tclean.

Selects CORRECTED_DATA when present; otherwise falls back to DATA.
Performs primary-beam correction and exports FITS products.
"""

import argparse
import logging
import os
from typing import Optional

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
    try:
        with table(ms_path, readonly=True) as t:
            cols = set(t.colnames())
        if "CORRECTED_DATA" in cols:
            return "corrected"
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
            return 2.0
        c = 299_792_458.0
        lam = c / float(np.nanmean(freq))
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
    niter: int = 1000,
    threshold: str = "0.0Jy",
    pbcor: bool = True,
) -> None:
    datacolumn = _detect_datacolumn(ms_path)
    if cell_arcsec is None:
        cell_arcsec = _default_cell_arcsec(ms_path)

    cell = f"{cell_arcsec:.3f}arcsec"
    LOG.info("Imaging %s -> %s", ms_path, imagename)
    LOG.info("datacolumn=%s cell=%s imsize=%d", datacolumn, cell, imsize)

    tclean(
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
        niter=niter,
        threshold=threshold,
        gridder="standard",
        stokes="I",
        restoringbeam="",
        pbcor=pbcor,
        interactive=False,
    )

    # Export FITS products if present
    for suffix in (".image", ".pb", ".pbcor", ".residual", ".model"):
        img = imagename + suffix
        if os.path.isdir(img):
            fits = imagename + suffix + ".fits"
            try:
                exportfits(imagename=img, fitsimage=fits, overwrite=True)
            except Exception as exc:
                LOG.debug("exportfits failed for %s: %s", img, exc)


def main(argv: Optional[list] = None) -> None:
    parser = argparse.ArgumentParser(description="Image an MS with tclean")
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
    parser.add_argument("--specmode", default="mfs")
    parser.add_argument("--deconvolver", default="hogbom")
    parser.add_argument("--niter", type=int, default=1000)
    parser.add_argument("--threshold", default="0.0Jy")
    parser.add_argument("--no-pbcor", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
    image_ms(
        args.ms,
        imagename=args.imagename,
        field=args.field,
        spw=args.spw,
        imsize=args.imsize,
        cell_arcsec=args.cell_arcsec,
        weighting=args.weighting,
        robust=args.robust,
        specmode=args.specmode,
        deconvolver=args.deconvolver,
        niter=args.niter,
        threshold=args.threshold,
        pbcor=not args.no_pbcor,
    )


if __name__ == "__main__":  # pragma: no cover
    main()

