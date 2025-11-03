from typing import List, Optional, Union

import os
import fnmatch
from casatasks import bandpass as casa_bandpass  # type: ignore[import]
from casatasks import gaincal as casa_gaincal  # type: ignore[import]
# setjy imported elsewhere; avoid unused import here
from casatasks import fluxscale as casa_fluxscale  # type: ignore[import]
import logging

from dsa110_contimg.calibration.validate import (
    validate_caltable_exists,
    validate_caltable_compatibility,
    validate_caltables_for_use,
)


def _validate_solve_success(caltable_path: str, refant: Optional[Union[int, str]] = None) -> None:
    """Validate that a calibration solve completed successfully.
    
    This ensures we follow "measure twice, cut once" - verify solutions exist
    immediately after each solve completes, before proceeding to the next step.
    
    Args:
        caltable_path: Path to calibration table
        refant: Optional reference antenna ID to verify has solutions
    
    Raises:
        RuntimeError: If table doesn't exist, has no solutions, or refant missing
    """
    from casacore.tables import table  # type: ignore[import]
    
    # Verify table exists
    if not os.path.exists(caltable_path):
        raise RuntimeError(
            f"Calibration solve failed: table was not created: {caltable_path}"
        )
    
    # Verify table has solutions
    try:
        with table(caltable_path, readonly=True) as tb:
            if tb.nrows() == 0:
                raise RuntimeError(
                    f"Calibration solve failed: table has no solutions: {caltable_path}"
                )
            
            # Verify refant has solutions if provided
            if refant is not None:
                refant_int = int(refant) if isinstance(refant, str) else refant
                antennas = tb.getcol('ANTENNA1')
                
                # For antenna-based calibration, check ANTENNA1
                # For baseline-based calibration, check both ANTENNA1 and ANTENNA2
                if 'ANTENNA2' in tb.colnames():
                    ant2 = tb.getcol('ANTENNA2')
                    # Filter out -1 values (baseline-based calibration uses -1 for antenna-based entries)
                    ant2_valid = ant2[ant2 != -1]
                    all_antennas = set(antennas) | set(ant2_valid)
                else:
                    all_antennas = set(antennas)
                
                if refant_int not in all_antennas:
                    raise RuntimeError(
                        f"Calibration solve failed: reference antenna {refant} has no solutions "
                        f"in table: {caltable_path}. Available antennas: {sorted(all_antennas)}"
                    )
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(
            f"Calibration solve validation failed: unable to read table {caltable_path}. "
            f"Error: {e}"
        ) from e

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
    
    **PRECONDITION**: MODEL_DATA must be populated before calling this function.
    This ensures consistent, reliable calibration results across all calibrators
    (bright or faint). The calling code should verify MODEL_DATA exists and is
    populated before invoking solve_delay().
    """
    from casacore.tables import table  # type: ignore[import]
    import numpy as np  # type: ignore[import]

    # Validate data availability before attempting calibration
    print(f"Validating data for delay solve on field(s) {cal_field}...")
    
    # PRECONDITION CHECK: Verify MODEL_DATA exists and is populated
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators (bright or faint).
    with table(ms) as tb:
        if "MODEL_DATA" not in tb.colnames():
            raise ValueError(
                f"MODEL_DATA column does not exist in MS. "
                f"This is a required precondition for K-calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_delay()."
            )
        
        # Check if MODEL_DATA is populated (not all zeros)
        model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
        if np.all(np.abs(model_sample) < 1e-10):
            raise ValueError(
                f"MODEL_DATA column exists but is all zeros (unpopulated). "
                f"This is a required precondition for K-calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_delay()."
            )
        
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
        # PRECONDITION CHECK: Verify K-calibration solve completed successfully
        # This ensures we follow "measure twice, cut once" - verify solutions exist
        # immediately after solve completes, before proceeding.
        _validate_solve_success(f"{table_prefix}_kcal", refant=refant)
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
            # PRECONDITION CHECK: Verify K-calibration solve completed successfully
            # This ensures we follow "measure twice, cut once" - verify solutions exist
            # immediately after solve completes, before proceeding.
            _validate_solve_success(f"{table_prefix}_kcal", refant=refant)
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
            # PRECONDITION CHECK: Verify fast K-calibration solve completed successfully
            # This ensures we follow "measure twice, cut once" - verify solutions exist
            # immediately after solve completes, before proceeding.
            _validate_solve_success(f"{table_prefix}_2kcal", refant=refant)
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
    """Solve bandpass in two stages: amplitude (bacal) then phase (bpcal).
    
    **PRECONDITION**: If `ktable` is provided, it must exist and be compatible
    with the MS. This ensures consistent, reliable calibration results.
    """
    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"
    
    # PRECONDITION CHECK: Validate K-table if provided
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators.
    if ktable:
        print(f"Validating K-table before bandpass calibration: {ktable}")
        try:
            validate_caltable_exists(ktable)
            # Convert refant string to int for validation
            refant_int = int(refant) if isinstance(refant, str) else refant
            warnings = validate_caltable_compatibility(
                ktable, ms, refant=refant_int
            )
            if warnings:
                print(f"Warnings for K-table compatibility: {warnings}")
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(
                f"K-table validation failed. This is a required precondition for "
                f"bandpass calibration. Error: {e}"
            ) from e
    
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
        # PRECONDITION CHECK: Verify bandpass amplitude solve completed successfully
        # This ensures we follow "measure twice, cut once" - verify solutions exist
        # immediately after solve completes, before proceeding.
        _validate_solve_success(f"{table_prefix}_bacal", refant=refant)
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
    # PRECONDITION CHECK: Verify bandpass phase solve completed successfully
    # This ensures we follow "measure twice, cut once" - verify solutions exist
    # immediately after solve completes, before proceeding.
    _validate_solve_success(f"{table_prefix}_bpcal", refant=refant)
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
    """Solve gain amplitude and phase; optionally short-timescale and fluxscale.
    
    **PRECONDITION**: If `ktable` or `bptables` are provided, they must exist and be
    compatible with the MS. This ensures consistent, reliable calibration results.
    """
    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"
    
    # PRECONDITION CHECK: Validate all required calibration tables
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators.
    required_tables = []
    if ktable:
        required_tables.append(ktable)
    required_tables.extend(bptables)
    
    if required_tables:
        print(f"Validating {len(required_tables)} calibration table(s) before gain calibration...")
        try:
            # Convert refant string to int for validation
            refant_int = int(refant) if isinstance(refant, str) else refant
            validate_caltables_for_use(
                required_tables, ms, require_all=True, refant=refant_int
            )
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(
                f"Calibration table validation failed. This is a required precondition for "
                f"gain calibration. Error: {e}"
            ) from e
    
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
        # PRECONDITION CHECK: Verify gain amplitude solve completed successfully
        # This ensures we follow "measure twice, cut once" - verify solutions exist
        # immediately after solve completes, before proceeding.
        _validate_solve_success(f"{table_prefix}_gacal", refant=refant)
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
    # PRECONDITION CHECK: Verify gain phase solve completed successfully
    # This ensures we follow "measure twice, cut once" - verify solutions exist
    # immediately after solve completes, before proceeding.
    _validate_solve_success(f"{table_prefix}_gpcal", refant=refant)
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
        # PRECONDITION CHECK: Verify short-timescale gain solve completed successfully
        # This ensures we follow "measure twice, cut once" - verify solutions exist
        # immediately after solve completes, before proceeding.
        _validate_solve_success(f"{table_prefix}_2gcal", refant=refant)
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
