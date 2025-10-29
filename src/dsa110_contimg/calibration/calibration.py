from typing import List, Optional

import os
import fnmatch
from casatasks import bandpass as casa_bandpass  # type: ignore[import]
from casatasks import gaincal as casa_gaincal  # type: ignore[import]
# setjy imported elsewhere; avoid unused import here
from casatasks import fluxscale as casa_fluxscale  # type: ignore[import]
from dsa110_contimg.qa.pipeline_quality import check_calibration_quality
import logging

logger = logging.getLogger(__name__)


def _resolve_field_ids(ms: str, field_sel: str) -> List[int]:
    """Resolve CASA-like field selection into a list of FIELD_ID integers.

    Supports numeric indices, comma lists, numeric ranges ("A~B"), and
    name/glob matching against FIELD::NAME.
    """
    from casacore.tables import table

    sel = str(field_sel).strip()
    # Try numeric selections first: comma-separated tokens and A~B ranges
    ids: List[int] = []
    numeric_tokens = [
        tok.strip() for tok in sel.replace(
            ";", ",").split(",") if tok.strip()]

    def _add_numeric(tok: str) -> bool:
        if "~" in tok:
            a, b = tok.split("~", 1)
            if a.strip().isdigit() and b.strip().isdigit():
                ai, bi = int(a), int(b)
                lo, hi = (ai, bi) if ai <= bi else (bi, ai)
                ids.extend(list(range(lo, hi + 1)))
                return True
            return False
        if tok.isdigit():
            ids.append(int(tok))
            return True
        return False

    any_numeric = False
    for tok in numeric_tokens:
        if _add_numeric(tok):
            any_numeric = True

    if any_numeric:
        # Deduplicate and return
        return sorted(set(ids))

    # Fall back to FIELD::NAME glob matching
    patterns = [p for p in numeric_tokens if p]
    # If no separators were present, still try the full selector as a single
    # pattern
    if not patterns:
        patterns = [sel]

    try:
        with table(f"{ms}::FIELD") as tf:
            names = list(tf.getcol("NAME"))
            out = []
            for i, name in enumerate(names):
                for pat in patterns:
                    if fnmatch.fnmatchcase(str(name), pat):
                        out.append(int(i))
                        break
            return sorted(set(out))
    except Exception:
        return []


def solve_delay(
    ms: str,
    cal_field: str,
    refant: str,
    table_prefix: Optional[str] = None,
    combine_spw: bool = False,
    t_slow: str = "inf",
    t_fast: Optional[str] = "60s",
) -> List[str]:
    """
    Solve delay (K) on slow and optional fast timescales using CASA gaincal.

    Uses casatasks.gaincal with gaintype='K' to avoid explicit casatools
    calibrater usage, which can be unstable in some notebook environments.
    """
    from casacore.tables import table  # type: ignore[import]
    import numpy as np  # type: ignore[import]

    # Validate data availability before attempting calibration
    print(f"Validating data for delay solve on field(s) {cal_field}...")
    with table(ms) as tb:
        field_ids = tb.getcol('FIELD_ID')
        # Resolve selector (names, ranges, lists) to numeric FIELD_IDs
        target_ids = _resolve_field_ids(ms, str(cal_field))
        if not target_ids:
            raise ValueError(f"Unable to resolve field selection: {cal_field}")
        field_mask = np.isin(
            field_ids, np.asarray(
                target_ids, dtype=field_ids.dtype))
        if not np.any(field_mask):
            raise ValueError(f"No data found for field selection {cal_field}")

        # Check if reference antenna exists in this field
        row_idx = np.nonzero(field_mask)[0]
        if row_idx.size == 0:
            raise ValueError(f"No data found for field selection {cal_field}")
        start_row = int(row_idx[0])
        nrow_sel = int(row_idx[-1] - start_row + 1)

        ant1_slice = tb.getcol('ANTENNA1', startrow=start_row, nrow=nrow_sel)
        ant2_slice = tb.getcol('ANTENNA2', startrow=start_row, nrow=nrow_sel)
        rel_idx = row_idx - start_row
        field_ant1 = ant1_slice[rel_idx]
        field_ant2 = ant2_slice[rel_idx]
        ref_present = np.any(
            (field_ant1 == int(refant)) | (
                field_ant2 == int(refant)))
        if not ref_present:
            raise ValueError(
                f"Reference antenna {refant} not found in field {cal_field}")

        # Check for unflagged data
        field_flags = np.stack([tb.getcell('FLAG', int(r))
                               for r in row_idx], axis=2)
        unflagged_count = int(np.sum(~field_flags))
        if unflagged_count == 0:
            raise ValueError(f"All data in field {cal_field} is flagged")

        import numpy as _np  # type: ignore[import]
        print(
            f"Field {cal_field}: {_np.sum(field_mask)} rows, "
            f"{unflagged_count} unflagged points"
        )

    # Use more conservative combination settings to avoid empty arrays
    # For field-per-integration MS, avoid combining across scans/obs
    combine = "spw" if combine_spw else ""
    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"

    tables: List[str] = []

    # Slow (infinite) delay solve with error handling
    try:
        print(
            f"Running delay solve (K) on field {cal_field} "
            f"with refant {refant}..."
        )
        casa_gaincal(
            vis=ms,
            caltable=f"{table_prefix}_kcal",
            field=cal_field,
            solint=t_slow,
            refant=refant,
            gaintype="K",
            combine=combine
        )
        tables.append(f"{table_prefix}_kcal")
        print(f"✓ Delay solve completed: {table_prefix}_kcal")
    except Exception as e:
        print(f"Delay solve failed: {e}")
        # Try with even more conservative settings
        try:
            print("Retrying with no combination...")
            casa_gaincal(
                vis=ms,
                caltable=f"{table_prefix}_kcal",
                field=cal_field,
                solint=t_slow,
                refant=refant,
                gaintype="K",
                combine=""
            )
            tables.append(f"{table_prefix}_kcal")
            print(f"✓ Delay solve completed (retry): {table_prefix}_kcal")
        except Exception as e2:
            raise RuntimeError(
                f"Delay solve failed even with conservative settings: {e2}")

    # Optional fast (short) delay solve
    if t_fast:
        try:
            print(f"Running fast delay solve (K) on field {cal_field}...")
            casa_gaincal(
                vis=ms,
                caltable=f"{table_prefix}_2kcal",
                field=cal_field,
                solint=t_fast,
                refant=refant,
                gaintype="K",
                combine=combine
            )
            tables.append(f"{table_prefix}_2kcal")
            print(f"✓ Fast delay solve completed: {table_prefix}_2kcal")
        except Exception as e:
            print(f"Fast delay solve failed: {e}")
            # Skip fast solve if it fails
            print("Skipping fast delay solve...")

    # QA validation of delay calibration tables
    try:
        from dsa110_contimg.qa.pipeline_quality import check_calibration_quality
        check_calibration_quality(tables, ms_path=ms, alert_on_issues=True)
    except Exception as e:
        print(f"Warning: QA validation failed: {e}")

    return tables


def solve_bandpass(
    ms: str,
    cal_field: str,
    refant: str,
    ktable: Optional[str],
    table_prefix: Optional[str] = None,
    set_model: bool = True,
    model_standard: str = "Perley-Butler 2017",
    combine_fields: bool = False,
    minsnr: float = 5.0,
    uvrange: str = "",
) -> List[str]:
    """Solve bandpass in two stages: amplitude (bacal) then phase (bpcal)."""
    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"

    # For bandpass calibration, use only the peak field and combine across all fields
    # Extract the peak field from the range (e.g., "19~23" -> "23")
    if '~' in str(cal_field):
        peak_field = str(cal_field).split(
            '~')[-1]  # Use the last field in range
        print(
            f"Using peak field {peak_field} for bandpass calibration (from range {cal_field})")
    else:
        peak_field = str(cal_field)
        print(f"Using field {peak_field} for bandpass calibration")

    # Avoid setjy here; CLI will write a calibrator MODEL_DATA when available.
    _unused = (set_model, model_standard)

    # Combine across scans and fields when requested; otherwise do not combine
    comb = "scan,field" if combine_fields else ""

    amplitude_ok = False
    try:
        print(
            f"Running bandpass amplitude solve on field {peak_field} (combining across fields)...")
        gaintable_list = [ktable] if ktable else []
        kwargs = dict(
            vis=ms,
            caltable=f"{table_prefix}_bacal",
            field=cal_field,  # Use full range for data selection
            solint="inf",
            combine=comb,
            refant=refant,
            solnorm=True,
            bandtype="B",
            gaintable=gaintable_list,
            minsnr=minsnr,
            selectdata=True)
        if uvrange:
            kwargs["uvrange"] = uvrange
        casa_bandpass(**kwargs)
        print(f"✓ Bandpass amplitude solve completed: {table_prefix}_bacal")
        amplitude_ok = True
    except Exception as exc:
        print(f"Bandpass amplitude solve failed (continuing without bacal): {exc}")

    print(
        f"Running bandpass phase solve on field {peak_field} (combining across fields)...")
    gaintable_list2 = ([ktable] if ktable else []) + ([f"{table_prefix}_bacal"] if amplitude_ok else [])
    kwargs = dict(
        vis=ms,
        caltable=f"{table_prefix}_bpcal",
        field=cal_field,  # Use full range for data selection
        solint="inf",
        combine=comb,
        refant=refant,
        solnorm=True,
        bandtype="B",
        gaintable=gaintable_list2,
        minsnr=minsnr,
        selectdata=True)
    if uvrange:
        kwargs["uvrange"] = uvrange
    casa_bandpass(**kwargs)
    print(f"✓ Bandpass phase solve completed: {table_prefix}_bpcal")

    out = []
    if amplitude_ok:
        out.append(f"{table_prefix}_bacal")
    out.append(f"{table_prefix}_bpcal")
    
    # QA validation of bandpass calibration tables
    try:
        from dsa110_contimg.qa.pipeline_quality import check_calibration_quality
        check_calibration_quality(out, ms_path=ms, alert_on_issues=True)
    except Exception as e:
        print(f"Warning: QA validation failed: {e}")
    
    return out


def solve_gains(
    ms: str,
    cal_field: str,
    refant: str,
    ktable: Optional[str],
    bptables: List[str],
    table_prefix: Optional[str] = None,
    t_short: str = "60s",
    do_fluxscale: bool = False,
    combine_fields: bool = False,
    *,
    phase_only: bool = False,
    uvrange: str = "",
    solint: str = "inf",
) -> List[str]:
    """Solve gain amplitude and phase; optionally short-timescale and fluxscale."""
    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"

    # For gain calibration, use only the peak field and combine across all
    # fields
    if '~' in str(cal_field):
        peak_field = str(cal_field).split(
            '~')[-1]  # Use the last field in range
        print(
            f"Using peak field {peak_field} for gain calibration (from range {cal_field})")
    else:
        peak_field = str(cal_field)
        print(f"Using field {peak_field} for gain calibration")

    gaintable = ([ktable] if ktable else []) + bptables
    # Combine across scans and fields when requested; otherwise do not combine
    comb = "scan,field" if combine_fields else ""

    if not phase_only:
        print(
            f"Running gain amplitude solve on field {peak_field} (combining across fields)...")
        kwargs = dict(
            vis=ms,
            caltable=f"{table_prefix}_gacal",
            field=cal_field,  # Use full range for data selection
            solint=solint,
            refant=refant,
            gaintype="G",
            calmode="a",
            gaintable=gaintable,
            combine=comb,
            minsnr=5.0,
            selectdata=True,
        )
        if uvrange:
            kwargs["uvrange"] = uvrange
        casa_gaincal(**kwargs)
        print(f"✓ Gain amplitude solve completed: {table_prefix}_gacal")

    gaintable2 = gaintable + [f"{table_prefix}_gacal"]
    print(
        f"Running gain phase solve on field {peak_field} (combining across fields)...")
    kwargs = dict(
        vis=ms,
        caltable=f"{table_prefix}_gpcal",
        field=cal_field,  # Use full range for data selection
        solint=solint,
        refant=refant,
        gaintype="G",
        calmode="p",
        gaintable=gaintable2 if not phase_only else gaintable,
        combine=comb,
        minsnr=5.0,
        selectdata=True,
    )
    if uvrange:
        kwargs["uvrange"] = uvrange
    casa_gaincal(**kwargs)
    print(f"✓ Gain phase solve completed: {table_prefix}_gpcal")

    out = [] if phase_only else [f"{table_prefix}_gacal"]
    out.append(f"{table_prefix}_gpcal")

    if t_short and not phase_only:
        print(
            f"Running short-timescale gain solve on field {peak_field} (combining across fields)...")
        kwargs = dict(
            vis=ms,
            caltable=f"{table_prefix}_2gcal",
            field=cal_field,  # Use full range for data selection
            solint=t_short,
            refant=refant,
            gaintype="G",
            calmode="ap",
            gaintable=gaintable2,
            combine=comb,
            minsnr=5.0,
            selectdata=True,
        )
        if uvrange:
            kwargs["uvrange"] = uvrange
        casa_gaincal(**kwargs)
        print(f"✓ Short-timescale gain solve completed: {table_prefix}_2gcal")
        out.append(f"{table_prefix}_2gcal")

    if do_fluxscale:
        print(f"Running flux scaling on field {peak_field}...")
        casa_fluxscale(
            vis=ms,
            caltable=f"{table_prefix}_gacal",
            fluxtable=f"{table_prefix}_flux.cal",
            reference=peak_field,  # Use peak field for reference
        )
        print(f"✓ Flux scaling completed: {table_prefix}_flux.cal")
        out.append(f"{table_prefix}_flux.cal")

    # QA validation of gain calibration tables
    try:
        from dsa110_contimg.qa.pipeline_quality import check_calibration_quality
        check_calibration_quality(out, ms_path=ms, alert_on_issues=True)
    except Exception as e:
        print(f"Warning: QA validation failed: {e}")

    return out
