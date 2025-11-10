"""Utility functions for imaging CLI."""

import numpy as np
# Ensure CASAPATH is set before importing CASA modules
from dsa110_contimg.utils.casa_init import ensure_casa_path
ensure_casa_path()

from casacore.tables import table


def detect_datacolumn(ms_path: str) -> str:
    """Choose datacolumn for tclean.

    Preference order:
    - Use CORRECTED_DATA if present and contains any non-zero values.
    - Otherwise fall back to DATA.

    **CRITICAL SAFEGUARD**: If CORRECTED_DATA column exists but is unpopulated
    (all zeros), this indicates calibration was attempted but failed. In this case,
    we FAIL rather than silently falling back to DATA to prevent imaging uncalibrated
    data when calibration was expected.

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
                        # Empty MS - can't determine, but CORRECTED_DATA exists
                        # so calibration was attempted, fail to be safe
                        raise RuntimeError(
                            f"CORRECTED_DATA column exists but MS has zero rows: {ms_path}. "
                            f"Calibration appears to have been attempted but failed. "
                            f"Cannot proceed with imaging."
                        )
                    # Sample up to 8 evenly spaced windows of up to 2048 rows
                    windows = 8
                    block = 2048
                    indices = []
                    for i in range(windows):
                        start_idx = int(i * total / max(1, windows))
                        indices.append(max(0, start_idx - block // 2))

                    found_nonzero = False
                    for start in indices:
                        n = min(block, total - start)
                        if n <= 0:
                            continue
                        cd = t.getcol("CORRECTED_DATA", start, n)
                        flags = t.getcol("FLAG", start, n)
                        # Check unflagged data
                        unflagged = cd[~flags]
                        if (
                            len(unflagged) > 0
                            and np.count_nonzero(np.abs(unflagged) > 1e-10) > 0
                        ):
                            found_nonzero = True
                            break

                    if found_nonzero:
                        return "corrected"
                    else:
                        # CORRECTED_DATA exists but is all zeros - calibration failed
                        raise RuntimeError(
                            f"CORRECTED_DATA column exists but appears unpopulated in {ms_path}. "
                            f"Calibration appears to have been attempted but failed (all zeros). "
                            f"Cannot proceed with imaging uncalibrated data. "
                            f"Please verify calibration was applied successfully using: "
                            f"python -m dsa110_contimg.calibration.cli apply --ms {ms_path}"
                        )
                except RuntimeError:
                    raise  # Re-raise our errors
                except Exception as e:
                    # Other exceptions - be safe and fail
                    raise RuntimeError(
                        f"Error checking CORRECTED_DATA in {ms_path}: {e}. "
                        f"Cannot determine if calibration was applied. Cannot proceed."
                    ) from e
            # CORRECTED_DATA doesn't exist - calibration never attempted, fall back to DATA
            return "data"
    except RuntimeError:
        raise  # Re-raise our errors
    except Exception as e:
        # Other exceptions - be safe and fail
        raise RuntimeError(
            f"Error accessing MS {ms_path}: {e}. Cannot determine calibration status. Cannot proceed."
        ) from e


def default_cell_arcsec(ms_path: str) -> float:
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
