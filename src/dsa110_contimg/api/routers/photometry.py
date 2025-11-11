"""Photometry and sources-related API routes extracted from routes.py."""
from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from dsa110_contimg.api.data_access import _connect, fetch_source_timeseries
from dsa110_contimg.api.models import (
    Detection,
    DetectionList,
    ExternalCatalogMatch,
    ExternalCatalogsResponse,
    LightCurveData,
    PostageStampInfo,
    PostageStampsResponse,
    SourceDetail,
    SourceFluxPoint,
    SourceSearchResponse,
    SourceTimeseries,
    VariabilityMetrics,
)

router = APIRouter()


@router.post("/sources/search", response_model=SourceSearchResponse)
def sources_search(request: Request, request_body: dict):
    cfg = request.app.state.cfg
    source_id = request_body.get("source_id", "")
    if not source_id:
        return SourceSearchResponse(sources=[], total=0)
    source_data = fetch_source_timeseries(cfg.products_db, source_id)
    if source_data is None:
        return SourceSearchResponse(sources=[], total=0)
    flux_points = [SourceFluxPoint(**fp) for fp in source_data["flux_points"]]
    source = SourceTimeseries(
        source_id=source_data["source_id"],
        ra_deg=source_data["ra_deg"],
        dec_deg=source_data["dec_deg"],
        catalog=source_data["catalog"],
        flux_points=flux_points,
        mean_flux_jy=source_data["mean_flux_jy"],
        std_flux_jy=source_data["std_flux_jy"],
        chi_sq_nu=source_data["chi_sq_nu"],
        is_variable=source_data["is_variable"],
    )
    return SourceSearchResponse(sources=[source], total=1)


@router.get("/sources/{source_id}/variability", response_model=VariabilityMetrics)
def get_source_variability(request: Request, source_id: str):
    from dsa110_contimg.photometry.source import Source
    cfg = request.app.state.cfg
    try:
        source = Source(source_id=source_id, products_db=cfg.products_db)
        metrics = source.calc_variability_metrics()
        return VariabilityMetrics(
            source_id=source_id,
            v=metrics.get("v", 0.0),
            eta=metrics.get("eta", 0.0),
            vs_mean=metrics.get("vs_mean"),
            m_mean=metrics.get("m_mean"),
            n_epochs=metrics.get("n_epochs", 0),
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found or error calculating metrics: {str(e)}")


@router.get("/sources/{source_id}/lightcurve", response_model=LightCurveData)
def get_source_lightcurve(request: Request, source_id: str):
    from astropy.time import Time
    from dsa110_contimg.photometry.source import Source
    cfg = request.app.state.cfg
    try:
        source = Source(source_id=source_id, products_db=cfg.products_db)
        if source.measurements.empty:
            raise HTTPException(status_code=404, detail=f"No measurements found for source {source_id}")
        flux_points = []
        normalized_flux_points = []
        for _, row in source.measurements.iterrows():
            mjd = row.get("mjd", 0.0)
            if mjd == 0 and "measured_at" in row:
                mjd = Time(row["measured_at"], format="datetime").mjd
            time_str = Time(mjd, format="mjd").iso if mjd > 0 else ""
            flux_jy = row.get("peak_jyb", row.get("flux_jy", 0.0))
            flux_err_jy = row.get("peak_err_jyb", row.get("flux_err_jy", None))
            image_path = row.get("image_path", "")
            flux_points.append(SourceFluxPoint(mjd=float(mjd), time=time_str, flux_jy=float(flux_jy) if flux_jy else 0.0, flux_err_jy=float(flux_err_jy) if flux_err_jy else None, image_id=image_path))
            if "normalized_flux_jy" in row:
                norm_flux_jy = row.get("normalized_flux_jy", 0.0)
                norm_flux_err_jy = row.get("normalized_flux_err_jy", None)
                normalized_flux_points.append(SourceFluxPoint(mjd=float(mjd), time=time_str, flux_jy=float(norm_flux_jy) if norm_flux_jy else 0.0, flux_err_jy=float(norm_flux_err_jy) if norm_flux_err_jy else None, image_id=image_path))
        return LightCurveData(source_id=source_id, ra_deg=source.ra_deg, dec_deg=source.dec_deg, flux_points=flux_points, normalized_flux_points=normalized_flux_points if normalized_flux_points else None)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found or error loading measurements: {str(e)}")


@router.get("/sources/{source_id}/postage_stamps", response_model=PostageStampsResponse)
def get_source_postage_stamps(
    request: Request,
    source_id: str,
    size_arcsec: float = Query(60.0, description="Cutout size in arcseconds"),
    max_stamps: int = Query(20, description="Maximum number of stamps to return"),
):
    from dsa110_contimg.photometry.source import Source
    from dsa110_contimg.qa.postage_stamps import create_cutout
    cfg = request.app.state.cfg
    try:
        source = Source(source_id=source_id, products_db=cfg.products_db)
        if source.measurements.empty:
            raise HTTPException(status_code=404, detail=f"No measurements found for source {source_id}")
        stamps = []
        temp_dir = Path(tempfile.gettempdir()) / "postage_stamps"
        temp_dir.mkdir(exist_ok=True)
        image_paths = source.measurements["image_path"].dropna().unique()[:max_stamps]
        for image_path in image_paths:
            if not Path(image_path).exists():
                stamps.append(PostageStampInfo(image_path=image_path, mjd=0.0, error=f"Image file not found: {image_path}"))
                continue
            img_measurements = source.measurements[source.measurements["image_path"] == image_path]
            mjd = img_measurements["mjd"].iloc[0] if "mjd" in img_measurements.columns else 0.0
            try:
                cutout_path = temp_dir / f"{source_id}_{Path(image_path).stem}_cutout.fits"
                fits_path = Path(image_path)
                size_arcmin = size_arcsec / 60.0
                cutout_data, cutout_wcs, metadata = create_cutout(fits_path=fits_path, ra_deg=source.ra_deg, dec_deg=source.dec_deg, size_arcmin=size_arcmin)
                from astropy.io import fits as _fits
                hdu = _fits.PrimaryHDU(data=cutout_data, header=cutout_wcs.to_header())
                hdu.writeto(cutout_path, overwrite=True)
                stamps.append(PostageStampInfo(image_path=image_path, mjd=float(mjd), cutout_path=str(cutout_path)))
            except Exception as e:
                stamps.append(PostageStampInfo(image_path=image_path, mjd=float(mjd), error=str(e)))
        return PostageStampsResponse(source_id=source_id, stamps=stamps)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting postage stamps for {source_id}: {e}")


@router.get("/sources/{source_id}/external_catalogs", response_model=ExternalCatalogsResponse)
def get_source_external_catalogs(
    request: Request,
    source_id: str,
    radius_arcsec: float = Query(5.0, description="Search radius in arcseconds"),
    catalogs: Optional[str] = Query(None, description="Comma-separated list of catalogs (simbad,ned,gaia). If None, queries all. "),
    timeout: float = Query(30.0, description="Query timeout in seconds"),
):
    from dsa110_contimg.photometry.source import Source
    cfg = request.app.state.cfg
    try:
        source = Source(source_id=source_id, products_db=cfg.products_db)
        if source.ra_deg is None or source.dec_deg is None:
            raise HTTPException(status_code=404, detail=f"Source {source_id} does not have RA/Dec coordinates")
        catalog_list = None
        if catalogs:
            catalog_list = [c.strip().lower() for c in catalogs.split(',')]
            valid_catalogs = {"simbad", "ned", "gaia"}
            invalid = set(catalog_list) - valid_catalogs
            if invalid:
                raise HTTPException(status_code=400, detail=f"Invalid catalogs: {invalid}. Valid options: simbad, ned, gaia")
        import time
        start_time = time.time()
        results = source.crossmatch_external(radius_arcsec=radius_arcsec, catalogs=catalog_list, timeout=timeout)
        query_time = time.time() - start_time
        matches = {}
        for catalog_name in ["simbad", "ned", "gaia"]:
            result = results.get(catalog_name)
            if result is None:
                matches[catalog_name] = ExternalCatalogMatch(catalog=catalog_name, matched=False)
            else:
                if catalog_name == "simbad":
                    matches[catalog_name] = ExternalCatalogMatch(catalog=catalog_name, matched=True, main_id=result.get("main_id"), object_type=result.get("otype"), separation_arcsec=result.get("separation_arcsec"), redshift=result.get("redshift"))
                elif catalog_name == "ned":
                    matches[catalog_name] = ExternalCatalogMatch(catalog=catalog_name, matched=True, main_id=result.get("ned_name"), object_type=result.get("object_type"), separation_arcsec=result.get("separation_arcsec"), redshift=result.get("redshift"))
                elif catalog_name == "gaia":
                    matches[catalog_name] = ExternalCatalogMatch(catalog=catalog_name, matched=True, main_id=result.get("source_id"), separation_arcsec=result.get("separation_arcsec"), parallax=result.get("parallax"), distance=result.get("distance"), pmra=result.get("pmra"), pmdec=result.get("pmdec"), phot_g_mean_mag=result.get("phot_g_mean_mag"))
        return ExternalCatalogsResponse(source_id=source_id, ra_deg=source.ra_deg, dec_deg=source.dec_deg, matches=matches, query_time_sec=query_time)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found or error querying catalogs: {str(e)}")


@router.get("/sources/{source_id}", response_model=SourceDetail)
def get_source_detail(request: Request, source_id: str):
    from dsa110_contimg.photometry.source import Source
    cfg = request.app.state.cfg
    try:
        source = Source(source_id=source_id, products_db=cfg.products_db)
        variability_metrics = None
        try:
            metrics = source.calc_variability_metrics()
            variability_metrics = VariabilityMetrics(
                source_id=source_id,
                v=metrics.get("v", 0.0),
                eta=metrics.get("eta", 0.0),
                vs_mean=metrics.get("vs_mean"),
                m_mean=metrics.get("m_mean"),
                n_epochs=metrics.get("n_epochs", 0),
                is_variable=metrics.get("is_variable", False),
            )
        except Exception:
            pass
        # Compute summary metrics
        n_forced = 0
        mean_flux = std_flux = max_snr = None
        try:
            if not source.measurements.empty:
                forced_mask = source.measurements.get("forced", source.measurements.get("is_forced", False))
                if forced_mask is not False:
                    n_forced = int(forced_mask.sum())
                flux = source.measurements.get("peak_jyb", source.measurements.get("flux_jy"))
                if flux is not None:
                    flux_vals = flux.dropna().astype(float)
                    if len(flux_vals) > 0:
                        mean_flux = float(flux_vals.mean())
                        std_flux = float(flux_vals.std())
                snr_series = source.measurements.get("snr")
                if snr_series is not None:
                    snr_vals = snr_series.dropna().astype(float)
                    if len(snr_vals) > 0:
                        max_snr = float(snr_vals.max())
        except Exception:
            pass
        # Simple ESE probability (heuristic)
        ese_probability = None
        try:
            if variability_metrics:
                v = variability_metrics.v or 0.0
                eta = variability_metrics.eta or 0.0
                chi2_nu = variability_metrics.chi_sq_nu if hasattr(variability_metrics, "chi_sq_nu") else None
                ese_timescale = None
                mean_flux_val = mean_flux
                std_flux_val = std_flux
                score = 0.0
                if eta > 0.1 or v > 0.2:
                    score += 0.4
                elif eta > 0.05 or v > 0.1:
                    score += 0.2
                if chi2_nu and chi2_nu > 3.0:
                    score += 0.3
                elif chi2_nu and chi2_nu > 2.0:
                    score += 0.15
                if ese_timescale:
                    score += 0.2
                if std_flux_val and mean_flux_val and mean_flux_val > 0:
                    flux_fractional_var = std_flux_val / mean_flux_val
                    if flux_fractional_var > 0.3:
                        score += 0.1
                    elif flux_fractional_var > 0.15:
                        score += 0.05
                ese_probability = min(1.0, round(score, 2))
        except Exception:
            ese_probability = None
        return SourceDetail(
            id=source_id,
            name=source.name,
            ra_deg=source.ra_deg,
            dec_deg=source.dec_deg,
            catalog="NVSS",
            n_meas=len(source.measurements),
            n_meas_forced=int(n_forced),
            mean_flux_jy=mean_flux,
            std_flux_jy=std_flux,
            max_snr=max_snr,
            is_variable=variability_metrics.is_variable if variability_metrics else False,
            ese_probability=ese_probability,
            new_source=None,
            variability_metrics=variability_metrics,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found: {str(e)}")


@router.get("/sources/{source_id}/detections", response_model=DetectionList)
def get_source_detections(
    request: Request,
    source_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
):
    from dsa110_contimg.photometry.source import Source
    cfg = request.app.state.cfg
    try:
        source = Source(source_id=source_id, products_db=cfg.products_db)
        if source.measurements.empty:
            return DetectionList(items=[], total=0, page=page, page_size=page_size)
        total = len(source.measurements)
        offset = (page - 1) * page_size
        end = offset + page_size
        page_measurements = source.measurements.iloc[offset:end]
        detections = []
        for _, row in page_measurements.iterrows():
            image_id = None
            image_path = row.get("image_path", "")
            if image_path:
                try:
                    with _connect(cfg.products_db) as conn:
                        img_row = conn.execute("SELECT id FROM images WHERE path = ?", (image_path,)).fetchone()
                        if img_row:
                            image_id = img_row["id"]
                except Exception:
                    pass
            flux_peak = row.get("peak_jyb", row.get("flux_jy", 0.0))
            if flux_peak and flux_peak < 1.0:
                flux_peak = flux_peak * 1000.0
            flux_peak_err = row.get("peak_err_jyb", row.get("flux_err_jy"))
            if flux_peak_err and flux_peak_err < 1.0:
                flux_peak_err = flux_peak_err * 1000.0
            flux_int = row.get("flux_int_jy")
            if flux_int and flux_int < 1.0:
                flux_int = flux_int * 1000.0
            flux_int_err = row.get("flux_int_err_jy")
            if flux_int_err and flux_int_err < 1.0:
                flux_int_err = flux_int_err * 1000.0
            measured_at = None
            if "measured_at" in row and row["measured_at"]:
                try:
                    if isinstance(row["measured_at"], (int, float)):
                        measured_at = datetime.fromtimestamp(row["measured_at"])  # type: ignore
                    else:
                        measured_at = datetime.fromisoformat(str(row["measured_at"]))
                except Exception:
                    pass
            detections.append(
                Detection(
                    id=None,
                    name=None,
                    image_id=image_id,
                    image_path=image_path,
                    ra=float(row.get("ra_deg", 0.0)),
                    dec=float(row.get("dec_deg", 0.0)),
                    flux_peak=float(flux_peak) if flux_peak else 0.0,
                    flux_peak_err=float(flux_peak_err) if flux_peak_err else None,
                    flux_int=float(flux_int) if flux_int else None,
                    flux_int_err=float(flux_int_err) if flux_int_err else None,
                    snr=float(row.get("snr")) if "snr" in row and row.get("snr") is not None else None,
                    forced=bool(row.get("forced", row.get("is_forced", False))),
                    frequency=None,
                    mjd=float(row.get("mjd")) if "mjd" in row and row.get("mjd") is not None else None,
                    measured_at=measured_at,
                )
            )
        return DetectionList(items=detections, total=total, page=page, page_size=page_size)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Source {source_id} not found: {str(e)}")

