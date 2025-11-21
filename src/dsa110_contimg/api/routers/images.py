# pylint: disable=no-member  # astropy.units uses dynamic attributes (deg, Jy, etc.)
"""Image-related API routes extracted from routes.py."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse

from dsa110_contimg.api.data_access import _connect
from dsa110_contimg.api.image_utils import get_fits_path
from dsa110_contimg.api.models import ImageDetail, ImageInfo, ImageList

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/images", response_model=ImageList)
def images(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    ms_path: str | None = None,
    image_type: str | None = None,
    pbcor: bool | None = None,
    start_date: str | None = Query(None, description="Start date filter (ISO 8601 format)"),
    end_date: str | None = Query(None, description="End date filter (ISO 8601 format)"),
    noise_max: float | None = Query(None, description="Maximum noise level (Jy)"),
    dec_min: float | None = Query(
        None,
        description="Minimum declination (degrees). EXPERIMENTAL: Requires opening FITS files, slow and may break pagination.",
    ),
    dec_max: float | None = Query(
        None,
        description="Maximum declination (degrees). EXPERIMENTAL: Requires opening FITS files, slow and may break pagination.",
    ),
    has_calibrator: bool | None = Query(
        None,
        description="Filter by calibrator detection status. EXPERIMENTAL: Uses heuristic path pattern matching, not actual detection results.",
    ),
) -> ImageList:
    """List available images for SkyView.

    Working filters (SQL-level, fast, accurate pagination):
    - start_date, end_date: Filter by creation timestamp
    - noise_max: Filter by noise level (Jy)
    - ms_path: Search MS path patterns
    - image_type: Filter by image type
    - pbcor: Filter by primary-beam correction status

    Experimental filters (post-processing, slower, pagination issues):
    - dec_min, dec_max: Extract coordinates from FITS headers (slow)
    - has_calibrator: Heuristic pattern matching on MS path

    Note: Declination and calibrator filters require opening FITS files or pattern matching,
    which is inefficient. For production use, store center_ra_deg/center_dec_deg in the
    images table and add a has_calibrator boolean column.
    """
    cfg = request.app.state.cfg
    limit = max(1, min(limit, 1000)) if limit > 0 else 100
    offset = max(0, offset) if offset >= 0 else 0
    db_path = cfg.products_db
    items: list[ImageInfo] = []
    total = 0
    if not db_path.exists():
        return ImageList(items=items, total=0)
    with _connect(db_path) as conn:
        where_clauses = []
        params: list[object] = []

        # Basic filters
        if ms_path:
            where_clauses.append("ms_path LIKE ?")
            params.append(f"%{ms_path}%")
        if image_type:
            where_clauses.append("type = ?")
            params.append(image_type)
        if pbcor is not None:
            where_clauses.append("pbcor = ?")
            params.append(1 if pbcor else 0)

        # Date range filters
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
                start_timestamp = start_dt.timestamp()
                where_clauses.append("created_at >= ?")
                params.append(start_timestamp)
            except (ValueError, AttributeError):
                pass  # Ignore invalid date format
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                end_timestamp = end_dt.timestamp()
                where_clauses.append("created_at <= ?")
                params.append(end_timestamp)
            except (ValueError, AttributeError):
                pass  # Ignore invalid date format

        # Noise threshold filter
        if noise_max is not None:
            where_clauses.append("noise_jy <= ?")
            params.append(noise_max)

        # Declination filters (require extracting from FITS or photometry table)
        # Note: These filters require RA/Dec coordinates which are not stored in images table
        # For now, we'll apply post-filtering if coordinates are available
        # This is a limitation - ideally we'd store center_ra_deg/center_dec_deg in the DB

        # Calibrator filter (requires checking MS path or joining with calibrator table)
        # Note: This requires additional logic to determine if MS has calibrator
        # For now, we can check ms_path patterns if there's a convention

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        count_query = f"SELECT COUNT(*) as total FROM images{where_sql}"
        total_row = conn.execute(count_query, params).fetchone()
        total = total_row["total"] if total_row else 0

        # For post-filtering (dec/calibrator), we need to fetch more rows first
        # Then apply post-filters, then apply offset/limit
        needs_post_filter = dec_min is not None or dec_max is not None or has_calibrator is not None
        fetch_limit = limit + offset + 1000 if needs_post_filter else limit
        fetch_offset = 0 if needs_post_filter else offset

        query = f"""
            SELECT id, path, ms_path, created_at, type, beam_major_arcsec, noise_jy, pbcor
            FROM images
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params_query = params.copy()
        params_query.extend([fetch_limit, fetch_offset])
        rows = conn.execute(query, params_query).fetchall()

        # Post-filter by declination if requested (requires extracting from FITS)
        # This is inefficient but necessary until RA/Dec are stored in DB
        filtered_rows = []
        for r in rows:
            # Extract RA/Dec from FITS if declination filter is requested
            center_dec = None
            if dec_min is not None or dec_max is not None:
                fits_path = get_fits_path(r["path"])
                if fits_path and Path(fits_path).exists():
                    try:
                        from astropy.io import fits
                        from astropy.wcs import WCS

                        with fits.open(fits_path) as hdul:
                            hdr = hdul[0].header
                            try:
                                wcs = WCS(hdr)
                                if wcs.has_celestial:
                                    center_pix = [
                                        hdr.get("NAXIS1", 0) / 2,
                                        hdr.get("NAXIS2", 0) / 2,
                                    ]
                                    if hdr.get("NAXIS", 0) >= 2:
                                        ra, center_dec = wcs.all_pix2world(
                                            center_pix[0], center_pix[1], 0
                                        )
                            except (
                                ValueError,
                                TypeError,
                                AttributeError,
                                KeyError,
                            ) as e:
                                logger.debug(
                                    f"Could not parse WCS for dec filter (image {r['id'] if 'id' in r.keys() else 'unknown'}): {e}"
                                )
                    except (OSError, IOError, KeyError) as e:
                        logger.debug(
                            f"Could not read FITS for dec filter (image {r['id'] if 'id' in r.keys() else 'unknown'}): {e}"
                        )

            # Apply declination filter
            if dec_min is not None and center_dec is not None and center_dec < dec_min:
                continue
            if dec_max is not None and center_dec is not None and center_dec > dec_max:
                continue

            # Apply calibrator filter (check ms_path pattern - this is a heuristic)
            if has_calibrator is not None:
                # Check if MS path contains calibrator indicators
                # This is a simple heuristic - may need refinement based on actual naming conventions
                ms_path_lower = r["ms_path"].lower()
                has_cal = any(
                    indicator in ms_path_lower for indicator in ["cal", "calibrator", "3c", "j1331"]
                )
                if has_calibrator and not has_cal:
                    continue
                if has_calibrator is False and has_cal:
                    continue

            filtered_rows.append(r)

        # Apply offset/limit after post-filtering
        if dec_min is not None or dec_max is not None or has_calibrator is not None:
            # Recalculate total - need to count all matching rows
            # For now, use filtered count (may be inaccurate if we hit fetch_limit)
            total = len(filtered_rows)
            # Apply offset/limit
            filtered_rows = filtered_rows[offset : offset + limit]
        else:
            # No post-filtering needed, rows already have correct limit/offset applied
            pass

        for r in filtered_rows:
            # Extract RA/Dec for response if available
            center_ra = None
            center_dec = None
            fits_path = get_fits_path(r["path"])
            if fits_path and Path(fits_path).exists():
                try:
                    from astropy.io import fits
                    from astropy.wcs import WCS

                    with fits.open(fits_path) as hdul:
                        hdr = hdul[0].header
                        try:
                            wcs = WCS(hdr)
                            if wcs.has_celestial:
                                center_pix = [
                                    hdr.get("NAXIS1", 0) / 2,
                                    hdr.get("NAXIS2", 0) / 2,
                                ]
                                if hdr.get("NAXIS", 0) >= 2:
                                    center_ra, center_dec = wcs.all_pix2world(
                                        center_pix[0], center_pix[1], 0
                                    )
                        except (ValueError, TypeError, AttributeError, KeyError) as e:
                            logger.debug(
                                f"Could not parse WCS for response (image {r['id'] if 'id' in r.keys() else 'unknown'}): {e}"
                            )
                except (OSError, IOError, KeyError) as e:
                    logger.debug(
                        f"Could not read FITS for response (image {r['id'] if 'id' in r.keys() else 'unknown'}): {e}"
                    )

            items.append(
                ImageInfo(
                    id=r["id"],
                    path=r["path"],
                    ms_path=r["ms_path"],
                    created_at=(
                        datetime.fromtimestamp(r["created_at"]) if r["created_at"] else None
                    ),
                    type=r["type"],
                    beam_major_arcsec=r["beam_major_arcsec"],
                    beam_minor_arcsec=None,
                    beam_pa_deg=None,
                    noise_jy=r["noise_jy"],
                    peak_flux_jy=None,
                    pbcor=bool(r["pbcor"]),
                    center_ra_deg=center_ra,
                    center_dec_deg=center_dec,
                    image_size_deg=None,
                    pixel_size_arcsec=None,
                )
            )
    return ImageList(items=items, total=total)


@router.get("/images/{image_id}/fits")
def get_image_fits(request: Request, image_id: int):
    cfg = request.app.state.cfg
    db_path = cfg.products_db
    if not db_path.exists():
        return HTMLResponse(status_code=404, content="Database not found")
    with _connect(db_path) as conn:
        row = conn.execute("SELECT path FROM images WHERE id = ?", (image_id,)).fetchone()
        if not row:
            return HTMLResponse(status_code=404, content="Image not found")
        image_path = row["path"]
    fits_path = get_fits_path(image_path)
    if not fits_path or not Path(fits_path).exists():
        return HTMLResponse(
            status_code=404,
            content=f"FITS file not found for image {image_id}. Conversion may have failed.",
        )
    return FileResponse(fits_path, media_type="application/fits", filename=Path(fits_path).name)


@router.get("/images/{image_id}", response_model=ImageDetail)
def get_image_detail(request: Request, image_id: int):
    from astropy import units as u
    from astropy.coordinates import SkyCoord
    from astropy.io import fits
    from astropy.wcs import WCS

    cfg = request.app.state.cfg
    db_path = cfg.products_db
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="Database not found")
    with _connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT id, path, ms_path, created_at, type, beam_major_arcsec,
                   beam_minor_arcsec, beam_pa_deg, noise_jy, pbcor
            FROM images
            WHERE id = ?
            """,
            (image_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Image {image_id} not found")
        image_path = row["path"]
        n_meas = 0
        try:
            tables = {
                r[0]
                for r in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            if "photometry" in tables:
                cols = {r[1] for r in conn.execute("PRAGMA table_info(photometry)").fetchall()}
                if "image_path" in cols:
                    count_row = conn.execute(
                        "SELECT COUNT(*) as cnt FROM photometry WHERE image_path = ?",
                        (image_path,),
                    ).fetchone()
                    n_meas = count_row["cnt"] if count_row else 0
        except Exception as e:
            logger.debug(f"Could not count measurements for image {image_id}: {e}")
        n_runs = 0
        ra = dec = ra_hms = dec_dms = gal_l = b = frequency = bandwidth = datetime_str = None
        fits_path = get_fits_path(image_path)
        if fits_path and Path(fits_path).exists():
            try:
                with fits.open(fits_path) as hdul:
                    hdr = hdul[0].header
                    try:
                        wcs = WCS(hdr)
                        if wcs.has_celestial:
                            center_pix = [
                                hdr.get("NAXIS1", 0) / 2,
                                hdr.get("NAXIS2", 0) / 2,
                            ]
                            if hdr.get("NAXIS", 0) >= 2:
                                ra, dec = wcs.all_pix2world(center_pix[0], center_pix[1], 0)
                                coord = SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")
                                ra_hms = coord.ra.to_string(unit=u.hour, sep=":", precision=2)
                                dec_dms = coord.dec.to_string(unit=u.deg, sep=":", precision=2)
                                gal_l = coord.galactic.l.deg
                                b = coord.galactic.b.deg
                    except (ValueError, TypeError, AttributeError, KeyError) as e:
                        # WCS parsing can fail if header is incomplete or malformed
                        logger.debug(f"Could not parse WCS coordinates for image {image_id}: {e}")
                    if "RESTFRQ" in hdr:
                        frequency = hdr["RESTFRQ"] / 1e6
                    elif "CRVAL3" in hdr and "CUNIT3" in hdr:
                        freq_val = hdr["CRVAL3"]
                        freq_unit = hdr["CUNIT3"]
                        if freq_unit == "Hz":
                            frequency = freq_val / 1e6
                        elif freq_unit == "MHz":
                            frequency = freq_val
                    if "CDELT3" in hdr and "CUNIT3" in hdr:
                        bw_val = abs(hdr["CDELT3"])
                        bw_unit = hdr["CUNIT3"]
                        if bw_unit == "Hz":
                            bandwidth = bw_val / 1e6
                        elif bw_unit == "MHz":
                            bandwidth = bw_val
                    if "DATE-OBS" in hdr:
                        datetime_str = hdr["DATE-OBS"]
            except (OSError, IOError, KeyError, ValueError, TypeError) as e:
                # FITS reading can fail for various reasons (corrupted file, missing keys, etc.)
                logger.warning(
                    f"Failed to read FITS header for image {image_id} ({image_path}): {e}",
                    exc_info=True,
                )
            except Exception as e:
                # Catch-all for unexpected errors during FITS reading
                logger.error(
                    f"Unexpected error reading FITS header for image {image_id} ({image_path}): {e}",
                    exc_info=True,
                )
        name = Path(image_path).name
        return ImageDetail(
            id=image_id,
            name=name,
            path=image_path,
            ms_path=row["ms_path"],
            ra=ra,
            dec=dec,
            ra_hms=ra_hms,
            dec_dms=dec_dms,
            gal_l=gal_l,
            b=b,
            frequency=frequency,
            bandwidth=bandwidth,
            datetime=datetime.fromisoformat(datetime_str) if datetime_str else None,
            created_at=(
                datetime.fromtimestamp(row["created_at"]) if row["created_at"] is not None else None
            ),
            n_meas=n_meas,
            n_runs=n_runs,
            type=row["type"],
            pbcor=bool(row["pbcor"]),
            beam_bmaj=((row["beam_major_arcsec"] / 3600.0) if row["beam_major_arcsec"] else None),
            beam_bmin=((row["beam_minor_arcsec"] / 3600.0) if row["beam_minor_arcsec"] else None),
            beam_bpa=row["beam_pa_deg"],
            rms_median=(row["noise_jy"] * 1000.0) if row["noise_jy"] else None,
            rms_min=None,
            rms_max=None,
        )
