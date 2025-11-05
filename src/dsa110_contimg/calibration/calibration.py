from typing import List, Optional, Union

import os
import fnmatch
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
    uvrange: str = "",
    minsnr: float = 5.0,
    skip_slow: bool = False,
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

        # Check for unflagged data (optimized: use getcol instead of per-row getcell)
        # This is much faster for large MS files
        field_flags = tb.getcol('FLAG', startrow=start_row, nrow=nrow_sel)
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
    # OPTIMIZATION: Allow skipping slow solve in fast mode for speed
    if not skip_slow:
        try:
            print(
                f"Running delay solve (K) on field {cal_field} "
                f"with refant {refant}..."
            )
            kwargs = dict(
                vis=ms,
                caltable=f"{table_prefix}_kcal",
                field=cal_field,
                solint=t_slow,
                refant=refant,
                gaintype="K",
                combine=combine,
                minsnr=minsnr,
                selectdata=True,
            )
            if uvrange:
                kwargs["uvrange"] = uvrange
                print(f"  Using uvrange filter: {uvrange}")
            casa_gaincal(**kwargs)
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
                kwargs = dict(
                    vis=ms,
                    caltable=f"{table_prefix}_kcal",
                    field=cal_field,
                    solint=t_slow,
                    refant=refant,
                    gaintype="K",
                    combine="",
                    minsnr=minsnr,
                    selectdata=True,
                )
                if uvrange:
                    kwargs["uvrange"] = uvrange
                casa_gaincal(**kwargs)
                # PRECONDITION CHECK: Verify K-calibration solve completed successfully
                # This ensures we follow "measure twice, cut once" - verify solutions exist
                # immediately after solve completes, before proceeding.
                _validate_solve_success(f"{table_prefix}_kcal", refant=refant)
                tables.append(f"{table_prefix}_kcal")
                print(f"✓ Delay solve completed (retry): {table_prefix}_kcal")
            except Exception as e2:
                raise RuntimeError(
                    f"Delay solve failed even with conservative settings: {e2}")
    else:
        print("  Skipping slow delay solve (fast mode optimization)")

    # Optional fast (short) delay solve
    # In skip_slow mode, fast solve is required (not optional)
    if t_fast or skip_slow:
        if skip_slow and not t_fast:
            # If skip_slow but no t_fast specified, use default
            t_fast = "60s"
            print(f"  Using default fast solution interval: {t_fast}")
        try:
            print(f"Running fast delay solve (K) on field {cal_field}...")
            kwargs = dict(
                vis=ms,
                caltable=f"{table_prefix}_2kcal",
                field=cal_field,
                solint=t_fast,
                refant=refant,
                gaintype="K",
                combine=combine,
                minsnr=minsnr,
                selectdata=True,
            )
            if uvrange:
                kwargs["uvrange"] = uvrange
            casa_gaincal(**kwargs)
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

    # QA validation of delay calibration tables (non-blocking: errors are warnings)
    # OPTIMIZATION: Only run QA validation if not in fast mode to avoid performance overhead
    # QA validation reads calibration tables which can be slow for large datasets
    # In fast mode, skip detailed QA to prioritize speed
    # Note: This is a trade-off - fast mode prioritizes speed over comprehensive QA
    if not uvrange or not uvrange.startswith('>'):
        # Only run QA if not in fast mode (no uvrange filter indicates normal mode)
        try:
            from dsa110_contimg.qa.pipeline_quality import check_calibration_quality
            check_calibration_quality(tables, ms_path=ms, alert_on_issues=True)
        except Exception as e:
            print(f"Warning: QA validation failed: {e}")
    else:
        print("  Skipping QA validation (fast mode)")

    return tables


def solve_prebandpass_phase(
    ms: str,
    cal_field: str,
    refant: str,
    table_prefix: Optional[str] = None,
    combine_fields: bool = False,
    uvrange: str = "",
    solint: str = "30s",  # Default to 30s for time-variable phase drifts (inf causes decorrelation)
    minsnr: float = 3.0,  # Default to 3.0 to match bandpass threshold (phase-only is more robust)
) -> str:
    """Solve phase-only calibration before bandpass to correct phase drifts in raw data.
    
    This phase-only calibration step is critical for uncalibrated raw data. It corrects
    for time-dependent phase variations that cause decorrelation and low SNR in bandpass
    calibration. This should be run BEFORE bandpass calibration.
    
    **PRECONDITION**: MODEL_DATA must be populated before calling this function.
    
    Returns:
        Path to phase-only calibration table (to be passed to bandpass via gaintable)
    """
    from casacore.tables import table  # type: ignore[import]
    import numpy as np  # type: ignore[import]
    
    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"
    
    # PRECONDITION CHECK: Verify MODEL_DATA exists and is populated
    print(f"Validating MODEL_DATA for pre-bandpass phase solve on field(s) {cal_field}...")
    with table(ms) as tb:
        if "MODEL_DATA" not in tb.colnames():
            raise ValueError(
                f"MODEL_DATA column does not exist in MS. "
                f"This is a required precondition for phase-only calibration. "
                f"Populate MODEL_DATA before calling solve_prebandpass_phase()."
            )
        
        model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
        if np.all(np.abs(model_sample) < 1e-10):
            raise ValueError(
                f"MODEL_DATA column exists but is all zeros (unpopulated). "
                f"This is a required precondition for phase-only calibration. "
                f"Populate MODEL_DATA before calling solve_prebandpass_phase()."
            )
    
    # Determine field selector based on combine_fields setting
    # - If combining across fields: use the full selection string to maximize SNR
    # - Otherwise: use a single peak field from the range (last index as heuristic)
    if '~' in str(cal_field):
        peak_field = str(cal_field).split('~')[-1]
    else:
        peak_field = str(cal_field)
    field_selector = str(cal_field) if combine_fields else peak_field
    print(
        f"Using field selector '{field_selector}' for pre-bandpass phase solve"
        + (f" (combined from range {cal_field})" if combine_fields else "")
    )
    
    # Combine across scans and fields when requested
    comb_parts = ["scan"]
    if combine_fields:
        comb_parts.append("field")
    comb = ",".join(comb_parts) if comb_parts else ""
    
    # Solve phase-only calibration (no previous calibrations applied)
    print(f"Running pre-bandpass phase-only solve on field {field_selector}...")
    kwargs = dict(
        vis=ms,
        caltable=f"{table_prefix}_prebp_phase",
        field=field_selector,
        solint=solint,
        refant=refant,
        calmode="p",  # Phase-only mode
        combine=comb,
        minsnr=minsnr,
        selectdata=True,
    )
    if uvrange:
        kwargs["uvrange"] = uvrange
    
    casa_gaincal(**kwargs)
    _validate_solve_success(f"{table_prefix}_prebp_phase", refant=refant)
    print(f"✓ Pre-bandpass phase-only solve completed: {table_prefix}_prebp_phase")
    
    return f"{table_prefix}_prebp_phase"


def solve_bandpass(
    ms: str,
    cal_field: str,
    refant: str,
    ktable: Optional[str],
    table_prefix: Optional[str] = None,
    set_model: bool = True,
    model_standard: str = "Perley-Butler 2017",
    combine_fields: bool = False,
    combine_spw: bool = False,
    minsnr: float = 5.0,
    uvrange: str = "",  # No implicit UV cut; caller/CLI may provide
    prebandpass_phase_table: Optional[str] = None,
    bp_smooth_type: Optional[str] = None,
    bp_smooth_window: Optional[int] = None,
) -> List[str]:
    """Solve bandpass using CASA bandpass task with bandtype='B'.
    
    This solves for frequency-dependent bandpass correction using the dedicated
    bandpass task, which properly handles per-channel solutions. The bandpass task
    requires a source model (smodel) which is provided via MODEL_DATA column.
    
    **PRECONDITION**: MODEL_DATA must be populated before calling this function.
    This ensures consistent, reliable calibration results across all calibrators
    (bright or faint). The calling code should verify MODEL_DATA exists and is
    populated before invoking solve_bandpass().
    
    **NOTE**: `ktable` parameter is kept for API compatibility but is NOT used
    (K-calibration is not used for DSA-110 connected-element array).
    """
    from casacore.tables import table  # type: ignore[import]
    import numpy as np  # type: ignore[import]
    from casatasks import bandpass as casa_bandpass  # type: ignore[import]
    
    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"
    
    # PRECONDITION CHECK: Verify MODEL_DATA exists and is populated
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators (bright or faint).
    print(f"Validating MODEL_DATA for bandpass solve on field(s) {cal_field}...")
    with table(ms) as tb:
        if "MODEL_DATA" not in tb.colnames():
            raise ValueError(
                f"MODEL_DATA column does not exist in MS. "
                f"This is a required precondition for bandpass calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_bandpass()."
            )
        
        # Check if MODEL_DATA is populated (not all zeros)
        model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
        if np.all(np.abs(model_sample) < 1e-10):
            raise ValueError(
                f"MODEL_DATA column exists but is all zeros (unpopulated). "
                f"This is a required precondition for bandpass calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_bandpass()."
            )
    
    # NOTE: K-table is NOT used for bandpass solve (K-calibration is applied in gain step, not before bandpass)
    # K-table parameter is kept for API compatibility but is not applied to bandpass solve
    
    # Determine CASA field selector based on combine_fields setting
    # - If combining across fields: use the full selection string to maximize SNR
    # - Otherwise: use a single peak field from the range (last index as heuristic)
    if '~' in str(cal_field):
        peak_field = str(cal_field).split('~')[-1]
    else:
        peak_field = str(cal_field)
    field_selector = str(cal_field) if combine_fields else peak_field
    print(
        f"Using field selector '{field_selector}' for bandpass calibration"
        + (f" (combined from range {cal_field})" if combine_fields else "")
    )

    # Avoid setjy here; CLI will write a calibrator MODEL_DATA when available.
    # Note: set_model and model_standard are kept for API compatibility but not used
    # (bandpass task uses MODEL_DATA column directly, not setjy)

    # Combine across scans by default to improve SNR; optionally across fields and SPWs
    # Only include 'spw' when explicitly requested and scientifically justified
    # (i.e., similar bandpass behavior across SPWs and appropriate spwmap on apply)
    comb_parts = ["scan"]
    if combine_fields:
        comb_parts.append("field")
    if combine_spw:
        comb_parts.append("spw")
    comb = ",".join(comb_parts)

    # Use bandpass task with bandtype='B' for proper bandpass calibration
    # The bandpass task requires MODEL_DATA to be populated (smodel source model)
    # uvrange='>1klambda' is the default to avoid short baselines
    # NOTE: Do NOT apply K-table to bandpass solve. K-calibration (delay correction)
    # should be applied AFTER bandpass, not before. Applying K-table before bandpass
    # can corrupt the frequency structure and cause low SNR/flagging.
    # CRITICAL: Apply pre-bandpass phase-only calibration if provided. This corrects
    # phase drifts in raw uncalibrated data that cause decorrelation and low SNR.
    combine_desc = f" (combining across {comb})" if comb else ""
    phase_desc = f" with pre-bandpass phase correction" if prebandpass_phase_table else ""
    print(
        f"Running bandpass solve using bandpass task (bandtype='B') on field {field_selector}{combine_desc}{phase_desc}...")
    kwargs = dict(
        vis=ms,
        caltable=f"{table_prefix}_bpcal",
        field=field_selector,
        solint="inf",  # Per-channel solution (bandpass)
        refant=refant,
        combine=comb,
        solnorm=True,
        bandtype="B",  # Bandpass type B (per-channel)
        selectdata=True,  # Required to use uvrange parameter
        minsnr=minsnr,  # Minimum SNR threshold for solutions
    )
    # Set uvrange (default: '>1klambda' to avoid short baselines)
    if uvrange:
        kwargs["uvrange"] = uvrange
    # Apply pre-bandpass phase-only calibration if provided
    # This corrects phase drifts that cause decorrelation in raw uncalibrated data
    if prebandpass_phase_table:
        kwargs["gaintable"] = [prebandpass_phase_table]
        print(f"  Applying pre-bandpass phase-only calibration: {prebandpass_phase_table}")
    # Do NOT apply K-table to bandpass solve (K-table is applied in gain calibration step)
    casa_bandpass(**kwargs)
    # PRECONDITION CHECK: Verify bandpass solve completed successfully
    # This ensures we follow "measure twice, cut once" - verify solutions exist
    # immediately after solve completes, before proceeding.
    _validate_solve_success(f"{table_prefix}_bpcal", refant=refant)
    print(f"✓ Bandpass solve completed: {table_prefix}_bpcal")

    # Optional smoothing of bandpass table (post-solve), off by default
    try:
        if bp_smooth_type and str(bp_smooth_type).lower() != "none" and bp_smooth_window and int(bp_smooth_window) > 1:
            try:
                # Prefer CASA smoothcal if available
                from casatasks import smoothcal as casa_smoothcal  # type: ignore[import]
                print(
                    f"Smoothing bandpass table '{table_prefix}_bpcal' with {bp_smooth_type} (window={bp_smooth_window})..."
                )
                # Best-effort: in-place smoothing using same output table
                casa_smoothcal(
                    vis=ms,
                    tablein=f"{table_prefix}_bpcal",
                    tableout=f"{table_prefix}_bpcal",
                    smoothtype=str(bp_smooth_type).lower(),
                    smoothwindow=int(bp_smooth_window),
                )
                print("✓ Bandpass table smoothing complete")
            except Exception as e:
                print(f"WARNING: Could not smooth bandpass table via CASA smoothcal: {e}")
    except Exception:
        # Do not fail calibration if smoothing parameters are malformed
        pass

    out = [f"{table_prefix}_bpcal"]
    
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
    minsnr: float = 5.0,
) -> List[str]:
    """Solve gain amplitude and phase; optionally short-timescale and fluxscale.
    
    **PRECONDITION**: MODEL_DATA must be populated before calling this function.
    This ensures consistent, reliable calibration results across all calibrators
    (bright or faint). The calling code should verify MODEL_DATA exists and is
    populated before invoking solve_gains().
    
    **PRECONDITION**: If `bptables` are provided, they must exist and be
    compatible with the MS. This ensures consistent, reliable calibration results.
    
    **NOTE**: `ktable` parameter is kept for API compatibility but is NOT used
    (K-calibration is not used for DSA-110 connected-element array).
    """
    from casacore.tables import table  # type: ignore[import]
    import numpy as np  # type: ignore[import]
    
    if table_prefix is None:
        table_prefix = f"{os.path.splitext(ms)[0]}_{cal_field}"
    
    # PRECONDITION CHECK: Verify MODEL_DATA exists and is populated
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators (bright or faint).
    print(f"Validating MODEL_DATA for gain solve on field(s) {cal_field}...")
    with table(ms) as tb:
        if "MODEL_DATA" not in tb.colnames():
            raise ValueError(
                f"MODEL_DATA column does not exist in MS. "
                f"This is a required precondition for gain calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_gains()."
            )
        
        # Check if MODEL_DATA is populated (not all zeros)
        model_sample = tb.getcol("MODEL_DATA", startrow=0, nrow=min(100, tb.nrows()))
        if np.all(np.abs(model_sample) < 1e-10):
            raise ValueError(
                f"MODEL_DATA column exists but is all zeros (unpopulated). "
                f"This is a required precondition for gain calibration. "
                f"Populate MODEL_DATA using setjy, ft(), or a catalog model before "
                f"calling solve_gains()."
            )
    
    # PRECONDITION CHECK: Validate all required calibration tables
    # This ensures we follow "measure twice, cut once" - establish requirements upfront
    # for consistent, reliable calibration across all calibrators.
    # NOTE: K-table is NOT used for gain calibration (K-calibration not used for DSA-110)
    if bptables:
        print(f"Validating {len(bptables)} bandpass table(s) before gain calibration...")
        try:
            # Convert refant string to int for validation
            refant_int = int(refant) if isinstance(refant, str) else refant
            validate_caltables_for_use(
                bptables, ms, require_all=True, refant=refant_int
            )
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(
                f"Calibration table validation failed. This is a required precondition for "
                f"gain calibration. Error: {e}"
            ) from e
    
    # Determine CASA field selector based on combine_fields setting
    if '~' in str(cal_field):
        peak_field = str(cal_field).split('~')[-1]
    else:
        peak_field = str(cal_field)
    field_selector = str(cal_field) if combine_fields else peak_field
    print(
        f"Using field selector '{field_selector}' for gain calibration"
        + (f" (combined from range {cal_field})" if combine_fields else "")
    )

    # NOTE: K-table is NOT used for gain calibration (K-calibration not used for DSA-110)
    # Only apply bandpass tables to gain solve
    gaintable = bptables
    # Combine across scans and fields when requested; otherwise do not combine
    comb = "scan,field" if combine_fields else ""

    # Always run phase-only gains (calmode='p') after bandpass
    # This corrects for time-dependent phase variations
    print(
        f"Running phase-only gain solve on field {field_selector}"
        + (" (combining across fields)..." if combine_fields else "...")
    )
    kwargs = dict(
        vis=ms,
        caltable=f"{table_prefix}_gpcal",
        field=field_selector,
        solint=solint,
        refant=refant,
        gaintype="G",
        calmode="p",  # Phase-only mode
        gaintable=gaintable,
        combine=comb,
        minsnr=minsnr,
        selectdata=True,
    )
    if uvrange:
        kwargs["uvrange"] = uvrange
    casa_gaincal(**kwargs)
    # PRECONDITION CHECK: Verify phase-only gain solve completed successfully
    # This ensures we follow "measure twice, cut once" - verify solutions exist
    # immediately after solve completes, before proceeding.
    _validate_solve_success(f"{table_prefix}_gpcal", refant=refant)
    print(f"✓ Phase-only gain solve completed: {table_prefix}_gpcal")

    out = [f"{table_prefix}_gpcal"]
    gaintable2 = gaintable + [f"{table_prefix}_gpcal"]

    if t_short:
        print(
            f"Running short-timescale phase-only gain solve on field {field_selector}"
            + (" (combining across fields)..." if combine_fields else "...")
        )
        kwargs = dict(
            vis=ms,
            caltable=f"{table_prefix}_2gcal",
            field=field_selector,
            solint=t_short,
            refant=refant,
            gaintype="G",
            calmode="p",  # Phase-only mode
            gaintable=gaintable2,
            combine=comb,
            minsnr=minsnr,
            selectdata=True,
        )
        if uvrange:
            kwargs["uvrange"] = uvrange
        casa_gaincal(**kwargs)
        # PRECONDITION CHECK: Verify short-timescale phase-only gain solve completed successfully
        # This ensures we follow "measure twice, cut once" - verify solutions exist
        # immediately after solve completes, before proceeding.
        _validate_solve_success(f"{table_prefix}_2gcal", refant=refant)
        print(f"✓ Short-timescale phase-only gain solve completed: {table_prefix}_2gcal")
        out.append(f"{table_prefix}_2gcal")

    # Note: Flux scaling removed - not used in phase-only calibration workflow

    # QA validation of gain calibration tables
    try:
        from dsa110_contimg.qa.pipeline_quality import check_calibration_quality
        check_calibration_quality(out, ms_path=ms, alert_on_issues=True)
    except Exception as e:
        print(f"Warning: QA validation failed: {e}")

    return out
