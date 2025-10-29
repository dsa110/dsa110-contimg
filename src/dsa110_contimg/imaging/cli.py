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
from casacore.tables import table  # type: ignore[import]
from casatasks import tclean, exportfits  # type: ignore[import]
try:
    from casatools import vpmanager as _vpmanager  # type: ignore[import]
    from casatools import msmetadata as _msmd  # type: ignore[import]
except Exception:  # pragma: no cover
    _vpmanager = None
    _msmd = None

LOG = logging.getLogger(__name__)

try:
    # Ensure temp artifacts go to scratch and not the repo root
    from dsa110_contimg.utils.tempdirs import prepare_temp_environment, derive_default_scratch_root
except Exception:  # pragma: no cover - defensive import
    prepare_temp_environment = None  # type: ignore
    derive_default_scratch_root = None  # type: ignore


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
                    total = t.nrows()
                    if total <= 0:
                        return "data"
                    # Sample up to 8 evenly spaced windows of up to 2048 rows
                    windows = 8
                    block = 2048
                    indices = []
                    for i in range(windows):
                        start_idx = int(i * total / max(1, windows))
                        indices.append(max(0, start_idx - block // 2))
                    for start in indices:
                        n = min(block, total - start)
                        if n <= 0:
                            continue
                        cd = t.getcol("CORRECTED_DATA", start, n)
                        if np.count_nonzero(np.abs(cd) > 0) > 0:
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
        from daskms import xds_from_ms  # type: ignore[import]
        dsets = xds_from_ms(ms_path, columns=["UVW", "DATA"], chunks={})
        umax = 0.0
        freq_list: list[float] = []
        for ds in dsets:
            uvw = np.asarray(ds.UVW.data.compute())
            umax = max(umax, float(np.nanmax(np.abs(uvw[:, 0]))))
            # derive mean freq per ddid
            with table(f"{ms_path}::DATA_DESCRIPTION", readonly=True) as dd:
                spw_map = dd.getcol("SPECTRAL_WINDOW_ID")
                spw_id = int(spw_map[ds.attrs["DATA_DESC_ID"]])
            with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
                chan = spw.getcol("CHAN_FREQ")[spw_id]
            freq_list.append(float(np.nanmean(chan)))
        if umax <= 0 or not freq_list:
            raise RuntimeError("bad umax or freq")
        c = 299_792_458.0
        lam = c / float(np.nanmean(freq_list))
        theta_rad = 0.5 * lam / umax
        cell = max(0.1, min(60.0, np.degrees(theta_rad) * 3600.0 / 5.0))
        return float(cell)
    except Exception:
        # CASA-only fallback using casacore tables if daskms missing
        try:
            with table(f"{ms_path}::MAIN", readonly=True) as main_tbl:
                uvw0 = main_tbl.getcol("UVW", 0, min(10000, main_tbl.nrows()))
                umax = float(np.nanmax(np.abs(uvw0[:, 0])))
            with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
                chan = spw.getcol("CHAN_FREQ")
                if hasattr(chan, "__array__"):
                    freq_scalar = float(np.nanmean(chan))
                else:
                    freq_scalar = float(np.nanmean(np.asarray(chan)))
            if umax <= 0 or not np.isfinite(freq_scalar):
                return 2.0
            c = 299_792_458.0
            lam = c / freq_scalar
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
    vptable: Optional[str] = None,
    wbawp: Optional[bool] = None,
    cfcache: Optional[str] = None,
    nvss_min_mjy: Optional[float] = None,
    calib_ra_deg: Optional[float] = None,
    calib_dec_deg: Optional[float] = None,
    calib_flux_jy: Optional[float] = None,
) -> None:
    # Prepare temp dirs and working directory to keep TempLattice* off the repo
    try:
        if prepare_temp_environment is not None:
            out_dir = os.path.dirname(os.path.abspath(imagename))
            root = os.getenv("CONTIMG_SCRATCH_DIR") or "/scratch/dsa110-contimg"
            prepare_temp_environment(root, cwd_to=out_dir)
    except Exception:
        # Best-effort; continue even if temp prep fails
        pass
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
    if vptable:
        kwargs["vptable"] = vptable
    if wbawp is not None:
        kwargs["wbawp"] = bool(wbawp)
    if cfcache:
        kwargs["cfcache"] = cfcache

    # Avoid overwriting any seeded MODEL_DATA during tclean
    kwargs["savemodel"] = "none"

    # Compute approximate FoV radius from image geometry
    import math as _math
    fov_x = (cell_arcsec * imsize) / 3600.0
    fov_y = (cell_arcsec * imsize) / 3600.0
    radius_deg = 0.5 * float(_math.hypot(fov_x, fov_y))

    # Optional: seed a single-component calibrator model if provided and in FoV
    did_seed = False
    if (calib_ra_deg is not None and calib_dec_deg is not None and calib_flux_jy is not None and calib_flux_jy > 0):
        try:
            with table(f"{ms_path}::FIELD", readonly=True) as fld:
                ph = fld.getcol("PHASE_DIR")[0]
                ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
                dec0_deg = float(ph[0][1]) * (180.0 / np.pi)
            # crude small-angle separation in deg
            d_ra = (float(calib_ra_deg) - ra0_deg) * np.cos(np.deg2rad(dec0_deg))
            d_dec = (float(calib_dec_deg) - dec0_deg)
            sep_deg = float(_math.hypot(d_ra, d_dec))
            if sep_deg <= radius_deg * 1.05:
                from dsa110_contimg.calibration.skymodels import make_point_cl, ft_from_cl  # type: ignore
                cl_path = f"{imagename}.calibrator_{calib_flux_jy:.3f}Jy.cl"
                make_point_cl(
                    name="calibrator",
                    ra_deg=float(calib_ra_deg),
                    dec_deg=float(calib_dec_deg),
                    flux_jy=float(calib_flux_jy),
                    freq_ghz=1.4,
                    out_path=cl_path,
                )
                ft_from_cl(ms_path, cl_path, field=field or "0", usescratch=True)
                LOG.info("Seeded MODEL_DATA with calibrator point model (flux=%.3f Jy)", calib_flux_jy)
                did_seed = True
        except Exception as exc:
            LOG.debug("Calibrator seeding skipped: %s", exc)

    # Optional: seed a sky model from NVSS (> nvss_min_mjy mJy) via ft(), if no calibrator seed
    if (not did_seed) and (nvss_min_mjy is not None):
        try:
            from dsa110_contimg.calibration.skymodels import (
                make_nvss_component_cl,
                ft_from_cl,
            )  # type: ignore
            # Determine phase center from FIELD table
            ra0_deg = dec0_deg = None
            with table(f"{ms_path}::FIELD", readonly=True) as fld:
                try:
                    ph = fld.getcol("PHASE_DIR")[0]
                    ra0_deg = float(ph[0][0]) * (180.0 / np.pi)
                    dec0_deg = float(ph[0][1]) * (180.0 / np.pi)
                except Exception:
                    pass
            if ra0_deg is None or dec0_deg is None:
                raise RuntimeError("FIELD::PHASE_DIR not available")
            # radius_deg computed above
            # Mean observing frequency
            freq_ghz = 1.4
            try:
                with table(f"{ms_path}::SPECTRAL_WINDOW", readonly=True) as spw:
                    ch = spw.getcol("CHAN_FREQ")[0]
                    freq_ghz = float(np.nanmean(ch)) / 1e9
            except Exception:
                pass
            cl_path = f"{imagename}.nvss_{float(nvss_min_mjy):g}mJy.cl"
            make_nvss_component_cl(
                ra0_deg,
                dec0_deg,
                radius_deg,
                min_mjy=float(nvss_min_mjy),
                freq_ghz=freq_ghz,
                out_path=cl_path,
            )
            ft_from_cl(ms_path, cl_path, field=field or "0", usescratch=True)
            LOG.info(
                "Seeded MODEL_DATA with NVSS skymodel (>%s mJy, radius %.2f deg)",
                nvss_min_mjy,
                radius_deg,
            )
        except Exception as exc:
            LOG.warning("NVSS skymodel seeding skipped: %s", exc)

    # If a VP table is supplied, proactively register it as user default for the
    # telescope reported by the MS (and for OVRO_DSA) to satisfy AWProject.
    if vptable and _vpmanager is not None and _msmd is not None:
        try:
            telname = None
            md = _msmd()
            md.open(ms_path)
            try:
                telname = md.telescope()
            finally:
                md.close()
            vp = _vpmanager()
            vp.loadfromtable(vptable)
            for tname in filter(None, [telname, "OVRO_DSA"]):
                try:
                    vp.setuserdefault(telescope=tname)
                except Exception:
                    pass
            LOG.debug("Registered VP table %s for telescope(s): %s", vptable, [telname, "OVRO_DSA"]) 
        except Exception as exc:
            LOG.debug("VP preload skipped: %s", exc)

    t0 = time.perf_counter()
    tclean(**kwargs)
    LOG.info("tclean completed in %.2fs", time.perf_counter() - t0)

    # QA validation of image products
    try:
        from dsa110_contimg.qa.pipeline_quality import check_image_quality
        image_path = imagename + ".image"
        if os.path.isdir(image_path):
            check_image_quality(image_path, alert_on_issues=True)
    except Exception as e:
        LOG.warning("QA validation failed: %s", e)

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
        help="Alias of --weighting",
    )
    parser.add_argument(
        "--weight",
        dest="robust_alias",
        type=float,
        default=None,
        help="Alias of --robust (Briggs robust)",
    )
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
        help=(
            "CASA phasecenter string (e.g., 'J2000 08h34m54.9 +55d34m21.1')"
        ),
    )
    parser.add_argument(
        "--gridder",
        default="standard",
        help="tclean gridder (standard|wproject|mosaic|awproject)",
    )
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
        help="uvrange selection, e.g. '>1klambda'",
    )
    parser.add_argument("--pblimit", type=float, default=0.2)
    parser.add_argument("--psfcutoff", type=float, default=None)
    parser.add_argument("--verbose", action="store_true")
    # NVSS skymodel seeding
    parser.add_argument(
        "--nvss-min-mjy",
        type=float,
        default=None,
        help="If set, seed MODEL_DATA by ft() of NVSS point sources above this flux",
    )
    # A-Projection related options
    parser.add_argument(
        "--vptable",
        default=None,
        help="Path to CASA VP table (vpmanager.saveastable)",
    )
    parser.add_argument(
        "--wbawp",
        action="store_true",
        help="Enable wideband A-Projection approximation",
    )
    parser.add_argument(
        "--cfcache",
        default=None,
        help="Convolution function cache directory",
    )
    args = parser.parse_args(argv)

    _configure_logging(args.verbose)
    # Apply aliases if provided
    weighting = (
        args.weighting_alias if args.weighting_alias else args.weighting
    )
    robust = (
        args.robust_alias if args.robust_alias is not None else args.robust
    )

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
        vptable=args.vptable,
        wbawp=bool(args.wbawp),
        cfcache=args.cfcache,
        nvss_min_mjy=args.nvss_min_mjy,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
